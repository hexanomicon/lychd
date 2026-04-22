# AGENTS.md

Operational guardrails and resource mapping for autonomous coding agents.

## Source of Truth

- `docs/`: Lore, metaphors, and conceptual framing.
- `docs/adr/`: Technical architecture decisions and constraints (The primary authority).
- `docs/adr/01-doctrine.md`: xDDD workflow doctrine.
- `docs/adr/03-quality.md`: Quality gates and tooling doctrine.
- `docs/adr/04-testing.md`: Testing strategy and verification doctrine.
- `docs/adr/12-configuration.md`: Codex + schema authority.
- `docs/adr/13-layout.md`: Filesystem geography and mount doctrine.
- `Makefile`: Canonical command surface for developer rituals.
- [DRIFT.md](DRIFT.md): Ledger of recurring agent mistakes (Review before coding).

When in doubt, ADRs win.

## Context & Workflow

- **Developer Workflow**: Defer to [CONTRIBUTING.md](CONTRIBUTING.md) for setup, commands, and implementation conventions.
- **Shell Awareness**: The host environment likely uses `fish` shell. Commands should be shell-agnostic or explicitly adapted if they rely on shell-specific features.
- **HiTL Context**: The user (`Magus`) uses `ctx` (a local fish function/script) for context management and "context catapulting." Treat `ctx` output as valid HiTL input.

## External Reference Discovery

When tasking requires external library/framework documentation, **do not assume or hallucinate behavior.**

1. **Look it up**: Use the repo-local helper `scripts/refctx.py` to discover and inspect staged references.
2. **Ask Magus**: If `refctx.py` returns no matches or is insufficient, ask Magus to find the info or stage it under `~/Documents/References/`.

**Crucial Rule**: Agent should **never assume** something he doesn't know. If an API contract or framework behavior is unclear, reference lookup is mandatory.

### Canonical Reference Root
All external docs intended for agent consumption live under `~/Documents/References/`.

### `refctx.py` Workflow
Use `uv run` to execute the helper. It is stdlib-only and resolves targets within the reference root.

```bash
uv run python scripts/refctx.py --list
uv run python scripts/refctx.py --find <query>
uv run python scripts/refctx.py -l -d 2 <path>
uv run python scripts/refctx.py -s 80 -d 3 <path>
```

Recommended sequence: **List/Find -> Scout (-l/-t) -> Spy (-s) -> Extract**.

## Operational Guardrails

1. **Adhere to ADRs**: Do not deviate from architectural decisions recorded in `docs/adr/`.
2. **Never Assume**: If you lack context on a dependency or system behavior, use `refctx.py` or ask Magus.
3. **Path Integrity**: Use `PATH_` constants from the core system. Never hardcode absolute paths.
4. **Mock the Host**: Never touch the physical host directly during tests. Use mocks to simulate the environment.
5. **No Side Effects**: CLI commands are entry points; true power must reside within service/domain layers.
6. **Direct Research**: Use `rg`, `sed`, `cat`, and other standard tools to inspect the workspace directly.
