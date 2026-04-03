"""
RefurbAdmin AI - Scrapers Module

Web scrapers for South African market price aggregation.
"""

from .base_scraper import BaseScraper, ScrapedProduct, ScrapingResult, RateLimiter
from .pricecheck_scraper import PriceCheckScraper
from .takealot_scraper import TakealotScraper
from .gumtree_scraper import GumtreeScraper

__all__ = [
    "BaseScraper",
    "ScrapedProduct",
    "ScrapingResult",
    "RateLimiter",
    "PriceCheckScraper",
    "TakealotScraper",
    "GumtreeScraper",
]
