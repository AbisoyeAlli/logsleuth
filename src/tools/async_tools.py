"""
Async versions of LogSleuth tools.

Provides async wrappers for all tools to support non-blocking execution
and streaming investigation workflows.
"""

import asyncio
from typing import Optional, Dict, Any, List, AsyncGenerator, Callable
from elasticsearch import Elasticsearch

from src.tools.search_logs import search_logs
from src.tools.get_error_frequency import get_error_frequency
from src.tools.find_correlated_logs import find_correlated_logs, find_error_traces
from src.tools.search_past_incidents import search_past_incidents
from src.tools.save_investigation import save_investigation


async def search_logs_async(
    client: Elasticsearch,
    search_query: str,
    time_range: str = "1h",
    service_name: Optional[str] = None,
    log_level: Optional[str] = None,
    max_results: int = 50,
) -> Dict[str, Any]:
    """
    Async version of search_logs.

    Runs the synchronous search_logs in a thread pool to avoid blocking.
    """
    return await asyncio.to_thread(
        search_logs,
        client,
        search_query=search_query,
        time_range=time_range,
        service_name=service_name,
        log_level=log_level,
        max_results=max_results,
    )


async def get_error_frequency_async(
    client: Elasticsearch,
    time_range: str = "1h",
    service_name: Optional[str] = None,
    error_type: Optional[str] = None,
    interval: str = "5m",
) -> Dict[str, Any]:
    """
    Async version of get_error_frequency.
    """
    return await asyncio.to_thread(
        get_error_frequency,
        client,
        time_range=time_range,
        service_name=service_name,
        error_type=error_type,
        interval=interval,
    )


async def find_correlated_logs_async(
    client: Elasticsearch,
    trace_id: str,
) -> Dict[str, Any]:
    """
    Async version of find_correlated_logs.
    """
    return await asyncio.to_thread(
        find_correlated_logs,
        client,
        trace_id=trace_id,
    )


async def find_error_traces_async(
    client: Elasticsearch,
    service_name: str,
    time_range: str = "1h",
    max_traces: int = 10,
) -> Dict[str, Any]:
    """
    Async version of find_error_traces.
    """
    return await asyncio.to_thread(
        find_error_traces,
        client,
        service_name=service_name,
        time_range=time_range,
        max_traces=max_traces,
    )


