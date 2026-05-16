# AGENTS.md

This is the coding-agent entrypoint for [LychD](README.md). It defines the shared repo contract for agents and tools working here. Read [CONTRIBUTING.md](CONTRIBUTING.md) for setup commands, implementation conventions, and human-facing contribution rules.

## Local Agent Overlay

LychD deliberately supports checkout-local and operator-local agent overlays. The tracked repo contract registers the socket; local files define the operator's preferred discipline.

Before nontrivial work, agents should load the first relevant overlay that exists:

1. `.agents/AGENTS.md` inside this checkout.
2. `~/.agents/AGENTS.md` on the host, when the operator has configured one.
3. Tool-specific profiles such as `~/.claude/CLAUDE.md` or Codex rules.

Local overlays may define shell discipline, VCS practice, journaling workflow, drift ledgers, personas, scratch-space layout, and reference shelves. They must not weaken tracked repository law, change LychD runtime behavior, or become required for LychD to build, test, package, or run.

If no local overlay exists, continue from this file, `CONTRIBUTING.md`, relevant docs, and source.

## Probe Map

This file is the stable entry node. Load only the next probe needed by the task; do not drag the whole castle into context.

- [CONTRIBUTING.md](CONTRIBUTING.md): setup commands, quality commands, conventions.
- Lore/identity: [docs/sepulcher/lich.md](docs/sepulcher/lich.md), loaded only for voice-sensitive docs or doctrine work.
- [.agents/scopes/](.agents/scopes/): official tracked agent extension for bounded context routing. LychD allows this shared extension and ignores the rest of `.agents/*`.
- Local overlays: `.agents/AGENTS.md` or `~/.agents/AGENTS.md` may route ignored local memory such as journals, drift ledgers, references, personas, and work artifacts.

## Context Discovery

Follow the cheapest useful edge:

1. Use innate knowledge for stable basics.
2. Load the local agent overlay when present and relevant.
3. Load a matching tracked scope from `.agents/scopes/` when one exists. For architecture, ADR, doctrine, tracked agent routing, or docs that define system truth, load [.agents/scopes/architecture.md](.agents/scopes/architecture.md).
4. Inspect LychD source and `src/lychd/system/constants.py` for project truth.
5. Inspect installed packages under `.venv/lib/` when dependency runtime behavior matters.
6. Use local reference shelves only when an overlay or the operator assigns them.
7. Probe with shell commands.
8. Ask the operator when context is still insufficient. If they are AFK, exhaust internal archaeology and shell probing first.

## Working Rules

- **xDDD**: eXtreme Documentation Driven Development. Establish the Logos first: write the truth, vocabulary, and boundaries in the right layer, then derive domain language and implementation from it. Lore belongs in docs/docstrings; engineering belongs in code/logs.
- **No Guessing**: do not hallucinate paths, APIs, or behavior.
- **Dynamic Sync**: if code changes system truth, update the matching docs.
- **Trust Verification**: when asked whether something is solid, audit the critical chain and report findings instead of reassurance.
