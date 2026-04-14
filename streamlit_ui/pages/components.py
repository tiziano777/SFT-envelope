"""Component management page."""

from __future__ import annotations

import asyncio
import logging

import streamlit as st

from streamlit_ui.crud.component_manager import ComponentManager
from streamlit_ui.errors import DeleteProtectionError, UIError
from streamlit_ui.utils.caching import get_api_client, get_neo4j_client

logger = logging.getLogger(__name__)


# Async helper functions
async def create_component_async(
    opt_code: str, technique_code: str, framework_code: str, docs_url: str, description: str
) -> dict:
    """Create component asynchronously."""
    db_client = await get_neo4j_client()
    api_client = await get_api_client()
    manager = ComponentManager(db_client, api_client)
    return await manager.create_component(
        opt_code=opt_code,
        technique_code=technique_code,
        framework_code=framework_code,
        docs_url=docs_url,
        description=description,
    )


async def list_components_async() -> list[dict]:
    """List components asynchronously."""
    db_client = await get_neo4j_client()
    api_client = await get_api_client()
    manager = ComponentManager(db_client, api_client)
    return await manager.list_components()


async def get_component_async(comp_id: str) -> dict:
    """Get component asynchronously."""
    db_client = await get_neo4j_client()
    api_client = await get_api_client()
    manager = ComponentManager(db_client, api_client)
    return await manager.get_component(comp_id)


async def update_component_async(comp_id: str, docs_url: str, description: str) -> None:
    """Update component asynchronously."""
    db_client = await get_neo4j_client()
    api_client = await get_api_client()
    manager = ComponentManager(db_client, api_client)
    await manager.update_component(comp_id, docs_url=docs_url, description=description)


async def check_component_deps_async(comp_id: str) -> int:
    """Check component dependencies asynchronously."""
    db_client = await get_neo4j_client()
    api_client = await get_api_client()
    manager = ComponentManager(db_client, api_client)
    return await manager.check_component_dependencies(comp_id)


async def delete_component_async(comp_id: str) -> None:
    """Delete component asynchronously."""
    db_client = await get_neo4j_client()
    api_client = await get_api_client()
    manager = ComponentManager(db_client, api_client)
    await manager.delete_component(comp_id)


