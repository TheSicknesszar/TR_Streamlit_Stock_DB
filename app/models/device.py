"""
RefurbAdmin AI - Device Inventory Model

SQLAlchemy model for device inventory tracking.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    Date,
    Numeric,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, ENUM as PGEnum
from sqlalchemy.orm import relationship

from app.database import Base


# Define ENUM types for SQLite compatibility
class DeviceStatus:
    """Device status enumeration."""
    INTAKE = "Intake"
    DIAGNOSIS = "Diagnosis"
    WAITING_PARTS = "Waiting Parts"
    READY = "Ready"
    SOLD = "Sold"
    BER = "BER"  # Beyond Economic Repair
    STRIP_FOR_PARTS = "Strip for Parts"


class ConditionGrade:
    """Condition grade enumeration."""
    GRADE_A = "Grade A"
    GRADE_B = "Grade B"
    GRADE_C = "Grade C"
    BER = "BER"
    PARTS = "Parts"


class Device(Base):
    """
    Device inventory model.
    
    Represents a single device in the refurbishment inventory.
    Tracks specifications, status, and pricing information.
    """
    
    __tablename__ = "devices"
    
    # Primary key
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    
    # Device identification
    serial_number = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # Device specifications
    make = Column(
        String(50),
        nullable=False,
        index=True,
    )
    model = Column(
        String(100),
        nullable=False,
        index=True,
    )
    processor = Column(
        String(100),
        nullable=True,
    )
    ram_gb = Column(
        Integer,
        nullable=True,
    )
    ssd_gb = Column(
        Integer,
        nullable=True,
    )
    
    # Condition and status
    condition_grade = Column(
        String(20),
        nullable=True,
    )
    status = Column(
        String(30),
        nullable=False,
        default=DeviceStatus.INTAKE,
        index=True,
    )
    
    # Dates
    date_received = Column(
        Date,
        nullable=False,
        default=date.today,
        index=True,
    )
    
    # Pricing
    cost_price = Column(
        Numeric(10, 2),
        nullable=True,
    )
    sale_price = Column(
        Numeric(10, 2),
        nullable=True,
    )
    
    # Foreign keys
    customer_id = Column(
        String(36),
        ForeignKey("customers.id"),
        nullable=True,
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
    
    # Relationships
    customer = relationship("Customer", back_populates="devices")
    quotes = relationship("Quote", back_populates="device")
    price_history = relationship("PriceHistory", back_populates="device")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "condition_grade IN ('Grade A', 'Grade B', 'Grade C', 'BER', 'Parts')",
            name="ck_devices_condition_grade",
        ),
        CheckConstraint(
            "status IN ('Intake', 'Diagnosis', 'Waiting Parts', 'Ready', 'Sold', 'BER', 'Strip for Parts')",
            name="ck_devices_status",
        ),
        Index(
            "idx_devices_model_specs",
            "make",
            "model",
            "ram_gb",
            "ssd_gb",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Device(id={self.id}, serial={self.serial_number}, status={self.status})>"
    
    @property
    def days_in_stock(self) -> int:
        """Calculate days in stock from date_received."""
        if self.date_received:
            delta = date.today() - self.date_received
            return delta.days
        return 0
    
    @property
    def is_ready_for_sale(self) -> bool:
        """Check if device is ready for sale."""
        return self.status == DeviceStatus.READY
    
    @property
    def is_ber(self) -> bool:
        """Check if device is Beyond Economic Repair."""
        return self.status == DeviceStatus.BER
    
    @property
    def is_for_parts(self) -> bool:
        """Check if device is for parts only."""
        return self.status == DeviceStatus.STRIP_FOR_PARTS
    
    def to_dict(self) -> dict:
        """Convert device to dictionary."""
        return {
            "id": self.id,
            "serial_number": self.serial_number,
            "make": self.make,
            "model": self.model,
            "processor": self.processor,
            "ram_gb": self.ram_gb,
            "ssd_gb": self.ssd_gb,
            "condition_grade": self.condition_grade,
            "status": self.status,
            "date_received": self.date_received.isoformat() if self.date_received else None,
            "cost_price": float(self.cost_price) if self.cost_price else None,
            "sale_price": float(self.sale_price) if self.sale_price else None,
            "days_in_stock": self.days_in_stock,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
