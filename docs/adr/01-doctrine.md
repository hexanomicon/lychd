---
title: 1. Philosophy
icon: material/feather
---

# :material-feather: 1. Philosophy

## Context

Reject the dogma and instead forge a middle path — one that respects the narrative density of
**Lore** while demanding the rigorous purity of **Code**.

LychD gives lore and engineering distinct work. Lore carries the telos of a bounded, relational
intelligence: answerable to consequence, capable of memory and repair, and unwilling to mistake
power for totality. Engineering must make that purpose exact enough to build and judge.
Architecture, implementation, delivery, and evidence therefore remain distinct kinds of truth;
neither lore nor engineering can stand in for the other.

Names such as Phylactery, Vessel, and Invocation offer cognitive cartography: they help a reader
remember jurisdiction. Their usefulness ends where they obscure a command, schema, log, recovery
step, or contract. The same test applies to method. Methodologies are **tools, not chains**;
the workflow imports only what it needs.

## Decision

LychD adopts **eXtreme Documentation Driven Development (xDDD)**:

> establish the Logos → derive the domain → prove the contract → manifest code → return observed consequence.

Exploration may precede a stable test. Completion requires executable behavior, architectural law,
the public delivery boundary, and routes into that truth to agree.

xDDD distills these practices, utilizing AI to dial the knobs to **11**.

### 1. eXtreme Programming (XP)

!!! success "Simplicity"
    **Simplicity is brilliance — Open for Grandeur, Closed for Stability.** Avoid over-engineering;
    extend where a concrete requirement calls for it.

!!! success "Courage"
    **The `'del'ete` Spell.** Reject the Sunk Cost Fallacy and do not be afraid to change course.

!!! success "Respect"
    **There is one obvious way to do it.** Frameworks are followed, not fought.

The Navigator may be an LLM. Close feedback and engineering judgment still govern the work.

**Abstract Spec is written first.** The vision must be solidified in text to guide the summoning.
**Code is the Documentation** regarding implementation details. Low-level mechanics are not
duplicated in the prose.

> _Travel light, but prepared._

### 2. Domain-Driven Design (DDD)

Software structure reflects the Vision. Lore (Map) and Code (Territory) remain distinct, with
their shared vocabulary kept in the [Lexicon](../lexicon/index.md).

**Domain Isolation:** Separation of concerns is mandatory. The Domain is isolated from the
Infrastructure. Bounded domains keep ownership clear and separate intent from effects.

Lore is welcome in documentation, docstrings, and CLI messages where it helps understanding.
Commands, schemas, operational logs, and low-level contracts must stay exact. A metaphor earns its
place by making the boundary easier to see.

### 3. Test-Driven Development (TDD)

Tests turn intent into executable examples and regression checks, binding the manifestation to
what it was meant to do. Their value lies in that feedback; blind adherence to an order of
operations does not establish correctness.

**Strict Test First** can stifle exploration. Prototyping is encouraged, provided tests are
backfilled before the final commit. Test order cannot substitute for judgment.

### 4. Readme/Specification-Driven Development (RDD/SDD)

Write the user-visible contract before committing to its implementation. This ensures the right
thing is being built before the thing is built right.

Documentation deals in abstract ideas and interfaces, avoiding redundant repetition of code logic.

### 5. Agile Methodology

Rapid iteration and adaptation are prioritized. Change is not feared. TDD loops and prototyping
keep feedback close to the work.

**The Ritual (Scrum/Sprints):** Artificial time-boxes are viewed as fractures in the vision.
**Flow is prioritized over sprinting.**

### 6. Waterfall Model

Adopt Waterfall's demand for foresight. Writing the **Prophecy (Documentation)** before code
exposes architectural mistakes while they are still cheap to change. Deliberate before an
irreversible act, and revise the plan when implementation contradicts it.

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
| `ROADMAP.md` | Short entry to the owning public roadmap. |

