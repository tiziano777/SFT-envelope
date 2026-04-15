"""Streamlit Master UI main application."""

from __future__ import annotations

import asyncio
import atexit
import os

import streamlit as st

from streamlit_ui.utils import get_api_client, get_config, get_neo4j_client


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

    # Ensure Neo4j constraints exist (only happens once per session)
    if "neo4j_constraints_created" not in st.session_state:
        try:
            db_client = get_neo4j_client()
            asyncio.run(db_client.ensure_recipe_constraints())
            st.session_state.neo4j_constraints_created = True
        except Exception as e:
            # Log warning but don't fail if constraint setup fails
            st.warning(f"Could not ensure Neo4j constraints: {e}")

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
