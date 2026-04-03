"""
RefurbAdmin AI - Database Configuration

Database connection and session management.
Supports both SQLite (development) and PostgreSQL (production).
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# =============================================================================
# DATABASE ENGINE SETUP
# =============================================================================

def create_engine() -> AsyncEngine:
    """
    Create async database engine based on configuration.
    
    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    # SQLite-specific settings for development
    if settings.database_url.startswith("sqlite"):
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            connect_args={"check_same_thread": False},
        )
    else:
        # PostgreSQL settings for production
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,  # Enable connection health checks
        )
    
    return engine


# Create the async engine
async_engine = create_engine()


# =============================================================================
# SESSION FACTORY
# =============================================================================

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# BASE MODEL
# =============================================================================

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    
    pass


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

async def init_db() -> None:
    """
    Initialize database tables.
    
    Creates all tables defined in the models module.
    Safe to call multiple times.
    """
    # Import models to ensure they're registered with Base
    from app.models import device, market_price, quote, api_key
    
    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    
    Should be called on application shutdown.
    """
    await async_engine.dispose()


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency.
    
    Yields:
        AsyncSession: Database session
        
    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    db = AsyncSessionLocal()
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def get_session() -> AsyncSession:
    """
    Get a database session for use outside of FastAPI dependencies.
    
    Returns:
        AsyncSession: Database session
        
    Note:
        Caller is responsible for closing the session.
        Usage:
            async with get_session() as db:
                # do something
    """
    return AsyncSessionLocal()


def is_sqlite() -> bool:
    """
    Check if using SQLite database.
    
    Returns:
        bool: True if using SQLite
    """
    return settings.database_url.startswith("sqlite")


def is_postgresql() -> bool:
    """
    Check if using PostgreSQL database.
    
    Returns:
        bool: True if using PostgreSQL
    """
    return settings.database_url.startswith("postgresql")
