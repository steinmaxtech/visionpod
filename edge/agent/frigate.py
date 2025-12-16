"""
Frigate Integration

Handles interaction with Frigate for:
- Triggering clip saves on events
- Getting snapshots
- Retrieving recordings
"""

import logging
from typing import Optional
from datetime import datetime, timezone

import httpx

from config import settings

logger = logging.getLogger(__name__)


class FrigateClient:
    """
    Client for Frigate NVR API.
    
    Docs: https://docs.frigate.video/integrations/api
    """
    
    def __init__(self, base_url: str = None, camera_name: str = None):
        self.base_url = base_url or settings.frigate_url
        self.camera_name = camera_name or settings.frigate_camera_name
        self._client: Optional[httpx.AsyncClient] = None
        self._enabled = settings.frigate_enabled
    
    async def connect(self):
        """Initialize HTTP client."""
        if not self._enabled:
            logger.info("Frigate integration disabled")
            return
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(10.0),
        )
        
        # Test connection
        try:
            response = await self._client.get("/api/version")
            response.raise_for_status()
            version = response.json()
            logger.info(f"Connected to Frigate {version}")
        except Exception as e:
            logger.warning(f"Could not connect to Frigate: {e}")
            self._enabled = False
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled and self._client is not None
    
    async def get_snapshot(self) -> Optional[bytes]:
        """
        Get current snapshot from camera.
        
        Returns:
            JPEG image bytes, or None on error
        """
        if not self.is_enabled:
            return None
        
        try:
            response = await self._client.get(
                f"/api/{self.camera_name}/latest.jpg",
                params={"quality": 80},
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Failed to get snapshot: {e}")
            return None
    
    async def create_event(
        self,
        label: str = "vehicle",
        sub_label: str = None,
        duration: int = 10,
        include_recording: bool = True,
        draw_box: bool = False,
    ) -> Optional[str]:
        """
        Create a manual event in Frigate.
        
        This triggers Frigate to save a clip around the current time.
        
        Args:
            label: Event label (e.g., "vehicle", "person")
            sub_label: Sub-label (e.g., plate number)
            duration: Event duration in seconds
            include_recording: Whether to save recording
            draw_box: Whether to draw detection box
            
        Returns:
            Event ID, or None on error
        """
        if not self.is_enabled:
            return None
        
        try:
            params = {
                "label": label,
                "duration": duration,
                "include_recording": int(include_recording),
                "draw": {"boxes": draw_box},
            }
            
            if sub_label:
                params["sub_label"] = sub_label
            
            response = await self._client.post(
                f"/api/{self.camera_name}/events/create",
                json=params,
            )
            response.raise_for_status()
            
            result = response.json()
            event_id = result.get("event_id")
            logger.info(f"Created Frigate event: {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to create Frigate event: {e}")
            return None
    
    async def get_event_clip_url(self, event_id: str) -> Optional[str]:
        """
        Get URL for event clip.
        
        Args:
            event_id: Frigate event ID
            
        Returns:
            URL to clip, or None
        """
        if not self.is_enabled:
            return None
        
        # Frigate serves clips at this path
        return f"{self.base_url}/api/events/{event_id}/clip.mp4"
    
    async def get_event_snapshot_url(self, event_id: str) -> Optional[str]:
        """
        Get URL for event snapshot.
        
        Args:
            event_id: Frigate event ID
            
        Returns:
            URL to snapshot, or None
        """
        if not self.is_enabled:
            return None
        
        return f"{self.base_url}/api/events/{event_id}/snapshot.jpg"
    
    async def get_recordings(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> list[dict]:
        """
        Get list of recordings.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of recording metadata
        """
        if not self.is_enabled:
            return []
        
        try:
            params = {}
            if start_time:
                params["after"] = int(start_time.timestamp())
            if end_time:
                params["before"] = int(end_time.timestamp())
            
            response = await self._client.get(
                f"/api/{self.camera_name}/recordings",
                params=params,
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get recordings: {e}")
            return []
    
    async def get_stats(self) -> dict:
        """Get Frigate statistics."""
        if not self.is_enabled:
            return {}
        
        try:
            response = await self._client.get("/api/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get Frigate stats: {e}")
            return {}


class MockFrigateClient(FrigateClient):
    """Mock client for testing without Frigate."""
    
    async def connect(self):
        logger.info("Mock Frigate client initialized")
        self._enabled = True
    
    async def close(self):
        pass
    
    async def get_snapshot(self) -> Optional[bytes]:
        logger.debug("[MOCK] Would get snapshot")
        return None
    
    async def create_event(self, **kwargs) -> Optional[str]:
        logger.debug(f"[MOCK] Would create event: {kwargs}")
        return "mock-event-id"
    
    async def get_event_clip_url(self, event_id: str) -> Optional[str]:
        return None
    
    async def get_event_snapshot_url(self, event_id: str) -> Optional[str]:
        return None
