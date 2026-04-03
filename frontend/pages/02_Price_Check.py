"""
RefurbAdmin AI - Price Check Page

Streamlit page for checking market prices and generating quotes.
Features: serial input, pricing breakdown, market comparison, quote generation.
"""

import streamlit as st
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Import components
from components.price_display import (
    format_zar,
    render_price_display,
    render_price_breakdown,
    render_market_comparison,
    render_quote_snippet,
)
from components.status_badge import render_status_badge_streamlit

# Page configuration
st.set_page_config(
    page_title="Price Check | RefurbAdmin AI",
    page_icon="💰",
    layout="wide",
)


# Mock market data for demonstration
def get_mock_market_data(search_query: str) -> Dict[str, Any]:
    """
    Get mock market data for a search query.

    Args:
        search_query: Product search query

    Returns:
        Market data dictionary
    """
    # Generate realistic mock data based on query
    base_price = 12000  # Default base price

    if "latitude" in search_query.lower():
        base_price = 11500
    elif "elitebook" in search_query.lower():
        base_price = 12000
    elif "thinkpad" in search_query.lower():
        base_price = 13500
    elif "macbook" in search_query.lower():
        base_price = 18000
    elif "precision" in search_query.lower():
        base_price = 20000

    return {
        "search_query": search_query,
        "median_price": base_price,
        "min_price": base_price * 0.85,
        "max_price": base_price * 1.25,
        "average_price": base_price * 1.02,
        "total_listings": 24,
        "price_by_source": {
            "PriceCheck.co.za": [base_price * 0.95, base_price, base_price * 1.05],
            "Takealot.com": [base_price * 1.0, base_price * 1.08],
            "Gumtree.co.za": [base_price * 0.85, base_price * 0.9, base_price * 0.92],
        },
        "listings_by_condition": {
            "refurbished": 12,
            "used": 8,
            "new": 4,
        },
        "sources_scraped": ["PriceCheck.co.za", "Takealot.com", "Gumtree.co.za"],
        "sources_failed": [],
        "scraped_at": datetime.now().isoformat(),
    }


def show_price_check_page() -> None:
    """Display price check page."""
    # Header
    st.markdown(
        """
        <div class="main-header">💰 Market Price Check</div>
        <div class="sub-header">Check market prices and generate quotes for your devices</div>
        """,
        unsafe_allow_html=True,
    )

    # Initialize session state
    if "market_data" not in st.session_state:
        st.session_state.market_data = None
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "is_scraping" not in st.session_state:
        st.session_state.is_scraping = False

    # Input section
    st.markdown("### 🔍 Search for Device")

    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input(
            "Device Model",
            placeholder="e.g., Dell Latitude 5420, HP EliteBook 840 G7",
            key="price_search_input",
            help="Enter the laptop model to check market prices",
        )

    with col2:
        search_btn = st.button("🔍 Check Prices", use_container_width=True, type="primary")

    # Quick select popular models
    st.markdown("**Popular Models:**")
    quick_models = [
        "Dell Latitude 5420",
        "HP EliteBook 840 G7",
        "Lenovo ThinkPad T14",
        "Dell Latitude 7490",
        "HP EliteBook 850 G5",
    ]

    cols = st.columns(5)
    for i, model in enumerate(quick_models):
        with cols[i]:
            if st.button(model, key=f"quick_{i}", use_container_width=True):
                st.session_state.search_query = model
                st.session_state.market_data = None
                st.rerun()

    # Handle search
    if search_btn or (search_query and search_query != st.session_state.search_query):
        st.session_state.search_query = search_query
        st.session_state.is_scraping = True
        st.rerun()

    # Show scraping progress
    if st.session_state.is_scraping and st.session_state.search_query:
        show_scraping_progress(st.session_state.search_query)

    # Show results if we have data
    if st.session_state.market_data and not st.session_state.is_scraping:
        show_price_results(st.session_state.market_data)


