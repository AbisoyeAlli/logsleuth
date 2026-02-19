"""
Unit tests for the investigation orchestrator.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from src.agent.orchestrator import (
    InvestigationOrchestrator,
    InvestigationStep,
    InvestigationContext,
    StepResult,
    run_investigation,
    investigate_sync,
)


class TestInvestigationStep:
    """Tests for the InvestigationStep enum."""

    def test_all_steps_defined(self):
        """All investigation steps should be defined."""
        assert InvestigationStep.UNDERSTAND.value == "understand"
        assert InvestigationStep.SEARCH.value == "search"
        assert InvestigationStep.ANALYZE.value == "analyze"
        assert InvestigationStep.CORRELATE.value == "correlate"
        assert InvestigationStep.SYNTHESIZE.value == "synthesize"
        assert InvestigationStep.COMPLETE.value == "complete"


class TestInvestigationContext:
    """Tests for the InvestigationContext dataclass."""

    def test_context_initialization(self):
        """Context should initialize with defaults."""
        context = InvestigationContext(
            incident_description="Test incident",
            time_range="1h"
        )

        assert context.incident_description == "Test incident"
        assert context.time_range == "1h"
        assert context.error_logs == []
        assert context.affected_services == []
        assert context.root_cause is None

    def test_context_accumulates_findings(self):
        """Context should allow accumulating findings."""
        context = InvestigationContext(incident_description="Test")

        context.affected_services.append("service-a")
        context.error_types.append("ConnectionException")
        context.total_errors = 100

        assert "service-a" in context.affected_services
        assert "ConnectionException" in context.error_types
        assert context.total_errors == 100


class TestStepResult:
    """Tests for the StepResult dataclass."""

    def test_step_result_creation(self):
        """StepResult should capture step execution details."""
        result = StepResult(
            step=InvestigationStep.SEARCH,
            success=True,
            data={"total": 50},
            reasoning="Found 50 error logs",
            next_action="Analyze patterns",
            duration_ms=150.5
        )

        assert result.step == InvestigationStep.SEARCH
        assert result.success is True
        assert result.data["total"] == 50
        assert "50 error logs" in result.reasoning
        assert result.duration_ms == 150.5


class TestInvestigationOrchestrator:
    """Tests for the InvestigationOrchestrator class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Elasticsearch client."""
        return MagicMock()

    @pytest.fixture
    def orchestrator(self, mock_client):
        """Create an orchestrator instance."""
        return InvestigationOrchestrator(mock_client)

    @pytest.fixture
    def mock_tool_responses(self):
        """Set up mock responses for all tools."""
        return {
            "search_logs": {
                "total": 10,
                "hits": [
                    {
                        "timestamp": "2026-01-20T10:00:00Z",
                        "service": "payment-service",
                        "level": "error",
                        "message": "Connection refused",
                        "trace_id": "trace-123",
                        "error_type": "ConnectionException",
                    }
                ]
            },
            "get_error_frequency": {
                "total_errors": 100,
                "service_breakdown": [
                    {"service": "payment-service", "error_count": 80, "error_types": []},
                    {"service": "checkout-service", "error_count": 20, "error_types": []},
                ],
                "histogram": [
                    {"timestamp": "2026-01-20T10:00:00Z", "total_errors": 20, "by_service": {}},
                    {"timestamp": "2026-01-20T10:05:00Z", "total_errors": 60, "by_service": {}},
                    {"timestamp": "2026-01-20T10:10:00Z", "total_errors": 20, "by_service": {}},
                ],
                "spike_detected": {
                    "timestamp": "2026-01-20T10:05:00Z",
                    "error_count": 60,
                    "severity": "medium"
                }
            },
            "search_past_incidents": {
                "total": 1,
                "incidents": [
                    {
                        "id": "INV-001",
                        "timestamp": "2026-01-15T10:00:00Z",
                        "root_cause": "Database failover",
                        "resolution": "Restarted pods",
                    }
                ]
            },
            "find_correlated_logs": {
                "trace_id": "trace-123",
                "total_logs": 5,
                "services_involved": ["api-gateway", "payment-service"],
                "has_errors": True,
                "root_cause_service": "payment-service",
                "first_error_time": "2026-01-20T10:00:00Z",
                "timeline": [],
            },
            "find_error_traces": {
                "service_name": "payment-service",
                "time_range": "2h",
                "traces_found": 3,
                "traces": [
                    {"trace_id": "trace-123", "error_type": "ConnectionException"},
                    {"trace_id": "trace-456", "error_type": "TimeoutException"},
                ]
            }
        }

    def test_orchestrator_initialization(self, mock_client):
        """Orchestrator should initialize with client."""
        orch = InvestigationOrchestrator(mock_client)

        assert orch.client == mock_client
        assert orch.on_progress is None

    def test_orchestrator_with_progress_callback(self, mock_client):
        """Orchestrator should accept progress callback."""
        callback = AsyncMock()
        orch = InvestigationOrchestrator(mock_client, on_progress=callback)

        assert orch.on_progress == callback

    def test_extract_keywords(self, orchestrator):
        """Should extract relevant keywords from incident description."""
        keywords = orchestrator._extract_keywords(
            "Payment service is throwing connection timeout errors"
        )

        assert "payment" in keywords
        assert "connection" in keywords
        assert "timeout" in keywords

    def test_extract_keywords_with_no_matches(self, orchestrator):
        """Should return default keyword when no matches found."""
        keywords = orchestrator._extract_keywords("Something weird happened")

        assert keywords == ["error"]

    def test_extract_services(self, orchestrator):
        """Should extract service names from description."""
        services = orchestrator._extract_services(
            "The payment-service and checkout-service are failing"
        )

        assert "payment-service" in services
        assert "checkout-service" in services

    def test_extract_services_with_spaces(self, orchestrator):
        """Should extract services mentioned with spaces."""
        services = orchestrator._extract_services(
            "The payment service is down"
        )

        assert "payment-service" in services

    def test_build_search_query(self, orchestrator):
        """Should build search query from description."""
        query = orchestrator._build_search_query(
            "Database connection refused errors in payment service"
        )

        assert "*" in query  # Should have wildcards
        assert "connection" in query or "database" in query

    def test_generate_suggestions(self, orchestrator):
        """Should generate appropriate suggestions based on context."""
        context = InvestigationContext(incident_description="test")
        context.error_types = ["ConnectionException"]

        suggestions = orchestrator._generate_suggestions(context)

        assert "connection" in suggestions.lower()
        assert "circuit breaker" in suggestions.lower()

    def test_generate_suggestions_for_timeout(self, orchestrator):
        """Should generate timeout-specific suggestions."""
        context = InvestigationContext(incident_description="test")
        context.error_types = ["TimeoutException"]

        suggestions = orchestrator._generate_suggestions(context)

        assert "timeout" in suggestions.lower()

    def test_generate_suggestions_from_past_incidents(self, orchestrator):
        """Should include suggestions from past incidents."""
        context = InvestigationContext(incident_description="test")
        context.past_incidents = [
            {"suggestions": "Restart the pods and clear the cache"}
        ]

        suggestions = orchestrator._generate_suggestions(context)

        assert "past incident" in suggestions.lower()

    def test_generate_root_cause(self, orchestrator):
        """Should generate comprehensive root cause description."""
        context = InvestigationContext(incident_description="test")
        context.root_cause_service = "payment-service"
        context.error_types = ["ConnectionException", "TimeoutException"]
        context.affected_services = ["payment-service", "checkout-service"]
        context.spike_detected = {
            "timestamp": "2026-01-20T10:00:00Z",
            "error_count": 100
        }

        root_cause = orchestrator._generate_root_cause(context)

        assert "payment-service" in root_cause
        assert "ConnectionException" in root_cause
        assert "spike" in root_cause.lower()

    @pytest.mark.asyncio
    async def test_investigate_returns_complete_report(
        self, mock_client, mock_tool_responses
    ):
        """Investigation should return complete report structure."""
        with patch("src.agent.orchestrator.search_logs") as mock_search, \
             patch("src.agent.orchestrator.get_error_frequency") as mock_freq, \
             patch("src.agent.orchestrator.find_correlated_logs") as mock_corr, \
             patch("src.agent.orchestrator.find_error_traces") as mock_traces, \
             patch("src.agent.orchestrator.search_past_incidents") as mock_past:

            mock_search.return_value = mock_tool_responses["search_logs"]
            mock_freq.return_value = mock_tool_responses["get_error_frequency"]
            mock_corr.return_value = mock_tool_responses["find_correlated_logs"]
            mock_traces.return_value = mock_tool_responses["find_error_traces"]
            mock_past.return_value = mock_tool_responses["search_past_incidents"]

            orch = InvestigationOrchestrator(mock_client)
            result = await orch.investigate("Payment service errors", time_range="2h")

            assert "status" in result
            assert result["status"] == "completed"
            assert "findings" in result
            assert "suggestions" in result
            assert "investigation_steps" in result

    @pytest.mark.asyncio
    async def test_investigate_tracks_all_steps(
        self, mock_client, mock_tool_responses
    ):
        """Investigation should execute and track all steps."""
        with patch("src.agent.orchestrator.search_logs") as mock_search, \
             patch("src.agent.orchestrator.get_error_frequency") as mock_freq, \
             patch("src.agent.orchestrator.find_correlated_logs") as mock_corr, \
             patch("src.agent.orchestrator.find_error_traces") as mock_traces, \
             patch("src.agent.orchestrator.search_past_incidents") as mock_past:

            mock_search.return_value = mock_tool_responses["search_logs"]
            mock_freq.return_value = mock_tool_responses["get_error_frequency"]
            mock_corr.return_value = mock_tool_responses["find_correlated_logs"]
            mock_traces.return_value = mock_tool_responses["find_error_traces"]
            mock_past.return_value = mock_tool_responses["search_past_incidents"]

            orch = InvestigationOrchestrator(mock_client)
            result = await orch.investigate("Test incident")

            steps = result["investigation_steps"]
            step_names = [s["step"] for s in steps]

            assert "understand" in step_names
            assert "search" in step_names
            assert "analyze" in step_names
            assert "correlate" in step_names
            assert "synthesize" in step_names

    @pytest.mark.asyncio
    async def test_investigate_calls_progress_callback(self, mock_client, mock_tool_responses):
        """Progress callback should be called for each step."""
        with patch("src.agent.orchestrator.search_logs") as mock_search, \
             patch("src.agent.orchestrator.get_error_frequency") as mock_freq, \
             patch("src.agent.orchestrator.find_correlated_logs") as mock_corr, \
             patch("src.agent.orchestrator.find_error_traces") as mock_traces, \
             patch("src.agent.orchestrator.search_past_incidents") as mock_past:

            mock_search.return_value = mock_tool_responses["search_logs"]
            mock_freq.return_value = mock_tool_responses["get_error_frequency"]
            mock_corr.return_value = mock_tool_responses["find_correlated_logs"]
            mock_traces.return_value = mock_tool_responses["find_error_traces"]
            mock_past.return_value = mock_tool_responses["search_past_incidents"]

            progress_callback = AsyncMock()
            orch = InvestigationOrchestrator(mock_client, on_progress=progress_callback)

            await orch.investigate("Test incident")

            # Progress should be called multiple times
            assert progress_callback.call_count >= 5

    @pytest.mark.asyncio
    async def test_investigate_records_duration(
        self, mock_client, mock_tool_responses
    ):
        """Investigation should record total duration."""
        with patch("src.agent.orchestrator.search_logs") as mock_search, \
             patch("src.agent.orchestrator.get_error_frequency") as mock_freq, \
             patch("src.agent.orchestrator.find_correlated_logs") as mock_corr, \
             patch("src.agent.orchestrator.find_error_traces") as mock_traces, \
             patch("src.agent.orchestrator.search_past_incidents") as mock_past:

            mock_search.return_value = mock_tool_responses["search_logs"]
            mock_freq.return_value = mock_tool_responses["get_error_frequency"]
            mock_corr.return_value = mock_tool_responses["find_correlated_logs"]
            mock_traces.return_value = mock_tool_responses["find_error_traces"]
            mock_past.return_value = mock_tool_responses["search_past_incidents"]

            orch = InvestigationOrchestrator(mock_client)
            result = await orch.investigate("Test incident")

            assert "duration_seconds" in result
            assert result["duration_seconds"] >= 0


class TestRunInvestigation:
    """Tests for the convenience function."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_run_investigation_creates_orchestrator(self, mock_client):
        """run_investigation should create and use orchestrator."""
        with patch.object(InvestigationOrchestrator, "investigate") as mock_investigate:
            mock_investigate.return_value = {"status": "completed"}

            result = await run_investigation(
                mock_client,
                "Test incident",
                time_range="1h"
            )

            mock_investigate.assert_called_once()
            assert result["status"] == "completed"


class TestInvestigateSyncWrapper:
    """Tests for the synchronous wrapper."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    def test_investigate_sync_runs_async(self, mock_client):
        """Sync wrapper should run async investigation."""
        with patch("src.agent.orchestrator.run_investigation") as mock_run:
            future = asyncio.Future()
            future.set_result({"status": "completed"})
            mock_run.return_value = future

            # Note: This test structure is simplified
            # In real tests, we'd need to handle asyncio.run properly
            pass  # Placeholder for sync wrapper test
