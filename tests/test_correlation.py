"""
Unit tests for the find_correlated_logs and find_error_traces tools.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from src.tools.find_correlated_logs import (
    find_correlated_logs,
    find_error_traces,
    TOOL_DEFINITION,
    FIND_ERROR_TRACES_TOOL,
)


class TestCorrelatedLogsToolDefinition:
    """Tests for the find_correlated_logs tool definition."""

    def test_tool_has_required_fields(self):
        """Tool definition should have all required fields."""
        assert "toolId" in TOOL_DEFINITION
        assert "description" in TOOL_DEFINITION
        assert "type" in TOOL_DEFINITION
        assert "parameters" in TOOL_DEFINITION

    def test_tool_id_is_valid(self):
        """Tool ID should be correct."""
        assert TOOL_DEFINITION["toolId"] == "find_correlated_logs"

    def test_trace_id_is_required(self):
        """trace_id should be required."""
        params = {p["name"]: p for p in TOOL_DEFINITION["parameters"]}
        assert "trace_id" in params
        assert params["trace_id"]["required"] is True

    def test_tool_has_correlation_label(self):
        """Tool should have correlation label."""
        assert "correlation" in TOOL_DEFINITION["labels"]


class TestFindErrorTracesToolDefinition:
    """Tests for the find_error_traces tool definition."""

    def test_tool_has_required_fields(self):
        """Tool definition should have all required fields."""
        assert "toolId" in FIND_ERROR_TRACES_TOOL
        assert "description" in FIND_ERROR_TRACES_TOOL
        assert "parameters" in FIND_ERROR_TRACES_TOOL

    def test_tool_id_is_valid(self):
        """Tool ID should be correct."""
        assert FIND_ERROR_TRACES_TOOL["toolId"] == "find_error_traces"

    def test_required_parameters(self):
        """service_name and time_range should be required."""
        params = {p["name"]: p for p in FIND_ERROR_TRACES_TOOL["parameters"]}

        assert "service_name" in params
        assert params["service_name"]["required"] is True

        assert "time_range" in params
        assert params["time_range"]["required"] is True


class TestFindCorrelatedLogsFunction:
    """Tests for the find_correlated_logs function."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Elasticsearch client."""
        return MagicMock()

    @pytest.fixture
    def sample_trace_response(self):
        """Sample response for a distributed trace."""
        return {
            "hits": {
                "total": {"value": 4},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00.000Z",
                            "message": "Received request POST /checkout",
                            "log": {"level": "info"},
                            "service": {"name": "api-gateway"},
                            "span": {"id": "span-1"},
                            "host": {"name": "gateway-1"},
                            "http": {
                                "request": {"method": "POST", "path": "/checkout"},
                            },
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00.100Z",
                            "message": "Processing checkout request",
                            "log": {"level": "info"},
                            "service": {"name": "checkout-service"},
                            "span": {"id": "span-2"},
                            "host": {"name": "checkout-1"},
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00.200Z",
                            "message": "Connection refused to database",
                            "log": {"level": "error"},
                            "service": {"name": "payment-service"},
                            "span": {"id": "span-3"},
                            "host": {"name": "payment-1"},
                            "error": {
                                "type": "ConnectionException",
                                "message": "Failed to connect to DB",
                            }
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00.300Z",
                            "message": "Checkout failed: payment error",
                            "log": {"level": "error"},
                            "service": {"name": "checkout-service"},
                            "span": {"id": "span-4"},
                            "host": {"name": "checkout-1"},
                            "error": {
                                "type": "PaymentException",
                                "message": "Payment processing failed",
                            }
                        }
                    },
                ]
            }
        }

    def test_find_correlated_logs_returns_trace_id(self, mock_client, sample_trace_response):
        """Should return the trace_id in response."""
        mock_client.search.return_value = sample_trace_response

        result = find_correlated_logs(mock_client, trace_id="trace-abc123")

        assert result["trace_id"] == "trace-abc123"

    def test_find_correlated_logs_returns_total_logs(self, mock_client, sample_trace_response):
        """Should return total log count."""
        mock_client.search.return_value = sample_trace_response

        result = find_correlated_logs(mock_client, trace_id="trace-abc123")

        assert result["total_logs"] == 4

    def test_find_correlated_logs_returns_services_involved(self, mock_client, sample_trace_response):
        """Should return list of all services in the trace."""
        mock_client.search.return_value = sample_trace_response

        result = find_correlated_logs(mock_client, trace_id="trace-abc123")

        assert "services_involved" in result
        assert set(result["services_involved"]) == {"api-gateway", "checkout-service", "payment-service"}

    def test_find_correlated_logs_detects_errors(self, mock_client, sample_trace_response):
        """Should detect if trace contains errors."""
        mock_client.search.return_value = sample_trace_response

        result = find_correlated_logs(mock_client, trace_id="trace-abc123")

        assert result["has_errors"] is True

    def test_find_correlated_logs_identifies_root_cause_service(self, mock_client, sample_trace_response):
        """Should identify the root cause service (first error)."""
        mock_client.search.return_value = sample_trace_response

        result = find_correlated_logs(mock_client, trace_id="trace-abc123")

        # payment-service has the first error
        assert result["root_cause_service"] == "payment-service"

    def test_find_correlated_logs_returns_first_error_time(self, mock_client, sample_trace_response):
        """Should return timestamp of first error."""
        mock_client.search.return_value = sample_trace_response

        result = find_correlated_logs(mock_client, trace_id="trace-abc123")

        assert result["first_error_time"] == "2026-01-20T10:00:00.200Z"

    def test_find_correlated_logs_returns_timeline(self, mock_client, sample_trace_response):
        """Should return chronological timeline of events."""
        mock_client.search.return_value = sample_trace_response

        result = find_correlated_logs(mock_client, trace_id="trace-abc123")

        assert "timeline" in result
        assert len(result["timeline"]) == 4

        # Check timeline is chronological
        timestamps = [entry["timestamp"] for entry in result["timeline"]]
        assert timestamps == sorted(timestamps)

    def test_find_correlated_logs_includes_error_details(self, mock_client, sample_trace_response):
        """Timeline entries should include error details when present."""
        mock_client.search.return_value = sample_trace_response

        result = find_correlated_logs(mock_client, trace_id="trace-abc123")

        error_entries = [e for e in result["timeline"] if e.get("error_type")]
        assert len(error_entries) == 2
        assert error_entries[0]["error_type"] == "ConnectionException"

    def test_find_correlated_logs_includes_http_details(self, mock_client, sample_trace_response):
        """Timeline entries should include HTTP details when present."""
        mock_client.search.return_value = sample_trace_response

        result = find_correlated_logs(mock_client, trace_id="trace-abc123")

        # First entry (api-gateway) should have HTTP info
        first_entry = result["timeline"][0]
        assert first_entry.get("http_method") == "POST"
        assert first_entry.get("http_path") == "/checkout"

    def test_find_correlated_logs_handles_no_errors(self, mock_client):
        """Should handle traces with no errors."""
        no_error_response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00Z",
                            "message": "Request received",
                            "log": {"level": "info"},
                            "service": {"name": "api-gateway"},
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:01Z",
                            "message": "Request completed",
                            "log": {"level": "info"},
                            "service": {"name": "api-gateway"},
                        }
                    },
                ]
            }
        }
        mock_client.search.return_value = no_error_response

        result = find_correlated_logs(mock_client, trace_id="trace-success")

        assert result["has_errors"] is False
        assert result["root_cause_service"] is None
        assert result["first_error_time"] is None

    def test_find_correlated_logs_handles_empty_trace(self, mock_client):
        """Should handle non-existent trace gracefully."""
        empty_response = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            }
        }
        mock_client.search.return_value = empty_response

        result = find_correlated_logs(mock_client, trace_id="nonexistent")

        assert result["total_logs"] == 0
        assert result["services_involved"] == []
        assert result["timeline"] == []


