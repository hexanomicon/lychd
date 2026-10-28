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
# Usage: make test K="animation"
#        make test PYTEST_TARGETS="tests/unit/config/runes"
# The reliable default is serial; opt into bounded parallelism explicitly (e.g., make test N=8).
# Disposable container receipts are excluded by default; explicit M replaces that selector.
# Default output is compact for agent context. Use VERBOSE=1 when debugging:
# it disables RTK filtering and makes pytest stream stdout plus long tracebacks
# into the caller and enables live DEBUG logging.
# RTK is optional; when it is missing, targets fall back to raw uv/curl/grep.
N ?= 0
VERBOSE ?= 0
PYTEST_TARGETS ?= tests
# Automatic CI covers these in-process contracts; host/filesystem qualification
# and disposable PostgreSQL remain separate. Keep the full test/check defaults.
CI_PYTEST_TARGETS := tests/unit/config tests/unit/db \
	tests/architecture/test_release_legal_artifacts.py tests/architecture/test_ward_native_postgres_receipt.py \
	tests/architecture/test_core_check_entrypoints.py tests/architecture/test_container_only_receipt.py \
	tests/unit/test_app.py tests/unit/cli/test_cli.py \
	tests/unit/system/operator tests/unit/cli/test_operator.py \
	tests/unit/cli/test_deletion_retirement.py \
	tests/unit/system/services/test_binding_preflight.py \
	tests/unit/system/services/test_init_binding_sites.py tests/unit/system/services/test_bind_compilation.py \
	tests/unit/system/test_schemas.py tests/unit/system/services/test_artifact_custody.py \
	tests/unit/system/services/test_artifact_publication.py \
	tests/unit/system/services/test_native_candidate_custody.py \
	tests/unit/system/services/test_native_candidate_authority.py \
	tests/unit/system/test_scout_worker.py tests/unit/system/test_scout_rss_worker.py \
	tests/unit/system/services/test_scout_extraction.py \
	tests/unit/system/services/test_scout_rss_extraction.py \
	tests/unit/system/services/test_scout_dns.py tests/unit/system/services/test_scout_socket.py \
	tests/unit/system/services/test_scout_http.py tests/unit/system/services/test_scout_fetch.py \
	tests/unit/system/services/test_scout_workflow.py tests/codex/test_local_access.py \
	tests/unit/domain/intercom tests/unit/system/services/test_intercom.py \
	tests/unit/cli/test_intercom_lab.py \
	tests/unit/interface tests/unit/cli/test_reach_prepare.py \
	tests/unit/cli/test_reach_worker.py tests/unit/cli/test_reach_operator.py \
	tests/unit/cli/test_reach_operator_model.py \
	tests/unit/cli/test_reach_operator_onboarding.py \
	tests/unit/system/services/test_intercom_http.py \
	tests/unit/domain/test_artifact_custody.py tests/unit/domain/test_evolution.py \
	tests/unit/domain/animation tests/unit/domain/cortex tests/unit/domain/delegation \
	tests/unit/domain/orchestration tests/unit/domain/privacy tests/unit/domain/web tests/unit/domain/scout \
	tests/unit/domain/ward \
	tests/unit/extensions tests/unit/lib tests/unit/compositions tests/agents tests/web \
	tests/integration/test_configuration_workflows.py \
	tests/integration/test_bridge_casting_workflow.py \
	tests/integration/test_blockworld_placement_vertical.py \
	tests/integration/test_crypt_extension_vertical.py \
	tests/integration/test_extension_configuration.py
CONTAINER_TEST_TARGETS ?= tests/integration/test_db_consent_pg.py \
	tests/integration/test_ward_pg.py tests/integration/test_native_candidate_authority_pg.py \
	tests/integration/test_db_blockworld_pg.py \
	tests/integration/test_database_authority_pg.py \
	tests/integration/test_db_atlas_pg.py \
	tests/integration/test_db_migrations_pg.py \
	tests/integration/test_db_nexus_pg.py \
	tests/integration/test_db_run_ledger_pg.py \
	tests/integration/test_delegated_process_recovery_pg.py \
	tests/integration/test_delegated_cli_v2_pg.py \
	tests/integration/test_delegated_host_disposition_pg.py \
	tests/integration/test_privacy_disclosure_pg.py tests/integration/test_privacy_disclosure_migrations_pg.py \
	tests/integration/test_intercom_pg.py tests/integration/test_intercom_migrations_pg.py \
	tests/integration/test_native_peer_migrations_pg.py \
	tests/integration/test_scout_attempts_pg.py tests/integration/test_scout_migrations_pg.py \
	tests/integration/test_scout_workflow_pg.py \
	tests/integration/test_production_wiring.py::test_production_wiring_real_factory_over_postgres_survives_second_boot
