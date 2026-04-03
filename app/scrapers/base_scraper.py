"""
RefurbAdmin AI - Base Scraper

Abstract base class for web scrapers with async HTTP client,
rate limiting, retry logic, and user agent rotation.

South African Context:
- Uses South African user agents
- Respects rate limits for SA-based websites
- Handles SAST timezone
"""

import asyncio
import random
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

logger = logging.getLogger(__name__)


@dataclass
class ScrapedProduct:
    """Normalized product data structure."""
    source: str
    title: str
    price: float
    currency: str = "ZAR"
    condition: Optional[str] = None
    seller: Optional[str] = None
    seller_type: Optional[str] = None  # 'dealer' or 'private'
    location: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    availability: Optional[str] = None
    scraped_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if data.get('scraped_at') and isinstance(data['scraped_at'], datetime):
            data['scraped_at'] = data['scraped_at'].isoformat()
        return data


@dataclass
class ScrapingResult:
    """Result container for scraping operations."""
    success: bool
    source: str
    products: List[ScrapedProduct]
    error: Optional[str] = None
    total_found: int = 0
    scrape_duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'source': self.source,
            'products': [p.to_dict() for p in self.products],
            'error': self.error,
            'total_found': self.total_found,
            'scrape_duration_ms': self.scrape_duration_ms,
        }


# South African User Agents
SOUTH_AFRICAN_USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


class RateLimiter:
    """Token bucket rate limiter for respectful scraping."""

    def __init__(self, rate: float = 1.0, burst: int = 2):
        """
        Initialize rate limiter.

        Args:
            rate: Requests per second allowed
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = datetime.now()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = datetime.now()
            elapsed = (now - self.last_update).total_seconds()
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class BaseScraper(ABC):
    """
    Abstract base class for market price scrapers.

    Features:
    - Async HTTP client using httpx
    - Rate limiting with token bucket algorithm
    - Retry logic with exponential backoff
    - User agent rotation
    - Comprehensive error handling
    """

    def __init__(
        self,
        timeout: int = 30,
        rate_limit: float = 1.0,
        max_retries: int = 3,
    ):
        """
        Initialize scraper.

        Args:
            timeout: Request timeout in seconds
            rate_limit: Requests per second
            max_retries: Maximum retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(rate=rate_limit, burst=2)
        self._client: Optional[httpx.AsyncClient] = None
        self._user_agent_index = 0

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "User-Agent": self._get_user_agent(),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-ZA,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
                follow_redirects=True,
                http2=True,
            )
        return self._client

    def _get_user_agent(self) -> str:
        """Get next user agent in rotation."""
        ua = SOUTH_AFRICAN_USER_AGENTS[self._user_agent_index % len(SOUTH_AFRICAN_USER_AGENTS)]
        self._user_agent_index += 1
        return ua

    def _rotate_user_agent(self) -> None:
        """Rotate to next user agent."""
        self._user_agent_index += 1
        if self._client:
            self._client.headers["User-Agent"] = self._get_user_agent()

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def scrape(self, search_query: str) -> ScrapingResult:
        """
        Scrape prices for a search query.

        Args:
            search_query: Product search query

        Returns:
            ScrapingResult with found products
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get scraper source name."""
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)),
        reraise=True,
    )
    async def _fetch_with_retry(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """
        Fetch URL with retry logic.

        Args:
            url: URL to fetch
            params: Query parameters

        Returns:
            HTTP response

        Raises:
            RetryError: After max retries exhausted
        """
        await self.rate_limiter.acquire()
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response

    async def fetch(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[httpx.Response]:
        """
        Fetch URL with error handling.

        Args:
            url: URL to fetch
            params: Query parameters
            headers: Additional headers

        Returns:
            HTTP response or None on error
        """
        try:
            await self.rate_limiter.acquire()
            request_headers = {**self.client.headers, **(headers or {})}
            response = await self.client.get(url, params=params, headers=request_headers)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout fetching {url}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.warning(f"Request error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    def validate_price(self, price: Any) -> bool:
        """Validate price value."""
        try:
            price_float = float(price)
            return 0 < price_float < 1_000_000  # Reasonable price range in ZAR
        except (TypeError, ValueError):
            return False

    def clean_text(self, text: str) -> str:
        """Clean scraped text."""
        if not text:
            return ""
        return " ".join(text.split())

    def parse_price(self, price_str: str) -> Optional[float]:
        """
        Parse price string to float.

        Handles South African price formats:
        - R 12,999
        - R12,999
        - 12,999
        - 12999
        """
        if not price_str:
            return None

        # Remove currency symbols, commas, and spaces
        cleaned = str(price_str).replace("R", "").replace(",", "").replace(" ", "").strip()

        try:
            return float(cleaned)
        except ValueError:
            logger.debug(f"Could not parse price: {price_str}")
            return None

    def parse_condition(self, condition_text: str) -> str:
        """
        Normalize condition text.

        Args:
            condition_text: Raw condition text

        Returns:
            Normalized condition string
        """
        if not condition_text:
            return "unknown"

        text = condition_text.lower()

        if any(word in text for word in ["new", "brand new", "sealed"]):
            return "new"
        elif any(word in text for word in ["refurbished", "renewed", "reconditioned", "recertified"]):
            return "refurbished"
        elif any(word in text for word in ["used", "pre-owned", "second hand", "open box"]):
            return "used"
        elif any(word in text for word in ["faulty", "broken", "spares", "repair"]):
            return "faulty"
        else:
            return "unknown"

    def get_timestamp(self) -> datetime:
        """Get current timestamp in SAST."""
        return datetime.utcnow()

    def create_scraped_product(
        self,
        title: str,
        price: float,
        condition: Optional[str] = None,
        seller: Optional[str] = None,
        seller_type: Optional[str] = None,
        location: Optional[str] = None,
        url: Optional[str] = None,
        image_url: Optional[str] = None,
        specs: Optional[Dict[str, Any]] = None,
        availability: Optional[str] = None,
    ) -> ScrapedProduct:
        """Create a normalized ScrapedProduct."""
        return ScrapedProduct(
            source=self.get_source_name(),
            title=self.clean_text(title),
            price=price,
            currency="ZAR",
            condition=self.parse_condition(condition) if condition else None,
            seller=self.clean_text(seller) if seller else None,
            seller_type=seller_type,
            location=self.clean_text(location) if location else None,
            url=url,
            image_url=image_url,
            specs=specs,
            availability=availability,
            scraped_at=self.get_timestamp(),
        )
