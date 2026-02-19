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
# CUSTOM CSS - Dark Command Center Aesthetic
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    /* ══════════════════════════════════════════════════════════════════════════
       TYPOGRAPHY - Import distinctive fonts
       ══════════════════════════════════════════════════════════════════════════ */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ══════════════════════════════════════════════════════════════════════════
       CSS VARIABLES - Dark Command Center Palette
       ══════════════════════════════════════════════════════════════════════════ */
    :root {
        --bg-primary: #0a0a0f;
        --bg-secondary: #12121a;
        --bg-tertiary: #1a1a24;
        --bg-card: rgba(26, 26, 36, 0.7);
        --bg-card-hover: rgba(32, 32, 45, 0.8);
        --border-subtle: rgba(255, 255, 255, 0.06);
        --border-glow: rgba(20, 184, 166, 0.3);
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --accent-teal: #14b8a6;
        --accent-teal-glow: rgba(20, 184, 166, 0.2);
        --accent-amber: #f59e0b;
        --accent-amber-glow: rgba(245, 158, 11, 0.2);
        --accent-rose: #f43f5e;
        --accent-rose-glow: rgba(244, 63, 94, 0.2);
        --accent-purple: #a855f7;
        --accent-blue: #3b82f6;
        --gradient-primary: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
        --gradient-danger: linear-gradient(135deg, #f43f5e 0%, #e11d48 100%);
        --gradient-warning: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        --gradient-card: linear-gradient(180deg, rgba(26,26,36,0.9) 0%, rgba(18,18,26,0.95) 100%);
    }

    /* ══════════════════════════════════════════════════════════════════════════
       GLOBAL STYLES - Dark theme foundation
       ══════════════════════════════════════════════════════════════════════════ */
    .stApp {
        background: var(--bg-primary);
        background-image:
            radial-gradient(ellipse at 20% 0%, rgba(20, 184, 166, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 100%, rgba(168, 85, 247, 0.05) 0%, transparent 50%),
            linear-gradient(180deg, var(--bg-primary) 0%, #0d0d14 100%);
        font-family: 'Outfit', sans-serif;
    }

    /* Subtle grid pattern overlay */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image:
            linear-gradient(rgba(20, 184, 166, 0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(20, 184, 166, 0.02) 1px, transparent 1px);
        background-size: 50px 50px;
        pointer-events: none;
        z-index: 0;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       SIDEBAR STYLING
       ══════════════════════════════════════════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d14 0%, #0a0a0f 100%);
        border-right: 1px solid var(--border-subtle);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: var(--text-secondary);
    }

    /* Sidebar title styling */
    [data-testid="stSidebar"] h1 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        font-size: 1.5rem;
        background: linear-gradient(135deg, #14b8a6 0%, #22d3ee 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.02em;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       MAIN HEADER STYLES
       ══════════════════════════════════════════════════════════════════════════ */
    .main-header {
        font-family: 'Outfit', sans-serif;
        font-size: 2.75rem;
        font-weight: 800;
        background: linear-gradient(135deg, #14b8a6 0%, #22d3ee 50%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0;
        letter-spacing: -0.03em;
        animation: shimmer 3s ease-in-out infinite;
    }

    @keyframes shimmer {
        0%, 100% { filter: brightness(1); }
        50% { filter: brightness(1.2); }
    }

    .sub-header {
        font-family: 'Outfit', sans-serif;
        font-size: 1.1rem;
        color: var(--text-secondary);
        margin-top: 4px;
        font-weight: 400;
        letter-spacing: 0.02em;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       TAB STYLING
       ══════════════════════════════════════════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: var(--bg-secondary);
        padding: 8px;
        border-radius: 16px;
        border: 1px solid var(--border-subtle);
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'Outfit', sans-serif;
        font-weight: 500;
        font-size: 0.95rem;
        color: var(--text-secondary);
        background: transparent;
        border-radius: 10px;
        padding: 10px 20px;
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: var(--bg-tertiary);
        color: var(--text-primary);
    }

    .stTabs [aria-selected="true"] {
        background: var(--gradient-primary) !important;
        color: white !important;
        box-shadow: 0 4px 15px var(--accent-teal-glow);
    }

    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }

    .stTabs [data-baseweb="tab-border"] {
        display: none;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       METRIC CARDS - Glassmorphism style
       ══════════════════════════════════════════════════════════════════════════ */
    [data-testid="stMetric"] {
        background: var(--gradient-card);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 24px;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }

    [data-testid="stMetric"]:hover {
        border-color: var(--border-glow);
        box-shadow: 0 8px 32px var(--accent-teal-glow);
        transform: translateY(-2px);
    }

    [data-testid="stMetric"] label {
        font-family: 'Outfit', sans-serif;
        font-weight: 500;
        color: var(--text-secondary) !important;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 2rem;
        color: var(--text-primary) !important;
    }

    [data-testid="stMetric"] [data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.875rem;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       BUTTONS - Neon glow effect
       ══════════════════════════════════════════════════════════════════════════ */
    .stButton > button {
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
        background: var(--gradient-primary);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 28px;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.875rem;
    }

    .stButton > button:hover {
        box-shadow: 0 6px 24px var(--accent-teal-glow), 0 0 40px var(--accent-teal-glow);
        transform: translateY(-2px);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* ══════════════════════════════════════════════════════════════════════════
       INPUT FIELDS - Dark style
       ══════════════════════════════════════════════════════════════════════════ */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div {
        font-family: 'JetBrains Mono', monospace;
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
        padding: 12px 16px;
        transition: all 0.2s ease;
    }

    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus {
        border-color: var(--accent-teal) !important;
        box-shadow: 0 0 0 3px var(--accent-teal-glow) !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: var(--text-muted) !important;
    }

    /* Selectbox specific fixes */
    .stSelectbox > div > div {
        min-height: 44px !important;
    }

    .stSelectbox [data-baseweb="select"] > div {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        min-height: 44px !important;
        padding: 0 12px !important;
    }

    .stSelectbox [data-baseweb="select"] span {
        color: var(--text-primary) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.875rem !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }

    /* Dropdown menu styling */
    [data-baseweb="popover"] {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 12px !important;
    }

    [data-baseweb="menu"] {
        background: var(--bg-secondary) !important;
    }

    [data-baseweb="menu"] li {
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    [data-baseweb="menu"] li:hover {
        background: var(--bg-tertiary) !important;
    }

    /* Sidebar selectbox - ensure full width */
    [data-testid="stSidebar"] .stSelectbox {
        width: 100% !important;
    }

    [data-testid="stSidebar"] .stSelectbox > div {
        width: 100% !important;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       EXPANDER - Card style
       ══════════════════════════════════════════════════════════════════════════ */
    .streamlit-expanderHeader {
        font-family: 'Outfit', sans-serif;
        font-weight: 500;
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        color: var(--text-primary);
        transition: all 0.2s ease;
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--accent-teal);
        background: var(--bg-tertiary);
    }

    .streamlit-expanderContent {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-top: none;
        border-radius: 0 0 12px 12px;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       DATAFRAME STYLING
       ══════════════════════════════════════════════════════════════════════════ */
    [data-testid="stDataFrame"] {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid var(--border-subtle);
    }

    [data-testid="stDataFrame"] table {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.875rem;
    }

    [data-testid="stDataFrame"] th {
        background: var(--bg-tertiary) !important;
        color: var(--text-secondary) !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.75rem;
    }

    [data-testid="stDataFrame"] td {
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-subtle) !important;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       ALERT BOXES
       ══════════════════════════════════════════════════════════════════════════ */
    .stSuccess {
        background: linear-gradient(135deg, rgba(20, 184, 166, 0.15) 0%, rgba(16, 185, 129, 0.1) 100%);
        border: 1px solid rgba(20, 184, 166, 0.3);
        border-radius: 12px;
        color: #5eead4;
    }

    .stError {
        background: linear-gradient(135deg, rgba(244, 63, 94, 0.15) 0%, rgba(239, 68, 68, 0.1) 100%);
        border: 1px solid rgba(244, 63, 94, 0.3);
        border-radius: 12px;
        color: #fda4af;
    }

    .stWarning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(234, 179, 8, 0.1) 100%);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 12px;
        color: #fde047;
    }

    .stInfo {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(99, 102, 241, 0.1) 100%);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px;
        color: #93c5fd;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       DIVIDER STYLING
       ══════════════════════════════════════════════════════════════════════════ */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, var(--border-subtle) 20%, var(--border-subtle) 80%, transparent 100%);
        margin: 32px 0;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       CUSTOM COMPONENT CLASSES
       ══════════════════════════════════════════════════════════════════════════ */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .status-online {
        background: linear-gradient(135deg, rgba(20, 184, 166, 0.2) 0%, rgba(16, 185, 129, 0.15) 100%);
        border: 1px solid rgba(20, 184, 166, 0.4);
        color: #5eead4;
    }

    .status-offline {
        background: linear-gradient(135deg, rgba(244, 63, 94, 0.2) 0%, rgba(239, 68, 68, 0.15) 100%);
        border: 1px solid rgba(244, 63, 94, 0.4);
        color: #fda4af;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: pulse 2s ease-in-out infinite;
    }

    .pulse-dot.online {
        background: #14b8a6;
        box-shadow: 0 0 10px #14b8a6;
    }

    .pulse-dot.offline {
        background: #f43f5e;
        box-shadow: 0 0 10px #f43f5e;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.6; transform: scale(1.1); }
    }

    .section-header {
        font-family: 'Outfit', sans-serif;
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 20px;
        padding-bottom: 12px;
        border-bottom: 2px solid var(--accent-teal);
        display: inline-block;
    }

    .card-container {
        background: var(--gradient-card);
        border: 1px solid var(--border-subtle);
        border-radius: 20px;
        padding: 28px;
        backdrop-filter: blur(10px);
        margin-bottom: 24px;
    }

    .footer-text {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-muted);
        text-align: center;
        padding: 24px 0;
        border-top: 1px solid var(--border-subtle);
        margin-top: 48px;
    }

    .logo-container {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px;
        background: linear-gradient(135deg, rgba(20, 184, 166, 0.1) 0%, rgba(168, 85, 247, 0.05) 100%);
        border-radius: 16px;
        border: 1px solid var(--border-subtle);
        margin-bottom: 24px;
    }

    .logo-icon {
        font-size: 2rem;
    }

    .investigation-result {
        background: linear-gradient(135deg, rgba(20, 184, 166, 0.08) 0%, rgba(168, 85, 247, 0.04) 100%);
        border: 1px solid rgba(20, 184, 166, 0.2);
        border-radius: 16px;
        padding: 24px;
        margin-top: 20px;
    }

    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--bg-tertiary);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }

    /* Hide Streamlit branding but keep sidebar toggle */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Style the sidebar collapse/expand button */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {
        visibility: visible !important;
        opacity: 1 !important;
    }

    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="collapsedControl"] button {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        color: var(--text-secondary) !important;
        transition: all 0.2s ease;
    }

    [data-testid="stSidebarCollapseButton"] button:hover,
    [data-testid="collapsedControl"] button:hover {
        background: var(--bg-tertiary) !important;
        border-color: var(--accent-teal) !important;
        color: var(--accent-teal) !important;
    }

    /* Style the collapsed sidebar expand button */
    [data-testid="collapsedControl"] {
        position: fixed;
        top: 14px;
        left: 14px;
        z-index: 1000;
    }

    /* Header - hide the decoration but keep functional elements */
    [data-testid="stHeader"] {
        background: transparent !important;
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
                "aggs": {"services": {"terms": {"field": "service.name.keyword", "size": 20}}}
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
    """Render the 5-step investigation progress stepper."""
    steps = [
        {"id": "understand", "label": "Understand", "icon": "🎯", "desc": "Parse incident"},
        {"id": "search", "label": "Search", "icon": "🔍", "desc": "Find errors"},
        {"id": "analyze", "label": "Analyze", "icon": "📊", "desc": "Detect patterns"},
        {"id": "correlate", "label": "Correlate", "icon": "🔗", "desc": "Trace requests"},
        {"id": "synthesize", "label": "Synthesize", "icon": "💡", "desc": "Root cause"},
    ]

    completed_ids = [s["step"] for s in (completed_steps or [])]

    step_html = '<div style="display: flex; justify-content: space-between; align-items: center; margin: 24px 0; padding: 20px; background: rgba(20, 184, 166, 0.05); border-radius: 16px; border: 1px solid rgba(20, 184, 166, 0.1);">'

    for i, step in enumerate(steps):
        is_completed = step["id"] in completed_ids
        is_current = step["id"] == current_step
        is_pending = not is_completed and not is_current

        if is_completed:
            bg_color = "rgba(20, 184, 166, 0.2)"
            border_color = "#14b8a6"
            text_color = "#5eead4"
            icon_opacity = "1"
        elif is_current:
            bg_color = "rgba(245, 158, 11, 0.2)"
            border_color = "#f59e0b"
            text_color = "#fde047"
            icon_opacity = "1"
        else:
            bg_color = "rgba(255, 255, 255, 0.03)"
            border_color = "rgba(255, 255, 255, 0.1)"
            text_color = "#64748b"
            icon_opacity = "0.5"

        step_html += f'''
        <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: {bg_color};
                        border: 2px solid {border_color}; display: flex; align-items: center;
                        justify-content: center; font-size: 1.2rem; opacity: {icon_opacity};
                        transition: all 0.3s ease;">
                {"✓" if is_completed else step["icon"]}
            </div>
            <div style="font-family: 'Outfit', sans-serif; font-size: 0.8rem; font-weight: 600;
                        color: {text_color}; margin-top: 8px; text-transform: uppercase;
                        letter-spacing: 0.05em;">{step["label"]}</div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
                        color: #64748b; margin-top: 2px;">{step["desc"]}</div>
        </div>
        '''

        # Add connector line between steps
        if i < len(steps) - 1:
            line_color = "#14b8a6" if is_completed else "rgba(255, 255, 255, 0.1)"
            step_html += f'''
            <div style="flex: 0.5; height: 2px; background: {line_color};
                        margin: 0 -10px; margin-bottom: 30px;"></div>
            '''

    step_html += '</div>'
    return step_html


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

    # Color links based on error status
    link_colors = [
        "rgba(244, 63, 94, 0.6)" if f.get("has_error") else "rgba(20, 184, 166, 0.4)"
        for f in service_flow
    ]

    # Node colors - highlight error services
    error_services = set(f["target"] for f in service_flow if f.get("has_error"))
    node_colors = [
        "#f43f5e" if svc in error_services else "#14b8a6"
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
            font=dict(family='Outfit, sans-serif', size=14, color='#94a3b8'),
            x=0.5
        ),
        font=dict(family='JetBrains Mono, monospace', size=11, color='#f1f5f9'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


# Sidebar
with st.sidebar:
    # Logo and branding
    st.markdown("""
    <div class="logo-container">
        <span class="logo-icon">🔍</span>
        <div>
            <div style="font-family: 'Outfit', sans-serif; font-weight: 700; font-size: 1.4rem;
                        background: linear-gradient(135deg, #14b8a6 0%, #22d3ee 100%);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                LogSleuth
            </div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b;
                        text-transform: uppercase; letter-spacing: 0.1em;">
                Incident Investigator
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Connection status
    connected, status = check_connection()

    st.markdown("""
    <div style="font-family: 'Outfit', sans-serif; font-size: 0.75rem; color: #64748b;
                text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;">
        System Status
    </div>
    """, unsafe_allow_html=True)

    if connected:
        st.markdown(f"""
        <div class="status-badge status-online">
            <span class="pulse-dot online"></span>
            Connected
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #94a3b8; margin-top: 8px;">
            Cluster: {status}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-badge status-offline">
            <span class="pulse-dot offline"></span>
            Disconnected
        </div>
        """, unsafe_allow_html=True)
        st.caption(f"⚠️ {status}")
        st.info("Configure `.env` file with Elasticsearch credentials")

    st.divider()

    # Time range selector with custom label
    st.markdown("""
    <div style="font-family: 'Outfit', sans-serif; font-size: 0.75rem; color: #64748b;
                text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;">
        Time Window
    </div>
    """, unsafe_allow_html=True)

    time_range = st.selectbox(
        "Time Range",
        ["30m", "1h", "2h", "6h", "12h", "24h"],
        index=2,
        label_visibility="collapsed"
    )

    st.divider()

    # Auto refresh toggle
    auto_refresh = st.checkbox("⟳ Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.rerun()

    # Add spacing before footer
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

    # Footer with gradient accent (using relative positioning)
    st.markdown("""
    <div style="margin-top: auto; padding-top: 20px;">
        <div style="height: 2px; background: linear-gradient(90deg, #14b8a6 0%, #a855f7 100%);
                    border-radius: 1px; margin-bottom: 16px;"></div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #64748b; text-align: center;">
            Elasticsearch Agent Builder<br>Hackathon 2026
        </div>
    </div>
    """, unsafe_allow_html=True)


# Main content
st.markdown("""
<div style="margin-bottom: 32px;">
    <p class="main-header">🔍 LogSleuth</p>
    <p class="sub-header">AI-Powered Incident Investigation & Root Cause Analysis</p>
</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔎 Investigate", "📜 Log Search", "📚 History"])

# Tab 1: Dashboard
with tab1:
    if not connected:
        st.markdown("""
        <div class="card-container" style="text-align: center; padding: 60px;">
            <div style="font-size: 3rem; margin-bottom: 16px;">⚡</div>
            <div style="font-family: 'Outfit', sans-serif; font-size: 1.25rem; color: #f1f5f9; margin-bottom: 8px;">
                Connect to Elasticsearch
            </div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; color: #64748b;">
                Configure your connection to view the dashboard
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
                st.markdown('<div class="section-header">Errors Over Time</div>', unsafe_allow_html=True)
                if stats.get("histogram"):
                    df = pd.DataFrame(stats["histogram"])
                    df["timestamp"] = pd.to_datetime(df["timestamp"])

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df["timestamp"],
                        y=df["total_errors"],
                        mode='lines',
                        fill='tozeroy',
                        line=dict(color='#14b8a6', width=2),
                        fillcolor='rgba(20, 184, 166, 0.2)',
                        name='Errors'
                    ))
                    fig.update_layout(
                        height=320,
                        margin=dict(l=20, r=20, t=40, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='JetBrains Mono, monospace', color='#94a3b8'),
                        title=dict(text=f"Last {time_range}", font=dict(family='Outfit, sans-serif', color='#64748b', size=12)),
                        xaxis=dict(gridcolor='rgba(255,255,255,0.06)', linecolor='rgba(255,255,255,0.1)'),
                        yaxis=dict(gridcolor='rgba(255,255,255,0.06)', linecolor='rgba(255,255,255,0.1)'),
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No error data in selected time range")

            with col2:
                st.markdown('<div class="section-header">Errors by Service</div>', unsafe_allow_html=True)
                if stats.get("service_breakdown"):
                    df = pd.DataFrame(stats["service_breakdown"])

                    # Custom color palette
                    colors = ['#14b8a6', '#f59e0b', '#f43f5e', '#a855f7', '#3b82f6', '#22d3ee', '#84cc16']

                    fig = go.Figure(data=[go.Pie(
                        labels=df["service"],
                        values=df["error_count"],
                        hole=0.55,
                        marker=dict(colors=colors[:len(df)], line=dict(color='#0a0a0f', width=2)),
                        textfont=dict(family='JetBrains Mono, monospace', color='#f1f5f9', size=11),
                        textinfo='percent',
                        hovertemplate='<b>%{label}</b><br>Errors: %{value}<br>%{percent}<extra></extra>'
                    )])
                    fig.update_layout(
                        height=320,
                        margin=dict(l=20, r=20, t=40, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='Outfit, sans-serif', color='#94a3b8'),
                        showlegend=True,
                        legend=dict(
                            font=dict(family='JetBrains Mono, monospace', size=10, color='#94a3b8'),
                            bgcolor='rgba(0,0,0,0)'
                        ),
                        annotations=[dict(
                            text=f'{int(df["error_count"].sum()):,}',
                            x=0.5, y=0.5,
                            font=dict(family='JetBrains Mono, monospace', size=24, color='#f1f5f9'),
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
            <div style="font-family: 'Outfit', sans-serif; font-size: 1.25rem; color: #f1f5f9; margin-bottom: 8px;">
                Connect to Elasticsearch
            </div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; color: #64748b;">
                Configure your connection to run investigations
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Investigation input with styled container
        st.markdown("""
        <div style="font-family: 'Outfit', sans-serif; font-size: 0.875rem; color: #94a3b8; margin-bottom: 12px;">
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
            investigate_btn = st.button("🔍 Investigate", type="primary", use_container_width=True)

        if investigate_btn and incident_desc:
            # Show progress stepper placeholder
            stepper_placeholder = st.empty()
            status_placeholder = st.empty()

            # Track current step for animation
            def update_progress(step, message):
                stepper_placeholder.markdown(
                    render_investigation_stepper(current_step=step, completed_steps=[]),
                    unsafe_allow_html=True
                )
                status_placeholder.markdown(f"""
                <div style="text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; color: #94a3b8;">
                    {message}
                </div>
                """, unsafe_allow_html=True)

            with st.spinner("🔍 Running investigation..."):
                results = run_investigation(incident_desc, time_range)

            # Show completed stepper
            if results:
                stepper_placeholder.markdown(
                    render_investigation_stepper(completed_steps=results.get("steps_completed", [])),
                    unsafe_allow_html=True
                )
                status_placeholder.empty()

                st.markdown("""
                <div class="investigation-result">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
                        <span style="font-size: 1.5rem;">✅</span>
                        <span style="font-family: 'Outfit', sans-serif; font-size: 1.1rem; font-weight: 600; color: #5eead4;">
                            Investigation Complete
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

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
                    <div style="font-family: 'Outfit', sans-serif; font-size: 0.8rem; color: #64748b; margin-bottom: 12px;">
                        Visualizing how the request flowed between services. <span style="color: #f43f5e;">Red</span> indicates error propagation.
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

                    # Style the timeline dataframe
                    def style_timeline_level(val):
                        colors = {
                            "ERROR": "color: #f43f5e; font-weight: 600;",
                            "WARN": "color: #f59e0b; font-weight: 600;",
                            "INFO": "color: #3b82f6;",
                            "DEBUG": "color: #64748b;"
                        }
                        return colors.get(val, "")

                    styled_df = df.style.applymap(style_timeline_level, subset=["Level"])
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)

                st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

                # Findings with styled card
                st.markdown('<div class="section-header">Analysis & Recommendations</div>', unsafe_allow_html=True)

                root_cause = results["root_cause"] or "Unable to determine"
                affected = ", ".join(results["services"][:5]) or "None identified"
                total_errors = int(results["errors"]["total_errors"]) if results["errors"] else 0

                st.markdown(f"""
                <div class="card-container">
                    <div style="margin-bottom: 20px;">
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b;
                                    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;">Incident</div>
                        <div style="font-family: 'Outfit', sans-serif; font-size: 1rem; color: #f1f5f9;">{incident_desc}</div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px;">
                        <div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b;
                                        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;">Root Cause</div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; color: #f43f5e; font-weight: 600;">{root_cause}</div>
                        </div>
                        <div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b;
                                        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;">Affected Services</div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; color: #f59e0b;">{affected}</div>
                        </div>
                        <div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b;
                                        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;">Total Errors</div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; color: #14b8a6; font-weight: 600;">{total_errors:,}</div>
                        </div>
                    </div>
                    <div style="border-top: 1px solid rgba(255,255,255,0.06); padding-top: 20px;">
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b;
                                    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px;">Recommended Actions</div>
                        <div style="font-family: 'Outfit', sans-serif; font-size: 0.9rem; color: #94a3b8; line-height: 1.8;">
                            <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px;">
                                <span style="color: #14b8a6;">1.</span>
                                <span>Review error logs from <span style="color: #f1f5f9; font-weight: 500;">{root_cause}</span> service</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px;">
                                <span style="color: #14b8a6;">2.</span>
                                <span>Check recent deployments or configuration changes</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px;">
                                <span style="color: #14b8a6;">3.</span>
                                <span>Verify database and external service connectivity</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; gap: 10px;">
                                <span style="color: #14b8a6;">4.</span>
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
            <div style="font-family: 'Outfit', sans-serif; font-size: 1.25rem; color: #f1f5f9; margin-bottom: 8px;">
                Connect to Elasticsearch
            </div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; color: #64748b;">
                Configure your connection to search logs
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Search description
        st.markdown("""
        <div style="font-family: 'Outfit', sans-serif; font-size: 0.875rem; color: #94a3b8; margin-bottom: 16px;">
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
            search_btn = st.button("Search", type="primary", use_container_width=True)

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        if search_btn and search_query:
            with st.spinner("🔍 Searching logs..."):
                results = search_logs_data(
                    search_query,
                    time_range,
                    service_filter,
                    level_filter,
                )

            if results:
                # Results header with count
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                    <div style="font-family: 'Outfit', sans-serif; font-size: 0.9rem; color: #94a3b8;">
                        Found <span style="color: #14b8a6; font-weight: 600; font-family: 'JetBrains Mono', monospace;">{results['total']}</span> logs matching
                    </div>
                    <div style="background: rgba(20, 184, 166, 0.15); border: 1px solid rgba(20, 184, 166, 0.3);
                                padding: 4px 12px; border-radius: 20px; font-family: 'JetBrains Mono', monospace;
                                font-size: 0.8rem; color: #5eead4;">
                        "{search_query}"
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

                    # Style the dataframe with dark theme colors
                    def highlight_log_level(val):
                        if val == "ERROR":
                            return "background-color: rgba(244, 63, 94, 0.2); color: #fda4af; font-weight: 600;"
                        elif val == "WARN":
                            return "background-color: rgba(245, 158, 11, 0.2); color: #fde047; font-weight: 600;"
                        elif val == "INFO":
                            return "color: #93c5fd;"
                        elif val == "DEBUG":
                            return "color: #64748b;"
                        return ""

                    styled_df = df.style.applymap(highlight_log_level, subset=["Level"])
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                else:
                    st.markdown("""
                    <div class="card-container" style="text-align: center; padding: 40px;">
                        <div style="font-size: 2rem; margin-bottom: 12px;">🔍</div>
                        <div style="font-family: 'Outfit', sans-serif; font-size: 1rem; color: #94a3b8;">
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
            <div style="font-family: 'Outfit', sans-serif; font-size: 1.25rem; color: #f1f5f9; margin-bottom: 8px;">
                Connect to Elasticsearch
            </div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; color: #64748b;">
                Configure your connection to view investigation history
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        from src.tools import search_past_incidents

        client = get_es_client()

        st.markdown("""
        <div style="font-family: 'Outfit', sans-serif; font-size: 0.875rem; color: #94a3b8; margin-bottom: 16px;">
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
                    <div style="font-family: 'Outfit', sans-serif; font-size: 0.9rem; color: #94a3b8;">
                        Found <span style="color: #a855f7; font-weight: 600; font-family: 'JetBrains Mono', monospace;">{results['total']}</span> past incidents
                    </div>
                </div>
                """, unsafe_allow_html=True)

                for inc in results["incidents"]:
                    incident_id = inc.get('id', 'Unknown')
                    incident_date = inc.get('timestamp', '')[:10] if inc.get('timestamp') else 'Unknown date'
                    root_cause = inc.get('root_cause', 'Not recorded')
                    services = ', '.join(inc.get('affected_services', [])) or 'None'
                    resolution = inc.get('resolution', 'Not recorded')

                    with st.expander(f"📋 **{incident_id}** — {incident_date}"):
                        st.markdown(f"""
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 16px;">
                            <div>
                                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b;
                                            text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">Root Cause</div>
                                <div style="font-family: 'Outfit', sans-serif; font-size: 0.9rem; color: #f43f5e;">{root_cause}</div>
                            </div>
                            <div>
                                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b;
                                            text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">Affected Services</div>
                                <div style="font-family: 'Outfit', sans-serif; font-size: 0.9rem; color: #f59e0b;">{services}</div>
                            </div>
                        </div>
                        <div style="margin-bottom: 12px;">
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b;
                                        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">Resolution</div>
                            <div style="font-family: 'Outfit', sans-serif; font-size: 0.9rem; color: #94a3b8;">{resolution}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if inc.get("suggestions"):
                            st.markdown(f"""
                            <div style="background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.2);
                                        border-radius: 8px; padding: 12px; margin-top: 12px;">
                                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #a855f7;
                                            text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;">💡 Suggestions</div>
                                <div style="font-family: 'Outfit', sans-serif; font-size: 0.875rem; color: #c4b5fd;">
                                    {inc.get('suggestions')}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="card-container" style="text-align: center; padding: 40px;">
                    <div style="font-size: 2rem; margin-bottom: 12px;">📭</div>
                    <div style="font-family: 'Outfit', sans-serif; font-size: 1rem; color: #f1f5f9; margin-bottom: 8px;">
                        No past incidents found
                    </div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #64748b;">
                        Run some investigations first to build your knowledge base
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card-container" style="text-align: center; padding: 48px;">
                <div style="font-size: 2.5rem; margin-bottom: 16px;">📚</div>
                <div style="font-family: 'Outfit', sans-serif; font-size: 1.1rem; color: #f1f5f9; margin-bottom: 8px;">
                    Search Your Investigation History
                </div>
                <div style="font-family: 'Outfit', sans-serif; font-size: 0.875rem; color: #64748b;">
                    Enter a keyword above to find past incidents and their resolutions
                </div>
            </div>
            """, unsafe_allow_html=True)


# Footer
st.markdown("""
<div class="footer-text">
    <div style="display: flex; justify-content: center; align-items: center; gap: 16px; margin-bottom: 8px;">
        <span style="color: #14b8a6;">●</span>
        <span>LogSleuth v0.1.0</span>
        <span style="color: #64748b;">|</span>
        <span>Powered by Elasticsearch</span>
        <span style="color: #a855f7;">●</span>
    </div>
    <div style="font-size: 0.65rem; color: #475569;">
        Elasticsearch Agent Builder Hackathon 2026
    </div>
</div>
""", unsafe_allow_html=True)
