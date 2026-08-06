# Architecture Scope

## Trigger

Load this scope for architecture, ADR, doctrine, package-boundary, tracked agent-routing, or
documentation changes that define system truth.
Also load [Build](build.md) when the task implements that truth under `src/**` or `tests/**`.

## Authorities

1. [AGENTS.md](../../AGENTS.md) governs repository agents.
2. [ADR 01](../../docs/adr/01-doctrine.md) owns architecture and xDDD;
   [Documentation Topology](../../docs/adr/01-doctrine.md#documentation-topology) owns document
   placement. ADR 02 is the historical record, not current topology law.
3. The [ADR index](../../docs/adr/index.md) routes each invariant to its accepted decision.
   For every Covenant task, read that index before opening or editing a numbered ADR; its closed
   register and ownership map determine which existing Covenant must be amended or rewritten.
   [ADR 28](../../docs/adr/28-workflow.md) owns Weaver and Pattern law; the
   [Composition index](../../docs/compositions/index.md) routes accepted designs and candidate
   studies according to each page's declared maturity.
4. [State of Work](../../docs/state-of-the-work.md) owns evidence-backed delivery status; it does
   not replace ADR law.
5. Tracked source and tests establish implementation evidence. Ignored `.agents/work/**` material
   may support review but cannot override tracked canon.
6. Tracked [workflow playbooks](../workflows/index.md) own repeatable procedure only and load after
   this scope; they cannot settle architecture, delivery, or implementation truth.

## Probes

- Covenants: `docs/adr/index.md` first, then the smallest existing owning ADR. Never infer a new
  Covenant number from the directory or bypass the index's closed-register law.
- Doctrine and quality: `docs/adr/01-doctrine.md`, `docs/adr/03-quality.md`,
  `docs/adr/04-testing.md`
- Extension law: `docs/adr/05-extensions.md`, `docs/sepulcher/extensions/`
- Native application contracts, Pattern catalogues, and workloads:
  `docs/compositions/index.md`, `docs/adr/28-workflow.md`; Portfolio membership accepts the
  reference contract, each leaf states current material, and State keeps the shared evidence envelope
- Containers and workers: `docs/adr/08-containers.md`, `docs/adr/14-workers.md`
- Security and configuration: `docs/adr/09-security.md`, `docs/adr/12-configuration.md`
- Agents and execution: `docs/adr/20-agents.md`, `docs/adr/22-dispatcher.md`,
  `docs/adr/23-orchestrator.md`, `docs/adr/24-graph.md`, `docs/adr/31-simulation.md`
- Persistence: `docs/adr/06-persistence.md`, `src/lychd/db/`,
  `src/lychd/domain/cortex/`
- Host lifecycle and Pulse: `docs/adr/13-layout.md`, `docs/adr/19-cli.md`,
  `src/lychd/cli/`, `src/lychd/system/readiness/`,
  `src/lychd/system/services/lifecycle/`
- Anatomy and assembly: `docs/adr/13-layout.md`, `src/lychd/system/constants.py`,
  `src/lychd/app.py`, `src/lychd/extensions/host.py`, `src/lychd/config/components.py`

## Optional Reference Probes

After canon and source are clear, [references.md](references.md) may route one bounded comparison
for [agent systems](references.md#agent-systems-and-cognition),
[backend/workers](references.md#backend-workers-and-application-structure),
[local inference](references.md#local-inference-hardware-and-packaging), or
[vision/ingestion](references.md#vision-and-document-ingestion). It cannot establish authority,
acceptance, delivery, compatibility, or performance.

## Verification

- Resolve every changed invariant to one owning ADR and one current source boundary.
- For delivery prose, run
  `make test PYTEST_TARGETS=tests/architecture/test_state_of_work.py N=0` and verify its cited
  focused evidence.
- Check links and source hooks with targeted `rg` queries.
- For Markdown-only work, run
  `git diff --check -- AGENTS.md docs .agents/scopes .agents/workflows`.
- For published documentation or navigation changes, run `uv run zensical build --clean`.
- For source-backed decisions, run the targeted and repository gates defined in
  [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Escalate

Escalate when canonical owners disagree, a change would silently reverse an accepted decision,
delivery status cannot be proved, or implementation would require guessing an authority,
persistence, security, recovery, or compatibility contract.
