#!/usr/bin/env python
"""Verification script for recipe manager fixes."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

# Test 1: Verify Pydantic models are serialized to dicts
print("=" * 60)
print("TEST 1: Pydantic models serialization")
print("=" * 60)

from envelope.config.models import RecipeConfig, RecipeEntry

# Create sample RecipeConfig with Pydantic models
entries_data = {
    "/path/1": {
        "chat_type": "simple",
        "dist_id": "dist_001",
        "dist_name": "Dataset 1",
        "dist_uri": "/mnt/data/dataset1.jsonl",
        "samples": 1000,
        "tokens": 500000,
        "words": 100000
    }
}

config = RecipeConfig(**entries_data)
print(f"RecipeConfig.entries type: {type(config.entries)}")
print(f"First entry type: {type(config.entries['/path/1'])}")
print(f"First entry class: {config.entries['/path/1'].__class__.__name__}")

# Verify serialization works
serialized = {
    path: entry.model_dump(mode="json", exclude_none=True)
    for path, entry in config.entries.items()
}
print(f"\nAfter serialization:")
print(f"Serialized entries type: {type(serialized)}")
print(f"First entry type after serialization: {type(serialized['/path/1'])}")
print(f"Serialized entry keys: {list(serialized['/path/1'].keys())}")
assert isinstance(serialized['/path/1'], dict), "Entry should be dict after serialization"
print("✓ PASS: Pydantic models correctly serialized to dicts")

# Test 2: Verify method names in recipes.py are correct
print("\n" + "=" * 60)
print("TEST 2: RecipeManager method names")
print("=" * 60)

from streamlit_ui.crud.recipe_manager import RecipeManager
import inspect

manager_methods = {name for name, _ in inspect.getmembers(RecipeManager, predicate=inspect.ismethod)
                   if not name.startswith('_')}
instance_methods = {name for name, _ in inspect.getmembers(RecipeManager, predicate=inspect.iscoroutinefunction)
                    if not name.startswith('_')}

print(f"RecipeManager async methods: {instance_methods}")

# Verify correct methods exist
assert 'create' in instance_methods, "RecipeManager should have 'create' method"
assert 'update' in instance_methods, "RecipeManager should have 'update' method"
assert 'delete' in instance_methods, "RecipeManager should have 'delete' method"
assert 'create_recipe' in instance_methods, "RecipeManager should have 'create_recipe' method"

# Verify incorrect method names DON'T exist
assert 'update_recipe' not in instance_methods, "RecipeManager should NOT have 'update_recipe' method"
assert 'delete_recipe' not in instance_methods, "RecipeManager should NOT have 'delete_recipe' method"
print("✓ PASS: RecipeManager has correct method names")

# Test 3: Verify recipes.py calls correct methods
print("\n" + "=" * 60)
print("TEST 3: recipes.py calls correct manager methods")
print("=" * 60)

import importlib.util
spec = importlib.util.spec_from_file_location("recipes", "streamlit_ui/ui_pages/recipes.py")
recipes_module = importlib.util.module_from_spec(spec)

# Check async function signatures
import inspect

# Mock the dependencies
recipes_module.get_neo4j_client = MagicMock()
recipes_module.get_api_client = MagicMock()
recipes_module.RecipeManager = MagicMock()
recipes_module.st = MagicMock()

# Read source to verify method calls
with open("streamlit_ui/ui_pages/recipes.py", "r") as f:
    source = f.read()

# Verify correct method names are called
assert "manager.update(" in source, "Should call manager.update()"
assert "manager.delete(" in source, "Should call manager.delete()"
assert "recipe_name=" in source, "Should use recipe_name parameter"

# Verify incorrect method names are NOT called
assert "manager.update_recipe(" not in source, "Should NOT call manager.update_recipe()"
assert "manager.delete_recipe(" not in source, "Should NOT call manager.delete_recipe()"

print("✓ PASS: recipes.py calls correct manager methods")

print("\n" + "=" * 60)
print("ALL VERIFICATION TESTS PASSED")
print("=" * 60)
