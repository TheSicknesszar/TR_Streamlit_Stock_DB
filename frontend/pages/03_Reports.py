"""
RefurbAdmin AI - Reports & Analytics Page

Streamlit page for business analytics and reporting.
Features: inventory velocity, margin analysis, sales metrics, charts.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Page configuration
st.set_page_config(
    page_title="Reports | RefurbAdmin AI",
    page_icon="📊",
    layout="wide",
)


# Mock data for demonstration
def get_mock_sales_data() -> List[Dict[str, Any]]:
    """Get mock sales data."""
    return [
        {
            "date": "2026-03-01",
            "device": "Dell Latitude 5420",
            "cost": 8500,
            "sale_price": 12500,
            "margin": 4000,
        },
        {
            "date": "2026-03-05",
            "device": "HP EliteBook 840 G7",
            "cost": 9000,
            "sale_price": 13500,
            "margin": 4500,
        },
        {
            "date": "2026-03-10",
            "device": "Lenovo ThinkPad T14",
            "cost": 10000,
            "sale_price": 15000,
            "margin": 5000,
        },
        {
            "date": "2026-03-15",
            "device": "Dell Latitude 7490",
            "cost": 5500,
            "sale_price": 8500,
            "margin": 3000,
        },
        {
            "date": "2026-03-20",
            "device": "HP EliteBook 850 G5",
            "cost": 7500,
            "sale_price": 11000,
            "margin": 3500,
        },
        {
            "date": "2026-03-25",
            "device": "Dell Precision 5540",
            "cost": 15000,
            "sale_price": 22000,
            "margin": 7000,
        },
        {
            "date": "2026-03-28",
            "device": "Lenovo ThinkPad X1",
            "cost": 12000,
            "sale_price": 17500,
            "margin": 5500,
        },
        {
            "date": "2026-04-01",
            "device": "HP ZBook 15",
            "cost": 18000,
            "sale_price": 26000,
            "margin": 8000,
        },
    ]


def get_mock_inventory_data() -> List[Dict[str, Any]]:
    """Get mock inventory data."""
    return [
        {
            "brand": "Dell",
            "model": "Latitude 5420",
            "status": "ready",
            "days_in_stock": 15,
            "value": 12500,
        },
        {
            "brand": "HP",
            "model": "EliteBook 840 G7",
            "status": "listed",
            "days_in_stock": 8,
            "value": 13500,
        },
        {
            "brand": "Lenovo",
            "model": "ThinkPad T14",
            "status": "refurbishing",
            "days_in_stock": 5,
            "value": 16000,
        },
        {
            "brand": "Dell",
            "model": "Latitude 7490",
            "status": "inspecting",
            "days_in_stock": 3,
            "value": 8500,
        },
        {
            "brand": "HP",
            "model": "EliteBook 850 G5",
            "status": "sold",
            "days_in_stock": 25,
            "value": 11000,
        },
        {
            "brand": "Dell",
            "model": "Precision 5540",
            "status": "ready",
            "days_in_stock": 20,
            "value": 25000,
        },
        {
            "brand": "Lenovo",
            "model": "ThinkPad X1",
            "status": "listed",
            "days_in_stock": 12,
            "value": 18000,
        },
        {
            "brand": "HP",
            "model": "ZBook 15",
            "status": "refurbishing",
            "days_in_stock": 7,
            "value": 28000,
        },
    ]


def show_reports_page() -> None:
    """Display reports and analytics page."""
    # Header
    st.markdown(
        """
        <div class="main-header">📊 Reports & Analytics</div>
        <div class="sub-header">Business insights and performance metrics</div>
        """,
        unsafe_allow_html=True,
    )

    # Date range selector
    st.markdown("### 📅 Date Range")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30),
            key="report_start_date",
        )

    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            key="report_end_date",
        )

    with col3:
        if st.button("🔄 Refresh", width="stretch"):
            st.rerun()

    # Load data
    sales_data = get_mock_sales_data()
    inventory_data = get_mock_inventory_data()

    # Convert to DataFrames
    sales_df = pd.DataFrame(sales_data)
    sales_df["date"] = pd.to_datetime(sales_df["date"])
    inventory_df = pd.DataFrame(inventory_data)

    # Filter by date range
    mask = (sales_df["date"] >= pd.to_datetime(start_date)) & (
        sales_df["date"] <= pd.to_datetime(end_date)
    )
    filtered_sales = sales_df[mask]

    # Key metrics
    st.markdown("### 📈 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    total_revenue = (
        filtered_sales["sale_price"].sum() if not filtered_sales.empty else 0
    )
    total_cost = filtered_sales["cost"].sum() if not filtered_sales.empty else 0
    total_margin = filtered_sales["margin"].sum() if not filtered_sales.empty else 0
    avg_margin_pct = (total_margin / total_revenue * 100) if total_revenue > 0 else 0

    with col1:
        st.metric(
            label="Total Revenue",
            value=f"R {total_revenue:,.0f}",
            delta=f"{len(filtered_sales)} sales",
        )

    with col2:
        st.metric(
            label="Total Margin",
            value=f"R {total_margin:,.0f}",
            delta=f"{avg_margin_pct:.1f}% avg",
            delta_color="normal",
        )

    with col3:
        inventory_value = sum(
            item["value"] for item in inventory_data if item["status"] != "sold"
        )
        st.metric(
            label="Inventory Value",
            value=f"R {inventory_value:,.0f}",
            delta=f"{len(inventory_data)} devices",
        )

    with col4:
        ready_count = len([i for i in inventory_data if i["status"] == "ready"])
        st.metric(
            label="Ready to Sell",
            value=ready_count,
            delta=f"R {ready_count * 13000:,.0f} est.",
        )

    st.markdown("---")

    # Tabs for different reports
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📊 Sales Trends",
            "🔄 Inventory Velocity",
            "💰 Margin Analysis",
            "📦 Brand Performance",
        ]
    )

    with tab1:
        show_sales_trends(filtered_sales)

    with tab2:
        show_inventory_velocity(inventory_df)

    with tab3:
        show_margin_analysis(filtered_sales)

    with tab4:
        show_brand_performance(inventory_df, filtered_sales)


def show_sales_trends(sales_df: pd.DataFrame) -> None:
    """
    Show sales trends chart.

    Args:
        sales_df: Sales data DataFrame
    """
    st.markdown("### Sales Trends")

    if sales_df.empty:
        st.info("No sales data for selected period.")
        return

    try:
        import plotly.graph_objects as go
        import plotly.express as px

        # Group by date
        daily_sales = (
            sales_df.groupby("date")
            .agg(
                {
                    "sale_price": "sum",
                    "margin": "sum",
                    "device": "count",
                }
            )
            .reset_index()
        )
        daily_sales.columns = ["date", "revenue", "margin", "units"]

        # Create figure
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=daily_sales["date"],
                y=daily_sales["revenue"],
                name="Revenue",
                line=dict(color="#0078D4", width=3),
                fill="tozeroy",
                fillcolor="rgba(0, 120, 212, 0.1)",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=daily_sales["date"],
                y=daily_sales["margin"],
                name="Margin",
                line=dict(color="#107C10", width=2, dash="dash"),
            )
        )

        fig.update_layout(
            title="Daily Revenue and Margin",
            xaxis_title="Date",
            yaxis_title="Amount (ZAR)",
            height=400,
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1),
        )

        st.plotly_chart(fig, width="stretch")

        # Summary stats
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Avg Daily Revenue", f"R {daily_sales['revenue'].mean():,.0f}")

        with col2:
            st.metric("Avg Daily Margin", f"R {daily_sales['margin'].mean():,.0f}")

        with col3:
            st.metric("Avg Units/Day", f"{daily_sales['units'].mean():.1f}")

    except ImportError:
        st.warning("Plotly not available. Install with: pip install plotly")

        # Fallback table
        st.dataframe(sales_df, width="stretch")


def show_inventory_velocity(inventory_df: pd.DataFrame) -> None:
    """
    Show inventory velocity analysis.

    Args:
        inventory_df: Inventory data DataFrame
    """
    st.markdown("### Inventory Velocity")

    # Status distribution
    st.markdown("**Status Distribution**")

    status_counts = inventory_df["status"].value_counts()

    col1, col2 = st.columns(2)

    with col1:
        try:
            import plotly.express as px

            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Devices by Status",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            st.plotly_chart(fig, width="stretch")

        except ImportError:
            for status, count in status_counts.items():
                st.markdown(f"- **{status.title()}:** {count}")

    with col2:
        # Days in stock analysis
        st.markdown("**Average Days in Stock by Status**")

        days_by_status = (
            inventory_df.groupby("status")["days_in_stock"].mean().sort_values()
        )

        for status, days in days_by_status.items():
            delta_color = "normal" if days < 14 else "inverse"
            st.metric(status.title(), f"{days:.1f} days", delta_color=delta_color)

    st.markdown("---")

    # Inventory aging
    st.markdown("**Inventory Aging**")

    aging_buckets = {
        "0-7 days": len([i for i in inventory_df["days_in_stock"] if i <= 7]),
        "8-14 days": len([i for i in inventory_df["days_in_stock"] if 8 <= i <= 14]),
        "15-30 days": len([i for i in inventory_df["days_in_stock"] if 15 <= i <= 30]),
        "30+ days": len([i for i in inventory_df["days_in_stock"] if i > 30]),
    }

    try:
        import plotly.graph_objects as go

        fig = go.Figure(
            go.Bar(
                x=list(aging_buckets.keys()),
                y=list(aging_buckets.values()),
                marker_color=["#107C10", "#FFB900", "#FF8C00", "#D13438"],
            )
        )

        fig.update_layout(
            title="Devices by Age in Stock",
            xaxis_title="Age Range",
            yaxis_title="Count",
            height=300,
        )

        st.plotly_chart(fig, width="stretch")

    except ImportError:
        for bucket, count in aging_buckets.items():
            st.markdown(f"- **{bucket}:** {count} devices")

    # Slow-moving inventory alert
    slow_moving = inventory_df[inventory_df["days_in_stock"] > 21]
    if not slow_moving.empty:
        st.warning(f"⚠️ {len(slow_moving)} devices have been in stock for over 21 days")


def show_margin_analysis(sales_df: pd.DataFrame) -> None:
    """
    Show margin analysis.

    Args:
        sales_df: Sales data DataFrame
    """
    st.markdown("### Margin Analysis")

    if sales_df.empty:
        st.info("No sales data for selected period.")
        return

    # Calculate margin percentage
    sales_df["margin_pct"] = (sales_df["margin"] / sales_df["sale_price"]) * 100

    # Overall stats
    col1, col2, col3 = st.columns(3)

    with col1:
        avg_margin_pct = sales_df["margin_pct"].mean()
        st.metric("Average Margin %", f"{avg_margin_pct:.1f}%")

    with col2:
        best_margin = sales_df.loc[sales_df["margin_pct"].idxmax()]
        st.metric(
            "Best Margin",
            f"{best_margin['margin_pct']:.1f}%",
            delta=best_margin["device"][:20],
        )

    with col3:
        worst_margin = sales_df.loc[sales_df["margin_pct"].idxmin()]
        st.metric(
            "Lowest Margin",
            f"{worst_margin['margin_pct']:.1f}%",
            delta=worst_margin["device"][:20],
            delta_color="inverse",
        )

    st.markdown("---")

    # Margin distribution
    try:
        import plotly.express as px

        fig = px.histogram(
            sales_df,
            x="margin_pct",
            nbins=10,
            title="Margin Percentage Distribution",
            labels={"margin_pct": "Margin %"},
            color_discrete_sequence=["#0078D4"],
        )

        fig.update_layout(
            xaxis_title="Margin %",
            yaxis_title="Number of Sales",
            height=400,
        )

        st.plotly_chart(fig, width="stretch")

    except ImportError:
        st.warning("Plotly not available.")

    # Sales by margin bracket
    st.markdown("**Sales by Margin Bracket**")

    brackets = {
        "Excellent (>35%)": len([m for m in sales_df["margin_pct"] if m > 35]),
        "Good (25-35%)": len([m for m in sales_df["margin_pct"] if 25 <= m <= 35]),
        "Average (15-25%)": len([m for m in sales_df["margin_pct"] if 15 <= m < 25]),
        "Low (<15%)": len([m for m in sales_df["margin_pct"] if m < 15]),
    }

    cols = st.columns(4)
    colors = ["#107C10", "#FFB900", "#FF8C00", "#D13438"]

    for i, (bracket, count) in enumerate(brackets.items()):
        with cols[i]:
            st.metric(bracket.split(" ")[0], count)

    # Individual sales table
    st.markdown("---")
    st.markdown("**Individual Sales**")

    display_df = sales_df[
        ["date", "device", "cost", "sale_price", "margin", "margin_pct"]
    ].copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    display_df.columns = [
        "Date",
        "Device",
        "Cost",
        "Sale Price",
        "Margin (R)",
        "Margin %",
    ]

    st.dataframe(display_df, width="stretch")


def show_brand_performance(inventory_df: pd.DataFrame, sales_df: pd.DataFrame) -> None:
    """
    Show brand performance analysis.

    Args:
        inventory_df: Inventory data DataFrame
        sales_df: Sales data DataFrame
    """
    st.markdown("### Brand Performance")

    # Inventory by brand
    st.markdown("**Current Inventory by Brand**")

    brand_inventory = (
        inventory_df.groupby("brand")
        .agg(
            {
                "value": "sum",
                "model": "count",
                "days_in_stock": "mean",
            }
        )
        .reset_index()
    )
    brand_inventory.columns = ["Brand", "Total Value", "Units", "Avg Days in Stock"]

    col1, col2 = st.columns(2)

    with col1:
        try:
            import plotly.express as px

            fig = px.bar(
                brand_inventory,
                x="Brand",
                y="Total Value",
                title="Inventory Value by Brand",
                color="Total Value",
                color_continuous_scale="Blues",
            )

            st.plotly_chart(fig, width="stretch")

        except ImportError:
            st.dataframe(brand_inventory, width="stretch")

    with col2:
        # Brand metrics
        for _, row in brand_inventory.iterrows():
            with st.expander(f"**{row['Brand']}**"):
                st.metric("Units", int(row["Units"]))
                st.metric("Total Value", f"R {row['Total Value']:,.0f}")
                st.metric("Avg Days", f"{row['Avg Days in Stock']:.1f}")

    st.markdown("---")

    # Sales by brand (if available)
    if not sales_df.empty:
        st.markdown("**Sales by Brand**")

        # Extract brand from device name
        sales_df["brand"] = sales_df["device"].apply(lambda x: x.split()[0])

        brand_sales = (
            sales_df.groupby("brand")
            .agg(
                {
                    "sale_price": "sum",
                    "margin": "sum",
                    "device": "count",
                }
            )
            .reset_index()
        )
        brand_sales.columns = ["Brand", "Revenue", "Margin", "Units Sold"]

        try:
            import plotly.graph_objects as go

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    name="Revenue",
                    x=brand_sales["Brand"],
                    y=brand_sales["Revenue"],
                    marker_color="#0078D4",
                )
            )

            fig.add_trace(
                go.Bar(
                    name="Margin",
                    x=brand_sales["Brand"],
                    y=brand_sales["Margin"],
                    marker_color="#107C10",
                )
            )

            fig.update_layout(
                title="Revenue and Margin by Brand",
                barmode="group",
                height=400,
            )

            st.plotly_chart(fig, width="stretch")

        except ImportError:
            st.dataframe(brand_sales, width="stretch")

    # Recommendations
    st.markdown("---")
    st.markdown("### 💡 Recommendations")

    # Find best and worst performers
    if not inventory_df.empty:
        fastest_selling = inventory_df.loc[inventory_df["days_in_stock"].idxmin()]
        slowest_selling = inventory_df.loc[inventory_df["days_in_stock"].idxmax()]

        col1, col2 = st.columns(2)

        with col1:
            st.success(
                f"""
                **Fast Mover:** {fastest_selling["brand"]} {fastest_selling["model"]}
                
                Only {fastest_selling["days_in_stock"]} days in stock.
                Consider stocking more of this model.
                """
            )

        with col2:
            st.warning(
                f"""
                **Slow Mover:** {slowest_selling["brand"]} {slowest_selling["model"]}
                
                {slowest_selling["days_in_stock"]} days in stock.
                Consider price adjustment or promotion.
                """
            )


# Main entry point
if __name__ == "__main__":
    show_reports_page()
else:
    # When imported as a page
    show_reports_page()