def show_scraping_progress(search_query: str) -> None:
    """
    Show scraping progress indicator.

    Args:
        search_query: Current search query
    """
    st.markdown("### 🔄 Scraping Market Prices...")

    progress_bar = st.progress(0)
    status_text = st.empty()

    # Simulate scraping progress
    sources = ["PriceCheck.co.za", "Takealot.com", "Gumtree.co.za"]

    for i, source in enumerate(sources):
        status_text.text(f"Scraping {source}...")
        progress_bar.progress((i + 1) / len(sources))
        asyncio.run(asyncio.sleep(0.5))  # Simulate delay

    # Get market data
    market_data = get_mock_market_data(search_query)
    st.session_state.market_data = market_data
    st.session_state.is_scraping = False

    status_text.text("✅ Complete!")
    st.success(f"Found {market_data['total_listings']} listings across {len(market_data['sources_scraped'])} sources")

    st.rerun()


def show_price_results(market_data: Dict[str, Any]) -> None:
    """
    Display price check results.

    Args:
        market_data: Market data dictionary
    """
    st.markdown("---")

    # Search query header
    st.markdown(f"### 📊 Results for: **{market_data['search_query']}**")

    # Last updated
    scraped_at = market_data.get("scraped_at", "")
    if scraped_at:
        st.caption(f"Last updated: {scraped_at[:19]} SAST")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Market Median",
            value=format_zar(market_data["median_price"]),
        )

    with col2:
        st.metric(
            label="Lowest Price",
            value=format_zar(market_data["min_price"]),
            delta="Best Deal",
            delta_color="normal",
        )

    with col3:
        st.metric(
            label="Highest Price",
            value=format_zar(market_data["max_price"]),
        )

    with col4:
        st.metric(
            label="Total Listings",
            value=market_data["total_listings"],
        )

    st.markdown("---")

    # Price breakdown and recommendations
    col1, col2 = st.columns(2)

    with col1:
        show_price_recommendation(market_data)

    with col2:
        show_source_breakdown(market_data)

    # Market comparison
    st.markdown("---")
    show_market_chart(market_data)

    # Quote generator
    st.markdown("---")
    show_quote_generator(market_data)


def show_price_recommendation(market_data: Dict[str, Any]) -> None:
    """
    Show price recommendation.

    Args:
        market_data: Market data dictionary
    """
    st.markdown("### 💡 Price Recommendation")

    median = market_data["median_price"]

    # Calculate recommended prices
    suggested_buy = median * 0.7  # 30% below median for buying
    suggested_sell = median * 0.95  # 5% below median for competitive selling
    min_acceptable = median * 0.8  # Minimum acceptable price

    st.info(
        f"""
        **Suggested Buying Price:** {format_zar(suggested_buy)}
        
        Buy below this price for good margin potential.
        """
    )

    st.success(
        f"""
        **Suggested Selling Price:** {format_zar(suggested_sell)}
        
        Competitive price for quick sale while maintaining margin.
        """
    )

    st.warning(
        f"""
        **Minimum Acceptable:** {format_zar(min_acceptable)}
        
        Don't go below this unless clearing stock.
        """
    )

    # Condition-based adjustments
    st.markdown("**Condition Adjustments:**")

    conditions = {
        "New": ("+25-35%", "Premium pricing for sealed units"),
        "Refurbished": ("Base", "Market median reference"),
        "Used": ("-15-25%", "Depends on wear and battery health"),
        "Faulty": ("-50-70%", "For parts/repair only"),
    }

    for condition, (adjustment, note) in conditions.items():
        st.markdown(f"- **{condition}:** {adjustment} — {note}")


def show_source_breakdown(market_data: Dict[str, Any]) -> None:
    """
    Show price breakdown by source.

    Args:
        market_data: Market data dictionary
    """
    st.markdown("### 🏪 Prices by Source")

    price_by_source = market_data.get("price_by_source", {})

    for source, prices in price_by_source.items():
        if prices:
            avg_price = sum(prices) / len(prices)
            min_p = min(prices)
            max_p = max(prices)

            with st.expander(f"**{source}**", expanded=True):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Avg", format_zar(avg_price))

                with col2:
                    st.metric("Min", format_zar(min_p))

                with col3:
                    st.metric("Max", format_zar(max_p))

                # List individual prices
                st.markdown("**Individual Listings:**")
                for i, price in enumerate(prices, 1):
                    st.markdown(f"{i}. {format_zar(price)}")


