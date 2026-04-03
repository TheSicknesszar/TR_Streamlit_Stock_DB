"""
RefurbAdmin AI - User Model

SQLAlchemy model for system users and authentication.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
)

from app.database import Base


class User(Base):
    """
    User model for system authentication and authorization.
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # User credentials
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash = Column(
        String(255),
        nullable=False,
    )
    
    # User profile
    name = Column(
        String(100),
        nullable=False,
    )
    role = Column(
        String(50),
        default="user",
    )
    
    # Account status
    is_active = Column(
        Boolean,
        default=True,
    )
    is_admin = Column(
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
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
    
    def to_dict(self) -> dict:
        """Convert user to dictionary (excluding password)."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
