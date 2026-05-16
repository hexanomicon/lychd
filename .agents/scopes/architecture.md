# Architecture Scope

## Trigger

Load this scope when changing architecture, ADRs, doctrine, tracked agent routing, or docs that define system truth.

## Purpose

Route architecture work through the smallest trustworthy set of docs and source hooks before writing.

## Agent Posture

Spec first, source second, prose last. Prefer updating existing doctrine over inventing parallel explanations.

## Probes

- ADR index: `docs/adr/index.md`
- Doctrine and quality: `docs/adr/01-doctrine.md`, `docs/adr/03-quality.md`
- Extension law: `docs/adr/05-extensions.md`, `docs/sepulcher/extensions/`
- Containers and workers: `docs/adr/08-containers.md`, `docs/adr/14-workers.md`
- Security and configuration: `docs/adr/09-security.md`, `docs/adr/12-configuration.md`
- Agent and simulation architecture: `docs/adr/20-agents.md`, `docs/adr/31-simulation.md`
- Anatomy: `src/lychd/system/constants.py`, `docs/adr/13-layout.md`
- Runtime source hooks: `src/lychd/config/`, `src/lychd/app.py`, `src/lychd/domain/animation/`, `src/lychd/extensions/`

## Write Bounds

- `docs/adr/**`
- `docs/sepulcher/**`
- `AGENTS.md`
- `.agents/scopes/**`
- Source files only when the architecture change also requires implementation sync.

## Verification

- Check links and source hooks with targeted `rg`.
- Run `git diff --check -- AGENTS.md docs .agents/scopes` for Markdown-only changes.
- For source-backed architecture changes, add targeted lint/type/test commands from `CONTRIBUTING.md`.
