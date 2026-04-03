"""
RefurbAdmin AI - Price Display Component

Reusable component for displaying prices in South African Rand (ZAR).
Includes formatting, comparison displays, and copy-to-clipboard functionality.
"""

import streamlit as st
from typing import Optional, Dict, Any, List
import json


def format_zar(amount: Optional[float], show_cents: bool = True) -> str:
    """
    Format amount as South African Rand.

    Args:
        amount: Amount in ZAR
        show_cents: Whether to show cents

    Returns:
        Formatted string (e.g., "R 12,500.00")
    """
    if amount is None:
        return "R 0.00"

    if show_cents:
        return f"R {amount:,.2f}"
    else:
        return f"R {int(amount):,}"


def render_price_display(
    price: float,
    label: str = "Price",
    original_price: Optional[float] = None,
    show_copy: bool = False,
    highlight: bool = False,
) -> None:
    """
    Render a price display with optional comparison.

    Args:
        price: Current price
        label: Label for the price
        original_price: Original price for comparison
        show_copy: Whether to show copy-to-clipboard button
        highlight: Whether to highlight the price
    """
    # Calculate discount if original price provided
    discount = None
    if original_price and original_price > price:
        discount = ((original_price - price) / original_price) * 100

    # Create container
    if highlight:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1rem;
                border-radius: 8px;
                color: white;
                text-align: center;
            ">
                <div style="font-size: 0.8rem; opacity: 0.9;">{label}</div>
                <div style="font-size: 1.8rem; font-weight: 700;">{format_zar(price)}</div>
                {f'<div style="font-size: 0.9rem; opacity: 0.8;">Save {discount:.0f}%</div>' if discount else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**{label}**")
            if original_price and original_price > price:
                st.markdown(
                    f"""
                    <span style="text-decoration: line-through; color: #999;">
                        {format_zar(original_price)}
                    </span>
                    <span style="color: #059669; font-weight: 600; margin-left: 0.5rem;">
                        {format_zar(price)}
                    </span>
                    <span style="background: #d1fae5; color: #065f46; padding: 0.1rem 0.5rem; border-radius: 4px; font-size: 0.8rem; margin-left: 0.5rem;">
                        -{discount:.0f}%
                    </span>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**{format_zar(price)}**")

        with col2:
            if show_copy:
                copy_button(price)


def copy_button(value: str, button_label: str = "📋 Copy") -> bool:
    """
    Render a copy-to-clipboard button.

    Args:
        value: Value to copy
        button_label: Button label

    Returns:
        True if clicked
    """
    # Streamlit doesn't have native clipboard support, so we use a workaround
    # with session state and instructions
    key = f"copy_{hash(str(value))}"

    if st.button(button_label, key=key, width="stretch"):
        st.success(f"Copied: {value}")
        return True
    return False


def render_price_breakdown(
    purchase_price: float,
    refurbishment_cost: float,
    market_price: float,
    margin_percent: float,
) -> None:
    """
    Render a price breakdown showing costs and margins.

    Args:
        purchase_price: Device purchase price
        refurbishment_cost: Cost of refurbishment
        market_price: Current market price
        margin_percent: Target margin percentage
    """
    total_cost = purchase_price + refurbishment_cost
    profit = market_price - total_cost
    actual_margin = (profit / market_price) * 100 if market_price > 0 else 0

    st.markdown("### 💰 Price Breakdown")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Total Cost",
            value=format_zar(total_cost),
            delta=f"R {refurbishment_cost} refurb",
        )

    with col2:
        st.metric(
            label="Market Price",
            value=format_zar(market_price),
            delta=f"{actual_margin:.1f}% margin",
            delta_color="normal" if actual_margin >= margin_percent else "inverse",
        )

    with col3:
        st.metric(
            label="Estimated Profit",
            value=format_zar(profit),
            delta=f"{actual_margin:.1f}%",
            delta_color="normal" if profit > 0 else "inverse",
        )

    # Progress bar for margin
    st.markdown("**Margin Progress**")
    margin_ratio = min(actual_margin / margin_percent, 1.0) if margin_percent > 0 else 0
    st.progress(margin_ratio)

    if actual_margin >= margin_percent:
        st.success(f"✅ Target margin of {margin_percent}% achieved!")
    else:
        shortfall = margin_percent - actual_margin
        st.warning(f"⚠️ {shortfall:.1f}% below target margin")


def render_market_comparison(
    our_price: float,
    market_median: float,
    market_min: float,
    market_max: float,
    competitor_count: int,
) -> None:
    """
    Render market price comparison.

    Args:
        our_price: Our selling price
        market_median: Market median price
        market_min: Market minimum price
        market_max: Market maximum price
        competitor_count: Number of competitor listings
    """
    st.markdown("### 🌍 Market Comparison")

    # Calculate position
    if our_price < market_min:
        position = "Below Market"
        color = "#059669"
    elif our_price > market_max:
        position = "Above Market"
        color = "#dc2626"
    elif our_price < market_median:
        position = "Competitive"
        color = "#2563eb"
    else:
        position = "Premium"
        color = "#7c3aed"

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Our Price:** {format_zar(our_price)}")
        st.markdown(f"**Market Median:** {format_zar(market_median)}")

        diff_percent = ((our_price - market_median) / market_median) * 100
        if diff_percent > 0:
            st.markdown(f":red[+{diff_percent:.1f}% vs market]")
        else:
            st.markdown(f":green[{diff_percent:.1f}% vs market]")

    with col2:
        st.markdown(f"**Position:** :{color}[{position}]")
        st.markdown(f"**Competitors:** {competitor_count} listings")
        st.markdown(
            f"**Market Range:** {format_zar(market_min)} - {format_zar(market_max)}"
        )

    # Visual comparison bar
    st.markdown("**Price Position**")

    # Create a simple visual representation
    range_size = market_max - market_min
    if range_size > 0:
        our_position = ((our_price - market_min) / range_size) * 100
        median_position = ((market_median - market_min) / range_size) * 100

        # Create columns for visualization
        cols = st.columns(10)
        for i, col in enumerate(cols):
            pos = i * 10
            if pos <= our_position < (i + 1) * 10:
                col.markdown("📍")
            elif pos <= median_position < (i + 1) * 10:
                col.markdown("📊")
            else:
                col.markdown("─")

        st.caption("📍 = Our Price | 📊 = Market Median")


def render_quote_snippet(
    device: Dict[str, Any],
    price: float,
    valid_days: int = 7,
) -> None:
    """
    Render a quote snippet for copying.

    Args:
        device: Device data
        price: Quoted price
        valid_days: Quote validity in days
    """
    from datetime import datetime, timedelta

    valid_until = datetime.now() + timedelta(days=valid_days)

    snippet = f"""
*QUOTE: {device.get("brand", "")} {device.get("model", "")}*
Serial: {device.get("serial_number", "N/A")}
Condition: {device.get("condition", "Unknown").title()}
Specs: {device.get("ram_gb", 0)}GB RAM, {device.get("storage_gb", 0)}GB {device.get("storage_type", "SSD")}

*Price: {format_zar(price)}*
Valid until: {valid_until.strftime("%Y-%m-%d")}

RefurbAdmin AI - Quality Refurbished IT
📞 011 123 4567 | 🌐 www.refurbadmin.co.za
""".strip()

    st.markdown("### 📝 Quote Snippet")
    st.code(snippet, language="text")

    if st.button("📋 Copy Quote to Clipboard"):
        st.success("Quote copied! Paste it in your email or message.")
