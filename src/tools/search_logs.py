"""
Search Logs Tool

Searches Elasticsearch for logs matching specified criteria.
This is the primary tool for finding relevant log entries during incident investigation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch

from src.utils.elasticsearch_client import LOG_INDEX


# ES|QL query for Agent Builder deployment
ESQL_QUERY = """
FROM logs-logsleuth
| WHERE @timestamp >= NOW() - ?time_range
| WHERE message LIKE ?search_query OR error.message LIKE ?search_query
| WHERE (?service_name == "" OR service.name == ?service_name)
| WHERE (?log_level == "" OR log.level == ?log_level)
| SORT @timestamp DESC
| LIMIT ?max_results
"""

# Tool definition for Agent Builder API
TOOL_DEFINITION = {
    "toolId": "search_logs",
    "description": """Search for logs in Elasticsearch matching the given criteria.

Use this tool when:
- The user asks about errors, warnings, or specific log messages
- You need to find logs from a specific service
- You need to search for logs within a time range
- You're investigating an incident and need to find relevant log entries

The tool returns log entries with timestamp, service name, log level, message, and error details if present.""",
    "labels": ["retrieval", "logs", "search"],
    "type": "esql",
    "configuration": {
        "query": ESQL_QUERY
    },
    "parameters": [
        {
            "name": "search_query",
            "type": "string",
            "description": "Search term to find in log messages (supports wildcards with *)",
            "required": True
        },
        {
            "name": "time_range",
            "type": "string",
            "description": "Time range to search, e.g., '1h' for last hour, '30m' for 30 minutes, '1d' for 1 day",
            "required": True
        },
        {
            "name": "service_name",
            "type": "string",
            "description": "Filter by service name (e.g., 'payment-service', 'checkout-service'). Leave empty for all services.",
            "required": False
        },
        {
            "name": "log_level",
            "type": "string",
            "description": "Filter by log level: 'error', 'warn', 'info', or 'debug'. Leave empty for all levels.",
            "required": False
        },
        {
            "name": "max_results",
            "type": "integer",
            "description": "Maximum number of results to return (default: 50, max: 200)",
            "required": False
        }
    ]
}


def search_logs(
    client: Elasticsearch,
    search_query: str,
    time_range: str = "1h",
    service_name: Optional[str] = None,
    log_level: Optional[str] = None,
    max_results: int = 50,
) -> Dict[str, Any]:
    """
    Search for logs matching the given criteria.

    This is the Python implementation for local testing.
    In production, this runs as an ES|QL query in Agent Builder.

    Args:
        client: Elasticsearch client
        search_query: Search term to find in messages
        time_range: Time range (e.g., "1h", "30m", "1d")
        service_name: Optional service name filter
        log_level: Optional log level filter
        max_results: Maximum results to return

    Returns:
        Dict with 'hits' list and 'total' count
    """
    # Parse time range to datetime
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

    # Build query
    must_clauses = [
        {"range": {"@timestamp": {"gte": start_time.isoformat()}}},
        {
            "bool": {
                "should": [
                    {"wildcard": {"message": f"*{search_query}*"}},
                    {"wildcard": {"error.message": f"*{search_query}*"}},
                    {"match": {"message": search_query}},
                    {"match": {"error.message": search_query}},
                ],
                "minimum_should_match": 1
            }
        }
    ]

    if service_name:
        must_clauses.append({"term": {"service.name.keyword": service_name}})

    if log_level:
        must_clauses.append({"term": {"log.level.keyword": log_level}})

    query = {
        "query": {"bool": {"must": must_clauses}},
        "sort": [{"@timestamp": "desc"}],
        "size": min(max_results, 200),
        "_source": [
            "@timestamp",
            "message",
            "log.level",
            "service.name",
            "error.type",
            "error.message",
            "trace.id",
            "host.name",
            "http.response.status_code",
            "event.outcome",
        ]
    }

    result = client.search(index=LOG_INDEX, body=query)

    # Format results
    hits = []
    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        formatted = {
            "timestamp": src.get("@timestamp"),
            "service": src.get("service", {}).get("name"),
            "level": src.get("log", {}).get("level"),
            "message": src.get("message"),
            "trace_id": src.get("trace", {}).get("id"),
            "host": src.get("host", {}).get("name"),
        }

        # Add error details if present
        if "error" in src:
            formatted["error_type"] = src["error"].get("type")
            formatted["error_message"] = src["error"].get("message")

        # Add HTTP status if present
        if "http" in src:
            formatted["http_status"] = src.get("http", {}).get("response", {}).get("status_code")

        hits.append(formatted)

    return {
        "total": result["hits"]["total"]["value"],
        "hits": hits,
        "query_info": {
            "search_query": search_query,
            "time_range": time_range,
            "service_name": service_name,
            "log_level": log_level,
        }
    }


if __name__ == "__main__":
    # Test the tool locally
    from src.utils.elasticsearch_client import get_elasticsearch_client

    client = get_elasticsearch_client()

    # Test search
    results = search_logs(
        client,
        search_query="Connection refused",
        time_range="2h",
        log_level="error",
    )

    print(f"Found {results['total']} logs")
    for hit in results["hits"][:5]:
        print(f"  [{hit['level']}] {hit['service']}: {hit['message'][:60]}...")
