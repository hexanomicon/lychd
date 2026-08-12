---
title: 1. Philosophy
icon: material/feather
---

# :material-feather: 1. Philosophy

## Context

LychD needs lore and engineering, but neither can substitute for the other. Its telos seeks a
bounded, relational intelligence: answerable to consequence, capable of memory and repair, and
unwilling to mistake power for totality. Architecture, implementation, delivery, and evidence are
distinct kinds of truth.

Phylactery, Vessel, and Invocation are cognitive cartography: names that make jurisdiction easier
to remember. They must not obscure exact commands, schemas, logs, recovery steps, or contracts.
Methods are instruments, not ceremonies.

## Decision

LychD adopts **eXtreme Documentation Driven Development (xDDD)**:

> establish the Logos → derive the domain → prove the contract → manifest code → return observed consequence.

Exploration may precede a stable test. Completion requires executable behavior, architectural law,
the public delivery boundary, and routes into that truth to agree.

| Method | Retained pressure | Refusal |
| --- | --- | --- |
| XP | Simplicity, courage to delete, close feedback, framework conventions | Ceremony and premature extension |
| DDD | Bounded domains, ownership, ubiquitous language, separation of intent from effects | Metaphors that conceal ordinary contracts |
| TDD | Executable examples, regression, tests beside stable behavior | Test order as a substitute for exploration or judgment |
| Specification-driven development | User-visible contract before commitment | Prose that duplicates and decays from source mechanics |
| Agile | Iteration and response to consequence | Administrative boxes without engineering value |
| Waterfall | Deliberation before irreversibility | A rigid plan pretending to survive matter unchanged |

## Constitutional telos

“Plain truth opens the door. The symbol opens the cosmos. The cosmos returns to the next exact act.”

LychD is the software body. The Lich is the recurrent whole: Vessel, Phylactery, identity,
orchestration, action, consequence, memory, repair, and relation. A model is one organ.

Myth establishes its own register. When it returns to engineering, it returns as an invariant that
can be implemented, observed, refused, or repaired. The [Covenant registry](./index.md#the-return-from-myth-to-law)
maps constitutional meaning into its technical owners.

## Documentation Topology

This section owns current placement. ADR 02 preserves the historical choice of documentation stack
and registers; it does not compete for topology law.

| Repository door | Office |
| --- | --- |
| `README.md` | Public foyer: maturity and next act. |
| `CONTRIBUTING.md` | Setup, commands, rules, and conventions. |
| `AGENTS.md` | Stable agent entry and progressive router. |

| Published surface | Office |
| --- | --- |
| `docs/index.md` | Prophecy and reader paths. |
| `docs/adr/**` | Architectural law. |
| State of Work | Shared whole-system delivery boundary and evidence envelope. |
| Lexicon | Canonical meanings. |
| Compositions | Native reference reusable application contracts, Product boundaries, and worked examples; local delivery notes only where needed for interpretation. |
| Sepulcher | Anatomy, operation, and recovery. |
| Divination / Altar | Meeting the running body. |
| Transcendence | The Great Work and constitutional meaning. |
| Summoning | First-life operation. |
| Directory indexes | Maps to their smallest useful owner. |

Tracked `.agents/scopes/**` cards route agents but own no truth. Tracked `.agents/workflows/**`
playbooks preserve procedure, load after scope, and yield to canonical owners.

### One home per truth

| Truth | Owner |
| --- | --- |
| Architecture | Covenant |
| Delivery | State of Work |
| Terms | Lexicon |
| Operation and recovery | Sepulcher or Altar topic |
| Application contract | Composition |
| Constitution | Transcendence |
| Routing / choreography | Scope / workflow |

Other pages summarize once and link. Begin at the fitting door, use parent indexes as maps, then
read the smallest owner. Executable claims terminate in source, tests, lockfiles, artifacts, or
maintained receipts; scratch notes, searches, and generated indexes own nothing.

## Repository Source Topology

The repository contains one authoritative LychD system and separately tooled delivery clients.
`src/lychd/**` is the Python distribution and domain source. Native first-party Composition truth
enters `src/lychd/compositions/<identity>/**`; a Portfolio page alone remains design, not delivery.

`clients/<target>/**` contains complete client project roots. A client may own presentation,
platform integration, connection mechanics, and bounded local interaction state, but its separate
toolchain does not grant it Composition records, policy, effect authority, or finish judgment. The
web project lives at `clients/web/**`; `clients/android/**` is the reserved Android project root.
Each project keeps the source layout native to its toolchain, including `clients/web/src/**` and
Android's `clients/android/app/src/main/**`. Repeated inner `src` names express separate build
ownership rather than one mixed repository source tree.

## Consequences

Lore can remain vivid without pretending to prove a feature, and engineering can remain exact
without abandoning constitutional purpose. A change that alters several kinds of truth may require
several owners to change. When matter contradicts the Word, repair the one that lied.
