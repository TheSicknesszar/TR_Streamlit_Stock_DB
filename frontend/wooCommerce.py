"""
WooCommerce API Service

Functions for fetching product stock from WooCommerce stores.
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime


class WooCommerceAPI:
    """WooCommerce REST API client."""

    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str):
        self.store_url = store_url.rstrip("/")
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.api_version = "wc/v3"

    def _get_base_url(self) -> str:
        """Get the API base URL."""
        if "/wp-json" in self.store_url:
            base = self.store_url.split("/wp-json")[0]
        else:
            base = self.store_url
        return f"{base}/wp-json/{self.api_version}"

    def _get_auth_params(self) -> Dict[str, str]:
        """Get authentication parameters."""
        return {
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret,
        }

    def get_products(
        self,
        per_page: int = 100,
        page: int = 1,
        stock_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch products from WooCommerce.

        Args:
            per_page: Number of products per page (max 100)
            page: Page number
            stock_status: Filter by 'instock', 'outofstock', or 'onbackorder'

        Returns:
            List of product dictionaries
        """
        url = f"{self._get_base_url()}/products"
        params = self._get_auth_params()
        params.update(
            {
                "per_page": min(per_page, 100),
                "page": page,
            }
        )

        if stock_status:
            params["stock_status"] = stock_status

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch products: {str(e)}")

    def get_all_products(
        self, stock_status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all products with pagination.

        Args:
            stock_status: Filter by 'instock', 'outofstock', or 'onbackorder'

        Returns:
            List of all product dictionaries
        """
        all_products = []
        page = 1

        while True:
            products = self.get_products(
                per_page=100, page=page, stock_status=stock_status
            )
            if not products:
                break
            all_products.extend(products)
            if len(products) < 100:
                break
            page += 1

        return all_products

    def get_product_stock(self, product_id: int) -> Dict[str, Any]:
        """
        Get stock information for a specific product.

        Args:
            product_id: WooCommerce product ID

        Returns:
            Dictionary with stock info
        """
        url = f"{self._get_base_url()}/products/{product_id}"
        params = self._get_auth_params()

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            product = response.json()
            return {
                "id": product.get("id"),
                "name": product.get("name"),
                "sku": product.get("sku"),
                "stock_quantity": product.get("stock_quantity", 0),
                "stock_status": product.get("stock_status"),
                "manage_stock": product.get("manage_stock", False),
                "price": product.get("price"),
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch product {product_id}: {str(e)}")

    def update_stock(self, product_id: int, stock_quantity: int) -> Dict[str, Any]:
        """
        Update stock quantity for a product.

        Args:
            product_id: WooCommerce product ID
            stock_quantity: New stock quantity

        Returns:
            Updated product dictionary
        """
        url = f"{self._get_base_url()}/products/{product_id}"
        params = self._get_auth_params()
        data = {
            "stock_quantity": stock_quantity,
            "manage_stock": True,
        }

        try:
            response = requests.put(url, params=params, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(
                f"Failed to update stock for product {product_id}: {str(e)}"
            )


def get_woo_products(
    store_url: str,
    consumer_key: str,
    consumer_secret: str,
    stock_status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch products from WooCommerce store.

    Args:
        store_url: WooCommerce store URL (e.g., https://example.com)
        consumer_key: WooCommerce consumer key
        consumer_secret: WooCommerce consumer secret
        stock_status: Optional filter ('instock', 'outofstock', 'onbackorder')

    Returns:
        List of products with stock info
    """
    api = WooCommerceAPI(store_url, consumer_key, consumer_secret)
    return api.get_all_products(stock_status=stock_status)


def format_woo_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format WooCommerce products for display.

    Args:
        products: Raw products from WooCommerce API

    Returns:
        Formatted list with relevant fields
    """
    formatted = []
    for product in products:
        formatted.append(
            {
                "woo_id": product.get("id"),
                "name": product.get("name"),
                "sku": product.get("sku"),
                "stock_quantity": product.get("stock_quantity", 0),
                "stock_status": product.get("stock_status"),
                "price": product.get("price"),
                "manage_stock": product.get("manage_stock", False),
                "total_sales": product.get("total_sales", 0),
                "date_created": product.get("date_created"),
            }
        )
    return formatted
