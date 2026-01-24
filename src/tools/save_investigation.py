"""
Save Investigation Tool

Saves completed investigations to Elasticsearch for future reference.
Builds a knowledge base of past incidents and their resolutions.
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from elasticsearch import Elasticsearch

from src.utils.elasticsearch_client import INVESTIGATION_INDEX


# Tool definition for Agent Builder API
# Note: This tool uses a custom implementation, not ES|QL
TOOL_DEFINITION = {
    "toolId": "save_investigation",
    "description": """Save a completed investigation to the knowledge base for future reference.

Use this tool when:
- You've completed an investigation and identified the root cause
- You want to save the findings for future similar incidents
- The user asks you to record or document the investigation

This creates a searchable record that helps with future incident response.""",
    "labels": ["persistence", "knowledge", "documentation"],
    "type": "custom",
    "parameters": [
        {
            "name": "incident_input",
            "type": "string",
            "description": "The original incident description or alert that triggered the investigation",
            "required": True
        },
        {
            "name": "time_range_start",
            "type": "string",
            "description": "Start of the incident time range (ISO format)",
            "required": True
        },
        {
            "name": "time_range_end",
            "type": "string",
            "description": "End of the incident time range (ISO format)",
            "required": True
        },
        {
            "name": "root_cause",
            "type": "string",
            "description": "Description of the root cause identified",
            "required": True
        },
        {
            "name": "root_cause_service",
            "type": "string",
            "description": "The service where the root cause originated",
            "required": True
        },
        {
            "name": "affected_services",
            "type": "array",
            "description": "List of services affected by the incident",
            "required": True
        },
        {
            "name": "error_types",
            "type": "array",
            "description": "Types of errors observed (e.g., 'ConnectionException', 'TimeoutException')",
            "required": False
        },
        {
            "name": "error_count",
            "type": "integer",
            "description": "Total number of errors observed during the incident",
            "required": False
        },
        {
            "name": "timeline",
            "type": "array",
            "description": "Key events in chronological order",
            "required": False
        },
        {
            "name": "suggestions",
            "type": "string",
            "description": "Remediation suggestions for this type of incident",
            "required": False
        },
        {
            "name": "resolution_applied",
            "type": "string",
            "description": "What was actually done to resolve the incident (if known)",
            "required": False
        }
    ]
}


def save_investigation(
    client: Elasticsearch,
    incident_input: str,
    time_range_start: str,
    time_range_end: str,
    root_cause: str,
    root_cause_service: str,
    affected_services: List[str],
    error_types: Optional[List[str]] = None,
    error_count: Optional[int] = None,
    timeline: Optional[List[Dict[str, str]]] = None,
    evidence_log_ids: Optional[List[str]] = None,
    suggestions: Optional[str] = None,
    resolution_applied: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save an investigation to Elasticsearch.

    Args:
        client: Elasticsearch client
        incident_input: Original incident description
        time_range_start: Incident start time (ISO format)
        time_range_end: Incident end time (ISO format)
        root_cause: Root cause description
        root_cause_service: Service where root cause originated
        affected_services: List of affected services
        error_types: List of error types observed
        error_count: Total error count
        timeline: List of timeline events
        evidence_log_ids: IDs of key log entries as evidence
        suggestions: Remediation suggestions
        resolution_applied: What was done to resolve

    Returns:
        Dict with investigation ID and status
    """
    investigation_id = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    document = {
        "@timestamp": datetime.utcnow().isoformat(),
        "investigation": {
            "id": investigation_id,
            "status": "completed",
        },
        "incident": {
            "input": incident_input,
            "time_range": {
                "start": time_range_start,
                "end": time_range_end,
            },
            "services_involved": affected_services,
        },
        "findings": {
            "root_cause": root_cause,
            "root_cause_service": root_cause_service,
            "affected_services": affected_services,
            "error_types": error_types or [],
            "error_count": error_count,
            "timeline": timeline or [],
            "evidence_log_ids": evidence_log_ids or [],
        },
        "remediation": {
            "suggestions": suggestions,
            "resolution_applied": resolution_applied,
        },
    }

    # Ensure index exists
    if not client.indices.exists(index=INVESTIGATION_INDEX):
        from src.data.index_templates import INVESTIGATION_INDEX_MAPPING
        client.indices.create(index=INVESTIGATION_INDEX, body=INVESTIGATION_INDEX_MAPPING)

    # Index the document
    result = client.index(
        index=INVESTIGATION_INDEX,
        id=investigation_id,
        document=document,
        refresh=True,  # Make immediately searchable
    )

    return {
        "success": result["result"] in ["created", "updated"],
        "investigation_id": investigation_id,
        "message": f"Investigation saved successfully with ID: {investigation_id}",
    }


