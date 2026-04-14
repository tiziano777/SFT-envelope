"""Recipe management page."""

from __future__ import annotations

import asyncio

import streamlit as st

from streamlit_ui.crud import RecipeManager
from streamlit_ui.errors import UIError
from streamlit_ui.utils.caching import get_api_client, get_neo4j_client
from streamlit_ui.validation import validate_recipe_yaml


# Async helper functions for recipe operations
async def create_recipe_async(name: str, yaml_content: str) -> dict:
    """Create recipe asynchronously."""
    db_client = await get_neo4j_client()
    api_client = await get_api_client()
    manager = RecipeManager(db_client, api_client)
    return await manager.create_recipe(name=name, yaml_content=yaml_content)


async def search_recipes_async(query: str) -> list[dict]:
    """Search recipes asynchronously."""
    db_client = await get_neo4j_client()
    api_client = await get_api_client()
    manager = RecipeManager(db_client, api_client)
    return await manager.search_recipes(query)


async def list_recipes_async(limit: int = 20) -> list[dict]:
    """List recipes asynchronously."""
    db_client = await get_neo4j_client()
    api_client = await get_api_client()
    manager = RecipeManager(db_client, api_client)
    return await manager.list_recipes(limit=limit)


def run() -> None:
    """Run recipe management page."""
    st.title("Recipe Management")

    tab1, tab2 = st.tabs(["Upload", "Browse"])

    with tab1:
        st.subheader("Upload YAML Recipe")

        uploaded_file = st.file_uploader("Upload YAML recipe", type=["yaml", "yml"])

        if uploaded_file:
            MAX_FILE_SIZE_MB = 10
            if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                st.error(f"File too large. Max {MAX_FILE_SIZE_MB}MB allowed.")
            else:
                yaml_content = uploaded_file.read().decode("utf-8")
                is_valid, config, errors = validate_recipe_yaml(yaml_content)

                if is_valid:
                    st.success("✓ Recipe validation passed")
                    st.info(f"**Name:** {config.name if config else 'N/A'}")

                    if st.button("Save Recipe", disabled=st.session_state.get("saving_recipe", False)):
                        st.session_state.saving_recipe = True
                        try:
                            result = asyncio.run(
                                create_recipe_async(
                                    name=getattr(config, "name", uploaded_file.name),
                                    yaml_content=yaml_content,
                                )
                            )
                            st.success(f"✓ Recipe '{result['name']}' created successfully!")
                            st.toast("Recipe saved!", icon="✓")
                        except UIError as e:
                            st.error(f"Error: {e.user_message}")
                            st.caption(e.details)
                        finally:
                            st.session_state.saving_recipe = False
                else:
                    st.error("✗ Recipe validation failed")
                    for error in errors:
                        st.error(f"  • {error}")

    with tab2:
        st.subheader("Browse Recipes")

        search_query = st.text_input("Search by name", value="")

        try:
            if search_query.strip():
                recipes = asyncio.run(search_recipes_async(search_query))
                st.caption(f"Found {len(recipes)} recipe(s)")
            else:
                recipes = asyncio.run(list_recipes_async(limit=20))

            if recipes:
                cols = st.columns(3)
                for idx, recipe in enumerate(recipes):
                    with cols[idx % 3]:
                        with st.container(border=True):
                            st.write(f"**{recipe.get('name', 'N/A')}**")
                            st.caption(f"Created: {recipe.get('created_at', 'N/A')}")
                            if st.button("View", key=f"view_{recipe['id']}"):
                                st.info(f"**ID:** {recipe['id']}")
                                st.write(f"**Description:** {recipe.get('description', 'N/A')}")
            else:
                st.info("No recipes found.")
        except UIError as e:
            st.error(f"Error: {e.user_message}")
            st.caption(e.details)