PYTEST_BASE_ROOT ?= .cache/pytest
PYTEST_BASETEMP ?=
RUFF_TARGETS ?= .
FORMAT_TARGETS ?= .
TYPECHECK_TARGETS ?=
RELEASE_REVISION ?=
RELEASE_TAG ?=
RELEASE_ARTIFACT_DIR ?= .cache/release-candidate/$(RELEASE_REVISION)
PYTEST_EFFECTIVE_TARGETS := $(PYTEST_TARGETS)
UV ?= uv
UV_DEV_RUN := $(UV) run --locked --extra postgres-binary
ifeq ($(LYCHD_TEST_CONTAINER),1)
UV_DEV_RUN := $(UV) run --offline --no-sync --extra postgres-binary
endif
UV_CACHE_DIR ?= .cache/uv
RTK ?= rtk
RTK_AVAILABLE := $(shell command -v $(RTK) >/dev/null 2>&1 && echo 1 || echo 0)
RTK_ACTIVE := $(RTK_AVAILABLE)
# Keep pytest attached directly to its xdist workers. A presentation wrapper may
# compact output, but it must not become part of worker shutdown correctness.
PYTEST := $(UV_DEV_RUN) pytest

ifeq ($(VERBOSE),1)
RTK_ACTIVE := 0
endif

ifeq ($(RTK_ACTIVE),1)
RUN := $(UV_DEV_RUN) $(RTK) run
ERR := $(UV_DEV_RUN) $(RTK) err
RUFF := $(UV_DEV_RUN) $(RTK) ruff
TYPECHECK := $(UV_DEV_RUN) --group typing --group container-test $(RTK) err basedpyright
CURL := $(RTK) curl
GREP := $(RTK) grep
else
RUN :=
ERR :=
RUFF := $(UV_DEV_RUN) ruff
TYPECHECK := $(UV_DEV_RUN) --group typing --group container-test basedpyright
CURL := curl
GREP := grep
endif

# Keep generated fixtures beneath the checkout so strict path-authority tests
# do not inherit a foreign-owned `/tmp` from containers or coding sandboxes.
PYTEST_ARGS := -n $(N) --dist loadscope
CONTAINER_PYTEST_ARGS := -n $(N) --dist loadscope -m container
ifeq ($(VERBOSE),1)
	PYTEST_ARGS += -s --tb=long -o log_cli=true --log-cli-level=DEBUG
	CONTAINER_PYTEST_ARGS += -s --tb=long -o log_cli=true --log-cli-level=DEBUG
else
	# pyproject adds ``-v``; two quiet flags yield one genuinely compact level.
	PYTEST_ARGS += -qq
	CONTAINER_PYTEST_ARGS += -qq
endif
ifdef K
	PYTEST_ARGS += -k "$(K)"
endif
ifdef M
	PYTEST_ARGS += -m "$(M)"
else
	PYTEST_ARGS += -m "not container"
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
WEB_CLIENT_DIR ?= clients/web

.PHONY: frontend-install
frontend-install: ## Install the pinned Svelte Altar dependencies with npm
	@echo "${INFO} Installing frontend dependencies..."
	@$(NPM) ci --prefix $(WEB_CLIENT_DIR)
	@echo "${OK} Frontend dependencies installed."

.PHONY: frontend-dev
frontend-dev: ## Run the SvelteKit Altar in loopback-only development mode
	@echo "${INFO} Starting frontend dev server..."
	@$(NPM) --prefix $(WEB_CLIENT_DIR) run dev

.PHONY: developer-fixture
developer-fixture: ## Run the read-only synthetic backend for local browser development
ifeq ($(LYCHD_TEST_CONTAINER),1)
	@$(UV_DEV_RUN) python -m lychd.developer --caged
else
	@bash scripts/container_checks.sh developer-fixture
endif

.PHONY: frontend-build
frontend-build: ## Generate contracts and compile the static Svelte Altar
	@echo "${INFO} Building frontend assets..."
	@$(UV_DEV_RUN) python scripts/export_openapi.py
	@$(NPM) --prefix $(WEB_CLIENT_DIR) run generate:api
	@$(NPM) --prefix $(WEB_CLIENT_DIR) run build
	@echo "${OK} Frontend build complete."

