"""
RefurbAdmin AI - API Key Model

SQLAlchemy model for API key authentication.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Index,
)

from app.database import Base
from app.config import settings


class APIKey(Base):
    """
    API Key model.
    
    Stores API keys for authentication with automatic expiry
    and usage tracking.
    """
    
    __tablename__ = "api_keys"
    
    # Primary key
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # Key hash (store hashed keys, not plain text)
    key_hash = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # Key metadata
    name = Column(
        String(100),
        nullable=False,
    )
    
    # Foreign keys
    created_by = Column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Expiry and status
    expires_at = Column(
        DateTime,
        nullable=False,
    )
    is_active = Column(
        Boolean,
        default=True,
        index=True,
    )
    
    # Usage tracking
    last_used_at = Column(
        DateTime,
        nullable=True,
    )
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    
    # Index for efficient lookups
    __table_args__ = (
        Index(
            "idx_api_keys_active_expiry",
            "is_active",
            "expires_at",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, active={self.is_active})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if API key has expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return True
    
    @property
    def is_valid(self) -> bool:
        """Check if API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired
    
    @property
    def days_until_expiry(self) -> int:
        """Calculate days until key expires."""
        if self.expires_at:
            delta = self.expires_at - datetime.utcnow()
            return max(0, delta.days)
        return 0
    
    def to_dict(self) -> dict:
        """Convert API key to dictionary (excluding sensitive data)."""
        return {
            "id": self.id,
            "name": self.name,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_expired": self.is_expired,
            "days_until_expiry": self.days_until_expiry,
        }
    
    @classmethod
    def generate_expiry(cls, days: int = None) -> datetime:
        """
        Generate expiry datetime.
        
        Args:
            days: Number of days until expiry (default from settings)
            
        Returns:
            datetime: Expiry datetime
        """
        if days is None:
            days = settings.api_key_expiry_days
        return datetime.utcnow() + timedelta(days=days)
