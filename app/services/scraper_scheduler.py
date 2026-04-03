"""
RefurbAdmin AI - Scraper Scheduler

Scheduled task runner for market price scrapers.
Handles daily scraping, cache expiry, health monitoring, and failure alerts.

South African Context:
- Runs on SAST timezone (UTC+2)
- Scheduled for off-peak hours (2 AM SAST)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ScraperHealthStatus:
    """Health status for a scraper."""
    name: str
    status: str  # 'healthy', 'degraded', 'failed'
    last_run: Optional[datetime]
    last_success: Optional[datetime]
    consecutive_failures: int
    error_message: Optional[str]
    avg_response_time_ms: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        for key in ['last_run', 'last_success']:
            if data.get(key) and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        return data


@dataclass
class SchedulerStats:
    """Scheduler statistics."""
    total_runs: int
    successful_runs: int
    failed_runs: int
    last_run: Optional[datetime]
    next_scheduled_run: Optional[datetime]
    cache_entries: int
    cache_expired: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        for key in ['last_run', 'next_scheduled_run']:
            if data.get(key) and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        return data


class ScraperScheduler:
    """
    Scheduler for running market price scrapers.

    Features:
    - Daily scheduled execution
    - Cache expiry management (24 hours)
    - Health monitoring
    - Failure alerting
    - Manual trigger support
    """

    # Default schedule: 2 AM SAST daily
    DEFAULT_SCHEDULE_HOUR = 2
    DEFAULT_SCHEDULE_MINUTE = 0

    # Alert thresholds
    CONSECUTIVE_FAILURE_THRESHOLD = 3
    MAX_RESPONSE_TIME_MS = 30000

    def __init__(
        self,
        db_session: AsyncSession,
        schedule_hour: int = DEFAULT_SCHEDULE_HOUR,
        schedule_minute: int = DEFAULT_SCHEDULE_MINUTE,
        alert_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize scraper scheduler.

        Args:
            db_session: Async database session
            schedule_hour: Hour to run daily scrape (SAST)
            schedule_minute: Minute to run daily scrape
            alert_callback: Callback function for alerts
        """
        self.db_session = db_session
        self.schedule_hour = schedule_hour
        self.schedule_minute = schedule_minute
        self.alert_callback = alert_callback

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._health_status: Dict[str, ScraperHealthStatus] = {}
        self._stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'last_run': None,
        }

        # Initialize health status for known scrapers
        self._init_health_status()

    def _init_health_status(self) -> None:
        """Initialize health status for scrapers."""
        scrapers = [
            "PriceCheck.co.za",
            "Takealot.com",
            "Gumtree.co.za",
        ]
        for name in scrapers:
            self._health_status[name] = ScraperHealthStatus(
                name=name,
                status="healthy",
                last_run=None,
                last_success=None,
                consecutive_failures=0,
                error_message=None,
                avg_response_time_ms=0,
            )

    async def start(self) -> None:
        """Start the scheduler background task."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(
            f"Scheduler started - daily runs at {self.schedule_hour:02d}:{self.schedule_minute:02d} SAST"
        )

    async def stop(self) -> None:
        """Stop the scheduler background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Scheduler stopped")

    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                # Calculate next run time
                next_run = self._get_next_run_time()
                sleep_seconds = (next_run - datetime.now()).total_seconds()

                if sleep_seconds > 0:
                    logger.debug(f"Next scrape scheduled in {sleep_seconds/3600:.1f} hours")
                    await asyncio.sleep(sleep_seconds)

                if self._running:
                    await self._run_daily_scrape()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    def _get_next_run_time(self) -> datetime:
        """Calculate next scheduled run time."""
        now = datetime.now()
        next_run = now.replace(
            hour=self.schedule_hour,
            minute=self.schedule_minute,
            second=0,
            microsecond=0,
        )

        # If already passed today, schedule for tomorrow
        if next_run <= now:
            next_run += timedelta(days=1)

        return next_run

    async def _run_daily_scrape(self) -> None:
        """Run daily scraping for all cached queries."""
        logger.info("Starting daily scraper run")
        start_time = datetime.now()

        try:
            # Import here to avoid circular imports
            from app.services.market_scraper_service import MarketScraperService

            # Get all cached search queries
            from app.models.market_price import MarketPrice
            stmt = select(MarketPrice.search_query).distinct()
            result = await self.db_session.execute(stmt)
            search_queries = [row[0] for row in result.all()]

            if not search_queries:
                logger.info("No cached queries to refresh")
                self._stats['last_run'] = start_time
                self._stats['total_runs'] += 1
                return

            # Create service with mock data disabled for real scraping
            service = MarketScraperService(self.db_session, enable_mock_data=False)

            # Scrape each query
            successful = 0
            failed = 0

            for query in search_queries:
                try:
                    logger.info(f"Refreshing cache for '{query}'")
                    market_data = await service.scrape_all_sources(query)

                    if market_data.total_listings > 0:
                        successful += 1
                        self._update_health_status(query, True, market_data.scrape_duration_ms if hasattr(market_data, 'scrape_duration_ms') else 0)
                    else:
                        failed += 1
                        self._update_health_status(query, False, 0, "No results")

                except Exception as e:
                    logger.error(f"Error scraping '{query}': {e}")
                    failed += 1
                    self._update_health_status(query, False, 0, str(e))

            # Update stats
            self._stats['last_run'] = start_time
            self._stats['total_runs'] += 1
            if failed == 0:
                self._stats['successful_runs'] += 1
            else:
                self._stats['failed_runs'] += 1

            # Send alert if too many failures
            if failed >= self.CONSECUTIVE_FAILURE_THRESHOLD:
                await self._send_alert(
                    f"Daily scrape: {failed}/{len(search_queries)} queries failed"
                )

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Daily scrape complete: {successful} successful, {failed} failed "
                f"in {duration:.1f}s"
            )

        except Exception as e:
            logger.error(f"Daily scrape failed: {e}")
            self._stats['failed_runs'] += 1
            await self._send_alert(f"Daily scrape failed: {e}")

    def _update_health_status(
        self,
        query: str,
        success: bool,
        response_time_ms: int,
        error: Optional[str] = None,
    ) -> None:
        """
        Update health status for scrapers.

        Args:
            query: Search query
            success: Whether scrape was successful
            response_time_ms: Response time in milliseconds
            error: Error message if failed
        """
        now = datetime.now()

        for name, status in self._health_status.items():
            status.last_run = now

            if success:
                status.status = "healthy"
                status.last_success = now
                status.consecutive_failures = 0
                status.error_message = None
                # Update average response time
                if status.avg_response_time_ms == 0:
                    status.avg_response_time_ms = response_time_ms
                else:
                    status.avg_response_time_ms = int(
                        (status.avg_response_time_ms * 0.8) + (response_time_ms * 0.2)
                    )
            else:
                status.consecutive_failures += 1
                status.error_message = error

                if status.consecutive_failures >= self.CONSECUTIVE_FAILURE_THRESHOLD:
                    status.status = "failed"
                elif status.consecutive_failures >= 1:
                    status.status = "degraded"

                # Check for slow response
                if response_time_ms > self.MAX_RESPONSE_TIME_MS:
                    status.status = "degraded"

    async def _send_alert(self, message: str) -> None:
        """
        Send alert notification.

        Args:
            message: Alert message
        """
        alert_msg = f"[RefurbAdmin Alert] {datetime.now().strftime('%Y-%m-%d %H:%M')} - {message}"
        logger.warning(alert_msg)

        if self.alert_callback:
            try:
                self.alert_callback(alert_msg)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    async def run_manual_scrape(self, search_queries: List[str]) -> Dict[str, Any]:
        """
        Run manual scraping for specified queries.

        Args:
            search_queries: List of search queries to scrape

        Returns:
            Results dictionary
        """
        logger.info(f"Manual scrape requested for {len(search_queries)} queries")

        from app.services.market_scraper_service import MarketScraperService

        service = MarketScraperService(self.db_session, enable_mock_data=True)
        results = {}

        for query in search_queries:
            try:
                market_data = await service.scrape_all_sources(query)
                results[query] = {
                    'success': True,
                    'data': market_data.to_dict(),
                }
            except Exception as e:
                logger.error(f"Manual scrape failed for '{query}': {e}")
                results[query] = {
                    'success': False,
                    'error': str(e),
                }

        return results

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status.

        Returns:
            Health status dictionary
        """
        return {
            'scrapers': [status.to_dict() for status in self._health_status.values()],
            'stats': self._stats,
            'next_scheduled_run': self._get_next_run_time().isoformat(),
            'is_running': self._running,
        }

    def get_stats(self) -> SchedulerStats:
        """Get scheduler statistics."""
        return SchedulerStats(
            total_runs=self._stats['total_runs'],
            successful_runs=self._stats['successful_runs'],
            failed_runs=self._stats['failed_runs'],
            last_run=self._stats['last_run'],
            next_scheduled_run=self._get_next_run_time(),
            cache_entries=0,  # Would need DB query
            cache_expired=0,
        )

    async def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        try:
            from app.models.market_price import MarketPrice

            # Total entries
            stmt = select(func.count(MarketPrice.id))
            result = await self.db_session.execute(stmt)
            total = result.scalar() or 0

            # Expired entries
            expiry_time = datetime.now() - timedelta(seconds=24 * 60 * 60)
            stmt = select(func.count(MarketPrice.id)).where(
                MarketPrice.scraped_at < expiry_time
            )
            result = await self.db_session.execute(stmt)
            expired = result.scalar() or 0

            return {
                'total_entries': total,
                'expired_entries': expired,
                'valid_entries': total - expired,
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                'total_entries': 0,
                'expired_entries': 0,
                'valid_entries': 0,
            }

    async def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """
        Clean up old market price data.

        Args:
            days_to_keep: Number of days to keep

        Returns:
            Number of records deleted
        """
        try:
            from app.models.market_price import MarketPrice

            cutoff = datetime.now() - timedelta(days=days_to_keep)
            # Note: Actual deletion would require a DELETE statement
            # This is a placeholder for the cleanup logic

            logger.info(f"Cleanup: Records older than {days_to_keep} days would be removed")
            return 0

        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return 0
