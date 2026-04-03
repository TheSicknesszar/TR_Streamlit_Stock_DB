#!/usr/bin/env python
"""
RefurbAdmin AI - Seed Market Data Script

Script to seed initial market price data for testing and development.
Creates realistic mock data for common laptop models in the South African market.

Usage:
    python scripts/seed_market_data.py
    
This script is useful for:
- Initial database setup
- Testing the frontend without running live scrapers
- Development and demonstration purposes
"""

import asyncio
import logging
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


# South African laptop market data templates
LAPTOP_MODELS = [
    {
        "search_query": "Dell Latitude 5420",
        "base_price": 11500,
        "ram_options": [8, 16],
        "storage_options": [256, 512],
    },
    {
        "search_query": "Dell Latitude 7490",
        "base_price": 8500,
        "ram_options": [8, 16],
        "storage_options": [256, 512],
    },
    {
        "search_query": "HP EliteBook 840 G7",
        "base_price": 12000,
        "ram_options": [8, 16],
        "storage_options": [256, 512],
    },
    {
        "search_query": "HP EliteBook 850 G5",
        "base_price": 9500,
        "ram_options": [8, 16],
        "storage_options": [256, 512],
    },
    {
        "search_query": "Lenovo ThinkPad T14",
        "base_price": 13500,
        "ram_options": [8, 16, 32],
        "storage_options": [256, 512, 1024],
    },
    {
        "search_query": "Lenovo ThinkPad X1 Carbon",
        "base_price": 18000,
        "ram_options": [16, 32],
        "storage_options": [512, 1024],
    },
    {
        "search_query": "Dell Precision 5540",
        "base_price": 22000,
        "ram_options": [16, 32],
        "storage_options": [512, 1024],
    },
    {
        "search_query": "HP ZBook 15",
        "base_price": 25000,
        "ram_options": [16, 32],
        "storage_options": [512, 1024],
    },
    {
        "search_query": "MacBook Pro 13 inch",
        "base_price": 20000,
        "ram_options": [8, 16],
        "storage_options": [256, 512],
    },
    {
        "search_query": "Asus ZenBook 14",
        "base_price": 10000,
        "ram_options": [8, 16],
        "storage_options": [512],
    },
]

# South African retailers
RETAILERS = {
    "PriceCheck.co.za": {
        "sellers": ["Incredible Connection", "Evetech", "Wootware", "Computer Mania", "Rebel Tech"],
        "price_variance": (0.95, 1.10),
    },
    "Takealot.com": {
        "sellers": ["Takealot"],
        "price_variance": (0.98, 1.08),
    },
    "Gumtree.co.za": {
        "sellers": ["Private Seller", "TechDeals ZA", "Laptop Outlet", "PC Warehouse"],
        "price_variance": (0.80, 1.00),
    },
}

# South African locations
LOCATIONS = [
    "Johannesburg, Gauteng",
    "Pretoria, Gauteng",
    "Cape Town, Western Cape",
    "Durban, KwaZulu-Natal",
    "Port Elizabeth, Eastern Cape",
    "Bloemfontein, Free State",
]


