# AGENTS.md

This is the coding-agent entrypoint and working contract for [LychD](README.md).
[CONTRIBUTING.md](CONTRIBUTING.md) owns setup, commands, and human contribution rules. Read its
[current collaboration phase](CONTRIBUTING.md#branches-and-everyday-collaboration) before choosing
a branch, committing, pushing, or opening a pull request; follow its
[coordination preflight](CONTRIBUTING.md#coordinate-before-starting-work) before proposing or
starting substantial work.

## Authority

- ADRs own accepted architecture; [State of Work](docs/state-of-the-work.md) owns public delivery
  status.
- Tracked source, focused tests, lockfiles, and maintained receipts own executable evidence.
- Topic pages own user operation and interpretation within those boundaries.
- Scopes route context; workflows prescribe procedure. Neither overrides those owners or creates
  architectural, delivery, or executable truth.
- Ignored `.agents/work/**`, journals, local shelves, and tool profiles are never project truth.

When owners disagree, find the stale owner or escalate. Do not reconcile them in prose.

## Scope router

Read one complete matching scope before task action:

| Trigger | Scope |
|---|---|
| ADRs, doctrine, package boundaries, system-truth documentation, or tracked agent routing | [Architecture](.agents/scopes/architecture.md) |
| Implementation or tests under `src/**`, `tests/**`, or `clients/android/**` | [Build](.agents/scopes/build.md) |
| `clients/web/**`, browser projection, Svelte/SvelteKit, Vite, or native CSS | [Frontend](.agents/scopes/frontend.md) |
| Divination (Transmutation, Transcendence, Altar, or Correspondence), the Great Work, mythic or philosophical interpretation, formation, consciousness, identity, or published documentation navigation | [Divination](.agents/scopes/divination.md) |
| Finding reference implementations for a local capability, or checking a named or decision-relevant external technology, protocol, library, project, or benchmark | [References](.agents/scopes/references.md), after the primary scope |

Frontend routes onward to Svelte when required. Backend work under `src/**` or `tests/**` starts
with Build; add Frontend only for browser, OpenAPI, or SSE projection changes. Load a second
domain scope only when the task crosses that boundary.

## Workflow router

After the matching scope, load only workflows for operations the task performs; do not preload
file-type cards.

| Trigger | Workflow |
|---|---|
| Greenfield rewrite, compression, or topology redesign of documentation | [Nuance-preserving rewrite](.agents/workflows/nuance-preserving-rewrite.md) |
| Editing tracked source or tests | [Editing](.agents/workflows/editing/index.md), then one just-in-time file-type card when available |
| Designing or operating delegated coding-agent labor | [Delegated coding](.agents/workflows/delegated-coding.md) |
| Introducing, moving, renaming, or changing a capability, contract, procedure, or context route | [Context-loading verification](.agents/workflows/context-loading.md), after the primary workflow when applicable |

Context-loading completion includes finding the changed truth from realistic questions without
supplied paths or answers; shared-router changes also check a neighboring task through that
workflow.

## Primary probes

- Commands and conventions: [CONTRIBUTING.md](CONTRIBUTING.md)
- Public entry: [README.md](README.md), then [docs/index.md](docs/index.md)
- Whole-system relations: [docs/map.md](docs/map.md), only when cheaper than one owning page
- Delivery: [State of Work](docs/state-of-the-work.md)
- Vocabulary: [Lexicon](docs/lexicon/index.md)
- Lore and identity: [Lich](docs/sepulcher/lich/index.md)
- Native application contracts, worked examples, and local current material:
  [Compositions](docs/compositions/index.md); State keeps the shared whole-system evidence envelope
- System constants: `src/lychd/system/constants.py`

## Discovery protocol

This protocol loads coding-agent context, not [runtime Context](docs/adr/21-context.md). Load one
useful edge at a time; a broad task does not justify speculative repository or reference-shelf
ingestion.

1. Frame the concrete question and answer needed: architecture, delivery, vocabulary, operation,
   implementation evidence, or procedure. Use stable knowledge for stable basics.
2. Follow the matching scope to its cheapest authoritative probe. If no trigger fits, use the
   nearest [primary probe](#primary-probes) and record the missing trigger, not a successful route.
3. For documentation, follow `docs/index.md`, the relevant directory `index.md`, and the smallest
   owning leaf. Do not inventory a tree when one route answers the question.
4. Inspect the smallest source and test slice for current behavior or delivery, and `.venv/lib/`
   when installed dependency behavior matters.
5. For a References task, check any operator-designated local shelf's index for a matching
   snapshot before browsing or guessing.
   Absence is not a blocker; the shelf never becomes project truth.
6. Close remaining uncertainty with targeted `rg` or `rg --files` in the routed area. Widen only
   if that area cannot answer; retain missing or misleading routes as findings. Ask the operator
   only after internal archaeology is exhausted.

Do not guess paths, APIs, delivery, compatibility, or recovery behavior. For a stale routed path,
use the next authority; repair the route only when routing maintenance is in scope.

Do not load `.agents/AGENTS.md`, `~/.agents/AGENTS.md`, or tool-specific local profiles unless the
operator assigns one for the current task.

## Working contract

- **xDDD:** establish the Logos—truth, vocabulary, and boundaries in owning documentation—then
  derive implementation. Myth is constitutional telos, not decorative copy or delivery evidence.
- **Documentation topology:** follow
  [ADR 01 §Documentation Topology](docs/adr/01-doctrine.md#documentation-topology). Root files are
  entry doors, not duplicate manuals.
- **Dynamic sync:** when code changes system truth, update its owner and any route or delivery
  record made stale.
- **Trust verification:** when asked whether something is solid, inspect the critical chain and
  report findings rather than reassurance.
- **Private-material boundary:** operator or company dossiers, client collateral, contracts,
  local transformation workspaces, and their generated artifacts belong outside the checkout.
  Ignoring a path prevents accidental publication; it does not make the checkout an acceptable
  private-material workspace.

For docs changes, verify local links; run the architecture State test when delivery prose moves.
For published routes or navigation, run a clean Zensical build. For source changes, use the focused
and repository gates in CONTRIBUTING and the selected scope.
