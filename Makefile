SHELL := /bin/bash
.DEFAULT_GOAL := help
.ONESHELL:
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory

# =============================================================================
# Configuration & Colors
# =============================================================================

# Argument extraction for tests
# Usage: make test K="animation" M="unit"
# Default parallelism is auto, but can be overridden (e.g., make test N=0)
N ?= auto

PYTEST_ARGS := -n $(N)
ifdef K
	PYTEST_ARGS += -k "$(K)"
endif
ifdef M
	PYTEST_ARGS += -m "$(M)"
endif
# Allow arbitrary extra args (e.g. make test ARGS="-s --pdb")
ifdef ARGS
    PYTEST_ARGS += $(ARGS)
endif

# Colors
BLUE := $(shell printf "\033[1;34m")
GREEN := $(shell printf "\033[1;32m")
RED := $(shell printf "\033[1;31m")
YELLOW := $(shell printf "\033[1;33m")
NC := $(shell printf "\033[0m") # No Color
INFO := $(shell printf "$(BLUE)ℹ$(NC)")
OK := $(shell printf "$(GREEN)✓$(NC)")
WARN := $(shell printf "$(YELLOW)⚠$(NC)")

# =============================================================================
# 🛠️ Setup & Management
# =============================================================================

.PHONY: install-uv
install-uv:                                         ## Install latest version of uv
	@echo "${INFO} Installing uv..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
	@echo "${OK} UV installed successfully"

.PHONY: install
install: ## Install dependencies (Backend & Frontend)
	@echo "${INFO} Syncing Python dependencies via uv..."
	@uv sync --all-extras --dev
	@echo "${OK} Ready to rock."

.PHONY: clean
clean: ## Nuke all artifacts, caches, and build files
	@echo "${INFO} Cleaning project..."
	@rm -rf .venv .ruff_cache .pytest_cache .mypy_cache .coverage htmlcov dist build
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "${OK} Cleaned."

.PHONY: lock
lock: ## Re-resolve dependencies and update uv.lock
	@echo "${INFO} Updating lockfile..."
	@uv lock --upgrade
	@echo "${OK} Locked."

# =============================================================================
# 🧪 Quality & Testing
# =============================================================================

.PHONY: lint
lint: ## Run Ruff (Linter)
	@echo "${INFO} Linting..."
	@uv run ruff check .
	@echo "${OK} Lint pass."

.PHONY: format
format: ## Run Ruff (Formatter)
	@echo "${INFO} Formatting..."
	@uv run ruff format .
	@echo "${OK} Formatted."

.PHONY: type-check
type-check: ## Run Static Type Checking (BasedPyright)
	@echo "${INFO} Type checking..."
	@uv run basedpyright
	@echo "${OK} Types are strict."

.PHONY: test
test: ## Run tests. Usage: make test K="anim" M="unit"
	@echo "${INFO} Running tests (Args: $(PYTEST_ARGS))..."
	@uv run pytest $(PYTEST_ARGS)

.PHONY: coverage
coverage: ## Run tests with coverage report
	@echo "${INFO} Generating coverage..."
	@uv run pytest --cov --cov-report=html:htmlcov --cov-report=term
	@echo "${OK} Report generated at htmlcov/index.html"

.PHONY: check
check: lint format type-check test ## Run ALL quality checks (The "CI" command)

## ============================================================================
## Documentation
## ============================================================================

.PHONY: docs
docs: ## Serve the documentation locally
	@echo "${INFO} Serving The Hexanomicon at http://localhost:7778"
	@uv run mkdocs serve --dev-addr localhost:7778 --livereload


# =============================================================================
# 📦 Release & Build
# =============================================================================

.PHONY: release
release: ## Bump version and git tag. Usage: make release part=patch (or minor/major)
ifndef part
	$(error "You must specify a part! Usage: make release part=patch")
endif
	@echo "${INFO} Bumping version ($(part))..."
	@uv run bump-my-version bump $(part)
	@echo "${OK} Version bumped and tagged."

.PHONY: build
build: ## Build the Python wheel
	@echo "${INFO} Building wheel..."
	@uv build
	@echo "${OK} Built."


# =============================================================================
# 🔮 LychD Specifics
# =============================================================================

.PHONY: init
init: ## Initialize LychD Codex
	@uv run lychd init

.PHONY: bind
bind: ## Bind Systemd units
	@uv run lychd bind

# =============================================================================
# 📚 Help
# =============================================================================
.PHONY: help
help: ## Display this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
