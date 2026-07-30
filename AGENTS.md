# AGENTS.md

This is the coding-agent entrypoint for [LychD](README.md). It routes context and states the
repository-wide working contract. [CONTRIBUTING.md](CONTRIBUTING.md) owns setup, commands, and
human-facing contribution rules.

## Authority

- ADRs own accepted architectural decisions.
- [State of Work](docs/state-of-the-work.md) owns public delivery status.
- Tracked source, focused tests, lockfiles, and maintained receipts own executable evidence.
- Topic pages own user operation and interpretation within those boundaries.
- Scope files route context only; they cannot override any owner above.
- Workflow playbooks prescribe task procedure only; they cannot create architectural, delivery,
  or executable truth.
- Ignored `.agents/work/**`, journals, local shelves, and tool profiles are never project truth.

When owners disagree, do not reconcile them in prose. Find the stale owner or escalate.

## Scope router

Load one matching scope before task action:

| Trigger | Scope |
|---|---|
| ADRs, doctrine, package boundaries, system-truth documentation, or tracked agent routing | [.agents/scopes/architecture.md](.agents/scopes/architecture.md) |
| Implementation or tests under `src/**` or `tests/**` | [.agents/scopes/build.md](.agents/scopes/build.md) |
| `frontend/**`, browser projection, Svelte/SvelteKit, Vite, or native CSS | [.agents/scopes/frontend.md](.agents/scopes/frontend.md) |
| Published Divination pages, Altar reader journey, or Zensical navigation | [.agents/scopes/divination.md](.agents/scopes/divination.md) |
| The Great Work, mythic voice, formation, consciousness, cosmology, or eschatology | [.agents/scopes/transcendence.md](.agents/scopes/transcendence.md) |
| Optional comparison with the checkout-local reference shelf | [.agents/scopes/references.md](.agents/scopes/references.md), after the primary scope |

The frontend scope routes onward to the Svelte scope when required. Cross-domain work may load a
second scope only when the task actually crosses that boundary.

## Workflow router

Load a workflow only after the matching scope and only when the task performs that operation:

| Trigger | Workflow |
|---|---|
| Greenfield rewrite, compression, or topology redesign of documentation | [.agents/workflows/nuance-preserving-rewrite.md](.agents/workflows/nuance-preserving-rewrite.md) |
| Editing tracked source or tests | [.agents/workflows/editing/index.md](.agents/workflows/editing/index.md), then one just-in-time file-type card when available |
| Designing or operating delegated coding-agent labor | [.agents/workflows/delegated-coding.md](.agents/workflows/delegated-coding.md) |

Do not preload every workflow or file-type card. A workflow governs method; the selected scope and
canonical owners still govern truth.

## Primary probes

- Development commands and conventions: [CONTRIBUTING.md](CONTRIBUTING.md)
- Public entry: [README.md](README.md), then [docs/index.md](docs/index.md)
- Whole-system relation map: [docs/map.md](docs/map.md), only when that view is cheaper than one
  owning page
- Delivery claims: [docs/state-of-the-work.md](docs/state-of-the-work.md)
- Vocabulary: [docs/lexicon/index.md](docs/lexicon/index.md)
- Lore and identity: [docs/sepulcher/lich/index.md](docs/sepulcher/lich/index.md)
- Application designs and candidate futures: [docs/compositions/index.md](docs/compositions/index.md);
  page-local maturity controls
- System constants: `src/lychd/system/constants.py`

For documentation, enter through `docs/index.md`, the relevant directory `index.md`, and then the
smallest owning leaf. Do not inventory a tree when one route answers the task.

## Discovery protocol

1. Use stable knowledge for stable basics.
2. Read the complete matching scope.
3. Follow its cheapest authoritative probe.
4. Inspect the smallest source and test slice that can establish current behavior.
5. Inspect `.venv/lib/` when installed dependency behavior matters.
6. Use shell probes to close remaining uncertainty.
7. Ask the operator only after internal archaeology is exhausted.

Do not guess paths, APIs, delivery, compatibility, or recovery behavior. If a routed path is stale,
use the next authority and repair the route only when routing maintenance is in scope.

Do not load `.agents/AGENTS.md`, `~/.agents/AGENTS.md`, or tool-specific local profiles unless the
operator assigns one for the current task.

## Working contract

- **xDDD:** establish the Logos—truth, vocabulary, and boundaries in the owning documentation—then
  derive implementation. Myth is constitutional telos, not decorative copy and not delivery
  evidence.
- **Documentation topology:** follow
  [ADR 01 §Documentation Topology](docs/adr/01-doctrine.md#documentation-topology). Root files are
  entry doors, not duplicate manuals.
- **Dynamic sync:** when code changes system truth, update its owner and any route or delivery
  record made stale by the change.
- **Trust verification:** when asked whether something is solid, inspect the critical chain and
  report findings rather than reassurance.
- **Progressive context:** load one useful edge at a time. A broad task does not justify speculative
  ingestion of the repository or local reference shelf.

For docs changes, verify local links and run the architecture State test when delivery prose
moves. For published routes or navigation, run a clean Zensical build. For source changes, use the
focused and repository gates in CONTRIBUTING and the selected scope.
