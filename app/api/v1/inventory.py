"""
RefurbAdmin AI - Inventory API Endpoints

CRUD endpoints for device inventory management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.device import Device, DeviceStatus
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListResponse,
)
from app.api.deps import require_api_key
from app.models.api_key import APIKey

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new device",
)
async def create_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key),
) -> DeviceResponse:
    """Create a new device record in inventory."""
    
    # Check for duplicate serial number
    query = select(Device).where(Device.serial_number == device_data.serial_number)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device with this serial number already exists",
        )
    
    # Create device
    device = Device(**device_data.model_dump())
    db.add(device)
    await db.commit()
    await db.refresh(device)
    
    logger.info(f"Device created: {device.serial_number}")
    
    return DeviceResponse(
        **device.to_dict(),
        days_in_stock=device.days_in_stock,
    )


@router.get(
    "",
    response_model=DeviceListResponse,
    summary="List devices",
)
async def list_devices(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    make: Optional[str] = Query(None, description="Filter by make"),
    search: Optional[str] = Query(None, description="Search in model/serial"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key),
) -> DeviceListResponse:
    """List devices with pagination and filters."""
    
    # Build query
    query = select(Device)
    
    # Apply filters
    filters = []
    if status:
        filters.append(Device.status == status)
    if make:
        filters.append(Device.make.ilike(f"%{make}%"))
    if search:
        filters.append(
            or_(
                Device.model.ilike(f"%{search}%"),
                Device.serial_number.ilike(f"%{search}%"),
            )
        )
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    devices = result.scalars().all()
    
    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page
    
    return DeviceListResponse(
        items=[
            DeviceResponse(
                **device.to_dict(),
                days_in_stock=device.days_in_stock,
            )
            for device in devices
        ],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Get device details",
)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key),
) -> DeviceResponse:
    """Get device details by ID."""
    
    query = select(Device).where(Device.id == device_id)
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    return DeviceResponse(
        **device.to_dict(),
        days_in_stock=device.days_in_stock,
    )


@router.put(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Update device",
)
async def update_device(
    device_id: str,
    device_data: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key),
) -> DeviceResponse:
    """Update device record."""
    
    query = select(Device).where(Device.id == device_id)
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    # Update fields
    update_data = device_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)
    
    await db.commit()
    await db.refresh(device)
    
    logger.info(f"Device updated: {device.serial_number}")
    
    return DeviceResponse(
        **device.to_dict(),
        days_in_stock=device.days_in_stock,
    )


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete device",
)
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key),
):
    """Delete device record (soft delete)."""
    
    query = select(Device).where(Device.id == device_id)
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    # Soft delete by setting status
    device.status = "Deleted"
    await db.commit()
    
    logger.info(f"Device deleted: {device.serial_number}")
    
    return None
