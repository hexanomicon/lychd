# Build Scope

## Trigger

Load this scope for implementation work under `src/**` or `tests/**`, including application
assembly, persistence, execution, capabilities, agents, orchestration, extensions, and interfaces.

## Authorities

- [AGENTS.md](../../AGENTS.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md) define repository and
  verification behavior.
- The matching accepted ADR owns the intended technical contract.
- Tracked source and tests own current implementation evidence.
- Published Sepulcher and Divination pages own user-facing behavior.
- Ignored `.agents/work/**` and `.agents/journal/**` files may inform archaeology only; they are
  never build contracts.

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

After inspecting tracked code, installed packages, and the owning ADR, use the
[local references scope](references.md) for one bounded implementation comparison:

- [agent systems and cognition](references.md#agent-systems-and-cognition);
- [backend, workers, and application structure](references.md#backend-workers-and-application-structure);
- [local inference, hardware, and packaging](references.md#local-inference-hardware-and-packaging);
- [vision and document ingestion](references.md#vision-and-document-ingestion);
- [developer workflow](references.md#developer-workflow).

Examples are not APIs. Check the lockfile and installed package source before adapting behavior,
and add no dependency merely because a reference uses it.

## Typical Change Surface

This is routing guidance, not authorization. A build slice normally changes one semantic owner,
its narrow source paths, its independent oracle under `tests/**`, and the canonical delivery/user
documentation needed for dynamic synchronization. New packages land only with a real caller,
implementation, failure contract, and test.

## Verification

- Run the targeted lint, type, and test commands from `CONTRIBUTING.md` during development.
- Before integration, run the affected boundary tests and the repository gates appropriate to the
  slice; do not add or weaken skips, timeouts, mocks, snapshots, or negative controls silently.
- Verify no new caller depends on a facade scheduled for retirement.
- Keep delivery claims synchronized with actual evidence and supported profiles.

## Escalate

Escalate when a worker must guess system truth, two changes own the same semantic boundary, a
schema/effect lacks migration or rollback law, an oracle would need weakening, or a change expands
privilege, exposure, persistence, external effects, or compatibility beyond the accepted contract.
