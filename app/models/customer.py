"""
RefurbAdmin AI - Customer Model

SQLAlchemy model for customer data with POPIA-compliant encryption.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    LargeBinary,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Customer(Base):
    """
    Customer model with POPIA-compliant PII encryption.
    
    All personally identifiable information (PII) is stored
    encrypted using Fernet symmetric encryption.
    """
    
    __tablename__ = "customers"
    
    # Primary key
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # Encrypted PII fields (stored as bytes)
    email_encrypted = Column(
        LargeBinary,
        nullable=False,
    )
    phone_encrypted = Column(
        LargeBinary,
        nullable=True,
    )
    name_encrypted = Column(
        LargeBinary,
        nullable=True,
    )
    
    # POPIA consent tracking
    consent_given = Column(
        Boolean,
        default=False,
    )
    consent_date = Column(
        DateTime,
        nullable=True,
    )
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    
    # Relationships
    devices = relationship("Device", back_populates="customer")
    
    def __repr__(self) -> str:
        return f"<Customer(id={self.id})>"
    
    def to_dict(self) -> dict:
        """Convert customer to dictionary (PII not included)."""
        return {
            "id": self.id,
            "consent_given": self.consent_given,
            "consent_date": self.consent_date.isoformat() if self.consent_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
