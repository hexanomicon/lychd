# AGENTS.md

This is the coding-agent entrypoint for [LychD](README.md). It defines the shared repo contract for agents and tools working here. Read [CONTRIBUTING.md](CONTRIBUTING.md) for setup commands, implementation conventions, and human-facing contribution rules.

## Probe Map

This file is the stable entry node. Load only the next probe needed by the task; do not drag the whole castle into context.

- [CONTRIBUTING.md](CONTRIBUTING.md): setup commands, quality commands, conventions.
- Lore/identity: [docs/sepulcher/lich.md](docs/sepulcher/lich.md), loaded only for voice-sensitive docs or doctrine work.
- [.agents/scopes/](.agents/scopes/): official tracked agent extension for bounded context routing. LychD allows this shared extension and ignores the rest of `.agents/*`.
- Local overlays: do not load `.agents/AGENTS.md`, `~/.agents/AGENTS.md`, or tool-specific local profiles for this repo unless the operator explicitly assigns one for the current task.

## Context Discovery

Follow the cheapest useful edge:

1. Use innate knowledge for stable basics.
2. Load a matching tracked scope from `.agents/scopes/` when one exists. For architecture, ADR, doctrine, tracked agent routing, or docs that define system truth, load [.agents/scopes/architecture.md](.agents/scopes/architecture.md).
3. Inspect LychD source and `src/lychd/system/constants.py` for project truth.
4. Inspect installed packages under `.venv/lib/` when dependency runtime behavior matters.
5. Use ignored local reference shelves only when the operator explicitly assigns them.
6. Probe with shell commands.
7. Ask the operator when context is still insufficient. If they are AFK, exhaust internal archaeology and shell probing first.

## Working Rules

- **xDDD**: eXtreme Documentation Driven Development. Establish the Logos first: write the truth, vocabulary, and boundaries in the right layer, then derive domain language and implementation from it. Lore belongs in docs/docstrings; engineering belongs in code/logs.
- **No Guessing**: do not hallucinate paths, APIs, or behavior.
- **Dynamic Sync**: if code changes system truth, update the matching docs.
- **Trust Verification**: when asked whether something is solid, audit the critical chain and report findings instead of reassurance.
