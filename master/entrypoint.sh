#!/bin/bash
set -e

echo "Starting Master API entrypoint..."

# Initialize Neo4j schema (idempotent)
echo "Initializing Neo4j schema..."
python3 -m neo4j_client.init_schema

if [ $? -ne 0 ]; then
    echo "Schema initialization failed, but continuing (schema may already be initialized)"
fi

echo "Schema initialization complete, starting Master API..."

# Start Master API
exec uvicorn master.api:app --host 0.0.0.0 --port 8000 --reload
