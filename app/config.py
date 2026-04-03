"""
RefurbAdmin AI - Configuration Settings

Centralized configuration management using environment variables.
South African context (ZAR currency, SAST timezone, POPIA compliance).
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # =========================================================================
    # APPLICATION SETTINGS
    # =========================================================================
    app_name: str = Field(default="RefurbAdmin AI", description="Application name")
    app_env: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=True, description="Debug mode")
    secret_key: str = Field(
        default="change-this-secret-key-in-production-min-32-characters",
        description="Secret key for security operations"
    )
    timezone: str = Field(default="Africa/Johannesburg", description="Timezone (SAST)")

    # =========================================================================
    # DATABASE CONFIGURATION
    # =========================================================================
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/refurbadmin_dev.db",
        description="Database connection URL"
    )
    db_pool_size: int = Field(default=5, description="Database connection pool size")
    db_max_overflow: int = Field(default=10, description="Database max overflow connections")

    # =========================================================================
    # API CONFIGURATION
    # =========================================================================
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    api_key_expiry_days: int = Field(default=90, description="API key expiry in days")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        description="CORS allowed origins"
    )

    # =========================================================================
    # SECURITY SETTINGS
    # =========================================================================
    encryption_key: Optional[str] = Field(
        default=None,
        description="Fernet encryption key for POPIA-compliant PII storage"
    )
    bcrypt_rounds: int = Field(default=12, description="Bcrypt hashing rounds")

    # =========================================================================
    # PRICING ENGINE SETTINGS
    # =========================================================================
    default_warranty_months: int = Field(default=3, description="Default warranty period in months")
    min_margin_percent: float = Field(default=25.0, description="Minimum margin percentage")
    max_discount_percent: float = Field(default=15.0, description="Maximum discount without override")
    
    # Velocity thresholds
    slow_moving_days: int = Field(default=30, description="Days before item is considered slow-moving")
    slow_moving_stock_threshold: int = Field(default=5, description="Stock count threshold for slow-moving")
    high_demand_stock_threshold: int = Field(default=3, description="Stock count threshold for high demand")
    
    # Velocity adjustments
    slow_moving_discount: float = Field(default=0.10, description="Discount for slow-moving items (10%)")
    high_demand_premium: float = Field(default=0.05, description="Premium for high-demand items (5%)")
    
    # Market data
    market_data_cache_hours: int = Field(default=24, description="Market data cache expiry in hours")

    # =========================================================================
    # WEB SCRAPING SETTINGS
    # =========================================================================
    scraper_rate_limit: float = Field(default=1.0, description="Scraper rate limit (requests/second)")
    scraper_max_concurrent: int = Field(default=5, description="Maximum concurrent scrapers")
    scraper_timeout: int = Field(default=30, description="Scraper request timeout in seconds")
    scraper_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="User agent for web scrapers"
    )

    # =========================================================================
    # LOGGING SETTINGS
    # =========================================================================
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Logging format: json, text")
    log_file: str = Field(default="data/logs/refurbadmin.log", description="Log file path")

    # =========================================================================
    # NOTIFICATION SETTINGS
    # =========================================================================
    smtp_host: Optional[str] = Field(default=None, description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_from_email: Optional[str] = Field(default=None, description="From email address")
    smtp_from_name: Optional[str] = Field(default="RefurbAdmin AI", description="From name")

    # =========================================================================
    # BUSINESS SETTINGS (South African Context)
    # =========================================================================
    currency_code: str = Field(default="ZAR", description="Currency code")
    currency_symbol: str = Field(default="R", description="Currency symbol (Rand)")
    country_code: str = Field(default="ZA", description="Country code")
    business_hour_start: str = Field(default="08:00", description="Business hour start (SAST)")
    business_hour_end: str = Field(default="17:00", description="Business hour end (SAST)")
    quote_validity_hours: int = Field(default=48, description="Quote validity period in hours")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"

    @property
    def uses_sqlite(self) -> bool:
        """Check if using SQLite database (development)."""
        return self.database_url.startswith("sqlite")

    class Config:
        """Pydantic settings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Convenience function for accessing settings
settings = get_settings()
