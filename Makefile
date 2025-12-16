SHELL := /bin/bash
# =============================================================================
# Variables & Style
# =============================================================================
.DEFAULT_GOAL:=help
.ONESHELL:
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory

BLUE := $(shell printf "\033[1;34m")
GREEN := $(shell printf "\033[1;32m")
NC := $(shell printf "\033[0m")
INFO := $(shell printf "$(BLUE)ℹ$(NC)")
OK := $(shell printf "$(GREEN)✓$(NC)")

## ============================================================================
## Project Setup & Management
## ============================================================================

.PHONY: install
install: clean ## Install dependencies for local development
	@echo "${INFO} Installing dependencies via uv..."
	@uv sync --all-extras --dev
	@echo "${OK} Installation complete!"

.PHONY: clean
clean: ## Remove cache, virtual environment, and build artifacts
	@echo "${INFO} Cleaning project artifacts..."
	@rm -rf .venv .ruff_cache site/ __pycache__ *.pyc
	@echo "${OK} Project cleaned."


## ============================================================================
## LychD Core Commands
## ============================================================================

.PHONY: init
init: ## Initialize the LychD Codex (~/.config/lychd)
	@echo "${INFO} Initializing Codex..."
	@uv run lychd init

.PHONY: bind
bind: ## Bind the configuration to Systemd units
	@echo "${INFO} Binding runes to Systemd..."
	@uv run lychd bind


## ============================================================================
## Quality & Linting
## ============================================================================

.PHONY: lint
lint: ## Run ruff linter
	@echo "${INFO} Running linter..."
	@uv run ruff check .

.PHONY: format
format: ## Run ruff formatter
	@echo "${INFO} Formatting code..."
	@uv run ruff format .

.PHONY: test
test: ## Run tests with pytest
	@echo "${INFO} Running tests..."
	@uv run pytest


## ============================================================================
## Documentation
## ============================================================================

.PHONY: docs
docs: ## Serve the documentation locally
	@echo "${INFO} Serving The Hexanomicon at http://localhost:8001"
	@uv run mkdocs serve --dev-addr localhost:8001 --livereload


## ============================================================================
## Help
## ============================================================================
.PHONY: help
help: ## Display this help message
	@awk 'BEGIN {FS = ":.*?##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
