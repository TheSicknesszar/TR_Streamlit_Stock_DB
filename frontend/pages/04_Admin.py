"""
Admin Dashboard for RefurbAdmin AI.

Streamlit page for system administration:
- User management
- API key management
- System configuration
- Audit log viewer
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Page config
st.set_page_config(
    page_title="Admin Dashboard - RefurbAdmin AI",
    page_icon="🔧",
    layout="wide",
)

# Title
st.title("🔧 Admin Dashboard")
st.markdown("---")

# Sidebar navigation
st.sidebar.title("Admin Menu")
admin_section = st.sidebar.radio(
    "Select Section",
    [
        "Dashboard Overview",
        "User Management",
        "API Keys",
        "System Configuration",
        "Audit Logs",
        "Backups",
    ],
)


# Mock data for demonstration
@st.cache_data
def get_mock_users() -> List[Dict]:
    return [
        {
            "id": 1,
            "name": "Admin User",
            "email": "admin@refurbadmin.co.za",
            "role": "admin",
            "status": "active",
        },
        {
            "id": 2,
            "name": "John Smith",
            "email": "john@example.co.za",
            "role": "user",
            "status": "active",
        },
        {
            "id": 3,
            "name": "Jane Doe",
            "email": "jane@example.co.za",
            "role": "user",
            "status": "inactive",
        },
    ]


@st.cache_data
def get_mock_api_keys() -> List[Dict]:
    return [
        {
            "id": 1,
            "name": "Production API",
            "key": "sk_prod_***",
            "created": "2024-01-01",
            "last_used": "2024-01-15",
            "status": "active",
        },
        {
            "id": 2,
            "name": "Development API",
            "key": "sk_dev_***",
            "created": "2024-01-05",
            "last_used": "2024-01-14",
            "status": "active",
        },
    ]


@st.cache_data
def get_mock_audit_logs() -> List[Dict]:
    return [
        {
            "id": 1,
            "event": "user.login",
            "user": "admin",
            "timestamp": "2024-01-15 10:30:00",
            "ip": "192.168.1.***",
        },
        {
            "id": 2,
            "event": "data.export",
            "user": "john",
            "timestamp": "2024-01-15 09:15:00",
            "ip": "192.168.1.***",
        },
        {
            "id": 3,
            "event": "config.change",
            "user": "admin",
            "timestamp": "2024-01-14 16:45:00",
            "ip": "192.168.1.***",
        },
    ]


# =============================================================================
# Dashboard Overview
# =============================================================================
if admin_section == "Dashboard Overview":
    st.header("📊 System Overview")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Users", "156", "+12%")

    with col2:
        st.metric("Active API Keys", "23", "+3%")

    with col3:
        st.metric("System Uptime", "99.9%", "✓")

    with col4:
        st.metric("Last Backup", "2 hours ago", "✓")

    st.markdown("---")

    # System health
    st.subheader("🏥 System Health")

    health_cols = st.columns(3)

    with health_cols[0]:
        st.success("✅ Database Connected")
        st.caption("PostgreSQL 16.0 - Response: 12ms")

    with health_cols[1]:
        st.success("✅ Cache Service")
        st.caption("Redis 7.0 - Hit Rate: 94%")

    with health_cols[2]:
        st.success("✅ Email Service")
        st.caption("SMTP Connected - Queue: 0")

    # Recent activity
    st.markdown("---")
    st.subheader("📈 Recent Activity")

    activity_data = get_mock_audit_logs()
    st.table(activity_data[:5])

# =============================================================================
# User Management
# =============================================================================
elif admin_section == "User Management":
    st.header("👥 User Management")

    # Action buttons
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input(
            "🔍 Search users", placeholder="Search by name or email..."
        )
    with col2:
        if st.button("➕ Add User", width="stretch"):
            st.session_state.show_add_user = True

    # Users table
    users = get_mock_users()

    if search:
        users = [
            u
            for u in users
            if search.lower() in u["name"].lower()
            or search.lower() in u["email"].lower()
        ]

    st.dataframe(
        users,
        column_config={
            "status": st.column_config.TextColumn(
                "Status",
                help="User account status",
            ),
        },
        width="stretch",
    )

    # User actions
    st.markdown("---")
    st.subheader("User Actions")

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        if st.button("📧 Send Welcome Email", width="stretch"):
            st.success("Welcome email sent!")

    with action_col2:
        if st.button("🔒 Reset Password", width="stretch"):
            st.warning("Password reset email sent to selected user")

    with action_col3:
        if st.button("⚠️ Deactivate User", width="stretch"):
            st.error("User deactivated successfully")

# =============================================================================
# API Keys
# =============================================================================
elif admin_section == "API Keys":
    st.header("🔑 API Key Management")

    # Create new key
    with st.expander("➕ Create New API Key"):
        key_name = st.text_input("Key Name")
        key_tier = st.selectbox("Tier", ["standard", "premium", "enterprise"])
        key_expiry = st.date_input(
            "Expiry Date", value=datetime.now() + timedelta(days=365)
        )

        if st.button("Generate Key"):
            st.code(f"sk_{key_tier[:3]}_{'x' * 32}", language="text")
            st.success("API key generated! Copy it now - you won't see it again.")

    # Existing keys
    st.subheader("Active API Keys")

    api_keys = get_mock_api_keys()

    for key in api_keys:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])

            col1.write(f"**{key['name']}**")
            col2.code(key["key"], language="text")
            col3.write(f"Created: {key['created']}")
            col4.write(f"Last used: {key['last_used']}")

            if col5.button("🗑️", key=f"delete_{key['id']}"):
                st.warning(f"API key '{key['name']}' revoked")

            st.divider()

# =============================================================================
# System Configuration
# =============================================================================
elif admin_section == "System Configuration":
    st.header("⚙️ System Configuration")

    tab1, tab2, tab3, tab4 = st.tabs(["General", "Email", "WhatsApp", "Security"])

    with tab1:
        st.subheader("General Settings")

        st.text_input("Company Name", value="RefurbAdmin AI")
        st.text_input("Company Address", value="123 Main Street, Johannesburg, 2001")
        st.text_input("Phone Number", value="0800 REFURB")
        st.text_input("Email", value="info@refurbadmin.co.za")

        st.selectbox("Currency", ["ZAR (R)", "USD ($)", "EUR (€)"])
        st.selectbox("Timezone", ["Africa/Johannesburg", "UTC"])

        if st.button("💾 Save General Settings"):
            st.success("Settings saved successfully!")

    with tab2:
        st.subheader("Email Configuration")

        st.text_input("SMTP Host", value="smtp.gmail.com")
        st.number_input("SMTP Port", value=587)
        st.text_input("SMTP Username", value="noreply@refurbadmin.co.za")
        st.text_input("SMTP Password", type="password")
        st.checkbox("Use TLS", value=True)

        if st.button("📧 Test Email Configuration"):
            st.success("Email configuration test passed!")

    with tab3:
        st.subheader("WhatsApp Configuration")

        st.checkbox("Enable WhatsApp Notifications")
        st.selectbox("Provider", ["Twilio", "360dialog", "Meta"])
        st.text_input("API Key", type="password")
        st.text_input("WhatsApp Number", value="+27123456789")

        if st.button("💬 Test WhatsApp"):
            st.info("Test WhatsApp message sent!")

    with tab4:
        st.subheader("Security Settings")

        st.number_input("Session Timeout (minutes)", value=60)
        st.number_input("Max Login Attempts", value=5)
        st.checkbox("Enable 2FA", value=True)
        st.checkbox("Enable Audit Logging", value=True)
        st.number_input("Password Min Length", value=10)

        if st.button("🔒 Save Security Settings"):
            st.success("Security settings updated!")

# =============================================================================
# Audit Logs
# =============================================================================
elif admin_section == "Audit Logs":
    st.header("📋 Audit Logs")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        event_type = st.selectbox(
            "Event Type", ["All", "auth", "data", "admin", "security"]
        )

    with col2:
        date_range = st.date_input(
            "Date Range", [datetime.now() - timedelta(days=7), datetime.now()]
        )

    with col3:
        if st.button("📥 Export Logs"):
            st.success("Logs exported to CSV!")

    # Logs table
    logs = get_mock_audit_logs()

    st.dataframe(
        logs,
        width="stretch",
        height=400,
    )

    # Log details
    st.markdown("---")
    st.subheader("Log Details")

    selected_log = st.selectbox(
        "Select Log Entry", [f"#{l['id']}: {l['event']}" for l in logs]
    )

    if selected_log:
        log_id = int(selected_log.split(":")[0].replace("#", ""))
        log = next((l for l in logs if l["id"] == log_id), None)

        if log:
            st.json(log)

# =============================================================================
# Backups
# =============================================================================
elif admin_section == "Backups":
    st.header("💾 Database Backups")

    # Backup status
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Last Backup", "2 hours ago")

    with col2:
        st.metric("Next Scheduled", "in 22 hours")

    with col3:
        st.metric("Storage Used", "245 MB")

    st.markdown("---")

    # Backup actions
    st.subheader("Backup Actions")

    action1, action2, action3 = st.columns(3)

    with action1:
        if st.button("🔄 Create Backup Now", width="stretch"):
            with st.spinner("Creating backup..."):
                st.success("Backup created successfully!")

    with action2:
        if st.button("📥 Download Latest", width="stretch"):
            st.info("Download started: backup_20240115.sql.gz")

    with action3:
        if st.button("⚠️ Restore Backup", width="stretch"):
            st.warning("Restore functionality requires confirmation")

    # Backup history
    st.markdown("---")
    st.subheader("Backup History")

    backup_history = [
        {
            "filename": "backup_20240115_020000.sql.gz",
            "size": "24.5 MB",
            "created": "2024-01-15 02:00:00",
            "status": "✓",
        },
        {
            "filename": "backup_20240114_020000.sql.gz",
            "size": "24.3 MB",
            "created": "2024-01-14 02:00:00",
            "status": "✓",
        },
        {
            "filename": "backup_20240113_020000.sql.gz",
            "size": "24.1 MB",
            "created": "2024-01-13 02:00:00",
            "status": "✓",
        },
    ]

    st.dataframe(backup_history, width="stretch")

# Footer
st.markdown("---")
st.caption(
    f"RefurbAdmin AI v1.0.0 | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 🇿🇦 South Africa"
)