| Published surface | Office |
| --- | --- |
| `docs/index.md` | Prophecy and reader paths. |
| `docs/adr/**` | Architectural law. |
| State of Work | Shared whole-system delivery boundary and evidence envelope. |
| `docs/roadmap.md` | Public direction, founding-year story and orienting weekly horizon. |
| Lexicon | Canonical meanings. |
| Compositions | Native reference reusable application contracts, Product boundaries, and worked examples; local delivery notes only where needed for interpretation. |
| Sepulcher | Anatomy, operation, and recovery. |
| Divination / Altar | Meeting the running body. |
| Transcendence | The Great Work and constitutional meaning. |
| Summoning | First-life operation. |
| Directory indexes | Maps to their smallest useful owner. |

Tracked `.agents/scopes/**` cards route agents but own no truth. Tracked `.agents/workflows/**`
playbooks preserve procedure, load after scope, and yield to canonical owners.

### Router delegation

A router helps the reader choose the next useful edge. It gives task triggers and explicit
links, and identifies each destination as a scope branch, canonical owner, or workflow playbook.
That role tells the reader whether to continue discovery, establish truth, or load procedure.
When the destination is another router, it owns the deeper routes; the parent keeps the branch
discoverable without copying its contents.

Follow only the branches required by the task. Cross-domain links make another scope tree
reachable without requiring its wholesale ingestion. Workflows load after the matching scope.
Routing grants no new authority, launches no work, and does not itself assemble a fresh Context.
[Discovery in Spellweaver](../sepulcher/extensions/weaver/discovery.md) shows the passage from
scope discovery to workflow selection and a bounded task handoff.

### One home per truth

| Truth | Owner |
| --- | --- |
| Architecture | Covenant |
| Delivery | State of Work |
| Direction and founding-year story | Roadmap |
| Terms | Lexicon |
| Operation and recovery | Sepulcher or Altar topic |
| Application contract | Composition |
| Constitution | Transcendence |
| Routing / choreography | Scope / workflow |

Begin at the fitting door, follow parent indexes as maps, and read the smallest owner. Other
pages may summarize that owner's truth once and link to it. An executable claim must eventually
reach source, tests, lockfiles, artifacts, or maintained receipts. Scratch notes, searches, and
generated indexes can help discovery, but own no truth.

Architecture and application pages explain a coherent system through its responsibilities,
records, handoffs, decisions, and recovery. State these contracts directly, without maturity
badges or `Designed` suffixes on headings. State of Work gathers the implementation evidence and
missing pieces. A local limitation belongs on the contract page only when it changes an operation
the reader can perform, an exact compatibility boundary, or the reading of a worked example.
Explain that concrete limit and link its evidence instead of repeating a delivery category.

## Repository Source Topology

The repository contains one authoritative LychD system and separately tooled delivery clients.
`src/lychd/**` is the Python distribution and domain source. Native first-party Composition truth
enters `src/lychd/compositions/<identity>/**`; a Portfolio page alone remains design, not delivery.

A delivery client keeps its complete project root under `clients/<target>/**`. It may own presentation,
platform integration, connection mechanics, and bounded local interaction state, but its separate
toolchain does not grant it Composition records, policy, effect authority, or finish judgment. The
web project lives at `clients/web/**`; the Android project lives at `clients/android/**`.
Each project keeps the source layout native to its toolchain. The current web source lives at
`clients/web/src/**`; the Android application module uses
`clients/android/app/src/main/**`. Repeated inner `src` names express separate build ownership
rather than one mixed repository source tree.

## Consequences

!!! quote "The Final Truth"
    When matter contradicts the Word, repair the one that lied.

**The Path Remains Local.**

The method is not the magic. The ultimate goal is the fulfillment of the
[Prophecy](../index.md), not religious adherence to this document.

Lore can remain vivid without pretending to prove a feature, and engineering can remain exact
without abandoning constitutional purpose. A change that alters several kinds of truth may require
several owners to change.

> Use the ritual to manifest the Vision. If the rules bind, **break them.**
