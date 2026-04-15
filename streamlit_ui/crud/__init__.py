"""CRUD package exports for streamlit_ui.crud.

This module intentionally re-exports concrete manager implementations
from their dedicated modules. The functional implementations live in
`recipe_manager.py`, `component_manager.py`, `experiment_manager.py`,
and `model_manager.py`.

Consumers should import specific managers directly from their modules
or via this package, e.g. `from streamlit_ui.crud.recipe_manager import RecipeManager`
or `from streamlit_ui.crud import RecipeManager`.
"""

from __future__ import annotations

from .recipe_manager import RecipeManager
from .component_manager import ComponentManager
from .experiment_manager import ExperimentManager
from .model_manager import ModelManager

__all__ = [
    "RecipeManager",
    "ComponentManager",
    "ExperimentManager",
    "ModelManager",
]
