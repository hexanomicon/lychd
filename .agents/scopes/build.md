# Build Scope

## Trigger

Load this scope for implementation work under `src/**` or `tests/**`, including application
assembly, persistence, execution, capabilities, agents, orchestration, extensions, and interfaces.
Also load [Architecture](architecture.md) when the implementation changes a decision,
documentation topology, public operation, or delivery truth.

## Authorities

1. [AGENTS.md](../../AGENTS.md) governs repository agents;
   [CONTRIBUTING.md](../../CONTRIBUTING.md) owns implementation and verification conventions.
2. The matching accepted ADR owns the intended technical contract.
3. Tracked source and tests own current implementation evidence.
4. Published topic pages own user operation and interpretation;
   [State of Work](../../docs/state-of-the-work.md) owns delivery status.
5. Ignored `.agents/work/**` and `.agents/journal/**` files are archaeology, never build contracts.

## Probes

- Composition: `src/lychd/app.py`, `src/lychd/extensions/host.py`,
  `src/lychd/config/components.py`
- Persistence: `docs/adr/06-persistence.md`, `src/lychd/db/`,
  `src/lychd/domain/cortex/ledger.py`
- Run execution: `docs/adr/14-workers.md`, `docs/adr/24-graph.md`,
  `src/lychd/domain/cortex/`, `src/lychd/ghouls/runs.py`
- Capabilities and orchestration: `docs/adr/22-dispatcher.md`,
  `docs/adr/23-orchestrator.md`, `src/lychd/domain/animation/`,
  `src/lychd/domain/orchestration/`
- Agent runtime: `docs/adr/20-agents.md`, `src/lychd/agents/`
- Extensions and host effects: `docs/adr/05-extensions.md`, `docs/adr/08-containers.md`,
  `docs/adr/10-privilege.md`, `src/lychd/extensions/`, `src/lychd/system/`

## Optional Reference Probes

After the owning ADR, tracked code, installed package, and lockfile, [references.md](references.md)
may route one bounded comparison for [agent systems](references.md#agent-systems-and-cognition),
[backend/workers](references.md#backend-workers-and-application-structure),
[local inference](references.md#local-inference-hardware-and-packaging),
[vision/ingestion](references.md#vision-and-document-ingestion), or
[developer workflow](references.md#developer-workflow). Examples are not APIs or dependency
justification.

## Verification

- Run targeted lint, type, and test commands from `CONTRIBUTING.md`.
- Before integration, run affected boundary tests and the repository gates appropriate to the
  slice. Do not silently add or weaken skips, timeouts, mocks, snapshots, or negative controls.
- Verify no new caller depends on a facade scheduled for retirement.
- Keep delivery claims synchronized with actual evidence and supported profiles.

## Escalate

Escalate when a worker must guess system truth, two changes own the same semantic boundary, a
schema/effect lacks migration or rollback law, an oracle would need weakening, or a change expands
privilege, exposure, persistence, external effects, or compatibility beyond the accepted contract.