.PHONY: frontend-check
frontend-check: ## Type-check and test the Svelte Altar
	@$(UV_DEV_RUN) python scripts/export_openapi.py
	@$(NPM) --prefix $(WEB_CLIENT_DIR) run generate:api
	@$(NPM) --prefix $(WEB_CLIENT_DIR) run check
	@$(NPM) --prefix $(WEB_CLIENT_DIR) run test

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

# Only the source-bound check image may execute Core test/check tools. An env
# flag by itself cannot bypass the host wrapper.
CORE_CHECK_TARGETS := lint format-check type-check test test-containers test-ci test-config coverage check
ifeq ($(LYCHD_TEST_CONTAINER),1)
CHECK_CONTAINER_OBSERVED := $(shell test -f /opt/lychd-test-image && { test -f /run/.containerenv || test -f /.dockerenv; } && echo 1)
ifneq ($(CHECK_CONTAINER_OBSERVED),1)
$(error Core checks require the OCI test image and an observed container marker)
endif
.PHONY: lint
lint: ## Run Ruff (Linter). Usage: make lint RUFF_TARGETS="src/lychd/app.py tests/unit"
	@read -r -a targets <<< "$$RUFF_TARGETS"
	@$(RUFF) check "$${targets[@]}"
	@echo "${OK} Lint pass."

.PHONY: format-check
format-check: ## Check Ruff formatting without changing files
	@read -r -a targets <<< "$$FORMAT_TARGETS"
	@$(RUFF) format --check "$${targets[@]}"
	@echo "${OK} Formatting is clean."

.PHONY: type-check
type-check: ## Run BasedPyright. Usage: make type-check TYPECHECK_TARGETS="src/lychd/app.py"
	@read -r -a targets <<< "$$TYPECHECK_TARGETS"
	@$(TYPECHECK) "$${targets[@]}"
	@echo "${OK} Types are strict."

.PHONY: test
test: ## Run tests. Usage: make test K="anim"
	@$(UV_DEV_RUN) python scripts/container_pytest_args.py

.PHONY: test-containers
test-containers: ## Run explicit disposable-PostgreSQL receipts; requires a Docker-compatible daemon
	@read -r -a targets <<< "$$CONTAINER_TEST_TARGETS"
	@args=(-n "$$N" --dist loadscope -m container)
	@if [[ "$$VERBOSE" == 1 ]]; then
		args+=(-s --tb=long -o log_cli=true --log-cli-level=DEBUG)
	@else
		args+=(-qq)
	fi
	@basetemp="$${PYTEST_BASETEMP:-}"
	@if [[ -z "$$basetemp" ]]; then
		mkdir -p "$$PYTEST_BASE_ROOT"
		basetemp="$$(mktemp -d "$$PYTEST_BASE_ROOT/run.XXXXXX")"
	@else
		mkdir -p "$$(dirname "$$basetemp")"
	fi
	@$(UV_DEV_RUN) --group container-test pytest "$${args[@]}" --basetemp "$$basetemp" "$${targets[@]}"

.PHONY: test-ci
test-ci: ## Run the core CI selection inside the OCI test image
	@$(MAKE) test PYTEST_TARGETS="$(CI_PYTEST_TARGETS)" M="not container" N=0

.PHONY: test-config
test-config: ## Run configurable/runes focused tests only
	@$(MAKE) test PYTEST_TARGETS="tests/unit/config/runes tests/unit/system/services/test_codex.py"

.PHONY: coverage
coverage: ## Run tests with coverage report
	@echo "${INFO} Generating coverage..."
	@basetemp="$${PYTEST_BASETEMP:-}"
	@if [[ -z "$$basetemp" ]]; then
		mkdir -p "$$PYTEST_BASE_ROOT"
		basetemp="$$(mktemp -d "$$PYTEST_BASE_ROOT/run.XXXXXX")"
	@else
		mkdir -p "$$(dirname "$$basetemp")"
	fi
	@$(PYTEST) --basetemp "$$basetemp" -m "not container" --cov --cov-report=html:htmlcov --cov-report=term
	@echo "${OK} Report generated at htmlcov/index.html"

.PHONY: check
check: lint format-check type-check test ## Run all non-mutating quality checks

