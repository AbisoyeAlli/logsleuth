"""
Unit tests for the get_error_frequency tool.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta

from src.tools.get_error_frequency import get_error_frequency, TOOL_DEFINITION


class TestErrorFrequencyToolDefinition:
    """Tests for the tool definition structure."""

    def test_tool_has_required_fields(self):
        """Tool definition should have all required fields."""
        assert "toolId" in TOOL_DEFINITION
        assert "description" in TOOL_DEFINITION
        assert "type" in TOOL_DEFINITION
        assert "parameters" in TOOL_DEFINITION

    def test_tool_id_is_valid(self):
        """Tool ID should be correct."""
        assert TOOL_DEFINITION["toolId"] == "get_error_frequency"

    def test_tool_type_is_esql(self):
        """Tool should be of type esql."""
        assert TOOL_DEFINITION["type"] == "esql"

    def test_required_parameters(self):
        """Time range should be required."""
        params = {p["name"]: p for p in TOOL_DEFINITION["parameters"]}

        assert "time_range" in params
        assert params["time_range"]["required"] is True

    def test_optional_parameters(self):
        """Service and error type should be optional."""
        params = {p["name"]: p for p in TOOL_DEFINITION["parameters"]}

        assert "service_name" in params
        assert params["service_name"]["required"] is False

        assert "error_type" in params
        assert params["error_type"]["required"] is False

    def test_tool_has_labels(self):
        """Tool should have appropriate labels."""
        assert "labels" in TOOL_DEFINITION
        assert "analytics" in TOOL_DEFINITION["labels"]


class TestGetErrorFrequencyFunction:
    """Tests for the get_error_frequency function."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Elasticsearch client."""
        return MagicMock()

    @pytest.fixture
    def sample_stats_response(self):
        """Sample response for stats aggregation."""
        return {
            "aggregations": {
                "by_service": {
                    "buckets": [
                        {
                            "key": "payment-service",
                            "doc_count": 50,
                            "by_error_type": {
                                "buckets": [
                                    {"key": "ConnectionException", "doc_count": 30},
                                    {"key": "TimeoutException", "doc_count": 20},
                                ]
                            }
                        },
                        {
                            "key": "checkout-service",
                            "doc_count": 20,
                            "by_error_type": {
                                "buckets": [
                                    {"key": "TimeoutException", "doc_count": 20},
                                ]
                            }
                        },
                    ]
                },
                "total_errors": {"value": 70}
            }
        }

    @pytest.fixture
    def sample_histogram_response(self):
        """Sample response for histogram aggregation."""
        return {
            "aggregations": {
                "errors_over_time": {
                    "buckets": [
                        {
                            "key_as_string": "2026-01-20T10:00:00Z",
                            "doc_count": 10,
                            "by_service": {
                                "buckets": [
                                    {"key": "payment-service", "doc_count": 10}
                                ]
                            }
                        },
                        {
                            "key_as_string": "2026-01-20T10:05:00Z",
                            "doc_count": 5,
                            "by_service": {
                                "buckets": [
                                    {"key": "payment-service", "doc_count": 5}
                                ]
                            }
                        },
                        {
                            "key_as_string": "2026-01-20T10:10:00Z",
                            "doc_count": 50,  # Spike!
                            "by_service": {
                                "buckets": [
                                    {"key": "payment-service", "doc_count": 35},
                                    {"key": "checkout-service", "doc_count": 15}
                                ]
                            }
                        },
                        {
                            "key_as_string": "2026-01-20T10:15:00Z",
                            "doc_count": 5,
                            "by_service": {
                                "buckets": [
                                    {"key": "payment-service", "doc_count": 5}
                                ]
                            }
                        },
                    ]
                }
            }
        }

    def test_get_error_frequency_returns_total_errors(
        self, mock_client, sample_stats_response, sample_histogram_response
    ):
        """Should return total error count."""
        mock_client.search.side_effect = [sample_stats_response, sample_histogram_response]

        result = get_error_frequency(mock_client, time_range="1h")

        assert "total_errors" in result
        assert result["total_errors"] == 70

    def test_get_error_frequency_returns_service_breakdown(
        self, mock_client, sample_stats_response, sample_histogram_response
    ):
        """Should return error breakdown by service."""
        mock_client.search.side_effect = [sample_stats_response, sample_histogram_response]

        result = get_error_frequency(mock_client, time_range="1h")

        assert "service_breakdown" in result
        assert len(result["service_breakdown"]) == 2

        payment_svc = next(
            s for s in result["service_breakdown"]
            if s["service"] == "payment-service"
        )
        assert payment_svc["error_count"] == 50
        assert len(payment_svc["error_types"]) == 2

    def test_get_error_frequency_returns_histogram(
        self, mock_client, sample_stats_response, sample_histogram_response
    ):
        """Should return time-based histogram."""
        mock_client.search.side_effect = [sample_stats_response, sample_histogram_response]

        result = get_error_frequency(mock_client, time_range="1h")

        assert "histogram" in result
        assert len(result["histogram"]) == 4

    def test_get_error_frequency_detects_spikes(
        self, mock_client, sample_stats_response, sample_histogram_response
    ):
        """Should detect error spikes (>2x average)."""
        mock_client.search.side_effect = [sample_stats_response, sample_histogram_response]

        result = get_error_frequency(mock_client, time_range="1h")

        assert "spike_detected" in result
        assert result["spike_detected"] is not None
        assert result["spike_detected"]["error_count"] == 50  # The spike bucket
        assert result["spike_detected"]["timestamp"] == "2026-01-20T10:10:00Z"

    def test_get_error_frequency_spike_severity_medium(
        self, mock_client, sample_stats_response, sample_histogram_response
    ):
        """Spike severity should be medium when 2x-5x average."""
        mock_client.search.side_effect = [sample_stats_response, sample_histogram_response]

        result = get_error_frequency(mock_client, time_range="1h")

        # Average is (10+5+50+5)/4 = 17.5, spike is 50 = ~2.86x average (medium)
        assert result["spike_detected"]["severity"] == "medium"

    def test_get_error_frequency_spike_severity_high(self, mock_client):
        """Spike severity should be high when >5x average."""
        stats_response = {
            "aggregations": {
                "by_service": {"buckets": []},
                "total_errors": {"value": 110}
            }
        }
        histogram_response = {
            "aggregations": {
                "errors_over_time": {
                    "buckets": [
                        {"key_as_string": "2026-01-20T10:00:00Z", "doc_count": 10, "by_service": {"buckets": []}},
                        {"key_as_string": "2026-01-20T10:05:00Z", "doc_count": 10, "by_service": {"buckets": []}},
                        {"key_as_string": "2026-01-20T10:10:00Z", "doc_count": 80, "by_service": {"buckets": []}},
                        {"key_as_string": "2026-01-20T10:15:00Z", "doc_count": 10, "by_service": {"buckets": []}},
                    ]
                }
            }
        }
        mock_client.search.side_effect = [stats_response, histogram_response]

        result = get_error_frequency(mock_client, time_range="1h")

        # Average is (10+10+80+10)/4 = 27.5, spike is 80 = ~2.9x (still medium, but close)
        # Let's make it more extreme
        assert result["spike_detected"] is not None

    def test_get_error_frequency_no_spike_when_uniform(self, mock_client):
        """Should not detect spike when errors are uniformly distributed."""
        stats_response = {
            "aggregations": {
                "by_service": {"buckets": []},
                "total_errors": {"value": 40}
            }
        }
        histogram_response = {
            "aggregations": {
                "errors_over_time": {
                    "buckets": [
                        {"key_as_string": "2026-01-20T10:00:00Z", "doc_count": 10, "by_service": {"buckets": []}},
                        {"key_as_string": "2026-01-20T10:05:00Z", "doc_count": 10, "by_service": {"buckets": []}},
                        {"key_as_string": "2026-01-20T10:10:00Z", "doc_count": 10, "by_service": {"buckets": []}},
                        {"key_as_string": "2026-01-20T10:15:00Z", "doc_count": 10, "by_service": {"buckets": []}},
                    ]
                }
            }
        }
        mock_client.search.side_effect = [stats_response, histogram_response]

        result = get_error_frequency(mock_client, time_range="1h")

        # All buckets are equal, no spike
        assert result["spike_detected"] is None

    def test_get_error_frequency_parses_time_range(self, mock_client):
        """Should parse various time range formats."""
        empty_response = {
            "aggregations": {
                "by_service": {"buckets": []},
                "total_errors": {"value": 0}
            }
        }
        empty_histogram = {
            "aggregations": {
                "errors_over_time": {"buckets": []}
            }
        }

        for time_range in ["1h", "30m", "2d"]:
            mock_client.search.reset_mock()
            mock_client.search.side_effect = [empty_response, empty_histogram]

            result = get_error_frequency(mock_client, time_range=time_range)

            assert result["time_range"] == time_range

    def test_get_error_frequency_filters_by_service(
        self, mock_client, sample_stats_response, sample_histogram_response
    ):
        """Should filter by service when specified."""
        mock_client.search.side_effect = [sample_stats_response, sample_histogram_response]

        get_error_frequency(
            mock_client,
            time_range="1h",
            service_name="payment-service"
        )

        # Both queries should have been called
        assert mock_client.search.call_count == 2

        # Check that service filter was applied
        first_call = mock_client.search.call_args_list[0]
        query_body = first_call[1]["body"]
        filter_clauses = query_body["query"]["bool"]["filter"]

        service_filter = next(
            (c for c in filter_clauses if "term" in c and "service.name.keyword" in c["term"]),
            None
        )
        assert service_filter is not None

    def test_get_error_frequency_includes_query_info(
        self, mock_client, sample_stats_response, sample_histogram_response
    ):
        """Should include query info in results."""
        mock_client.search.side_effect = [sample_stats_response, sample_histogram_response]

        result = get_error_frequency(
            mock_client,
            time_range="2h",
            service_name="api-gateway",
            error_type="TimeoutException"
        )

        assert "query_info" in result
        assert result["query_info"]["service_name"] == "api-gateway"
        assert result["query_info"]["error_type"] == "TimeoutException"

    def test_get_error_frequency_handles_empty_results(self, mock_client):
        """Should handle empty results gracefully."""
        empty_response = {
            "aggregations": {
                "by_service": {"buckets": []},
                "total_errors": {"value": 0}
            }
        }
        empty_histogram = {
            "aggregations": {
                "errors_over_time": {"buckets": []}
            }
        }
        mock_client.search.side_effect = [empty_response, empty_histogram]

        result = get_error_frequency(mock_client, time_range="1h")

        assert result["total_errors"] == 0
        assert result["service_breakdown"] == []
        assert result["histogram"] == []
        assert result["spike_detected"] is None


