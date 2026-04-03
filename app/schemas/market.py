"""
RefurbAdmin AI - Market Data Schemas

Pydantic schemas for market data operations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# MARKET PRICE SCHEMAS
# =============================================================================

class MarketPriceCreate(BaseModel):
    """Schema for creating a market price record."""
    
    model: str = Field(..., min_length=1, max_length=100)
    ram_gb: int = Field(..., ge=1, le=128)
    ssd_gb: int = Field(..., ge=16, le=8000)
    price_zar: Decimal = Field(..., ge=0)
    source: str = Field(..., min_length=1, max_length=50)
    source_url: Optional[str] = None
    is_verified: bool = False


class MarketPriceResponse(BaseModel):
    """Schema for market price response."""
    
    id: str
    model: str
    ram_gb: int
    ssd_gb: int
    price_zar: Decimal
    source: str
    source_url: Optional[str]
    scraped_at: datetime
    is_verified: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class MarketPriceListResponse(BaseModel):
    """Schema for market price list response."""
    
    items: list[MarketPriceResponse]
    total: int
    median_price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None


# =============================================================================
# MARKET DATA AGGREGATION SCHEMAS
# =============================================================================

class MarketDataSummary(BaseModel):
    """Schema for market data summary."""
    
    model: str
    ram_gb: int
    ssd_gb: int
    median_price: Decimal
    min_price: Decimal
    max_price: Decimal
    sample_size: int
    sources: list[str]
    last_updated: datetime
    is_stale: bool
