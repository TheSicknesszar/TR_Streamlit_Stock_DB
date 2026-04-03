"""
RefurbAdmin AI - Price History Model

SQLAlchemy model for tracking price changes over time.
"""

import uuid
from datetime import datetime
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


class PriceHistory(Base):
    """
    Price history model.
    
    Tracks all price changes for devices to maintain
    an audit trail and support analytics.
    """
    
    __tablename__ = "price_history"
    
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
    changed_by = Column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Price information
    price_zar = Column(
        Numeric(10, 2),
        nullable=False,
    )
    reason = Column(
        String(50),
        nullable=True,
    )
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    
    # Relationships
    device = relationship("Device", back_populates="price_history")
    
    # Index for efficient lookups
    __table_args__ = (
        Index(
            "idx_price_history_device_date",
            "device_id",
            "created_at",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<PriceHistory(device_id={self.device_id}, price={self.price_zar})>"
    
    def to_dict(self) -> dict:
        """Convert price history to dictionary."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "price_zar": float(self.price_zar) if self.price_zar else None,
            "reason": self.reason,
            "changed_by": self.changed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
