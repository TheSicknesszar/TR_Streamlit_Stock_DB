"""
RefurbAdmin AI - Pricing Schemas

Pydantic schemas for pricing request/response validation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class PriceCheckRequest(BaseModel):
    """
    Request schema for /api/v1/price-check endpoint.
    """
    
    serial_number: str = Field(
        ...,
        description="Device serial number to look up",
        min_length=1,
        max_length=100,
        examples=["1LW10Y2"],
    )
    include_warranty: bool = Field(
        default=True,
        description="Include warranty information in response",
    )
    margin_override: Optional[Decimal] = Field(
        default=None,
        description="Override margin percentage (requires manager approval)",
        ge=0,
        le=100,
    )
    
    @field_validator("serial_number")
    @classmethod
    def validate_serial_number(cls, v: str) -> str:
        """Validate serial number format."""
        if not v or not v.strip():
            raise ValueError("Serial number cannot be empty")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "serial_number": "1LW10Y2",
                "include_warranty": True,
                "margin_override": None,
            }
        }


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class DeviceSpecs(BaseModel):
    """Device specifications schema."""
    
    cpu: Optional[str] = Field(None, description="Processor/CPU")
    ram: Optional[str] = Field(None, description="Memory (RAM)")
    ssd: Optional[str] = Field(None, description="Storage (SSD)")
    condition: Optional[str] = Field(None, description="Condition grade")


class DeviceInfo(BaseModel):
    """Device information schema for price check response."""
    
    serial: str = Field(..., description="Serial number")
    model: str = Field(..., description="Full model name")
    specs: DeviceSpecs = Field(..., description="Device specifications")
    inventory_status: str = Field(..., description="Current inventory status")
    days_in_stock: int = Field(..., description="Days in inventory")


class PricingInfo(BaseModel):
    """Pricing information schema."""
    
    base_market_price_zar: Decimal = Field(
        ...,
        description="Base market price in ZAR",
    )
    velocity_adjustment: Decimal = Field(
        ...,
        description="Velocity adjustment amount in ZAR",
    )
    velocity_adjustment_percent: str = Field(
        ...,
        description="Velocity adjustment percentage",
    )
    final_price_zar: Decimal = Field(
        ...,
        description="Final price in ZAR after adjustments",
    )
    currency: str = Field(
        default="ZAR",
        description="Currency code",
    )
    warranty_months: int = Field(
        default=3,
        description="Warranty period in months",
    )
    margin_percent: Optional[Decimal] = Field(
        None,
        description="Profit margin percentage",
    )


class PriceCheckResponse(BaseModel):
    """
    Response schema for /api/v1/price-check endpoint.
    """
    
    status: str = Field(
        ...,
        description="Response status: success or error",
    )
    device: Optional[DeviceInfo] = Field(
        None,
        description="Device information",
    )
    pricing: Optional[PricingInfo] = Field(
        None,
        description="Pricing breakdown",
    )
    client_snippet: Optional[str] = Field(
        None,
        description="Client-ready text snippet for copy-pasting",
    )
    quote_valid_until: Optional[datetime] = Field(
        None,
        description="Quote validity expiry datetime",
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "device": {
                    "serial": "1LW10Y2",
                    "model": "Dell Inspiron 3580",
                    "specs": {
                        "cpu": "i5-8265U",
                        "ram": "8GB",
                        "ssd": "256GB",
                        "condition": "Grade A Refurbished",
                    },
                    "inventory_status": "ready",
                    "days_in_stock": 14,
                },
                "pricing": {
                    "base_market_price_zar": 6500.00,
                    "velocity_adjustment": 0.00,
                    "velocity_adjustment_percent": "0%",
                    "final_price_zar": 6500.00,
                    "currency": "ZAR",
                    "warranty_months": 3,
                    "margin_percent": 30.0,
                },
                "client_snippet": "We have the Dell Inspiron 3580 (Serial: 1LW10Y2) available for R6,500. Includes 3-month warranty and full quality inspection.",
                "quote_valid_until": "2026-04-03T23:59:59Z",
            }
        }


# =============================================================================
# ERROR RESPONSE SCHEMAS
# =============================================================================

class PriceCheckError(BaseModel):
    """Error response schema for price check endpoint."""
    
    status: str = Field(default="error")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    suggested_action: Optional[str] = Field(None, description="Suggested action")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "code": "DEVICE_NOT_READY",
                "message": "Serial number found but status is 'BER' (Beyond Economic Repair).",
                "suggested_action": "Offer parts valuation or trade-in.",
            }
        }


class DeviceNotFoundError(PriceCheckError):
    """Device not found error."""
    
    code: str = "DEVICE_NOT_FOUND"
    message: str = "No device found with the provided serial number."
    suggested_action: str = "Verify the serial number and try again."


class DeviceNotReadyError(PriceCheckError):
    """Device not ready for sale error."""
    
    code: str = "DEVICE_NOT_READY"
    suggested_action: str = "Check device status in inventory system."


class BERDeviceError(PriceCheckError):
    """Beyond Economic Repair error."""
    
    code: str = "DEVICE_BER"
    message: str = "Device is marked as Beyond Economic Repair (BER)."
    suggested_action: str = "Offer parts valuation or trade-in."


class PartsOnlyError(PriceCheckError):
    """Parts only device error."""
    
    code: str = "DEVICE_PARTS_ONLY"
    message: str = "Device is marked for parts only."
    suggested_action: str = "Device is not available for sale as a complete unit."
