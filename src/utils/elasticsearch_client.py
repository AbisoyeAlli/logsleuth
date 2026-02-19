"""Elasticsearch client configuration and connection utilities."""

import os
import hashlib
import json
from functools import lru_cache
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY CACHING - Reduce repeated ES queries
# ═══════════════════════════════════════════════════════════════════════════════

class QueryCache:
    """
    Simple in-memory cache for Elasticsearch query results.

    Caches query results for a configurable TTL to reduce load on ES
    and improve response times for repeated queries.
    """

    def __init__(self, default_ttl_seconds: int = 60):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl_seconds

    def _make_key(self, query_type: str, **kwargs) -> str:
        """Generate a cache key from query parameters."""
        # Sort kwargs for consistent key generation
        sorted_params = json.dumps(kwargs, sort_keys=True, default=str)
        key_string = f"{query_type}:{sorted_params}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, query_type: str, **kwargs) -> Optional[Any]:
        """
        Get cached result if available and not expired.

        Args:
            query_type: Type of query (e.g., 'error_frequency', 'search_logs')
            **kwargs: Query parameters used to generate cache key

        Returns:
            Cached result or None if not found/expired
        """
        key = self._make_key(query_type, **kwargs)
        entry = self._cache.get(key)

        if entry is None:
            return None

        if datetime.utcnow() > entry["expires"]:
            del self._cache[key]
            return None

        return entry["data"]

    def set(self, query_type: str, data: Any, ttl_seconds: int = None, **kwargs):
        """
        Cache a query result.

        Args:
            query_type: Type of query
            data: Result data to cache
            ttl_seconds: Time to live in seconds (uses default if not specified)
            **kwargs: Query parameters used to generate cache key
        """
        key = self._make_key(query_type, **kwargs)
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl

        self._cache[key] = {
            "data": data,
            "expires": datetime.utcnow() + timedelta(seconds=ttl),
            "created": datetime.utcnow(),
        }

    def invalidate(self, query_type: str = None, **kwargs):
        """
        Invalidate cached entries.

        Args:
            query_type: If provided with kwargs, invalidates specific entry.
                       If only query_type, invalidates all entries of that type.
                       If neither, clears entire cache.
            **kwargs: Query parameters for specific entry invalidation
        """
        if query_type and kwargs:
            key = self._make_key(query_type, **kwargs)
            self._cache.pop(key, None)
        elif query_type:
            # Remove all entries starting with this query type
            keys_to_remove = [k for k in self._cache.keys()]
            for key in keys_to_remove:
                # Note: This is a simple approach; could be optimized with prefix storage
                self._cache.pop(key, None)
        else:
            self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        valid_entries = sum(1 for e in self._cache.values() if e["expires"] > now)
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
        }


# Global cache instance
_query_cache = QueryCache(default_ttl_seconds=60)


def get_query_cache() -> QueryCache:
    """Get the global query cache instance."""
    return _query_cache


