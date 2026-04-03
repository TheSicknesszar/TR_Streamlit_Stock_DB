"""
RefurbAdmin AI - Takealot.com Scraper

Scraper for Takealot.com - South Africa's largest online retailer.
Extracts refurbished laptop prices, specifications, and availability.

Note: This scraper includes mock data fallback for testing when
live scraping is blocked or rate-limited.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScrapingResult, ScrapedProduct

logger = logging.getLogger(__name__)


class TakealotScraper(BaseScraper):
    """
    Scraper for Takealot.com.

    Takealot is South Africa's largest online retailer with a growing
    refurbished electronics section.
    """

    BASE_URL = "https://www.takealot.com"
    SEARCH_URL = "https://www.takealot.com/palsearch"

    def __init__(self, timeout: int = 30, rate_limit: float = 0.5, max_retries: int = 3):
        """
        Initialize Takealot scraper.

        Args:
            timeout: Request timeout in seconds
            rate_limit: Requests per second (0.5 = 1 request per 2 seconds)
            max_retries: Maximum retry attempts
        """
        super().__init__(timeout=timeout, rate_limit=rate_limit, max_retries=max_retries)
        self._mock_data_enabled = False

    def get_source_name(self) -> str:
        """Get scraper source name."""
        return "Takealot.com"

    def enable_mock_data(self, enabled: bool = True) -> None:
        """Enable/disable mock data fallback."""
        self._mock_data_enabled = enabled

    async def scrape(self, search_query: str) -> ScrapingResult:
        """
        Scrape prices from Takealot for a search query.

        Args:
            search_query: Product search query (e.g., "Dell Latitude 5420")

        Returns:
            ScrapingResult with found products
        """
        start_time = datetime.now()
        products: List[ScrapedProduct] = []

        try:
            logger.info(f"Takealot: Searching for '{search_query}'")

            # Build search URL
            params = {
                "searchterm": search_query,
            }

            response = await self.fetch(self.SEARCH_URL, params=params)

            if response is None:
                logger.warning("Takealot: No response received")
                if self._mock_data_enabled:
                    products = self._get_mock_data(search_query)
                    return self._create_result(True, products, start_time)
                return self._create_result(False, [], start_time, "No response from Takealot")

            # Parse HTML
            products = self._parse_search_results(response.text, search_query)

            # Handle pagination (get up to 2 pages - Takealot has many results)
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
                            break
                    else:
                        break

            if not products and self._mock_data_enabled:
                logger.info("Takealot: Using mock data fallback")
                products = self._get_mock_data(search_query)

            success = len(products) > 0
            return self._create_result(success, products, start_time)

        except Exception as e:
            logger.error(f"Takealot: Error scraping: {e}")
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

        # Find product listings - Takealot specific selectors
        product_cards = soup.select(
            "div.product-card, "
            "div.product, "
            "article.product, "
            "div[class*='product-listing'], "
            "div[class*='product-card']"
        )

        for card in product_cards[:20]:  # Limit to 20 per page
            try:
                product = self._parse_product_card(card, search_query)
                if product and self.validate_price(product.price):
                    # Filter by condition if looking for refurbished
                    if "refurbished" in search_query.lower():
                        if product.condition not in ["refurbished", "used"]:
                            continue
                    products.append(product)
            except Exception as e:
                logger.debug(f"Takealot: Error parsing product card: {e}")
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
        title_elem = card.select_one("h3 a, h2 a, .product-title a, a[href*='/product/']")
        if not title_elem:
            return None
        title = title_elem.get_text(strip=True)

        # Skip if title doesn't match search query somewhat
        if search_query.lower() not in title.lower():
            return None

        # Extract price - Takealot uses specific price formatting
        price_elem = card.select_one(
            ".price, "
            ".product-price, "
            "[class*='price'], "
            "span[class*='now'], "
            "span[class*='current']"
        )
        price_text = price_elem.get_text(strip=True) if price_elem else ""
        price = self.parse_price(price_text)

        if price is None:
            return None

        # Extract seller - Takealot is usually the seller
        seller_elem = card.select_one(".seller, .shop-name, [class*='seller']")
        seller = seller_elem.get_text(strip=True) if seller_elem else "Takealot"

        # Extract URL
        link_elem = card.select_one("a[href*='/product/']")
        url = None
        if link_elem and link_elem.get("href"):
            href = link_elem["href"]
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        # Extract image
        img_elem = card.select_one("img[src], img[data-src]")
        image_url = None
        if img_elem:
            image_url = img_elem.get("src") or img_elem.get("data-src")

        # Extract condition
        condition = self._extract_condition(title, card)

        # Extract specs if available
        specs = self._extract_specs(card)

        # Check availability
        availability = self._check_availability(card)

        return self.create_scraped_product(
            title=title,
            price=price,
            condition=condition,
            seller=seller,
            seller_type="dealer",
            location="South Africa",
            url=url,
            image_url=image_url,
            specs=specs,
            availability=availability,
        )

    def _extract_condition(self, title: str, card: Any) -> str:
        """Extract condition from title or card."""
        title_lower = title.lower()

        # Check for explicit condition indicators
        if "refurbished" in title_lower or "renewed" in title_lower:
            return "refurbished"
        elif "used" in title_lower or "pre-owned" in title_lower or "second hand" in title_lower:
            return "used"
        elif "open box" in title_lower:
            return "used"
        elif "new" in title_lower:
            return "new"

        # Check card for condition badges
        condition_text = card.get_text().lower()
        if "refurbished" in condition_text:
            return "refurbished"
        elif "certified pre-owned" in condition_text:
            return "refurbished"

        return "unknown"

    def _extract_specs(self, card: Any) -> Optional[Dict[str, Any]]:
        """Extract specifications from product card."""
        specs = {}
        card_text = card.get_text()

        # Extract common laptop specs
        if "intel" in card_text.lower() or "amd" in card_text.lower():
            # Try to extract processor info
            if "i5" in card_text.lower():
                specs["processor"] = "Intel Core i5"
            elif "i7" in card_text.lower():
                specs["processor"] = "Intel Core i7"
            elif "i3" in card_text.lower():
                specs["processor"] = "Intel Core i3"
            elif "ryzen 5" in card_text.lower():
                specs["processor"] = "AMD Ryzen 5"
            elif "ryzen 7" in card_text.lower():
                specs["processor"] = "AMD Ryzen 7"

        # Extract RAM
        import re
        ram_match = re.search(r"(\d+)\s*GB\s*RAM", card_text, re.IGNORECASE)
        if ram_match:
            specs["ram"] = f"{ram_match.group(1)}GB"

        # Extract storage
        storage_match = re.search(r"(\d+)\s*(GB|TB)\s*(SSD|HDD)", card_text, re.IGNORECASE)
        if storage_match:
            specs["storage"] = f"{storage_match.group(1)}{storage_match.group(2)} {storage_match.group(3)}"

        # Extract screen size
        screen_match = re.search(r"(\d{2})\.?(\d)?\s*['\"]?\s*(inch|\")", card_text, re.IGNORECASE)
        if screen_match:
            size = screen_match.group(1)
            if screen_match.group(2):
                size += f".{screen_match.group(2)}"
            specs["screen"] = f"{size}\""

        return specs if specs else None

    def _check_availability(self, card: Any) -> str:
        """Check product availability."""
        card_text = card.get_text().lower()

        if "out of stock" in card_text or "unavailable" in card_text:
            return "Out of Stock"
        elif "in stock" in card_text or "available" in card_text:
            return "In Stock"
        elif "pre-order" in card_text:
            return "Pre-order"

        return "In Stock"  # Default assumption

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
        logger.info(f"Takealot: Generating mock data for '{search_query}'")

        # Generate realistic mock prices
        base_price = self._estimate_base_price(search_query)

        mock_products = []

        # Takealot typically has multiple listings
        for i in range(3):
            price_variation = random.uniform(0.95, 1.1)
            price = round(base_price * price_variation, 2)

            condition = "refurbished" if i == 0 else random.choice(["refurbished", "new", "used"])

            mock_products.append(self.create_scraped_product(
                title=f"{search_query} - Takealot Listing {i+1}",
                price=price,
                condition=condition,
                seller="Takealot",
                seller_type="dealer",
                location="Cape Town, Western Cape",
                url=f"https://www.takealot.com/product/{i+1}",
                availability="In Stock" if i < 2 else "Limited Stock",
                specs={
                    "processor": "Intel Core i5/i7",
                    "ram": "8GB/16GB",
                    "storage": "256GB/512GB SSD",
                } if i == 0 else None,
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
