"""Devices API endpoints."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Device, Property
from app.schemas import (
    DeviceCreate,
    DeviceHeartbeat,
    DeviceResponse,
    DeviceUpdate,
)

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    property_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all devices, optionally filtered by property."""
    query = select(Device)
    
    if property_id:
        query = query.where(Device.property_id == property_id)
    if status:
        query = query.where(Device.status == status)
    
    query = query.order_by(Device.name).limit(limit).offset(offset)
    
    result = await db.execute(query)
    devices = result.scalars().all()
    
    return devices


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single device."""
    result = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return device


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new device."""
    # Verify property exists
    result = await db.execute(
        select(Property).where(Property.id == device_data.property_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Property not found")
    
    device = Device(**device_data.model_dump())
    db.add(device)
    await db.flush()
    await db.refresh(device)
    
    return device


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    device_data: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a device."""
    result = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    update_data = device_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)
    
    await db.flush()
    await db.refresh(device)
    
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a device."""
    result = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.delete(device)


@router.post("/{device_id}/heartbeat", response_model=DeviceResponse)
async def device_heartbeat(
    device_id: UUID,
    heartbeat: DeviceHeartbeat,
    db: AsyncSession = Depends(get_db),
):
    """Update device status via heartbeat from edge device."""
    result = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Update device status
    device.status = heartbeat.status
    device.last_seen = datetime.now(timezone.utc)
    
    if heartbeat.firmware_version:
        device.firmware_version = heartbeat.firmware_version
    if heartbeat.local_ip:
        device.local_ip = heartbeat.local_ip
    if heartbeat.error:
        device.last_error = heartbeat.error
    elif heartbeat.status == "online":
        device.last_error = None  # Clear error on successful heartbeat
    
    await db.flush()
    await db.refresh(device)
    
    return device
