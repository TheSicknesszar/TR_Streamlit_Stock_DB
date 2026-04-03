"""
RefurbAdmin AI - Common Schemas

Shared Pydantic schemas for API responses.
"""

from datetime import datetime
from typing import Optional, Generic, TypeVar

from pydantic import BaseModel, Field


# =============================================================================
# GENERIC RESPONSE WRAPPER
# =============================================================================

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Generic API response wrapper."""
    
    success: bool = Field(default=True, description="Request success status")
    data: Optional[T] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    
    items: list[T]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


# =============================================================================
# ERROR SCHEMAS
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response schema."""
    
    status: str = Field(default="error")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""
    
    loc: list[str] = Field(..., description="Location of the error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    
    status: str = Field(default="error")
    code: str = Field(default="VALIDATION_ERROR")
    message: str = Field(default="Request validation failed")
    errors: list[ValidationErrorDetail] = Field(..., description="Validation errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# HEALTH CHECK SCHEMAS
# =============================================================================

class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: str = Field(default="unknown", description="Database status")


# =============================================================================
# AUTHENTICATION SCHEMAS
# =============================================================================

class APIKeyCreate(BaseModel):
    """Schema for creating a new API key."""
    
    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    expires_in_days: int = Field(default=90, ge=1, le=365, description="Expiry in days")


class APIKeyResponse(BaseModel):
    """Schema for API key response (without the actual key)."""
    
    id: str
    name: str
    expires_at: datetime
    is_active: bool
    created_at: datetime
    days_until_expiry: int


class APIKeyCreateResponse(BaseModel):
    """Schema for API key creation response (includes the key once)."""
    
    id: str
    name: str
    key: str  # Only returned once on creation
    expires_at: datetime
    is_active: bool
    created_at: datetime