class TestFindErrorTracesFunction:
    """Tests for the find_error_traces function."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Elasticsearch client."""
        return MagicMock()

    @pytest.fixture
    def sample_error_traces_response(self):
        """Sample response with error traces."""
        return {
            "hits": {
                "total": {"value": 5},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00Z",
                            "trace": {"id": "trace-1"},
                            "message": "Connection refused to database",
                            "error": {"type": "ConnectionException"},
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:01:00Z",
                            "trace": {"id": "trace-1"},  # Duplicate trace
                            "message": "Retry failed",
                            "error": {"type": "ConnectionException"},
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:02:00Z",
                            "trace": {"id": "trace-2"},
                            "message": "Timeout waiting for response",
                            "error": {"type": "TimeoutException"},
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:03:00Z",
                            "trace": {"id": "trace-3"},
                            "message": "Invalid payment data",
                            "error": {"type": "ValidationException"},
                        }
                    },
                ]
            }
        }

    def test_find_error_traces_returns_service_name(self, mock_client, sample_error_traces_response):
        """Should return the service name queried."""
        mock_client.search.return_value = sample_error_traces_response

        result = find_error_traces(
            mock_client,
            service_name="payment-service",
            time_range="1h"
        )

        assert result["service_name"] == "payment-service"

    def test_find_error_traces_returns_time_range(self, mock_client, sample_error_traces_response):
        """Should return the time range queried."""
        mock_client.search.return_value = sample_error_traces_response

        result = find_error_traces(
            mock_client,
            service_name="payment-service",
            time_range="2h"
        )

        assert result["time_range"] == "2h"

    def test_find_error_traces_deduplicates_traces(self, mock_client, sample_error_traces_response):
        """Should deduplicate traces with same ID."""
        mock_client.search.return_value = sample_error_traces_response

        result = find_error_traces(
            mock_client,
            service_name="payment-service",
            time_range="1h"
        )

        # Should have 3 unique traces, not 4
        assert result["traces_found"] == 3
        trace_ids = [t["trace_id"] for t in result["traces"]]
        assert len(set(trace_ids)) == len(trace_ids)

    def test_find_error_traces_includes_error_type(self, mock_client, sample_error_traces_response):
        """Traces should include error type."""
        mock_client.search.return_value = sample_error_traces_response

        result = find_error_traces(
            mock_client,
            service_name="payment-service",
            time_range="1h"
        )

        first_trace = result["traces"][0]
        assert "error_type" in first_trace
        assert first_trace["error_type"] == "ConnectionException"

    def test_find_error_traces_includes_timestamp(self, mock_client, sample_error_traces_response):
        """Traces should include timestamp."""
        mock_client.search.return_value = sample_error_traces_response

        result = find_error_traces(
            mock_client,
            service_name="payment-service",
            time_range="1h"
        )

        first_trace = result["traces"][0]
        assert "timestamp" in first_trace

    def test_find_error_traces_truncates_message(self, mock_client):
        """Long messages should be truncated to 100 chars."""
        long_message = "A" * 200
        response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00Z",
                            "trace": {"id": "trace-1"},
                            "message": long_message,
                            "error": {"type": "TestException"},
                        }
                    }
                ]
            }
        }
        mock_client.search.return_value = response

        result = find_error_traces(
            mock_client,
            service_name="test-service",
            time_range="1h"
        )

        assert len(result["traces"][0]["message"]) == 100

    def test_find_error_traces_respects_max_traces(self, mock_client):
        """Should respect max_traces limit."""
        many_traces = {
            "hits": {
                "total": {"value": 20},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": f"2026-01-20T10:0{i}:00Z",
                            "trace": {"id": f"trace-{i}"},
                            "message": f"Error {i}",
                            "error": {"type": "TestException"},
                        }
                    }
                    for i in range(20)
                ]
            }
        }
        mock_client.search.return_value = many_traces

        result = find_error_traces(
            mock_client,
            service_name="test-service",
            time_range="1h",
            max_traces=5
        )

        assert result["traces_found"] == 5
        assert len(result["traces"]) == 5

    def test_find_error_traces_handles_empty_results(self, mock_client):
        """Should handle no error traces found."""
        empty_response = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            }
        }
        mock_client.search.return_value = empty_response

        result = find_error_traces(
            mock_client,
            service_name="healthy-service",
            time_range="1h"
        )

        assert result["traces_found"] == 0
        assert result["traces"] == []

    def test_find_error_traces_handles_missing_trace_id(self, mock_client):
        """Should skip logs without trace_id."""
        response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00Z",
                            # No trace.id
                            "message": "Error without trace",
                            "error": {"type": "TestException"},
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:01:00Z",
                            "trace": {"id": "trace-1"},
                            "message": "Error with trace",
                            "error": {"type": "TestException"},
                        }
                    }
                ]
            }
        }
        mock_client.search.return_value = response

        result = find_error_traces(
            mock_client,
            service_name="test-service",
            time_range="1h"
        )

        # Only one trace with ID
        assert result["traces_found"] == 1


