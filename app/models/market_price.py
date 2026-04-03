"""
RefurbAdmin AI - Market Price Model

SQLAlchemy model for caching market price data from scrapers.
Supports both individual price records and aggregated market data.
"""

import uuid
import json
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    DateTime,
    Boolean,
    Text,
    Index,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database import Base


class MarketPrice(Base):
    """
    Market price cache model.

    Stores aggregated price data from South African retailers
    (PriceCheck, Takealot, Gumtree, etc.) for pricing comparisons.
    
    Supports two modes:
    1. Individual price records (legacy) - one row per scraped price
    2. Aggregated market data (new) - one row per search query with stats
    """

    __tablename__ = "market_prices"

    # Primary key
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Search query for aggregated data
    search_query = Column(
        String(200),
        nullable=True,
        index=True,
    )

    # Device specifications for matching (legacy individual records)
    model = Column(
        String(100),
        nullable=True,
        index=True,
    )
    ram_gb = Column(
        Integer,
        nullable=True,
    )
    ssd_gb = Column(
        Integer,
        nullable=True,
    )

    # Aggregated price statistics (new)
    median_price = Column(
        Numeric(10, 2),
        nullable=True,
    )
    min_price = Column(
        Numeric(10, 2),
        nullable=True,
    )
    max_price = Column(
        Numeric(10, 2),
        nullable=True,
    )
    average_price = Column(
        Numeric(10, 2),
        nullable=True,
    )
    total_listings = Column(
        Integer,
        default=0,
    )

    # Legacy single price field
    price_zar = Column(
        Numeric(10, 2),
        nullable=True,
    )

    # JSON fields for complex data
    _price_by_source = Column(
        Text,
        nullable=True,
    )
    _listings_by_condition = Column(
        Text,
        nullable=True,
    )
    _sources_scraped = Column(
        Text,
        nullable=True,
    )
    _sources_failed = Column(
        Text,
        nullable=True,
    )

    # Source information (legacy individual records)
    source = Column(
        String(50),
        nullable=True,
        index=True,
    )
    source_url = Column(
        Text,
        nullable=True,
    )

    # Scraping metadata
    scraped_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    is_verified = Column(
        Boolean,
        default=False,
    )

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Index for efficient lookups
    __table_args__ = (
        Index(
            "idx_market_prices_specs",
            "model",
            "ram_gb",
            "ssd_gb",
        ),
        Index(
            "idx_market_prices_search_query",
            "search_query",
        ),
    )

    def __repr__(self) -> str:
        if self.search_query:
            return f"<MarketPrice(query={self.search_query}, median={self.median_price})>"
        return f"<MarketPrice(model={self.model}, price={self.price_zar}, source={self.source})>"

    # Property getters/setters for JSON fields
    @property
    def price_by_source(self) -> Dict[str, List[float]]:
        """Get price by source dictionary."""
        if self._price_by_source:
            return json.loads(self._price_by_source)
        return {}

    @price_by_source.setter
    def price_by_source(self, value: Dict[str, List[float]]) -> None:
        """Set price by source dictionary."""
        self._price_by_source = json.dumps(value)

    @property
    def listings_by_condition(self) -> Dict[str, int]:
        """Get listings by condition dictionary."""
        if self._listings_by_condition:
            return json.loads(self._listings_by_condition)
        return {}

    @listings_by_condition.setter
    def listings_by_condition(self, value: Dict[str, int]) -> None:
        """Set listings by condition dictionary."""
        self._listings_by_condition = json.dumps(value)

    @property
    def sources_scraped(self) -> List[str]:
        """Get list of successfully scraped sources."""
        if self._sources_scraped:
            return json.loads(self._sources_scraped)
        return []

    @sources_scraped.setter
    def sources_scraped(self, value: List[str]) -> None:
        """Set list of successfully scraped sources."""
        self._sources_scraped = json.dumps(value)

    @property
    def sources_failed(self) -> List[str]:
        """Get list of failed sources."""
        if self._sources_failed:
            return json.loads(self._sources_failed)
        return []

    @sources_failed.setter
    def sources_failed(self, value: List[str]) -> None:
        """Set list of failed sources."""
        self._sources_failed = json.dumps(value)

    @property
    def is_stale(self) -> bool:
        """
        Check if market price data is stale.

        Returns:
            bool: True if data is older than 24 hours
        """
        if self.scraped_at:
            delta = datetime.utcnow() - self.scraped_at
            return delta.total_seconds() > 24 * 60 * 60  # 24 hours
        return True

    @property
    def cache_age_hours(self) -> float:
        """Get cache age in hours."""
        if self.scraped_at:
            delta = datetime.utcnow() - self.scraped_at
            return delta.total_seconds() / 3600
        return 999

    def to_dict(self) -> Dict[str, Any]:
        """Convert market price to dictionary."""
        return {
            "id": self.id,
            "search_query": self.search_query,
            "model": self.model,
            "ram_gb": self.ram_gb,
            "ssd_gb": self.ssd_gb,
            "median_price": float(self.median_price) if self.median_price else None,
            "min_price": float(self.min_price) if self.min_price else None,
            "max_price": float(self.max_price) if self.max_price else None,
            "average_price": float(self.average_price) if self.average_price else None,
            "total_listings": self.total_listings,
            "price_zar": float(self.price_zar) if self.price_zar else None,
            "price_by_source": self.price_by_source,
            "listings_by_condition": self.listings_by_condition,
            "source": self.source,
            "source_url": self.source_url,
            "sources_scraped": self.sources_scraped,
            "sources_failed": self.sources_failed,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "is_verified": self.is_verified,
            "cache_age_hours": round(self.cache_age_hours, 2),
        }

    @classmethod
    def from_market_data(cls, search_query: str, market_data: Any) -> "MarketPrice":
        """
        Create MarketPrice from MarketPriceData.

        Args:
            search_query: Search query
            market_data: MarketPriceData object

        Returns:
            MarketPrice instance
        """
        record = cls(
            search_query=search_query,
            median_price=market_data.median_price,
            min_price=market_data.min_price,
            max_price=market_data.max_price,
            average_price=market_data.average_price,
            total_listings=market_data.total_listings,
            scraped_at=market_data.scraped_at,
        )
        record.price_by_source = market_data.price_by_source
        record.listings_by_condition = market_data.listings_by_condition
        record.sources_scraped = market_data.sources_scraped
        record.sources_failed = market_data.sources_failed
        return record
