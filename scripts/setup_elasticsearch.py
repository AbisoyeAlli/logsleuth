#!/usr/bin/env python3
"""
Setup script for LogSleuth Elasticsearch environment.

This script:
1. Verifies Elasticsearch connection
2. Creates required indices
3. Generates and ingests synthetic log data

Usage:
    python scripts/setup_elasticsearch.py [--force] [--logs-only]

Options:
    --force      Delete existing indices and recreate them
    --logs-only  Only generate and ingest logs (skip index creation)
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, BulkIndexError

from src.utils.elasticsearch_client import (
    get_elasticsearch_client,
    verify_connection,
    LOG_INDEX,
    INVESTIGATION_INDEX,
)
from src.data.index_templates import create_indices, delete_indices
from src.data.log_generator import generate_full_dataset


def ingest_logs(client: Elasticsearch, logs: list, batch_size: int = 500) -> dict:
    """
    Ingest logs into Elasticsearch using bulk API.

    Args:
        client: Elasticsearch client
        logs: List of log documents
        batch_size: Number of documents per bulk request

    Returns:
        dict: Ingestion statistics
    """
    stats = {
        "total": len(logs),
        "success": 0,
        "failed": 0,
    }

    def generate_actions():
        for log in logs:
            yield {
                "_index": LOG_INDEX,
                "_source": log,
            }

    try:
        success, failed = bulk(
            client,
            generate_actions(),
            chunk_size=batch_size,
            raise_on_error=False,
            raise_on_exception=False,
        )
        stats["success"] = success
        stats["failed"] = len(logs) - success if isinstance(failed, list) else 0

    except BulkIndexError as e:
        print(f"Bulk indexing error: {e}")
        stats["failed"] = len(e.errors)
        stats["success"] = stats["total"] - stats["failed"]

    return stats


def main():
    parser = argparse.ArgumentParser(description="Setup LogSleuth Elasticsearch environment")
    parser.add_argument("--force", action="store_true", help="Delete and recreate indices")
    parser.add_argument("--logs-only", action="store_true", help="Only ingest logs")
    parser.add_argument("--no-incidents", action="store_true", help="Generate logs without incidents")
    args = parser.parse_args()

    print("=" * 60)
    print("LogSleuth Elasticsearch Setup")
    print("=" * 60)

    # Step 1: Connect to Elasticsearch
    print("\n[1/4] Connecting to Elasticsearch...")
    try:
        client = get_elasticsearch_client()
        verify_connection(client)
    except Exception as e:
        print(f"\nError: {e}")
        print("\nPlease check your .env file and ensure Elasticsearch credentials are correct.")
        print("Copy .env.example to .env and fill in your Elastic Cloud credentials.")
        sys.exit(1)

    # Step 2: Create indices (unless --logs-only)
    if not args.logs_only:
        print("\n[2/4] Creating indices...")
        if args.force:
            print("Force flag set - deleting existing indices...")
            delete_indices(client)
        create_indices(client, force=args.force)
    else:
        print("\n[2/4] Skipping index creation (--logs-only)")

    # Step 3: Generate synthetic logs
    print("\n[3/4] Generating synthetic log data...")
    include_incidents = not args.no_incidents
    logs = generate_full_dataset(include_incidents=include_incidents)
    print(f"Generated {len(logs)} log entries")

    # Step 4: Ingest logs
    print("\n[4/4] Ingesting logs into Elasticsearch...")
    stats = ingest_logs(client, logs)

    print(f"\nIngestion complete:")
    print(f"  - Total documents: {stats['total']}")
    print(f"  - Successfully indexed: {stats['success']}")
    print(f"  - Failed: {stats['failed']}")

    # Refresh the index to make documents searchable immediately
    client.indices.refresh(index=LOG_INDEX)

    # Verify data
    print("\n[Verification] Checking indexed data...")
    count = client.count(index=LOG_INDEX)
    print(f"Total documents in {LOG_INDEX}: {count['count']}")

    # Show some stats (use keyword subfields for aggregations)
    print("\n[Stats] Log distribution by service:")
    try:
        agg_result = client.search(
            index=LOG_INDEX,
            body={
                "size": 0,
                "aggs": {
                    "services": {
                        "terms": {"field": "service.name.keyword", "size": 10}
                    }
                }
            }
        )
        for bucket in agg_result["aggregations"]["services"]["buckets"]:
            print(f"  - {bucket['key']}: {bucket['doc_count']} logs")
    except Exception as e:
        print(f"  Could not aggregate by service: {e}")

    print("\n[Stats] Log distribution by level:")
    try:
        agg_result = client.search(
            index=LOG_INDEX,
            body={
                "size": 0,
                "aggs": {
                    "levels": {
                        "terms": {"field": "log.level.keyword", "size": 10}
                    }
                }
            }
        )
        for bucket in agg_result["aggregations"]["levels"]["buckets"]:
            print(f"  - {bucket['key']}: {bucket['doc_count']} logs")
    except Exception as e:
        print(f"  Could not aggregate by level: {e}")

    # Create sample investigations for demo
    print("\n[5/5] Creating sample investigations...")
    try:
        from src.tools.save_investigation import create_sample_investigations
        investigation_ids = create_sample_investigations(client)
        print(f"Created {len(investigation_ids)} sample investigations:")
        for inv_id in investigation_ids:
            print(f"  - {inv_id}")
    except Exception as e:
        print(f"  Warning: Could not create sample investigations: {e}")

    print("\n" + "=" * 60)
    print("Setup complete! LogSleuth is ready to use.")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Test queries: python scripts/test_queries.py")
    print("  2. Run CLI: python -m src.cli investigate 'timeout errors'")
    print("  3. Deploy to Agent Builder: python scripts/deploy_agent.py --dry-run")


if __name__ == "__main__":
    main()
