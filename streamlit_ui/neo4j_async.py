"""Async Neo4j client for Streamlit UI."""

from __future__ import annotations

from typing import Any, Optional

from neo4j import AsyncDriver, AsyncGraphDatabase


class AsyncNeo4jClient:
    """Async Neo4j client wrapper with connection pooling."""

    def __init__(self, uri: str, user: str, password: str, pool_size: int = 50):
        """Initialize async Neo4j client.

        Args:
            uri: Neo4j bolt URI.
            user: Neo4j username.
            password: Neo4j password.
            pool_size: Max connection pool size.
        """
        self.uri = uri
        self.user = user
        self.pool_size = pool_size
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri,
            auth=(user, password),
            max_pool_size=pool_size,
        )

    async def run(self, query: str, **kwargs) -> Any:
        """Execute a Cypher query.

        Args:
            query: Cypher query string.
            **kwargs: Query parameters.

        Returns:
            Query result.
        """
        async with self.driver.session() as session:
            result = await session.run(query, **kwargs)
            return result

    async def run_single(self, query: str, **kwargs) -> Optional[dict]:
        """Execute a query expecting a single result.

        Args:
            query: Cypher query string.
            **kwargs: Query parameters.

        Returns:
            Single result record or None.
        """
        async with self.driver.session() as session:
            result = await session.run(query, **kwargs)
            record = await result.single()
            return dict(record) if record else None

    async def run_list(self, query: str, **kwargs) -> list[dict]:
        """Execute a query returning a list of results.

        Args:
            query: Cypher query string.
            **kwargs: Query parameters.

        Returns:
            List of result records.
        """
        async with self.driver.session() as session:
            result = await session.run(query, **kwargs)
            records = await result.list()
            return [dict(record) for record in records]

    async def count_relationships(self, node_id: str, label: str) -> int:
        """Count incoming relationships to a node.

        Args:
            node_id: Node ID to check.
            label: Node label (e.g., 'Model', 'Component', 'Recipe').

        Returns:
            Count of incoming relationships.

        Raises:
            ValueError: If label is not in the allowed set.
        """
        ALLOWED_LABELS = {"Model", "Component", "Recipe"}
        if label not in ALLOWED_LABELS:
            raise ValueError(f"Invalid label: {label}. Allowed: {ALLOWED_LABELS}")

        # Use separate queries for each allowed label to prevent Cypher injection
        if label == "Model":
            query = """
            MATCH (n:Model {id: $id})<-[r]-(m)
            RETURN count(r) as dep_count
            """
        elif label == "Component":
            query = """
            MATCH (n:Component {id: $id})<-[r]-(m)
            RETURN count(r) as dep_count
            """
        else:  # label == "Recipe"
            query = """
            MATCH (n:Recipe {id: $id})<-[r]-(m)
            RETURN count(r) as dep_count
            """

        result = await self.run_single(query, id=node_id)
        return result["dep_count"] if result else 0

    async def close(self) -> None:
        """Close the Neo4j driver."""
        if self.driver:
            await self.driver.close()
