#!/usr/bin/env python3
"""
LogSleuth Dashboard - Streamlit-based incident investigation interface.

Run with: streamlit run src/dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import html
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Page config
st.set_page_config(
    page_title="LogSleuth - Incident Investigator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════════
# ENTERPRISE COMMAND CENTER CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    /* ══════════════════════════════════════════════════════════════════════════
       TYPOGRAPHY - Enterprise-grade fonts
       Plus Jakarta Sans: Clean, professional headers
       IBM Plex Mono: Technical precision for data
       ══════════════════════════════════════════════════════════════════════════ */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    /* ══════════════════════════════════════════════════════════════════════════
       CSS VARIABLES - Enterprise Command Center Palette
       Deep navy foundation with emerald accents - Bloomberg/Datadog inspired
       ══════════════════════════════════════════════════════════════════════════ */
    :root {
        /* Base colors - Deep navy foundation */
        --bg-void: #030712;
        --bg-primary: #0B1120;
        --bg-secondary: #111827;
        --bg-elevated: #1F2937;
        --bg-surface: rgba(17, 24, 39, 0.95);

        /* Border system */
        --border-default: rgba(55, 65, 81, 0.5);
        --border-subtle: rgba(55, 65, 81, 0.3);
        --border-focus: #10B981;

        /* Text hierarchy */
        --text-primary: #F9FAFB;
        --text-secondary: #9CA3AF;
        --text-tertiary: #6B7280;
        --text-muted: #4B5563;

        /* Accent palette */
        --accent-primary: #10B981;
        --accent-primary-hover: #059669;
        --accent-primary-subtle: rgba(16, 185, 129, 0.15);
        --accent-primary-glow: rgba(16, 185, 129, 0.4);

        /* Status colors */
        --status-critical: #EF4444;
        --status-critical-subtle: rgba(239, 68, 68, 0.15);
        --status-warning: #F59E0B;
        --status-warning-subtle: rgba(245, 158, 11, 0.15);
        --status-success: #10B981;
        --status-success-subtle: rgba(16, 185, 129, 0.15);
        --status-info: #3B82F6;
        --status-info-subtle: rgba(59, 130, 246, 0.15);

    }

    /* ══════════════════════════════════════════════════════════════════════════
       GLOBAL STYLES - Mission Control Foundation
       ══════════════════════════════════════════════════════════════════════════ */
    .stApp {
        background: var(--bg-void);
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       SIDEBAR - Control Panel
       ══════════════════════════════════════════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: var(--bg-primary) !important;
        border-right: 1px solid var(--border-default) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: var(--text-secondary);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        font-size: 0.875rem;
        line-height: 1.5;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       TAB NAVIGATION - Command Tabs
       ══════════════════════════════════════════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: var(--bg-secondary);
        padding: 6px;
        border-radius: 10px;
        border: 1px solid var(--border-default);
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 600;
        font-size: 0.8rem;
        color: var(--text-tertiary);
        background: transparent;
        border-radius: 6px;
        padding: 10px 18px;
        transition: all 0.15s ease;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        border: 1px solid transparent;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: var(--bg-elevated);
        color: var(--text-primary);
    }

    .stTabs [aria-selected="true"] {
        background: var(--accent-primary) !important;
        color: var(--bg-void) !important;
        font-weight: 700;
        box-shadow: 0 2px 8px var(--accent-primary-glow);
    }

    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        display: none;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       METRIC CARDS - Data Display Units
       ══════════════════════════════════════════════════════════════════════════ */
    [data-testid="stMetric"] {
        background: var(--bg-secondary);
        border: 1px solid var(--border-default);
        border-radius: 8px;
        padding: 20px 24px;
        position: relative;
        overflow: hidden;
        transition: all 0.2s ease;
    }

    [data-testid="stMetric"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--accent-primary);
        opacity: 0;
        transition: opacity 0.2s ease;
    }

    [data-testid="stMetric"]:hover {
        border-color: var(--accent-primary);
        transform: translateY(-1px);
    }

    [data-testid="stMetric"]:hover::before {
        opacity: 1;
    }

    [data-testid="stMetric"] label {
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 500;
        color: var(--text-tertiary) !important;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        font-size: 1.75rem;
        color: var(--text-primary) !important;
        letter-spacing: -0.02em;
    }

    [data-testid="stMetric"] [data-testid="stMetricDelta"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        font-weight: 500;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       BUTTONS - Action Triggers
       ══════════════════════════════════════════════════════════════════════════ */
    .stButton > button {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 700;
        background: var(--accent-primary);
        color: var(--bg-void);
        border: none;
        border-radius: 6px;
        padding: 12px 24px;
        transition: all 0.15s ease;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-size: 0.75rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    .stButton > button:hover {
        background: var(--accent-primary-hover);
        box-shadow: 0 4px 12px var(--accent-primary-glow);
        transform: translateY(-1px);
    }

    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    /* ══════════════════════════════════════════════════════════════════════════
       INPUT FIELDS - Data Entry
       ══════════════════════════════════════════════════════════════════════════ */
    .stTextInput > div > div > input {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.875rem;
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: 6px !important;
        color: var(--text-primary) !important;
        padding: 12px 14px;
        transition: all 0.15s ease;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 3px var(--accent-primary-subtle) !important;
        outline: none;
    }

    .stTextInput > div > div > input::placeholder {
        color: var(--text-muted) !important;
        font-style: normal;
    }

    /* Selectbox styling */
    .stSelectbox [data-baseweb="select"] > div {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: 6px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        min-height: 42px !important;
    }

    .stSelectbox [data-baseweb="select"] span {
        color: var(--text-primary) !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.875rem !important;
    }

    [data-baseweb="popover"] {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: 6px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important;
    }

    [data-baseweb="menu"] {
        background: var(--bg-secondary) !important;
    }

    [data-baseweb="menu"] li {
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.875rem;
        padding: 10px 14px !important;
    }

    [data-baseweb="menu"] li:hover {
        background: var(--bg-elevated) !important;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       DATAFRAME - Data Grid
       ══════════════════════════════════════════════════════════════════════════ */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid var(--border-default);
    }

    [data-testid="stDataFrame"] table {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
    }

    [data-testid="stDataFrame"] th {
        background: var(--bg-elevated) !important;
        color: var(--text-tertiary) !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-size: 0.7rem;
        padding: 12px 16px !important;
        border-bottom: 2px solid var(--accent-primary) !important;
    }

    [data-testid="stDataFrame"] td {
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-subtle) !important;
        padding: 10px 16px !important;
    }

    [data-testid="stDataFrame"] tr:hover td {
        background: var(--bg-elevated) !important;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       EXPANDER - Collapsible Sections
       ══════════════════════════════════════════════════════════════════════════ */
    .streamlit-expanderHeader {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 600;
        font-size: 0.9rem;
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: 6px !important;
        color: var(--text-primary) !important;
        padding: 14px 18px !important;
        transition: all 0.15s ease;
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--accent-primary) !important;
        background: var(--bg-elevated) !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-default) !important;
        border-top: none !important;
        border-radius: 0 0 6px 6px !important;
        padding: 16px !important;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       ALERTS - Status Messages
       ══════════════════════════════════════════════════════════════════════════ */
    .stSuccess {
        background: var(--status-success-subtle) !important;
        border: 1px solid var(--status-success) !important;
        border-radius: 6px;
        border-left: 4px solid var(--status-success) !important;
    }

    .stSuccess p {
        color: var(--status-success) !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 500;
    }

    .stError {
        background: var(--status-critical-subtle) !important;
        border: 1px solid var(--status-critical) !important;
        border-radius: 6px;
        border-left: 4px solid var(--status-critical) !important;
    }

    .stError p {
        color: var(--status-critical) !important;
    }

    .stWarning {
        background: var(--status-warning-subtle) !important;
        border: 1px solid var(--status-warning) !important;
        border-radius: 6px;
        border-left: 4px solid var(--status-warning) !important;
    }

    .stWarning p {
        color: var(--status-warning) !important;
    }

    .stInfo {
        background: var(--status-info-subtle) !important;
        border: 1px solid var(--status-info) !important;
        border-radius: 6px;
        border-left: 4px solid var(--status-info) !important;
    }

    .stInfo p {
        color: var(--status-info) !important;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       SPINNER - Loading State
       ══════════════════════════════════════════════════════════════════════════ */
    .stSpinner > div {
        border-top-color: var(--accent-primary) !important;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       CUSTOM LOADER - Enterprise Search Processing
       ══════════════════════════════════════════════════════════════════════════ */
    .logsleuth-loader {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px 24px;
        background: var(--bg-secondary);
        border: 1px solid var(--border-default);
        border-radius: 12px;
        margin: 20px 0;
    }

    .loader-spinner {
        display: flex;
        gap: 6px;
        margin-bottom: 24px;
    }

    .loader-bar {
        width: 4px;
        height: 32px;
        background: var(--accent-primary);
        border-radius: 2px;
        animation: loader-pulse 1s ease-in-out infinite;
    }

    .loader-bar:nth-child(1) { animation-delay: 0s; }
    .loader-bar:nth-child(2) { animation-delay: 0.1s; }
    .loader-bar:nth-child(3) { animation-delay: 0.2s; }
    .loader-bar:nth-child(4) { animation-delay: 0.3s; }
    .loader-bar:nth-child(5) { animation-delay: 0.4s; }

    @keyframes loader-pulse {
        0%, 100% {
            transform: scaleY(0.4);
            opacity: 0.4;
        }
        50% {
            transform: scaleY(1);
            opacity: 1;
        }
    }

    .loader-status {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 8px;
    }

    .loader-substatus {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-tertiary);
        letter-spacing: 0.02em;
    }

    .loader-progress {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 16px;
    }

    .loader-step {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        background: var(--bg-elevated);
        border-radius: 4px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .loader-step.active {
        background: var(--accent-primary-subtle);
        color: var(--accent-primary);
        border: 1px solid var(--accent-primary);
    }

    .loader-step.complete {
        background: var(--status-success-subtle);
        color: var(--status-success);
    }

    /* ══════════════════════════════════════════════════════════════════════════
       CUSTOM COMPONENT CLASSES
       ══════════════════════════════════════════════════════════════════════════ */

    /* Status Badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 14px;
        border-radius: 4px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .status-online {
        background: var(--status-success-subtle);
        border: 1px solid var(--status-success);
        color: var(--status-success);
    }

    .status-offline {
        background: var(--status-critical-subtle);
        border: 1px solid var(--status-critical);
        color: var(--status-critical);
    }

    /* Pulse indicator */
    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: pulse-glow 2s ease-in-out infinite;
    }

    .pulse-dot.online {
        background: var(--status-success);
    }

    .pulse-dot.offline {
        background: var(--status-critical);
    }

    @keyframes pulse-glow {
        0%, 100% {
            opacity: 1;
            box-shadow: 0 0 4px currentColor;
        }
        50% {
            opacity: 0.6;
            box-shadow: 0 0 8px currentColor, 0 0 12px currentColor;
        }
    }

    /* Section Headers */
    .section-header {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--text-tertiary);
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 16px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border-default);
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .section-header::before {
        content: '';
        width: 3px;
        height: 16px;
        background: var(--accent-primary);
        border-radius: 2px;
    }

    /* Card Container */
    .card-container {
        background: var(--bg-secondary);
        border: 1px solid var(--border-default);
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 20px;
        position: relative;
    }

    .card-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: var(--accent-primary);
        border-radius: 8px 8px 0 0;
    }

    /* Logo Container */
    .logo-container {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 18px;
        background: var(--bg-secondary);
        border-radius: 8px;
        border: 1px solid var(--border-default);
        margin-bottom: 24px;
    }

    .logo-icon {
        font-size: 1.8rem;
        filter: drop-shadow(0 0 8px var(--accent-primary-glow));
    }

    /* Investigation Result */
    .investigation-result {
        background: var(--bg-secondary);
        border: 1px solid var(--status-success);
        border-radius: 8px;
        padding: 20px;
        margin-top: 16px;
        position: relative;
    }

    .investigation-result::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--status-success);
        border-radius: 8px 8px 0 0;
    }

    /* Footer */
    .footer-text {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: var(--text-muted);
        text-align: center;
        padding: 20px 0;
        border-top: 1px solid var(--border-subtle);
        margin-top: 40px;
        letter-spacing: 0.02em;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       SCROLLBAR - Minimal Style
       ══════════════════════════════════════════════════════════════════════════ */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--border-default);
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }

    /* ══════════════════════════════════════════════════════════════════════════
       STREAMLIT OVERRIDES
       ══════════════════════════════════════════════════════════════════════════ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Sidebar toggle */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="collapsedControl"] button {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: 4px !important;
        color: var(--text-secondary) !important;
        transition: all 0.15s ease;
    }

    [data-testid="stSidebarCollapseButton"] button:hover,
    [data-testid="collapsedControl"] button:hover {
        background: var(--bg-elevated) !important;
        border-color: var(--accent-primary) !important;
        color: var(--accent-primary) !important;
    }

    /* Checkbox styling */
    .stCheckbox label span {
        color: var(--text-secondary) !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.875rem;
    }

    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: var(--border-default);
        margin: 24px 0;
    }

    /* Main header styles */
    .main-header {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 2rem;
        font-weight: 800;
        background: var(--accent-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0;
        letter-spacing: -0.03em;
    }

    .sub-header {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.95rem;
        color: var(--text-tertiary);
        margin-top: 6px;
        font-weight: 400;
        letter-spacing: 0.01em;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_es_client():
    """Get cached Elasticsearch client."""
    try:
        from src.utils.elasticsearch_client import get_elasticsearch_client
        return get_elasticsearch_client()
    except Exception as e:
        return None


def check_connection():
    """Check Elasticsearch connection status."""
    client = get_es_client()
    if client is None:
        return False, "Failed to create client"
    try:
        info = client.info()
        return True, info.get('cluster_name', 'Connected')
    except Exception as e:
        return False, str(e)


def render_loader(title: str, subtitle: str = "", steps: list = None):
    """
    Render a custom enterprise-style loader.

    Args:
        title: Main loading message (e.g., "Searching logs...")
        subtitle: Secondary status text
        steps: Optional list of step dicts with 'name' and 'status' (pending/active/complete)
    """
    steps_html = ""
    if steps:
        step_items = []
        for step in steps:
            status_class = step.get("status", "pending")
            icon = "✓" if status_class == "complete" else "◦" if status_class == "pending" else "●"
            step_items.append(f'<div class="loader-step {status_class}">{icon} {step["name"]}</div>')
        steps_html = f'<div class="loader-progress">{"".join(step_items)}</div>'

    subtitle_html = f'<div class="loader-substatus">{subtitle}</div>' if subtitle else ""

    return st.markdown(f"""
    <div class="logsleuth-loader">
        <div class="loader-spinner">
            <div class="loader-bar"></div>
            <div class="loader-bar"></div>
            <div class="loader-bar"></div>
            <div class="loader-bar"></div>
            <div class="loader-bar"></div>
        </div>
        <div class="loader-status">{title}</div>
        {subtitle_html}
        {steps_html}
    </div>
    """, unsafe_allow_html=True)


def get_error_stats(time_range: str = "2h"):
    """Get error statistics for dashboard."""
    client = get_es_client()
    if client is None:
        return None

    try:
        from src.tools import get_error_frequency
        return get_error_frequency(client, time_range=time_range, interval="5m")
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        return None


def search_logs_data(query: str, time_range: str, service: str = None, level: str = None):
    """Search logs and return results."""
    client = get_es_client()
    if client is None:
        return None

    try:
        from src.tools import search_logs
        return search_logs(
            client,
            search_query=query,
            time_range=time_range,
            service_name=service if service != "All Services" else None,
            log_level=level if level != "All Levels" else None,
            max_results=100,
        )
    except Exception as e:
        st.error(f"Error searching logs: {e}")
        return None


def get_services_list():
    """Get list of services from logs."""
    client = get_es_client()
    if client is None:
        return ["All Services"]

    try:
        from src.utils.elasticsearch_client import LOG_INDEX
        result = client.search(
            index=LOG_INDEX,
            body={
                "size": 0,
                "aggs": {"services": {"terms": {"field": "service.name", "size": 20}}}
            }
        )
        services = ["All Services"] + [b["key"] for b in result["aggregations"]["services"]["buckets"]]
        return services
    except:
        return ["All Services"]


def run_investigation(description: str, time_range: str, progress_callback=None):
    """Run a full investigation and return results."""
    client = get_es_client()
    if client is None:
        return None

    from src.tools import search_logs, get_error_frequency, find_error_traces, find_correlated_logs

    results = {
        "description": description,
        "time_range": time_range,
        "errors": None,
        "services": [],
        "root_cause": None,
        "timeline": [],
        "trace_info": None,
        "service_flow": [],  # For Sankey diagram
        "steps_completed": [],  # For progress stepper
    }

    # Step 1: Understand
    if progress_callback:
        progress_callback("understand", "Parsing incident description...")
    results["steps_completed"].append({"step": "understand", "status": "completed", "message": "Parsed incident description"})

    # Step 2: Search
    if progress_callback:
        progress_callback("search", "Searching for error logs...")
    error_freq = get_error_frequency(client, time_range=time_range)
    if error_freq:
        results["errors"] = error_freq
        results["services"] = [s["service"] for s in error_freq.get("service_breakdown", [])]
    results["steps_completed"].append({"step": "search", "status": "completed", "message": f"Found {error_freq.get('total_errors', 0) if error_freq else 0} errors"})

    # Step 3: Analyze
    if progress_callback:
        progress_callback("analyze", "Analyzing error patterns...")
    if error_freq and error_freq.get("service_breakdown"):
        root_service = error_freq["service_breakdown"][0]["service"]
        results["root_cause"] = root_service
    results["steps_completed"].append({"step": "analyze", "status": "completed", "message": f"Identified root cause: {results.get('root_cause', 'Unknown')}"})

    # Step 4: Correlate
    if progress_callback:
        progress_callback("correlate", "Correlating traces across services...")
    if results["root_cause"]:
        traces = find_error_traces(client, service_name=results["root_cause"], time_range=time_range)
        if traces.get("traces"):
            trace_id = traces["traces"][0]["trace_id"]
            trace_info = find_correlated_logs(client, trace_id)
            results["trace_info"] = trace_info
            results["timeline"] = trace_info.get("timeline", [])

            # Build service flow for Sankey diagram
            if trace_info.get("timeline"):
                service_order = []
                for entry in trace_info["timeline"]:
                    svc = entry.get("service")
                    if svc and (not service_order or service_order[-1] != svc):
                        service_order.append(svc)

                # Create flow connections
                for i in range(len(service_order) - 1):
                    results["service_flow"].append({
                        "source": service_order[i],
                        "target": service_order[i + 1],
                        "value": 1,
                        "has_error": any(
                            e.get("service") == service_order[i + 1] and e.get("level") == "error"
                            for e in trace_info["timeline"]
                        )
                    })

    results["steps_completed"].append({"step": "correlate", "status": "completed", "message": f"Traced {len(results.get('timeline', []))} events"})

    # Step 5: Synthesize
    if progress_callback:
        progress_callback("synthesize", "Generating recommendations...")
    results["steps_completed"].append({"step": "synthesize", "status": "completed", "message": "Generated analysis and recommendations"})

    return results


def render_investigation_stepper(current_step: str = None, completed_steps: list = None):
    """Render the 5-step investigation progress stepper using Streamlit columns."""
    steps = [
        {"id": "understand", "label": "Understand", "icon": "🎯"},
        {"id": "search", "label": "Search", "icon": "🔍"},
        {"id": "analyze", "label": "Analyze", "icon": "📊"},
        {"id": "correlate", "label": "Correlate", "icon": "🔗"},
        {"id": "synthesize", "label": "Synthesize", "icon": "💡"},
    ]

    completed_ids = [s["step"] for s in (completed_steps or [])]

    cols = st.columns(5)
    for i, step in enumerate(steps):
        is_completed = step["id"] in completed_ids
        is_current = step["id"] == current_step

        with cols[i]:
            if is_completed:
                st.markdown(f"### ✅")
                st.caption(f"**{step['label']}**")
            elif is_current:
                st.markdown(f"### ⏳")
                st.caption(f"**{step['label']}**")
            else:
                st.markdown(f"### {step['icon']}")
                st.caption(step['label'])


def render_sankey_diagram(service_flow: list, title: str = "Request Flow"):
    """Render a Sankey diagram showing service-to-service flow."""
    if not service_flow:
        return None

    # Get unique services and create index mapping
    services = []
    for flow in service_flow:
        if flow["source"] not in services:
            services.append(flow["source"])
        if flow["target"] not in services:
            services.append(flow["target"])

    # Create Sankey diagram
    source_indices = [services.index(f["source"]) for f in service_flow]
    target_indices = [services.index(f["target"]) for f in service_flow]
    values = [f["value"] for f in service_flow]

    # Color links based on error status - Enterprise palette
    link_colors = [
        "rgba(239, 68, 68, 0.6)" if f.get("has_error") else "rgba(16, 185, 129, 0.4)"
        for f in service_flow
    ]

    # Node colors - highlight error services
    error_services = set(f["target"] for f in service_flow if f.get("has_error"))
    node_colors = [
        "#EF4444" if svc in error_services else "#10B981"
        for svc in services
    ]

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=25,
            line=dict(color="rgba(0,0,0,0)", width=0),
            label=services,
            color=node_colors,
            customdata=services,
            hovertemplate='%{customdata}<extra></extra>'
        ),
        link=dict(
            source=source_indices,
            target=target_indices,
            value=values,
            color=link_colors,
            hovertemplate='%{source.label} → %{target.label}<extra></extra>'
        )
    )])

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family='Plus Jakarta Sans, sans-serif', size=13, color='#9CA3AF'),
            x=0.5
        ),
        font=dict(family='IBM Plex Mono, monospace', size=11, color='#F9FAFB'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=280,
        margin=dict(l=20, r=20, t=45, b=20),
    )

    return fig


# Sidebar
with st.sidebar:
    # Enterprise Logo and branding
    st.markdown("""
    <div class="logo-container">
        <div style="width: 42px; height: 42px; background: #10B981;
                    border-radius: 8px; display: flex; align-items: center; justify-content: center;
                    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);">
            <span style="font-size: 1.4rem; filter: brightness(10);">🔍</span>
        </div>
        <div>
            <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 800; font-size: 1.25rem;
                        color: #F9FAFB; letter-spacing: -0.02em;">
                LogSleuth
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; color: #6B7280;
                        text-transform: uppercase; letter-spacing: 0.12em; margin-top: 2px;">
                Enterprise • v2.0
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Connection status
    connected, status = check_connection()

    st.markdown("""
    <div class="section-header" style="margin-top: 8px; font-size: 0.7rem;">
        System Status
    </div>
    """, unsafe_allow_html=True)

    if connected:
        escaped_status = html.escape(status)
        st.markdown(f"""
        <div class="status-badge status-online">
            <span class="pulse-dot online"></span>
            Operational
        </div>
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #9CA3AF;
                    margin-top: 10px; padding: 10px; background: rgba(17, 24, 39, 0.6);
                    border-radius: 4px; border: 1px solid rgba(55, 65, 81, 0.3);">
            <div style="color: #6B7280; font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;">Cluster</div>
            <div style="color: #F9FAFB;">{escaped_status}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-badge status-offline">
            <span class="pulse-dot offline"></span>
            Offline
        </div>
        """, unsafe_allow_html=True)
        st.caption(f"⚠️ {status}")
        st.info("Configure `.env` file with Elasticsearch credentials")

    st.divider()

    # Time range selector with custom label
    st.markdown("""
    <div class="section-header" style="font-size: 0.7rem;">
        Analysis Window
    </div>
    """, unsafe_allow_html=True)

    time_range = st.selectbox(
        "Time Range",
        ["30m", "1h", "2h", "6h", "12h", "24h"],
        index=2,
        label_visibility="collapsed"
    )

    st.divider()

    # Quick actions section
    st.markdown("""
    <div class="section-header" style="font-size: 0.7rem;">
        Quick Actions
    </div>
    """, unsafe_allow_html=True)

    auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.rerun()

    # Add spacing before footer
    st.markdown("<div style='height: 60px;'></div>", unsafe_allow_html=True)

    # Enterprise footer
    st.markdown("""
    <div style="padding: 16px; background: rgba(17, 24, 39, 0.6); border-radius: 6px;
                border: 1px solid rgba(55, 65, 81, 0.3); margin-top: auto;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <div style="width: 6px; height: 6px; background: #10B981; border-radius: 50%;
                        box-shadow: 0 0 8px #10B981;"></div>
            <span style="font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; color: #9CA3AF;
                         text-transform: uppercase; letter-spacing: 0.08em;">Elastic Agent Builder</span>
        </div>
        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.7rem; color: #6B7280;">
            Hackathon 2026 Edition
        </div>
    </div>
    """, unsafe_allow_html=True)


