"""
SteinMax Vision Edge Agent

Main application that runs on edge devices at customer sites.

Responsibilities:
- Receive plate detection webhooks from Plate Recognizer
- Check plates against local cache (Redis + SQLite fallback)
- Trigger Gatewise to open gates for authorized vehicles
- Create events in Frigate for video clips
- Log events to cloud backend
- Sync plate lists from cloud
- Send heartbeats to report device status
"""

import asyncio
import base64
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import settings
from cache import PlateCache
from gatewise import GatewiseClient, MockGatewiseClient
from frigate import FrigateClient, MockFrigateClient
from sync import CloudSync

# =============================================================================
# LOGGING SETUP
# =============================================================================

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("edge-agent")

# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

cache: Optional[PlateCache] = None
gatewise: Optional[GatewiseClient] = None
frigate: Optional[FrigateClient] = None
cloud_sync: Optional[CloudSync] = None

# =============================================================================
# APPLICATION LIFECYCLE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    global cache, gatewise, frigate, cloud_sync
    
    logger.info("=" * 60)
    logger.info("STEINMAX VISION EDGE AGENT")
    logger.info("=" * 60)
    logger.info(f"Device ID:    {settings.device_id}")
    logger.info(f"Property ID:  {settings.property_id}")
    logger.info(f"Cloud API:    {settings.cloud_api_url}")
    logger.info(f"Gatewise:     {'Enabled' if settings.gatewise_enabled else 'Disabled'}")
    logger.info(f"Frigate:      {'Enabled' if settings.frigate_enabled else 'Disabled'}")
    logger.info("=" * 60)
    
    # Initialize plate cache
    cache = PlateCache()
    await cache.connect()
    
    # Initialize Gatewise client
    if settings.gatewise_enabled and settings.gatewise_api_key:
        gatewise = GatewiseClient()
        await gatewise.connect()
    else:
        logger.warning("Gatewise not configured, using mock client")
        gatewise = MockGatewiseClient()
        await gatewise.connect()
    
    # Initialize Frigate client
    if settings.frigate_enabled:
        frigate = FrigateClient()
        await frigate.connect()
    else:
        frigate = MockFrigateClient()
        await frigate.connect()
    
    # Initialize cloud sync
    cloud_sync = CloudSync(cache)
    await cloud_sync.connect()
    await cloud_sync.start_background_tasks()
    
    # Report ready status
    plate_count = await cache.get_plate_count()
    logger.info(f"✓ Ready! {plate_count} plates in cache")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await cloud_sync.close()
    await gatewise.close()
    await frigate.close()
    await cache.close()
    logger.info("Goodbye!")


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="SteinMax Vision Edge Agent",
    description="Vehicle Access Control - Edge Processing",
    version="1.0.0",
    lifespan=lifespan,
)

# =============================================================================
# SCHEMAS
# =============================================================================

class WebhookResponse(BaseModel):
    success: bool
    decision: str
    plate: Optional[str] = None
    confidence: Optional[float] = None
    message: Optional[str] = None
    processing_ms: Optional[int] = None
    event_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    device_id: str
    property_id: str
    plates_cached: int
    last_sync: Optional[str]
    cloud_connected: bool
    gatewise_enabled: bool
    frigate_enabled: bool
    uptime_seconds: int


# Track uptime
_start_time = datetime.now(timezone.utc)

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    plate_count = await cache.get_plate_count() if cache else 0
    last_sync = await cache.get_last_sync() if cache else None
    uptime = int((datetime.now(timezone.utc) - _start_time).total_seconds())
    
    return HealthResponse(
        status="healthy",
        device_id=settings.device_id,
        property_id=settings.property_id,
        plates_cached=plate_count,
        last_sync=last_sync,
        cloud_connected=cloud_sync.is_connected if cloud_sync else False,
        gatewise_enabled=gatewise.is_enabled if gatewise else False,
        frigate_enabled=frigate.is_enabled if frigate else False,
        uptime_seconds=uptime,
    )


