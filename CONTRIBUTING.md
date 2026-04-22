# Joining the Cult: Contributing to LychD

LychD is a systemd-native daemon for agentic orchestration. Contributions must favor correctness, traceability, and explicit architecture.

## The Iron Pact (No CLA)

By submitting code, you license your contribution under **AGPL-3.0-or-later** as defined in **[ADR 00: License](docs/adr/00-license.md)**.

## Local Setup

```bash
make install             # Python dependencies (Syncs all extras + dev)
uv sync --group dev      # Manual sync of the dev dependency group
make init                # Initialize local Codex (~/.config/lychd)
make frontend-install    # Altar frontend dependencies (npm)
make help                # View all available rituals
```

## Quality & Testing

### Purification Commands
```bash
make lint [RUFF_TARGETS="path/to/file.py"]   # Targeted or repo-wide lint
make format [RUFF_TARGETS="path/to/file.py"] # Targeted or repo-wide format
make type-check [TYPECHECK_TARGETS="path"]   # Targeted or repo-wide BasedPyright
make check                                   # Full purification (Lint -> Format -> Type -> Test)
```

### The Ritual of Testing
```bash
make test                                    # Run all tests (Parallel)
make test N=0                                # Run tests Serially (Better for debugging)
make test K="keyword"                        # Filter by test name
make test M="unit"                           # Filter by marker
make test PYTEST_TARGETS="path/to/test.py"   # Targeted file/directory
make test ARGS="-vv --pdb"                   # Pass raw pytest arguments
```

## Implementation Conventions

### Python Style
- **Modern Syntax**: Target Python 3.12+. Use PEP 695 generics (`class Runic[T](...)`).
- **Imports**: Use lazy imports in `on_app_init` / `on_cli_init` hooks to keep boot times fast.
- **Paths**: Never hardcode `~/.config/...`. Use `PATH_*` constants from `src/lychd/system/constants.py`.

### Architecture Boundaries
- **Domain vs System**: Domain computes intent (no side effects); System performs mutations (filesystem, systemd).
- **Settings**: Access via `get_settings()`. Follow precedence: `init -> env -> dotenv -> lychd.toml`.
- **Runes**: Inheriting `RuneConfig` auto-registers schemas and owns a directory in `~/.config/lychd/runes/`.
- **Logging**: Use `structlog` with semantic event IDs and machine-parseable fields. Use `logger.exception(...)` for active exceptions.

### Dependency Policy
Do not hand-edit `pyproject.toml` or `uv.lock`. Use `uv add`, `uv add --dev`, or `uv remove`.

## Critical References
- **[ADR 01: Doctrine](docs/adr/01-doctrine.md)**: Workflow principles.
- **[ADR 11: Backend](docs/adr/11-backend.md)**: Service architecture.
- **[ADR 12: Configuration](docs/adr/12-configuration.md)**: Settings and Runes.
- **[ADR 13: Layout](docs/adr/13-layout.md)**: Filesystem geography.
