---
title: 1. Philosophy
icon: material/feather
---

# :material-feather: 1. Philosophy

## Context

Reject the dogma and instead forge a middle path — one that respects the narrative density of
**Lore** while demanding the rigorous purity of **Code**.

LychD needs lore and engineering, but neither can substitute for the other. Its telos seeks a
bounded, relational intelligence: answerable to consequence, capable of memory and repair, and
unwilling to mistake power for totality. Architecture, implementation, delivery, and evidence are
distinct kinds of truth.

Phylactery, Vessel, and Invocation are cognitive cartography: names that make jurisdiction easier
to remember. They must not obscure exact commands, schemas, logs, recovery steps, or contracts.
Methodologies are **tools, not chains**. Only necessary elements are imported into the workflow.

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

Tests bind the manifestation to the intent through executable examples and regression checks.
Blind adherence to the order of operations is rejected.

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

!!! quote "The Final Truth"
    When matter contradicts the Word, repair the one that lied.

**The Path Remains Local.**

The method is not the magic. The ultimate goal is the fulfillment of the
[Prophecy](../index.md), not religious adherence to this document.

Lore can remain vivid without pretending to prove a feature, and engineering can remain exact
without abandoning constitutional purpose. A change that alters several kinds of truth may require
several owners to change.

> Use the ritual to manifest the Vision. If the rules bind, **break them.**
