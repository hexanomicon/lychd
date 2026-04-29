# Joining the Cult: Contributing to LychD

Read **[AGENTS.md](AGENTS.md)** first — concepts defined there are not repeated here. This file covers the practical rituals: setup commands, implementation conventions, and the authorities that govern specific implementation decisions. Agents and humans alike are expected to internalize both.

## The Iron Pact (No CLA)

By submitting code, you license your contribution under **AGPL-3.0-or-later** as defined in **[ADR 00: License](docs/adr/00-license.md)**.

## Local Rituals (Setup & Commands)

### Initialization

```bash
make install             # Python dependencies (.venv)
make init                # Initialize local Codex (~/.config/lychd)
make frontend-install    # Altar frontend dependencies (node_modules)
make help                # View all available rituals
```

### Purification (Quality Control)

```bash
make lint [RUFF_TARGETS="..."]   # Targeted or repo-wide lint
make type-check [TYPECHECK_TARGETS="..."] # Targeted or repo-wide BasedPyright
make check                       # Full purification (Lint -> Type -> Test)
```

### The Ritual of Testing

```bash
make test                        # Run all tests (Parallel)
make test N=0                    # Run tests Serially (Better for debugging)
make test PYTEST_TARGETS="..."   # Targeted file/directory
```

### The Ritual of Jujutsu (JJ)

LychD embraces **Jujutsu (jj)** as a first-class alternative to Git. Its "working-copy-as-a-commit" model aligns perfectly with our autopoietic nature, providing implicit checkpointing for both the Magus and the Agents.

```bash
jj st               # Check the state of the current change
jj log              # Visualize the revision graph
jj describe         # Add a name (commit message) to the current intent
jj new              # Begin a new speculative timeline (branch)
jj diff             # Inspect the current manifestations
jj git push         # Synchronize with the external world (Git remotes)
```

> [!TIP]
> Conflicts in `jj` are first-class citizens. They do not block your workflow; they are captured as part of the revision graph until you are ready to resolve them. This is the preferred way to handle temporal collisions in the Shadow Realm.

## Implementation Conventions

- **Python**: Target 3.12+. Use PEP 695 generics. Use lazy imports in boot hooks.
- **Paths**: Never hardcode `~/.config/...`. Use `PATH_*` constants from `src/lychd/system/constants.py`.
- **Boundaries**: Domain computes intent (pure); System performs mutations (filesystem, systemd).
- **Logging**: Use `structlog` with semantic event IDs. Use `logger.exception(...)` for active exceptions.
- **Dependencies**: Use `uv add` or `uv remove`. Do not hand-edit `pyproject.toml`.

## Critical Authorities

For implementation-level guidance, consult the relevant **[Architecture Decision Records](docs/adr/)**.

- **[ADR 01: Doctrine](docs/adr/01-doctrine.md)**: The xDDD workflow.
- **[ADR 11: Backend](docs/adr/11-backend.md)**: Service architecture.
- **[ADR 12: Configuration](docs/adr/12-configuration.md)**: Settings and Runes.
- **[ADR 13: Layout](docs/adr/13-layout.md)**: Filesystem geography.
