"""
RefurbAdmin AI - Device Schemas

Pydantic schemas for device inventory operations.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


# =============================================================================
# ENUM SCHEMAS
# =============================================================================

class DeviceStatusEnum(str, Enum):
    """Device status enumeration."""
    INTAKE = "Intake"
    DIAGNOSIS = "Diagnosis"
    WAITING_PARTS = "Waiting Parts"
    READY = "Ready"
    SOLD = "Sold"
    BER = "BER"
    STRIP_FOR_PARTS = "Strip for Parts"


class ConditionGradeEnum(str, Enum):
    """Condition grade enumeration."""
    GRADE_A = "Grade A"
    GRADE_B = "Grade B"
    GRADE_C = "Grade C"
    BER = "BER"
    PARTS = "Parts"


# =============================================================================
# CREATE/UPDATE SCHEMAS
# =============================================================================

class DeviceCreate(BaseModel):
    """Schema for creating a new device."""
    
    serial_number: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique serial number",
    )
    make: str = Field(..., min_length=1, max_length=50, description="Device make/brand")
    model: str = Field(..., min_length=1, max_length=100, description="Device model")
    processor: Optional[str] = Field(None, max_length=100, description="Processor/CPU")
    ram_gb: Optional[int] = Field(None, ge=1, le=128, description="RAM in GB")
    ssd_gb: Optional[int] = Field(None, ge=16, le=8000, description="SSD storage in GB")
    condition_grade: Optional[ConditionGradeEnum] = Field(None, description="Condition grade")
    status: DeviceStatusEnum = Field(default=DeviceStatusEnum.INTAKE, description="Device status")
    date_received: date = Field(default_factory=date.today, description="Date received")
    cost_price: Optional[Decimal] = Field(None, ge=0, description="Cost price in ZAR")
    
    @field_validator("serial_number")
    @classmethod
    def validate_serial(cls, v: str) -> str:
        return v.strip()
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "serial_number": "1LW10Y2",
                "make": "Dell",
                "model": "Inspiron 3580",
                "processor": "i5-8265U",
                "ram_gb": 8,
                "ssd_gb": 256,
                "condition_grade": "Grade A",
                "status": "Intake",
                "date_received": "2026-04-01",
                "cost_price": 4500.00,
            }
        }
    )


class DeviceUpdate(BaseModel):
    """Schema for updating a device (partial update)."""
    
    make: Optional[str] = Field(None, min_length=1, max_length=50)
    model: Optional[str] = Field(None, min_length=1, max_length=100)
    processor: Optional[str] = Field(None, max_length=100)
    ram_gb: Optional[int] = Field(None, ge=1, le=128)
    ssd_gb: Optional[int] = Field(None, ge=16, le=8000)
    condition_grade: Optional[ConditionGradeEnum] = Field(None)
    status: Optional[DeviceStatusEnum] = Field(None)
    date_received: Optional[date] = Field(None)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    sale_price: Optional[Decimal] = Field(None, ge=0)
    
    model_config = ConfigDict(json_schema_extra={"example": {"status": "Ready"}})


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class DeviceResponse(BaseModel):
    """Schema for device response."""
    
    id: str
    serial_number: str
    make: str
    model: str
    processor: Optional[str]
    ram_gb: Optional[int]
    ssd_gb: Optional[int]
    condition_grade: Optional[str]
    status: str
    date_received: date
    cost_price: Optional[Decimal]
    sale_price: Optional[Decimal]
    days_in_stock: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DeviceListResponse(BaseModel):
    """Schema for paginated device list response."""
    
    items: list[DeviceResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    
    model_config = ConfigDict(from_attributes=True)
