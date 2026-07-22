# Joining the Cult: Contributing to LychD

Read **[AGENTS.md](AGENTS.md)** first — concepts defined there are not repeated here. This file covers the practical rituals: setup commands, implementation conventions, and the authorities that govern specific implementation decisions. Agents and humans alike are expected to internalize both.

## Agent Context Boundary

LychD's tracked agent context comes from **[AGENTS.md](AGENTS.md)** and the tracked scopes under **[.agents/scopes/](.agents/scopes/)**.

Agents must not load checkout-local overlays such as `.agents/AGENTS.md`, host-level profiles such as `~/.agents/AGENTS.md`, or tool-specific local profiles for this repo unless the operator explicitly assigns one for the current task. Ignored local shelves may exist as private scratch space, but they are not repository authorities and must not be required for LychD to build, test, package, or run.

## The Iron Pact (Implicit DCA)

By submitting code, you license your contribution under **MPL-2.0** as defined in **[ADR 00: License](docs/adr/00-license.md)**.

**Implicit Developer Certificate of Origin (DCA):**
There is no CLA to sign, no private relicensing grant, and no required git sign-off ritual. By submitting a contribution, you certify that you have the right to submit it under MPL-2.0 and agree that it is licensed under MPL-2.0.

## Local Rituals (Setup & Commands)

### Initialization

```bash
make install             # Python dependencies (.venv)
make init                # Initialize local Codex (~/.config/lychd)
make frontend-install    # Altar frontend dependencies (node_modules)
make help                # View all available rituals
```

The Altar's frontend contract is **Vite compatibility**, not a specific JavaScript package manager. The default rituals currently use `npm`; alternatives such as `bun` are acceptable only if they preserve the Litestar/Vite workflow and environment semantics.

### Purification (Quality Control)

```bash
make lint [RUFF_TARGETS="..."]   # Targeted or repo-wide lint
make type-check [TYPECHECK_TARGETS="..."] # Targeted or repo-wide BasedPyright
make check                       # Full purification (Lint -> Type -> Test)
```

When `rtk` is available on `PATH`, Makefile targets automatically route noisy CLI calls through it for compact agent-facing output. If `rtk` is absent, the targets fall back to the underlying tools (`uv`, `npm`, `curl`, `grep`) so bootstrap remains plain.

Use `VERBOSE=1` when an agent or human needs full logs in the terminal/LLM context. It disables RTK filtering for that invocation and makes pytest stream stdout plus long tracebacks. Pytest's debug log streaming is already configured in `pyproject.toml`.

### The Ritual of Testing

```bash
make test                        # Run all tests (Parallel)
make test N=0                    # Run tests Serially (Better for debugging)
make test PYTEST_TARGETS="..."   # Targeted file/directory
make test VERBOSE=1              # Full raw pytest output/logs; no RTK filtering
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
- **Documentation**: Follow **[ADR 01 §Documentation Topology](docs/adr/01-doctrine.md#documentation-topology)**. Keep root entry doors (`README.md`, `CONTRIBUTING.md`, `AGENTS.md`) thin and routed; put architectural law in ADRs, canonical terms in `docs/lexicon.md`, published orientation in `docs/index.md`, accepted application contracts in `docs/compositions/`, domain doctrine in Sepulcher/Divination pages, uncommitted proposals in `docs/incubator/`, and routing hints in `.agents/scopes/`. Composition pages are accepted architecture but not delivery evidence; Incubator pages are neither accepted architecture nor actionable backlog. When a docs change moves system truth, update the links and hints that route readers to that truth.
- **Vessel (Litestar) Laws**: See **[ADR 11 §6](docs/adr/11-backend.md)** for full mandates:
    1. **Unbound Routing**: Use standalone `Controller` or `Router`. Never use `@app.get`.
    2. **DTO Mandate**: Use `SQLAlchemyDTO`. Never write redundant Pydantic models for ORM.
    3. **Repository Law**: Use `SQLAlchemyAsyncRepository`. Never write raw `session.execute` in routes.
    4. **Native Responses**: Use Litestar's built-in HTMX and OpenTelemetry plugins. No external shims.
- **Dependencies**: Use `uv add` or `uv remove` with proper groups. Ideally do not hand-edit `pyproject.toml`.
- **Frontend Tooling**: Keep the default Altar surface thin (`HTMX + Alpine + Jinja`). Introduce TypeScript and Vite-compiled Svelte only for bounded instrument islands with enough client-side logic to justify stronger contracts; do not add a thick SPA runtime by default.
- **Logging**: Use `structlog` with semantic event IDs.
    - Our global config uses `log_exceptions="always"` and an `EventRenamer`.
    - **Convention**: For fatal initialization errors, simply `raise` the exception with a descriptive message. The logger will automatically capture the message and the traceback. Manual `logger.critical()` calls are only needed if you must log an event *without* stopping execution.

## Critical Authorities

For implementation-level guidance, consult the relevant **[Architecture Decision Records](docs/adr/)**.

- **[ADR 01: Doctrine](docs/adr/01-doctrine.md)**: The xDDD workflow.
- **[ADR 11: Backend](docs/adr/11-backend.md)**: Service architecture.
- **[ADR 12: Configuration](docs/adr/12-configuration.md)**: Settings and Runes.
- **[ADR 13: Layout](docs/adr/13-layout.md)**: Filesystem geography.
