"""
RefurbAdmin AI - WooCommerce Stock Management Page

Streamlit page for managing WooCommerce product stock.
Features: sync stock, view products, update inventory, bulk actions.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from wooCommerce import get_woo_products, format_woo_products, WooCommerceAPI

st.set_page_config(
    page_title="WooCommerce Stock | RefurbAdmin AI",
    page_icon="🛒",
    layout="wide",
)


def init_session_state():
    """Initialize session state variables."""
    if "woo_products" not in st.session_state:
        st.session_state.woo_products = []
    if "woo_connected" not in st.session_state:
        st.session_state.woo_connected = False
    if "woo_last_sync" not in st.session_state:
        st.session_state.woo_last_sync = None
    if "woo_store_url" not in st.session_state:
        st.session_state.woo_store_url = "https://techrestored.co.za"
    if "woo_consumer_key" not in st.session_state:
        st.session_state.woo_consumer_key = (
            "ck_96a77a81971d519f74f91423c87f85d43b474003"
        )
    if "woo_consumer_secret" not in st.session_state:
        st.session_state.woo_consumer_secret = (
            "cs_290e37230811d657bb51f6a54c289cdbd90d5f9e"
        )


def render_woo_header():
    """Render the WooCommerce page header."""
    st.markdown(
        """
    <style>
    .woo-header {
        background: linear-gradient(135deg, #96588a 0%, #7f4c70 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .woo-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
    }
    .woo-header p {
        color: rgba(255,255,255,0.85);
        margin: 0.5rem 0 0 0;
    }
    .stat-card {
        background: white;
        border-radius: 10px;
        padding: 1.25rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
    }
    .stat-card .stat-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #2d3748;
    }
    .stat-card .stat-label {
        font-size: 0.875rem;
        color: #718096;
        margin-top: 0.25rem;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-instock { background: #c6f6d5; color: #22543d; }
    .status-outofstock { background: #fed7d7; color: #742a2a; }
    .status-onbackorder { background: #feebc8; color: #7c2d12; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="woo-header"><h1>🛒 WooCommerce Stock</h1><p>Sync and manage your online store inventory</p></div>',
        unsafe_allow_html=True,
    )


def render_connection_panel():
    """Render the connection configuration panel."""
    with st.expander("⚙️ Connection Settings", expanded=True):
        col1, col2, col3 = st.columns([3, 2, 2])

        with col1:
            store_url = st.text_input(
                "Store URL",
                value=st.session_state.woo_store_url,
                placeholder="https://yourstore.com",
                key="wc_store_url",
            )

        with col2:
            consumer_key = st.text_input(
                "Consumer Key",
                value=st.session_state.woo_consumer_key,
                type="password",
                key="wc_consumer_key",
            )

        with col3:
            consumer_secret = st.text_input(
                "Consumer Secret",
                value=st.session_state.woo_consumer_secret,
                type="password",
                key="wc_consumer_secret",
            )

        # Save credentials
        if store_url and consumer_key and consumer_secret:
            st.session_state.woo_store_url = store_url
            st.session_state.woo_consumer_key = consumer_key
            st.session_state.woo_consumer_secret = consumer_secret

        return store_url, consumer_key, consumer_secret


def render_sync_button(store_url: str, consumer_key: str, consumer_secret: str):
    """Render the sync button and handle sync action."""
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        sync_btn = st.button(
            "🔄 Sync Now",
            use_container_width=True,
            type="primary",
            disabled=not (store_url and consumer_key and consumer_secret),
        )

    with col2:
        auto_refresh = st.checkbox("Auto-refresh", value=False, key="wc_auto_refresh")

    with col3:
        if st.session_state.woo_last_sync:
            last_sync = datetime.fromisoformat(st.session_state.woo_last_sync)
            st.caption(f"Last synced: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.caption("Never synced")

    if sync_btn:
        with st.spinner("Connecting to WooCommerce..."):
            try:
                products = get_woo_products(store_url, consumer_key, consumer_secret)
                st.session_state.woo_products = format_woo_products(products)
                st.session_state.woo_connected = True
                st.session_state.woo_last_sync = datetime.now().isoformat()
                st.success(f"✅ Synced {len(st.session_state.woo_products)} products!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Connection failed: {str(e)}")

    return auto_refresh


def render_stats():
    """Render statistics cards."""
    if not st.session_state.woo_products:
        return

    products = st.session_state.woo_products
    in_stock = sum(1 for p in products if p["stock_status"] == "instock")
    out_of_stock = sum(1 for p in products if p["stock_status"] == "outofstock")
    on_backorder = sum(1 for p in products if p["stock_status"] == "onbackorder")
    total_stock = sum(p.get("stock_quantity") or 0 for p in products)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(
            f"""
        <div class="stat-card">
            <div class="stat-value">{len(products)}</div>
            <div class="stat-label">Total Products</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div class="stat-card">
            <div class="stat-value" style="color: #22c55e;">{in_stock}</div>
            <div class="stat-label">In Stock</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
        <div class="stat-card">
            <div class="stat-value" style="color: #ef4444;">{out_of_stock}</div>
            <div class="stat-label">Out of Stock</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
        <div class="stat-card">
            <div class="stat-value" style="color: #f59e0b;">{on_backorder}</div>
            <div class="stat-label">On Backorder</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col5:
        st.markdown(
            f"""
        <div class="stat-card">
            <div class="stat-value">{total_stock}</div>
            <div class="stat-label">Total Units</div>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_product_filters():
    """Render product filters."""
    if not st.session_state.woo_products:
        return

    products = st.session_state.woo_products
    brands = list(set(p.get("name", "").split()[0] for p in products if p.get("name")))

    col1, col2, col3 = st.columns(3)

    with col1:
        stock_filter = st.selectbox(
            "Stock Status",
            options=["All", "In Stock", "Out of Stock", "On Backorder"],
            key="wc_stock_filter",
        )

    with col2:
        search = st.text_input("🔍 Search products", key="wc_search")

    with col3:
        sort_by = st.selectbox(
            "Sort by",
            options=[
                "Name (A-Z)",
                "Name (Z-A)",
                "Stock (High-Low)",
                "Stock (Low-High)",
                "Price (High-Low)",
                "Price (Low-High)",
            ],
            key="wc_sort",
        )

    return stock_filter, search, sort_by


def filter_products(
    products: List[Dict], stock_filter: str, search: str, sort_by: str
) -> List[Dict]:
    """Filter and sort products."""
    filtered = products.copy()

    # Filter by stock status
    if stock_filter == "In Stock":
        filtered = [p for p in filtered if p["stock_status"] == "instock"]
    elif stock_filter == "Out of Stock":
        filtered = [p for p in filtered if p["stock_status"] == "outofstock"]
    elif stock_filter == "On Backorder":
        filtered = [p for p in filtered if p["stock_status"] == "onbackorder"]

    # Filter by search
    if search:
        search_lower = search.lower()
        filtered = [
            p
            for p in filtered
            if search_lower in p.get("name", "").lower()
            or search_lower in p.get("sku", "").lower()
        ]

    # Sort
    if sort_by == "Name (A-Z)":
        filtered.sort(key=lambda x: x.get("name", ""))
    elif sort_by == "Name (Z-A)":
        filtered.sort(key=lambda x: x.get("name", ""), reverse=True)
    elif sort_by == "Stock (High-Low)":
        filtered.sort(key=lambda x: x.get("stock_quantity") or 0, reverse=True)
    elif sort_by == "Stock (Low-High)":
        filtered.sort(key=lambda x: x.get("stock_quantity") or 0)
    elif sort_by == "Price (High-Low)":
        filtered.sort(key=lambda x: float(x.get("price", 0) or 0), reverse=True)
    elif sort_by == "Price (Low-High)":
        filtered.sort(key=lambda x: float(x.get("price", 0) or 0))

    return filtered


def render_product_table(products: List[Dict]):
    """Render the product data table."""
    if not products:
        st.info("No products found.")
        return

    df = pd.DataFrame(products)

    # Format for display
    display_df = df.copy()
    display_df["stock_status"] = display_df["stock_status"].map(
        {
            "instock": "🟢 In Stock",
            "outofstock": "🔴 Out of Stock",
            "onbackorder": "🟡 On Backorder",
        }
    )
    display_df["price"] = display_df["price"].apply(
        lambda x: f"R {float(x or 0):.2f}" if x else "—"
    )
    display_df["stock_quantity"] = display_df["stock_quantity"].fillna(0).astype(int)

    # Reorder columns
    display_df = display_df[
        ["name", "stock_quantity", "stock_status", "price", "total_sales"]
    ]
    display_df.columns = ["Product Name", "Stock", "Status", "Price", "Sales"]

    # Render table with custom styling
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Stock": st.column_config.NumberColumn(format="%d"),
            "Sales": st.column_config.NumberColumn(format="%d"),
        },
    )


def render_low_stock_alerts():
    """Render low stock alerts section."""
    if not st.session_state.woo_products:
        return

    low_stock = [
        p for p in st.session_state.woo_products if (p.get("stock_quantity") or 0) <= 5
    ]

    if low_stock:
        with st.expander(f"⚠️ Low Stock Alert ({len(low_stock)} items)", expanded=False):
            for product in low_stock:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{product.get('name', 'Unknown')}**")
                with col2:
                    st.write(f"SKU: `{product.get('sku', 'N/A')}`")
                with col3:
                    st.warning(f"Only {(product.get('stock_quantity') or 0)} left")
                st.divider()


def render_export_section():
    """Render export options."""
    if not st.session_state.woo_products:
        return

    with st.expander("📤 Export Data", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            df = pd.DataFrame(st.session_state.woo_products)
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="woo_products.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col2:
            json_str = json.dumps(st.session_state.woo_products, indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name="woo_products.json",
                mime="application/json",
                use_container_width=True,
            )


def show_woo_page():
    """Main WooCommerce page."""
    init_session_state()
    render_woo_header()

    # Connection panel
    store_url, consumer_key, consumer_secret = render_connection_panel()

    # Sync button
    auto_refresh = render_sync_button(store_url, consumer_key, consumer_secret)

    st.markdown("---")

    # Stats
    if st.session_state.woo_connected:
        render_stats()
        st.markdown("---")

        # Filters
        stock_filter, search, sort_by = render_product_filters()

        # Apply filters
        filtered = filter_products(
            st.session_state.woo_products,
            stock_filter,
            search,
            sort_by,
        )

        st.markdown(
            f"**Showing {len(filtered)} of {len(st.session_state.woo_products)} products**"
        )

        # Product table
        render_product_table(filtered)

        # Low stock alerts
        render_low_stock_alerts()

        # Export
        render_export_section()
    else:
        st.info(
            "👈 Enter your WooCommerce credentials above and click 'Sync Now' to connect to your store."
        )


if __name__ == "__main__":
    show_woo_page()