def show_market_chart(market_data: Dict[str, Any]) -> None:
    """
    Show market price visualization.

    Args:
        market_data: Market data dictionary
    """
    st.markdown("### 📈 Price Distribution")

    try:
        import plotly.graph_objects as go

        # Prepare data
        price_by_source = market_data.get("price_by_source", {})

        # Create box plot
        fig = go.Figure()

        for source, prices in price_by_source.items():
            fig.add_trace(go.Box(
                y=prices,
                name=source,
                boxpoints="all",
                jitter=0.3,
                pointpos=-1.8,
            ))

        fig.update_layout(
            title="Price Distribution by Source",
            yaxis_title="Price (ZAR)",
            xaxis_title="Source",
            height=400,
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("Plotly not available. Install with: pip install plotly")

        # Fallback text display
        st.markdown("**Price Range by Source:**")
        for source, prices in market_data.get("price_by_source", {}).items():
            if prices:
                st.markdown(f"- **{source}:** {format_zar(min(prices))} - {format_zar(max(prices))}")


def show_quote_generator(market_data: Dict[str, Any]) -> None:
    """
    Show quote generator.

    Args:
        market_data: Market data dictionary
    """
    st.markdown("### 📝 Generate Quote")

    col1, col2 = st.columns(2)

    with col1:
        # Device details
        st.markdown("**Device Details**")
        device_brand = st.text_input("Brand", placeholder="e.g., Dell")
        device_model = st.text_input("Model", value=market_data["search_query"])
        device_serial = st.text_input("Serial Number", placeholder="Service tag")
        device_ram = st.selectbox("RAM", options=[4, 8, 16, 32, 64], index=2)
        device_storage = st.selectbox("Storage", options=[256, 512, 1024], index=1)
        device_condition = st.selectbox(
            "Condition",
            options=["refurbished", "used", "new", "faulty"],
            index=0,
        )

    with col2:
        # Pricing
        st.markdown("**Pricing**")

        median = market_data["median_price"]
        suggested_price = median * 0.95

        # Get condition multiplier
        condition_multipliers = {
            "new": 1.25,
            "refurbished": 1.0,
            "used": 0.8,
            "faulty": 0.5,
        }
        multiplier = condition_multipliers.get(device_condition, 1.0)

        calculated_price = suggested_price * multiplier

        quote_price = st.number_input(
            "Quote Price (R)",
            min_value=0.0,
            value=calculated_price,
            step=100.0,
        )

        valid_days = st.slider("Valid For (Days)", min_value=1, max_value=30, value=7)

        customer_name = st.text_input("Customer Name", placeholder="Optional")
        customer_email = st.text_input("Customer Email", placeholder="Optional")

    # Generate quote button
    if st.button("📄 Generate Quote", type="primary", use_container_width=True):
        device = {
            "brand": device_brand or "Unknown",
            "model": device_model,
            "serial_number": device_serial or "N/A",
            "ram_gb": device_ram,
            "storage_gb": device_storage,
            "condition": device_condition,
        }

        render_quote_snippet(device, quote_price, valid_days)

        # Download button for quote
        quote_text = f"""
QUOTE: {device_brand or 'Unknown'} {device_model}
Serial: {device_serial or 'N/A'}
Condition: {device_condition.title()}
Specs: {device_ram}GB RAM, {device_storage}GB SSD

Price: R {quote_price:,.2f}
Valid until: {(datetime.now() + timedelta(days=valid_days)).strftime('%Y-%m-%d')}

RefurbAdmin AI - Quality Refurbished IT
📞 011 123 4567 | 🌐 www.refurbadmin.co.za
""".strip()

        st.download_button(
            label="📥 Download Quote",
            data=quote_text,
            file_name=f"quote_{device_serial or 'device'}.txt",
            mime="text/plain",
        )


# Main entry point
if __name__ == "__main__":
    show_price_check_page()
else:
    # When imported as a page
    show_price_check_page()