class TestTraceCorrelationWorkflow:
    """Tests for the complete trace correlation workflow."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    def test_workflow_find_traces_then_correlate(self, mock_client):
        """Test the typical workflow: find error traces, then correlate."""
        # Step 1: Find error traces
        error_traces_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00Z",
                            "trace": {"id": "trace-abc"},
                            "message": "Database error",
                            "error": {"type": "DBException"},
                        }
                    }
                ]
            }
        }

        # Step 2: Correlate the found trace
        correlated_response = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00Z",
                            "message": "Request start",
                            "log": {"level": "info"},
                            "service": {"name": "api-gateway"},
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:01Z",
                            "message": "Database error",
                            "log": {"level": "error"},
                            "service": {"name": "db-service"},
                            "error": {"type": "DBException", "message": "Connection failed"},
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:02Z",
                            "message": "Request failed",
                            "log": {"level": "error"},
                            "service": {"name": "api-gateway"},
                            "error": {"type": "UpstreamException", "message": "DB unavailable"},
                        }
                    },
                ]
            }
        }

        mock_client.search.return_value = error_traces_response
        traces = find_error_traces(mock_client, "db-service", "1h")

        assert traces["traces_found"] == 1
        trace_id = traces["traces"][0]["trace_id"]
        assert trace_id == "trace-abc"

        mock_client.search.return_value = correlated_response
        correlation = find_correlated_logs(mock_client, trace_id)

        assert correlation["services_involved"] == ["api-gateway", "db-service"]
        assert correlation["root_cause_service"] == "db-service"
