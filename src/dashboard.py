#!/usr/bin/env python3
"""
LogSleuth Dashboard - Streamlit-based incident investigation interface.

Run with: streamlit run src/dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
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

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-top: 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .error-text {
        color: #ff4b4b;
    }
    .success-text {
        color: #00c853;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
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


def run_investigation(description: str, time_range: str):
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
    }

    # Get error frequency
    error_freq = get_error_frequency(client, time_range=time_range)
    if error_freq:
        results["errors"] = error_freq
        results["services"] = [s["service"] for s in error_freq.get("service_breakdown", [])]

        # Get root cause service
        if error_freq.get("service_breakdown"):
            root_service = error_freq["service_breakdown"][0]["service"]
            results["root_cause"] = root_service

            # Find traces
            traces = find_error_traces(client, service_name=root_service, time_range=time_range)
            if traces.get("traces"):
                trace_id = traces["traces"][0]["trace_id"]
                trace_info = find_correlated_logs(client, trace_id)
                results["trace_info"] = trace_info
                results["timeline"] = trace_info.get("timeline", [])

    return results


# Sidebar
with st.sidebar:
    st.image("https://www.elastic.co/favicon-32x32.png", width=32)
    st.title("LogSleuth")
    st.caption("Intelligent Incident Investigator")

    st.divider()

    # Connection status
    connected, status = check_connection()
    if connected:
        st.success(f"Connected: {status}")
    else:
        st.error("Disconnected")
        st.caption(status)
        st.info("Configure .env file with Elasticsearch credentials")

    st.divider()

    # Time range selector
    time_range = st.selectbox(
        "Time Range",
        ["30m", "1h", "2h", "6h", "12h", "24h"],
        index=2,
    )

    # Auto refresh
    auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.experimental_rerun()

    st.divider()
    st.caption("Built for Elasticsearch Agent Builder Hackathon 2026")


# Main content
st.markdown('<p class="main-header">🔍 LogSleuth</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-Powered Incident Investigation</p>', unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔎 Investigate", "📜 Log Search", "📚 History"])

# Tab 1: Dashboard
with tab1:
    if not connected:
        st.warning("Connect to Elasticsearch to view dashboard")
    else:
        # Get stats
        stats = get_error_stats(time_range)

        if stats:
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total Errors",
                    f"{int(stats['total_errors']):,}",
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

            st.divider()

            # Charts row
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Errors Over Time")
                if stats.get("histogram"):
                    df = pd.DataFrame(stats["histogram"])
                    df["timestamp"] = pd.to_datetime(df["timestamp"])

                    fig = px.area(
                        df,
                        x="timestamp",
                        y="total_errors",
                        title=f"Error Count (Last {time_range})",
                        labels={"total_errors": "Errors", "timestamp": "Time"},
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No error data in selected time range")

            with col2:
                st.subheader("Errors by Service")
                if stats.get("service_breakdown"):
                    df = pd.DataFrame(stats["service_breakdown"])

                    fig = px.pie(
                        df,
                        values="error_count",
                        names="service",
                        title="Error Distribution",
                        hole=0.4,
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No service data available")

            # Service breakdown table
            st.subheader("Service Error Breakdown")
            if stats.get("service_breakdown"):
                for svc in stats["service_breakdown"]:
                    with st.expander(f"**{svc['service']}** - {svc['error_count']} errors"):
                        error_df = pd.DataFrame(svc.get("error_types", []))
                        if not error_df.empty:
                            st.dataframe(error_df, use_container_width=True, hide_index=True)

# Tab 2: Investigate
with tab2:
    st.subheader("Incident Investigation")

    if not connected:
        st.warning("Connect to Elasticsearch to run investigations")
    else:
        # Investigation input
        col1, col2 = st.columns([3, 1])
        with col1:
            incident_desc = st.text_input(
                "Describe the incident",
                placeholder="e.g., checkout-service throwing timeout errors",
            )
        with col2:
            investigate_btn = st.button("🔍 Investigate", type="primary", use_container_width=True)

        if investigate_btn and incident_desc:
            with st.spinner("Investigating..."):
                results = run_investigation(incident_desc, time_range)

            if results:
                st.success("Investigation Complete")

                # Summary cards
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Errors", int(results["errors"]["total_errors"]) if results["errors"] else 0)
                with col2:
                    st.metric("Services Affected", len(results["services"]))
                with col3:
                    st.metric("Root Cause Service", results["root_cause"] or "Unknown")

                st.divider()

                # Timeline
                if results["timeline"]:
                    st.subheader("Request Timeline")

                    timeline_data = []
                    for entry in results["timeline"][:15]:
                        timeline_data.append({
                            "Time": entry.get("timestamp", "")[:19].replace("T", " "),
                            "Service": entry.get("service", ""),
                            "Level": entry.get("level", "").upper(),
                            "Message": entry.get("message", "")[:80],
                        })

                    df = pd.DataFrame(timeline_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                # Findings
                st.subheader("Findings")

                findings_md = f"""
