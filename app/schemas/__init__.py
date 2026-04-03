"""
RefurbAdmin AI - Pydantic Schemas

Export all Pydantic schemas for easy importing.
"""

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

from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListResponse,
    DeviceStatusEnum,
    ConditionGradeEnum,
)

from app.schemas.market import (
    MarketPriceCreate,
    MarketPriceResponse,
    MarketPriceListResponse,
    MarketDataSummary,
)

from app.schemas.common import (
    APIResponse,
    PaginatedResponse,
    ErrorResponse,
    ValidationErrorResponse,
    HealthCheckResponse,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreateResponse,
)

__all__ = [
    # Pricing
    "PriceCheckRequest",
    "PriceCheckResponse",
    "PriceCheckError",
    "DeviceInfo",
    "DeviceSpecs",
    "PricingInfo",
    "DeviceNotFoundError",
    "DeviceNotReadyError",
    "BERDeviceError",
    "PartsOnlyError",
    # Device
    "DeviceCreate",
    "DeviceUpdate",
    "DeviceResponse",
    "DeviceListResponse",
    "DeviceStatusEnum",
    "ConditionGradeEnum",
    # Market
    "MarketPriceCreate",
    "MarketPriceResponse",
    "MarketPriceListResponse",
    "MarketDataSummary",
    # Common
    "APIResponse",
    "PaginatedResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    "HealthCheckResponse",
    "APIKeyCreate",
    "APIKeyResponse",
    "APIKeyCreateResponse",
]