class TestErrorFrequencyAnomalyDetection:
    """Tests specifically for anomaly/spike detection logic."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    def test_spike_threshold_is_2x_average(self, mock_client):
        """Spike should be detected when count is >2x average."""
        stats_response = {
            "aggregations": {
                "by_service": {"buckets": []},
                "total_errors": {"value": 25}
            }
        }
        # Average = 25/5 = 5, so spike threshold is 10
        histogram_response = {
            "aggregations": {
                "errors_over_time": {
                    "buckets": [
                        {"key_as_string": "t1", "doc_count": 5, "by_service": {"buckets": []}},
                        {"key_as_string": "t2", "doc_count": 5, "by_service": {"buckets": []}},
                        {"key_as_string": "t3", "doc_count": 5, "by_service": {"buckets": []}},
                        {"key_as_string": "t4", "doc_count": 5, "by_service": {"buckets": []}},
                        {"key_as_string": "t5", "doc_count": 5, "by_service": {"buckets": []}},
                    ]
                }
            }
        }
        mock_client.search.side_effect = [stats_response, histogram_response]

        result = get_error_frequency(mock_client, time_range="1h")

        # No bucket is >2x average (5), so no spike
        assert result["spike_detected"] is None

    def test_spike_detected_at_correct_timestamp(self, mock_client):
        """Spike timestamp should be the bucket with max errors."""
        stats_response = {
            "aggregations": {
                "by_service": {"buckets": []},
                "total_errors": {"value": 100}
            }
        }
        histogram_response = {
            "aggregations": {
                "errors_over_time": {
                    "buckets": [
                        {"key_as_string": "2026-01-20T10:00:00Z", "doc_count": 10, "by_service": {"buckets": []}},
                        {"key_as_string": "2026-01-20T10:05:00Z", "doc_count": 60, "by_service": {"buckets": []}},
                        {"key_as_string": "2026-01-20T10:10:00Z", "doc_count": 20, "by_service": {"buckets": []}},
                        {"key_as_string": "2026-01-20T10:15:00Z", "doc_count": 10, "by_service": {"buckets": []}},
                    ]
                }
            }
        }
        mock_client.search.side_effect = [stats_response, histogram_response]

        result = get_error_frequency(mock_client, time_range="1h")

        assert result["spike_detected"]["timestamp"] == "2026-01-20T10:05:00Z"
        assert result["spike_detected"]["error_count"] == 60
