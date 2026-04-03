"""
RefurbAdmin AI - Device Card Component

Reusable component for displaying device information in a card format.
"""

import streamlit as st
from typing import Optional, Dict, Any, Callable


def render_device_card(
    device: Dict[str, Any],
    on_edit: Optional[Callable[[str], None]] = None,
    on_delete: Optional[Callable[[str], None]] = None,
    show_actions: bool = True,
) -> None:
    """
    Render a device information card.

    Args:
        device: Device data dictionary
        on_edit: Callback for edit action
        on_delete: Callback for delete action
        show_actions: Whether to show action buttons
    """
    # Extract device info
    device_id = device.get("id", "unknown")
    serial = device.get("serial_number", "N/A")
    model = device.get("model", "Unknown Model")
    brand = device.get("brand", "Unknown")
    ram_gb = device.get("ram_gb", 0)
    storage_gb = device.get("storage_gb", 0)
    storage_type = device.get("storage_type", "SSD")
    condition = device.get("condition", "unknown")
    status = device.get("status", "pending")
    purchase_price = device.get("purchase_price", 0)
    estimated_value = device.get("estimated_value", 0)
    location = device.get("location", "Unknown")
    acquired_date = device.get("acquired_date", "")

    # Create card container
    with st.container():
        # Header row
        col1, col2, col3 = st.columns([4, 2, 2])

        with col1:
            st.markdown(f"**{brand} {model}**")
            st.caption(f"Serial: `{serial}`")

        with col2:
            st.markdown(f"**💰 {format_currency_zar(estimated_value)}**")
            st.caption(f"Cost: {format_currency_zar(purchase_price)}")

        with col3:
            status_color = get_status_color(status)
            st.markdown(
                f"""
                <span style="
                    display: inline-block;
                    padding: 0.25rem 0.75rem;
                    border-radius: 9999px;
                    font-size: 0.75rem;
                    font-weight: 600;
                    background-color: {status_color[0]};
                    color: {status_color[1]};
                ">
                    {status.upper()}
                </span>
                """,
                unsafe_allow_html=True,
            )

        # Specs row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"💾 **{ram_gb}GB RAM**")

        with col2:
            st.markdown(f"📀 **{storage_gb}GB {storage_type}**")

        with col3:
            condition_icon = get_condition_icon(condition)
            st.markdown(f"{condition_icon} **{condition.title()}**")

        with col4:
            st.markdown(f"📍 **{location}**")

        # Metadata row
        if acquired_date:
            st.caption(f"Acquired: {acquired_date}")

        # Action buttons
        if show_actions:
            st.markdown("---")
            col1, col2, col3 = st.columns([3, 1, 1])

            with col2:
                if st.button("✏️ Edit", key=f"edit_{device_id}", width="stretch"):
                    if on_edit:
                        on_edit(device_id)

            with col3:
                if st.button("🗑️ Delete", key=f"delete_{device_id}", width="stretch"):
                    if on_delete:
                        on_delete(device_id)

        st.markdown("---")


def get_status_color(status: str) -> tuple:
    """
    Get color scheme for status.

    Args:
        status: Device status

    Returns:
        Tuple of (background_color, text_color)
    """
    colors = {
        "pending": ("#fef3c7", "#92400e"),
        "inspecting": ("#dbeafe", "#1e40af"),
        "refurbishing": ("#e0e7ff", "#3730a3"),
        "ready": ("#d1fae5", "#065f46"),
        "listed": ("#cffafe", "#0e7490"),
        "reserved": ("#fef9c3", "#854d0e"),
        "sold": ("#fee2e2", "#991b1b"),
        "archived": ("#f3f4f6", "#374151"),
    }
    return colors.get(status.lower(), ("#f3f4f6", "#374151"))


def get_condition_icon(condition: str) -> str:
    """
    Get icon for condition.

    Args:
        condition: Device condition

    Returns:
        Icon emoji
    """
    icons = {
        "new": "✨",
        "refurbished": "🔄",
        "used": "👌",
        "faulty": "⚠️",
    }
    return icons.get(condition.lower(), "❓")


def format_currency_zar(amount: float) -> str:
    """
    Format amount as South African Rand.

    Args:
        amount: Amount in ZAR

    Returns:
        Formatted string
    """
    if amount is None:
        return "R 0.00"
    return f"R {amount:,.2f}"
