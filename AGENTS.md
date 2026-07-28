# AGENTS.md

This is the coding-agent entrypoint for [LychD](README.md). It defines the shared repo contract for agents and tools working here. Read [CONTRIBUTING.md](CONTRIBUTING.md) for setup commands, implementation conventions, and human-facing contribution rules.

## Probe Map

This file is the stable entry node. Load only the next probe needed by the task; do not drag the whole castle into context.

- [CONTRIBUTING.md](CONTRIBUTING.md): setup commands, quality commands, conventions.
- Public/user orientation: [README.md](README.md), then [docs/index.md](docs/index.md) when the published Hexanomicon entry matters.
- Current delivery boundary: [docs/state-of-the-work.md](docs/state-of-the-work.md), loaded when a
  claim depends on what is Available, requires Operator validation, is Partial, remains Designed,
  is Experimental, or belongs to an External project.
- Terminology: [docs/lexicon.md](docs/lexicon.md), loaded when vocabulary or lore/code naming boundaries matter.
- Lore/identity: [docs/sepulcher/lich/index.md](docs/sepulcher/lich/index.md), loaded only for voice-sensitive docs or doctrine work.
- The Great Work: [docs/divination/transcendence/index.md](docs/divination/transcendence/index.md),
  loaded for mythic doctrine, source correspondence, formation, consciousness, eschatology, or
  philosophical voice; route through
  [.agents/scopes/transcendence.md](.agents/scopes/transcendence.md) before selecting a stage.
- Frontend/Altar: route through [.agents/scopes/frontend.md](.agents/scopes/frontend.md) before
  analyzing, editing, or reviewing `frontend/**`, Svelte/SvelteKit code, browser projection, or
  native CSS. The scope routes agents to the official Svelte AI tools and ADR 15 constraints.
- Application designs and candidate futures: [docs/compositions/index.md](docs/compositions/index.md),
  loaded when a task concerns the Portfolio, an application Pattern catalogue, cross-organ
  ownership, or promotion from idea into accepted architecture. Each page declares its own
  maturity; directory membership proves neither acceptance nor delivery.
- Optional external probes: route through
  [.agents/scopes/references.md](.agents/scopes/references.md) when a task benefits from comparison
  with the operator's checkout-local reference shelf. The shelf is never authority or a build
  dependency, and its absence is non-blocking.
- [.agents/scopes/](.agents/scopes/): official tracked agent extension for bounded context routing. LychD allows this shared extension and ignores the rest of `.agents/*`.
- Local overlays: do not load `.agents/AGENTS.md`, `~/.agents/AGENTS.md`, or tool-specific local profiles for this repo unless the operator explicitly assigns one for the current task.

## Context Discovery

Progressive context loading is mandatory. Treat this entrypoint like a Django root URLconf:
`AGENTS.md` selects a domain scope, that scope selects the smallest relevant authority or probe,
and the leaf documentation/source owns the actual behavior.

- When a tracked scope's Trigger matches, read that scope completely before task action and respect
  its Authorities, Probes, Verification, and Escalate sections.
- Do not skip a matching scope, load every scope speculatively, or jump from this root directly
  into a large documentation tree or local reference shelf.
- Load one cheapest useful edge at a time. Add another scope only when the task genuinely crosses
  domains.
- A scope routes context; it never overrides an ADR, State of the Work, tracked source, tests,
  lockfiles, or maintained receipts.
- If a routed path is missing or stale, do not guess. Use the next authoritative probe and repair
  the routing only when that maintenance is within the task.

Then follow the cheapest useful edge:

1. Use innate knowledge for stable basics.
2. Load a matching tracked scope from `.agents/scopes/` when one exists. For architecture, ADR, doctrine, tracked agent routing, or docs that define system truth, load [.agents/scopes/architecture.md](.agents/scopes/architecture.md).
3. For frontend or Altar implementation work, load
   [.agents/scopes/frontend.md](.agents/scopes/frontend.md) before touching Svelte files.
4. For the Great Work, philosophy, mythic doctrine, or formation work, load
   [.agents/scopes/transcendence.md](.agents/scopes/transcendence.md) and follow its smallest
   canonical path. Do not infer delivery from the Logos.
5. For documentation work, use [docs/index.md](docs/index.md) as the published parent map,
   [docs/lexicon.md](docs/lexicon.md) for terms, and directory `index.md` files before child pages.
   Route application architecture and unselected possibilities through
   [docs/compositions/index.md](docs/compositions/index.md); use the page's declared maturity
   rather than its directory as the acceptance boundary.
6. Inspect LychD source and `src/lychd/system/constants.py` for project truth.
7. Inspect installed packages under `.venv/lib/` when dependency runtime behavior matters.
8. When an external implementation or research comparison would help, load
   [.agents/scopes/references.md](.agents/scopes/references.md) and follow one matching edge into the
   operator-assigned local shelf. Do not inventory or load the whole shelf.
9. Probe with shell commands.
10. Ask the operator when context is still insufficient. If they are AFK, exhaust internal archaeology and shell probing first.

## Working Rules

- **xDDD**: eXtreme Documentation Driven Development. Establish the Logos first: write the truth,
  vocabulary, and boundaries in the right layer, then derive domain language and implementation
  from it. Myth is constitutional telos, not disposable styling; it may never impersonate delivery
  evidence. Lore belongs in docs/docstrings; engineering belongs in code/logs.
- **Delivery Ownership**: [State of the Work](docs/state-of-the-work.md) owns public delivery
  boundaries. ADRs own decisions; topic pages own operation; source, focused tests, lockfiles, and
  maintained receipts own executable evidence.
- **Documentation Topology**: For docs changes, follow [ADR 01 §Documentation Topology](docs/adr/01-doctrine.md#documentation-topology) and the documentation convention in [CONTRIBUTING.md](CONTRIBUTING.md#implementation-conventions). Keep AGENTS.md as an entrypoint, not the full doctrine.
- **No Guessing**: do not hallucinate paths, APIs, or behavior.
- **Dynamic Sync**: if code changes system truth, update the matching docs.
- **Trust Verification**: when asked whether something is solid, audit the critical chain and report findings instead of reassurance.
