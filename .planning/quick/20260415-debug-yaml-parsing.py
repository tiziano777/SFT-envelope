#!/usr/bin/env python3
"""Debug YAML parsing issue for recipes."""

import yaml
from pathlib import Path

# Test 1: Load actual user YAML
yaml_file = Path("/Users/T.Finizzi/Downloads/r1_recipe.yaml")
yaml_content = yaml_file.read_text()

print("=" * 60)
print("TEST 1: YAML Raw Content")
print("=" * 60)
data = yaml.safe_load(yaml_content)
print(f"Type: {type(data)}")
print(f"Keys: {list(data.keys())}")
print(f"Structure: {data}\n")

# Test 2: Try RecipeConfig parsing with user's format
print("=" * 60)
print("TEST 2: RecipeConfig Parsing with User Format (Expected to FAIL)")
print("=" * 60)
try:
    from envelope.config.models import RecipeConfig

    config = RecipeConfig(**data)
    print(f"✓ Parsing succeeded (unexpected!)")
    print(f"  - name: {config.name}")
    print(f"  - entries: {len(config.entries)} items")
    print(f"  - entries keys: {list(config.entries.keys())}")
except Exception as e:
    print(f"✗ Parsing FAILED (expected):")
    print(f"  Error type: {type(e).__name__}")
    print(f"  Error: {e}\n")

# Test 3: Try with wrapped format (expected correct format)
print("=" * 60)
print("TEST 3: RecipeConfig with Wrapped Format (Expected to SUCCEED)")
print("=" * 60)
wrapped_data = {
    "name": "r1_recipe",
    "entries": data  # Original data becomes entries
}
try:
    config = RecipeConfig(**wrapped_data)
    print(f"✓ Parsing succeeded!")
    print(f"  - name: {config.name}")
    print(f"  - entries: {len(config.entries)} items")
    for path, entry in config.entries.items():
        print(f"    - {path[:50]}... → samples={entry.samples}, tokens={entry.tokens}")
except Exception as e:
    print(f"✗ Parsing FAILED:")
    print(f"  Error: {e}\n")

# Test 4: Check what happens with current create_recipe implementation
print("=" * 60)
print("TEST 4: Simulate Current create_recipe() Flow")
print("=" * 60)
import asyncio
from streamlit_ui.crud.recipe_manager import RecipeManager

async def test_create():
    from streamlit_ui.neo4j_async import AsyncNeo4jClient
    from streamlit_ui.api_client import HTTPXClient

    # Create manager with test clients
    db = AsyncNeo4jClient()
    api = HTTPXClient(base_url="http://master-api:8000")
    manager = RecipeManager(db, api)

    try:
        result = await manager.create_recipe(
            name="r1_recipe_test",
            yaml_content=yaml_content
        )
        print(f"✓ create_recipe() succeeded:")
        print(f"  - name: {result.get('name')}")
        print(f"  - entries: {result.get('entries')}")
    except Exception as e:
        print(f"✗ create_recipe() failed:")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Error: {e}")

print("Running async test...")
try:
    asyncio.run(test_create())
except Exception as e:
    print(f"Async test failed: {e}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
The issue is that the YAML format doesn't match RecipeConfig expectations.

**User's YAML format:**
/path1:
  chat_type: ...
  dist_id: ...

**Expected format:**
name: my_recipe
entries:
  /path1:
    chat_type: ...
    dist_id: ...

The create_recipe() method tries to parse user's YAML directly into RecipeConfig,
which fails because there's no 'entries' key. The exception is caught but the
error is silent in Streamlit.

**SOLUTION:**
Enhance create_recipe() to auto-detect and wrap URI-based YAML format.
""")
