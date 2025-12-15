"""Plates (Allow List) API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Plate, Property
from app.schemas import (
    PlateBulkCreate,
    PlateCreate,
    PlateResponse,
    PlateUpdate,
)

router = APIRouter(prefix="/plates", tags=["Plates"])


@router.get("", response_model=list[PlateResponse])
async def list_plates(
    property_id: Optional[UUID] = Query(None),
    list_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search plate number or description"),
    include_expired: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List plates with optional filters."""
    query = select(Plate)
    
    if property_id:
        query = query.where(Plate.property_id == property_id)
    if list_type:
        query = query.where(Plate.list_type == list_type)
    if search:
        search_term = f"%{search.upper()}%"
        query = query.where(
            (Plate.plate_number.ilike(search_term)) |
            (Plate.description.ilike(search_term))
        )
    if not include_expired:
        query = query.where(
            (Plate.expires_at.is_(None)) |
            (Plate.expires_at > func.now())
        )
    
    query = query.order_by(Plate.plate_number).limit(limit).offset(offset)
    
    result = await db.execute(query)
    plates = result.scalars().all()
    
    return plates


@router.get("/property/{property_id}", response_model=list[PlateResponse])
async def get_property_plates(
    property_id: UUID,
    list_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get all plates for a property (convenience endpoint)."""
    query = select(Plate).where(Plate.property_id == property_id)
    
    if list_type:
        query = query.where(Plate.list_type == list_type)
    
    # Only active plates
    query = query.where(
        (Plate.expires_at.is_(None)) |
        (Plate.expires_at > func.now())
    )
    
    query = query.order_by(Plate.plate_number)
    
    result = await db.execute(query)
    plates = result.scalars().all()
    
    return plates


@router.get("/{plate_id}", response_model=PlateResponse)
async def get_plate(
    plate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single plate."""
    result = await db.execute(
        select(Plate).where(Plate.id == plate_id)
    )
    plate = result.scalar_one_or_none()
    
    if not plate:
        raise HTTPException(status_code=404, detail="Plate not found")
    
    return plate


@router.post("", response_model=PlateResponse, status_code=201)
async def create_plate(
    plate_data: PlateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new plate entry."""
    # Verify property exists
    result = await db.execute(
        select(Property).where(Property.id == plate_data.property_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Normalize plate number
    plate_dict = plate_data.model_dump()
    plate_dict["plate_number"] = plate_dict["plate_number"].upper().replace(" ", "")
    
    plate = Plate(**plate_dict)
    db.add(plate)
    
    try:
        await db.flush()
        await db.refresh(plate)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Plate {plate_dict['plate_number']} already exists for this property"
        )
    
    return plate


@router.post("/bulk", response_model=list[PlateResponse], status_code=201)
async def create_plates_bulk(
    bulk_data: PlateBulkCreate,
    db: AsyncSession = Depends(get_db),
):
    """Bulk create plates."""
    created_plates = []
    errors = []
    
    for plate_data in bulk_data.plates:
        plate_dict = plate_data.model_dump()
        plate_dict["plate_number"] = plate_dict["plate_number"].upper().replace(" ", "")
        
        plate = Plate(**plate_dict)
        db.add(plate)
        
        try:
            await db.flush()
            await db.refresh(plate)
            created_plates.append(plate)
        except IntegrityError:
            await db.rollback()
            errors.append(plate_dict["plate_number"])
    
    if errors:
        # Still return what we created, but note the duplicates
        # In production, you might want to handle this differently
        pass
    
    return created_plates


@router.patch("/{plate_id}", response_model=PlateResponse)
async def update_plate(
    plate_id: UUID,
    plate_data: PlateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a plate."""
    result = await db.execute(
        select(Plate).where(Plate.id == plate_id)
    )
    plate = result.scalar_one_or_none()
    
    if not plate:
        raise HTTPException(status_code=404, detail="Plate not found")
    
    update_data = plate_data.model_dump(exclude_unset=True)
    
    # Normalize plate number if being updated
    if "plate_number" in update_data:
        update_data["plate_number"] = update_data["plate_number"].upper().replace(" ", "")
    
    for field, value in update_data.items():
        setattr(plate, field, value)
    
    try:
        await db.flush()
        await db.refresh(plate)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Plate {update_data.get('plate_number', plate.plate_number)} already exists for this property"
        )
    
    return plate


@router.delete("/{plate_id}", status_code=204)
async def delete_plate(
    plate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a plate."""
    result = await db.execute(
        select(Plate).where(Plate.id == plate_id)
    )
    plate = result.scalar_one_or_none()
    
    if not plate:
        raise HTTPException(status_code=404, detail="Plate not found")
    
    await db.delete(plate)


@router.get("/check/{property_id}/{plate_number}")
async def check_plate(
    property_id: UUID,
    plate_number: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a plate is allowed for a property.
    Used by edge devices for local validation.
    """
    normalized_plate = plate_number.upper().replace(" ", "")
    
    result = await db.execute(
        select(Plate)
        .where(Plate.property_id == property_id)
        .where(Plate.plate_number == normalized_plate)
        .where(
            (Plate.expires_at.is_(None)) |
            (Plate.expires_at > func.now())
        )
        .where(
            (Plate.starts_at.is_(None)) |
            (Plate.starts_at <= func.now())
        )
    )
    plate = result.scalar_one_or_none()
    
    if plate and plate.list_type == "allow":
        return {
            "allowed": True,
            "plate_id": str(plate.id),
            "description": plate.description,
            "list_type": plate.list_type,
        }
    elif plate and plate.list_type == "deny":
        return {
            "allowed": False,
            "plate_id": str(plate.id),
            "description": plate.description,
            "list_type": plate.list_type,
            "reason": "Plate is on deny list",
        }
    else:
        return {
            "allowed": False,
            "plate_id": None,
            "description": None,
            "list_type": None,
            "reason": "Plate not found in allow list",
        }
