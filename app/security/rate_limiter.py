"""
Rate Limiter for RefurbAdmin AI.

Implements token bucket algorithm for API rate limiting with support for:
- Per-API-key limits
- Configurable requests per minute
- Redis backend for production
- In-memory backend for development

South African Context:
- Default limits suitable for SA business hours traffic patterns
- Configurable for different tiers (standard, premium, enterprise)
"""

import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from collections import defaultdict
from threading import Lock

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded", 
        retry_after: int = 60,
        limit: int = 100,
        remaining: int = 0
    ):
        self.message = message
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        super().__init__(self.message)


@dataclass
class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    capacity: int  # Maximum tokens
    tokens: float = field(default=0.0)
    last_update: float = field(default_factory=time.time)
    refill_rate: float = field(default=1.0)  # Tokens per second
    
    def __post_init__(self):
        if self.tokens == 0.0:
            self.tokens = float(self.capacity)
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_update = now
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait until tokens are available."""
        self._refill()
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.refill_rate


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    enabled: bool = True
    
    # Tier-based limits (South African business context)
    tier_limits: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        "standard": {"rpm": 60, "rph": 1000, "burst": 10},
        "premium": {"rpm": 200, "rph": 5000, "burst": 30},
        "enterprise": {"rpm": 1000, "rph": 50000, "burst": 100},
    })
    
    # Exempt API keys (for internal services)
    exempt_keys: set = field(default_factory=set)
    
    @classmethod
    def from_env(cls, env_dict: Dict[str, Any]) -> "RateLimitConfig":
        """Create config from environment variables."""
        return cls(
            requests_per_minute=int(env_dict.get("RATE_LIMIT_RPM", 60)),
            requests_per_hour=int(env_dict.get("RATE_LIMIT_RPH", 1000)),
            burst_limit=int(env_dict.get("RATE_LIMIT_BURST", 10)),
            enabled=env_dict.get("RATE_LIMIT_ENABLED", "true").lower() == "true",
        )


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    
    Supports both in-memory and Redis backends.
    Redis is recommended for production with multiple instances.
    """
    
    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        redis_url: Optional[str] = None,
        use_redis: bool = False
    ):
        self.config = config or RateLimitConfig()
        self._lock = Lock()
        self._buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(capacity=self.config.burst_limit)
        )
        
        # Redis setup for production
        self._redis: Optional[redis.Redis] = None
        self._use_redis = use_redis and REDIS_AVAILABLE
        
        if self._use_redis and redis_url:
            try:
                self._redis = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                self._redis.ping()
                logger.info("Redis rate limiter connected successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, falling back to in-memory: {e}")
                self._use_redis = False
    
    def is_exempt(self, api_key: str) -> bool:
        """Check if API key is exempt from rate limiting."""
        return api_key in self.config.exempt_keys
    
    def get_tier(self, api_key: str) -> str:
        """
        Get the tier for an API key.
        
        In production, this would query a database.
        For now, returns 'standard' by default.
        """
        # Placeholder - implement based on your API key storage
        return "standard"
    
    def get_limits_for_tier(self, tier: str) -> Dict[str, int]:
        """Get rate limits for a specific tier."""
        return self.config.tier_limits.get(
            tier, 
            self.config.tier_limits["standard"]
        )
    
    def _get_bucket_key(self, api_key: str, endpoint: str) -> str:
        """Generate bucket key for Redis."""
        return f"ratelimit:{api_key}:{endpoint}"
    
    def check_rate_limit(
        self,
        api_key: str,
        endpoint: str = "api",
        cost: int = 1
    ) -> Dict[str, Any]:
        """
        Check if request is within rate limit.
        
        Args:
            api_key: The API key making the request
            endpoint: The API endpoint being accessed
            cost: The cost of this request in tokens
            
        Returns:
            Dict with limit, remaining, reset time
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        if not self.config.enabled:
            return {"limit": -1, "remaining": -1, "reset": 0}
        
        if self.is_exempt(api_key):
            return {"limit": -1, "remaining": -1, "reset": 0}
        
        tier = self.get_tier(api_key)
        limits = self.get_limits_for_tier(tier)
        
        if self._use_redis and self._redis:
            return self._check_redis(api_key, endpoint, cost, limits)
        else:
            return self._check_memory(api_key, endpoint, cost, limits)
    
    def _check_memory(
        self,
        api_key: str,
        endpoint: str,
        cost: int,
        limits: Dict[str, int]
    ) -> Dict[str, Any]:
        """Check rate limit using in-memory storage."""
        with self._lock:
            bucket_key = f"{api_key}:{endpoint}"
            bucket = self._buckets[bucket_key]
            
            # Update bucket capacity based on tier
            if bucket.capacity != limits["burst"]:
                bucket.capacity = limits["burst"]
                bucket.refill_rate = limits["rpm"] / 60.0
            
            if bucket.consume(cost):
                remaining = int(bucket.tokens)
                reset_time = int(bucket.get_wait_time(cost))
                
                return {
                    "limit": limits["rpm"],
                    "remaining": remaining,
                    "reset": reset_time,
                    "tier": tier
                }
            else:
                wait_time = int(bucket.get_wait_time(cost))
                raise RateLimitExceeded(
                    message=f"Rate limit exceeded for tier '{tier}'",
                    retry_after=wait_time,
                    limit=limits["rpm"],
                    remaining=0
                )
    
    def _check_redis(
        self,
        api_key: str,
        endpoint: str,
        cost: int,
        limits: Dict[str, int]
    ) -> Dict[str, Any]:
        """Check rate limit using Redis storage."""
        try:
            key = self._get_bucket_key(api_key, endpoint)
            now = time.time()
            window = 60  # 1 minute window
            
            # Use Redis pipeline for atomic operations
            pipe = self._redis.pipeline()
            
            # Get current count
            current = self._redis.get(key)
            current = int(current) if current else 0
            
            # Check limit
            if current + cost <= limits["rpm"]:
                # Increment counter
                pipe.incrby(key, cost)
                pipe.expire(key, window)
                pipe.execute()
                
                return {
                    "limit": limits["rpm"],
                    "remaining": limits["rpm"] - current - cost,
                    "reset": window,
                    "tier": tier
                }
            else:
                ttl = self._redis.ttl(key)
                raise RateLimitExceeded(
                    message=f"Rate limit exceeded for tier '{tier}'",
                    retry_after=max(1, ttl),
                    limit=limits["rpm"],
                    remaining=0
                )
                
        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # Fallback to allowing request on Redis failure
            return {
                "limit": limits["rpm"],
                "remaining": limits["rpm"],
                "reset": 60,
                "tier": tier,
                "warning": "Redis unavailable"
            }
    
    def get_usage_stats(self, api_key: str) -> Dict[str, Any]:
        """Get usage statistics for an API key."""
        stats = {
            "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
            "tier": self.get_tier(api_key),
            "limits": self.get_limits_for_tier(self.get_tier(api_key)),
            "exempt": self.is_exempt(api_key),
        }
        return stats
    
    def reset_limit(self, api_key: str, endpoint: Optional[str] = None) -> bool:
        """
        Reset rate limit for an API key.
        
        Args:
            api_key: The API key to reset
            endpoint: Specific endpoint or None for all
            
        Returns:
            True if reset was successful
        """
        if self._use_redis and self._redis:
            try:
                if endpoint:
                    key = self._get_bucket_key(api_key, endpoint)
                    self._redis.delete(key)
                else:
                    pattern = self._get_bucket_key(api_key, "*")
                    keys = self._redis.keys(pattern)
                    if keys:
                        self._redis.delete(*keys)
                return True
            except redis.RedisError as e:
                logger.error(f"Redis error resetting limit: {e}")
                return False
        else:
            with self._lock:
                if endpoint:
                    bucket_key = f"{api_key}:{endpoint}"
                    if bucket_key in self._buckets:
                        del self._buckets[bucket_key]
                else:
                    keys_to_delete = [
                        k for k in self._buckets.keys() 
                        if k.startswith(f"{api_key}:")
                    ]
                    for key in keys_to_delete:
                        del self._buckets[key]
            return True


# Middleware for FastAPI
class RateLimitMiddleware:
    """
    FastAPI middleware for rate limiting.
    
    Usage:
        app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
    """
    
    def __init__(self, app, rate_limiter: RateLimiter):
        self.app = app
        self.rate_limiter = rate_limiter
    
    async def __call__(self, scope, receive, send):
        from fastapi import Request
        from fastapi.responses import JSONResponse
        
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        request = Request(scope, receive)
        
        # Get API key from headers or query params
        api_key = (
            request.headers.get("X-API-Key") or
            request.headers.get("Authorization", "").replace("Bearer ", "") or
            request.query_params.get("api_key", "anonymous")
        )
        
        endpoint = request.url.path
        
        try:
            result = self.rate_limiter.check_rate_limit(api_key, endpoint)
            
            # Add rate limit headers to response
            async def send_with_headers(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.extend([
                        (b"x-ratelimit-limit", str(result["limit"]).encode()),
                        (b"x-ratelimit-remaining", str(result["remaining"]).encode()),
                        (b"x-ratelimit-reset", str(result["reset"]).encode()),
                    ])
                    message["headers"] = headers
                await send(message)
            
            return await self.app(scope, receive, send_with_headers)
            
        except RateLimitExceeded as e:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": e.message,
                    "retry_after": e.retry_after,
                    "limit": e.limit,
                },
                headers={
                    "Retry-After": str(e.retry_after),
                    "X-RateLimit-Limit": str(e.limit),
                    "X-RateLimit-Remaining": "0",
                }
            )


# Singleton instance
_rate_limiter_instance: Optional[RateLimiter] = None


def get_rate_limiter(
    config: Optional[RateLimitConfig] = None,
    redis_url: Optional[str] = None,
    use_redis: bool = False
) -> RateLimiter:
    """Get or create the rate limiter singleton."""
    global _rate_limiter_instance
    
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter(
            config=config,
            redis_url=redis_url,
            use_redis=use_redis
        )
    
    return _rate_limiter_instance
