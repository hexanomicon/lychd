# Architecture Scope

## Trigger

Load this scope for architecture, ADR, doctrine, package-boundary, tracked agent-routing, or
documentation changes that define system truth.

## Authorities

- [AGENTS.md](../../AGENTS.md) defines repository-wide agent behavior.
- [ADR 01](../../docs/adr/01-doctrine.md) owns architectural doctrine and xDDD.
- [ADR 02](../../docs/adr/02-documentation.md) owns documentation topology.
- The [ADR index](../../docs/adr/index.md) routes to the decision that owns a particular invariant.
- [ADR 28](../../docs/adr/28-workflow.md) owns Weaver and Pattern law; the
  [Composition index](../../docs/compositions/index.md) routes to accepted application designs
  and visibly marked candidate studies.
- [State of the Work](../../docs/state-of-the-work.md) owns granular public delivery boundaries;
  it derives claims from evidence and does not replace ADR law.
- Tracked source and tests establish current implementation evidence. Ignored `.agents/work/**`
  material is review evidence only and cannot override tracked canon.

## Probes

- Doctrine and quality: `docs/adr/01-doctrine.md`, `docs/adr/03-quality.md`,
  `docs/adr/04-testing.md`
- Extension law: `docs/adr/05-extensions.md`, `docs/sepulcher/extensions/`
- Application designs and Pattern catalogues: `docs/compositions/index.md`,
  `docs/adr/28-workflow.md`
- Candidate Patterns, extensions, workloads, and tutorial arcs: `docs/compositions/index.md`;
  page-local maturity controls whether a document is proposal or accepted architecture
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

After canonical owners and current source are clear, the
[local references scope](references.md) routes bounded comparisons:

- [agent systems and cognition](references.md#agent-systems-and-cognition) for Agent, graph,
  memory, A2A/AVP, evaluation, or multi-agent proposals;
- [backend and workers](references.md#backend-workers-and-application-structure) for Litestar,
  SAQ, and application-structure comparisons;
- [local inference and packaging](references.md#local-inference-hardware-and-packaging) for
  Animator, serving, hardware, quantization, or container proposals;
- [vision and ingestion](references.md#vision-and-document-ingestion) for OCR or document-parsing
  proposals.

Read one matching reference only when it improves the decision. No reference can prove acceptance,
delivery, compatibility, performance, or architectural authority.

## Typical Change Surface

This is routing guidance, not authorization. Architecture work commonly touches `docs/adr/**`,
`docs/sepulcher/**`, `AGENTS.md`, `.agents/scopes/**`, and the smallest source/test slice needed to
keep implementation and doctrine synchronized.

## Verification

- Resolve every changed invariant to one owning ADR and one current source boundary.
- When delivery prose changes, run
  `uv run pytest -q tests/architecture/test_state_of_work.py` and verify the cited focused evidence.
- Check links and source hooks with targeted `rg` queries.
- For Markdown-only work, run `git diff --check -- AGENTS.md docs .agents/scopes`.
- For published documentation or navigation changes, run `uv run zensical build --clean`.
- For source-backed decisions, run the targeted and repository gates defined in
  [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Escalate

Escalate when canonical owners disagree, a change would silently reverse an accepted decision,
delivery status cannot be proved, or implementation would require guessing an authority,
persistence, security, recovery, or compatibility contract.
