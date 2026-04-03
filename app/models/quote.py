"""
RefurbAdmin AI - Quote Model

SQLAlchemy model for quote history tracking.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.config import settings


class Quote(Base):
    """
    Quote model.
    
    Tracks price quotes generated for devices, including
    pricing breakdown and validity period.
    """
    
    __tablename__ = "quotes"
    
    # Primary key
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # Foreign keys
    device_id = Column(
        String(36),
        ForeignKey("devices.id"),
        nullable=False,
        index=True,
    )
    quoted_by = Column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Pricing breakdown
    quoted_price = Column(
        Numeric(10, 2),
        nullable=False,
    )
    base_market_price = Column(
        Numeric(10, 2),
        nullable=True,
    )
    velocity_adjustment = Column(
        Numeric(5, 2),
        nullable=True,
    )
    margin_override = Column(
        Numeric(5, 2),
        nullable=True,
    )
    
    # Quote metadata
    valid_until = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(hours=settings.quote_validity_hours),
    )
    status = Column(
        String(20),
        default="pending",
        index=True,
    )
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    
    # Relationships
    device = relationship("Device", back_populates="quotes")
    
    # Index for efficient lookups
    __table_args__ = (
        Index(
            "idx_quotes_device_created",
            "device_id",
            "created_at",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Quote(id={self.id}, device_id={self.device_id}, price={self.quoted_price})>"
    
    @property
    def is_valid(self) -> bool:
        """Check if quote is still valid."""
        if self.valid_until:
            return datetime.utcnow() < self.valid_until
        return False
    
    @property
    def is_expired(self) -> bool:
        """Check if quote has expired."""
        return not self.is_valid
    
    @property
    def hours_remaining(self) -> float:
        """Calculate hours remaining until quote expires."""
        if self.valid_until:
            delta = self.valid_until - datetime.utcnow()
            return max(0, delta.total_seconds() / 3600)
        return 0
    
    def to_dict(self) -> dict:
        """Convert quote to dictionary."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "quoted_price": float(self.quoted_price) if self.quoted_price else None,
            "base_market_price": float(self.base_market_price) if self.base_market_price else None,
            "velocity_adjustment": float(self.velocity_adjustment) if self.velocity_adjustment else None,
            "margin_override": float(self.margin_override) if self.margin_override else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "status": self.status,
            "is_valid": self.is_valid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
