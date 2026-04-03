"""
RefurbAdmin AI - Services Module

Business logic services for pricing, scraping, and scheduling.
"""

from .pricing_service import PricingService
from .market_scraper_service import MarketScraperService, MarketPriceData, PriceRecommendation
from .scraper_scheduler import ScraperScheduler, ScraperHealthStatus, SchedulerStats
from .email_service import EmailService
from .whatsapp_service import WhatsAppService
from .report_generator import ReportGenerator
from .analytics_service import AnalyticsService

__all__ = [
    # Core services
    "PricingService",
    "MarketScraperService",
    "MarketPriceData",
    "PriceRecommendation",
    "ScraperScheduler",
    "ScraperHealthStatus",
    "SchedulerStats",
    # Advanced services (Phase 6)
    "EmailService",
    "WhatsAppService",
    "ReportGenerator",
    "AnalyticsService",
]
