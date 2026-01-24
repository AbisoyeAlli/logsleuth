#!/usr/bin/env python3
"""
Test script for LogSleuth Elasticsearch queries.

This script tests the core queries that will be used by the agent tools:
1. Search logs by keyword/error
2. Get error frequency over time
3. Find correlated logs by trace_id
4. Search by service and time range

Usage:
    python scripts/test_queries.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.elasticsearch_client import get_elasticsearch_client, LOG_INDEX


def test_search_logs_by_keyword(client, keyword: str = "Connection refused"):
    """Test searching logs by keyword."""
    print(f"\n{'='*60}")
    print(f"TEST: Search logs containing '{keyword}'")
    print("="*60)

    result = client.search(
        index=LOG_INDEX,
        body={
            "query": {
                "bool": {
                    "should": [
                        {"match": {"message": keyword}},
                        {"match": {"error.message": keyword}},
                    ]
                }
            },
            "sort": [{"@timestamp": "desc"}],
            "size": 5,
        }
    )

    print(f"Found {result['hits']['total']['value']} matching logs")
    print("\nTop 5 results:")
    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        print(f"  - [{src['log']['level'].upper()}] {src['service']['name']}: {src['message'][:80]}...")

    return result["hits"]["total"]["value"] > 0


def test_search_by_service_and_level(client, service: str = "payment-service", level: str = "error"):
    """Test searching logs by service and log level."""
    print(f"\n{'='*60}")
    print(f"TEST: Search {level} logs from {service}")
    print("="*60)

    result = client.search(
        index=LOG_INDEX,
        body={
            "query": {
                "bool": {
                    "must": [
                        {"term": {"service.name": service}},
                        {"term": {"log.level": level}},
                    ]
                }
            },
            "sort": [{"@timestamp": "desc"}],
            "size": 5,
        }
    )

    print(f"Found {result['hits']['total']['value']} {level} logs from {service}")
    print("\nTop 5 results:")
    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        error_type = src.get("error", {}).get("type", "N/A")
        print(f"  - {src['@timestamp']}: [{error_type}] {src['message'][:60]}...")

    return result["hits"]["total"]["value"] > 0


def test_error_frequency(client, service: str = "payment-service", interval: str = "1m"):
    """Test getting error frequency over time."""
    print(f"\n{'='*60}")
    print(f"TEST: Error frequency for {service} (interval: {interval})")
    print("="*60)

    result = client.search(
        index=LOG_INDEX,
        body={
            "query": {
                "bool": {
                    "must": [
                        {"term": {"service.name": service}},
                        {"term": {"log.level": "error"}},
                    ]
                }
            },
            "size": 0,
            "aggs": {
                "errors_over_time": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "fixed_interval": interval,
                    }
                }
            }
        }
    )

    buckets = result["aggregations"]["errors_over_time"]["buckets"]
    print(f"Found {len(buckets)} time buckets with errors")

    # Show buckets with errors
    error_buckets = [b for b in buckets if b["doc_count"] > 0]
    print(f"\nTime buckets with errors ({len(error_buckets)} buckets):")
    for bucket in error_buckets[:10]:  # Show first 10
        print(f"  - {bucket['key_as_string']}: {bucket['doc_count']} errors")

    return len(error_buckets) > 0


def test_find_trace(client):
    """Test finding logs by trace_id."""
    print(f"\n{'='*60}")
    print("TEST: Find correlated logs by trace_id")
    print("="*60)

    # First, find a trace_id from an error log
    error_result = client.search(
        index=LOG_INDEX,
        body={
            "query": {"term": {"log.level": "error"}},
            "size": 1,
            "_source": ["trace.id", "service.name", "message"],
        }
    )

    if not error_result["hits"]["hits"]:
        print("No error logs found to test trace correlation")
        return False

    trace_id = error_result["hits"]["hits"][0]["_source"].get("trace", {}).get("id")
    if not trace_id:
        print("Error log has no trace_id")
        return False

    print(f"Found trace_id: {trace_id}")

    # Now find all logs with this trace_id
    trace_result = client.search(
        index=LOG_INDEX,
        body={
            "query": {"term": {"trace.id": trace_id}},
            "sort": [{"@timestamp": "asc"}],
            "size": 20,
        }
    )

    print(f"Found {trace_result['hits']['total']['value']} logs for this trace")
    print("\nTrace timeline:")
    for hit in trace_result["hits"]["hits"]:
        src = hit["_source"]
        print(f"  - {src['@timestamp']} [{src['service']['name']}]: {src['message'][:50]}...")

    return trace_result["hits"]["total"]["value"] > 0


def test_error_type_aggregation(client):
    """Test aggregating errors by type."""
    print(f"\n{'='*60}")
    print("TEST: Aggregate errors by type")
    print("="*60)

    result = client.search(
        index=LOG_INDEX,
        body={
            "query": {"term": {"log.level": "error"}},
            "size": 0,
            "aggs": {
                "error_types": {
                    "terms": {
                        "field": "error.type",
                        "size": 10,
                    }
                },
                "by_service": {
                    "terms": {
                        "field": "service.name",
                        "size": 10,
                    }
                }
            }
        }
    )

    print("\nError types:")
    for bucket in result["aggregations"]["error_types"]["buckets"]:
        print(f"  - {bucket['key']}: {bucket['doc_count']} occurrences")

    print("\nErrors by service:")
    for bucket in result["aggregations"]["by_service"]["buckets"]:
        print(f"  - {bucket['key']}: {bucket['doc_count']} errors")

    return len(result["aggregations"]["error_types"]["buckets"]) > 0


def test_time_range_query(client):
    """Test querying logs within a time range."""
    print(f"\n{'='*60}")
    print("TEST: Query logs within time range")
    print("="*60)

    # Get the time range of our data
    range_result = client.search(
        index=LOG_INDEX,
        body={
            "size": 0,
            "aggs": {
                "min_time": {"min": {"field": "@timestamp"}},
                "max_time": {"max": {"field": "@timestamp"}},
            }
        }
    )

    min_time = range_result["aggregations"]["min_time"]["value_as_string"]
    max_time = range_result["aggregations"]["max_time"]["value_as_string"]

    print(f"Data time range: {min_time} to {max_time}")

    # Query errors in a specific time window
    result = client.search(
        index=LOG_INDEX,
        body={
            "query": {
                "bool": {
                    "must": [
                        {"term": {"log.level": "error"}},
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": min_time,
                                    "lte": max_time,
                                }
                            }
                        }
                    ]
                }
            },
            "size": 5,
            "sort": [{"@timestamp": "asc"}],
        }
    )

    print(f"Found {result['hits']['total']['value']} errors in time range")

    return result["hits"]["total"]["value"] > 0


def main():
    print("=" * 60)
    print("LogSleuth Query Tests")
    print("=" * 60)

    try:
        client = get_elasticsearch_client()
        print("Connected to Elasticsearch")
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    # Check if index exists and has data
    if not client.indices.exists(index=LOG_INDEX):
        print(f"\nError: Index '{LOG_INDEX}' does not exist.")
        print("Run 'python scripts/setup_elasticsearch.py' first.")
        sys.exit(1)

    count = client.count(index=LOG_INDEX)
    if count["count"] == 0:
        print(f"\nError: Index '{LOG_INDEX}' is empty.")
        print("Run 'python scripts/setup_elasticsearch.py' first.")
        sys.exit(1)

    print(f"Index '{LOG_INDEX}' has {count['count']} documents")

    # Run tests
    tests = [
        ("Search by keyword", lambda: test_search_logs_by_keyword(client)),
        ("Search by service and level", lambda: test_search_by_service_and_level(client)),
        ("Error frequency", lambda: test_error_frequency(client)),
        ("Find trace", lambda: test_find_trace(client)),
        ("Error type aggregation", lambda: test_error_type_aggregation(client)),
        ("Time range query", lambda: test_time_range_query(client)),
    ]

    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, "PASS" if passed else "FAIL"))
        except Exception as e:
            print(f"\nError in test: {e}")
            results.append((name, "ERROR"))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, status in results:
        emoji = "✓" if status == "PASS" else "✗"
        print(f"  {emoji} {name}: {status}")

    passed = sum(1 for _, s in results if s == "PASS")
    print(f"\n{passed}/{len(results)} tests passed")


if __name__ == "__main__":
    main()
