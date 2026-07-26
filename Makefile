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
# Default output is compact for agent context. Use VERBOSE=1 when debugging:
# it disables RTK filtering and makes pytest stream stdout plus long tracebacks
# into the caller. Pytest log streaming is already owned by pyproject.toml.
# RTK is optional; when it is missing, targets fall back to raw uv/curl/grep.
N ?= auto
VERBOSE ?= 0
PYTEST_TARGETS ?= tests
PYTEST_BASETEMP ?= .cache/pytest
RUFF_TARGETS ?= .
FORMAT_TARGETS ?= .
TYPECHECK_TARGETS ?=
PYTEST_EFFECTIVE_TARGETS := $(PYTEST_TARGETS)
UV ?= uv
UV_CACHE_DIR ?= .cache/uv
RTK ?= rtk
RTK_AVAILABLE := $(shell command -v $(RTK) >/dev/null 2>&1 && echo 1 || echo 0)
RTK_ACTIVE := $(RTK_AVAILABLE)

ifeq ($(VERBOSE),1)
RTK_ACTIVE := 0
endif

ifeq ($(RTK_ACTIVE),1)
RUN := $(UV) run $(RTK) run
ERR := $(UV) run $(RTK) err
RUFF := $(UV) run $(RTK) ruff
PYTEST := $(UV) run $(RTK) pytest
TYPECHECK := $(UV) run --group typing $(RTK) err basedpyright
CURL := $(RTK) curl
GREP := $(RTK) grep
else
RUN :=
ERR :=
RUFF := $(UV) run ruff
PYTEST := $(UV) run pytest
TYPECHECK := $(UV) run --group typing basedpyright
CURL := curl
GREP := grep
endif

# Keep generated fixtures beneath the checkout so strict path-authority tests
# do not inherit a foreign-owned `/tmp` from containers or coding sandboxes.
PYTEST_ARGS := -n $(N) --basetemp $(PYTEST_BASETEMP)
ifeq ($(VERBOSE),1)
	PYTEST_ARGS += -s --tb=long
endif
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
	@$(CURL) -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
	@echo "${OK} UV installed successfully"

.PHONY: install
install: ## Install Python dependencies (Backend)
	@echo "${INFO} Syncing Python dependencies via uv..."
	@$(ERR) $(UV) sync --all-extras --dev
	@echo "${OK} Ready to rock."

# =============================================================================
# 🕯️ Altar Frontend
# =============================================================================

NPM ?= npm

.PHONY: frontend-install
frontend-install: ## Install the pinned Svelte Altar dependencies with npm
	@echo "${INFO} Installing frontend dependencies..."
	@$(NPM) ci --prefix frontend
	@echo "${OK} Frontend dependencies installed."

.PHONY: frontend-dev
frontend-dev: ## Run the SvelteKit Altar in loopback-only development mode
	@echo "${INFO} Starting frontend dev server..."
	@$(NPM) --prefix frontend run dev

.PHONY: frontend-build
frontend-build: ## Generate contracts and compile the static Svelte Altar
	@echo "${INFO} Building frontend assets..."
	@$(UV) run python scripts/export_openapi.py
	@$(NPM) --prefix frontend run generate:api
	@$(NPM) --prefix frontend run build
	@echo "${OK} Frontend build complete."

.PHONY: frontend-check
frontend-check: ## Type-check and test the Svelte Altar
	@$(UV) run python scripts/export_openapi.py
	@$(NPM) --prefix frontend run generate:api
	@$(NPM) --prefix frontend run check
	@$(NPM) --prefix frontend run test

.PHONY: clean
clean: ## Nuke all artifacts, caches, and build files
	@echo "${INFO} Cleaning project..."
	@$(RUN) rm -rf .venv .cache .ruff_cache .pytest_cache .mypy_cache .coverage htmlcov dist build
	@$(RUN) find . -type d -name "__pycache__" -exec rm -rf {} +
	@$(RUN) find . -type f -name "*.pyc" -delete
	@echo "${OK} Cleaned."

