"""
RefurbAdmin AI - Pricing Service

Smart pricing engine with market data integration and velocity modifiers.
South African context (ZAR currency, retail psychology pricing).
"""

import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device, DeviceStatus
from app.models.market_price import MarketPrice
from app.config import settings

logger = logging.getLogger(__name__)


class PricingService:
    """
    Smart pricing service for dynamic price calculation.
    
    Features:
    - Market price lookup and aggregation
    - Inventory velocity-based adjustments
    - Retail psychology price rounding
    - Margin calculation and validation
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize pricing service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.config = settings
    
    async def calculate_price(
        self,
        device: Device,
        margin_override: Optional[Decimal] = None,
    ) -> dict:
        """
        Calculate dynamic price for a device.
        
        Args:
            device: Device to price
            margin_override: Optional margin override percentage
            
        Returns:
            dict: Pricing breakdown with all components
        """
        # Get base market price
        base_price = await self._get_base_market_price(device)
        
        # If no market data, use cost price with minimum margin
        if base_price is None:
            if device.cost_price:
                base_price = Decimal(str(device.cost_price)) * Decimal("1.25")  # 25% minimum margin
            else:
                base_price = Decimal("5000")  # Default fallback
        
        # Calculate velocity adjustment
        velocity_adjustment, velocity_percent = await self._calculate_velocity_adjustment(
            device, base_price
        )
        
        # Apply adjustment
        adjusted_price = base_price + velocity_adjustment
        
        # Apply retail psychology rounding
        final_price = self._round_to_retail(adjusted_price)
        
        # Calculate margin
        margin_percent = None
        if device.cost_price and device.cost_price > 0:
            cost = Decimal(str(device.cost_price))
            margin_percent = ((final_price - cost) / cost) * 100
        
        # Apply margin override if provided
        if margin_override is not None and device.cost_price:
            cost = Decimal(str(device.cost_price))
            final_price = cost * (1 + margin_override / 100)
            final_price = self._round_to_retail(final_price)
            margin_percent = margin_override
        
        return {
            "base_market_price_zar": base_price.quantize(Decimal("0.01")),
            "velocity_adjustment": velocity_adjustment.quantize(Decimal("0.01")),
            "velocity_adjustment_percent": velocity_percent,
            "final_price_zar": final_price.quantize(Decimal("0.01")),
            "currency": settings.currency_code,
            "warranty_months": settings.default_warranty_months,
            "margin_percent": margin_percent.quantize(Decimal("0.01")) if margin_percent else None,
        }
    
    async def _get_base_market_price(self, device: Device) -> Optional[Decimal]:
        """
        Get base market price from cached market data.
        
        Args:
            device: Device to find market prices for
            
        Returns:
            Decimal: Median market price or None
        """
        # Build query for similar devices
        query = select(MarketPrice.price_zar).where(
            MarketPrice.model.ilike(f"%{device.model}%")
        )
        
        # Add RAM filter if available
        if device.ram_gb:
            query = query.where(MarketPrice.ram_gb == device.ram_gb)
        
        # Add SSD filter if available
        if device.ssd_gb:
            query = query.where(MarketPrice.ssd_gb == device.ssd_gb)
        
        # Execute query
        result = await self.db.execute(query)
        prices = result.scalars().all()
        
        if not prices:
            logger.debug(f"No market data found for {device.make} {device.model}")
            return None
        
        # Calculate median
        prices_sorted = sorted([Decimal(str(p)) for p in prices])
        n = len(prices_sorted)
        
        if n % 2 == 0:
            median = (prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2
        else:
            median = prices_sorted[n // 2]
        
        logger.debug(f"Median market price for {device.model}: R{median}")
        return median
    
    async def _calculate_velocity_adjustment(
        self,
        device: Device,
        base_price: Decimal,
    ) -> Tuple[Decimal, str]:
        """
        Calculate inventory velocity-based price adjustment.
        
        Args:
            device: Device to calculate adjustment for
            base_price: Base market price
            
        Returns:
            Tuple[Decimal, str]: Adjustment amount and percentage string
        """
        days_in_stock = device.days_in_stock
        
        # Count similar devices in stock
        similar_count = await self._count_similar_devices(device)
        
        adjustment = Decimal("0")
        adjustment_percent = "0%"
        
        # Slow-moving inventory: >30 days AND >5 units
        if days_in_stock > self.config.slow_moving_days and similar_count > self.config.slow_moving_stock_threshold:
            adjustment = -base_price * Decimal(str(self.config.slow_moving_discount))
            adjustment_percent = f"-{int(self.config.slow_moving_discount * 100)}%"
            logger.info(
                f"Applying slow-moving discount: {device.serial_number} "
                f"({days_in_stock} days, {similar_count} units)"
            )
        
        # High-demand inventory: <3 units
        elif similar_count < self.config.high_demand_stock_threshold:
            adjustment = base_price * Decimal(str(self.config.high_demand_premium))
            adjustment_percent = f"+{int(self.config.high_demand_premium * 100)}%"
            logger.info(
                f"Applying high-demand premium: {device.serial_number} "
                f"({similar_count} units in stock)"
            )
        
        # Normal inventory: no adjustment
        else:
            logger.debug(f"No velocity adjustment for {device.serial_number}")
        
        return adjustment, adjustment_percent
    
    async def _count_similar_devices(self, device: Device) -> int:
        """
        Count similar devices in ready status.
        
        Args:
            device: Device to find similar devices for
            
        Returns:
            int: Count of similar devices
        """
        query = select(func.count(Device.id)).where(
            Device.status == DeviceStatus.READY,
            Device.make == device.make,
            Device.model == device.model,
        )
        
        if device.ram_gb:
            query = query.where(Device.ram_gb == device.ram_gb)
        
        if device.ssd_gb:
            query = query.where(Device.ssd_gb == device.ssd_gb)
        
        result = await self.db.execute(query)
        count = result.scalar() or 0
        
        return count
    
    def _round_to_retail(self, price: Decimal) -> Decimal:
        """
        Apply retail psychology price rounding.
        
        Rounds to common retail price points:
        - R4,999 / R5,499 / R5,999 / R6,499 / R6,999
        - R7,499 / R7,999 / R8,499 / R8,999 / R9,499 / R9,999
        
        Args:
            price: Raw price
            
        Returns:
            Decimal: Rounded retail price
        """
        # Round to nearest 500, then adjust to retail psychology
        rounded = int(price)
        
        # Find the thousand base
        thousands = (rounded // 1000) * 1000
        
        # Get the remainder
        remainder = rounded % 1000
        
        # Apply retail rounding
        if remainder < 250:
            retail_price = thousands - 1 + 999  # e.g., R6,999
        elif remainder < 500:
            retail_price = thousands + 499  # e.g., R6,499
        elif remainder < 750:
            retail_price = thousands + 999  # e.g., R6,999
        else:
            retail_price = thousands + 1499  # e.g., R7,499
        
        # Ensure we don't go below cost + minimum margin
        min_price = price
        
        return Decimal(max(retail_price, int(min_price)))
    
    def generate_client_snippet(
        self,
        device: Device,
        final_price: Decimal,
        include_warranty: bool = True,
    ) -> str:
        """
        Generate client-ready text snippet.
        
        Args:
            device: Device being quoted
            final_price: Final price in ZAR
            include_warranty: Include warranty information
            
        Returns:
            str: Client-ready text snippet
        """
        model_name = f"{device.make} {device.model}"
        price_str = self.format_price(final_price)
        
        snippet = f"We have the {model_name} (Serial: {device.serial_number}) available for {price_str}."
        
        if include_warranty:
            snippet += f" Includes {settings.default_warranty_months}-month warranty and full quality inspection."
        
        return snippet
    
    def format_price(self, price: Decimal) -> str:
        """
        Format price for display (South African format).
        
        Args:
            price: Price in ZAR
            
        Returns:
            str: Formatted price string (e.g., "R6,500")
        """
        # Round to whole number for display
        rounded = int(price.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        
        # Format with commas
        formatted = f"{rounded:,}"
        
        return f"{settings.currency_symbol}{formatted}"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def round_to_retail(price: float) -> int:
    """
    Standalone function for retail price rounding.
    
    Args:
        price: Raw price
        
    Returns:
        int: Rounded retail price
    """
    service = PricingService(None)  # type: ignore
    return int(service._round_to_retail(Decimal(str(price))))