**Incident**: {incident_desc}

**Root Cause Service**: {results["root_cause"] or "Unable to determine"}

**Affected Services**: {", ".join(results["services"][:5]) or "None identified"}

**Total Errors**: {int(results["errors"]["total_errors"]) if results["errors"] else 0}

### Recommended Actions

1. Review error logs from **{results["root_cause"]}** service
2. Check recent deployments or configuration changes
3. Verify database and external service connectivity
4. Consider enabling circuit breakers if not already active
"""
                st.markdown(findings_md)

        elif investigate_btn:
            st.warning("Please enter an incident description")

# Tab 3: Log Search
with tab3:
    st.subheader("Log Search")

    if not connected:
        st.warning("Connect to Elasticsearch to search logs")
    else:
        # Search filters
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            search_query = st.text_input("Search Query", placeholder="Enter search term...")
        with col2:
            services = get_services_list()
            service_filter = st.selectbox("Service", services)
        with col3:
            level_filter = st.selectbox("Level", ["All Levels", "error", "warn", "info", "debug"])
        with col4:
            search_btn = st.button("Search", type="primary", use_container_width=True)

        if search_btn and search_query:
            with st.spinner("Searching..."):
                results = search_logs_data(
                    search_query,
                    time_range,
                    service_filter,
                    level_filter,
                )

            if results:
                st.info(f"Found {results['total']} logs matching '{search_query}'")

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

                    # Style the dataframe
                    def highlight_level(val):
                        if val == "ERROR":
                            return "background-color: #ffcdd2"
                        elif val == "WARN":
                            return "background-color: #fff9c4"
                        return ""

                    styled_df = df.style.applymap(highlight_level, subset=["Level"])
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
        elif search_btn:
            st.warning("Please enter a search query")

# Tab 4: History
with tab4:
    st.subheader("Past Investigations")

    if not connected:
        st.warning("Connect to Elasticsearch to view history")
    else:
        from src.tools import search_past_incidents

        client = get_es_client()
        history_query = st.text_input("Search past incidents", placeholder="e.g., database, timeout, connection")

        if history_query:
            results = search_past_incidents(client, search_terms=history_query)

            if results.get("incidents"):
                st.info(f"Found {results['total']} past incidents")

                for inc in results["incidents"]:
                    with st.expander(f"**{inc.get('id', 'Unknown')}** - {inc.get('timestamp', '')[:10] if inc.get('timestamp') else 'Unknown date'}"):
                        st.markdown(f"**Root Cause:** {inc.get('root_cause', 'Not recorded')}")
                        st.markdown(f"**Services:** {', '.join(inc.get('affected_services', []))}")
                        st.markdown(f"**Resolution:** {inc.get('resolution', 'Not recorded')}")
                        if inc.get("suggestions"):
                            st.markdown(f"**Suggestions:**\n{inc.get('suggestions')}")
            else:
                st.info("No past incidents found. Run some investigations first!")
        else:
            st.caption("Enter a search term to find past incidents")


# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col2:
    st.caption("LogSleuth v0.1.0 | Elasticsearch Agent Builder Hackathon 2026")
