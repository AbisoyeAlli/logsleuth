"""
Find Correlated Logs Tool

Finds all logs sharing the same trace_id to trace requests across services.
Essential for understanding how errors propagate through a microservices architecture.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch

from src.utils.elasticsearch_client import LOG_INDEX


# ES|QL query for Agent Builder deployment
ESQL_QUERY = """
FROM logs-logsleuth
| WHERE trace.id == ?trace_id
| SORT @timestamp ASC
| LIMIT 100
"""

# Alternative: Find trace_ids from error logs, then get full trace
ESQL_FIND_ERROR_TRACES = """
FROM logs-logsleuth
| WHERE @timestamp >= NOW() - ?time_range
| WHERE log.level == "error"
| WHERE service.name == ?service_name
| WHERE trace.id IS NOT NULL
| KEEP @timestamp, trace.id, service.name, message, error.type
| SORT @timestamp DESC
| LIMIT 20
"""

# Tool definition for Agent Builder API
TOOL_DEFINITION = {
    "toolId": "find_correlated_logs",
    "description": """Find all logs that share the same trace_id, showing how a request flowed through multiple services.

Use this tool when:
- You have a trace_id and want to see the full request journey
- You need to understand how an error propagated across services
- You want to build a timeline of events for a specific request
- You're investigating which service was the root cause

Returns logs from all services involved in the traced request, ordered chronologically.""",
    "labels": ["correlation", "tracing", "distributed"],
    "type": "esql",
    "configuration": {
        "query": ESQL_QUERY
    },
    "parameters": [
        {
            "name": "trace_id",
            "type": "string",
            "description": "The trace ID to look up. Get this from error logs or search results.",
            "required": True
        }
    ]
}

# Additional tool for finding traces from errors
FIND_ERROR_TRACES_TOOL = {
    "toolId": "find_error_traces",
    "description": """Find trace IDs from recent error logs for a specific service.

Use this tool when:
- You need to find trace_ids to investigate further
- You want to identify which requests resulted in errors
- You're starting an investigation and need entry points