.PHONY: lock
lock: ## Re-resolve dependencies and update uv.lock
	@echo "${INFO} Updating lockfile..."
	@$(ERR) $(UV) lock --upgrade
	@echo "${OK} Locked."

# =============================================================================
# 🧪 Quality & Testing
# =============================================================================

.PHONY: lint
lint: ## Run Ruff (Linter). Usage: make lint RUFF_TARGETS="src/lychd/app.py tests/unit"
	@$(call validate_paths,$(RUFF_TARGETS))
	@echo "${INFO} Linting (Targets: $(RUFF_TARGETS))..."
	@$(RUFF) check $(RUFF_TARGETS)
	@echo "${OK} Lint pass."

.PHONY: format
format: ## Run Ruff (Formatter). Usage: make format FORMAT_TARGETS="src/lychd/app.py"
	@$(call validate_paths,$(FORMAT_TARGETS))
	@echo "${INFO} Formatting (Targets: $(FORMAT_TARGETS))..."
	@$(RUFF) format $(FORMAT_TARGETS)
	@echo "${OK} Formatted."

.PHONY: type-check
type-check: ## Run BasedPyright. Usage: make type-check TYPECHECK_TARGETS="src/lychd/app.py"
	@$(call validate_paths,$(TYPECHECK_TARGETS))
	@echo "${INFO} Type checking (Targets: $(if $(strip $(TYPECHECK_TARGETS)),$(TYPECHECK_TARGETS),<repo-default>))..."
	@$(TYPECHECK) $(TYPECHECK_TARGETS)
	@echo "${OK} Types are strict."

.PHONY: test
test: ## Run tests. Usage: make test K="anim" M="unit"
	@echo "${INFO} Running tests (Args: $(PYTEST_ARGS) Targets: $(PYTEST_EFFECTIVE_TARGETS))..."
	@$(PYTEST) $(PYTEST_ARGS) $(PYTEST_EFFECTIVE_TARGETS)

.PHONY: test-config
test-config: ## Run configurable/runes focused tests only
	@$(MAKE) test PYTEST_TARGETS="tests/unit/config/runes tests/unit/system/services/test_codex.py"

.PHONY: coverage
coverage: ## Run tests with coverage report
	@echo "${INFO} Generating coverage..."
	@$(PYTEST) --basetemp $(PYTEST_BASETEMP) --cov --cov-report=html:htmlcov --cov-report=term
	@echo "${OK} Report generated at htmlcov/index.html"

.PHONY: check
check: lint format type-check test ## Run ALL quality checks (The "CI" command)

## ============================================================================
## Documentation
## ============================================================================


.PHONY: docs
docs: ## Serve the documentation locally
	@echo "${INFO} Serving The Hexanomicon at http://localhost:7778"
	@$(RUN) $(UV) run zensical serve --dev-addr localhost:7778


.PHONY: kill-docs
kill-docs: ## Kill any process running on the docs port (7778)
	@echo "${INFO} Finding and stopping process on port 7778..."
	@$(RUN) lsof -t -i:7778 | xargs -r kill -9 || true
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
	@$(ERR) $(UV) run bump-my-version bump $(part)
	@echo "${OK} Version bumped and tagged."

.PHONY: build
build: ## Build the Python wheel
	@echo "${INFO} Building wheel..."
	@$(ERR) $(UV) build
	@echo "${OK} Built."


# =============================================================================
# 🔮 LychD Specifics
# =============================================================================

.PHONY: init
init: ## Initialize the local LychD host layout
	@$(ERR) $(UV) run lychd init

.PHONY: bind
bind: ## Bind Systemd units
	@$(ERR) $(UV) run lychd bind

# =============================================================================
# 📚 Help
# =============================================================================
.PHONY: help
help: ## Display this help message
	@$(GREP) -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
