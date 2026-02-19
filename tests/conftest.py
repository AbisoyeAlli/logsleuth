"""
Pytest configuration and shared fixtures for LogSleuth tests.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (requires ES)"
    )


@pytest.fixture
def mock_es_client():
    """
    Create a mock Elasticsearch client.

    This fixture provides a MagicMock that simulates the Elasticsearch
    client interface without requiring a real connection.
    """
    client = MagicMock()
    client.indices.exists.return_value = True
    return client


@pytest.fixture
def sample_log_hit():
    """Sample Elasticsearch log document."""
    return {
        "_source": {
            "@timestamp": "2026-01-20T10:00:00Z",
            "message": "Connection refused to database primary",
            "log": {"level": "error"},
            "service": {"name": "payment-service", "version": "2.1.0"},
            "trace": {"id": "abc123-def456"},
            "span": {"id": "span-001"},
            "host": {"name": "payment-host-1"},
            "error": {
                "type": "ConnectionException",
                "message": "Failed to connect to database",
                "stack_trace": "at com.example.db.connect()",
            },
            "http": {
                "request": {"method": "POST", "path": "/api/payment"},
                "response": {"status_code": 500},
            },
            "event": {
                "outcome": "failure",
                "duration": 5000000,  # 5ms in nanoseconds
            }
        }
    }


@pytest.fixture
def sample_error_logs():
    """Sample list of error log documents."""
    return {
        "hits": {
            "total": {"value": 3},
            "hits": [
                {
                    "_source": {
                        "@timestamp": "2026-01-20T10:00:00Z",
                        "message": "Connection refused to database",
                        "log": {"level": "error"},
                        "service": {"name": "payment-service"},
                        "trace": {"id": "trace-001"},
                        "error": {"type": "ConnectionException"},
                    }
                },
                {
                    "_source": {
                        "@timestamp": "2026-01-20T10:00:05Z",
                        "message": "Timeout waiting for response",
                        "log": {"level": "error"},
                        "service": {"name": "payment-service"},
                        "trace": {"id": "trace-002"},
                        "error": {"type": "TimeoutException"},
                    }
                },
                {
                    "_source": {
                        "@timestamp": "2026-01-20T10:00:10Z",
                        "message": "Upstream service unavailable",
                        "log": {"level": "error"},
                        "service": {"name": "checkout-service"},
                        "trace": {"id": "trace-003"},
                        "error": {"type": "ServiceUnavailableException"},
                    }
                },
            ]
        }
    }


@pytest.fixture
def sample_investigation():
    """Sample investigation document."""
    return {
        "@timestamp": "2026-01-20T11:00:00Z",
        "investigation": {
            "id": "INV-20260120-ABC123",
            "status": "completed",
        },
        "incident": {
            "input": "Payment service throwing connection errors",
            "time_range": {
                "start": "2026-01-20T10:00:00Z",
                "end": "2026-01-20T10:30:00Z",
            },
            "services_involved": ["payment-service", "checkout-service"],
        },
        "findings": {
            "root_cause": "Database primary failover caused connection pool exhaustion",
            "root_cause_service": "payment-service",
            "affected_services": ["payment-service", "checkout-service", "api-gateway"],
            "error_types": ["ConnectionException", "TimeoutException"],
            "error_count": 156,
            "timeline": [
                {"timestamp": "2026-01-20T10:12:00Z", "event": "DB failover", "service": "database"},
                {"timestamp": "2026-01-20T10:12:15Z", "event": "Errors begin", "service": "payment-service"},
            ],
        },
        "remediation": {
            "suggestions": "Implement connection pool auto-recovery",
            "resolution_applied": "Restarted payment-service pods",
        }
    }


@pytest.fixture
def time_ranges():
    """Common time ranges for testing."""
    return {
        "last_hour": "1h",
        "last_30_min": "30m",
        "last_day": "1d",
        "last_2_hours": "2h",
    }


@pytest.fixture
def known_services():
    """List of known service names."""
    return [
        "api-gateway",
        "user-service",
        "payment-service",
        "checkout-service",
        "inventory-service",
    ]


@pytest.fixture
def error_types():
    """Common error types."""
    return [
        "ConnectionException",
        "TimeoutException",
        "ValidationException",
        "ServiceUnavailableException",
        "ConnectionPoolExhaustedException",
    ]


class MockElasticsearchResponse:
    """Helper class to build mock Elasticsearch responses."""

    @staticmethod
    def search_result(hits: list, total: int = None):
        """Build a search result response."""
        return {
            "hits": {
                "total": {"value": total if total is not None else len(hits)},
                "hits": hits
            }
        }

    @staticmethod
    def aggregation_result(aggregations: dict):
        """Build an aggregation result response."""
        return {"aggregations": aggregations}

    @staticmethod
    def index_result(success: bool = True):
        """Build an index result response."""
        return {
            "result": "created" if success else "error",
            "_id": "doc-001",
        }


@pytest.fixture
def mock_response_builder():
    """Fixture providing the MockElasticsearchResponse helper."""
    return MockElasticsearchResponse


# Async fixtures for orchestrator tests
@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
