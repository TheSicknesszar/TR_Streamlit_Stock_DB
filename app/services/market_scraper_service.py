"""
RefurbAdmin AI - Market Scraper Service

Service for aggregating market price data from multiple scrapers.
Handles concurrent scraping, data normalization, caching, and price analysis.

South African Context:
- All prices in ZAR (South African Rand)
- SAST timezone for timestamps
- Local retailer focus
"""

import asyncio
import logging
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers import (
    PriceCheckScraper,
    TakealotScraper,
    GumtreeScraper,
    ScrapingResult,
    ScrapedProduct,
)

logger = logging.getLogger(__name__)


@dataclass
class MarketPriceData:
    """Normalized market price data for a product."""
    search_query: str
    median_price: float
    min_price: float
    max_price: float
    average_price: float
    total_listings: int
    price_by_source: Dict[str, List[float]]
    listings_by_condition: Dict[str, int]
    scraped_at: datetime
    sources_scraped: List[str]
    sources_failed: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if data.get('scraped_at') and isinstance(data['scraped_at'], datetime):
            data['scraped_at'] = data['scraped_at'].isoformat()
        return data


@dataclass
class PriceRecommendation:
    """Price recommendation based on market data."""
    suggested_price: float
    min_acceptable: float
    max_acceptable: float
    confidence: str  # 'high', 'medium', 'low'
    reasoning: str
    market_median: float
    competitor_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MarketScraperService:
    """
    Service for aggregating market price data from multiple sources.

    Features:
    - Concurrent scraping from multiple sources
    - Data normalization and deduplication
    - Database caching with expiry
    - Statistical price analysis
    - Price recommendations
    """

    # Cache expiry in seconds (24 hours)
    CACHE_EXPIRY_SECONDS = 24 * 60 * 60

    def __init__(
        self,
        db_session: AsyncSession,
        enable_mock_data: bool = True,
    ):
        """
        Initialize market scraper service.

        Args:
            db_session: Async database session
            enable_mock_data: Enable mock data fallback for testing
        """
        self.db_session = db_session
        self.enable_mock_data = enable_mock_data

        # Initialize scrapers
        self.scrapers = [
            PriceCheckScraper(),
            TakealotScraper(),
            GumtreeScraper(),
        ]

        # Enable mock data if requested
        if enable_mock_data:
            for scraper in self.scrapers:
                scraper.enable_mock_data(True)

    async def scrape_all_sources(self, search_query: str) -> MarketPriceData:
        """
        Scrape all sources concurrently for a search query.

        Args:
            search_query: Product search query

        Returns:
            MarketPriceData with aggregated results
        """
        logger.info(f"MarketScraperService: Starting scrape for '{search_query}'")
        start_time = datetime.now()

        # Run all scrapers concurrently
        tasks = [self._scrape_with_timeout(scraper, search_query) for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        all_products: List[ScrapedProduct] = []
        sources_scraped: List[str] = []
        sources_failed: List[str] = []

        for i, result in enumerate(results):
            scraper_name = self.scrapers[i].get_source_name()
            if isinstance(result, Exception):
                logger.error(f"{scraper_name}: Scraping failed - {result}")
                sources_failed.append(scraper_name)
            elif isinstance(result, ScrapingResult):
                if result.success:
                    all_products.extend(result.products)
                    sources_scraped.append(scraper_name)
                    logger.info(f"{scraper_name}: Found {result.total_found} products")
                else:
                    sources_failed.append(scraper_name)
                    logger.warning(f"{scraper_name}: No results - {result.error}")

        # Analyze and aggregate data
        market_data = self._analyze_prices(search_query, all_products, start_time)
        market_data.sources_scraped = sources_scraped
        market_data.sources_failed = sources_failed

        # Cache results in database
        await self._cache_market_data(market_data)

        logger.info(
            f"MarketScraperService: Complete - {market_data.total_listings} listings, "
            f"median R{market_data.median_price:,.2f}"
        )

        return market_data

    async def _scrape_with_timeout(
        self,
        scraper,
        search_query: str,
        timeout: int = 60,
    ) -> ScrapingResult:
        """
        Scrape with timeout protection.

        Args:
            scraper: Scraper instance
            search_query: Search query
            timeout: Timeout in seconds

        Returns:
            ScrapingResult
        """
        try:
            result = await asyncio.wait_for(
                scraper.scrape(search_query),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"{scraper.get_source_name()}: Timeout after {timeout}s")
            return ScrapingResult(
                success=False,
                source=scraper.get_source_name(),
                products=[],
                error=f"Timeout after {timeout}s",
                total_found=0,
                scrape_duration_ms=timeout * 1000,
            )
        finally:
            await scraper.close()

    def _analyze_prices(
        self,
        search_query: str,
        products: List[ScrapedProduct],
        start_time: datetime,
    ) -> MarketPriceData:
        """
        Analyze and aggregate price data.

        Args:
            search_query: Search query
            products: List of scraped products
            start_time: Scrape start time

        Returns:
            MarketPriceData with analysis
        """
        if not products:
            return MarketPriceData(
                search_query=search_query,
                median_price=0,
                min_price=0,
                max_price=0,
                average_price=0,
                total_listings=0,
                price_by_source={},
                listings_by_condition={},
                scraped_at=datetime.now(),
                sources_scraped=[],
                sources_failed=[],
            )

        # Extract prices
        prices = [p.price for p in products if p.price and p.price > 0]

        # Group by source
        price_by_source: Dict[str, List[float]] = {}
        for product in products:
            if product.price and product.price > 0:
                if product.source not in price_by_source:
                    price_by_source[product.source] = []
                price_by_source[product.source].append(product.price)

        # Group by condition
        listings_by_condition: Dict[str, int] = {}
        for product in products:
            condition = product.condition or "unknown"
            listings_by_condition[condition] = listings_by_condition.get(condition, 0) + 1

        # Calculate statistics
        median_price = statistics.median(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        average_price = statistics.mean(prices) if prices else 0

        return MarketPriceData(
            search_query=search_query,
            median_price=round(median_price, 2),
            min_price=round(min_price, 2),
            max_price=round(max_price, 2),
            average_price=round(average_price, 2),
            total_listings=len(products),
            price_by_source=price_by_source,
            listings_by_condition=listings_by_condition,
            scraped_at=datetime.now(),
            sources_scraped=[],
            sources_failed=[],
        )

    async def _cache_market_data(self, market_data: MarketPriceData) -> None:
        """
        Cache market data in database.

        Args:
            market_data: Market data to cache
        """
        try:
            # Import models here to avoid circular imports
            from app.models.market_price import MarketPrice

            # Check if existing record exists
            stmt = select(MarketPrice).where(
                MarketPrice.search_query == market_data.search_query
            )
            result = await self.db_session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.median_price = market_data.median_price
                existing.min_price = market_data.min_price
                existing.max_price = market_data.max_price
                existing.average_price = market_data.average_price
                existing.total_listings = market_data.total_listings
                existing.price_by_source = market_data.price_by_source
                existing.listings_by_condition = market_data.listings_by_condition
                existing.scraped_at = market_data.scraped_at
                existing.sources_scraped = market_data.sources_scraped
                existing.sources_failed = market_data.sources_failed
            else:
                # Create new record
                new_record = MarketPrice(
                    search_query=market_data.search_query,
                    median_price=market_data.median_price,
                    min_price=market_data.min_price,
                    max_price=market_data.max_price,
                    average_price=market_data.average_price,
                    total_listings=market_data.total_listings,
                    price_by_source=market_data.price_by_source,
                    listings_by_condition=market_data.listings_by_condition,
                    scraped_at=market_data.scraped_at,
                    sources_scraped=market_data.sources_scraped,
                    sources_failed=market_data.sources_failed,
                )
                self.db_session.add(new_record)

            await self.db_session.commit()
            logger.debug(f"Cached market data for '{market_data.search_query}'")

        except Exception as e:
            logger.error(f"Error caching market data: {e}")
            await self.db_session.rollback()

    async def get_cached_data(self, search_query: str) -> Optional[MarketPriceData]:
        """
        Get cached market data if not expired.

        Args:
            search_query: Search query

        Returns:
            MarketPriceData or None if expired/not found
        """
        try:
            from app.models.market_price import MarketPrice

            stmt = select(MarketPrice).where(
                MarketPrice.search_query == search_query
            )
            result = await self.db_session.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                return None

            # Check if cache is expired
            expiry = timedelta(seconds=self.CACHE_EXPIRY_SECONDS)
            if datetime.now() - record.scraped_at > expiry:
                logger.debug(f"Cache expired for '{search_query}'")
                return None

            # Convert to MarketPriceData
            return MarketPriceData(
                search_query=record.search_query,
                median_price=record.median_price,
                min_price=record.min_price,
                max_price=record.max_price,
                average_price=record.average_price,
                total_listings=record.total_listings,
                price_by_source=record.price_by_source,
                listings_by_condition=record.listings_by_condition,
                scraped_at=record.scraped_at,
                sources_scraped=record.sources_scraped or [],
                sources_failed=record.sources_failed or [],
            )

        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            return None

    def generate_price_recommendation(
        self,
        market_data: MarketPriceData,
        device_condition: str = "refurbished",
        margin_percent: float = 20,
    ) -> PriceRecommendation:
        """
        Generate price recommendation based on market data.

        Args:
            market_data: Market price data
            device_condition: Device condition
            margin_percent: Desired profit margin percentage

        Returns:
            PriceRecommendation
        """
        if market_data.total_listings == 0:
            return PriceRecommendation(
                suggested_price=0,
                min_acceptable=0,
                max_acceptable=0,
                confidence="low",
                reasoning="No market data available",
                market_median=0,
                competitor_count=0,
            )

        # Get prices for similar condition
        condition_prices = market_data.price_by_source
        all_prices = []
        for source_prices in condition_prices.values():
            all_prices.extend(source_prices)

        if not all_prices:
            all_prices = [market_data.median_price]

        median = market_data.median_price

        # Adjust for condition
        condition_multiplier = {
            "new": 1.3,
            "refurbished": 1.0,
            "used": 0.8,
            "faulty": 0.5,
        }.get(device_condition, 1.0)

        adjusted_median = median * condition_multiplier

        # Calculate suggested price with margin
        # For refurbished, we want to be competitive but maintain margin
        suggested_price = adjusted_median * (1 - margin_percent / 100)

        # Set acceptable range
        min_acceptable = suggested_price * 0.9  # 10% below suggested
        max_acceptable = suggested_price * 1.15  # 15% above suggested

        # Determine confidence based on data quality
        competitor_count = market_data.total_listings
        if competitor_count >= 10:
            confidence = "high"
            reasoning = f"Based on {competitor_count} market listings across {len(condition_prices)} sources"
        elif competitor_count >= 5:
            confidence = "medium"
            reasoning = f"Based on {competitor_count} market listings"
        else:
            confidence = "low"
            reasoning = f"Limited data - only {competitor_count} listings found"

        return PriceRecommendation(
            suggested_price=round(suggested_price, 2),
            min_acceptable=round(min_acceptable, 2),
            max_acceptable=round(max_acceptable, 2),
            confidence=confidence,
            reasoning=reasoning,
            market_median=round(median, 2),
            competitor_count=competitor_count,
        )

    async def refresh_expired_cache(self) -> int:
        """
        Refresh all expired cache entries.

        Returns:
            Number of entries refreshed
        """
        try:
            from app.models.market_price import MarketPrice

            expiry_time = datetime.now() - timedelta(seconds=self.CACHE_EXPIRY_SECONDS)

            stmt = select(MarketPrice).where(
                MarketPrice.scraped_at < expiry_time
            )
            result = await self.db_session.execute(stmt)
            expired_records = result.scalars().all()

            refreshed = 0
            for record in expired_records:
                logger.info(f"Refreshing cache for '{record.search_query}'")
                market_data = await self.scrape_all_sources(record.search_query)
                if market_data.total_listings > 0:
                    refreshed += 1

            return refreshed

        except Exception as e:
            logger.error(f"Error refreshing cache: {e}")
            return 0

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get scraper health status.

        Returns:
            Health status dictionary
        """
        return {
            "status": "healthy",
            "scrapers": [
                {
                    "name": scraper.get_source_name(),
                    "status": "available",
                }
                for scraper in self.scrapers
            ],
            "cache_expiry_hours": self.CACHE_EXPIRY_SECONDS / 3600,
            "mock_data_enabled": self.enable_mock_data,
        }
