"""
Simple JSON-based data persistence for Streamlit app.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def get_file_path(filename: str) -> Path:
    """Get the full path for a data file."""
    return DATA_DIR / filename


def load_json(filename: str, default: Any = None) -> Any:
    """Load data from a JSON file."""
    filepath = get_file_path(filename)
    if not filepath.exists():
        return default if default is not None else []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default if default is not None else []


def save_json(filename: str, data: Any) -> bool:
    """Save data to a JSON file."""
    filepath = get_file_path(filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError:
        return False


INVENTORY_FILE = "inventory.json"
WOOCOMMERCE_FILE = "woo_products.json"


def load_inventory() -> List[Dict]:
    """Load inventory from file."""
    return load_json(INVENTORY_FILE, default=[])


def save_inventory(inventory: List[Dict]) -> bool:
    """Save inventory to file."""
    return save_json(INVENTORY_FILE, inventory)


def load_woo_products() -> List[Dict]:
    """Load WooCommerce products from file."""
    return load_json(WOOCOMMERCE_FILE, default=[])


def save_woo_products(products: List[Dict]) -> bool:
    """Save WooCommerce products to file."""
    return save_json(WOOCOMMERCE_FILE, products)


def get_default_inventory() -> List[Dict]:
    """Get default mock inventory."""
    return [
        {
            "id": "1",
            "serial_number": "DL-5420-001",
            "brand": "Dell",
            "model": "Latitude 5420",
            "ram_gb": 16,
            "storage_gb": 512,
            "storage_type": "SSD",
            "condition": "refurbished",
            "status": "ready",
            "purchase_price": 8500.00,
            "estimated_value": 12500.00,
            "location": "Johannesburg",
            "acquired_date": "2026-03-15",
        },
        {
            "id": "2",
            "serial_number": "HP-840G7-002",
            "brand": "HP",
            "model": "EliteBook 840 G7",
            "ram_gb": 16,
            "storage_gb": 256,
            "storage_type": "SSD",
            "condition": "refurbished",
            "status": "listed",
            "purchase_price": 9000.00,
            "estimated_value": 13500.00,
            "location": "Cape Town",
            "acquired_date": "2026-03-10",
        },
        {
            "id": "3",
            "serial_number": "LN-T14-003",
            "brand": "Lenovo",
            "model": "ThinkPad T14",
            "ram_gb": 32,
            "storage_gb": 1024,
            "storage_type": "SSD",
            "condition": "refurbished",
            "status": "refurbishing",
            "purchase_price": 10000.00,
            "estimated_value": 16000.00,
            "location": "Johannesburg",
            "acquired_date": "2026-03-20",
        },
    ]


def init_inventory() -> List[Dict]:
    """Initialize inventory, loading from file or creating default."""
    inventory = load_inventory()
    if not inventory:
        inventory = get_default_inventory()
        save_inventory(inventory)
    return inventory
