"""
Cloud Sync Service

Handles communication with the cloud backend:
- Syncing plate lists
- Sending heartbeats
- Posting events
"""

import asyncio
import logging
import socket
from datetime import datetime, timezone
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from cache import PlateCache

logger = logging.getLogger(__name__)


class CloudSync:
    """
    Manages synchronization with cloud backend.
    
    Responsibilities:
    - Pull plate lists periodically
    - Send device heartbeats
    - Post events for logging
    - Handle offline scenarios gracefully
    """
    
    def __init__(self, cache: PlateCache):
        self.cache = cache
        self._client: Optional[httpx.AsyncClient] = None
        self._running = False
        self._last_sync_success = False
        self._event_queue: list[dict] = []  # Queue for offline events
    
    async def connect(self):
        """Initialize HTTP client."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SteinMax-Edge-Agent/1.0",
            "X-Device-ID": settings.device_id,
        }
        
        if settings.cloud_api_key:
            headers["X-API-Key"] = settings.cloud_api_key
        
        self._client = httpx.AsyncClient(
            base_url=settings.cloud_api_url,
            headers=headers,
            timeout=httpx.Timeout(settings.cloud_api_timeout),
        )
        logger.info(f"Cloud sync connected to {settings.cloud_api_url}")
    
    async def close(self):
        """Close connections and flush queued events."""
        self._running = False
        
        # Try to flush any queued events
        await self._flush_event_queue()
        
        if self._client:
            await self._client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def sync_plates(self) -> bool:
        """
        Fetch latest plate list from cloud.
        
        Returns:
            True if sync successful
        """
        if not self._client:
            logger.error("Cloud client not connected")
            return False
        
        try:
            response = await self._client.get(
                f"/sync/devices/{settings.device_id}/plates"
            )
            response.raise_for_status()
            
            data = response.json()
            plates = data.get("plates", [])
            
            await self.cache.sync_plates(plates)
            
            self._last_sync_success = True
            logger.info(f"Plate sync complete: {len(plates)} plates")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Cloud API error during sync: {e.response.status_code}")
            self._last_sync_success = False
            return False
        except httpx.RequestError as e:
            logger.error(f"Cloud unreachable during sync: {e}")
            self._last_sync_success = False
            return False
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self._last_sync_success = False
            return False
    
    async def send_heartbeat(self) -> bool:
        """
        Send heartbeat to report device status.
        
        Returns:
            True if heartbeat successful
        """
        if not self._client:
            return False
        
        try:
            payload = {
                "status": "online",
                "local_ip": self._get_local_ip(),
                "firmware_version": "1.0.0",
                "plates_cached": await self.cache.get_plate_count(),
                "last_sync": await self.cache.get_last_sync(),
            }
            
            response = await self._client.post(
                f"/devices/{settings.device_id}/heartbeat",
                json=payload,
            )
            response.raise_for_status()
            
            logger.debug("Heartbeat sent successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
            return False
    
    async def post_event(self, event_data: dict) -> bool:
        """
        Post access event to cloud.
        
        If cloud is unreachable, queues event for later.
        
        Args:
            event_data: Event details
            
        Returns:
            True if event posted (or queued) successfully
        """
        # Ensure required fields
        event_data["device_id"] = settings.device_id
        event_data["property_id"] = settings.property_id
        event_data["created_at"] = datetime.now(timezone.utc).isoformat()
        
        if not self._client:
            self._queue_event(event_data)
            return True
        
        try:
            response = await self._client.post("/events", json=event_data)
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Event posted to cloud: {result.get('id')}")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to post event: {e.response.status_code}")
            self._queue_event(event_data)
            return False
        except httpx.RequestError as e:
            logger.warning(f"Cloud unreachable, queueing event: {e}")
            self._queue_event(event_data)
            return True  # Queued successfully
    
    def _queue_event(self, event_data: dict):
        """Queue event for later posting."""
        self._event_queue.append(event_data)
        
        # Limit queue size
        if len(self._event_queue) > 1000:
            self._event_queue = self._event_queue[-1000:]
        
        logger.debug(f"Event queued, {len(self._event_queue)} events pending")
    
    async def _flush_event_queue(self):
        """Attempt to post all queued events."""
        if not self._event_queue or not self._client:
            return
        
        logger.info(f"Flushing {len(self._event_queue)} queued events")
        
        posted = 0
        remaining = []
        
        for event in self._event_queue:
            try:
                response = await self._client.post("/events", json=event)
                response.raise_for_status()
                posted += 1
            except Exception:
                remaining.append(event)
        
        self._event_queue = remaining
        logger.info(f"Flushed {posted} events, {len(remaining)} remaining")
    
    async def start_background_tasks(self):
        """Start periodic sync and heartbeat tasks."""
        self._running = True
        
        # Initial sync
        logger.info("Running initial plate sync...")
        await self.sync_plates()
        await self.send_heartbeat()
        
        # Start background loops
        asyncio.create_task(self._sync_loop())
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._event_flush_loop())
        
        logger.info("Background sync tasks started")
    
    async def _sync_loop(self):
        """Periodically sync plate list."""
        while self._running:
            await asyncio.sleep(settings.sync_interval_seconds)
            try:
                await self.sync_plates()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
    
    async def _heartbeat_loop(self):
        """Periodically send heartbeat."""
        while self._running:
            await asyncio.sleep(settings.heartbeat_interval_seconds)
            try:
                await self.send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
    
    async def _event_flush_loop(self):
        """Periodically try to flush queued events."""
        while self._running:
            await asyncio.sleep(300)  # Every 5 minutes
            try:
                await self._flush_event_queue()
            except Exception as e:
                logger.error(f"Event flush error: {e}")
    
    def _get_local_ip(self) -> Optional[str]:
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None
    
    @property
    def is_connected(self) -> bool:
        """Check if last sync was successful."""
        return self._last_sync_success