def cached_query(query_type: str, ttl_seconds: int = 60):
    """
    Decorator for caching query function results.

    Usage:
        @cached_query("error_frequency", ttl_seconds=30)
        def get_error_frequency(client, time_range, ...):
            ...

    Args:
        query_type: Identifier for this query type
        ttl_seconds: Cache TTL in seconds
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_query_cache()

            # Create cache key from kwargs (skip client argument)
            cache_kwargs = {k: v for k, v in kwargs.items() if k != 'client'}

            # Check cache
            cached_result = cache.get(query_type, **cache_kwargs)
            if cached_result is not None:
                return cached_result

            # Execute query
            result = func(*args, **kwargs)

            # Cache result
            cache.set(query_type, result, ttl_seconds=ttl_seconds, **cache_kwargs)

            return result
        return wrapper
    return decorator


def get_elasticsearch_client() -> Elasticsearch:
    """
    Create and return an Elasticsearch client based on environment configuration.

    Supports three authentication methods:
    1. API Key (recommended for production)
    2. Cloud ID with API Key
    3. Username/Password

    Returns:
        Elasticsearch: Configured Elasticsearch client

    Raises:
        ValueError: If required configuration is missing
    """
    # Check for Cloud ID first (Elastic Cloud deployment)
    cloud_id = os.getenv("ELASTICSEARCH_CLOUD_ID")
    api_key = os.getenv("ELASTICSEARCH_API_KEY")
    url = os.getenv("ELASTICSEARCH_URL")
    username = os.getenv("ELASTICSEARCH_USERNAME")
    password = os.getenv("ELASTICSEARCH_PASSWORD")

    # Option 1: Cloud ID with API Key (Elastic Cloud)
    if cloud_id and api_key:
        return Elasticsearch(
            cloud_id=cloud_id,
            api_key=api_key,
            request_timeout=30,
        )

    # Option 2: URL with API Key
    if url and api_key:
        return Elasticsearch(
            hosts=[url],
            api_key=api_key,
            request_timeout=30,
        )

    # Option 3: URL with username/password
    if url and username and password:
        return Elasticsearch(
            hosts=[url],
            basic_auth=(username, password),
            request_timeout=30,
        )

    raise ValueError(
        "Missing Elasticsearch configuration. Please set either:\n"
        "1. ELASTICSEARCH_CLOUD_ID + ELASTICSEARCH_API_KEY, or\n"
        "2. ELASTICSEARCH_URL + ELASTICSEARCH_API_KEY, or\n"
        "3. ELASTICSEARCH_URL + ELASTICSEARCH_USERNAME + ELASTICSEARCH_PASSWORD"
    )


def verify_connection(client: Optional[Elasticsearch] = None) -> bool:
    """
    Verify the Elasticsearch connection is working.

    Args:
        client: Optional Elasticsearch client. If not provided, creates one.

    Returns:
        bool: True if connection is successful

    Raises:
        ConnectionError: If connection fails
    """
    if client is None:
        client = get_elasticsearch_client()

    try:
        info = client.info()
        print(f"Connected to Elasticsearch cluster: {info['cluster_name']}")
        print(f"Elasticsearch version: {info['version']['number']}")
        return True
    except Exception as e:
        raise ConnectionError(f"Failed to connect to Elasticsearch: {e}")


def get_index_settings() -> dict:
    """Get default index settings from environment or use defaults."""
    return {
        "log_index_pattern": os.getenv("LOG_INDEX_PATTERN", "logs-*"),
        "investigation_index": os.getenv("INVESTIGATION_INDEX", "investigations"),
    }


# Index names as constants
LOG_INDEX = "logs-logsleuth"
INVESTIGATION_INDEX = "investigations-logsleuth"


def get_available_services(client: Elasticsearch) -> list:
    """
    Dynamically get the list of available services from Elasticsearch.

    This allows the agent to know what services exist without hardcoding.

    Args:
        client: Elasticsearch client

    Returns:
        List of service names found in the logs index
    """
    try:
        result = client.search(
            index=LOG_INDEX,
            body={
                "size": 0,
                "aggs": {
                    "services": {
                        "terms": {
                            "field": "service.name.keyword",
                            "size": 50
                        }
                    }
                }
            }
        )

        services = [
            bucket["key"]
            for bucket in result["aggregations"]["services"]["buckets"]
        ]
        return services
    except Exception:
        # Fallback to known services if query fails
        return [
            "api-gateway",
            "user-service",
            "checkout-service",
            "payment-service",
            "inventory-service",
        ]


def get_error_types(client: Elasticsearch, time_range_hours: int = 24) -> list:
    """
    Dynamically get the list of error types from recent logs.

    Args:
        client: Elasticsearch client
        time_range_hours: How far back to look for error types

    Returns:
        List of error type names found in recent error logs
    """
    try:
        result = client.search(
            index=LOG_INDEX,
            body={
                "size": 0,
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"log.level.keyword": "error"}},
                            {"range": {"@timestamp": {"gte": f"now-{time_range_hours}h"}}}
                        ]
                    }
                },
                "aggs": {
                    "error_types": {
                        "terms": {
                            "field": "error.type.keyword",
                            "size": 50
                        }
                    }
                }
            }
        )

        error_types = [
            bucket["key"]
            for bucket in result["aggregations"]["error_types"]["buckets"]
        ]
        return error_types
    except Exception:
        return []
