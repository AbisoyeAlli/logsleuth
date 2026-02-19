"""
Unit tests for the search_logs tool.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.tools.search_logs import search_logs, TOOL_DEFINITION


class TestSearchLogsToolDefinition:
    """Tests for the tool definition structure."""

    def test_tool_has_required_fields(self):
        """Tool definition should have all required fields for Agent Builder."""
        assert "toolId" in TOOL_DEFINITION
        assert "description" in TOOL_DEFINITION
        assert "type" in TOOL_DEFINITION
        assert "parameters" in TOOL_DEFINITION

    def test_tool_id_is_valid(self):
        """Tool ID should be a valid identifier."""
        assert TOOL_DEFINITION["toolId"] == "search_logs"

    def test_tool_type_is_esql(self):
        """Tool should be of type esql."""
        assert TOOL_DEFINITION["type"] == "esql"

    def test_required_parameters(self):
        """Tool should have required parameters correctly marked."""
        params = {p["name"]: p for p in TOOL_DEFINITION["parameters"]}

        assert "search_query" in params
        assert params["search_query"]["required"] is True

        assert "time_range" in params
        assert params["time_range"]["required"] is True

    def test_optional_parameters(self):
        """Tool should have optional parameters correctly marked."""
        params = {p["name"]: p for p in TOOL_DEFINITION["parameters"]}

        assert "service_name" in params
        assert params["service_name"]["required"] is False

        assert "log_level" in params
        assert params["log_level"]["required"] is False


class TestSearchLogsFunction:
    """Tests for the search_logs function implementation."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Elasticsearch client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def sample_es_response(self):
        """Sample Elasticsearch response."""
        return {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00Z",
                            "message": "Connection refused to database",
                            "log": {"level": "error"},
                            "service": {"name": "payment-service"},
                            "trace": {"id": "abc123"},
                            "host": {"name": "host-1"},
                            "error": {
                                "type": "ConnectionException",
                                "message": "Failed to connect"
                            }
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:01:00Z",
                            "message": "Database connection timeout",
                            "log": {"level": "error"},
                            "service": {"name": "payment-service"},
                            "trace": {"id": "def456"},
                            "host": {"name": "host-2"},
                        }
                    }
                ]
            }
        }

    def test_search_logs_returns_formatted_results(self, mock_client, sample_es_response):
        """search_logs should return properly formatted results."""
        mock_client.search.return_value = sample_es_response

        result = search_logs(
            mock_client,
            search_query="connection",
            time_range="1h",
        )

        assert "total" in result
        assert "hits" in result
        assert result["total"] == 2
        assert len(result["hits"]) == 2

    def test_search_logs_includes_trace_id(self, mock_client, sample_es_response):
        """Results should include trace_id for correlation."""
        mock_client.search.return_value = sample_es_response

        result = search_logs(
            mock_client,
            search_query="connection",
            time_range="1h",
        )

        assert result["hits"][0]["trace_id"] == "abc123"

    def test_search_logs_includes_error_details(self, mock_client, sample_es_response):
        """Results should include error details when present."""
        mock_client.search.return_value = sample_es_response

        result = search_logs(
            mock_client,
            search_query="connection",
            time_range="1h",
        )

        assert result["hits"][0]["error_type"] == "ConnectionException"
        assert result["hits"][0]["error_message"] == "Failed to connect"

    def test_search_logs_parses_time_range_hours(self, mock_client, sample_es_response):
        """Time range in hours should be parsed correctly."""
        mock_client.search.return_value = sample_es_response

        search_logs(mock_client, search_query="test", time_range="2h")

        # Verify the query was called
        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args
        query_body = call_args[1]["body"]

        # Check that a time range filter was applied
        must_clauses = query_body["query"]["bool"]["must"]
        time_filter = next(
            (c for c in must_clauses if "range" in c and "@timestamp" in c["range"]),
            None
        )
        assert time_filter is not None

    def test_search_logs_parses_time_range_minutes(self, mock_client, sample_es_response):
        """Time range in minutes should be parsed correctly."""
        mock_client.search.return_value = sample_es_response

        search_logs(mock_client, search_query="test", time_range="30m")

        mock_client.search.assert_called_once()

    def test_search_logs_parses_time_range_days(self, mock_client, sample_es_response):
        """Time range in days should be parsed correctly."""
        mock_client.search.return_value = sample_es_response

        search_logs(mock_client, search_query="test", time_range="1d")

        mock_client.search.assert_called_once()

    def test_search_logs_filters_by_service(self, mock_client, sample_es_response):
        """Service filter should be applied when provided."""
        mock_client.search.return_value = sample_es_response

        search_logs(
            mock_client,
            search_query="test",
            time_range="1h",
            service_name="payment-service"
        )

        call_args = mock_client.search.call_args
        query_body = call_args[1]["body"]
        must_clauses = query_body["query"]["bool"]["must"]

        # Check for service filter
        service_filter = next(
            (c for c in must_clauses if "term" in c and "service.name.keyword" in c["term"]),
            None
        )
        assert service_filter is not None
        assert service_filter["term"]["service.name.keyword"] == "payment-service"

    def test_search_logs_filters_by_level(self, mock_client, sample_es_response):
        """Log level filter should be applied when provided."""
        mock_client.search.return_value = sample_es_response

        search_logs(
            mock_client,
            search_query="test",
            time_range="1h",
            log_level="error"
        )

        call_args = mock_client.search.call_args
        query_body = call_args[1]["body"]
        must_clauses = query_body["query"]["bool"]["must"]

        # Check for level filter
        level_filter = next(
            (c for c in must_clauses if "term" in c and "log.level.keyword" in c["term"]),
            None
        )
        assert level_filter is not None

    def test_search_logs_respects_max_results(self, mock_client, sample_es_response):
        """Max results should be respected and capped at 200."""
        mock_client.search.return_value = sample_es_response

        search_logs(
            mock_client,
            search_query="test",
            time_range="1h",
            max_results=50
        )

        call_args = mock_client.search.call_args
        query_body = call_args[1]["body"]
        assert query_body["size"] == 50

    def test_search_logs_caps_max_results_at_200(self, mock_client, sample_es_response):
        """Max results should be capped at 200."""
        mock_client.search.return_value = sample_es_response

        search_logs(
            mock_client,
            search_query="test",
            time_range="1h",
            max_results=500
        )

        call_args = mock_client.search.call_args
        query_body = call_args[1]["body"]
        assert query_body["size"] == 200

    def test_search_logs_includes_query_info(self, mock_client, sample_es_response):
        """Results should include query info for debugging."""
        mock_client.search.return_value = sample_es_response

        result = search_logs(
            mock_client,
            search_query="connection error",
            time_range="2h",
            service_name="api-gateway",
            log_level="error"
        )

        assert "query_info" in result
        assert result["query_info"]["search_query"] == "connection error"
        assert result["query_info"]["time_range"] == "2h"
        assert result["query_info"]["service_name"] == "api-gateway"
        assert result["query_info"]["log_level"] == "error"

    def test_search_logs_handles_empty_results(self, mock_client):
        """search_logs should handle empty results gracefully."""
        mock_client.search.return_value = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            }
        }

        result = search_logs(
            mock_client,
            search_query="nonexistent",
            time_range="1h",
        )

        assert result["total"] == 0
        assert result["hits"] == []

    def test_search_logs_handles_missing_fields(self, mock_client):
        """search_logs should handle documents with missing optional fields."""
        mock_client.search.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2026-01-20T10:00:00Z",
                            "message": "Simple log message",
                        }
                    }
                ]
            }
        }

        result = search_logs(
            mock_client,
            search_query="simple",
            time_range="1h",
        )

        assert result["total"] == 1
        assert result["hits"][0]["message"] == "Simple log message"
        assert result["hits"][0].get("trace_id") is None
        assert result["hits"][0].get("error_type") is None


class TestSearchLogsIntegration:
    """Integration tests that require a real Elasticsearch connection."""

    @pytest.mark.integration
    def test_search_logs_against_real_es(self):
        """Test against real Elasticsearch if available."""
        pytest.skip("Requires Elasticsearch connection - run with --integration flag")
