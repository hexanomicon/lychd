---
title: Spellweaver
icon: material/state-machine
---

# :material-state-machine: The Spellweaver

> _A Spell gives one station its action. The Spellweaver keeps the Scroll through motion, pause,
> and return._

An Agent call, Gate, tool, effect, wait, or delegation may warrant an independently named semantic
action: a **Spell**. One Scroll-local station places that Spell's exact contract. The whole
immutable Pattern revision is its **Scroll**. **Spellweaver** is LychD's singular logical workflow
jurisdiction: it validates Scrolls and admits their casting through execution, pause, return, and
ending. `Weaver` remains the short name used by code and existing paths.

Future packages may contribute Spell contracts and Scroll declarations through separate
Spellweaver-shaped stores. Executable implementations and adapters remain separate Extension or
effect-owner registrations; publication and activation are not implied by contribution. The Core
office retains workflow authority. Spellweaver never inherits the policy or physical control of
the offices it sequences. [ADR 28](../../../adr/28-workflow.md) owns the complete contract.

## From Product to performance

These identities keep packaging, domain truth, score, performance, and ledger distinct:

- **[Product](../../../compositions/index.md#products-package-compositions)** names the professional
  or market package and its supported use cases; it grants no member authority.
- **[Composition](../../../compositions/index.md)** owns reusable application records, judgment,
  policy, effects, and outcomes.
- **Pattern** is one named executable-score lineage owned by that Composition; one immutable
  revision is a **Scroll**.
- **Spell** is one independently named semantic action contract; a station places it in that
  Scroll.
- **Invocation** opens one bounded [Circle](../../../divination/altar/circle.md).
- **Casting** performs the exact Scroll inside that Invocation.
- **Run** is the durable execution and ledger identity of that Invocation.

Graph is the typed topology that advances Scroll state among Spell placements. The
[Loom](../../../divination/altar/loom.md) is a read-only projection of its declared truth. The
current fixed registry has no independent Spell catalogue or teaching surface.

The current registry is fixed and source-defined:

```text
bridge_chat@1
WeaveContext → Converse → AwaitConsent? → ProjectReply → End

delegated_rite@1
DispatchDelegate ⇢ ProjectDelegatedReply → End
```

Admission chooses once. The registered workflow name and exact manifest snapshot are committed
with the Run; resume looks up that stored choice and never routes the Intent again.

The registry is executable substrate, not a general workflow platform. `delegated_rite@1`
exercises only the deterministic reference adapter; it delivers no foreign runtime or execution
plane.

## The present score

[Topology-A local runs](../../../state-of-the-work.md#topology-a-local-runs) and the [Pydantic AI
1.25.1 adapter](../../../state-of-the-work.md#pydantic-ai-v1-adapter) are **Available**. [Graph
Stasis](../../../state-of-the-work.md#graph-stasis-consent), [delegated
execution](../../../state-of-the-work.md#delegated-agent-execution), [extension
activation](../../../state-of-the-work.md#extension-activation-contributions), and
[Loom](../../../state-of-the-work.md#loom-workflow-views) remain **Partial**.

Pattern contribution and durable publication, scheduling, durable parallelism, compatibility and
migration, editing, authorship attestation, and protected-region admission remain undelivered.
Architectural treatment is not operational evidence.

## Follow the Scroll

Choose the route that matches the question:

- **[Pattern lifecycle](./pattern-lifecycle.md)** covers identity, manifests, admission,
  contribution, authorship protection, and revision continuity.
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

Repository coding-agent choreography is separate: the
[tracked workflow playbooks](https://github.com/hexanomicon/lychd/tree/main/.agents/workflows) own
contributor procedure only, never Spellweaver or Pattern law.
