---
title: Spellweaver
icon: material/state-machine
---

# :material-state-machine: The Spellweaver

> _A Spell gives one station its action. The Spellweaver keeps the Scroll through motion, pause,
> and return._

**Spellweaver** keeps one chosen score through execution, pause, return, and ending. It is LychD's
singular logical workflow jurisdiction: it validates immutable **Scrolls** and admits their casting.
`Weaver` remains the short name used by code and existing paths.

A Scroll is one immutable revision of a **Pattern**. An Agent call, Gate, tool, effect, wait, or
delegation may warrant an independently named **Spell**; a Scroll-local station places that
Spell's exact contract. The score fixes their relationship before work begins.

Future packages may contribute Spell contracts and Scroll declarations through separate
Spellweaver-shaped stores. Executable implementations and adapters remain separate Extension or
effect-owner registrations; publication and activation are not implied by contribution. The Core
office retains workflow authority. Spellweaver never inherits the policy or physical control of
the offices it sequences. [ADR 28](../../../adr/28-workflow.md) owns the complete contract.

## From Product to performance

A [Composition or Suite](../../../compositions/products-and-suites.md) publishes the score for its
work. A Product packages that choice; application records, judgment, and effects remain with their
owners.

- **Pattern** is one named executable-score lineage published by its application owner: normally a
  Composition, or a Suite for coordination only; one immutable revision is a **Scroll**. The two
  delivered Core Patterns are an explicit retained pre-Portfolio exception.
- **Spell** is one independently named semantic action contract; a station places it in that
  Scroll.
- **Invocation** opens one bounded [Circle](../../../divination/altar/circle.md).
- **Casting** performs the exact Scroll inside that Invocation.
- **Run** is the durable execution and ledger identity of that Invocation.

A Suite Casting opens one parent coordination Invocation/Run from its Suite-owned Scroll and
separate child Composition Invocations/Runs. The parent owns correlation and aggregate settlement,
never a member's records, judgment, consent, credentials, or effects.

Graph is the typed topology that advances Scroll state among Spell placements. The
[Loom](../../../divination/altar/loom.md) is a read-only projection of its declared truth. The
current fixed registry has no independent Spell catalogue or teaching surface.

The current registry is fixed and source-defined:

```text
bridge_chat@1 (default) / bridge_chat@2 (configured exact capability)
WeaveContext → Converse → AwaitConsent? → ProjectReply → End

delegated_rite@1
DispatchDelegate ⇢ ProjectDelegatedReply → End
```

Admission chooses once. The registered workflow name and exact manifest snapshot are committed
with the Run; resume looks up that stored choice and never routes the Intent again.

The registry is executable substrate, not a general workflow platform. `delegated_rite@1`
exercises only the deterministic reference adapter; it delivers no foreign runtime or execution
plane.

## Choose a Bridge capability

In the Codex's `lychd.toml`, select the registered Bridge revision and the exact capability key
from your declared runtime inventory:

```toml
[weaver.bridge]
revision = "2"
capability_key = "my-runtime:chat:my-model"
```

Replace the example key with your runtime's key. It identifies the Animator, capability family,
and model together; a shared model name alone cannot pin a runtime. The selected capability must
support chat and tools. Loading Settings validates the selector's shape without contacting an
engine; Dispatcher checks the actual declaration, readiness, and policy at execution. An unknown,
incompatible, or unavailable target refuses the turn rather than choosing another runtime.

Restarting with this configuration selects revision 2 for new Bridge admissions. The Run stores
its choice before queue publication and retains it through hardware retries and consent pauses.
Changing or removing the setting does not redirect an existing Run or an idempotent retry. Omitting
the section keeps revision 1's eligible-pool selection for new turns. Both revisions stay registered
for retained work. This key pins capability identity, not a model artifact or runtime configuration
fingerprint; the general Resolution Lock remains a separate contract.

## Follow the Scroll

Choose the route that matches the question:

- **[Discovery and router delegation](discovery.md)** follows scope branches, makes nested routes
  and workflows discoverable, and carries the selected routes into a bounded task handoff.
- **[Pattern lifecycle](./pattern-lifecycle.md)** covers identity, manifests, admission,
  contribution, authorship protection, and revision continuity.
- **[Crucible](./crucible.md)** covers two-round adversarial formation: declared biased Postures,
  independent first claims, attributed rebuttal, dissent-preserving synthesis, and the Magus Gate.
- **[Agentic software development](sdlc.md)** applies bounded Inquiry at direction and construction
  scales, then follows task handoffs, tests, review, documentation and authorized VCS effects.
- **[:material-autorenew: Ouroboros](ouroboros.md)** connects work, evaluation and training through
  correction, memory, Assimilation, Packaging and Evolution.
- **[Scheduling and service classes](./scheduling-and-service-classes.md)** covers foreground,
  deadline-windowed, and spare-capacity admission, schedule time law, overlap, and explicit misses.
- **[Stasis and return](stasis-and-return.md)** covers Live and Durable Stasis, checkpoints,
  re-admission, terminal cleanup, and recovery limits.
- **[Execution roads](execution-roads.md)** covers the layered choice among native/local work,
  Portal-backed cognition, sovereign A2A tasks, delegated coding runtimes, and operator seats.
- **[Anonymization, taint, and egress](anonymization.md)** covers the local Privacy Cut,
  information-flow labels, Portal admission, quarantined return, and the boundary that makes
  subsidized remote reasoning usable.
- **[Delegated agents](delegated-agents.md)** covers the typed delegated station, `AgentJob`
  boundary, containment, and the present deterministic, no-network, effect-free reference
  adapter.

## Progressive craft without a mutable score

A Scroll may admit several explicit finish boundaries. A completed intermediate artifact can
begin a new forward Invocation; a terminal Run is never reopened to continue it.
[Pattern lifecycle](pattern-lifecycle.md#a-new-score-is-a-new-revision) distinguishes new input
from a changed score.

Model and engine choice stays in the receiver-owned Resolution Lock. A Comfy graph is an
implementation preset, and a portable A2A Scroll remains inert until admitted. Follow
[Composition Suites](../../../compositions/products-and-suites.md#compositions-relate-without-nesting) when the
work needs live coordination across application owners.

## Hand off a bounded task

In the designed [scoped context handoff](../../../adr/28-workflow.md#scoped-context-handoff-designed),
the coordinating Agent keeps the wider purpose while another Agent receives a fresh Context for
one task. For a repository change, that packet gives the requested result, relevant operator
decisions, acceptance checks, allowed paths, source revision, dependencies, and a scope routing to
the owning documents and code. The recipient reads those owners without inheriting the whole
conversation that led to the task.

If a needed decision is missing, the recipient requests that bounded input. It returns a candidate
patch or findings with verification evidence and unresolved questions for the coordinator to
assess. Merely loading another scope in the same conversation does not perform this handoff.

## The present score

[State of Work](../../../state-of-the-work.md) records local execution and the separate Stasis,
delegation, extension, and Loom delivery boundaries. Pattern
contribution and durable publication, scheduling, durable parallelism, compatibility and migration,
editing, authorship attestation, and protected-region admission remain undelivered.

Repository coding-agent choreography is separate: the
[tracked workflow playbooks](https://github.com/hexanomicon/lychd/tree/main/.agents/workflows) own
contributor procedure only, never Spellweaver or Pattern law.
