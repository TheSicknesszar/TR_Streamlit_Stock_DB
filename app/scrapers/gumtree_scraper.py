"""
RefurbAdmin AI - Gumtree.co.za Scraper

Scraper for Gumtree South Africa - Classified ads marketplace.
Extracts laptop prices from private sellers and dealers.

Note: This scraper includes mock data fallback for testing when
live scraping is blocked or rate-limited.
"""

import asyncio
import logging
import random
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScrapingResult, ScrapedProduct

logger = logging.getLogger(__name__)


class GumtreeScraper(BaseScraper):
    """
    Scraper for Gumtree.co.za.

    Gumtree is South Africa's popular classified ads platform,
    featuring both private sellers and dealers.
    """

    BASE_URL = "https://www.gumtree.co.za"
    SEARCH_URL = "https://www.gumtree.co.za/s-laptops/notebooks-laptops-for-sale/"

    def __init__(self, timeout: int = 30, rate_limit: float = 0.3, max_retries: int = 3):
        """
        Initialize Gumtree scraper.

        Args:
            timeout: Request timeout in seconds
            rate_limit: Requests per second (0.3 = 1 request per ~3 seconds)
            max_retries: Maximum retry attempts
        """
        # Gumtree requires slower rate limiting
        super().__init__(timeout=timeout, rate_limit=rate_limit, max_retries=max_retries)
        self._mock_data_enabled = False

    def get_source_name(self) -> str:
        """Get scraper source name."""
        return "Gumtree.co.za"

    def enable_mock_data(self, enabled: bool = True) -> None:
        """Enable/disable mock data fallback."""
        self._mock_data_enabled = enabled

    async def scrape(self, search_query: str) -> ScrapingResult:
        """
        Scrape prices from Gumtree for a search query.

        Args:
            search_query: Product search query (e.g., "Dell Latitude 5420")

        Returns:
            ScrapingResult with found products
        """
        start_time = datetime.now()
        products: List[ScrapedProduct] = []

        try:
            logger.info(f"Gumtree: Searching for '{search_query}'")

            # Build search URL - Gumtree uses URL-encoded search terms
            search_term = search_query.replace(" ", "-")
            search_url = f"{self.SEARCH_URL}/{search_term}"

            response = await self.fetch(search_url)

            if response is None:
                logger.warning("Gumtree: No response received")
                if self._mock_data_enabled:
                    products = self._get_mock_data(search_query)
                    return self._create_result(True, products, start_time)
                return self._create_result(False, [], start_time, "No response from Gumtree")

            # Parse HTML
            products = self._parse_search_results(response.text, search_query)

            # Handle pagination (get up to 3 pages)
            if products:
                for page in range(2, 4):
                    await asyncio.sleep(3)  # Gumtree requires slower requests
                    paginated_url = f"{search_url}/page-{page}"
                    response = await self.fetch(paginated_url)
                    if response and response.status_code == 200:
                        page_products = self._parse_search_results(response.text, search_query)
                        if page_products:
                            products.extend(page_products)
                        else:
                            break
                    else:
                        break

            if not products and self._mock_data_enabled:
                logger.info("Gumtree: Using mock data fallback")
                products = self._get_mock_data(search_query)

            success = len(products) > 0
            return self._create_result(success, products, start_time)

        except Exception as e:
            logger.error(f"Gumtree: Error scraping: {e}")
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

        # Find product listings - Gumtree specific selectors
        product_cards = soup.select(
            "div.search-result-item, "
            "article.listing, "
            "div[class*='listing'], "
            "div[class*='search-result'], "
            ".listing-item"
        )

        for card in product_cards[:20]:  # Limit to 20 per page
            try:
                product = self._parse_product_card(card, search_query)
                if product and self.validate_price(product.price):
                    products.append(product)
            except Exception as e:
                logger.debug(f"Gumtree: Error parsing product card: {e}")
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
        title_elem = card.select_one("h3 a, h2 a, .listing-title a, a[href*='/ad/']")
        if not title_elem:
            return None
        title = title_elem.get_text(strip=True)

        # Skip if title doesn't match search query somewhat
        if search_query.lower() not in title.lower() and len(title) < 10:
            return None

        # Extract price - Gumtree uses specific formatting
        price_elem = card.select_one(
            ".price, "
            "[class*='price'], "
            "span[class*='amount']"
        )
        price_text = price_elem.get_text(strip=True) if price_elem else ""
        price = self.parse_price(price_text)

        if price is None:
            # Check if price says "Contact seller" or similar
            if price_text and "contact" in price_text.lower():
                return None
            return None

        # Extract seller type (private vs dealer)
        seller_type = self._determine_seller_type(card)

        # Extract seller name
        seller_elem = card.select_one(".seller-name, [class*='seller'], .poster-name")
        seller = seller_elem.get_text(strip=True) if seller_elem else None

        # Extract location
        location_elem = card.select_one(".location, [class*='location'], .area")
        location = location_elem.get_text(strip=True) if location_elem else None

        # Extract URL
        link_elem = card.select_one("a[href*='/ad/']")
        url = None
        if link_elem and link_elem.get("href"):
            href = link_elem["href"]
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        # Extract image
        img_elem = card.select_one("img[src], img[data-original]")
        image_url = None
        if img_elem:
            image_url = img_elem.get("src") or img_elem.get("data-original")

        # Extract condition
        condition = self._extract_condition(title, card)

        # Extract posting date if available
        date_elem = card.select_one(".date, [class*='date'], time")
        posted_date = date_elem.get_text(strip=True) if date_elem else None

        return self.create_scraped_product(
            title=title,
            price=price,
            condition=condition,
            seller=seller,
            seller_type=seller_type,
            location=location,
            url=url,
            image_url=image_url,
            availability="Available" if posted_date else "Unknown",
        )

    def _determine_seller_type(self, card: Any) -> str:
        """Determine if seller is private or dealer."""
        card_text = card.get_text().lower()

        # Dealer indicators
        dealer_indicators = [
            "store", "shop", "deals", "wholesale", "retail",
            "trading", "cc", "pty", "ltd", "enterprise"
        ]

        if any(indicator in card_text for indicator in dealer_indicators):
            return "dealer"

        # Check for dealer badge/class
        if card.select_one(".dealer-badge, [class*='dealer'], .verified-seller"):
            return "dealer"

        return "private"

    def _extract_condition(self, title: str, card: Any) -> str:
        """Extract condition from title or card."""
        title_lower = title.lower()
        card_text = card.get_text().lower()

        # Check for explicit condition indicators
        if "refurbished" in title_lower or "renewed" in title_lower or "reconditioned" in title_lower:
            return "refurbished"
        elif "used" in title_lower or "pre-owned" in title_lower or "second hand" in title_lower:
            return "used"
        elif "open box" in title_lower or "display unit" in title_lower:
            return "used"
        elif "new" in title_lower or "sealed" in title_lower or "brand new" in title_lower:
            return "new"
        elif "faulty" in title_lower or "broken" in title_lower or "spares" in title_lower or "repair" in title_lower:
            return "faulty"

        # Check card for condition info
        if "excellent condition" in card_text:
            return "used"
        elif "good condition" in card_text:
            return "used"
        elif "like new" in card_text:
            return "used"

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
        logger.info(f"Gumtree: Generating mock data for '{search_query}'")

        # South African locations
        locations = [
            "Johannesburg, Gauteng",
            "Pretoria, Gauteng",
            "Cape Town, Western Cape",
            "Durban, KwaZulu-Natal",
            "Port Elizabeth, Eastern Cape",
            "Bloemfontein, Free State",
        ]

        # Seller names (mix of private and dealer)
        private_sellers = ["John D.", "Sarah M.", "Mike R.", "Lisa K.", "David P."]
        dealer_sellers = ["TechDeals ZA", "Laptop Outlet", "PC Warehouse", "Gadget Store"]

        # Generate realistic mock prices (typically lower on Gumtree)
        base_price = self._estimate_base_price(search_query)

        mock_products = []

        # Generate private seller listings
        for i, location in enumerate(locations[:3]):
            price_variation = random.uniform(0.8, 1.0)  # Private sellers often cheaper
            price = round(base_price * price_variation, 2)

            mock_products.append(self.create_scraped_product(
                title=f"{search_query} - Good Condition",
                price=price,
                condition=random.choice(["used", "refurbished"]),
                seller=random.choice(private_sellers),
                seller_type="private",
                location=location,
                url=f"https://www.gumtree.co.za/ad/{i}",
                availability="Available",
            ))

        # Generate dealer listings
        for i, dealer in enumerate(dealer_sellers[:2]):
            price_variation = random.uniform(0.9, 1.05)
            price = round(base_price * price_variation, 2)

            mock_products.append(self.create_scraped_product(
                title=f"{search_query} - Refurbished by Dealer",
                price=price,
                condition="refurbished",
                seller=dealer,
                seller_type="dealer",
                location=random.choice(locations),
                url=f"https://www.gumtree.co.za/ad/{i+10}",
                availability="In Stock",
            ))

        return mock_products

    def _estimate_base_price(self, search_query: str) -> float:
        """Estimate base price from search query."""
        query_lower = search_query.lower()

        # Premium brands
        if any(brand in query_lower for brand in ["thinkpad", "dell precision", "hp zbook", "macbook"]):
            return random.uniform(10000, 22000)  # Gumtree prices typically lower
        # Business class
        elif any(brand in query_lower for brand in ["latitude", "elitebook", "probook", "thinkbook"]):
            return random.uniform(7000, 13000)
        # Consumer class
        else:
            return random.uniform(4000, 8000)
