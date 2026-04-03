"""
RefurbAdmin AI - PriceCheck.co.za Scraper

Scraper for PriceCheck.co.za - South African price comparison website.
Extracts laptop prices, conditions, and seller information.

Note: This scraper includes mock data fallback for testing when
live scraping is blocked or rate-limited.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup
import httpx

from .base_scraper import BaseScraper, ScrapingResult, ScrapedProduct

logger = logging.getLogger(__name__)


class PriceCheckScraper(BaseScraper):
    """
    Scraper for PriceCheck.co.za.

    PriceCheck is South Africa's leading price comparison website,
    aggregating prices from multiple local retailers.
    """

    BASE_URL = "https://www.pricecheck.co.za"
    SEARCH_URL = "https://www.pricecheck.co.za/search"

    def __init__(self, timeout: int = 30, rate_limit: float = 0.5, max_retries: int = 3):
        """
        Initialize PriceCheck scraper.

        Args:
            timeout: Request timeout in seconds
            rate_limit: Requests per second (0.5 = 1 request per 2 seconds)
            max_retries: Maximum retry attempts
        """
        super().__init__(timeout=timeout, rate_limit=rate_limit, max_retries=max_retries)
        self._mock_data_enabled = False

    def get_source_name(self) -> str:
        """Get scraper source name."""
        return "PriceCheck.co.za"

    def enable_mock_data(self, enabled: bool = True) -> None:
        """Enable/disable mock data fallback."""
        self._mock_data_enabled = enabled

    async def scrape(self, search_query: str) -> ScrapingResult:
        """
        Scrape prices from PriceCheck for a search query.

        Args:
            search_query: Product search query (e.g., "Dell Latitude 5420")

        Returns:
            ScrapingResult with found products
        """
        start_time = datetime.now()
        products: List[ScrapedProduct] = []

        try:
            logger.info(f"PriceCheck: Searching for '{search_query}'")

            # Build search URL
            params = {
                "search": search_query,
                "category": "computers_laptops",  # Filter to laptops
            }

            response = await self.fetch(self.SEARCH_URL, params=params)

            if response is None:
                logger.warning("PriceCheck: No response received")
                if self._mock_data_enabled:
                    products = self._get_mock_data(search_query)
                    return self._create_result(True, products, start_time)
                return self._create_result(False, [], start_time, "No response from PriceCheck")

            # Parse HTML
            products = self._parse_search_results(response.text, search_query)

            # Handle pagination (get up to 3 pages)
            if products:
                for page in range(2, 4):
                    await asyncio.sleep(2)  # Respect rate limits
                    params["page"] = page
                    response = await self.fetch(self.SEARCH_URL, params=params)
                    if response and response.status_code == 200:
                        page_products = self._parse_search_results(response.text, search_query)
                        if page_products:
                            products.extend(page_products)
                        else:
                            break  # No more results
                    else:
                        break

            if not products and self._mock_data_enabled:
                logger.info("PriceCheck: Using mock data fallback")
                products = self._get_mock_data(search_query)

            success = len(products) > 0
            return self._create_result(success, products, start_time)

        except Exception as e:
            logger.error(f"PriceCheck: Error scraping: {e}")
            if self._mock_data_enabled:
                products = self._get_mock_data(search_query)
                return self._create_result(True, products, start_time)
            return self._create_result(False, [], start_time, str(e))

    def _parse_search_results(self, html: str, search_query: str) -> List[ScrapedProduct]:
        """
        Parse search results HTML.

        Args:
            html: HTML content
            search_query: Original search query

        Returns:
            List of ScrapedProduct
        """
        products = []
        soup = BeautifulSoup(html, "lxml")

        # Find product listings - adjust selectors based on actual PriceCheck HTML structure
        # Note: These selectors are based on typical PriceCheck structure
        product_cards = soup.select("li.offer, div.product, div.offer-card, .product-card")

        for card in product_cards[:20]:  # Limit to 20 per page
            try:
                product = self._parse_product_card(card, search_query)
                if product and self.validate_price(product.price):
                    products.append(product)
            except Exception as e:
                logger.debug(f"PriceCheck: Error parsing product card: {e}")
                continue

        return products

    def _parse_product_card(self, card: Any, search_query: str) -> Optional[ScrapedProduct]:
        """
        Parse individual product card.

        Args:
            card: BeautifulSoup element
            search_query: Original search query

        Returns:
            ScrapedProduct or None
        """
        # Extract title
        title_elem = card.select_one("h3 a, h2 a, .product-title a, .title a")
        if not title_elem:
            return None
        title = title_elem.get_text(strip=True)

        # Skip if title doesn't match search query somewhat
        if search_query.lower() not in title.lower():
            return None

        # Extract price
        price_elem = card.select_one(".price, .offer-price, .product-price, [class*='price']")
        price_text = price_elem.get_text(strip=True) if price_elem else ""
        price = self.parse_price(price_text)

        if price is None:
            return None

        # Extract seller
        seller_elem = card.select_one(".seller, .shop-name, .merchant, [class*='seller']")
        seller = seller_elem.get_text(strip=True) if seller_elem else None

        # Extract URL
        link_elem = card.select_one("a[href]")
        url = None
        if link_elem and link_elem.get("href"):
            href = link_elem["href"]
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        # Extract image
        img_elem = card.select_one("img[src]")
        image_url = img_elem.get("src") if img_elem else None

        # Extract condition from title or description
        condition = self._extract_condition(title)

        return self.create_scraped_product(
            title=title,
            price=price,
            condition=condition,
            seller=seller,
            seller_type="dealer",  # PriceCheck lists registered dealers
            url=url,
            image_url=image_url,
            availability="In Stock",
        )

    def _extract_condition(self, title: str) -> str:
        """Extract condition from product title."""
        title_lower = title.lower()
        if "refurbished" in title_lower or "renewed" in title_lower:
            return "refurbished"
        elif "used" in title_lower or "pre-owned" in title_lower:
            return "used"
        elif "new" in title_lower:
            return "new"
        return "unknown"

    def _create_result(
        self,
        success: bool,
        products: List[ScrapedProduct],
        start_time: datetime,
        error: Optional[str] = None,
    ) -> ScrapingResult:
        """Create ScrapingResult."""
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        return ScrapingResult(
            success=success,
            source=self.get_source_name(),
            products=products,
            error=error,
            total_found=len(products),
            scrape_duration_ms=duration,
        )

    def _get_mock_data(self, search_query: str) -> List[ScrapedProduct]:
        """
        Generate mock data for testing.

        Args:
            search_query: Product search query

        Returns:
            List of mock ScrapedProduct
        """
        logger.info(f"PriceCheck: Generating mock data for '{search_query}'")

        # South African retailers on PriceCheck
        retailers = [
            "Takealot", "Incredible Connection", "Evetech", "Wootware",
            "Computer Mania", "Rebel Tech", "Afritech", "Laptop Outlet"
        ]

        # Generate realistic mock prices based on search query
        base_price = self._estimate_base_price(search_query)

        mock_products = []
        for i, retailer in enumerate(retailers[:5]):
            price_variation = random.uniform(0.9, 1.15)  # ±10% variation
            price = round(base_price * price_variation, 2)

            mock_products.append(self.create_scraped_product(
                title=f"{search_query} - {retailer}",
                price=price,
                condition="refurbished" if i % 3 == 0 else "new",
                seller=retailer,
                seller_type="dealer",
                location="Johannesburg, Gauteng",
                url=f"https://www.pricecheck.co.za/product/{i}",
                availability="In Stock",
            ))

        return mock_products

    def _estimate_base_price(self, search_query: str) -> float:
        """Estimate base price from search query."""
        query_lower = search_query.lower()

        # Premium brands
        if any(brand in query_lower for brand in ["thinkpad", "dell precision", "hp zbook", "macbook"]):
            return random.uniform(12000, 25000)
        # Business class
        elif any(brand in query_lower for brand in ["latitude", "elitebook", "probook", "thinkbook"]):
            return random.uniform(8000, 15000)
        # Consumer class
        else:
            return random.uniform(5000, 10000)


# Import random for mock data
import random
