"""Sync endpoints for edge devices."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Device, Plate
from app.schemas import DeviceConfig, PlateListSync, PlateResponse

router = APIRouter(prefix="/sync", tags=["Sync"])


@router.get("/devices/{device_id}/plates", response_model=PlateListSync)
async def get_device_plates(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all active plates for a device's property.
    Used by edge devices to sync their local allow list.
    """
    # Get device and verify it exists
    result = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get all active plates for the property
    result = await db.execute(
        select(Plate)
        .where(Plate.property_id == device.property_id)
        .where(
            (Plate.expires_at.is_(None)) |
            (Plate.expires_at > func.now())
        )
        .where(
            (Plate.starts_at.is_(None)) |
            (Plate.starts_at <= func.now())
        )
        .order_by(Plate.plate_number)
    )
    plates = result.scalars().all()
    
    return PlateListSync(
        plates=[PlateResponse.model_validate(p) for p in plates],
        sync_timestamp=datetime.now(timezone.utc),
        property_id=device.property_id,
    )


@router.get("/devices/{device_id}/config", response_model=DeviceConfig)
async def get_device_config(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get configuration for an edge device.
    Includes API keys and integration settings.
    """
    result = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return DeviceConfig(
        device_id=device.id,
        property_id=device.property_id,
        gatewise_device_id=device.gatewise_device_id,
        gatewise_api_key=device.gatewise_api_key,
        plate_recognizer_token=device.plate_recognizer_token,
        camera_rtsp_url=device.camera_rtsp_url,
        config=device.config or {},
    )


@router.get("/plates/hash/{property_id}")
async def get_plates_hash(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a hash of the current plate list for a property.
    Edge devices can use this to check if their local cache is stale.
    """
    # Get count and latest update time
    result = await db.execute(
        select(
            func.count(Plate.id).label("count"),
            func.max(Plate.updated_at).label("latest_update"),
        )
        .where(Plate.property_id == property_id)
        .where(
            (Plate.expires_at.is_(None)) |
            (Plate.expires_at > func.now())
        )
    )
    row = result.one()
    
    # Simple hash based on count and latest update
    # In production, you might want a more robust hash
    hash_input = f"{row.count}-{row.latest_update or 'none'}"
    import hashlib
    list_hash = hashlib.md5(hash_input.encode()).hexdigest()[:16]
    
    return {
        "property_id": str(property_id),
        "hash": list_hash,
        "count": row.count,
        "latest_update": row.latest_update,
    }
