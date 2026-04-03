"""
RefurbAdmin AI - Inventory Management Page

Streamlit page for managing device inventory.
Features: device list, filters, search, status updates, add new device.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Import components
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from components.device_card import render_device_card
from components.status_badge import (
    render_status_badge_streamlit,
    render_status_selector,
    render_status_filter,
    STATUS_CONFIG,
)
from components.price_display import format_zar

# Page configuration
st.set_page_config(
    page_title="Inventory | RefurbAdmin AI",
    page_icon="📦",
    layout="wide",
)


# Mock data for demonstration
def get_mock_inventory() -> List[Dict[str, Any]]:
    """Get mock inventory data."""
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
        {
            "id": "4",
            "serial_number": "DL-7490-004",
            "brand": "Dell",
            "model": "Latitude 7490",
            "ram_gb": 8,
            "storage_gb": 256,
            "storage_type": "SSD",
            "condition": "used",
            "status": "inspecting",
            "purchase_price": 5500.00,
            "estimated_value": 8500.00,
            "location": "Durban",
            "acquired_date": "2026-03-25",
        },
        {
            "id": "5",
            "serial_number": "HP-850G5-005",
            "brand": "HP",
            "model": "EliteBook 850 G5",
            "ram_gb": 16,
            "storage_gb": 512,
            "storage_type": "SSD",
            "condition": "refurbished",
            "status": "sold",
            "purchase_price": 7500.00,
            "estimated_value": 11000.00,
            "location": "Pretoria",
            "acquired_date": "2026-02-28",
        },
    ]


def show_inventory_page() -> None:
    """Display inventory management page."""
    # Header
    st.markdown(
        """
        <div class="main-header">📦 Inventory Management</div>
        <div class="sub-header">Manage your IT refurbishment inventory</div>
        """,
        unsafe_allow_html=True,
    )

    # Initialize session state
    if "inventory" not in st.session_state:
        st.session_state.inventory = get_mock_inventory()
    if "show_add_form" not in st.session_state:
        st.session_state.show_add_form = False
    if "woo_products" not in st.session_state:
        st.session_state.woo_products = []
    if "woo_connected" not in st.session_state:
        st.session_state.woo_connected = False

    # Sidebar filters
    with st.sidebar:
        st.markdown("### 🔍 Filters")

        # Status filter
        status_filter = render_status_filter(key="inv_status_filter")

        # Brand filter
        brands = list(set(item["brand"] for item in st.session_state.inventory))
        brand_filter = st.selectbox(
            "Brand",
            options=["All"] + sorted(brands),
            key="inv_brand_filter",
        )

        # Location filter
        locations = list(set(item["location"] for item in st.session_state.inventory))
        location_filter = st.selectbox(
            "Location",
            options=["All"] + sorted(locations),
            key="inv_location_filter",
        )

        # Condition filter
        condition_filter = st.selectbox(
            "Condition",
            options=["All", "New", "Refurbished", "Used", "Faulty"],
            key="inv_condition_filter",
        )

        # Price range
        st.markdown("---")
        st.markdown("**Price Range**")
        min_price = st.number_input("Min Price", min_value=0, value=0, step=1000)
        max_price = st.number_input("Max Price", min_value=0, value=50000, step=1000)

        # Reset filters
        st.markdown("---")
        if st.button("🔄 Reset Filters", use_container_width=True):
            st.session_state.inv_status_filter = "All"
            st.session_state.inv_brand_filter = "All"
            st.session_state.inv_location_filter = "All"
            st.session_state.inv_condition_filter = "All"
            st.rerun()

    # Main content area
    # Search bar
    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input(
            "🔍 Search",
            placeholder="Search by serial number, model, or brand...",
            key="inv_search",
        )

    with col2:
        if st.button("➕ Add Device", use_container_width=True, type="primary"):
            st.session_state.show_add_form = True
            st.rerun()

    # Apply filters
    filtered_inventory = st.session_state.inventory.copy()

    if search_query:
        search_lower = search_query.lower()
        filtered_inventory = [
            item
            for item in filtered_inventory
            if search_lower in item["serial_number"].lower()
            or search_lower in item["model"].lower()
            or search_lower in item["brand"].lower()
        ]

    if status_filter:
        filtered_inventory = [
            item
            for item in filtered_inventory
            if item["status"].lower() == status_filter.lower()
        ]

    if brand_filter != "All":
        filtered_inventory = [
            item for item in filtered_inventory if item["brand"] == brand_filter
        ]

    if location_filter != "All":
        filtered_inventory = [
            item for item in filtered_inventory if item["location"] == location_filter
        ]

    if condition_filter != "All":
        filtered_inventory = [
            item
            for item in filtered_inventory
            if item["condition"].lower() == condition_filter.lower()
        ]

    filtered_inventory = [
        item
        for item in filtered_inventory
        if min_price <= item.get("estimated_value", 0) <= max_price
    ]

    # Display results count
    st.markdown(
        f"**{len(filtered_inventory)}** of **{len(st.session_state.inventory)}** devices"
    )

    st.markdown("---")

    # Display inventory
    if not filtered_inventory:
        st.info("No devices match your filters. Try adjusting your search criteria.")
    else:
        # View toggle
        view_mode = st.radio(
            "View Mode",
            options=["Cards", "Table"],
            horizontal=True,
            key="inv_view_mode",
        )

        if view_mode == "Cards":
            # Card view
            for device in filtered_inventory:
                render_device_card(
                    device=device,
                    on_edit=lambda id: edit_device(id),
                    on_delete=lambda id: delete_device(id),
                )
        else:
            # Table view
            df = pd.DataFrame(filtered_inventory)
            df = df[
                [
                    "serial_number",
                    "brand",
                    "model",
                    "ram_gb",
                    "storage_gb",
                    "condition",
                    "status",
                    "purchase_price",
                    "estimated_value",
                    "location",
                ]
            ]
            df.columns = [
                "Serial",
                "Brand",
                "Model",
                "RAM",
                "Storage",
                "Condition",
                "Status",
                "Cost",
                "Value",
                "Location",
            ]
            st.dataframe(df, use_container_width=True)

    # Show add form if requested
    if st.session_state.show_add_form:
        show_add_device_form()


def show_add_device_form() -> None:
    """Display add new device form."""
    st.markdown("---")
    st.markdown("### ➕ Add New Device")

    with st.form("add_device_form"):
        col1, col2 = st.columns(2)

        with col1:
            brand = st.selectbox(
                "Brand *",
                options=["Dell", "HP", "Lenovo", "Apple", "Asus", "Acer", "Other"],
            )
            model = st.text_input("Model *", placeholder="e.g., Latitude 5420")
            serial_number = st.text_input(
                "Serial Number *", placeholder="Service tag or serial"
            )
            ram_gb = st.selectbox("RAM (GB)", options=[4, 8, 16, 32, 64])
            storage_gb = st.selectbox(
                "Storage (GB)", options=[128, 256, 512, 1024, 2048]
            )
            storage_type = st.selectbox("Storage Type", options=["SSD", "HDD", "NVMe"])

        with col2:
            condition = st.selectbox(
                "Condition *",
                options=["new", "refurbished", "used", "faulty"],
            )
            status = st.selectbox(
                "Status *",
                options=["pending", "inspecting", "refurbishing", "ready", "listed"],
            )
            purchase_price = st.number_input(
                "Purchase Price (R) *",
                min_value=0.0,
                step=100.0,
            )
            estimated_value = st.number_input(
                "Estimated Value (R)",
                min_value=0.0,
                step=100.0,
            )
            location = st.selectbox(
                "Location",
                options=[
                    "Johannesburg",
                    "Cape Town",
                    "Durban",
                    "Pretoria",
                    "Port Elizabeth",
                ],
            )
            acquired_date = st.date_input("Acquired Date", value=datetime.now())

        notes = st.text_area("Notes", placeholder="Any additional information...")

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            submitted = st.form_submit_button(
                "💾 Save Device", use_container_width=True, type="primary"
            )

        with col2:
            cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submitted:
            # Validate required fields
            if not model or not serial_number:
                st.error("Please fill in all required fields.")
            else:
                # Create new device
                new_device = {
                    "id": str(len(st.session_state.inventory) + 1),
                    "serial_number": serial_number,
                    "brand": brand,
                    "model": model,
                    "ram_gb": ram_gb,
                    "storage_gb": storage_gb,
                    "storage_type": storage_type,
                    "condition": condition,
                    "status": status,
                    "purchase_price": purchase_price,
                    "estimated_value": estimated_value or purchase_price * 1.5,
                    "location": location,
                    "acquired_date": acquired_date.strftime("%Y-%m-%d"),
                    "notes": notes,
                }

                st.session_state.inventory.append(new_device)
                st.success("Device added successfully!")
                st.session_state.show_add_form = False
                st.rerun()

        if cancelled:
            st.session_state.show_add_form = False
            st.rerun()


def edit_device(device_id: str) -> None:
    """
    Handle edit device action.

    Args:
        device_id: Device ID to edit
    """
    # Find device
    device = next((d for d in st.session_state.inventory if d["id"] == device_id), None)

    if not device:
        st.error("Device not found.")
        return

    st.session_state.editing_device = device
    st.session_state.show_edit_form = True
    st.rerun()


def delete_device(device_id: str) -> None:
    """
    Handle delete device action.

    Args:
        device_id: Device ID to delete
    """
    # Confirm deletion
    st.warning("Are you sure you want to delete this device?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Yes, Delete", key=f"confirm_delete_{device_id}"):
            st.session_state.inventory = [
                d for d in st.session_state.inventory if d["id"] != device_id
            ]
            st.success("Device deleted successfully!")
            st.rerun()

    with col2:
        if st.button("❌ Cancel", key=f"cancel_delete_{device_id}"):
            st.rerun()


def show_edit_device_form() -> None:
    """Display edit device form."""
    device = st.session_state.get("editing_device")

    if not device:
        return

    st.markdown("---")
    st.markdown("### ✏️ Edit Device")

    with st.form("edit_device_form"):
        col1, col2 = st.columns(2)

        with col1:
            brand = st.selectbox(
                "Brand *",
                options=["Dell", "HP", "Lenovo", "Apple", "Asus", "Acer", "Other"],
                index=["Dell", "HP", "Lenovo", "Apple", "Asus", "Acer", "Other"].index(
                    device.get("brand", "Dell")
                ),
            )
            model = st.text_input("Model *", value=device.get("model", ""))
            serial_number = st.text_input(
                "Serial Number *", value=device.get("serial_number", "")
            )
            ram_gb = st.selectbox(
                "RAM (GB)",
                options=[4, 8, 16, 32, 64],
                index=[4, 8, 16, 32, 64].index(device.get("ram_gb", 8)),
            )
            storage_gb = st.selectbox(
                "Storage (GB)",
                options=[128, 256, 512, 1024, 2048],
                index=[128, 256, 512, 1024, 2048].index(device.get("storage_gb", 256)),
            )
            storage_type = st.selectbox(
                "Storage Type",
                options=["SSD", "HDD", "NVMe"],
                index=["SSD", "HDD", "NVMe"].index(device.get("storage_type", "SSD")),
            )

        with col2:
            condition = st.selectbox(
                "Condition *",
                options=["new", "refurbished", "used", "faulty"],
                index=["new", "refurbished", "used", "faulty"].index(
                    device.get("condition", "refurbished")
                ),
            )
            status = st.selectbox(
                "Status *",
                options=[
                    "pending",
                    "inspecting",
                    "refurbishing",
                    "ready",
                    "listed",
                    "reserved",
                    "sold",
                    "archived",
                ],
                index=[
                    "pending",
                    "inspecting",
                    "refurbishing",
                    "ready",
                    "listed",
                    "reserved",
                    "sold",
                    "archived",
                ].index(device.get("status", "pending")),
            )
            purchase_price = st.number_input(
                "Purchase Price (R) *",
                min_value=0.0,
                value=float(device.get("purchase_price", 0)),
                step=100.0,
            )
            estimated_value = st.number_input(
                "Estimated Value (R)",
                min_value=0.0,
                value=float(device.get("estimated_value", 0)),
                step=100.0,
            )
            location = st.selectbox(
                "Location",
                options=[
                    "Johannesburg",
                    "Cape Town",
                    "Durban",
                    "Pretoria",
                    "Port Elizabeth",
                ],
                index=[
                    "Johannesburg",
                    "Cape Town",
                    "Durban",
                    "Pretoria",
                    "Port Elizabeth",
                ].index(device.get("location", "Johannesburg")),
            )

        notes = st.text_area("Notes", value=device.get("notes", ""))

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            submitted = st.form_submit_button(
                "💾 Save Changes", use_container_width=True, type="primary"
            )

        with col2:
            cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submitted:
            # Update device
            device["brand"] = brand
            device["model"] = model
            device["serial_number"] = serial_number
            device["ram_gb"] = ram_gb
            device["storage_gb"] = storage_gb
            device["storage_type"] = storage_type
            device["condition"] = condition
            device["status"] = status
            device["purchase_price"] = purchase_price
            device["estimated_value"] = estimated_value
            device["location"] = location
            device["notes"] = notes

            st.success("Device updated successfully!")
            st.session_state.editing_device = None
            st.session_state.show_edit_form = False
            st.rerun()

        if cancelled:
            st.session_state.editing_device = None
            st.session_state.show_edit_form = False
            st.rerun()


# Main entry point
if __name__ == "__main__":
    show_inventory_page()
else:
    # When imported as a page
    show_inventory_page()
