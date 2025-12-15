"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# BASE SCHEMAS
# =============================================================================

class BaseSchema(BaseModel):
    """Base schema with common config."""
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# ORGANIZATION SCHEMAS
# =============================================================================

class OrganizationBase(BaseModel):
    name: str
    slug: Optional[str] = None
    settings: dict = Field(default_factory=dict)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    settings: Optional[dict] = None


class OrganizationResponse(OrganizationBase, BaseSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime


# =============================================================================
# PROPERTY SCHEMAS
# =============================================================================

class PropertyBase(BaseModel):
    name: str
    address: Optional[str] = None
    timezone: str = "America/New_York"
    settings: dict = Field(default_factory=dict)
    status: str = "active"


class PropertyCreate(PropertyBase):
    organization_id: UUID


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    timezone: Optional[str] = None
    settings: Optional[dict] = None
    status: Optional[str] = None


class PropertyResponse(PropertyBase, BaseSchema):
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime


class PropertyWithStats(PropertyResponse):
    """Property with additional statistics."""
    device_count: int = 0
    plate_count: int = 0
    events_today: int = 0


# =============================================================================
# DEVICE SCHEMAS
# =============================================================================

class DeviceBase(BaseModel):
    name: str
    device_type: str = "lpr"
    tailscale_ip: Optional[str] = None
    tailscale_hostname: Optional[str] = None
    local_ip: Optional[str] = None
    gatewise_device_id: Optional[str] = None
    gatewise_api_key: Optional[str] = None
    plate_recognizer_token: Optional[str] = None
    camera_rtsp_url: Optional[str] = None
    config: dict = Field(default_factory=dict)


class DeviceCreate(DeviceBase):
    property_id: UUID


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    device_type: Optional[str] = None
    tailscale_ip: Optional[str] = None
    tailscale_hostname: Optional[str] = None
    local_ip: Optional[str] = None
    gatewise_device_id: Optional[str] = None
    gatewise_api_key: Optional[str] = None
    plate_recognizer_token: Optional[str] = None
    camera_rtsp_url: Optional[str] = None
    status: Optional[str] = None
    config: Optional[dict] = None


class DeviceResponse(DeviceBase, BaseSchema):
    id: UUID
    property_id: UUID
    status: str
    last_seen: Optional[datetime]
    last_error: Optional[str]
    firmware_version: Optional[str]
    created_at: datetime
    updated_at: datetime


class DeviceHeartbeat(BaseModel):
    """Edge device heartbeat payload."""
    status: str = "online"
    firmware_version: Optional[str] = None
    local_ip: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# PLATE SCHEMAS
# =============================================================================

class PlateBase(BaseModel):
    plate_number: str = Field(..., min_length=1, max_length=20)
    plate_state: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, max_length=255)
    list_type: str = "allow"
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    schedule: Optional[dict] = None
    notes: Optional[str] = None


class PlateCreate(PlateBase):
    property_id: UUID


class PlateUpdate(BaseModel):
    plate_number: Optional[str] = Field(None, min_length=1, max_length=20)
    plate_state: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, max_length=255)
    list_type: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    schedule: Optional[dict] = None
    notes: Optional[str] = None


class PlateResponse(PlateBase, BaseSchema):
    id: UUID
    property_id: UUID
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class PlateBulkCreate(BaseModel):
    """Bulk plate import."""
    plates: list[PlateCreate]


# =============================================================================
# EVENT SCHEMAS
# =============================================================================

class EventBase(BaseModel):
    plate_number: Optional[str] = None
    plate_confidence: Optional[float] = None
    plate_region: Optional[str] = None
    decision: str
    decision_reason: Optional[str] = None


class EventCreate(EventBase):
    device_id: UUID
    property_id: UUID
    matched_plate_id: Optional[UUID] = None
    image_url: Optional[str] = None
    image_s3_key: Optional[str] = None
    clip_url: Optional[str] = None
    clip_s3_key: Optional[str] = None
    gatewise_response: Optional[dict] = None
    plate_recognizer_response: Optional[dict] = None
    processing_time_ms: Optional[int] = None


class EventResponse(EventBase, BaseSchema):
    id: UUID
    device_id: UUID
    property_id: UUID
    matched_plate_id: Optional[UUID]
    image_url: Optional[str]
    clip_url: Optional[str]
    processing_time_ms: Optional[int]
    created_at: datetime


class EventWithDetails(EventResponse):
    """Event with related device and plate info."""
    device_name: Optional[str] = None
    matched_plate_description: Optional[str] = None


class EventFilter(BaseModel):
    """Filters for event queries."""
    property_id: Optional[UUID] = None
    device_id: Optional[UUID] = None
    plate_number: Optional[str] = None
    decision: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


# =============================================================================
# WEBHOOK SCHEMAS
# =============================================================================

class PlateRecognizerWebhook(BaseModel):
    """Webhook payload from Plate Recognizer Stream."""
    
    class VehicleData(BaseModel):
        score: float
        type: Optional[str] = None
        box: Optional[dict] = None
    
    class PlateResult(BaseModel):
        score: float
        plate: str
        region: Optional[dict] = None
        vehicle: Optional[dict] = None
        box: Optional[dict] = None
    
    # Core fields
    data: dict  # Full plate recognizer response
    filename: Optional[str] = None
    timestamp: Optional[str] = None
    camera_id: Optional[str] = None
    
    # Extracted for convenience
    @property
    def best_plate(self) -> Optional[str]:
        """Extract best plate from response."""
        results = self.data.get("results", [])
        if results:
            return results[0].get("plate", "").upper()
        return None
    
    @property
    def confidence(self) -> Optional[float]:
        """Extract confidence score."""
        results = self.data.get("results", [])
        if results:
            return results[0].get("score", 0) * 100  # Convert to percentage
        return None


class WebhookResponse(BaseModel):
    """Response to webhook."""
    success: bool
    event_id: Optional[UUID] = None
    decision: str
    message: Optional[str] = None


# =============================================================================
# SYNC SCHEMAS (for edge devices)
# =============================================================================

class PlateListSync(BaseModel):
    """Plate list for edge device sync."""
    plates: list[PlateResponse]
    sync_timestamp: datetime
    property_id: UUID


class DeviceConfig(BaseModel):
    """Configuration for edge device."""
    device_id: UUID
    property_id: UUID
    gatewise_device_id: Optional[str]
    gatewise_api_key: Optional[str]
    plate_recognizer_token: Optional[str]
    camera_rtsp_url: Optional[str]
    config: dict


# =============================================================================
# PAGINATION
# =============================================================================

class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    items: list
    total: int
    limit: int
    offset: int
    
    @property
    def has_more(self) -> bool:
        return (self.offset + len(self.items)) < self.total