def generate_market_data(
    model: Dict[str, Any],
    days_ago: int = 0,
) -> Dict[str, Any]:
    """
    Generate realistic market data for a laptop model.

    Args:
        model: Model configuration
        days_ago: How many days ago to timestamp the data

    Returns:
        Market data dictionary
    """
    base_price = model["base_price"]
    search_query = model["search_query"]

    # Generate prices by source
    price_by_source = {}
    all_prices = []

    for source, config in RETAILERS.items():
        source_prices = []
        num_listings = random.randint(3, 8)

        for _ in range(num_listings):
            variance = random.uniform(*config["price_variance"])
            price = round(base_price * variance, 2)
            source_prices.append(price)
            all_prices.append(price)

        price_by_source[source] = source_prices

    # Calculate statistics
    median_price = sorted(all_prices)[len(all_prices) // 2]
    min_price = min(all_prices)
    max_price = max(all_prices)
    average_price = sum(all_prices) / len(all_prices)

    # Listings by condition
    listings_by_condition = {
        "refurbished": random.randint(8, 15),
        "used": random.randint(5, 10),
        "new": random.randint(2, 5),
    }

    scraped_at = datetime.now() - timedelta(days=days_ago)

    return {
        "search_query": search_query,
        "median_price": round(median_price, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "average_price": round(average_price, 2),
        "total_listings": len(all_prices),
        "price_by_source": price_by_source,
        "listings_by_condition": listings_by_condition,
        "sources_scraped": list(RETAILERS.keys()),
        "sources_failed": [],
        "scraped_at": scraped_at,
    }


async def seed_database(
    db_url: str = "sqlite+aiosqlite:///./data/refurbadmin.db",
    clear_existing: bool = False,
) -> None:
    """
    Seed the database with market data.

    Args:
        db_url: Database URL
        clear_existing: Whether to clear existing data first
    """
    from app.models.market_price import MarketPrice

    logger.info(f"Seeding database: {db_url}")

    # Create database session
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Clear existing data if requested
        if clear_existing:
            logger.info("Clearing existing market price data...")
            from sqlalchemy import delete
            await session.execute(delete(MarketPrice))
            await session.commit()

        # Generate and insert data
        records_to_insert = []

        for model in LAPTOP_MODELS:
            logger.info(f"Generating data for: {model['search_query']}")

            # Generate current data
            market_data = generate_market_data(model, days_ago=0)
            record = MarketPrice.from_market_data(
                market_data["search_query"],
                type("MarketPriceData", (), market_data)(),
            )
            records_to_insert.append(record)

            # Generate historical data (past 7 days)
            for days_ago in range(1, 8):
                historical_data = generate_market_data(model, days_ago=days_ago)
                record = MarketPrice.from_market_data(
                    historical_data["search_query"],
                    type("MarketPriceData", (), historical_data)(),
                )
                records_to_insert.append(record)

        # Bulk insert
        logger.info(f"Inserting {len(records_to_insert)} records...")
        session.add_all(records_to_insert)
        await session.commit()

    logger.info("✅ Database seeded successfully!")


async def show_summary(
    db_url: str = "sqlite+aiosqlite:///./data/refurbadmin.db",
) -> None:
    """
    Show summary of seeded data.

    Args:
        db_url: Database URL
    """
    from sqlalchemy import select, func
    from app.models.market_price import MarketPrice

    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Count total records
        stmt = select(func.count(MarketPrice.id))
        result = await session.execute(stmt)
        total = result.scalar()

        # Count by search query
        stmt = select(
            MarketPrice.search_query,
            func.count(MarketPrice.id),
            func.avg(MarketPrice.median_price),
        ).group_by(MarketPrice.search_query)
        result = await session.execute(stmt)
        by_query = result.all()

        # Latest data
        stmt = select(MarketPrice).order_by(MarketPrice.scraped_at.desc()).limit(5)
        result = await session.execute(stmt)
        latest = result.scalars().all()

    print("\n" + "=" * 60)
    print("MARKET DATA SUMMARY")
    print("=" * 60)
    print(f"Total records: {total}")
    print(f"Unique queries: {len(by_query)}")
    print()

    print("By Model:")
    print("-" * 60)
    for query, count, avg_price in by_query:
        print(f"  {query}:")
        print(f"    Records: {count}, Avg Price: R {avg_price:,.2f}")

    print()
    print("Latest Entries:")
    print("-" * 60)
    for record in latest:
        print(f"  {record.search_query}: R {record.median_price:,.2f} ({record.scraped_at})")

    print("=" * 60)


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed market price data for RefurbAdmin AI",
    )

    parser.add_argument(
        "--db",
        default="sqlite+aiosqlite:///./data/refurbadmin.db",
        help="Database URL",
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before seeding",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary after seeding",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Run seeding
    logger.info("Starting market data seeding...")
    asyncio.run(seed_database(args.db, args.clear))

    # Show summary
    if args.summary:
        asyncio.run(show_summary(args.db))


if __name__ == "__main__":
    main()
