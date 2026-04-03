"""
RefurbAdmin AI - API Dependencies

Common dependencies for API endpoints (authentication, database, etc.).
"""

import logging
from datetime import datetime
from typing import Optional, AsyncGenerator

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.config import settings
from app.models.api_key import APIKey

logger = logging.getLogger(__name__)


# =============================================================================
# API KEY AUTHENTICATION
# =============================================================================

# API Key header scheme
api_key_header = APIKeyHeader(
    name=settings.api_key_header,
    auto_error=False,
)


async def get_api_key(
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Optional[APIKey]:
    """
    Validate API key from request header.
    
    Args:
        api_key: API key from header
        db: Database session
        
    Returns:
        APIKey: Validated API key object
        
    Raises:
        HTTPException: If API key is invalid or expired
    """
    if not api_key:
        return None
    
    # Look up API key by hash (in production, hash the provided key)
    # For now, we do a simple lookup
    query = select(APIKey).where(APIKey.key_hash == api_key)
    result = await db.execute(query)
    api_key_obj = result.scalar_one_or_none()
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if not api_key_obj.is_valid:
        if api_key_obj.is_expired:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is inactive",
                headers={"WWW-Authenticate": "ApiKey"},
            )
    
    # Update last used timestamp
    api_key_obj.last_used_at = datetime.utcnow()
    await db.commit()
    
    logger.debug(f"API key validated: {api_key_obj.name}")
    
    return api_key_obj


async def require_api_key(
    api_key: Optional[APIKey] = Depends(get_api_key),
) -> APIKey:
    """
    Require valid API key for endpoint.
    
    Args:
        api_key: API key from get_api_key dependency
        
    Returns:
        APIKey: Validated API key
        
    Raises:
        HTTPException: If API key is not provided
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key


async def require_admin(
    api_key: APIKey = Depends(require_api_key),
) -> APIKey:
    """
    Require admin-level API key.
    
    Args:
        api_key: API key from require_api_key dependency
        
    Returns:
        APIKey: Admin API key
        
    Raises:
        HTTPException: If API key is not admin level
    """
    # For now, we check if the key name contains 'admin'
    # In production, this would check user roles
    if "admin" not in api_key.name.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return api_key


# =============================================================================
# RATE LIMITING (Basic Implementation)
# =============================================================================

from collections import defaultdict
import time

# Simple in-memory rate limiter (use Redis in production)
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(
    request: Request,
    calls: int = 100,
    period: float = 60,
) -> bool:
    """
    Check if request is within rate limit.
    
    Args:
        request: FastAPI request
        calls: Maximum calls allowed
        period: Time period in seconds
        
    Returns:
        bool: True if within limit
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Clean old entries
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip]
        if now - t < period
    ]
    
    # Check limit
    if len(_rate_limit_store[client_ip]) >= calls:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(int(period))},
        )
    
    # Record this request
    _rate_limit_store[client_ip].append(now)
    
    return True


async def rate_limit_dependency(
    request: Request,
) -> None:
    """Rate limit dependency for endpoints."""
    check_rate_limit(request, calls=100, period=60)
