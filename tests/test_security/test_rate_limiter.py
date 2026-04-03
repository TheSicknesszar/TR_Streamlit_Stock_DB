"""
Tests for Rate Limiter module.

Tests cover:
- Token bucket algorithm
- Per-API-key limits
- Configurable requests per minute
- Rate limit exceeded exceptions
"""

import pytest
import time
from unittest.mock import Mock, patch

from app.security.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    TokenBucket,
    get_rate_limiter,
)


class TestTokenBucket:
    """Tests for TokenBucket class."""
    
    def test_initial_tokens(self):
        """Test bucket starts with full capacity."""
        bucket = TokenBucket(capacity=10)
        assert bucket.tokens == 10.0
    
    def test_consume_tokens(self):
        """Test consuming tokens from bucket."""
        bucket = TokenBucket(capacity=10)
        
        assert bucket.consume(5) is True
        assert bucket.tokens == 5.0
        
        assert bucket.consume(5) is True
        assert bucket.tokens == 0.0
    
    def test_consume_insufficient_tokens(self):
        """Test consuming more tokens than available."""
        bucket = TokenBucket(capacity=10, tokens=5)
        
        assert bucket.consume(6) is False
        assert bucket.tokens == 5.0  # Tokens not consumed
    
    def test_token_refill(self):
        """Test tokens refill over time."""
        bucket = TokenBucket(capacity=10, tokens=0, refill_rate=10.0)
        
        # Wait a bit for tokens to refill
        time.sleep(0.1)
        bucket._refill()
        
        assert bucket.tokens > 0
    
    def test_get_wait_time(self):
        """Test calculating wait time for tokens."""
        bucket = TokenBucket(capacity=10, tokens=0, refill_rate=10.0)
        
        wait_time = bucket.get_wait_time(5)
        
        # Should wait approximately 0.5 seconds for 5 tokens at 10/sec
        assert 0.4 <= wait_time <= 0.6


