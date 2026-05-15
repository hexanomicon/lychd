# Joining the Cult: Contributing to LychD

Read **[AGENTS.md](AGENTS.md)** first — concepts defined there are not repeated here. This file covers the practical rituals: setup commands, implementation conventions, and the authorities that govern specific implementation decisions. Agents and humans alike are expected to internalize both.

## Journal Contract

The journal in `.agents/journal/` is the continuity layer for multi-session work. Treat it as the authoritative handoff record for active and completed workstreams.

- Every chapter begins with `00-intro.md`.
- A chapter is not closed by an ordinary session conclusion. It remains open until it contains a dedicated summary file whose name ends in `-summary.md`.
- If you resume work inside an existing chapter, read `00-intro.md` first and then the latest `*-summary.md` if one exists. If no summary exists yet, read the latest relevant session.
- The operator is responsible for assigning non-conflicting work. Agents are not expected to load unrelated open chapters by default.
- Use the templates in `.agents/journal/templates/` when opening or closing chapters.
- When the journal becomes noisy, open a new summarisation chapter that consumes older chapters into a fresh trustworthy state report.
- After that consuming summary exists, superseded chapters may be moved to `.agents/journal/.old/`. Do not delete journal history by default.

## The Iron Pact (Implicit DCA)

By submitting code, you license your contribution under **MPL-2.0** as defined in **[ADR 00: License](docs/adr/00-license.md)**.

**Implicit Developer Certificate of Origin (DCA):**
There is no CLA to sign, and you do not need to sign your git commits. By reading this contributing guide, you are aware of the Implicit DCA. Everything you commit is automatically covered by this agreement, confirming that you have the right to submit the code under the MPL 2.0 license.

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
- **Vessel (Litestar) Laws**: See **[ADR 11 §6](docs/adr/11-backend.md)** for full mandates:
    1. **Unbound Routing**: Use standalone `Controller` or `Router`. Never use `@app.get`.
    2. **DTO Mandate**: Use `SQLAlchemyDTO`. Never write redundant Pydantic models for ORM.
    3. **Repository Law**: Use `SQLAlchemyAsyncRepository`. Never write raw `session.execute` in routes.
    4. **Native Responses**: Use Litestar's built-in HTMX and OpenTelemetry plugins. No external shims.
- **Dependencies**: Use `uv add` or `uv remove` with proper groups. Ideally do not hand-edit `pyproject.toml`.
- **Frontend Tooling**: Keep the default Altar surface thin (`HTMX + Alpine + Jinja`). Introduce TypeScript when an island has enough client-side logic to justify stronger contracts; do not add a thick SPA runtime by default.
- **Logging**: Use `structlog` with semantic event IDs.
    - Our global config uses `log_exceptions="always"` and an `EventRenamer`.
    - **Convention**: For fatal initialization errors, simply `raise` the exception with a descriptive message. The logger will automatically capture the message and the traceback. Manual `logger.critical()` calls are only needed if you must log an event *without* stopping execution.

## Critical Authorities

For implementation-level guidance, consult the relevant **[Architecture Decision Records](docs/adr/)**.

- **[ADR 01: Doctrine](docs/adr/01-doctrine.md)**: The xDDD workflow.
- **[ADR 11: Backend](docs/adr/11-backend.md)**: Service architecture.
- **[ADR 12: Configuration](docs/adr/12-configuration.md)**: Settings and Runes.
- **[ADR 13: Layout](docs/adr/13-layout.md)**: Filesystem geography.
