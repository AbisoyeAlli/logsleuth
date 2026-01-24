"""Elasticsearch index templates for LogSleuth.

This module defines ECS-compatible index mappings for:
1. Application logs (logs-logsleuth)
2. Investigation history (investigations-logsleuth)
"""

from elasticsearch import Elasticsearch
from src.utils.elasticsearch_client import LOG_INDEX, INVESTIGATION_INDEX


# ECS-compatible log index mapping
LOG_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            # Timestamp
            "@timestamp": {"type": "date"},

            # Log level and message
            "log": {
                "properties": {
                    "level": {"type": "keyword"},
                    "logger": {"type": "keyword"},
                }
            },
            "message": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},

            # Service information
            "service": {
                "properties": {
                    "name": {"type": "keyword"},
                    "version": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "node": {
                        "properties": {
                            "name": {"type": "keyword"},
                        }
                    },
                }
            },

            # Trace and span IDs for distributed tracing
            "trace": {
                "properties": {
                    "id": {"type": "keyword"},
                }
            },
            "span": {
                "properties": {
                    "id": {"type": "keyword"},
                }
            },
            "transaction": {
                "properties": {
                    "id": {"type": "keyword"},
                }
            },

            # Error information
            "error": {
                "properties": {
                    "type": {"type": "keyword"},
                    "message": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "stack_trace": {"type": "text"},
                    "code": {"type": "keyword"},
                }
            },

            # Host information
            "host": {
                "properties": {
                    "name": {"type": "keyword"},
                    "ip": {"type": "ip"},
                    "hostname": {"type": "keyword"},
                }
            },

            # Cloud information
            "cloud": {
                "properties": {
                    "provider": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "availability_zone": {"type": "keyword"},
                }
            },

            # HTTP request information (for API services)
            "http": {
                "properties": {
                    "request": {
                        "properties": {
                            "method": {"type": "keyword"},
                            "path": {"type": "keyword"},
                        }
                    },
                    "response": {
                        "properties": {
                            "status_code": {"type": "integer"},
                        }
                    },
                }
            },

            # Event information
            "event": {
                "properties": {
                    "duration": {"type": "long"},  # in nanoseconds
                    "outcome": {"type": "keyword"},  # success, failure, unknown
                    "category": {"type": "keyword"},
                    "action": {"type": "keyword"},
                }
            },

            # Custom labels
            "labels": {
                "type": "object",
                "dynamic": True,
            },

            # User information
            "user": {
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                }
            },
        }
    },
    "settings": {
        "index": {
            "refresh_interval": "5s",
        }
    }
}


# Investigation history index mapping
INVESTIGATION_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "@timestamp": {"type": "date"},

            "investigation": {
                "properties": {
                    "id": {"type": "keyword"},
                    "status": {"type": "keyword"},  # in_progress, completed, failed
                }
            },

            "incident": {
                "properties": {
                    "input": {"type": "text"},
                    "time_range": {
                        "properties": {
                            "start": {"type": "date"},
                            "end": {"type": "date"},
                        }
                    },
                    "services_involved": {"type": "keyword"},
                }
            },

            "findings": {
                "properties": {
                    "root_cause": {"type": "text"},
                    "root_cause_service": {"type": "keyword"},
                    "affected_services": {"type": "keyword"},
                    "error_types": {"type": "keyword"},
                    "error_count": {"type": "integer"},
                    "blast_radius": {"type": "text"},
                    "timeline": {
                        "type": "nested",
                        "properties": {
                            "timestamp": {"type": "date"},
                            "event": {"type": "text"},
                            "service": {"type": "keyword"},
                        }
                    },
                    "evidence_log_ids": {"type": "keyword"},
                }
            },

            "remediation": {
                "properties": {
                    "suggestions": {"type": "text"},
                    "similar_incidents": {"type": "keyword"},
                    "resolution_applied": {"type": "text"},
                }
            },
        }
    },
    "settings": {
        "index": {
            "refresh_interval": "5s",
        }
    }
}


def create_indices(client: Elasticsearch, force: bool = False) -> dict:
    """
    Create the required indices in Elasticsearch.

    Args:
        client: Elasticsearch client
        force: If True, delete existing indices first

    Returns:
        dict: Status of index creation
    """
    results = {}

    indices_to_create = [
        (LOG_INDEX, LOG_INDEX_MAPPING),
        (INVESTIGATION_INDEX, INVESTIGATION_INDEX_MAPPING),
    ]

    for index_name, mapping in indices_to_create:
        try:
            # Check if index exists
            if client.indices.exists(index=index_name):
                if force:
                    client.indices.delete(index=index_name)
                    print(f"Deleted existing index: {index_name}")
                else:
                    results[index_name] = "already_exists"
                    print(f"Index already exists: {index_name}")
                    continue

            # Create the index
            client.indices.create(index=index_name, body=mapping)
            results[index_name] = "created"
            print(f"Created index: {index_name}")

        except Exception as e:
            results[index_name] = f"error: {str(e)}"
            print(f"Error creating index {index_name}: {e}")

    return results


def delete_indices(client: Elasticsearch) -> dict:
    """
    Delete the LogSleuth indices.

    Args:
        client: Elasticsearch client

    Returns:
        dict: Status of index deletion
    """
    results = {}

    for index_name in [LOG_INDEX, INVESTIGATION_INDEX]:
        try:
            if client.indices.exists(index=index_name):
                client.indices.delete(index=index_name)
                results[index_name] = "deleted"
                print(f"Deleted index: {index_name}")
            else:
                results[index_name] = "not_found"
                print(f"Index not found: {index_name}")
        except Exception as e:
            results[index_name] = f"error: {str(e)}"
            print(f"Error deleting index {index_name}: {e}")

    return results
