"""Streamlit Master UI main application."""

from __future__ import annotations

import os

import streamlit as st

from streamlit_ui.config import Config
from streamlit_ui.utils.caching import get_config


def main() -> None:
    """Main Streamlit app entry point."""
    st.set_page_config(
        page_title="FineTuning Envelope Master",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state
    if "config" not in st.session_state:
        st.session_state.config = get_config()

    if "api_token" not in st.session_state:
        st.session_state.api_token = os.getenv("MASTER_API_TOKEN", "")

    # Sidebar navigation
    st.sidebar.title("FineTuning Envelope")
    st.sidebar.write("Master Lineage UI v0.1")

    page = st.sidebar.radio(
        "Navigate",
        [
            "Recipes",
            "Models",
            "Components",
            "Experiments",
            "Health Check",
        ],
    )

    # Dynamic page loading
    if page == "Recipes":
        from pages import recipes

        recipes.run()
    elif page == "Models":
        from pages import models

        models.run()
    elif page == "Components":
        from pages import components

        components.run()
    elif page == "Experiments":
        from pages import experiments

        experiments.run()
    elif page == "Health Check":
        from pages import health_check

        health_check.run()

    # Footer
    st.sidebar.divider()
    st.sidebar.caption(f"API: {st.session_state.config.master_api_url}")
    st.sidebar.caption(f"Neo4j: {st.session_state.config.neo4j_uri}")


if __name__ == "__main__":
    main()
