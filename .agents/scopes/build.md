# Build Scope

## Trigger

Load this scope when implementing wave-plan work under `src/**` or `tests/**` — the run substrate, persistence, capabilities, agents/graph, or the composition root.

## Purpose

Route a builder to the reconciled spec and the delivered source before writing code, so the docs (the Logos) and the build stay coherent. The blueprint under `.agents/work/` is the contract; `docs/**` is the published truth it derives.

## Agent Posture

Spec first, source second. Read the locked rulings before touching a file the wave plan names. Keep `make type-check` green per unit and write tests in the same unit. Do not restate doctrine in code comments that belongs in an ADR.

## Probes

- Locked decisions and lexicon rulings: `.agents/work/INTRODUCTION.md`, `.agents/work/spec-00-FINAL.md`
- Current build state (waves done / in flight): `.agents/journal/CURRENT.md`
- Composition root and process memos: `src/lychd/app.py`, `src/lychd/extensions/host.py`, `src/lychd/config/components.py`, `src/lychd/domain/cortex/substrate.py`
- Persistence: `src/lychd/db/models/`, `src/lychd/db/engine.py`, `src/lychd/db/migrations/versions/0001_phylactery_first_light.py`
- Run substrate: `src/lychd/domain/cortex/{engine,runs,events,ledger}.py`, `src/lychd/ghouls/runs.py`
- Capabilities: `src/lychd/domain/animation/capabilities.py`, `src/lychd/domain/animation/services/`
- Agents and graph: `src/lychd/agents/`, `src/lychd/agents/workflows/`, `src/lychd/domain/cortex/graph_runner.py`
- Governing doctrine: `docs/adr/06-persistence.md`, `docs/adr/14-workers.md`, `docs/adr/22-dispatcher.md`, `docs/adr/23-orchestrator.md`, `docs/adr/24-graph.md`

## Write Bounds

- `src/**`, `tests/**` per the wave plan's per-builder file ownership.
- Docs are out of bounds for build work; a forced doctrine change is routed to the architecture scope, not written inline.

## Verification

- Per-unit: `make type-check`, `make lint`, `make test` (see `CONTRIBUTING.md`).
- DB-backed work: `docker compose up db` (pgvector); keep the in-memory `RunLedger` path DB-free.
- Do not run integration/podman/systemd suites on non-Linux hosts; defer to the Linux pass.
