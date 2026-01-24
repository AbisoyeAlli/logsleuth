"""Custom tools for the LogSleuth agent.

This module exports all tool definitions and implementations for:
1. Local Python testing
2. Deployment to Elastic Agent Builder
"""

from src.tools.search_logs import (
    TOOL_DEFINITION as SEARCH_LOGS_TOOL,
    search_logs,
)
from src.tools.get_error_frequency import (
    TOOL_DEFINITION as ERROR_FREQUENCY_TOOL,
    get_error_frequency,
)
from src.tools.find_correlated_logs import (
    TOOL_DEFINITION as CORRELATED_LOGS_TOOL,
    FIND_ERROR_TRACES_TOOL,
    find_correlated_logs,
    find_error_traces,
)
from src.tools.search_past_incidents import (
    TOOL_DEFINITION as PAST_INCIDENTS_TOOL,
    search_past_incidents,
)
from src.tools.save_investigation import (
    TOOL_DEFINITION as SAVE_INVESTIGATION_TOOL,
    save_investigation,
    create_sample_investigations,
)

# All tool definitions for Agent Builder deployment
ALL_TOOL_DEFINITIONS = [
    SEARCH_LOGS_TOOL,
    ERROR_FREQUENCY_TOOL,
    CORRELATED_LOGS_TOOL,
    FIND_ERROR_TRACES_TOOL,
    PAST_INCIDENTS_TOOL,
    SAVE_INVESTIGATION_TOOL,
]

# Tool implementations for local testing
TOOL_IMPLEMENTATIONS = {
    "search_logs": search_logs,
    "get_error_frequency": get_error_frequency,
    "find_correlated_logs": find_correlated_logs,
    "find_error_traces": find_error_traces,
    "search_past_incidents": search_past_incidents,
    "save_investigation": save_investigation,
}

__all__ = [
    # Tool definitions
    "SEARCH_LOGS_TOOL",
    "ERROR_FREQUENCY_TOOL",
    "CORRELATED_LOGS_TOOL",
    "FIND_ERROR_TRACES_TOOL",
    "PAST_INCIDENTS_TOOL",
    "SAVE_INVESTIGATION_TOOL",
    "ALL_TOOL_DEFINITIONS",
    # Tool implementations
    "search_logs",
    "get_error_frequency",
    "find_correlated_logs",
    "find_error_traces",
    "search_past_incidents",
    "save_investigation",
    "create_sample_investigations",
    "TOOL_IMPLEMENTATIONS",
]
