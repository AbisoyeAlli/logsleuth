"""
Get Error Frequency Tool

Analyzes error patterns over time to identify spikes and anomalies.
Critical for understanding when an incident started and its severity.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch

from src.utils.elasticsearch_client import LOG_INDEX


# ES|QL query for Agent Builder deployment
ESQL_QUERY = """
FROM logs-logsleuth
| WHERE @timestamp >= NOW() - ?time_range
| WHERE log.level == "error"
| WHERE (?service_name == "" OR service.name == ?service_name)
| WHERE (?error_type == "" OR error.type == ?error_type)
| STATS error_count = COUNT(*) BY service.name, error.type
| SORT error_count DESC
| LIMIT 50
"""

# Alternative query for time-based histogram
ESQL_HISTOGRAM_QUERY = """
FROM logs-logsleuth
| WHERE @timestamp >= NOW() - ?time_range
| WHERE log.level == "error"
| WHERE (?service_name == "" OR service.name == ?service_name)
| EVAL time_bucket = DATE_TRUNC(?interval, @timestamp)
| STATS error_count = COUNT(*) BY time_bucket, service.name
| SORT time_bucket ASC
"""

# Tool definition for Agent Builder API
TOOL_DEFINITION = {
    "toolId": "get_error_frequency",
    "description": """Analyze error frequency and patterns over time.

Use this tool when:
- You need to identify when errors started occurring (incident start time)
- You want to see error trends and spikes
- You need to compare error rates across services
- You're determining the severity of an incident

Returns error counts grouped by service and error type, helping identify patterns and anomalies.""",
    "labels": ["analytics", "errors", "metrics"],
    "type": "esql",
    "configuration": {
        "query": ESQL_QUERY
    },
    "parameters": [
        {
            "name": "time_range",
            "type": "string",
            "description": "Time range to analyze, e.g., '1h', '30m', '2h', '1d'",
            "required": True
        },
        {
            "name": "service_name",
            "type": "string",
            "description": "Filter by specific service name. Leave empty for all services.",
            "required": False
        },
        {
            "name": "error_type",
            "type": "string",
            "description": "Filter by error type (e.g., 'ConnectionException', 'TimeoutException'). Leave empty for all types.",
            "required": False
        }
    ]
}


def get_error_frequency(
    client: Elasticsearch,
    time_range: str = "1h",
    service_name: Optional[str] = None,
    error_type: Optional[str] = None,
    interval: str = "5m",
) -> Dict[str, Any]:
    """
    Get error frequency statistics over time.

    Args:
        client: Elasticsearch client
        time_range: Time range to analyze (e.g., "1h", "30m")
        service_name: Optional service filter
        error_type: Optional error type filter
        interval: Bucket interval for histogram (e.g., "1m", "5m")

    Returns:
        Dict with error statistics and time-based histogram
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

    # Build filter clauses (use .keyword for text fields)
    filter_clauses = [
        {"range": {"@timestamp": {"gte": start_time.isoformat()}}},
        {"term": {"log.level.keyword": "error"}},
    ]

    if service_name:
        filter_clauses.append({"term": {"service.name.keyword": service_name}})
    if error_type:
        filter_clauses.append({"term": {"error.type.keyword": error_type}})

    # Query 1: Error counts by service and type (use .keyword for text fields)
    stats_query = {
        "query": {"bool": {"filter": filter_clauses}},
        "size": 0,
        "aggs": {
            "by_service": {
                "terms": {"field": "service.name.keyword", "size": 20},
                "aggs": {
                    "by_error_type": {
                        "terms": {"field": "error.type.keyword", "size": 10}
                    }
                }
            },
            "total_errors": {"value_count": {"field": "@timestamp"}}
        }
    }

    stats_result = client.search(index=LOG_INDEX, body=stats_query)

    # Query 2: Time-based histogram
    histogram_query = {
        "query": {"bool": {"filter": filter_clauses}},
        "size": 0,
        "aggs": {
            "errors_over_time": {
                "date_histogram": {
                    "field": "@timestamp",
                    "fixed_interval": interval,
                },
                "aggs": {
                    "by_service": {
                        "terms": {"field": "service.name.keyword", "size": 10}
                    }
                }
            }
        }
    }

    histogram_result = client.search(index=LOG_INDEX, body=histogram_query)

    # Format service breakdown
    service_breakdown = []
    for service_bucket in stats_result["aggregations"]["by_service"]["buckets"]:
        service_data = {
            "service": service_bucket["key"],
            "error_count": service_bucket["doc_count"],
            "error_types": [
                {"type": et["key"], "count": et["doc_count"]}
                for et in service_bucket["by_error_type"]["buckets"]
            ]
        }
        service_breakdown.append(service_data)

    # Format histogram
    histogram = []
    for bucket in histogram_result["aggregations"]["errors_over_time"]["buckets"]:
        if bucket["doc_count"] > 0:
            histogram.append({
                "timestamp": bucket["key_as_string"],
                "total_errors": bucket["doc_count"],
                "by_service": {
                    s["key"]: s["doc_count"]
                    for s in bucket["by_service"]["buckets"]
                }
            })

    # Identify spike (bucket with highest error count)
    spike = None
    if histogram:
        max_bucket = max(histogram, key=lambda x: x["total_errors"])
        avg_errors = sum(h["total_errors"] for h in histogram) / len(histogram)
        if max_bucket["total_errors"] > avg_errors * 2:  # Spike = 2x average
            spike = {
                "timestamp": max_bucket["timestamp"],
                "error_count": max_bucket["total_errors"],
                "severity": "high" if max_bucket["total_errors"] > avg_errors * 5 else "medium"
            }

    return {
        "total_errors": stats_result["aggregations"]["total_errors"]["value"],
        "time_range": time_range,
        "interval": interval,
        "service_breakdown": service_breakdown,
        "histogram": histogram,
        "spike_detected": spike,
        "query_info": {
            "service_name": service_name,
            "error_type": error_type,
        }
    }


if __name__ == "__main__":
    # Test the tool locally
    from src.utils.elasticsearch_client import get_elasticsearch_client

    client = get_elasticsearch_client()

    results = get_error_frequency(
        client,
        time_range="2h",
        interval="5m",
    )

    print(f"Total errors: {results['total_errors']}")
    print(f"\nService breakdown:")
    for svc in results["service_breakdown"]:
        print(f"  {svc['service']}: {svc['error_count']} errors")
        for et in svc["error_types"]:
            print(f"    - {et['type']}: {et['count']}")

    if results["spike_detected"]:
        print(f"\nSpike detected at {results['spike_detected']['timestamp']}")
        print(f"  Error count: {results['spike_detected']['error_count']}")
        print(f"  Severity: {results['spike_detected']['severity']}")
