"""
RefurbAdmin AI - Formatters

Utility functions for formatting currency, dates, and other values.
South African context (ZAR currency, SAST timezone).
"""

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

import pytz

from app.config import settings


# =============================================================================
# CURRENCY FORMATTING
# =============================================================================

def format_currency(
    amount: Union[int, float, Decimal],
    currency: str = None,
    symbol: str = None,
    include_cents: bool = False,
) -> str:
    """
    Format amount as South African currency (ZAR).
    
    Args:
        amount: Amount to format
        currency: Currency code (default: ZAR)
        symbol: Currency symbol (default: R)
        include_cents: Include cents in output
        
    Returns:
        str: Formatted currency string (e.g., "R6,500" or "R6,500.00")
        
    Examples:
        >>> format_currency(6500)
        'R6,500'
        >>> format_currency(6500.50, include_cents=True)
        'R6,500.50'
    """
    currency = currency or settings.currency_code
    symbol = symbol or settings.currency_symbol
    
    # Convert to Decimal for precise formatting
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    
    # Round appropriately
    if include_cents:
        amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{symbol}{amount:,.2f}"
    else:
        amount = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"{symbol}{int(amount):,}"


def format_price_range(min_price: Decimal, max_price: Decimal) -> str:
    """
    Format price range.
    
    Args:
        min_price: Minimum price
        max_price: Maximum price
        
    Returns:
        str: Formatted price range (e.g., "R5,000 - R7,000")
    """
    min_str = format_currency(min_price)
    max_str = format_currency(max_price)
    return f"{min_str} - {max_str}"


# =============================================================================
# DATE/TIME FORMATTING
# =============================================================================

def format_date(
    dt: Union[date, datetime],
    format_str: str = "%d %B %Y",
) -> str:
    """
    Format date using South African conventions.
    
    Args:
        dt: Date/datetime to format
        format_str: strftime format string
        
    Returns:
        str: Formatted date string
        
    Examples:
        >>> format_date(date(2026, 4, 1))
        '01 April 2026'
    """
    if isinstance(dt, datetime):
        # Convert to SAST timezone
        tz = pytz.timezone(settings.timezone)
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        else:
            dt = dt.astimezone(tz)
    
    return dt.strftime(format_str)


def format_datetime_short(dt: datetime) -> str:
    """
    Format datetime in short South African format.
    
    Args:
        dt: Datetime to format
        
    Returns:
        str: Formatted datetime (e.g., "01 Apr 2026 14:30")
    """
    return format_date(dt, "%d %b %Y %H:%M")


def get_sast_now() -> datetime:
    """
    Get current datetime in SAST timezone.
    
    Returns:
        datetime: Current datetime in SAST
    """
    tz = pytz.timezone(settings.timezone)
    return datetime.now(tz)


def format_relative_date(dt: date) -> str:
    """
    Format date relative to today.
    
    Args:
        dt: Date to format
        
    Returns:
        str: Relative date string (e.g., "Today", "Yesterday", "2 days ago")
    """
    today = date.today()
    delta = today - dt
    
    if delta.days == 0:
        return "Today"
    elif delta.days == 1:
        return "Yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    else:
        return format_date(dt)


# =============================================================================
# PERCENTAGE FORMATTING
# =============================================================================

def format_percentage(value: Union[int, float, Decimal], decimals: int = 0) -> str:
    """
    Format value as percentage.
    
    Args:
        value: Percentage value (e.g., 0.15 for 15%)
        decimals: Number of decimal places
        
    Returns:
        str: Formatted percentage (e.g., "15%" or "15.00%")
    """
    if isinstance(value, (int, float)):
        value = Decimal(str(value))
    
    percent = value * 100
    
    if decimals == 0:
        return f"{int(percent)}%"
    else:
        format_str = f"%.{decimals}f%%"
        return format_str % float(percent)


def format_adjustment(adjustment: Decimal) -> str:
    """
    Format price adjustment with sign.
    
    Args:
        adjustment: Adjustment amount (positive or negative)
        
    Returns:
        str: Formatted adjustment (e.g., "+R500" or "-R650")
    """
    symbol = "+" if adjustment >= 0 else ""
    amount = abs(adjustment)
    return f"{symbol}{format_currency(amount)}"


# =============================================================================
# SERIAL NUMBER FORMATTING
# =============================================================================

def format_serial(serial: str, mask: bool = False) -> str:
    """
    Format serial number for display.
    
    Args:
        serial: Serial number
        mask: Mask partial serial for privacy
        
    Returns:
        str: Formatted serial number
    """
    if not serial:
        return "N/A"
    
    if mask and len(serial) > 4:
        return f"{'*' * (len(serial) - 4)}{serial[-4:]}"
    
    return serial


# =============================================================================
# NUMBER FORMATTING
# =============================================================================

def format_number(value: int, separator: str = ",") -> str:
    """
    Format number with thousand separators.
    
    Args:
        value: Number to format
        separator: Thousand separator (default: comma)
        
    Returns:
        str: Formatted number
    """
    return f"{value:,}".replace(",", separator)


def format_days(days: int) -> str:
    """
    Format days in human-readable format.
    
    Args:
        days: Number of days
        
    Returns:
        str: Formatted days string
    """
    if days == 0:
        return "Today"
    elif days == 1:
        return "1 day"
    elif days < 7:
        return f"{days} days"
    elif days < 30:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''}"
    else:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''}"
