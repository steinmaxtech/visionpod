"""Properties API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Property, Device, Plate, Event
from app.schemas import (
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
    PropertyWithStats,
)

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get("", response_model=list[PropertyResponse])
async def list_properties(
    organization_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all properties, optionally filtered by organization."""
    query = select(Property)
    
    if organization_id:
        query = query.where(Property.organization_id == organization_id)
    if status:
        query = query.where(Property.status == status)
    
    query = query.order_by(Property.name).limit(limit).offset(offset)
    
    result = await db.execute(query)
    properties = result.scalars().all()
    
    return properties


@router.get("/{property_id}", response_model=PropertyWithStats)
async def get_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single property with stats."""
    # Get property
    result = await db.execute(
        select(Property).where(Property.id == property_id)
    )
    property = result.scalar_one_or_none()
    
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get counts
    device_count = await db.scalar(
        select(func.count(Device.id)).where(Device.property_id == property_id)
    )
    plate_count = await db.scalar(
        select(func.count(Plate.id)).where(Plate.property_id == property_id)
    )
    # Events today (simplified - you'd want timezone handling in production)
    events_today = await db.scalar(
        select(func.count(Event.id))
        .where(Event.property_id == property_id)
        .where(func.date(Event.created_at) == func.current_date())
    )
    
    return PropertyWithStats(
        **PropertyResponse.model_validate(property).model_dump(),
        device_count=device_count or 0,
        plate_count=plate_count or 0,
        events_today=events_today or 0,
    )


@router.post("", response_model=PropertyResponse, status_code=201)
async def create_property(
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new property."""
    property = Property(**property_data.model_dump())
    db.add(property)
    await db.flush()
    await db.refresh(property)
    
    return property


@router.patch("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: UUID,
    property_data: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a property."""
    result = await db.execute(
        select(Property).where(Property.id == property_id)
    )
    property = result.scalar_one_or_none()
    
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    update_data = property_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(property, field, value)
    
    await db.flush()
    await db.refresh(property)
    
    return property


@router.delete("/{property_id}", status_code=204)
async def delete_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a property."""
    result = await db.execute(
        select(Property).where(Property.id == property_id)
    )
    property = result.scalar_one_or_none()
    
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    await db.delete(property)
