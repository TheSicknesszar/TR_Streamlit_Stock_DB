"""
RefurbAdmin AI - Validators

Input validation utilities for serial numbers, devices, and data integrity.
"""

import re
from typing import Optional, Tuple


# =============================================================================
# SERIAL NUMBER VALIDATION
# =============================================================================

def validate_serial_number(serial: str) -> Tuple[bool, Optional[str]]:
    """
    Validate serial number format.
    
    Args:
        serial: Serial number to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not serial:
        return False, "Serial number is required"
    
    serial = serial.strip()
    
    if len(serial) < 3:
        return False, "Serial number must be at least 3 characters"
    
    if len(serial) > 100:
        return False, "Serial number must be less than 100 characters"
    
    # Check for invalid characters (allow alphanumeric, dash, slash)
    if not re.match(r'^[a-zA-Z0-9\-\/]+$', serial):
        return False, "Serial number contains invalid characters"
    
    return True, None


def normalize_serial_number(serial: str) -> str:
    """
    Normalize serial number for consistent storage and lookup.
    
    Args:
        serial: Serial number to normalize
        
    Returns:
        str: Normalized serial number
    """
    if not serial:
        return ""
    
    # Strip whitespace
    serial = serial.strip()
    
    # Convert to uppercase for consistency
    serial = serial.upper()
    
    # Remove common prefixes that don't add value
    prefixes_to_remove = ["S/N:", "SN:", "SERIAL:", "SERIAL NO:"]
    for prefix in prefixes_to_remove:
        if serial.startswith(prefix):
            serial = serial[len(prefix):].strip()
    
    return serial


def is_invd_serial(serial: str) -> bool:
    """
    Check if serial number is an INVD placeholder.
    
    Args:
        serial: Serial number to check
        
    Returns:
        bool: True if INVD placeholder
    """
    if not serial:
        return True
    
    serial = serial.strip().upper()
    return serial in ["INVD", "N/A", "NA", "NONE", "UNKNOWN", ""]


# =============================================================================
# DEVICE SPECIFICATION VALIDATION
# =============================================================================

def validate_ram(ram_gb: Optional[int]) -> Tuple[bool, Optional[str]]:
    """
    Validate RAM value.
    
    Args:
        ram_gb: RAM in GB
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if ram_gb is None:
        return True, None  # Optional field
    
    if not isinstance(ram_gb, int):
        return False, "RAM must be a whole number"
    
    if ram_gb < 1:
        return False, "RAM must be at least 1GB"
    
    if ram_gb > 128:
        return False, "RAM must be 128GB or less"
    
    # Common RAM sizes
    common_sizes = [1, 2, 4, 8, 12, 16, 24, 32, 64, 128]
    if ram_gb not in common_sizes:
        # Allow any value but log warning
        pass
    
    return True, None


def validate_ssd(ssd_gb: Optional[int]) -> Tuple[bool, Optional[str]]:
    """
    Validate SSD storage value.
    
    Args:
        ssd_gb: SSD storage in GB
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if ssd_gb is None:
        return True, None  # Optional field
    
    if not isinstance(ssd_gb, int):
        return False, "SSD must be a whole number"
    
    if ssd_gb < 16:
        return False, "SSD must be at least 16GB"
    
    if ssd_gb > 8000:
        return False, "SSD must be 8TB or less"
    
    return True, None


def validate_price(price: Optional[float]) -> Tuple[bool, Optional[str]]:
    """
    Validate price value.
    
    Args:
        price: Price in ZAR
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if price is None:
        return True, None  # Optional field
    
    if not isinstance(price, (int, float)):
        return False, "Price must be a number"
    
    if price < 0:
        return False, "Price cannot be negative"
    
    if price > 1_000_000:
        return False, "Price seems too high (max R1,000,000)"
    
    return True, None


# =============================================================================
# DATE VALIDATION
# =============================================================================

def validate_date_received(date_received) -> Tuple[bool, Optional[str]]:
    """
    Validate date received.
    
    Args:
        date_received: Date received value
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    from datetime import date, datetime
    
    if date_received is None:
        return False, "Date received is required"
    
    if isinstance(date_received, date):
        # Check not in future
        if date_received > date.today():
            return False, "Date received cannot be in the future"
        
        # Check not too old (more than 10 years)
        ten_years_ago = date.today().replace(year=date.today().year - 10)
        if date_received < ten_years_ago:
            return False, "Date received seems too old (more than 10 years)"
        
        return True, None
    
    if isinstance(date_received, datetime):
        return validate_date_received(date_received.date())
    
    return False, "Invalid date format"


# =============================================================================
# STATUS VALIDATION
# =============================================================================

VALID_STATUSES = {
    "Intake",
    "Diagnosis",
    "Waiting Parts",
    "Ready",
    "Sold",
    "BER",
    "Strip for Parts",
}

VALID_CONDITIONS = {
    "Grade A",
    "Grade B",
    "Grade C",
    "BER",
    "Parts",
}


def validate_status(status: str) -> Tuple[bool, Optional[str]]:
    """
    Validate device status.
    
    Args:
        status: Status value
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not status:
        return False, "Status is required"
    
    if status not in VALID_STATUSES:
        return False, f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"
    
    return True, None


def validate_condition(condition: str) -> Tuple[bool, Optional[str]]:
    """
    Validate condition grade.
    
    Args:
        condition: Condition grade
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if condition is None:
        return True, None  # Optional field
    
    if condition not in VALID_CONDITIONS:
        return False, f"Invalid condition. Must be one of: {', '.join(VALID_CONDITIONS)}"
    
    return True, None
