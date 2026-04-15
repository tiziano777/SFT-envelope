"""Recipe management page."""

from __future__ import annotations

import asyncio

import streamlit as st

from streamlit_ui.crud import RecipeManager
from streamlit_ui.errors import UIError
from streamlit_ui.utils import get_api_client, get_neo4j_client
from streamlit_ui.validation import validate_recipe_yaml


# Async helper functions for recipe operations
async def create_recipe_async(name: str, yaml_content: str, description: str = "") -> dict:
    """Create recipe asynchronously."""
    db_client = get_neo4j_client()
    api_client = get_api_client()
    manager = RecipeManager(db_client, api_client)
    return await manager.create_recipe(name=name, yaml_content=yaml_content, description=description)


async def search_recipes_async(query: str) -> list[dict]:
    """Search recipes asynchronously."""
    db_client = get_neo4j_client()
    api_client = get_api_client()
    manager = RecipeManager(db_client, api_client)
    return await manager.search_recipes(query)


async def list_recipes_async(limit: int = 20) -> list[dict]:
    """List recipes asynchronously."""
    db_client = get_neo4j_client()
    api_client = get_api_client()
    manager = RecipeManager(db_client, api_client)
    return await manager.list_recipes(limit=limit)


async def update_recipe_async(recipe_id: str, description: str = "", tags: list[str] | None = None) -> dict:
    """Update recipe asynchronously."""
    db_client = get_neo4j_client()
    api_client = get_api_client()
    manager = RecipeManager(db_client, api_client)
    return await manager.update_recipe(recipe_id, description=description, tags=tags)


async def delete_recipe_async(recipe_id: str) -> None:
    """Delete recipe asynchronously."""
    db_client = get_neo4j_client()
    api_client = get_api_client()
    manager = RecipeManager(db_client, api_client)
    await manager.delete_recipe(recipe_id)


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
                is_valid, config, errors = validate_recipe_yaml(yaml_content, filename=uploaded_file.name)

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
                            st.toast("Recipe saved!", icon="✅")
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
        st.subheader("Browse & Manage Recipes")

        search_query = st.text_input("Search by name", value="", key="search_recipes")

        try:
            if search_query.strip():
                recipes = asyncio.run(search_recipes_async(search_query))
                st.caption(f"Found {len(recipes)} recipe(s)")
            else:
                recipes = asyncio.run(list_recipes_async(limit=20))

            if recipes:
                for recipe in recipes:
                    key_suffix = recipe.get("id") if recipe.get("id") is not None else recipe.get("name")
                    with st.expander(f"📋 {recipe.get('name', 'N/A')}", expanded=False):
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.write(f"**Description:** {recipe.get('description', 'N/A')}")
                            st.caption(f"Created: {recipe.get('created_at', 'N/A')}")

                            # Display recipe entries
                            entries = recipe.get("entries")
                            if entries and isinstance(entries, dict):
                                st.divider()
                                st.subheader("📊 Dataset Entries")
                                for dist_uri, entry in entries.items():
                                    if isinstance(entry, dict):
                                        cols = st.columns([2, 1, 1, 1, 1])
                                        with cols[0]:
                                            st.caption(f"📁 {entry.get('dist_id', 'N/A')}")
                                        with cols[1]:
                                            st.caption(f"📈 {entry.get('samples', 'N/A')}")
                                        with cols[2]:
                                            st.caption(f"🔤 {entry.get('tokens', 'N/A')}")
                                        with cols[3]:
                                            st.caption(f"📝 {entry.get('words', 'N/A')}")
                                        with cols[4]:
                                            st.caption(f"✅ {entry.get('dist_name', 'N/A')[:15]}")
                                        st.caption(f"URI: `{dist_uri}`")
                            else:
                                st.info("No entries in this recipe")

                        with col2:
                            if st.button("✏️ Edit", key=f"edit_{key_suffix}"):
                                st.session_state[f"edit_recipe_{key_suffix}"] = True

                            if st.button("🗑️ Delete", key=f"delete_{key_suffix}"):
                                st.session_state[f"confirm_delete_{key_suffix}"] = True

                        if st.session_state.get(f"edit_recipe_{key_suffix}", False):
                            st.divider()
                            st.subheader("Edit Recipe")
                            new_desc = st.text_area("Description", value=recipe.get('description', ''), key=f"new_desc_{key_suffix}")

                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.button("Save Changes", key=f"save_edit_{key_suffix}"):
                                    try:
                                        result = asyncio.run(update_recipe_async(
                                            recipe.get('id'),
                                            description=new_desc
                                        ))
                                        st.success(f"✓ Recipe updated!")
                                        st.session_state[f"edit_recipe_{key_suffix}"] = False
                                        st.rerun()
                                    except UIError as e:
                                        st.error(f"Error: {e.user_message}")

                            with col_cancel:
                                if st.button("Cancel", key=f"cancel_edit_{key_suffix}"):
                                    st.session_state[f"edit_recipe_{key_suffix}"] = False
                                    st.rerun()

                        if st.session_state.get(f"confirm_delete_{key_suffix}", False):
                            st.divider()
                            st.warning(f"⚠️ Are you sure you want to delete '{recipe.get('name')}'?")
                            col_confirm, col_cancel = st.columns(2)

                            with col_confirm:
                                if st.button("Yes, delete", key=f"confirm_delete_yes_{key_suffix}", type="primary"):
                                    try:
                                        asyncio.run(delete_recipe_async(recipe.get('id')))
                                        st.success(f"✓ Recipe '{recipe.get('name')}' deleted!")
                                        st.session_state[f"confirm_delete_{key_suffix}"] = False
                                        st.rerun()
                                    except UIError as e:
                                        st.error(f"Error: {e.user_message}")

                            with col_cancel:
                                if st.button("Cancel", key=f"cancel_delete_{key_suffix}"):
                                    st.session_state[f"confirm_delete_{key_suffix}"] = False
                                    st.rerun()
            else:
                st.info("No recipes found.")
        except UIError as e:
            st.error(f"Error: {e.user_message}")
            st.caption(e.details)