# Main content - Enterprise Header
st.markdown("""
<div style="margin-bottom: 28px; padding-bottom: 20px; border-bottom: 1px solid rgba(55, 65, 81, 0.3);">
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 8px;">
        <div style="width: 4px; height: 28px; background: #10B981;
                    border-radius: 4px;"></div>
        <h1 class="main-header" style="margin: 0;">LogSleuth</h1>
    </div>
    <p class="sub-header" style="margin-left: 22px;">Enterprise Incident Investigation Platform</p>
</div>
""", unsafe_allow_html=True)

# Tabs - Enterprise Navigation
tab1, tab2, tab3, tab4 = st.tabs(["OVERVIEW", "INVESTIGATE", "LOG SEARCH", "HISTORY"])

# Tab 1: Dashboard
with tab1:
    if not connected:
        st.markdown("""
        <div class="card-container" style="text-align: center; padding: 60px;">
            <div style="font-size: 2.5rem; margin-bottom: 20px; opacity: 0.8;">⚡</div>
            <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.1rem; color: #F9FAFB;
                        margin-bottom: 8px; font-weight: 600;">
                Connect to Elasticsearch
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #6B7280;">
                Configure your connection to view system metrics
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Get stats
        stats = get_error_stats(time_range)

        if stats:
            # Metrics row with enhanced styling
            st.markdown('<div class="section-header">System Overview</div>', unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_errors = int(stats['total_errors'])
                st.metric(
                    "Total Errors",
                    f"{total_errors:,}",
                    delta=None,
                )

            with col2:
                services_affected = len(stats.get("service_breakdown", []))
                st.metric("Services Affected", services_affected)

            with col3:
                spike = stats.get("spike_detected")
                if spike:
                    st.metric("Spike Detected", spike["severity"].upper(), delta=f"{spike['error_count']} errors")
                else:
                    st.metric("Spike Detected", "None", delta="normal")

            with col4:
                error_types = set()
                for svc in stats.get("service_breakdown", []):
                    for et in svc.get("error_types", []):
                        error_types.add(et["type"])
                st.metric("Error Types", len(error_types))

            st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

            # Charts row with dark theme
            col1, col2 = st.columns(2)

            # Dark theme for Plotly charts
            dark_template = {
                'layout': {
                    'paper_bgcolor': 'rgba(0,0,0,0)',
                    'plot_bgcolor': 'rgba(0,0,0,0)',
                    'font': {'family': 'JetBrains Mono, monospace', 'color': '#94a3b8'},
                    'title': {'font': {'family': 'Outfit, sans-serif', 'color': '#f1f5f9', 'size': 16}},
                    'xaxis': {
                        'gridcolor': 'rgba(255,255,255,0.06)',
                        'linecolor': 'rgba(255,255,255,0.1)',
                        'tickfont': {'color': '#64748b'}
                    },
                    'yaxis': {
                        'gridcolor': 'rgba(255,255,255,0.06)',
                        'linecolor': 'rgba(255,255,255,0.1)',
                        'tickfont': {'color': '#64748b'}
                    },
                    'legend': {'font': {'color': '#94a3b8'}}
                }
            }

            with col1:
                st.markdown('<div class="section-header">Error Trend</div>', unsafe_allow_html=True)
                if stats.get("histogram"):
                    df = pd.DataFrame(stats["histogram"])
                    df["timestamp"] = pd.to_datetime(df["timestamp"])

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df["timestamp"],
                        y=df["total_errors"],
                        mode='lines',
                        fill='tozeroy',
                        line=dict(color='#10B981', width=2),
                        fillcolor='rgba(16, 185, 129, 0.15)',
                        name='Errors'
                    ))
                    fig.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=35, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='IBM Plex Mono, monospace', size=10, color='#9CA3AF'),
                        title=dict(text=f"Last {time_range}", font=dict(family='Plus Jakarta Sans, sans-serif', color='#6B7280', size=11)),
                        xaxis=dict(gridcolor='rgba(55, 65, 81, 0.3)', linecolor='rgba(55, 65, 81, 0.5)', tickfont=dict(size=9)),
                        yaxis=dict(gridcolor='rgba(55, 65, 81, 0.3)', linecolor='rgba(55, 65, 81, 0.5)', tickfont=dict(size=9)),
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No error data in selected time range")

            with col2:
                st.markdown('<div class="section-header">Service Distribution</div>', unsafe_allow_html=True)
                if stats.get("service_breakdown"):
                    df = pd.DataFrame(stats["service_breakdown"])

                    # Enterprise color palette - professional and distinct
                    colors = ['#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#3B82F6', '#06B6D4', '#84CC16']

                    fig = go.Figure(data=[go.Pie(
                        labels=df["service"],
                        values=df["error_count"],
                        hole=0.6,
                        marker=dict(colors=colors[:len(df)], line=dict(color='#0B1120', width=2)),
                        textfont=dict(family='IBM Plex Mono, monospace', color='#F9FAFB', size=10),
                        textinfo='percent',
                        hovertemplate='<b>%{label}</b><br>Errors: %{value}<br>%{percent}<extra></extra>'
                    )])
                    fig.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=35, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='Plus Jakarta Sans, sans-serif', color='#9CA3AF'),
                        showlegend=True,
                        legend=dict(
                            font=dict(family='IBM Plex Mono, monospace', size=9, color='#9CA3AF'),
                            bgcolor='rgba(0,0,0,0)',
                            orientation='h',
                            yanchor='bottom',
                            y=-0.15,
                            xanchor='center',
                            x=0.5
                        ),
                        annotations=[dict(
                            text=f'<b>{int(df["error_count"].sum()):,}</b>',
                            x=0.5, y=0.5,
                            font=dict(family='IBM Plex Mono, monospace', size=22, color='#F9FAFB'),
                            showarrow=False
                        )]
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No service data available")

            st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

            # Service breakdown table
            st.markdown('<div class="section-header">Service Breakdown</div>', unsafe_allow_html=True)
            if stats.get("service_breakdown"):
                for svc in stats["service_breakdown"]:
                    with st.expander(f"🔹 **{svc['service']}** — {svc['error_count']} errors"):
                        error_df = pd.DataFrame(svc.get("error_types", []))
                        if not error_df.empty:
                            st.dataframe(error_df, use_container_width=True, hide_index=True)

# Tab 2: Investigate
with tab2:
    st.markdown('<div class="section-header">Incident Investigation</div>', unsafe_allow_html=True)

    if not connected:
        st.markdown("""
        <div class="card-container" style="text-align: center; padding: 60px;">
            <div style="font-size: 3rem; margin-bottom: 16px;">🔐</div>
            <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.25rem; color: #F9FAFB; margin-bottom: 8px;">
                Connect to Elasticsearch
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.875rem; color: #6B7280;">
                Configure your connection to run investigations
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Investigation input with styled container
        st.markdown("""
        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; color: #9CA3AF; margin-bottom: 12px;">
            Describe the incident you want to investigate. Our AI will analyze logs, traces, and metrics to identify root causes.
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([4, 1])
        with col1:
            incident_desc = st.text_input(
                "Describe the incident",
                placeholder="e.g., checkout-service throwing timeout errors, payment failures...",
                label_visibility="collapsed"
            )
        with col2:
            investigate_btn = st.button("🔍 Investigate", type="primary", width="stretch")

        if investigate_btn and incident_desc:
            # Create placeholder for loader
            loader_placeholder = st.empty()

            # Show custom loader
            with loader_placeholder.container():
                render_loader(
                    "Running investigation...",
                    "Analyzing logs, traces, and metrics",
                    [
                        {"name": "Understand", "status": "active"},
                        {"name": "Search", "status": "pending"},
                        {"name": "Analyze", "status": "pending"},
                        {"name": "Correlate", "status": "pending"},
                    ]
                )

            # Run investigation
            results = run_investigation(incident_desc, time_range)

            # Clear loader
            loader_placeholder.empty()

            # Show completed stepper and results
            if results:
                # Show progress stepper
                render_investigation_stepper(completed_steps=results.get("steps_completed", []))

                st.success("✅ Investigation Complete")

                # Summary cards
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Errors", int(results["errors"]["total_errors"]) if results["errors"] else 0)
                with col2:
                    st.metric("Services Affected", len(results["services"]))
                with col3:
                    st.metric("Root Cause", results["root_cause"] or "Unknown")

                st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

                # Service Flow Visualization (Sankey Diagram)
                if results.get("service_flow"):
                    st.markdown('<div class="section-header">Service Request Flow</div>', unsafe_allow_html=True)
                    st.markdown("""
                    <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.8rem; color: #6B7280; margin-bottom: 12px;">
                        Visualizing how the request flowed between services. <span style="color: #EF4444;">Red</span> indicates error propagation.
                    </div>
                    """, unsafe_allow_html=True)

                    sankey_fig = render_sankey_diagram(results["service_flow"], "Request Trace Flow")
                    if sankey_fig:
                        st.plotly_chart(sankey_fig, use_container_width=True)

                st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

                # Timeline
                if results["timeline"]:
                    st.markdown('<div class="section-header">Request Timeline</div>', unsafe_allow_html=True)

                    timeline_data = []
                    for entry in results["timeline"][:15]:
                        level = entry.get("level", "").upper()
                        timeline_data.append({
                            "Time": entry.get("timestamp", "")[:19].replace("T", " "),
                            "Service": entry.get("service", ""),
                            "Level": level,
                            "Message": entry.get("message", "")[:80],
                        })

                    df = pd.DataFrame(timeline_data)

                    # Display the timeline dataframe
                    st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

                # Findings with styled card
                st.markdown('<div class="section-header">Analysis & Recommendations</div>', unsafe_allow_html=True)

                root_cause = results["root_cause"] or "Unable to determine"
                affected = ", ".join(results["services"][:5]) or "None identified"
                total_errors = int(results["errors"]["total_errors"]) if results["errors"] else 0

                # Escape user-provided and database content for safe HTML rendering
                escaped_incident = html.escape(incident_desc)
                escaped_root_cause = html.escape(root_cause)
                escaped_affected = html.escape(affected)

                st.markdown(f"""
                <div class="card-container">
                    <div style="margin-bottom: 20px;">
                        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #6B7280;
                                    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;">Incident</div>
                        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1rem; color: #F9FAFB;">{escaped_incident}</div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px;">
                        <div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #6B7280;
                                        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;">Root Cause</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.95rem; color: #EF4444; font-weight: 600;">{escaped_root_cause}</div>
                        </div>
                        <div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #6B7280;
                                        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;">Affected Services</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.95rem; color: #f59e0b;">{escaped_affected}</div>
                        </div>
                        <div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #6B7280;
                                        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;">Total Errors</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.95rem; color: #10B981; font-weight: 600;">{total_errors:,}</div>
                        </div>
                    </div>
                    <div style="border-top: 1px solid rgba(255,255,255,0.06); padding-top: 20px;">
                        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #6B7280;
                                    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px;">Recommended Actions</div>
                        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; color: #9CA3AF; line-height: 1.8;">
                            <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px;">
                                <span style="color: #10B981;">1.</span>
                                <span>Review error logs from <span style="color: #F9FAFB; font-weight: 500;">{escaped_root_cause}</span> service</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px;">
                                <span style="color: #10B981;">2.</span>
                                <span>Check recent deployments or configuration changes</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px;">
                                <span style="color: #10B981;">3.</span>
                                <span>Verify database and external service connectivity</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; gap: 10px;">
                                <span style="color: #10B981;">4.</span>
                                <span>Consider enabling circuit breakers if not already active</span>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        elif investigate_btn:
            st.warning("⚠️ Please enter an incident description")

# Tab 3: Log Search
with tab3:
    st.markdown('<div class="section-header">Log Search</div>', unsafe_allow_html=True)

    if not connected:
        st.markdown("""
        <div class="card-container" style="text-align: center; padding: 60px;">
            <div style="font-size: 3rem; margin-bottom: 16px;">📜</div>
            <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.25rem; color: #F9FAFB; margin-bottom: 8px;">
                Connect to Elasticsearch
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.875rem; color: #6B7280;">
                Configure your connection to search logs
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Search description
        st.markdown("""
        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; color: #9CA3AF; margin-bottom: 16px;">
            Search through your logs with powerful filters. Use keywords, error types, or trace IDs to find what you're looking for.
        </div>
        """, unsafe_allow_html=True)

        # Search filters with improved layout
        col1, col2, col3, col4 = st.columns([3, 1.5, 1, 1])

        with col1:
            search_query = st.text_input(
                "Search Query",
                placeholder="🔍 Enter search term, error type, or trace ID...",
                label_visibility="collapsed"
            )
        with col2:
            services = get_services_list()
            service_filter = st.selectbox("Service", services, label_visibility="collapsed")
        with col3:
            level_filter = st.selectbox("Level", ["All Levels", "error", "warn", "info", "debug"], label_visibility="collapsed")
        with col4:
            search_btn = st.button("Search", type="primary", width="stretch")

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        if search_btn and search_query:
            # Create placeholder for loader
            loader_placeholder = st.empty()

            # Show custom loader
            with loader_placeholder.container():
                render_loader(
                    "Searching logs...",
                    f"Querying Elasticsearch for \"{search_query}\"",
                    [
                        {"name": "Connect", "status": "complete"},
                        {"name": "Query", "status": "active"},
                        {"name": "Process", "status": "pending"},
                    ]
                )

            # Run search
            results = search_logs_data(
                search_query,
                time_range,
                service_filter,
                level_filter,
            )

            # Clear loader
            loader_placeholder.empty()

            if results:
                # Results header with count
                escaped_query = html.escape(search_query)
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                    <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; color: #9CA3AF;">
                        Found <span style="color: #10B981; font-weight: 600; font-family: 'IBM Plex Mono', monospace;">{results['total']}</span> logs matching
                    </div>
                    <div style="background: rgba(20, 184, 166, 0.15); border: 1px solid rgba(20, 184, 166, 0.3);
                                padding: 4px 12px; border-radius: 20px; font-family: 'IBM Plex Mono', monospace;
                                font-size: 0.8rem; color: #5eead4;">
                        "{escaped_query}"
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if results["hits"]:
                    # Convert to dataframe
                    log_data = []
                    for hit in results["hits"]:
                        log_data.append({
                            "Time": hit.get("timestamp", "")[:19].replace("T", " ") if hit.get("timestamp") else "",
                            "Service": hit.get("service", ""),
                            "Level": hit.get("level", "").upper() if hit.get("level") else "",
                            "Message": hit.get("message", ""),
                            "Error Type": hit.get("error_type", ""),
                            "Trace ID": hit.get("trace_id", "")[:12] + "..." if hit.get("trace_id") else "",
                        })

                    df = pd.DataFrame(log_data)

                    # Display the dataframe
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.markdown("""
                    <div class="card-container" style="text-align: center; padding: 40px;">
                        <div style="font-size: 2rem; margin-bottom: 12px;">🔍</div>
                        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1rem; color: #9CA3AF;">
                            No logs found matching your search criteria
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        elif search_btn:
            st.warning("⚠️ Please enter a search query")

# Tab 4: History
with tab4:
    st.markdown('<div class="section-header">Past Investigations</div>', unsafe_allow_html=True)

    if not connected:
        st.markdown("""
        <div class="card-container" style="text-align: center; padding: 60px;">
            <div style="font-size: 3rem; margin-bottom: 16px;">📚</div>
            <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.25rem; color: #F9FAFB; margin-bottom: 8px;">
                Connect to Elasticsearch
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.875rem; color: #6B7280;">
                Configure your connection to view investigation history
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        from src.tools import search_past_incidents

        client = get_es_client()

        st.markdown("""
        <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; color: #9CA3AF; margin-bottom: 16px;">
            Search through past incidents to find similar issues and learn from previous resolutions.
        </div>
        """, unsafe_allow_html=True)

        history_query = st.text_input(
            "Search past incidents",
            placeholder="🔍 Search by keyword: database, timeout, connection, payment...",
            label_visibility="collapsed"
        )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        if history_query:
            results = search_past_incidents(client, search_terms=history_query)

            if results.get("incidents"):
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                    <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; color: #9CA3AF;">
                        Found <span style="color: #a855f7; font-weight: 600; font-family: 'IBM Plex Mono', monospace;">{results['total']}</span> past incidents
                    </div>
                </div>
                """, unsafe_allow_html=True)

                for inc in results["incidents"]:
                    incident_id = html.escape(inc.get('id', 'Unknown'))
                    incident_date = html.escape(inc.get('timestamp', '')[:10] if inc.get('timestamp') else 'Unknown date')
                    root_cause = html.escape(inc.get('root_cause', 'Not recorded'))
                    services = html.escape(', '.join(inc.get('affected_services', [])) or 'None')
                    resolution = html.escape(inc.get('resolution', 'Not recorded'))

                    with st.expander(f"📋 **{incident_id}** — {incident_date}"):
                        st.markdown(f"""
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 16px;">
                            <div>
                                <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #6B7280;
                                            text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">Root Cause</div>
                                <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; color: #EF4444;">{root_cause}</div>
                            </div>
                            <div>
                                <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #6B7280;
                                            text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">Affected Services</div>
                                <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; color: #f59e0b;">{services}</div>
                            </div>
                        </div>
                        <div style="margin-bottom: 12px;">
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #6B7280;
                                        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">Resolution</div>
                            <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; color: #9CA3AF;">{resolution}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if inc.get("suggestions"):
                            suggestions = html.escape(inc.get('suggestions', ''))
                            st.markdown(f"""
                            <div style="background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.2);
                                        border-radius: 8px; padding: 12px; margin-top: 12px;">
                                <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #a855f7;
                                            text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;">💡 Suggestions</div>
                                <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; color: #c4b5fd;">
                                    {suggestions}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="card-container" style="text-align: center; padding: 40px;">
                    <div style="font-size: 2rem; margin-bottom: 12px;">📭</div>
                    <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1rem; color: #F9FAFB; margin-bottom: 8px;">
                        No past incidents found
                    </div>
                    <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #6B7280;">
                        Run some investigations first to build your knowledge base
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card-container" style="text-align: center; padding: 48px;">
                <div style="font-size: 2.5rem; margin-bottom: 16px;">📚</div>
                <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.1rem; color: #F9FAFB; margin-bottom: 8px;">
                    Search Your Investigation History
                </div>
                <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; color: #6B7280;">
                    Enter a keyword above to find past incidents and their resolutions
                </div>
            </div>
            """, unsafe_allow_html=True)


# Footer
st.markdown("""
<div class="footer-text">
    <div style="display: flex; justify-content: center; align-items: center; gap: 16px; margin-bottom: 8px;">
        <span style="color: #10B981;">●</span>
        <span>LogSleuth v0.1.0</span>
        <span style="color: #6B7280;">|</span>
        <span>Powered by Elasticsearch</span>
        <span style="color: #a855f7;">●</span>
    </div>
    <div style="font-size: 0.65rem; color: #475569;">
        Elasticsearch Agent Builder Hackathon 2026
    </div>
</div>
""", unsafe_allow_html=True)
