"""
Analytics Service for RefurbAdmin AI.

Provides business intelligence:
- Sales forecasting
- Inventory turnover analysis
- Profit margin trends
- Seasonal patterns

South African market considerations included.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsConfig:
    """Analytics configuration."""
    
    forecast_days: int = 30
    min_data_points: int = 10
    confidence_level: float = 0.95
    
    @classmethod
    def from_env(cls) -> "AnalyticsConfig":
        """Create config from environment."""
        return cls()


@dataclass
class SalesForecast:
    """Sales forecast result."""
    
    forecast_date: datetime
    predicted_sales: float
    confidence_lower: float
    confidence_upper: float
    trend: str  # increasing, decreasing, stable


class AnalyticsService:
    """
    Business analytics service for RefurbAdmin AI.
    
    Features:
    - Sales forecasting
    - Inventory turnover
    - Margin trends
    - Seasonal analysis
    """
    
    def __init__(self, config: Optional[AnalyticsConfig] = None):
        self.config = config or AnalyticsConfig()
        logger.info("Analytics service initialized")
    
    def calculate_sales_forecast(
        self,
        historical_sales: List[Dict[str, Any]],
        days_ahead: int = None,
    ) -> List[SalesForecast]:
        """
        Forecast future sales based on historical data.
        
        Args:
            historical_sales: List of historical sales records
            days_ahead: Days to forecast
            
        Returns:
            List of SalesForecast objects
        """
        days_ahead = days_ahead or self.config.forecast_days
        
        if len(historical_sales) < self.config.min_data_points:
            logger.warning("Insufficient data for forecasting")
            return []
        
        # Aggregate sales by day
        daily_sales = defaultdict(float)
        for sale in historical_sales:
            date = sale.get('date', datetime.utcnow())
            if isinstance(date, str):
                date = datetime.fromisoformat(date)
            daily_sales[date.date()] += sale.get('total', 0)
        
        if not daily_sales:
            return []
        
        # Calculate moving average
        sorted_dates = sorted(daily_sales.keys())
        values = [daily_sales[d] for d in sorted_dates]
        
        # Simple linear trend
        if len(values) >= 2:
            trend = self._calculate_trend(values)
        else:
            trend = 0
        
        # Generate forecast
        forecasts = []
        avg_sales = statistics.mean(values) if values else 0
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        for i in range(1, days_ahead + 1):
            forecast_date = datetime.utcnow() + timedelta(days=i)
            predicted = avg_sales + (trend * i)
            
            # Confidence interval
            margin = 1.96 * std_dev  # 95% confidence
            
            forecasts.append(SalesForecast(
                forecast_date=forecast_date,
                predicted_sales=max(0, predicted),
                confidence_lower=max(0, predicted - margin),
                confidence_upper=predicted + margin,
                trend="increasing" if trend > 0 else "decreasing" if trend < 0 else "stable",
            ))
        
        return forecasts
    
    def calculate_inventory_turnover(
        self,
        inventory_items: List[Dict[str, Any]],
        sales_data: List[Dict[str, Any]],
        period_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Calculate inventory turnover metrics.
        
        Args:
            inventory_items: Current inventory
            sales_data: Sales data for period
            period_days: Analysis period
            
        Returns:
            Turnover metrics
        """
        total_inventory_value = sum(
            item.get('cost_price', 0) * item.get('quantity', 0)
            for item in inventory_items
        )
        
        total_cogs = sum(
            sale.get('cost', 0)
            for sale in sales_data
        )
        
        turnover_ratio = total_cogs / total_inventory_value if total_inventory_value > 0 else 0
        
        # Days to sell inventory
        days_to_sell = period_days / turnover_ratio if turnover_ratio > 0 else float('inf')
        
        return {
            "turnover_ratio": round(turnover_ratio, 2),
            "days_to_sell_inventory": round(days_to_sell, 1),
            "total_inventory_value": total_inventory_value,
            "cost_of_goods_sold": total_cogs,
            "period_days": period_days,
        }
    
    def analyze_margin_trends(
        self,
        sales_data: List[Dict[str, Any]],
        group_by: str = "week",
    ) -> Dict[str, Any]:
        """
        Analyze profit margin trends.
        
        Args:
            sales_data: Sales records
            group_by: Grouping (day, week, month)
            
        Returns:
            Margin trend analysis
        """
        # Group sales by period
        grouped = defaultdict(list)
        
        for sale in sales_data:
            date = sale.get('date', datetime.utcnow())
            if isinstance(date, str):
                date = datetime.fromisoformat(date)
            
            if group_by == "week":
                key = date.isocalendar()[1]
            elif group_by == "month":
                key = date.month
            else:
                key = date.date()
            
            revenue = sale.get('total', 0)
            cost = sale.get('cost', 0)
            margin = ((revenue - cost) / revenue * 100) if revenue > 0 else 0
            
            grouped[key].append(margin)
        
        # Calculate averages
        period_margins = {
            period: statistics.mean(margins)
            for period, margins in grouped.items()
        }
        
        # Determine trend
        if len(period_margins) >= 2:
            values = list(period_margins.values())
            trend = self._calculate_trend(values)
        else:
            trend = 0
        
        return {
            "period_margins": period_margins,
            "average_margin": statistics.mean(period_margins.values()) if period_margins else 0,
            "trend": "increasing" if trend > 0.5 else "decreasing" if trend < -0.5 else "stable",
            "trend_value": trend,
        }
    
    def detect_seasonal_patterns(
        self,
        sales_data: List[Dict[str, Any]],
        min_periods: int = 12,
    ) -> Dict[str, Any]:
        """
        Detect seasonal patterns in sales.
        
        Args:
            sales_data: Historical sales
            min_periods: Minimum months of data
            
        Returns:
            Seasonal pattern analysis
        """
        # Group by month
        monthly_sales = defaultdict(float)
        monthly_counts = defaultdict(int)
        
        for sale in sales_data:
            date = sale.get('date', datetime.utcnow())
            if isinstance(date, str):
                date = datetime.fromisoformat(date)
            
            month = date.month
            monthly_sales[month] += sale.get('total', 0)
            monthly_counts[month] += 1
        
        if len(monthly_sales) < min_periods:
            return {"error": "Insufficient data for seasonal analysis"}
        
        # Calculate averages
        monthly_avg = {
            month: total / monthly_counts[month]
            for month, total in monthly_sales.items()
        }
        
        # Find peak and low months
        peak_month = max(monthly_avg, key=monthly_avg.get)
        low_month = min(monthly_avg, key=monthly_avg.get)
        
        # South African context
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December",
        }
        
        return {
            "peak_month": month_names.get(peak_month, str(peak_month)),
            "peak_month_avg": monthly_avg[peak_month],
            "low_month": month_names.get(low_month, str(low_month)),
            "low_month_avg": monthly_avg[low_month],
            "seasonality_index": monthly_avg[peak_month] / monthly_avg[low_month] if monthly_avg[low_month] > 0 else 1,
            "monthly_averages": {month_names.get(k, str(k)): v for k, v in monthly_avg.items()},
        }
    
    def get_business_insights(
        self,
        inventory: List[Dict],
        sales: List[Dict],
        quotes: List[Dict],
    ) -> Dict[str, Any]:
        """
        Generate comprehensive business insights.
        
        Args:
            inventory: Inventory data
            sales: Sales data
            quotes: Quotes data
            
        Returns:
            Business insights
        """
        insights = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {},
            "recommendations": [],
            "alerts": [],
        }
        
        # Sales insights
        total_sales = len(sales)
        total_revenue = sum(s.get('total', 0) for s in sales)
        
        insights["summary"]["total_sales"] = total_sales
        insights["summary"]["total_revenue"] = total_revenue
        
        # Quote conversion rate
        total_quotes = len(quotes)
        converted_quotes = sum(1 for q in quotes if q.get('status') == 'converted')
        conversion_rate = (converted_quotes / total_quotes * 100) if total_quotes > 0 else 0
        
        insights["summary"]["quote_conversion_rate"] = round(conversion_rate, 1)
        
        # Inventory insights
        low_stock_items = [i for i in inventory if i.get('quantity', 0) < 5]
        if low_stock_items:
            insights["alerts"].append({
                "type": "low_stock",
                "message": f"{len(low_stock_items)} items are low on stock",
                "items": [i.get('name') for i in low_stock_items[:5]],
            })
            insights["recommendations"].append("Review and reorder low stock items")
        
        # Margin insights
        if sales:
            total_cost = sum(s.get('cost', 0) for s in sales)
            overall_margin = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0
            
            insights["summary"]["overall_margin_percent"] = round(overall_margin, 1)
            
            if overall_margin < 20:
                insights["alerts"].append({
                    "type": "low_margin",
                    "message": f"Overall margin ({overall_margin:.1f}%) is below target (20%)",
                })
                insights["recommendations"].append("Review pricing strategy to improve margins")
        
        # Recommendations based on conversion rate
        if conversion_rate < 30:
            insights["recommendations"].append("Consider follow-up strategies for quotes")
        
        return insights
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate linear trend using simple regression."""
        if len(values) < 2:
            return 0
        
        n = len(values)
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(i * v for i, v in enumerate(values))
        sum_x2 = sum(i * i for i in range(n))
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope


# =============================================================================
# Singleton
# =============================================================================

_analytics_service_instance: Optional[AnalyticsService] = None


def get_analytics_service(config: Optional[AnalyticsConfig] = None) -> AnalyticsService:
    """Get or create the analytics service singleton."""
    global _analytics_service_instance
    
    if _analytics_service_instance is None:
        _analytics_service_instance = AnalyticsService(config=config)
    
    return _analytics_service_instance
