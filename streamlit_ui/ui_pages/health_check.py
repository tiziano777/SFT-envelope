"""Health check page."""

from __future__ import annotations

import streamlit as st

from streamlit_ui.utils import get_api_client, get_neo4j_client


def run() -> None:
    """Run health check page."""
    st.title("Health Check")

    try:
        api = get_api_client()
        db = get_neo4j_client()

        # Simple connectivity checks
        st.subheader("API")
        st.write(f"Base URL: {api.base_url}")

        st.subheader("Neo4j")
        st.write(f"URI: {db.uri}")

        st.success("Connections objects available (see detailed logs for runtime checks).")
    except Exception as e:
        st.error(f"Health check error: {str(e)}")