Returns trace IDs from error logs that can be used with find_correlated_logs.""",
    "labels": ["correlation", "errors", "discovery"],
    "type": "esql",
    "configuration": {
        "query": ESQL_FIND_ERROR_TRACES
    },
    "parameters": [
        {
            "name": "service_name",
            "type": "string",
            "description": "The service to find error traces from",
            "required": True
        },
        {
            "name": "time_range",
            "type": "string",
            "description": "Time range to search (e.g., '1h', '30m')",
            "required": True
        }
    ]
}


def find_correlated_logs(
    client: Elasticsearch,
    trace_id: str,
) -> Dict[str, Any]:
    """
    Find all logs sharing the same trace_id.

    Args:
        client: Elasticsearch client
        trace_id: The trace ID to search for

    Returns:
        Dict with timeline of logs across all services
    """
    query = {
        "query": {
            "term": {"trace.id": trace_id}
        },
        "sort": [{"@timestamp": "asc"}],
        "size": 100,
        "_source": [
            "@timestamp",
            "message",
            "log.level",
            "service.name",
            "error.type",
            "error.message",
            "span.id",
            "host.name",
            "http.request.method",
            "http.request.path",
            "http.response.status_code",
            "event.duration",
            "event.outcome",
        ]
    }

    result = client.search(index=LOG_INDEX, body=query)

    # Build timeline
    timeline = []
    services_involved = set()
    has_errors = False
    root_cause_service = None
    first_error_time = None

    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        service = src.get("service", {}).get("name", "unknown")
        services_involved.add(service)

        entry = {
            "timestamp": src.get("@timestamp"),
            "service": service,
            "level": src.get("log", {}).get("level"),
            "message": src.get("message"),
            "span_id": src.get("span", {}).get("id"),
            "host": src.get("host", {}).get("name"),
        }

        # Add HTTP details if present
        if "http" in src:
            entry["http_method"] = src.get("http", {}).get("request", {}).get("method")
            entry["http_path"] = src.get("http", {}).get("request", {}).get("path")
            entry["http_status"] = src.get("http", {}).get("response", {}).get("status_code")

        # Add error details if present
        if "error" in src:
            entry["error_type"] = src["error"].get("type")
            entry["error_message"] = src["error"].get("message")
            has_errors = True

            # Track first error (likely root cause)
            if first_error_time is None:
                first_error_time = src.get("@timestamp")
                root_cause_service = service

        # Add duration if present
        if "event" in src:
            duration_ns = src.get("event", {}).get("duration")
            if duration_ns:
                entry["duration_ms"] = duration_ns / 1_000_000

        timeline.append(entry)

    return {
        "trace_id": trace_id,
        "total_logs": result["hits"]["total"]["value"],
        "services_involved": list(services_involved),
        "has_errors": has_errors,
        "root_cause_service": root_cause_service,
        "first_error_time": first_error_time,
        "timeline": timeline,
    }


def find_error_traces(
    client: Elasticsearch,
    service_name: str,
    time_range: str = "1h",
    max_traces: int = 10,
) -> Dict[str, Any]:
    """
    Find trace IDs from error logs for a specific service.

    Args:
        client: Elasticsearch client
        service_name: Service to find errors from
        time_range: Time range to search
        max_traces: Maximum number of traces to return

    Returns:
        Dict with list of trace IDs and their error summaries
    """
    # Parse time range
    time_value = int(time_range[:-1])
    time_unit = time_range[-1]

    if time_unit == 'h':
        time_delta = timedelta(hours=time_value)
    elif time_unit == 'm':
        time_delta = timedelta(minutes=time_value)
    elif time_unit == 'd':
        time_delta = timedelta(days=time_value)
    else:
        time_delta = timedelta(hours=1)

    start_time = datetime.utcnow() - time_delta

    query = {
        "query": {
            "bool": {
                "filter": [
                    {"range": {"@timestamp": {"gte": start_time.isoformat()}}},
                    {"term": {"log.level": "error"}},
                    {"term": {"service.name": service_name}},
                    {"exists": {"field": "trace.id"}},
                ]
            }
        },
        "sort": [{"@timestamp": "desc"}],
        "size": max_traces * 2,  # Get extra in case of duplicates
        "_source": [
            "@timestamp",
            "trace.id",
            "message",
            "error.type",
            "error.message",
        ]
    }

    result = client.search(index=LOG_INDEX, body=query)

    # Deduplicate by trace_id
    seen_traces = set()
    traces = []

    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        trace_id = src.get("trace", {}).get("id")

        if trace_id and trace_id not in seen_traces:
            seen_traces.add(trace_id)
            traces.append({
                "trace_id": trace_id,
                "timestamp": src.get("@timestamp"),
                "error_type": src.get("error", {}).get("type"),
                "message": src.get("message", "")[:100],
            })

            if len(traces) >= max_traces:
                break

    return {
        "service_name": service_name,
        "time_range": time_range,
        "traces_found": len(traces),
        "traces": traces,
    }


if __name__ == "__main__":
    # Test the tool locally
    from src.utils.elasticsearch_client import get_elasticsearch_client

    client = get_elasticsearch_client()

    # First, find some error traces
    print("Finding error traces from payment-service...")
    traces = find_error_traces(
        client,
        service_name="payment-service",
        time_range="2h",
    )

    print(f"Found {traces['traces_found']} traces")
    for t in traces["traces"][:3]:
        print(f"  - {t['trace_id']}: [{t['error_type']}] {t['message'][:50]}...")

    # Then trace one of them
    if traces["traces"]:
        trace_id = traces["traces"][0]["trace_id"]
        print(f"\nTracing {trace_id}...")

        correlated = find_correlated_logs(client, trace_id)
        print(f"Services involved: {correlated['services_involved']}")
        print(f"Root cause service: {correlated['root_cause_service']}")
        print(f"\nTimeline:")
        for entry in correlated["timeline"]:
            level = entry.get("level", "info").upper()
            print(f"  {entry['timestamp']} [{level}] {entry['service']}: {entry['message'][:50]}...")
