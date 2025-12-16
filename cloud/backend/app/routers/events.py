"""Events API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Event, Device, Plate
from app.schemas import (
    EventCreate,
    EventResponse,
    EventWithDetails,
)

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=list[EventWithDetails])
async def list_events(
    property_id: Optional[UUID] = Query(None),
    device_id: Optional[UUID] = Query(None),
    plate_number: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List events with filters."""
    query = (
        select(Event)
        .options(
            selectinload(Event.device),
            selectinload(Event.matched_plate),
        )
    )
    
    if property_id:
        query = query.where(Event.property_id == property_id)
    if device_id:
        query = query.where(Event.device_id == device_id)
    if plate_number:
        query = query.where(Event.plate_number.ilike(f"%{plate_number.upper()}%"))
    if decision:
        query = query.where(Event.decision == decision)
    if start_date:
        query = query.where(Event.created_at >= start_date)
    if end_date:
        query = query.where(Event.created_at <= end_date)
    
    query = query.order_by(Event.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    # Enrich with device and plate names
    enriched_events = []
    for event in events:
        event_dict = EventResponse.model_validate(event).model_dump()
        event_dict["device_name"] = event.device.name if event.device else None
        event_dict["matched_plate_description"] = (
            event.matched_plate.description if event.matched_plate else None
        )
        enriched_events.append(EventWithDetails(**event_dict))
    
    return enriched_events


@router.get("/stats")
async def get_event_stats(
    property_id: Optional[UUID] = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Get event statistics for dashboard."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Base query
    base = select(Event).where(Event.created_at >= cutoff)
    if property_id:
        base = base.where(Event.property_id == property_id)
    
    # Total events
    total = await db.scalar(
        select(func.count(Event.id)).where(Event.created_at >= cutoff)
    )
    
    # By decision
    granted = await db.scalar(
        select(func.count(Event.id))
        .where(Event.created_at >= cutoff)
        .where(Event.decision == "granted")
    )
    denied = await db.scalar(
        select(func.count(Event.id))
        .where(Event.created_at >= cutoff)
        .where(Event.decision == "denied")
    )
    
    # Events per day
    daily_query = (
        select(
            func.date(Event.created_at).label("date"),
            func.count(Event.id).label("count"),
        )
        .where(Event.created_at >= cutoff)
        .group_by(func.date(Event.created_at))
        .order_by(func.date(Event.created_at))
    )
    if property_id:
        daily_query = daily_query.where(Event.property_id == property_id)
    
    daily_result = await db.execute(daily_query)
    daily_counts = [
        {"date": str(row.date), "count": row.count}
        for row in daily_result.all()
    ]
    
    return {
        "total": total or 0,
        "granted": granted or 0,
        "denied": denied or 0,
        "days": days,
        "daily": daily_counts,
    }


@router.get("/{event_id}", response_model=EventWithDetails)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single event with details."""
    result = await db.execute(
        select(Event)
        .options(
            selectinload(Event.device),
            selectinload(Event.matched_plate),
        )
        .where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event_dict = EventResponse.model_validate(event).model_dump()
    event_dict["device_name"] = event.device.name if event.device else None
    event_dict["matched_plate_description"] = (
        event.matched_plate.description if event.matched_plate else None
    )
    
    return EventWithDetails(**event_dict)


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new event.
    Typically called by edge devices after plate detection.
    """
    event = Event(**event_data.model_dump())
    db.add(event)
    await db.flush()
    await db.refresh(event)
    
    return event


@router.get("/property/{property_id}/recent", response_model=list[EventWithDetails])
async def get_recent_events(
    property_id: UUID,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get recent events for a property (for dashboard)."""
    result = await db.execute(
        select(Event)
        .options(
            selectinload(Event.device),
            selectinload(Event.matched_plate),
        )
        .where(Event.property_id == property_id)
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    
    enriched_events = []
    for event in events:
        event_dict = EventResponse.model_validate(event).model_dump()
        event_dict["device_name"] = event.device.name if event.device else None
        event_dict["matched_plate_description"] = (
            event.matched_plate.description if event.matched_plate else None
        )
        enriched_events.append(EventWithDetails(**event_dict))
    
    return enriched_events
