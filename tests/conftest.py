"""
RefurbAdmin AI - Pytest Fixtures

Common fixtures for testing.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db
from app.main import app
from app.models.device import Device, DeviceStatus
from app.models.api_key import APIKey
from app.config import settings


# =============================================================================
# TEST DATABASE SETUP
# =============================================================================

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    db = async_session()
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_device_data():
    """Sample device data for testing."""
    return {
        "serial_number": "TEST123",
        "make": "Dell",
        "model": "Inspiron 3580",
        "processor": "i5-8265U",
        "ram_gb": 8,
        "ssd_gb": 256,
        "condition_grade": "Grade A",
        "status": "Ready",
        "cost_price": 4500.00,
    }


@pytest.fixture
def sample_ber_device_data():
    """Sample BER device data for testing."""
    return {
        "serial_number": "BER456",
        "make": "HP",
        "model": "EliteBook 840",
        "processor": "i7-8550U",
        "ram_gb": 16,
        "ssd_gb": 512,
        "condition_grade": "BER",
        "status": "BER",
        "cost_price": 3000.00,
    }


@pytest_asyncio.fixture
async def test_device(test_db, sample_device_data) -> Device:
    """Create a test device."""
    device = Device(**sample_device_data)
    test_db.add(device)
    await test_db.commit()
    await test_db.refresh(device)
    return device


@pytest_asyncio.fixture
async def test_ber_device(test_db, sample_ber_device_data) -> Device:
    """Create a test BER device."""
    device = Device(**sample_ber_device_data)
    test_db.add(device)
    await test_db.commit()
    await test_db.refresh(device)
    return device


@pytest_asyncio.fixture
async def test_api_key(test_db) -> APIKey:
    """Create a test API key."""
    api_key = APIKey(
        key_hash="test-api-key-12345",
        name="Test API Key",
        expires_at=APIKey.generate_expiry(days=90),
        is_active=True,
    )
    test_db.add(api_key)
    await test_db.commit()
    return api_key


# =============================================================================
# TEST CLIENT FIXTURE
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_client(test_db, test_api_key) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    
    # Override database dependency
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        app=app,
        base_url="http://test",
        headers={"X-API-Key": "test-api-key-12345"},
    ) as client:
        yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


# =============================================================================
# UTILITY FIXTURES
# =============================================================================

@pytest.fixture
def auth_headers(test_api_key):
    """Get authentication headers for API requests."""
    return {"X-API-Key": "test-api-key-12345"}


@pytest.fixture
def invalid_auth_headers():
    """Get invalid authentication headers."""
    return {"X-API-Key": "invalid-key"}
