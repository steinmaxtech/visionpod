"""SQLAlchemy ORM models for SteinMax Vision."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Organization(Base):
    """Customer organization (property management company, HOA, etc.)."""
    
    __tablename__ = "organizations"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    properties: Mapped[list["Property"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship(back_populates="organization")


class Property(Base):
    """A physical location with gates/access points."""
    
    __tablename__ = "properties"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="America/New_York")
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="properties")
    devices: Mapped[list["Device"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    plates: Mapped[list["Plate"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="property", cascade="all, delete-orphan")


class Device(Base):
    """Edge device deployed at a property."""
    
    __tablename__ = "devices"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), default="lpr")
    
    # Networking
    tailscale_ip: Mapped[Optional[str]] = mapped_column(String(45))
    tailscale_hostname: Mapped[Optional[str]] = mapped_column(String(255))
    local_ip: Mapped[Optional[str]] = mapped_column(String(45))
    
    # Integrations
    gatewise_device_id: Mapped[Optional[str]] = mapped_column(String(255))
    gatewise_api_key: Mapped[Optional[str]] = mapped_column(String(255))
    plate_recognizer_token: Mapped[Optional[str]] = mapped_column(String(255))
    camera_rtsp_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="offline")
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    firmware_version: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Config
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    property: Mapped["Property"] = relationship(back_populates="devices")
    events: Mapped[list["Event"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class Plate(Base):
    """License plate in allow/deny list."""
    
    __tablename__ = "plates"
    __table_args__ = (
        UniqueConstraint("property_id", "plate_number", name="uq_property_plate"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    
    # Plate info
    plate_number: Mapped[str] = mapped_column(String(20), nullable=False)
    plate_state: Mapped[Optional[str]] = mapped_column(String(10))
    description: Mapped[Optional[str]] = mapped_column(String(255))
    
    # List configuration
    list_type: Mapped[str] = mapped_column(String(50), default="allow")
    
    # Time restrictions
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Schedule
    schedule: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    property: Mapped["Property"] = relationship(back_populates="plates")
    events: Mapped[list["Event"]] = relationship(back_populates="matched_plate")


class Event(Base):
    """Access event (plate detection and decision)."""
    
    __tablename__ = "events"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    
    # Detection data
    plate_number: Mapped[Optional[str]] = mapped_column(String(20))
    plate_confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    plate_region: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Decision
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    decision_reason: Mapped[Optional[str]] = mapped_column(String(255))
    matched_plate_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("plates.id", ondelete="SET NULL"))
    
    # Media
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    image_s3_key: Mapped[Optional[str]] = mapped_column(String(500))
    clip_url: Mapped[Optional[str]] = mapped_column(Text)
    clip_s3_key: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Integration responses
    gatewise_response: Mapped[Optional[dict]] = mapped_column(JSONB)
    plate_recognizer_response: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Metadata
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    device: Mapped["Device"] = relationship(back_populates="events")
    property: Mapped["Property"] = relationship(back_populates="events")
    matched_plate: Mapped[Optional["Plate"]] = relationship(back_populates="events")


class User(Base):
    """User account (synced from Clerk)."""
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    
    # Organization
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String(50), default="member")
    
    # Permissions
    permissions: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="active")
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(back_populates="users")


class AuditLog(Base):
    """Audit trail for compliance."""
    
    __tablename__ = "audit_log"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50))
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    changes: Mapped[Optional[dict]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
