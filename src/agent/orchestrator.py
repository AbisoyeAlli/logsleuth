"""
Agent Orchestrator for LogSleuth

Demonstrates multi-step reasoning with tool chaining.
This module shows how the agent decides which tools to use based on
intermediate results, building a complete incident investigation.

The orchestrator implements the 5-step investigation methodology:
1. UNDERSTAND - Parse and understand the incident description
2. SEARCH - Find relevant error logs and patterns
3. ANALYZE - Identify spikes, anomalies, and affected services
4. CORRELATE - Trace errors across service boundaries
5. SYNTHESIZE - Generate root cause analysis and recommendations
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Awaitable
from elasticsearch import Elasticsearch

from src.tools import (
    search_logs,
    get_error_frequency,
    find_correlated_logs,
    find_error_traces,
    search_past_incidents,
    save_investigation,
)


class InvestigationStep(Enum):
    """Steps in the investigation workflow."""
    UNDERSTAND = "understand"
    SEARCH = "search"
    ANALYZE = "analyze"
    CORRELATE = "correlate"
    SYNTHESIZE = "synthesize"
    COMPLETE = "complete"


@dataclass
class StepResult:
    """Result from a single investigation step."""
    step: InvestigationStep
    success: bool
    data: Dict[str, Any]
    reasoning: str
    next_action: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class InvestigationContext:
    """Context accumulated during investigation."""
    incident_description: str
    time_range: str = "2h"

    # Accumulated findings
    error_logs: List[Dict[str, Any]] = field(default_factory=list)
    error_frequency: Optional[Dict[str, Any]] = None
    affected_services: List[str] = field(default_factory=list)
    trace_ids: List[str] = field(default_factory=list)
    correlated_traces: List[Dict[str, Any]] = field(default_factory=list)
    past_incidents: List[Dict[str, Any]] = field(default_factory=list)

    # Analysis results
    spike_detected: Optional[Dict[str, Any]] = None
    root_cause_service: Optional[str] = None
    root_cause: Optional[str] = None
    error_types: List[str] = field(default_factory=list)
    total_errors: int = 0

    # Timeline and metadata
    timeline: List[Dict[str, str]] = field(default_factory=list)
    steps_completed: List[StepResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)


# Type alias for progress callback
ProgressCallback = Callable[[InvestigationStep, str, Dict[str, Any]], Awaitable[None]]


class InvestigationOrchestrator:
    """
    Orchestrates multi-step incident investigation.

    This class demonstrates how an AI agent reasons through an investigation,
    making decisions about which tools to use based on intermediate results.
    """

    def __init__(
        self,
        client: Elasticsearch,
        on_progress: Optional[ProgressCallback] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            client: Elasticsearch client
            on_progress: Optional async callback for progress updates
        """
        self.client = client
        self.on_progress = on_progress

    async def _emit_progress(
        self,
        step: InvestigationStep,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Emit progress update if callback is registered."""
        if self.on_progress:
            await self.on_progress(step, message, data or {})

    async def investigate(
        self,
        incident_description: str,
        time_range: str = "2h",
        save_results: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a complete incident investigation.

        This method orchestrates the full investigation workflow, making
        decisions about which tools to use based on intermediate results.

        Args:
            incident_description: Natural language description of the incident
            time_range: Time range to investigate (e.g., "2h", "1d")
            save_results: Whether to save the investigation to the knowledge base

        Returns:
            Complete investigation results with root cause and recommendations
        """
        context = InvestigationContext(
            incident_description=incident_description,
            time_range=time_range,
        )

        # Execute investigation steps
        await self._step_understand(context)
        await self._step_search(context)
        await self._step_analyze(context)
        await self._step_correlate(context)
        await self._step_synthesize(context)

        # Optionally save to knowledge base
        if save_results and context.root_cause:
            await self._save_investigation(context)

        return self._build_final_report(context)

    async def _step_understand(self, context: InvestigationContext) -> StepResult:
        """
        Step 1: UNDERSTAND - Parse the incident description.

        Extract key information like:
        - Service names mentioned
        - Error types or symptoms
        - Time indicators
        """
        start = datetime.utcnow()
        await self._emit_progress(
            InvestigationStep.UNDERSTAND,
            "Parsing incident description...",
            {"incident": context.incident_description}
        )

        # Extract keywords for search (simple keyword extraction)
        keywords = self._extract_keywords(context.incident_description)
        services_mentioned = self._extract_services(context.incident_description)

        reasoning = f"Identified keywords: {keywords}. "
        if services_mentioned:
            reasoning += f"Services mentioned: {services_mentioned}. "
            context.affected_services.extend(services_mentioned)

        reasoning += "Will search for error logs matching these patterns."

        result = StepResult(
            step=InvestigationStep.UNDERSTAND,
            success=True,
            data={"keywords": keywords, "services": services_mentioned},
            reasoning=reasoning,
            next_action="Search for error logs",
            duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
        )
        context.steps_completed.append(result)

        await self._emit_progress(
            InvestigationStep.UNDERSTAND,
            "Analysis complete",
            {"keywords": keywords, "services": services_mentioned}
        )

        return result

    async def _step_search(self, context: InvestigationContext) -> StepResult:
        """
        Step 2: SEARCH - Find relevant error logs.

        Uses search_logs tool to find errors matching the incident description.
        Adapts search strategy based on what was found in step 1.
        """
        start = datetime.utcnow()
        await self._emit_progress(
            InvestigationStep.SEARCH,
            "Searching for error logs...",
            {"time_range": context.time_range}
        )

        # Build search query from incident description
        search_query = self._build_search_query(context.incident_description)

        # Search for error logs
        results = await asyncio.to_thread(
            search_logs,
            self.client,
            search_query=search_query,
            time_range=context.time_range,
            log_level="error",
            max_results=100,
        )

        context.error_logs = results.get("hits", [])

        # Extract trace IDs for correlation
        for log in context.error_logs:
            if log.get("trace_id") and log["trace_id"] not in context.trace_ids:
                context.trace_ids.append(log["trace_id"])
            if log.get("service") and log["service"] not in context.affected_services:
                context.affected_services.append(log["service"])
            if log.get("error_type") and log["error_type"] not in context.error_types:
                context.error_types.append(log["error_type"])

        # Determine next action based on results
        if results.get("total", 0) == 0:
            reasoning = "No error logs found matching the criteria. "
            reasoning += "Will broaden search in analysis phase."
            next_action = "Analyze overall error patterns"
        else:
            reasoning = f"Found {results['total']} error logs. "
            reasoning += f"Identified {len(context.trace_ids)} unique traces. "
            reasoning += f"Services affected: {context.affected_services}. "
            reasoning += "Will analyze error frequency to identify spikes."
            next_action = "Analyze error frequency"

        result = StepResult(
            step=InvestigationStep.SEARCH,
            success=results.get("total", 0) > 0,
            data={"total_logs": results.get("total", 0), "trace_ids": context.trace_ids[:5]},
            reasoning=reasoning,
            next_action=next_action,
            duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
        )
        context.steps_completed.append(result)

        await self._emit_progress(
            InvestigationStep.SEARCH,
            f"Found {results.get('total', 0)} error logs",
            {"services": context.affected_services, "error_types": context.error_types}
        )

        return result

    async def _step_analyze(self, context: InvestigationContext) -> StepResult:
        """
        Step 3: ANALYZE - Identify patterns and anomalies.

        Uses get_error_frequency to find spikes and determine incident severity.
        Also searches for similar past incidents.
        """
        start = datetime.utcnow()
        await self._emit_progress(
            InvestigationStep.ANALYZE,
            "Analyzing error patterns...",
            {}
        )

        # Get error frequency analysis
        freq_results = await asyncio.to_thread(
            get_error_frequency,
            self.client,
            time_range=context.time_range,
            interval="5m",
        )

        context.error_frequency = freq_results
        context.total_errors = freq_results.get("total_errors", 0)
        context.spike_detected = freq_results.get("spike_detected")

        # Update affected services from frequency analysis
        for svc in freq_results.get("service_breakdown", []):
            if svc["service"] not in context.affected_services:
                context.affected_services.append(svc["service"])
            for et in svc.get("error_types", []):
                if et["type"] not in context.error_types:
                    context.error_types.append(et["type"])

        # Search for similar past incidents
        if context.error_types:
            search_terms = " ".join(context.error_types[:3])
        else:
            search_terms = context.incident_description[:50]

        past_results = await asyncio.to_thread(
            search_past_incidents,
            self.client,
            search_terms=search_terms,
        )
        context.past_incidents = past_results.get("incidents", [])

        # Build reasoning
        reasoning = f"Total errors in timeframe: {context.total_errors}. "

        if context.spike_detected:
            reasoning += f"Spike detected at {context.spike_detected['timestamp']} "
            reasoning += f"with {context.spike_detected['error_count']} errors "
            reasoning += f"(severity: {context.spike_detected['severity']}). "
            context.timeline.append({
                "timestamp": context.spike_detected["timestamp"],
                "event": f"Error spike ({context.spike_detected['error_count']} errors)",
                "service": "multiple",
            })

        if context.past_incidents:
            reasoning += f"Found {len(context.past_incidents)} similar past incidents. "

        reasoning += "Will correlate traces to identify root cause service."

        result = StepResult(
            step=InvestigationStep.ANALYZE,
            success=True,
            data={
                "total_errors": context.total_errors,
                "spike": context.spike_detected,
                "past_incidents": len(context.past_incidents),
            },
            reasoning=reasoning,
            next_action="Correlate traces across services",
            duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
        )
        context.steps_completed.append(result)

        await self._emit_progress(
            InvestigationStep.ANALYZE,
            f"Analyzed {context.total_errors} errors",
            {"spike": context.spike_detected, "past_incidents": len(context.past_incidents)}
        )

        return result

    async def _step_correlate(self, context: InvestigationContext) -> StepResult:
        """
        Step 4: CORRELATE - Trace errors across services.

        Uses find_correlated_logs to understand error propagation.
        Identifies the root cause service based on trace analysis.
        """
        start = datetime.utcnow()
        await self._emit_progress(
            InvestigationStep.CORRELATE,
            "Correlating traces across services...",
            {"trace_count": len(context.trace_ids)}
        )

        root_cause_candidates = {}

        # If we have trace IDs, correlate them
        if context.trace_ids:
            for trace_id in context.trace_ids[:5]:  # Limit to 5 traces
                try:
                    trace_result = await asyncio.to_thread(
                        find_correlated_logs,
                        self.client,
                        trace_id=trace_id,
                    )
                    context.correlated_traces.append(trace_result)

                    # Track root cause service candidates
                    if trace_result.get("root_cause_service"):
                        svc = trace_result["root_cause_service"]
                        root_cause_candidates[svc] = root_cause_candidates.get(svc, 0) + 1

                        # Add to timeline
                        if trace_result.get("first_error_time"):
                            context.timeline.append({
                                "timestamp": trace_result["first_error_time"],
                                "event": f"Error in trace {trace_id[:8]}...",
                                "service": svc,
                            })
                except Exception:
                    continue
        else:
            # No trace IDs, find them from the most affected service
            if context.affected_services:
                service = context.affected_services[0]
                traces = await asyncio.to_thread(
                    find_error_traces,
                    self.client,
                    service_name=service,
                    time_range=context.time_range,
                )

                for trace in traces.get("traces", [])[:3]:
                    try:
                        trace_result = await asyncio.to_thread(
                            find_correlated_logs,
                            self.client,
                            trace_id=trace["trace_id"],
                        )
                        context.correlated_traces.append(trace_result)

                        if trace_result.get("root_cause_service"):
                            svc = trace_result["root_cause_service"]
                            root_cause_candidates[svc] = root_cause_candidates.get(svc, 0) + 1
                    except Exception:
                        continue

        # Determine most likely root cause service
        if root_cause_candidates:
            context.root_cause_service = max(
                root_cause_candidates,
                key=root_cause_candidates.get
            )
        elif context.affected_services:
            context.root_cause_service = context.affected_services[0]

        # Build reasoning
        reasoning = f"Analyzed {len(context.correlated_traces)} correlated traces. "
        if root_cause_candidates:
            reasoning += f"Root cause candidates: {dict(root_cause_candidates)}. "
            reasoning += f"Most likely root cause service: {context.root_cause_service}. "
        reasoning += "Will synthesize findings into final report."

        result = StepResult(
            step=InvestigationStep.CORRELATE,
            success=len(context.correlated_traces) > 0,
            data={
                "traces_analyzed": len(context.correlated_traces),
                "root_cause_service": context.root_cause_service,
                "candidates": root_cause_candidates,
            },
            reasoning=reasoning,
            next_action="Synthesize findings",
            duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
        )
        context.steps_completed.append(result)

        await self._emit_progress(
            InvestigationStep.CORRELATE,
            f"Root cause service: {context.root_cause_service}",
            {"traces": len(context.correlated_traces), "candidates": root_cause_candidates}
        )

        return result

    async def _step_synthesize(self, context: InvestigationContext) -> StepResult:
        """
        Step 5: SYNTHESIZE - Generate final analysis and recommendations.

        Combines all findings into a coherent root cause analysis
        and actionable recommendations.
        """
        start = datetime.utcnow()
        await self._emit_progress(
            InvestigationStep.SYNTHESIZE,
            "Synthesizing findings...",
            {}
        )

        # Build root cause description
        context.root_cause = self._generate_root_cause(context)

        # Sort timeline
        context.timeline.sort(key=lambda x: x.get("timestamp", ""))

        # Build reasoning summary
        reasoning = f"Investigation complete. "
        reasoning += f"Root cause: {context.root_cause_service} - "
        reasoning += f"{context.root_cause[:100]}... " if context.root_cause else ""
        reasoning += f"Total errors: {context.total_errors}. "
        reasoning += f"Services affected: {len(context.affected_services)}."

        result = StepResult(
            step=InvestigationStep.SYNTHESIZE,
            success=True,
            data={
                "root_cause": context.root_cause,
                "root_cause_service": context.root_cause_service,
            },
            reasoning=reasoning,
            next_action=None,
            duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
        )
        context.steps_completed.append(result)

        await self._emit_progress(
            InvestigationStep.COMPLETE,
            "Investigation complete",
            {"root_cause": context.root_cause}
        )

        return result

    async def _save_investigation(self, context: InvestigationContext):
        """Save the investigation to the knowledge base."""
        await asyncio.to_thread(
            save_investigation,
            self.client,
            incident_input=context.incident_description,
            time_range_start=context.start_time.isoformat(),
            time_range_end=datetime.utcnow().isoformat(),
            root_cause=context.root_cause or "Unknown",
            root_cause_service=context.root_cause_service or "Unknown",
            affected_services=context.affected_services,
            error_types=context.error_types,
            error_count=context.total_errors,
            timeline=context.timeline,
            suggestions=self._generate_suggestions(context),
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from incident description."""
        # Common error-related keywords
        error_keywords = [
            "timeout", "connection", "refused", "failed", "error", "exception",
            "slow", "latency", "spike", "crash", "memory", "cpu", "disk",
            "database", "db", "cache", "redis", "queue", "kafka",
            "payment", "checkout", "user", "auth", "login",
        ]

        text_lower = text.lower()
        found = [kw for kw in error_keywords if kw in text_lower]
        return found or ["error"]

    def _extract_services(self, text: str) -> List[str]:
        """Extract service names from incident description."""
        known_services = [
            "payment-service", "checkout-service", "user-service",
            "inventory-service", "api-gateway",
        ]

        text_lower = text.lower()
        found = []
        for svc in known_services:
            if svc in text_lower or svc.replace("-", " ") in text_lower:
                found.append(svc)

        return found

    def _build_search_query(self, text: str) -> str:
        """Build search query from incident description."""
        keywords = self._extract_keywords(text)
        return "*" + keywords[0] + "*" if keywords else "*error*"

    def _generate_root_cause(self, context: InvestigationContext) -> str:
        """Generate root cause description from context."""
        parts = []

        if context.root_cause_service:
            parts.append(f"The root cause originated in {context.root_cause_service}.")

        if context.error_types:
            parts.append(f"Error types observed: {', '.join(context.error_types[:3])}.")

        if context.spike_detected:
            parts.append(
                f"A significant error spike was detected at "
                f"{context.spike_detected['timestamp']} with "
                f"{context.spike_detected['error_count']} errors."
            )

        if context.affected_services:
            parts.append(
                f"The incident affected {len(context.affected_services)} services: "
                f"{', '.join(context.affected_services)}."
            )

        if context.past_incidents:
            similar = context.past_incidents[0]
            parts.append(
                f"Similar incident found from {similar.get('timestamp', 'past')}: "
                f"{similar.get('root_cause', 'Unknown cause')[:100]}..."
            )

        return " ".join(parts) if parts else "Root cause could not be determined."

    def _generate_suggestions(self, context: InvestigationContext) -> str:
        """Generate remediation suggestions."""
        suggestions = []

        # Based on error types
        if "ConnectionException" in context.error_types or "connection" in str(context.error_types).lower():
            suggestions.append("1. Check database/service connectivity and connection pool settings")
            suggestions.append("2. Implement circuit breaker pattern for failing connections")

        if "TimeoutException" in context.error_types or "timeout" in str(context.error_types).lower():
            suggestions.append("1. Review and adjust timeout configurations")
            suggestions.append("2. Check for slow database queries or external API calls")
            suggestions.append("3. Consider implementing request hedging for critical paths")

        if context.spike_detected and context.spike_detected.get("severity") == "high":
            suggestions.append("1. Scale affected services horizontally")
            suggestions.append("2. Review rate limiting and load shedding policies")

        # Based on past incidents
        if context.past_incidents:
            past_suggestions = context.past_incidents[0].get("suggestions", "")
            if past_suggestions:
                suggestions.append(f"From past incident: {past_suggestions[:200]}")

        if not suggestions:
            suggestions = [
                "1. Review logs for the affected service",
                "2. Check resource utilization (CPU, memory, connections)",
                "3. Verify external dependencies are healthy",
            ]

        return "\n".join(suggestions)

    def _build_final_report(self, context: InvestigationContext) -> Dict[str, Any]:
        """Build the final investigation report."""
        duration = (datetime.utcnow() - context.start_time).total_seconds()

        return {
            "status": "completed",
            "duration_seconds": duration,
            "incident": {
                "description": context.incident_description,
                "time_range": context.time_range,
            },
            "findings": {
                "root_cause": context.root_cause,
                "root_cause_service": context.root_cause_service,
                "affected_services": context.affected_services,
                "error_types": context.error_types,
                "total_errors": context.total_errors,
                "spike_detected": context.spike_detected,
            },
            "timeline": context.timeline,
            "past_incidents": [
                {
                    "id": inc.get("id"),
                    "root_cause": inc.get("root_cause"),
                    "resolution": inc.get("resolution"),
                }
                for inc in context.past_incidents[:3]
            ],
            "suggestions": self._generate_suggestions(context),
            "investigation_steps": [
                {
                    "step": step.step.value,
                    "success": step.success,
                    "reasoning": step.reasoning,
                    "duration_ms": step.duration_ms,
                }
                for step in context.steps_completed
            ],
        }


async def run_investigation(
    client: Elasticsearch,
    incident: str,
    time_range: str = "2h",
    on_progress: Optional[ProgressCallback] = None,
    save_results: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to run an investigation.

    Args:
        client: Elasticsearch client
        incident: Incident description
        time_range: Time range to investigate
        on_progress: Optional progress callback
        save_results: Whether to save to knowledge base

    Returns:
        Investigation results
    """
    orchestrator = InvestigationOrchestrator(client, on_progress=on_progress)
    return await orchestrator.investigate(incident, time_range, save_results)


# Synchronous wrapper for non-async contexts
def investigate_sync(
    client: Elasticsearch,
    incident: str,
    time_range: str = "2h",
    save_results: bool = False,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for investigation.

    For use in contexts where async is not available.
    """
    return asyncio.run(run_investigation(client, incident, time_range, save_results=save_results))


if __name__ == "__main__":
    # Demo the orchestrator
    import json
    from src.utils.elasticsearch_client import get_elasticsearch_client

    async def progress_printer(step: InvestigationStep, message: str, data: Dict[str, Any]):
        """Print progress updates."""
        print(f"  [{step.value.upper()}] {message}")
        if data:
            for key, value in data.items():
                print(f"    - {key}: {value}")

    async def main():
        client = get_elasticsearch_client()

        print("=" * 60)
        print("LogSleuth Investigation Orchestrator Demo")
        print("=" * 60)
        print()

        incident = "Payment service is throwing connection refused errors"
        print(f"Incident: {incident}")
        print("-" * 60)

        results = await run_investigation(
            client,
            incident=incident,
            time_range="2h",
            on_progress=progress_printer,
        )

        print()
        print("=" * 60)
        print("INVESTIGATION RESULTS")
        print("=" * 60)
        print(json.dumps(results, indent=2, default=str))

    asyncio.run(main())
