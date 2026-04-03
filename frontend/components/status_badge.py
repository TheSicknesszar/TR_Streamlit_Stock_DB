"""
RefurbAdmin AI - Status Badge Component

Reusable component for displaying status indicators with colors.
"""

import streamlit as st
from typing import Optional
from enum import Enum


class StatusType(str, Enum):
    """Device status types."""
    PENDING = "pending"
    INSPECTING = "inspecting"
    REFURBISHING = "refurbishing"
    READY = "ready"
    LISTED = "listed"
    RESERVED = "reserved"
    SOLD = "sold"
    ARCHIVED = "archived"


# Status configuration
STATUS_CONFIG = {
    StatusType.PENDING: {
        "label": "Pending",
        "icon": "⏳",
        "bg_color": "#fef3c7",
        "text_color": "#92400e",
        "description": "Awaiting inspection",
    },
    StatusType.INSPECTING: {
        "label": "Inspecting",
        "icon": "🔍",
        "bg_color": "#dbeafe",
        "text_color": "#1e40af",
        "description": "Under inspection",
    },
    StatusType.REFURBISHING: {
        "label": "Refurbishing",
        "icon": "🔧",
        "bg_color": "#e0e7ff",
        "text_color": "#3730a3",
        "description": "Being refurbished",
    },
    StatusType.READY: {
        "label": "Ready",
        "icon": "✅",
        "bg_color": "#d1fae5",
        "text_color": "#065f46",
        "description": "Ready for sale",
    },
    StatusType.LISTED: {
        "label": "Listed",
        "icon": "📢",
        "bg_color": "#cffafe",
        "text_color": "#0e7490",
        "description": "Actively listed",
    },
    StatusType.RESERVED: {
        "label": "Reserved",
        "icon": "🔒",
        "bg_color": "#fef9c3",
        "text_color": "#854d0e",
        "description": "Reserved for customer",
    },
    StatusType.SOLD: {
        "label": "Sold",
        "icon": "💰",
        "bg_color": "#fee2e2",
        "text_color": "#991b1b",
        "description": "Sold",
    },
    StatusType.ARCHIVED: {
        "label": "Archived",
        "icon": "📁",
        "bg_color": "#f3f4f6",
        "text_color": "#374151",
        "description": "Archived",
    },
}


def render_status_badge(
    status: str,
    show_label: bool = True,
    show_icon: bool = True,
    size: str = "medium",
) -> str:
    """
    Render a status badge as HTML.

    Args:
        status: Status string
        show_label: Whether to show label text
        show_icon: Whether to show icon
        size: Badge size ('small', 'medium', 'large')

    Returns:
        HTML string for the badge
    """
    config = get_status_config(status)

    # Size configuration
    sizes = {
        "small": {"padding": "0.15rem 0.5rem", "font": "0.7rem"},
        "medium": {"padding": "0.25rem 0.75rem", "font": "0.8rem"},
        "large": {"padding": "0.4rem 1rem", "font": "0.9rem"},
    }
    size_config = sizes.get(size, sizes["medium"])

    # Build badge content
    content = ""
    if show_icon:
        content += f"{config['icon']} "
    if show_label:
        content += config['label']

    html = f"""
    <span style="
        display: inline-block;
        padding: {size_config['padding']};
        border-radius: 9999px;
        font-size: {size_config['font']};
        font-weight: 600;
        background-color: {config['bg_color']};
        color: {config['text_color']};
        white-space: nowrap;
    ">
        {content.strip()}
    </span>
    """

    return html


def render_status_badge_streamlit(
    status: str,
    show_label: bool = True,
    show_icon: bool = True,
    size: str = "medium",
) -> None:
    """
    Render a status badge using Streamlit markdown.

    Args:
        status: Status string
        show_label: Whether to show label text
        show_icon: Whether to show icon
        size: Badge size ('small', 'medium', 'large')
    """
    html = render_status_badge(status, show_label, show_icon, size)
    st.markdown(html, unsafe_allow_html=True)


def get_status_config(status: str) -> dict:
    """
    Get configuration for a status.

    Args:
        status: Status string

    Returns:
        Configuration dictionary
    """
    try:
        status_enum = StatusType(status.lower())
        return STATUS_CONFIG[status_enum]
    except (ValueError, KeyError):
        # Default configuration for unknown status
        return {
            "label": status.title(),
            "icon": "❓",
            "bg_color": "#f3f4f6",
            "text_color": "#374151",
            "description": "Unknown status",
        }


def get_status_description(status: str) -> str:
    """
    Get description for a status.

    Args:
        status: Status string

    Returns:
        Description string
    """
    config = get_status_config(status)
    return config.get("description", "")


def render_status_selector(
    key: str = "status_selector",
    default: str = "pending",
    label: str = "Status",
    exclude: Optional[list] = None,
) -> str:
    """
    Render a status selector dropdown.

    Args:
        key: Streamlit widget key
        default: Default selected value
        label: Label for the selector
        exclude: List of statuses to exclude

    Returns:
        Selected status value
    """
    exclude = exclude or []

    options = []
    for status_type in StatusType:
        if status_type.value not in exclude:
            config = STATUS_CONFIG[status_type]
            options.append(f"{config['icon']} {config['label']}")

    # Find index of default
    default_config = get_status_config(default)
    default_label = f"{default_config['icon']} {default_config['label']}"

    try:
        default_index = options.index(default_label)
    except ValueError:
        default_index = 0

    selected = st.selectbox(
        label,
        options=options,
        index=default_index,
        key=key,
    )

    # Convert back to status value
    selected_status = selected.split(" ", 1)[1].lower() if " " in selected else selected.lower()

    # Map back to enum value
    for status_type in StatusType:
        config = STATUS_CONFIG[status_type]
        if config['label'].lower() == selected_status:
            return status_type.value

    return default


def render_status_timeline(current_status: str) -> None:
    """
    Render a status timeline showing progress.

    Args:
        current_status: Current device status
    """
    # Define timeline order
    timeline = [
        StatusType.PENDING,
        StatusType.INSPECTING,
        StatusType.REFURBISHING,
        StatusType.READY,
        StatusType.LISTED,
        StatusType.SOLD,
    ]

    try:
        current_index = timeline.index(StatusType(current_status.lower()))
    except ValueError:
        current_index = 0

    st.markdown("**Status Progress**")

    # Create timeline visualization
    cols = st.columns(len(timeline))

    for i, (col, status_type) in enumerate(zip(cols, timeline)):
        config = STATUS_CONFIG[status_type]
        is_current = i == current_index
        is_past = i < current_index

        if is_current:
            col.markdown(f"**{config['icon']} {config['label']}**")
            col.caption("← Current")
        elif is_past:
            col.markdown(f"✅ {config['label']}")
        else:
            col.markdown(f"⚪ {config['label']}")

    # Progress bar
    progress = (current_index + 1) / len(timeline)
    st.progress(progress)


def render_status_filter(key: str = "status_filter", label: str = "Filter by Status") -> Optional[str]:
    """
    Render a status filter dropdown.

    Args:
        key: Streamlit widget key
        label: Label for the filter

    Returns:
        Selected status or None for "All"
    """
    options = ["All"] + [f"{STATUS_CONFIG[s]['icon']} {STATUS_CONFIG[s]['label']}" for s in StatusType]

    selected = st.selectbox(
        label,
        options=options,
        key=key,
    )

    if selected == "All":
        return None

    # Extract status value
    selected_text = selected.split(" ", 1)[1] if " " in selected else selected
    for status_type, config in STATUS_CONFIG.items():
        if config['label'] == selected_text:
            return status_type.value

    return None