def create_sample_investigations(client: Elasticsearch) -> List[str]:
    """
    Create sample investigations for demo purposes.

    Returns:
        List of created investigation IDs
    """
    sample_investigations = [
        {
            "incident_input": "Payment service throwing database connection errors",
            "time_range_start": "2026-01-20T10:00:00Z",
            "time_range_end": "2026-01-20T10:30:00Z",
            "root_cause": "Database primary failover caused connection pool exhaustion in payment-service. The failover took 45 seconds during which all connection attempts failed, leading to pool exhaustion.",
            "root_cause_service": "payment-service",
            "affected_services": ["payment-service", "checkout-service", "api-gateway"],
            "error_types": ["ConnectionPoolExhaustedException", "ConnectionException"],
            "error_count": 156,
            "timeline": [
                {"timestamp": "2026-01-20T10:12:03Z", "event": "Database primary failover initiated", "service": "database"},
                {"timestamp": "2026-01-20T10:12:15Z", "event": "Connection errors begin", "service": "payment-service"},
                {"timestamp": "2026-01-20T10:12:45Z", "event": "Connection pool exhausted", "service": "payment-service"},
                {"timestamp": "2026-01-20T10:13:00Z", "event": "Upstream errors cascade", "service": "checkout-service"},
            ],
            "suggestions": "1. Implement connection pool auto-recovery\n2. Add database failover detection\n3. Configure circuit breaker for database calls\n4. Increase connection timeout during failover",
            "resolution_applied": "Restarted payment-service pods to reset connection pools. Database recovered automatically.",
        },
        {
            "incident_input": "Checkout timeouts during peak traffic",
            "time_range_start": "2026-01-15T14:00:00Z",
            "time_range_end": "2026-01-15T14:45:00Z",
            "root_cause": "Inventory service thread pool exhaustion due to slow database queries during peak load. Query optimization needed for high-traffic scenarios.",
            "root_cause_service": "inventory-service",
            "affected_services": ["inventory-service", "checkout-service", "api-gateway"],
            "error_types": ["TimeoutException", "RejectedExecutionException", "ServerOverloadException"],
            "error_count": 423,
            "timeline": [
                {"timestamp": "2026-01-15T14:05:00Z", "event": "Traffic spike begins", "service": "api-gateway"},
                {"timestamp": "2026-01-15T14:10:00Z", "event": "Slow queries detected", "service": "inventory-service"},
                {"timestamp": "2026-01-15T14:15:00Z", "event": "Thread pool exhausted", "service": "inventory-service"},
                {"timestamp": "2026-01-15T14:18:00Z", "event": "Timeout cascade", "service": "checkout-service"},
            ],
            "suggestions": "1. Optimize slow inventory queries\n2. Add database query caching\n3. Implement request rate limiting\n4. Scale inventory-service horizontally during peak hours",
            "resolution_applied": "Scaled inventory-service to 5 replicas. Added query result caching.",
        },
    ]

    created_ids = []
    for investigation in sample_investigations:
        result = save_investigation(client, **investigation)
        if result["success"]:
            created_ids.append(result["investigation_id"])

    return created_ids


if __name__ == "__main__":
    # Test the tool locally
    from src.utils.elasticsearch_client import get_elasticsearch_client

    client = get_elasticsearch_client()

    # Create sample investigations
    print("Creating sample investigations...")
    ids = create_sample_investigations(client)
    print(f"Created {len(ids)} sample investigations:")
    for id in ids:
        print(f"  - {id}")