def run() -> None:
    """Run component management page."""
    st.title("Component Management")

    tab_create, tab_browse, tab_edit, tab_delete = st.tabs(["Create", "Browse", "Edit", "Delete"])

    with tab_create:
        st.subheader("Create New Component")
        with st.form("create_component_form"):
            opt_code = st.text_input("Optimization Code", placeholder="lora")
            technique_code = st.text_input("Technique Code", placeholder="lora_grpo")
            framework_code = st.text_input("Framework Code", placeholder="unsloth")
            docs_url = st.text_input("Documentation URL", value="")
            description = st.text_area("Description", value="")
            submitted = st.form_submit_button("Create Component")

            if submitted:
                if not all([opt_code.strip(), technique_code.strip(), framework_code.strip()]):
                    st.error("All code fields are required")
                else:
                    try:
                        result = asyncio.run(
                            create_component_async(
                                opt_code=opt_code,
                                technique_code=technique_code,
                                framework_code=framework_code,
                                docs_url=docs_url,
                                description=description,
                            )
                        )
                        st.success(f"✓ Component '{result['opt_code']}' created successfully!")
                        st.toast("Component created!", icon="✓")
                    except UIError as e:
                        st.error(f"Error: {e.user_message}")
                    except asyncio.TimeoutError:
                        st.error("Request timed out. Please try again.")
                        logger.exception("Timeout in create_component")
                    except Exception as e:
                        st.error(f"Unexpected error: {str(e)}")
                        logger.exception("Uncaught exception in create_component")

    with tab_browse:
        st.subheader("Browse Components")
        try:
            components = asyncio.run(list_components_async())

            if components:
                for comp in components:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 2, 2])
                        with col1:
                            st.write(f"**{comp.get('opt_code', 'N/A')}**")
                        with col2:
                            st.caption(f"Technique: {comp.get('technique_code', 'N/A')}")
                        with col3:
                            st.caption(f"Framework: {comp.get('framework_code', 'N/A')}")
            else:
                st.info("No components found.")
        except UIError as e:
            st.error(f"Error: {e.user_message}")

    with tab_edit:
        st.subheader("Update Component")
        try:
            components = asyncio.run(list_components_async())
            comp_map = {f"{c['opt_code']} ({c['technique_code']})" : c["id"] for c in components}

            selected_comp = st.selectbox("Select Component", list(comp_map.keys()))

            if selected_comp:
                comp_id = comp_map[selected_comp]
                comp = asyncio.run(get_component_async(comp_id))

                with st.form("edit_component_form"):
                    docs_url = st.text_input("Doc URL", value=comp.get("docs_url", ""))
                    description = st.text_area("Description", value=comp.get("description", ""))
                    submitted = st.form_submit_button("Update Component")

                    if submitted:
                        try:
                            asyncio.run(
                                update_component_async(comp_id, docs_url=docs_url, description=description)
                            )
                            st.success("✓ Component updated!")
                        except UIError as e:
                            st.error(f"Error: {e.user_message}")
        except UIError as e:
            st.error(f"Error: {e.user_message}")

    with tab_delete:
        st.subheader("Delete Component")
        try:
            components = asyncio.run(list_components_async())
            comp_map = {f"{c['opt_code']} ({c['technique_code']})" : c["id"] for c in components}

            selected_comp = st.selectbox("Select Component to Delete", list(comp_map.keys()), key="delete")

            if selected_comp:
                comp_id = comp_map[selected_comp]

                try:
                    dep_count = asyncio.run(check_component_deps_async(comp_id))

                    if dep_count > 0:
                        st.warning(f"⚠️ This component is used by {dep_count} recipe(s). Cannot delete.")
                    else:
                        st.success("✓ No dependencies found. Safe to delete.")
                        confirm = st.checkbox(f"I confirm deletion of '{selected_comp}'")
                        if confirm and st.button("Delete Component"):
                            try:
                                asyncio.run(delete_component_async(comp_id))
                                st.success("✓ Component deleted!")
                            except UIError as e:
                                st.error(f"Error: {e.user_message}")
                except DeleteProtectionError as e:
                    st.error(f"Delete Protected: {e.user_message}")
        except UIError as e:
            st.error(f"Error: {e.user_message}")

    """Run component management page."""
    st.title("Component Management")

    db_client = get_neo4j_client()
    api_client = get_api_client()
    manager = ComponentManager(db_client, api_client)

    tab_create, tab_browse, tab_edit, tab_delete = st.tabs(["Create", "Browse", "Edit", "Delete"])

    with tab_create:
        st.subheader("Create New Component")
        with st.form("create_component_form"):
            opt_code = st.text_input("Optimization Code", placeholder="lora")
            technique_code = st.text_input("Technique Code", placeholder="lora_grpo")
            framework_code = st.text_input("Framework Code", placeholder="unsloth")
            docs_url = st.text_input("Documentation URL", value="")
            description = st.text_area("Description", value="")
            submitted = st.form_submit_button("Create Component")

            if submitted:
                if not all([opt_code.strip(), technique_code.strip(), framework_code.strip()]):
                    st.error("All code fields are required")
                else:
                    try:
                        result = asyncio.run(
                            manager.create_component(
                                opt_code=opt_code,
                                technique_code=technique_code,
                                framework_code=framework_code,
                                docs_url=docs_url,
                                description=description,
                            )
                        )
                        st.success(f"✓ Component '{result['opt_code']}' created successfully!")
                        st.toast("Component created!", icon="✓")
                    except UIError as e:
                        st.error(f"Error: {e.user_message}")
                    except asyncio.TimeoutError:
                        st.error("Request timed out. Please try again.")
                        logger.exception("Timeout in create_component")
                    except Exception as e:
                        st.error(f"Unexpected error: {str(e)}")
                        logger.exception("Uncaught exception in create_component")

    with tab_browse:
        st.subheader("Browse Components")
        try:
            components = asyncio.run(manager.list_components())

            if components:
                for comp in components:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 2, 2])
                        with col1:
                            st.write(f"**{comp.get('opt_code', 'N/A')}**")
                        with col2:
                            st.caption(f"Technique: {comp.get('technique_code', 'N/A')}")
                        with col3:
                            st.caption(f"Framework: {comp.get('framework_code', 'N/A')}")
            else:
                st.info("No components found.")
        except UIError as e:
            st.error(f"Error: {e.user_message}")

    with tab_edit:
        st.subheader("Update Component")
        try:
            components = asyncio.run(manager.list_components())
            comp_map = {f"{c['opt_code']} ({c['technique_code']})" : c["id"] for c in components}

            selected_comp = st.selectbox("Select Component", list(comp_map.keys()))

            if selected_comp:
                comp_id = comp_map[selected_comp]
                comp = asyncio.run(manager.get_component(comp_id))

                with st.form("edit_component_form"):
                    docs_url = st.text_input("Doc URL", value=comp.get("docs_url", ""))
                    description = st.text_area("Description", value=comp.get("description", ""))
                    submitted = st.form_submit_button("Update Component")

                    if submitted:
                        try:
                            asyncio.run(
                                manager.update_component(
                                    comp_id,
                                    docs_url=docs_url,
                                    description=description,
                                )
                            )
                            st.success("✓ Component updated!")
                        except UIError as e:
                            st.error(f"Error: {e.user_message}")
        except UIError as e:
            st.error(f"Error: {e.user_message}")

    with tab_delete:
        st.subheader("Delete Component")
        try:
            components = asyncio.run(manager.list_components())
            comp_map = {f"{c['opt_code']} ({c['technique_code']})" : c["id"] for c in components}

            selected_comp = st.selectbox("Select Component to Delete", list(comp_map.keys()), key="delete")

            if selected_comp:
                comp_id = comp_map[selected_comp]

                try:
                    dep_count = asyncio.run(manager.check_component_dependencies(comp_id))

                    if dep_count > 0:
                        st.warning(f"⚠️ This component is used by {dep_count} experiment(s). Cannot delete.")
                    else:
                        st.success("✓ No dependencies found. Safe to delete.")
                        confirm = st.checkbox(f"I confirm deletion of '{selected_comp}'")
                        if confirm and st.button("Delete Component"):
                            try:
                                asyncio.run(manager.delete_component(comp_id))
                                st.success("✓ Component deleted!")
                            except UIError as e:
                                st.error(f"Error: {e.user_message}")
                except DeleteProtectionError as e:
                    st.error(f"Delete Protected: {e.user_message}")
        except UIError as e:
            st.error(f"Error: {e.user_message}")
