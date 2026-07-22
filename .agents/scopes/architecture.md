# Architecture Scope

## Trigger

Load this scope for architecture, ADR, doctrine, package-boundary, tracked agent-routing, or
documentation changes that define system truth.

## Authorities

- [AGENTS.md](../../AGENTS.md) defines repository-wide agent behavior.
- [ADR 01](../../docs/adr/01-doctrine.md) owns architectural doctrine and xDDD.
- [ADR 02](../../docs/adr/02-documentation.md) owns documentation topology.
- The [ADR index](../../docs/adr/index.md) routes to the decision that owns a particular invariant.
- [State of the Work](../../docs/state-of-the-work.md) owns granular public delivery boundaries;
  it derives claims from evidence and does not replace ADR law.
- Tracked source and tests establish current implementation evidence. Ignored `.agents/work/**`
  material is review evidence only and cannot override tracked canon.

## Probes

- Doctrine and quality: `docs/adr/01-doctrine.md`, `docs/adr/03-quality.md`,
  `docs/adr/04-testing.md`
- Extension law: `docs/adr/05-extensions.md`, `docs/sepulcher/extensions/`
- Containers and workers: `docs/adr/08-containers.md`, `docs/adr/14-workers.md`
- Security and configuration: `docs/adr/09-security.md`, `docs/adr/12-configuration.md`
- Agents and execution: `docs/adr/20-agents.md`, `docs/adr/22-dispatcher.md`,
  `docs/adr/23-orchestrator.md`, `docs/adr/24-graph.md`, `docs/adr/31-simulation.md`
- Persistence: `docs/adr/06-persistence.md`, `src/lychd/db/`,
  `src/lychd/domain/cortex/`
- Anatomy and assembly: `docs/adr/13-layout.md`, `src/lychd/system/constants.py`,
  `src/lychd/app.py`, `src/lychd/extensions/host.py`, `src/lychd/config/components.py`

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
