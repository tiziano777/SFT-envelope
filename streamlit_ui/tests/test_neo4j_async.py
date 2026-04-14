"""Tests for neo4j_async module."""

from __future__ import annotations

import pytest

from streamlit_ui.neo4j_async import AsyncNeo4jClient


@pytest.mark.asyncio
async def test_async_neo4j_client_init():
    """Test AsyncNeo4jClient initialization."""
    client = AsyncNeo4jClient(
        uri="neo4j://localhost:7687",
        user="neo4j",
        password="password",
    )
    assert client.uri == "neo4j://localhost:7687"
    assert client.user == "neo4j"
    await client.close()


@pytest.mark.asyncio
async def test_count_relationships_valid_labels():
    """Test that count_relationships accepts valid labels (security test)."""
    client = AsyncNeo4jClient(
        uri="neo4j://localhost:7687",
        user="neo4j",
        password="password",
    )

    # These should not raise ValueError (though they may fail at DB level)
    # The point is to verify the whitelist validation passes
    try:
        # We expect these to potentially fail due to missing DB, but not due to label validation
        await client.count_relationships("test-id", "Model")
    except ValueError as e:
        pytest.fail(f"Valid label 'Model' rejected: {e}")
    except Exception:
        # Expected - DB might not be running, but label validation passed
        pass

    try:
        await client.count_relationships("test-id", "Component")
    except ValueError as e:
        pytest.fail(f"Valid label 'Component' rejected: {e}")
    except Exception:
        pass

    try:
        await client.count_relationships("test-id", "Recipe")
    except ValueError as e:
        pytest.fail(f"Valid label 'Recipe' rejected: {e}")
    except Exception:
        pass

    await client.close()


@pytest.mark.asyncio
async def test_count_relationships_invalid_label_injection():
    """Test that count_relationships rejects invalid labels (SQL injection prevention)."""
    client = AsyncNeo4jClient(
        uri="neo4j://localhost:7687",
        user="neo4j",
        password="password",
    )

    # Test various injection payloads - all should raise ValueError
    injection_payloads = [
        "User'; DROP TABLE Model; --",        # SQL injection pattern
        "Model} DETACH DELETE m //',          # Cypher injection pattern
        "Model) LOAD CSV FROM",               # LOAD CSV injection
        "ArbitraryLabel",                     # Unknown label
        "model",                               # Case mismatch (should be Model)
    ]

    for payload in injection_payloads:
        with pytest.raises(ValueError, match=f"Invalid label: {payload}"):
            await client.count_relationships("test-id", payload)

    await client.close()
