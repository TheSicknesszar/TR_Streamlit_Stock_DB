"""
RefurbAdmin AI - Frontend Dashboard

Streamlit-based dashboard for IT refurbishment inventory and pricing management.
South African context with ZAR currency and local retailer integration.

Usage:
    streamlit run frontend/app.py

Or use the batch file:
    run_frontend.bat
"""

import streamlit as st
import httpx
from datetime import datetime
from typing import Optional, Dict, Any

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="RefurbAdmin AI | Smart Pricing",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/refurbadmin",
        "Report a bug": "https://github.com/refurbadmin/issues",
        "About": "# RefurbAdmin AI\n\nSouth African IT Refurbishment Inventory & Pricing Platform",
    },
)

# Custom CSS for South African branding
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        font-weight: 600;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-active {
        background-color: #d1fae5;
        color: #065f46;
    }
    .status-pending {
        background-color: #fef3c7;
        color: #92400e;
    }
    .status-sold {
        background-color: #fee2e2;
        color: #991b1b;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# API Configuration
API_BASE_URL = "http://localhost:8000"


# Session state initialization
def init_session_state() -> None:
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "api_token" not in st.session_state:
        st.session_state.api_token = None
    if "sidebar_expanded" not in st.session_state:
        st.session_state.sidebar_expanded = True


def format_currency_zar(amount: float) -> str:
    """Format amount as South African Rand."""
    if amount is None:
        return "R 0.00"
    return f"R {amount:,.2f}"


def format_datetime_sast(dt: Optional[datetime]) -> str:
    """Format datetime in SAST timezone."""
    if not dt:
        return "N/A"
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d %H:%M SAST")


# Authentication functions
def login(username: str, password: str) -> bool:
    """
    Authenticate user.

    Args:
        username: Username
        password: Password

    Returns:
        bool: True if successful
    """
    # For demo purposes, accept any non-empty credentials
    # In production, this would call the API
    if username and password:
        st.session_state.authenticated = True
        st.session_state.user = username
        st.session_state.api_token = "demo_token"
        return True
    return False


def logout() -> None:
    """Log out current user."""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.api_token = None
    st.rerun()


# Login page
def show_login_page() -> None:
    """Display login page."""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            """
            <div style="text-align: center; padding: 2rem 0;">
                <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">💻 RefurbAdmin AI</h1>
                <p style="font-size: 1.2rem; color: #666;">Smart Pricing for IT Refurbishment</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input(
                "Password", type="password", placeholder="Enter your password"
            )

            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                submit = st.form_submit_button("Sign In", use_container_width=True)

            if submit:
                if login(username, password):
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")

        st.markdown("---")
        st.markdown(
            """
            <div style="text-align: center; color: #666; font-size: 0.9rem;">
                <p>🇿🇦 Made in South Africa | SAST Timezone</p>
                <p>Demo credentials: any username / any password</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# Main application
def show_main_app() -> None:
    """Display main application."""
    # Sidebar
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 1rem 0;">
                <h2 style="font-size: 1.5rem;">💻 RefurbAdmin</h2>
                <p style="font-size: 0.8rem; color: #666;">AI-Powered Pricing</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # User info
        st.markdown(f"**👤 Logged in as:** {st.session_state.user}")
        st.markdown(f"**🕐 Current time:** {datetime.now().strftime('%H:%M SAST')}")

        st.markdown("---")

        # Quick stats
        st.markdown("**📈 Quick Stats**")
        st.metric("Inventory Items", "24", delta="3 this week")
        st.metric("Avg. Margin", "22%", delta="+2%")

        st.markdown("---")

        # Logout button
        if st.button("🚪 Sign Out", use_container_width=True):
            logout()

        st.markdown("---")

        # Footer
        st.markdown(
            """
            <div style="text-align: center; font-size: 0.75rem; color: #888; padding: 1rem 0;">
                <p>🇿🇦 Made in South Africa | SAST Timezone</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# Home page content
def show_home() -> None:
    """Display home page content."""
    # Sidebar for authenticated users
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 1rem 0;">
                <h2 style="font-size: 1.5rem;">💻 RefurbAdmin</h2>
                <p style="font-size: 0.8rem; color: #666;">AI-Powered Pricing</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # User info
        st.markdown(f"**👤 Logged in as:** {st.session_state.user}")
        st.markdown(f"**🕐 Current time:** {datetime.now().strftime('%H:%M SAST')}")

        st.markdown("---")

        # Quick stats
        st.markdown("**📈 Quick Stats**")
        st.metric("Inventory Items", "24", delta="3 this week")
        st.metric("Avg. Margin", "22%", delta="+2%")

        st.markdown("---")

        # Logout button
        if st.button("🚪 Sign Out", use_container_width=True):
            logout()

        st.markdown("---")

        # Footer
        st.markdown(
            """
            <div style="text-align: center; font-size: 0.75rem; color: #888; padding: 1rem 0;">
                <p>🇿🇦 Made in South Africa | SAST Timezone</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="main-header">Welcome to RefurbAdmin AI</div>
        <div class="sub-header">Smart Pricing for South African IT Refurbishment</div>
        """,
        unsafe_allow_html=True,
    )

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-value">24</div>
                <div class="metric-label">Devices in Stock</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="metric-value">R 485k</div>
                <div class="metric-label">Total Value</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <div class="metric-value">22%</div>
                <div class="metric-label">Avg. Margin</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            """
            <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                <div class="metric-value">8</div>
                <div class="metric-label">Sold This Month</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Quick actions
    st.markdown("### ⚡ Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📦 Add New Device", use_container_width=True, type="primary"):
            st.switch_page("pages/01_Inventory.py")

    with col2:
        if st.button("💰 Check Market Price", use_container_width=True):
            st.switch_page("pages/02_Price_Check.py")

    with col3:
        if st.button("📊 View Reports", use_container_width=True):
            st.switch_page("pages/03_Reports.py")

    st.markdown("---")

    # Recent activity
    st.markdown("### 📋 Recent Activity")

    activity_data = {
        "Date": ["2026-04-01", "2026-03-31", "2026-03-30", "2026-03-29"],
        "Activity": [
            "Added Dell Latitude 5420 to inventory",
            "Sold HP EliteBook 840 G7",
            "Price updated for Lenovo ThinkPad T14",
            "Market scan completed for 15 devices",
        ],
        "User": ["Admin", "Admin", "System", "System"],
    }

    st.table(activity_data)

    # Market insights
    st.markdown("---")
    st.markdown("### 🌍 Market Insights")

    col1, col2 = st.columns(2)

    with col1:
        st.info(
            """
            **PriceCheck.co.za**\n\n
            Average Dell Latitude 5420 (16GB/512GB): **R 12,500**\n
            Trend: ⬆️ +3.5% this week
            """
        )

    with col2:
        st.info(
            """
            **Takealot.com**\n\n
            Refurbished laptops demand: **High**\n
            Best sellers: Business class (Latitude, EliteBook, ThinkPad)
            """
        )


# Main entry point
def main() -> None:
    """Main application entry point."""
    init_session_state()

    if not st.session_state.authenticated:
        show_login_page()
        return

    # Define pages for navigation
    pages = {
        "Home": st.Page(show_home, title="Home", icon="🏠"),
        "Inventory": st.Page("pages/01_Inventory.py", title="Inventory", icon="📦"),
        "Price Check": st.Page(
            "pages/02_Price_Check.py", title="Price Check", icon="💰"
        ),
        "Reports": st.Page("pages/03_Reports.py", title="Reports", icon="📊"),
        "WooCommerce": st.Page(
            "pages/05_WooCommerce.py", title="WooCommerce", icon="🛒"
        ),
        "Admin": st.Page("pages/04_Admin.py", title="Admin", icon="⚙️"),
    }

    # Create navigation with sidebar
    pg = st.navigation(list(pages.values()), position="sidebar")

    # Run the selected page
    pg.run()


if __name__ == "__main__":
    main()
