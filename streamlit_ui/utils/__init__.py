"""Caching utilities for Streamlit UI."""

from __future__ import annotations

import streamlit as st

from streamlit_ui.api_client import HTTPXClient
from streamlit_ui.config import Config
from streamlit_ui.neo4j_async import AsyncNeo4jClient


@st.cache_resource
def get_config() -> Config:
    """Get or cache Config instance (non-async)."""
    return Config()


@st.cache_async
async def get_neo4j_client() -> AsyncNeo4jClient:
    """Get or cache AsyncNeo4jClient instance with connection pool management.

    Returns:
        AsyncNeo4jClient: Cached async Neo4j client instance.

    Note:
        Cleanup is handled by app.py atexit handler on process exit.
    """
    config = get_config()
    return AsyncNeo4jClient(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password,
    )


@st.cache_async
async def get_api_client() -> HTTPXClient:
    """Get or cache HTTPXClient instance with connection pool management.

    Returns:
        HTTPXClient: Cached async HTTP client instance.

    Note:
        Cleanup is handled by app.py atexit handler on process exit.
    """
    config = get_config()
    return HTTPXClient(
        base_url=config.master_api_url,
        api_token=config.master_api_token,
    )

