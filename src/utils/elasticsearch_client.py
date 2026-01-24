"""Elasticsearch client configuration and connection utilities."""

import os
from typing import Optional
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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
