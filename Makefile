.PHONY: setup validate techniques frameworks compatible help

# ─── Setup Generation ───

setup: ## Generate a setup directory. Usage: make setup NAME=my-exp CONFIG=configs/examples/grpo_qlora_qwen.yaml
	@if [ -z "$(NAME)" ] || [ -z "$(CONFIG)" ]; then \
		echo "Usage: make setup NAME=<experiment-name> CONFIG=<path-to-yaml>"; \
		exit 1; \
	fi
	python -m envelope.cli setup --name $(NAME) --config $(CONFIG) $(if $(OUTPUT),--output $(OUTPUT),)

validate: ## Validate a YAML config. Usage: make validate CONFIG=configs/examples/grpo_qlora_qwen.yaml
	@if [ -z "$(CONFIG)" ]; then \
		echo "Usage: make validate CONFIG=<path-to-yaml>"; \
		exit 1; \
	fi
	python -m envelope.cli validate --config $(CONFIG)

techniques: ## List all registered training techniques
	python -m envelope.cli techniques

frameworks: ## List all registered framework adapters
	python -m envelope.cli frameworks

compatible: ## Show compatible frameworks for a technique. Usage: make compatible TECHNIQUE=grpo
	@if [ -z "$(TECHNIQUE)" ]; then \
		echo "Usage: make compatible TECHNIQUE=<technique-name>"; \
		exit 1; \
	fi
	python -m envelope.cli compatible $(TECHNIQUE)

# ─── Development ───

install: ## Install the project and dependencies
	pip install -e ".[dev]"

test: ## Run test suite
	pytest tests/ -v

lint: ## Run linter
	ruff check envelope/ tests/

format: ## Format code
	ruff format envelope/ tests/

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