@app.post("/webhook/plate", response_model=WebhookResponse)
async def plate_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for Plate Recognizer Stream.
    
    Called every time a plate is detected.
    
    Flow:
    1. Extract plate from webhook
    2. Check against local cache
    3. If allowed, open gate via Gatewise
    4. Create Frigate event for clip
    5. Log to cloud (async)
    """
    start_time = datetime.now(timezone.utc)
    
    # Parse webhook payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Extract plate data from Plate Recognizer response
    data = payload.get("data", payload)  # Handle both nested and flat formats
    results = data.get("results", [])
    
    if not results:
        logger.debug("No plates detected in webhook")
        return WebhookResponse(
            success=True,
            decision="unknown",
            message="No plates detected in image",
        )
    
    # Get best result
    best = results[0]
    plate_number = best.get("plate", "").upper().replace(" ", "")
    confidence = best.get("score", 0) * 100  # Convert to percentage
    region = best.get("region", {}).get("code", "")
    
    if not plate_number:
        logger.warning("Empty plate number in webhook")
        return WebhookResponse(
            success=True,
            decision="unknown",
            message="Could not read plate number",
        )
    
    logger.info(f"🚗 Plate detected: {plate_number} ({confidence:.1f}%)")
    
    # Check against local cache
    check_result = await cache.check_plate(plate_number)
    
    decision = "granted" if check_result["allowed"] else "denied"
    reason = check_result["reason"]
    
    if decision == "granted":
        logger.info(f"✅ ACCESS GRANTED: {plate_number} - {reason}")
    else:
        logger.info(f"❌ ACCESS DENIED: {plate_number} - {reason}")
    
    # Trigger gate if allowed
    gatewise_response = None
    if check_result["allowed"] and gatewise and gatewise.is_enabled:
        description = check_result.get("description") or plate_number
        gatewise_response = await gatewise.open_gate(
            reason=f"LPR: {description}",
            plate_number=plate_number,
        )
        
        if gatewise_response.get("success"):
            logger.info(f"🚪 Gate opened for {plate_number}")
        else:
            logger.error(f"🚪 Gate open FAILED: {gatewise_response}")
    
    # Create Frigate event for clip
    frigate_event_id = None
    if frigate and frigate.is_enabled:
        frigate_event_id = await frigate.create_event(
            label="vehicle",
            sub_label=plate_number,
            duration=10,
            include_recording=True,
        )
    
    # Get snapshot from Frigate
    snapshot_data = None
    if frigate and frigate.is_enabled:
        snapshot_bytes = await frigate.get_snapshot()
        if snapshot_bytes:
            snapshot_data = base64.b64encode(snapshot_bytes).decode()
    
    # Calculate processing time
    processing_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
    
    # Build event data for cloud
    event_data = {
        "plate_number": plate_number,
        "plate_confidence": confidence,
        "plate_region": region,
        "decision": decision,
        "decision_reason": reason,
        "matched_plate_id": check_result.get("plate_id"),
        "gatewise_response": gatewise_response,
        "plate_recognizer_response": payload,
        "processing_time_ms": processing_ms,
        "frigate_event_id": frigate_event_id,
    }
    
    # Post to cloud in background (don't block response)
    background_tasks.add_task(cloud_sync.post_event, event_data)
    
    return WebhookResponse(
        success=True,
        decision=decision,
        plate=plate_number,
        confidence=confidence,
        message=reason,
        processing_ms=processing_ms,
        event_id=frigate_event_id,
    )


@app.post("/webhook/test")
async def test_webhook(request: Request):
    """Test endpoint to inspect webhook payloads."""
    payload = await request.json()
    logger.info(f"Test webhook received: {payload}")
    return {"received": payload}


@app.post("/sync/trigger")
async def trigger_sync():
    """Manually trigger plate list sync."""
    if not cloud_sync:
        raise HTTPException(status_code=503, detail="Sync not initialized")
    
    success = await cloud_sync.sync_plates()
    count = await cache.get_plate_count()
    
    return {
        "success": success,
        "plates_synced": count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/plates/check/{plate_number}")
async def check_plate(plate_number: str):
    """
    Manually check if a plate is allowed.
    
    Useful for testing without a camera.
    """
    if not cache:
        raise HTTPException(status_code=503, detail="Cache not ready")
    
    result = await cache.check_plate(plate_number)
    return result


@app.get("/plates/count")
async def get_plate_count():
    """Get number of cached plates."""
    count = await cache.get_plate_count() if cache else 0
    last_sync = await cache.get_last_sync() if cache else None
    
    return {
        "count": count,
        "last_sync": last_sync,
    }


@app.post("/gate/open")
async def manual_gate_open(reason: str = "Manual override"):
    """
    Manually trigger gate open.
    
    For testing or emergency access.
    """
    if not gatewise or not gatewise.is_enabled:
        raise HTTPException(status_code=503, detail="Gatewise not configured")
    
    result = await gatewise.open_gate(reason=reason)
    return result


@app.get("/frigate/snapshot")
async def get_frigate_snapshot():
    """Get current camera snapshot from Frigate."""
    if not frigate or not frigate.is_enabled:
        raise HTTPException(status_code=503, detail="Frigate not configured")
    
    snapshot = await frigate.get_snapshot()
    if not snapshot:
        raise HTTPException(status_code=503, detail="Failed to get snapshot")
    
    return JSONResponse(
        content={"snapshot": base64.b64encode(snapshot).decode()},
        media_type="application/json",
    )


@app.get("/config")
async def get_config():
    """Show current configuration (for debugging)."""
    return {
        "device_id": settings.device_id,
        "property_id": settings.property_id,
        "cloud_api_url": settings.cloud_api_url,
        "gatewise_enabled": settings.gatewise_enabled,
        "gatewise_device_id": settings.gatewise_device_id,
        "frigate_enabled": settings.frigate_enabled,
        "frigate_url": settings.frigate_url,
        "sync_interval": settings.sync_interval_seconds,
        "heartbeat_interval": settings.heartbeat_interval_seconds,
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        access_log=True,
    )
