.PHONY: help master-up master-down master-logs master-test master-shell master-reset neo4j-shell

help:
	@echo "FineTuning-Envelope Lineage System — Master Infrastructure"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  master-up          Start all services (Neo4j + Phoenix + Master API)"
	@echo "  master-down        Stop all services gracefully"
	@echo "  master-reset       Stop services and remove volumes (⚠️ data loss)"
	@echo "  master-logs        Stream logs from all services"
	@echo "  master-logs-neo4j  Stream logs from Neo4j only"
	@echo "  master-logs-phoenix Stream logs from Phoenix only"
	@echo "  master-logs-api    Stream logs from Master API only"
	@echo "  master-test        Run lineage tests with Docker (requires master-up)"
	@echo "  master-shell       Open shell in Neo4j container"
	@echo "  master-status      Show service status"
	@echo ""

master-up:
	@echo "🚀 Starting Master infrastructure..."
	docker-compose -f docker-compose.yml up -d
	@echo "✅ Services started"
	@echo ""
	@echo "Access points:"
	@echo "  Neo4j Browser: http://localhost:7474 (neo4j/password)"
	@echo "  Phoenix UI:    http://localhost:6006"
	@echo "  Master API:    http://localhost:8000"
	@echo ""

master-down:
	@echo "⏹️  Stopping Master infrastructure..."
	docker-compose -f docker-compose.yml down
	@echo "✅ Services stopped"

master-reset:
	@echo "🔄 Resetting Master infrastructure (removing volumes)..."
	docker-compose -f docker-compose.yml down -v
	@echo "✅ Services stopped and volumes removed"

master-logs:
	docker-compose -f docker-compose.yml logs -f

master-logs-neo4j:
	docker-compose -f docker-compose.yml logs -f neo4j

master-logs-phoenix:
	docker-compose -f docker-compose.yml logs -f phoenix

master-logs-api:
	docker-compose -f docker-compose.yml logs -f master-api

master-status:
	@docker-compose -f docker-compose.yml ps

neo4j-shell:
	@echo "Opening Neo4j cypher-shell..."
	docker exec -it lineage-neo4j cypher-shell -u neo4j -p password

master-test:
	@echo "🧪 Running Phase 2 lineage tests with Docker..."
	source .venv/bin/activate && python -m pytest tests/lineage/ -v --tb=short
	@echo "✅ Tests complete"

# Testing shortcuts
test-constraints:
	source .venv/bin/activate && python -m pytest tests/lineage/test_constraints.py -v

test-triggers:
	source .venv/bin/activate && python -m pytest tests/lineage/test_apoc_triggers.py -v

test-driver:
	source .venv/bin/activate && python -m pytest tests/lineage/test_neo4j_driver.py -v

test-repository:
	source .venv/bin/activate && python -m pytest tests/lineage/test_repository_impl.py tests/lineage/test_repository_advanced.py -v

# Development helpers
lint:
	source .venv/bin/activate && ruff check . --fix

format:
	source .venv/bin/activate && ruff format .

type-check:
	source .venv/bin/activate && python -m mypy master/ --ignore-missing-imports

dev-setup:
	pip install -e ".[dev,test,master]"

# CI targets
ci-test: master-up test-constraints test-triggers test-driver test-repository
	@echo "✅ All tests passed"

ci-lint: lint format
	@echo "✅ Linting passed"
