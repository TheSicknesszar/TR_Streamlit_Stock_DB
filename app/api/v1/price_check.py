"""
RefurbAdmin AI - Price Check API Endpoint

Core endpoint for dynamic pricing via serial number lookup.
Implements /api/v1/price-check as specified in the PRD.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.device import Device, DeviceStatus
from app.schemas.pricing import (
    PriceCheckRequest,
    PriceCheckResponse,
    PriceCheckError,
    DeviceInfo,
    DeviceSpecs,
    PricingInfo,
    DeviceNotFoundError,
    DeviceNotReadyError,
    BERDeviceError,
    PartsOnlyError,
)
from app.services.pricing_service import PricingService
from app.api.deps import require_api_key
from app.models.api_key import APIKey
from app.config import settings

logger = logging.getLogger(__name__)

# Router for price check endpoints
router = APIRouter(prefix="/price-check", tags=["Pricing"])


@router.post(
    "",
    response_model=PriceCheckResponse,
    responses={
        200: {"model": PriceCheckResponse, "description": "Successful price check"},
        400: {"model": PriceCheckError, "description": "Device not ready for sale"},
        404: {"model": PriceCheckError, "description": "Device not found"},
        401: {"description": "Unauthorized - Invalid API key"},
    },
    summary="Get dynamic pricing for a device",
    description="""
    Get dynamic pricing for a device by serial number.
    
    This is the core feature of RefurbAdmin AI. It:
    1. Validates the serial number against inventory
    2. Checks device status (must be 'Ready' for sale)
    3. Calculates dynamic price based on:
       - Market data from SA retailers
       - Inventory velocity (days in stock, stock count)
       - Retail psychology price rounding
    4. Returns a client-ready quote snippet
    
    **Pricing Logic:**
    - **Slow-moving** (>30 days, >5 units): -10% discount
    - **High-demand** (<3 units): +5% premium
    - **Normal**: No adjustment
    
    **South African Context:**
    - Prices in ZAR (R)
    - SAST timezone for quote validity
    - POPIA-compliant data handling
    """,
)
async def price_check(
    request: PriceCheckRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key),
) -> PriceCheckResponse:
    """
    Get dynamic pricing for a device by serial number.
    
    Args:
        request: Price check request with serial number
        db: Database session
        api_key: Validated API key
        
    Returns:
        PriceCheckResponse: Pricing breakdown and client snippet
        
    Raises:
        HTTPException: If device not found or not ready
    """
    logger.info(f"Price check requested for serial: {request.serial_number}")
    
    # Normalize serial number
    serial = request.serial_number.strip().upper()
    
    # Look up device
    query = select(Device).where(Device.serial_number == serial)
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    
    # Handle device not found
    if not device:
        logger.warning(f"Device not found: {serial}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=DeviceNotFoundError().model_dump(),
        )
    
    # Check device status
    if device.status == DeviceStatus.BER:
        logger.info(f"Device is BER: {serial}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BERDeviceError().model_dump(),
        )
    
    if device.status == DeviceStatus.STRIP_FOR_PARTS:
        logger.info(f"Device is for parts: {serial}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=PartsOnlyError().model_dump(),
        )
    
    if device.status != DeviceStatus.READY:
        logger.info(f"Device not ready: {serial} (status: {device.status})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=DeviceNotReadyError(
                message=f"Device status is '{device.status}', not 'Ready'."
            ).model_dump(),
        )
    
    # Calculate dynamic pricing
    pricing_service = PricingService(db)
    pricing_data = await pricing_service.calculate_price(
        device,
        margin_override=request.margin_override,
    )
    
    # Generate client snippet
    client_snippet = pricing_service.generate_client_snippet(
        device,
        Decimal(str(pricing_data["final_price_zar"])),
        include_warranty=request.include_warranty,
    )
    
    # Calculate quote validity
    quote_valid_until = datetime.utcnow() + timedelta(
        hours=settings.quote_validity_hours
    )
    
    # Build response
    response = PriceCheckResponse(
        status="success",
        device=DeviceInfo(
            serial=device.serial_number,
            model=f"{device.make} {device.model}",
            specs=DeviceSpecs(
                cpu=device.processor,
                ram=f"{device.ram_gb}GB" if device.ram_gb else None,
                ssd=f"{device.ssd_gb}GB" if device.ssd_gb else None,
                condition=f"{device.condition_grade} Refurbished" if device.condition_grade else None,
            ),
            inventory_status=device.status.lower(),
            days_in_stock=device.days_in_stock,
        ),
        pricing=PricingInfo(
            base_market_price_zar=pricing_data["base_market_price_zar"],
            velocity_adjustment=pricing_data["velocity_adjustment"],
            velocity_adjustment_percent=pricing_data["velocity_adjustment_percent"],
            final_price_zar=pricing_data["final_price_zar"],
            currency=pricing_data["currency"],
            warranty_months=pricing_data["warranty_months"],
            margin_percent=pricing_data["margin_percent"],
        ),
        client_snippet=client_snippet,
        quote_valid_until=quote_valid_until,
    )
    
    logger.info(
        f"Price check successful: {serial} -> R{pricing_data['final_price_zar']}"
    )
    
    return response


@router.get(
    "/{serial_number}",
    response_model=PriceCheckResponse,
    summary="Get pricing by serial (GET variant)",
    description="GET variant of price check for quick lookups.",
)
async def price_check_get(
    serial_number: str,
    include_warranty: bool = True,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key),
) -> PriceCheckResponse:
    """
    GET variant of price check endpoint.
    
    Useful for quick lookups via URL or browser.
    """
    request = PriceCheckRequest(
        serial_number=serial_number,
        include_warranty=include_warranty,
    )
    return await price_check(request, db, api_key)