else
.PHONY: $(CORE_CHECK_TARGETS)
lint: ## Run Ruff lint inside the source-bound OCI test image
format-check: ## Check formatting inside the OCI test image
type-check: ## Run BasedPyright inside the OCI test image
test: ## Run tests inside OCI; select with PYTEST_TARGETS, K, M, ARGS and N
test-containers: ## Run OCI PostgreSQL receipts with explicit LYCHD_TEST_DAEMON_SOCKET
test-ci: ## Run the Core CI selection inside the OCI test image
test-config: ## Run configuration tests inside the OCI test image
coverage: ## Enforce coverage inside OCI; HTML is private to that disposable container
check: ## Run all non-mutating Python checks inside the OCI test image
$(CORE_CHECK_TARGETS):
	@bash scripts/container_checks.sh $@
endif

.PHONY: format
format: ## Run Ruff (Formatter). Usage: make format FORMAT_TARGETS="src/lychd/app.py"
	@$(call validate_paths,$(FORMAT_TARGETS))
	@echo "${INFO} Formatting (Targets: $(FORMAT_TARGETS))..."
	@$(RUFF) format $(FORMAT_TARGETS)
	@echo "${OK} Formatted."

## ============================================================================
## Documentation
## ============================================================================


.PHONY: docs
docs: ## Serve the documentation locally
	@echo "${INFO} Serving Hexanomicon at http://localhost:7778"
	@$(RUN) $(UV_DEV_RUN) zensical serve --dev-addr localhost:7778


.PHONY: kill-docs
kill-docs: ## Kill any process running on the docs port (7778)
	@echo "${INFO} Finding and stopping process on port 7778..."
	@$(RUN) lsof -t -i:7778 | xargs -r kill -9 || true
	@echo "${OK} Port 7778 is clear."

# =============================================================================
# 📦 Release & Build
# =============================================================================

.PHONY: release
release: ## Prepare version fields only; never commits, tags, or publishes
ifndef part
	$(error "You must specify a part! Usage: make release part=patch")
endif
	@echo "${INFO} Bumping version ($(part))..."
	@$(ERR) $(UV) run bump-my-version bump $(part)
	@echo "${OK} Version fields updated locally; review and commit them manually."

.PHONY: build
build: frontend-build ## Build local, explicitly non-release Python artifacts
	@echo "${INFO} Building local source artifacts..."
	@$(ERR) $(UV) build
	@echo "${OK} Built."

.PHONY: release-preflight
release-preflight: ## Require a clean checkout at RELEASE_REVISION
	@$(RUN) $(UV) run python scripts/verify_release_source.py "$(RELEASE_REVISION)"

.PHONY: frontend-release-build
frontend-release-build: release-preflight ## Compile Altar against exact RELEASE_REVISION
	@echo "${INFO} Building Altar for immutable source $(RELEASE_REVISION)..."
	@$(MAKE) frontend-build LYCHD_ALTAR_VERSION="$(RELEASE_REVISION)"
	@echo "${OK} Exact-source Altar built."

.PHONY: release-candidate
release-candidate: release-preflight ## Test and build audited artifacts; never uploads them
	@echo "${INFO} Verifying release candidate $(RELEASE_REVISION)..."
	@$(MAKE) lint
	@$(MAKE) format-check
	@$(MAKE) type-check
	@$(MAKE) test
	@$(MAKE) frontend-check
	@$(MAKE) frontend-release-build RELEASE_REVISION="$(RELEASE_REVISION)"
	@$(ERR) $(UV) build --out-dir "$(RELEASE_ARTIFACT_DIR)"
	@$(RUN) $(UV) run python scripts/verify_release_artifacts.py \
		--dist-dir "$(RELEASE_ARTIFACT_DIR)" \
		--source-revision "$(RELEASE_REVISION)" \
		--release-tag "$(RELEASE_TAG)" \
		--install-check
	@echo "${OK} Release candidate verified locally; nothing was uploaded."


# =============================================================================
# 🔮 LychD Specifics
# =============================================================================

.PHONY: init
init: ## Initialize the local LychD host layout
	@$(ERR) $(UV_DEV_RUN) lychd init

.PHONY: bind
bind: ## Bind Systemd units
	@$(ERR) $(UV_DEV_RUN) lychd bind

# =============================================================================
# 📚 Help
# =============================================================================
.PHONY: help
help: ## Display this help message
	@$(GREP) -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