async def search_past_incidents_async(
    client: Elasticsearch,
    search_terms: str,
    service_name: Optional[str] = None,
    error_type: Optional[str] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    Async version of search_past_incidents.
    """
    return await asyncio.to_thread(
        search_past_incidents,
        client,
        search_terms=search_terms,
        service_name=service_name,
        error_type=error_type,
        max_results=max_results,
    )


async def save_investigation_async(
    client: Elasticsearch,
    incident_input: str,
    time_range_start: str,
    time_range_end: str,
    root_cause: str,
    root_cause_service: str,
    affected_services: List[str],
    **kwargs,
) -> Dict[str, Any]:
    """
    Async version of save_investigation.
    """
    return await asyncio.to_thread(
        save_investigation,
        client,
        incident_input=incident_input,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
        root_cause=root_cause,
        root_cause_service=root_cause_service,
        affected_services=affected_services,
        **kwargs,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# STREAMING SUPPORT
# ═══════════════════════════════════════════════════════════════════════════════

class StreamingInvestigation:
    """
    Streaming investigation that yields results as they become available.

    Allows for real-time progress updates during long-running investigations.
    """

    def __init__(self, client: Elasticsearch):
        self.client = client

    async def investigate_stream(
        self,
        incident: str,
        time_range: str = "2h",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream investigation results as they become available.

        Yields dictionaries with:
        - step: Current investigation step
        - status: 'started', 'completed', or 'error'
        - data: Step-specific data

        Usage:
            async for update in investigation.investigate_stream("error in payment"):
                print(f"Step: {update['step']}, Status: {update['status']}")
        """
        # Step 1: Understand
        yield {
            "step": "understand",
            "status": "started",
            "message": "Parsing incident description...",
        }
        await asyncio.sleep(0.1)  # Small delay for UI updates
        yield {
            "step": "understand",
            "status": "completed",
            "data": {"incident": incident, "time_range": time_range},
        }

        # Step 2: Search
        yield {
            "step": "search",
            "status": "started",
            "message": "Searching for error logs...",
        }
        try:
            error_freq = await get_error_frequency_async(
                self.client,
                time_range=time_range,
            )
            yield {
                "step": "search",
                "status": "completed",
                "data": {
                    "total_errors": error_freq.get("total_errors", 0),
                    "services": [s["service"] for s in error_freq.get("service_breakdown", [])],
                },
            }
        except Exception as e:
            yield {
                "step": "search",
                "status": "error",
                "error": str(e),
            }
            return

        # Step 3: Analyze
        yield {
            "step": "analyze",
            "status": "started",
            "message": "Analyzing error patterns...",
        }

        root_cause_service = None
        spike_detected = error_freq.get("spike_detected")

        if error_freq.get("service_breakdown"):
            root_cause_service = error_freq["service_breakdown"][0]["service"]

        yield {
            "step": "analyze",
            "status": "completed",
            "data": {
                "root_cause_service": root_cause_service,
                "spike_detected": spike_detected,
            },
        }

        # Step 4: Correlate
        yield {
            "step": "correlate",
            "status": "started",
            "message": "Correlating traces across services...",
        }

        trace_info = None
        if root_cause_service:
            try:
                traces = await find_error_traces_async(
                    self.client,
                    service_name=root_cause_service,
                    time_range=time_range,
                )
                if traces.get("traces"):
                    trace_id = traces["traces"][0]["trace_id"]
                    trace_info = await find_correlated_logs_async(
                        self.client,
                        trace_id=trace_id,
                    )
            except Exception as e:
                yield {
                    "step": "correlate",
                    "status": "error",
                    "error": str(e),
                }

        yield {
            "step": "correlate",
            "status": "completed",
            "data": {
                "trace_info": trace_info,
                "services_involved": trace_info.get("services_involved", []) if trace_info else [],
            },
        }

        # Step 5: Synthesize
        yield {
            "step": "synthesize",
            "status": "started",
            "message": "Generating recommendations...",
        }

        # Search for similar past incidents
        past_incidents = []
        if root_cause_service:
            try:
                past = await search_past_incidents_async(
                    self.client,
                    search_terms=root_cause_service,
                )
                past_incidents = past.get("incidents", [])
            except:
                pass

        yield {
            "step": "synthesize",
            "status": "completed",
            "data": {
                "past_incidents": len(past_incidents),
                "recommendations": self._generate_recommendations(
                    root_cause_service, spike_detected, past_incidents
                ),
            },
        }

        # Final summary
        yield {
            "step": "complete",
            "status": "completed",
            "data": {
                "incident": incident,
                "root_cause_service": root_cause_service,
                "total_errors": error_freq.get("total_errors", 0),
                "spike_detected": spike_detected,
                "services_affected": len(error_freq.get("service_breakdown", [])),
                "timeline": trace_info.get("timeline", []) if trace_info else [],
            },
        }

    def _generate_recommendations(
        self,
        root_cause_service: Optional[str],
        spike_detected: Optional[Dict],
        past_incidents: List,
    ) -> List[str]:
        """Generate recommendations based on investigation findings."""
        recommendations = []

        if root_cause_service:
            recommendations.append(
                f"Review recent changes to {root_cause_service}"
            )

        if spike_detected:
            severity = spike_detected.get("severity", "unknown")
            if severity == "high":
                recommendations.append("Consider scaling affected services immediately")
                recommendations.append("Enable circuit breakers if not already active")
            else:
                recommendations.append("Monitor error rates closely for the next hour")

        if past_incidents:
            recommendations.append(
                f"Review {len(past_incidents)} similar past incidents for resolution patterns"
            )

        if not recommendations:
            recommendations = [
                "Review application logs for more details",
                "Check external dependencies for availability",
                "Verify recent deployments or configuration changes",
            ]

        return recommendations


async def run_streaming_investigation(
    client: Elasticsearch,
    incident: str,
    time_range: str = "2h",
    on_update: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Run a streaming investigation with optional update callback.

    Args:
        client: Elasticsearch client
        incident: Incident description
        time_range: Time range to investigate
        on_update: Optional callback for each update

    Returns:
        Final investigation results
    """
    streamer = StreamingInvestigation(client)
    final_result = None

    async for update in streamer.investigate_stream(incident, time_range):
        if on_update:
            on_update(update)
        if update.get("step") == "complete":
            final_result = update.get("data", {})

    return final_result or {}


# Export async tools
__all__ = [
    "search_logs_async",
    "get_error_frequency_async",
    "find_correlated_logs_async",
    "find_error_traces_async",
    "search_past_incidents_async",
    "save_investigation_async",
    "StreamingInvestigation",
    "run_streaming_investigation",
]
