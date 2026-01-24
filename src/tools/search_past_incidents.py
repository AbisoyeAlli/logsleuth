"""
Search Past Incidents Tool

Searches the investigation history to find similar past incidents.
Helps identify recurring issues and suggests resolutions based on past fixes.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from elasticsearch import Elasticsearch

from src.utils.elasticsearch_client import INVESTIGATION_INDEX


# ES|QL query for Agent Builder deployment
ESQL_QUERY = """
FROM investigations-logsleuth
| WHERE findings.root_cause LIKE ?search_terms OR incident.input LIKE ?search_terms
| WHERE (?service_name == "" OR findings.root_cause_service == ?service_name)
| WHERE (?error_type == "" OR findings.error_types == ?error_type)
| SORT @timestamp DESC
| LIMIT 10
"""

# Tool definition for Agent Builder API
TOOL_DEFINITION = {
    "toolId": "search_past_incidents",
    "description": """Search for similar past incidents in the investigation history.

Use this tool when:
- You've identified a root cause and want to see if it happened before
- You want to find how similar incidents were resolved
- You're looking for patterns in recurring issues
- You need remediation suggestions based on past experience

Returns past investigations with their root causes and resolutions.""",
    "labels": ["history", "incidents", "knowledge"],
    "type": "esql",
    "configuration": {
        "query": ESQL_QUERY
    },
    "parameters": [
        {
            "name": "search_terms",
            "type": "string",
            "description": "Keywords to search for in past incidents (e.g., 'database connection', 'timeout', 'circuit breaker')",
            "required": True
        },
        {
            "name": "service_name",
            "type": "string",
            "description": "Filter by service that was the root cause. Leave empty for all services.",
            "required": False
        },
        {
            "name": "error_type",
            "type": "string",
            "description": "Filter by error type. Leave empty for all types.",
            "required": False
        }
    ]
}


def search_past_incidents(
    client: Elasticsearch,
    search_terms: str,
    service_name: Optional[str] = None,
    error_type: Optional[str] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    Search for similar past incidents.

    Args:
        client: Elasticsearch client
        search_terms: Keywords to search for
        service_name: Optional service filter
        error_type: Optional error type filter
        max_results: Maximum results to return

    Returns:
        Dict with matching past incidents
    """
    # Check if index exists
    if not client.indices.exists(index=INVESTIGATION_INDEX):
        return {
            "total": 0,
            "incidents": [],
            "message": "No investigation history found. This may be the first incident."
        }

    # Build query
    must_clauses = [
        {
            "bool": {
                "should": [
                    {"match": {"findings.root_cause": search_terms}},
                    {"match": {"incident.input": search_terms}},
                    {"match": {"remediation.suggestions": search_terms}},
                ],
                "minimum_should_match": 1
            }
        }
    ]

    if service_name:
        must_clauses.append({"term": {"findings.root_cause_service": service_name}})

    if error_type:
        must_clauses.append({"term": {"findings.error_types": error_type}})

    query = {
        "query": {"bool": {"must": must_clauses}},
        "sort": [{"@timestamp": "desc"}],
        "size": max_results,
    }

    try:
        result = client.search(index=INVESTIGATION_INDEX, body=query)
    except Exception as e:
        return {
            "total": 0,
            "incidents": [],
            "message": f"Error searching incidents: {str(e)}"
        }

    # Format results
    incidents = []
    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        incident = {
            "id": src.get("investigation", {}).get("id"),
            "timestamp": src.get("@timestamp"),
            "input": src.get("incident", {}).get("input"),
            "root_cause": src.get("findings", {}).get("root_cause"),
            "root_cause_service": src.get("findings", {}).get("root_cause_service"),
            "affected_services": src.get("findings", {}).get("affected_services", []),
            "error_types": src.get("findings", {}).get("error_types", []),
            "resolution": src.get("remediation", {}).get("resolution_applied"),
            "suggestions": src.get("remediation", {}).get("suggestions"),
        }
        incidents.append(incident)

    return {
        "total": result["hits"]["total"]["value"],
        "search_terms": search_terms,
        "incidents": incidents,
    }


def get_incident_by_id(
    client: Elasticsearch,
    incident_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get a specific incident by ID.

    Args:
        client: Elasticsearch client
        incident_id: The investigation ID

    Returns:
        The incident document or None
    """
    if not client.indices.exists(index=INVESTIGATION_INDEX):
        return None

    query = {
        "query": {"term": {"investigation.id": incident_id}},
        "size": 1,
    }

    result = client.search(index=INVESTIGATION_INDEX, body=query)

    if result["hits"]["hits"]:
        return result["hits"]["hits"][0]["_source"]
    return None


if __name__ == "__main__":
    # Test the tool locally
    from src.utils.elasticsearch_client import get_elasticsearch_client

    client = get_elasticsearch_client()

    # Test search
    results = search_past_incidents(
        client,
        search_terms="database connection",
    )

    print(f"Found {results['total']} past incidents")
    for incident in results["incidents"]:
        print(f"\n  ID: {incident['id']}")
        print(f"  Root cause: {incident['root_cause'][:80] if incident['root_cause'] else 'N/A'}...")
        print(f"  Resolution: {incident['resolution'][:80] if incident['resolution'] else 'N/A'}...")
