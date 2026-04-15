"""Streamlit Master UI main application."""

from __future__ import annotations

import asyncio
import atexit
import os
from pathlib import Path

import streamlit as st

from streamlit_ui.utils import get_api_client, get_config, get_neo4j_client


async def ensure_schema_initialized() -> None:
    """Execute Neo4j DDL schema initialization script (idempotent).

    Runs CREATE CONSTRAINT ... IF NOT EXISTS commands from database/schema_init.cypher.
    Safe to call multiple times; subsequent runs are no-ops if constraints exist.
    """
    try:
        db_client = get_neo4j_client()
        # Read and execute schema_init.cypher
        schema_file = Path(__file__).parent.parent / "database" / "schema_init.cypher"
        if not schema_file.exists():
            st.warning(f"Schema file not found: {schema_file}")
            return

        with open(schema_file) as f:
            cypher_commands = f.read()

        # Split by semicolon and execute each command
        for command in cypher_commands.split(";"):
            command = command.strip()
            if command and not command.startswith("//"):
                await db_client.run(command)

        st.session_state.schema_initialized = True
    except Exception as e:
        st.warning(f"Schema initialization warning (non-fatal): {e}")


def main() -> None:
    """Main Streamlit app entry point."""
    st.set_page_config(
        page_title="FineTuning Envelope Master",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Register cleanup handler once per session
    if "cleanup_registered" not in st.session_state:
        atexit.register(cleanup_resources)
        st.session_state.cleanup_registered = True

    # Initialize session state
    if "config" not in st.session_state:
        st.session_state.config = get_config()

    if "api_token" not in st.session_state:
        st.session_state.api_token = os.getenv("MASTER_API_TOKEN", "")

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Recipes"

    # Initialize Neo4j schema (only happens once per session)
    if "schema_initialized" not in st.session_state:
        asyncio.run(ensure_schema_initialized())

    # Sidebar navigation
    st.sidebar.title("FineTuning Envelope")
    

    # Page selection with session state
    page_options = [
        "Recipes",
        "Models",
        "Experiments",
        "Components",
        "Health Check",
    ]

    page = st.sidebar.radio(
        "Navigate",
        page_options,
        index=page_options.index(st.session_state.current_page),
    )

    # Update session state when page changes
    st.session_state.current_page = page

    # Dynamic page loading
    try:
        if page == "Recipes":
            from ui_pages import recipes
            recipes.run()
        elif page == "Models":
            from ui_pages import models
            models.run()
        elif page == "Experiments":
            from ui_pages import experiments
            experiments.run()
        elif page == "Components":
            from ui_pages import components
            components.run()
        elif page == "Health Check":
            from ui_pages import health_check
            health_check.run()
    except Exception as e:
        st.error(f"Error loading page: {str(e)}")
        st.exception(e)

    # Footer
    st.sidebar.divider()
    st.sidebar.caption(f"API: {st.session_state.config.master_api_url}")
    st.sidebar.caption(f"Neo4j: {st.session_state.config.neo4j_uri}")


def cleanup_resources() -> None:
    """Cleanup database and API connections on app exit.

    Called via atexit handler to ensure resources are released when the Streamlit
    process terminates. This prevents connection pool exhaustion and ensures
    proper shutdown of async clients.
    """
    try:
        api_client = get_api_client()
        db_client = get_neo4j_client()

        # Create a temporary event loop for cleanup (we're in shutdown phase)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Close both clients gracefully
        loop.run_until_complete(api_client.close())
        loop.run_until_complete(db_client.close())

        loop.close()
    except Exception:
        # Silently ignore errors during shutdown - don't raise exceptions in teardown
        pass


if __name__ == "__main__":
    main()
