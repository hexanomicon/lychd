SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
.ONESHELL:
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory

# =============================================================================
# Configuration & Colors
# =============================================================================

# Argument extraction for tests
# Usage: make test K="animation" M="unit"
#        make test PYTEST_TARGETS="tests/unit/config/runes"
# Default parallelism is auto, but can be overridden (e.g., make test N=0)
N ?= auto
PYTEST_TARGETS ?= tests
RUFF_TARGETS ?= .
FORMAT_TARGETS ?= .
TYPECHECK_TARGETS ?=
PYTEST_EFFECTIVE_TARGETS := $(PYTEST_TARGETS)

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
	ifeq ($(strip $(PYTEST_TARGETS)),tests)
		PYTEST_EFFECTIVE_TARGETS :=
	endif
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

define validate_paths
	paths="$(strip $(1))"; \
	if [ -n "$$paths" ]; then \
		missing=0; \
		for path in $$paths; do \
			if [ ! -e "$$path" ]; then \
				echo "${RED}✗${NC} Path not found: $$path"; \
				missing=1; \
			fi; \
		done; \
		if [ $$missing -ne 0 ]; then \
			exit 2; \
		fi; \
	fi
endef

# =============================================================================
# 🛠️ Setup & Management
# =============================================================================

.PHONY: install-uv
install-uv:                                         ## Install latest version of uv
	@echo "${INFO} Installing uv..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
	@echo "${OK} UV installed successfully"

.PHONY: install
install: ## Install Python dependencies (Backend)
	@echo "${INFO} Syncing Python dependencies via uv..."
	@uv sync --all-extras --dev
	@echo "${OK} Ready to rock."

# =============================================================================
# 🕯️ Altar Frontend (TODO: expand as frontend pipeline matures)
# =============================================================================

.PHONY: frontend-install
frontend-install: ## Install frontend dependencies for the Altar (TODO)
	@echo "${INFO} Installing frontend dependencies..."
	@npm ci
	@echo "${OK} Frontend dependencies installed."

.PHONY: frontend-dev
frontend-dev: ## Run the Altar frontend in watch mode (TODO)
	@echo "${INFO} Starting frontend dev server..."
	@npm run dev

.PHONY: frontend-build
frontend-build: ## Build frontend assets for the Altar (TODO)
	@echo "${INFO} Building frontend assets..."
	@npm run build
	@echo "${OK} Frontend build complete."

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
lint: ## Run Ruff (Linter). Usage: make lint RUFF_TARGETS="src/lychd/app.py tests/unit"
	@$(call validate_paths,$(RUFF_TARGETS))
	@echo "${INFO} Linting (Targets: $(RUFF_TARGETS))..."
	@uv run ruff check $(RUFF_TARGETS)
	@echo "${OK} Lint pass."

.PHONY: format
format: ## Run Ruff (Formatter). Usage: make format FORMAT_TARGETS="src/lychd/app.py"
	@$(call validate_paths,$(FORMAT_TARGETS))
	@echo "${INFO} Formatting (Targets: $(FORMAT_TARGETS))..."
	@uv run ruff format $(FORMAT_TARGETS)
	@echo "${OK} Formatted."

.PHONY: type-check
type-check: ## Run BasedPyright. Usage: make type-check TYPECHECK_TARGETS="src/lychd/app.py"
	@$(call validate_paths,$(TYPECHECK_TARGETS))
	@echo "${INFO} Type checking (Targets: $(if $(strip $(TYPECHECK_TARGETS)),$(TYPECHECK_TARGETS),<repo-default>))..."
	@uv run --group typing basedpyright $(TYPECHECK_TARGETS)
	@echo "${OK} Types are strict."

.PHONY: test
test: ## Run tests. Usage: make test K="anim" M="unit"
	@echo "${INFO} Running tests (Args: $(PYTEST_ARGS) Targets: $(PYTEST_EFFECTIVE_TARGETS))..."
	@uv run pytest $(PYTEST_ARGS) $(PYTEST_EFFECTIVE_TARGETS)

.PHONY: test-config
test-config: ## Run configurable/runes focused tests only
	@$(MAKE) test PYTEST_TARGETS="tests/unit/config/runes tests/unit/system/services/test_codex.py"

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
	@uv run zensical serve --dev-addr localhost:7778


.PHONY: kill-docs
kill-docs: ## Kill any process running on the docs port (7778)
	@echo "${INFO} Finding and stopping process on port 7778..."
	@lsof -t -i:7778 | xargs -r kill -9 || true
	@echo "${OK} Port 7778 is clear."

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
