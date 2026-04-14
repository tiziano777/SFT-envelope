"""Health check page."""

from __future__ import annotations

import asyncio

import streamlit as st

from streamlit_ui.health import (
    check_master_api_health,
    check_neo4j_health,
    check_streamlit_health,
)
from streamlit_ui.utils.caching import get_api_client, get_config, get_neo4j_client


# Async helper functions for health checks
async def check_neo4j_async() -> bool:
    """Check Neo4j health asynchronously."""
    db_client = await get_neo4j_client()
    return await check_neo4j_health(db_client)


async def check_api_async() -> bool:
    """Check Master API health asynchronously."""
    api_client = await get_api_client()
    config = get_config()
    return await check_master_api_health(config.master_api_url, config.master_api_token)


def run() -> None:
    """Run health check page."""
    st.title("Health Check")

    config = get_config()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Neo4j")
        try:
            health = asyncio.run(check_neo4j_async())
            if health:
                st.success("✓ Connected")
            else:
                st.error("✗ Failed")
        except Exception as e:
            st.error(f"✗ {str(e)}")

    with col2:
        st.subheader("Master API")
        try:
            health = asyncio.run(check_api_async())
            if health:
                st.success("✓ Connected")
            else:
                st.error("✗ Failed")
        except Exception as e:
            st.error(f"✗ {str(e)}")

    with col3:
        st.subheader("Streamlit")
        try:
            health = check_streamlit_health()
            if health:
                st.success("✓ Running")
            else:
                st.error("✗ Failed")
        except Exception as e:
            st.error(f"✗ {str(e)}")

    st.divider()
    st.subheader("Configuration")
    st.info(f"**Neo4j URI:** {config.neo4j_uri}")
    st.info(f"**Master API:** {config.master_api_url}")

