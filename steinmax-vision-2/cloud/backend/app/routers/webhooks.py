"""Webhook endpoints for external integrations."""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Device, Event, Plate
from app.schemas import WebhookResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def lookup_plate(
    db: AsyncSession,
    property_id: UUID,
    plate_number: str,
) -> tuple[bool, Optional[Plate], str]:
    """
    Look up a plate in the allow list.
    Returns: (is_allowed, matched_plate, reason)
    """
    normalized_plate = plate_number.upper().replace(" ", "").replace("-", "")
    
    # Find matching plate
    result = await db.execute(
        select(Plate)
        .where(Plate.property_id == property_id)
        .where(Plate.plate_number == normalized_plate)
    )
    plate = result.scalar_one_or_none()
    
    if not plate:
        return False, None, "Plate not found in allow list"
    
    # Check if on deny list
    if plate.list_type == "deny":
        return False, plate, "Plate is on deny list"
    
    # Check expiration
    now = datetime.now(timezone.utc)
    if plate.expires_at and plate.expires_at < now:
        return False, plate, "Plate authorization has expired"
    
    # Check start time
    if plate.starts_at and plate.starts_at > now:
        return False, plate, "Plate authorization not yet active"
    
    # TODO: Check schedule (time-of-day restrictions)
    # if plate.schedule:
    #     if not is_within_schedule(plate.schedule, now):
    #         return False, plate, "Outside authorized time window"
    
    return True, plate, "Plate matched allow list"


async def trigger_gatewise(
    device: Device,
    plate_number: str,
    reason: str,
) -> dict:
    """
    Trigger Gatewise to open the gate.
    Returns the API response.
    """
    # TODO: Implement actual Gatewise API call
    # For now, just log and return mock response
    
    logger.info(
        f"GATEWISE: Would open gate for device {device.gatewise_device_id} "
        f"(plate: {plate_number}, reason: {reason})"
    )
    
    # Mock response - replace with actual API call:
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(
    #         f"{settings.gatewise_api_url}/access/open",
    #         headers={"Authorization": f"Bearer {device.gatewise_api_key}"},
    #         json={
    #             "device_id": device.gatewise_device_id,
    #             "reason": reason,
    #         }
    #     )
    #     return response.json()
    
    return {
        "success": True,
        "message": "Gate opened (mock)",
        "device_id": device.gatewise_device_id,
    }


@router.post("/plate-recognizer/{device_id}", response_model=WebhookResponse)
async def plate_recognizer_webhook(
    device_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook endpoint for Plate Recognizer Stream.
    
    This is called every time Plate Recognizer detects a plate.
    Flow:
    1. Parse the plate detection
    2. Look up plate in allow list
    3. If allowed, trigger Gatewise
    4. Log the event
    """
    start_time = datetime.now(timezone.utc)
    
    # Parse webhook payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Get device
    result = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        logger.warning(f"Webhook received for unknown device: {device_id}")
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Extract plate data from Plate Recognizer response
    results = payload.get("data", {}).get("results", [])
    
    if not results:
        logger.debug(f"No plates detected in webhook for device {device_id}")
        return WebhookResponse(
            success=True,
            decision="unknown",
            message="No plates detected in image",
        )
    
    # Get best result
    best_result = results[0]
    plate_number = best_result.get("plate", "").upper()
    confidence = best_result.get("score", 0) * 100  # Convert to percentage
    region = best_result.get("region", {}).get("code", "")
    
    if not plate_number:
        logger.warning(f"Empty plate number in webhook for device {device_id}")
        return WebhookResponse(
            success=True,
            decision="unknown",
            message="Could not read plate number",
        )
    
    logger.info(f"Plate detected: {plate_number} (confidence: {confidence:.1f}%) on device {device_id}")
    
    # Look up plate in allow list
    is_allowed, matched_plate, reason = await lookup_plate(
        db, device.property_id, plate_number
    )
    
    decision = "granted" if is_allowed else "denied"
    
    # Trigger gate if allowed
    gatewise_response = None
    if is_allowed and device.gatewise_device_id:
        try:
            gatewise_response = await trigger_gatewise(
                device,
                plate_number,
                f"LPR match: {matched_plate.description}" if matched_plate else "LPR match",
            )
        except Exception as e:
            logger.error(f"Gatewise API error: {e}")
            gatewise_response = {"error": str(e)}
    
    # Calculate processing time
    processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
    
    # Create event record
    event = Event(
        device_id=device.id,
        property_id=device.property_id,
        plate_number=plate_number,
        plate_confidence=confidence,
        plate_region=region,
        decision=decision,
        decision_reason=reason,
        matched_plate_id=matched_plate.id if matched_plate else None,
        plate_recognizer_response=payload,
        gatewise_response=gatewise_response,
        processing_time_ms=processing_time,
        # image_url and clip_url would be set if we upload to S3
    )
    
    db.add(event)
    await db.flush()
    await db.refresh(event)
    
    # Update device last_seen
    device.last_seen = datetime.now(timezone.utc)
    device.status = "online"
    
    logger.info(
        f"Event created: {event.id} - {plate_number} {decision} "
        f"(processing: {processing_time}ms)"
    )
    
    return WebhookResponse(
        success=True,
        event_id=event.id,
        decision=decision,
        message=reason,
    )


@router.post("/test")
async def test_webhook(request: Request):
    """Test endpoint to inspect webhook payloads."""
    payload = await request.json()
    logger.info(f"Test webhook received: {payload}")
    return {"received": payload}