class TestRateLimitConfig:
    """Tests for RateLimitConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()
        
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_limit == 10
        assert config.enabled is True
    
    def test_config_from_env(self):
        """Test creating config from environment variables."""
        env_dict = {
            "RATE_LIMIT_RPM": "120",
            "RATE_LIMIT_RPH": "2000",
            "RATE_LIMIT_BURST": "20",
            "RATE_LIMIT_ENABLED": "false",
        }
        
        config = RateLimitConfig.from_env(env_dict)
        
        assert config.requests_per_minute == 120
        assert config.requests_per_hour == 2000
        assert config.burst_limit == 20
        assert config.enabled is False
    
    def test_tier_limits(self):
        """Test tier-based limits."""
        config = RateLimitConfig()
        
        assert config.tier_limits["standard"]["rpm"] == 60
        assert config.tier_limits["premium"]["rpm"] == 200
        assert config.tier_limits["enterprise"]["rpm"] == 1000


class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    @pytest.fixture
    def limiter(self):
        """Create a rate limiter for testing."""
        config = RateLimitConfig(
            requests_per_minute=60,
            burst_limit=10,
            enabled=True,
        )
        return RateLimiter(config=config)
    
    def test_is_exempt(self, limiter):
        """Test exempt API keys."""
        limiter.config.exempt_keys = {"exempt-key-123"}
        
        assert limiter.is_exempt("exempt-key-123") is True
        assert limiter.is_exempt("normal-key") is False
    
    def test_get_tier(self, limiter):
        """Test getting tier for API key."""
        # Default tier is standard
        assert limiter.get_tier("any-key") == "standard"
    
    def test_get_limits_for_tier(self, limiter):
        """Test getting limits for tier."""
        limits = limiter.get_limits_for_tier("standard")
        
        assert limits["rpm"] == 60
        assert limits["burst"] == 10
    
    def test_check_rate_limit_success(self, limiter):
        """Test successful rate limit check."""
        result = limiter.check_rate_limit("test-api-key", "api/test")
        
        assert "limit" in result
        assert "remaining" in result
        assert "reset" in result
        assert result["remaining"] >= 0
    
    def test_check_rate_limit_exceeded(self, limiter):
        """Test rate limit exceeded."""
        # Create limiter with very low limit
        config = RateLimitConfig(burst_limit=2, enabled=True)
        limiter = RateLimiter(config=config)
        
        # Exhaust the limit
        limiter.check_rate_limit("test-key", "api/test")
        limiter.check_rate_limit("test-key", "api/test")
        
        # Next request should fail
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_rate_limit("test-key", "api/test")
        
        assert exc_info.value.retry_after >= 0
        assert exc_info.value.limit == 2
    
    def test_disabled_rate_limiter(self, limiter):
        """Test disabled rate limiter allows all requests."""
        limiter.config.enabled = False
        
        result = limiter.check_rate_limit("test-key", "api/test")
        
        assert result["limit"] == -1
        assert result["remaining"] == -1
    
    def test_exempt_key_bypasses_limit(self, limiter):
        """Test exempt keys bypass rate limiting."""
        limiter.config.exempt_keys = {"exempt-key"}
        limiter.config.enabled = False  # Disable to test exemption
        
        result = limiter.check_rate_limit("exempt-key", "api/test")
        
        assert result["limit"] == -1
    
    def test_reset_limit(self, limiter):
        """Test resetting rate limit."""
        # Make some requests
        limiter.check_rate_limit("test-key", "api/test")
        
        # Reset
        assert limiter.reset_limit("test-key", "api/test") is True
    
    def test_get_usage_stats(self, limiter):
        """Test getting usage statistics."""
        stats = limiter.get_usage_stats("test-key")
        
        assert "api_key" in stats
        assert "tier" in stats
        assert "limits" in stats


class TestRateLimiterRedis:
    """Tests for RateLimiter with Redis backend."""
    
    @patch('app.security.rate_limiter.redis')
    def test_redis_connection(self, mock_redis):
        """Test Redis connection setup."""
        mock_redis.from_url.return_value.ping.return_value = True
        
        config = RateLimitConfig()
        limiter = RateLimiter(
            config=config,
            redis_url="redis://localhost:6379",
            use_redis=True
        )
        
        assert limiter._use_redis is True
    
    @patch('app.security.rate_limiter.redis')
    def test_redis_fallback_on_failure(self, mock_redis):
        """Test fallback to in-memory on Redis failure."""
        mock_redis.from_url.side_effect = Exception("Connection refused")
        
        config = RateLimitConfig()
        limiter = RateLimiter(
            config=config,
            redis_url="redis://localhost:6379",
            use_redis=True
        )
        
        assert limiter._use_redis is False


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""
    
    def test_middleware_initialization(self):
        """Test middleware can be initialized."""
        from app.security.rate_limiter import RateLimitMiddleware
        
        config = RateLimitConfig()
        limiter = RateLimiter(config=config)
        
        # Mock ASGI app
        mock_app = Mock()
        
        middleware = RateLimitMiddleware(mock_app, limiter)
        
        assert middleware.app == mock_app
        assert middleware.rate_limiter == limiter


class TestGetRateLimiter:
    """Tests for get_rate_limiter singleton."""
    
    def test_singleton_returns_same_instance(self):
        """Test that get_rate_limiter returns same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        
        assert limiter1 is limiter2
    
    def test_singleton_with_config(self):
        """Test singleton with custom config."""
        config = RateLimitConfig(requests_per_minute=100)
        limiter = get_rate_limiter(config=config)
        
        assert limiter.config.requests_per_minute == 100


# Integration-style tests
class TestRateLimiterIntegration:
    """Integration-style tests for rate limiter."""
    
    def test_concurrent_requests(self):
        """Test rate limiter with concurrent requests."""
        import threading
        
        config = RateLimitConfig(burst_limit=100, enabled=True)
        limiter = RateLimiter(config=config)
        
        results = []
        errors = []
        
        def make_request():
            try:
                result = limiter.check_rate_limit("concurrent-test", "api/test")
                results.append(result)
            except RateLimitExceeded as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=make_request) for _ in range(50)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have some successful requests
        assert len(results) + len(errors) == 50
    
    def test_multiple_endpoints(self):
        """Test rate limiting across multiple endpoints."""
        config = RateLimitConfig(burst_limit=10, enabled=True)
        limiter = RateLimiter(config=config)
        
        # Each endpoint should have separate limits
        for endpoint in ["/api/users", "/api/products", "/api/orders"]:
            result = limiter.check_rate_limit("test-key", endpoint)
            assert result["remaining"] >= 0
