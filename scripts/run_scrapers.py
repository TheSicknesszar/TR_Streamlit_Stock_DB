#!/usr/bin/env python
"""
RefurbAdmin AI - Run Scrapers Script

Manual script to run market price scrapers for testing and data collection.
Can be run standalone or scheduled via cron/Task Scheduler.

Usage:
    python scripts/run_scrapers.py [search_query...]
    
Examples:
    python scripts/run_scrapers.py "Dell Latitude 5420"
    python scripts/run_scrapers.py "HP EliteBook 840" "Lenovo ThinkPad T14"
    python scripts/run_scrapers.py --all  # Run for all cached queries
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.scrapers import PriceCheckScraper, TakealotScraper, GumtreeScraper
from app.services.market_scraper_service import MarketScraperService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/scrapers.log", mode="a"),
    ],
)

logger = logging.getLogger(__name__)


# Default search queries for South African market
DEFAULT_QUERIES = [
    "Dell Latitude 5420",
    "Dell Latitude 7490",
    "HP EliteBook 840 G7",
    "HP EliteBook 850 G5",
    "Lenovo ThinkPad T14",
    "Lenovo ThinkPad X1 Carbon",
    "Dell Precision 5540",
    "HP ZBook 15",
]


async def run_scrapers(
    search_queries: list[str],
    db_url: str = "sqlite+aiosqlite:///./data/refurbadmin.db",
    enable_mock: bool = True,
) -> None:
    """
    Run scrapers for given search queries.

    Args:
        search_queries: List of search queries
        db_url: Database URL
        enable_mock: Enable mock data fallback
    """
    logger.info(f"Starting scraper run for {len(search_queries)} queries")
    logger.info(f"Database: {db_url}")
    logger.info(f"Mock data: {'enabled' if enable_mock else 'disabled'}")

    # Create database session
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    total_products = 0
    successful_queries = 0

    async with async_session() as session:
        service = MarketScraperService(session, enable_mock_data=enable_mock)

        for query in search_queries:
            logger.info(f"\n{'='*60}")
            logger.info(f"Scraping: {query}")
            logger.info(f"{'='*60}")

            start_time = datetime.now()

            try:
                market_data = await service.scrape_all_sources(query)

                duration = (datetime.now() - start_time).total_seconds()

                if market_data.total_listings > 0:
                    successful_queries += 1
                    total_products += market_data.total_listings

                    logger.info(f"✅ Success: {market_data.total_listings} products found")
                    logger.info(f"   Median Price: R {market_data.median_price:,.2f}")
                    logger.info(f"   Price Range: R {market_data.min_price:,.2f} - R {market_data.max_price:,.2f}")
                    logger.info(f"   Sources: {', '.join(market_data.sources_scraped)}")
                    logger.info(f"   Duration: {duration:.1f}s")

                    # Print by-source breakdown
                    logger.info("   Prices by Source:")
                    for source, prices in market_data.price_by_source.items():
                        if prices:
                            avg = sum(prices) / len(prices)
                            logger.info(f"     - {source}: {len(prices)} listings, avg R {avg:,.2f}")

                else:
                    logger.warning(f"⚠️ No results for: {query}")
                    if market_data.sources_failed:
                        logger.warning(f"   Failed sources: {', '.join(market_data.sources_failed)}")

            except Exception as e:
                logger.error(f"❌ Error scraping '{query}': {e}")

        # Commit all changes
        await session.commit()

    logger.info(f"\n{'='*60}")
    logger.info("SCRAPER RUN COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Queries processed: {len(search_queries)}")
    logger.info(f"Successful: {successful_queries}")
    logger.info(f"Total products found: {total_products}")
    logger.info(f"Average products per query: {total_products / len(search_queries):.1f}")


async def run_all_cached(
    db_url: str = "sqlite+aiosqlite:///./data/refurbadmin.db",
) -> None:
    """
    Run scrapers for all cached queries.

    Args:
        db_url: Database URL
    """
    from sqlalchemy import select
    from app.models.market_price import MarketPrice

    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(MarketPrice.search_query).distinct()
        result = await session.execute(stmt)
        queries = [row[0] for row in result.all() if row[0]]

    if not queries:
        logger.info("No cached queries found. Using default queries.")
        queries = DEFAULT_QUERIES

    logger.info(f"Found {len(queries)} cached queries")
    await run_scrapers(queries, db_url, enable_mock=False)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run market price scrapers for RefurbAdmin AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Dell Latitude 5420"
  %(prog)s "HP EliteBook" "Lenovo ThinkPad"
  %(prog)s --all
  %(prog)s --default
        """,
    )

    parser.add_argument(
        "queries",
        nargs="*",
        help="Search queries to scrape",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run for all cached queries",
    )

    parser.add_argument(
        "--default",
        action="store_true",
        help="Run for default queries",
    )

    parser.add_argument(
        "--no-mock",
        action="store_true",
        help="Disable mock data fallback",
    )

    parser.add_argument(
        "--db",
        default="sqlite+aiosqlite:///./data/refurbadmin.db",
        help="Database URL (default: sqlite+aiosqlite:///./data/refurbadmin.db)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(args.log_level)

    # Determine queries to run
    if args.all:
        logger.info("Running for all cached queries...")
        asyncio.run(run_all_cached(args.db))
    elif args.default or not args.queries:
        queries = args.queries if args.queries else DEFAULT_QUERIES
        logger.info(f"Running for {len(queries)} queries...")
        asyncio.run(run_scrapers(queries, args.db, enable_mock=not args.no_mock))
    else:
        logger.info(f"Running for {len(args.queries)} custom queries...")
        asyncio.run(run_scrapers(args.queries, args.db, enable_mock=not args.no_mock))


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    main()
