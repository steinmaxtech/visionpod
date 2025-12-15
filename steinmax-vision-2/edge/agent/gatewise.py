"""
Gatewise API Client

Controls access gates via Gatewise's cloud API.
"""

import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

logger = logging.getLogger(__name__)


class GatewiseClient:
    """
    Client for Gatewise access control API.
    
    Handles:
    - Opening gates
    - Checking gate status
    - Error handling and retries
    """
    
    def __init__(
        self,
        api_url: str = None,
        api_key: str = None,
        device_id: str = None,
    ):
        self.api_url = api_url or settings.gatewise_api_url
        self.api_key = api_key or settings.gatewise_api_key
        self.device_id = device_id or settings.gatewise_device_id
        self._client: Optional[httpx.AsyncClient] = None
        self._enabled = settings.gatewise_enabled and bool(self.api_key)
    
    async def connect(self):
        """Initialize HTTP client."""
        if not self._enabled:
            logger.warning("Gatewise disabled or not configured")
            return
        
        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "SteinMax-Edge-Agent/1.0",
            },
            timeout=httpx.Timeout(settings.gatewise_timeout),
        )
        logger.info(f"Gatewise client initialized for device {self.device_id}")
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
    
    @property
    def is_enabled(self) -> bool:
        """Check if Gatewise is enabled and configured."""
        return self._enabled and self._client is not None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    )
    async def open_gate(
        self,
        reason: str = "LPR Access",
        plate_number: str = None,
    ) -> dict:
        """
        Trigger gate to open.
        
        Args:
            reason: Reason for opening (logged by Gatewise)
            plate_number: Optional plate number for logging
            
        Returns:
            API response dict with success status
        """
        if not self.is_enabled:
            logger.warning("Gatewise not enabled, skipping gate open")
            return {"success": False, "error": "Gatewise not enabled", "mock": True}
        
        if not self.device_id:
            logger.error("No Gatewise device ID configured")
            return {"success": False, "error": "No device ID configured"}
        
        # Build request payload
        # NOTE: Adjust this based on actual Gatewise API documentation
        payload = {
            "device_id": self.device_id,
            "action": "unlock",
            "duration": 5,  # Hold open for 5 seconds
            "reason": reason,
        }
        
        if plate_number:
            payload["metadata"] = {"plate_number": plate_number}
        
        try:
            logger.info(f"Opening gate {self.device_id}: {reason}")
            
            # NOTE: Adjust endpoint based on actual Gatewise API
            response = await self._client.post("/access/trigger", json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Gate opened successfully: {result}")
            
            return {
                "success": True,
                "response": result,
                "device_id": self.device_id,
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Gatewise API error: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}",
                "detail": e.response.text,
            }
        except httpx.TimeoutException:
            logger.error("Gatewise API timeout")
            return {"success": False, "error": "Timeout"}
        except httpx.RequestError as e:
            logger.error(f"Gatewise request failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_status(self) -> dict:
        """Get gate status (if supported by Gatewise)."""
        if not self.is_enabled:
            return {"error": "Gatewise not enabled"}
        
        try:
            response = await self._client.get(f"/devices/{self.device_id}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get gate status: {e}")
            return {"error": str(e)}


class MockGatewiseClient(GatewiseClient):
    """
    Mock client for testing without real Gatewise hardware.
    
    Logs actions but doesn't actually open gates.
    """
    
    async def connect(self):
        logger.info("Mock Gatewise client initialized (no real hardware)")
        self._enabled = True
    
    async def close(self):
        pass
    
    @property
    def is_enabled(self) -> bool:
        return True
    
    async def open_gate(self, reason: str = "LPR Access", plate_number: str = None) -> dict:
        logger.info(f"[MOCK] Would open gate: {reason} (plate: {plate_number})")
        return {
            "success": True,
            "mock": True,
            "message": f"Gate would open: {reason}",
            "device_id": self.device_id or "mock-device",
        }
    
    async def get_status(self) -> dict:
        return {"status": "mock", "gate": "unknown"}
