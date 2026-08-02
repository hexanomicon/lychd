---
title: Weaver
icon: material/state-machine
---

# :material-state-machine: The Weaver

> _An Agent is a single note. The Weaver keeps the score through motion, pause, and return._

An Agent performs one typed cognitive step. **Weaver** is LychD's singular logical workflow
jurisdiction. It validates and admits immutable, versioned **Patterns** that order those steps
through execution, pause, return, and ending.

Future packages may contribute Pattern declarations through a Weaver-shaped store, but the Core
office retains workflow authority. Weaver never inherits the policy or physical control of the
offices it sequences. [ADR 28](../../../adr/28-workflow.md) owns the complete contract.

## From purpose to performance

Four identities keep purpose, score, performance, and ledger distinct:

- **[Composition](../../../compositions/index.md)** records the operator-visible application and
  human purpose.
- **Pattern** is one versioned executable score owned by that Composition.
- **Invocation** is one admitted performance pinned to an exact Pattern revision.
- **Run** is the durable execution and ledger identity of that Invocation.

Graph is the typed topology that advances Pattern state. The
[Loom](../../../divination/altar/loom.md) is a read-only projection of its declared truth.

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
migration, and editing remain undelivered. Architectural treatment is not operational evidence.

## Follow the score

Choose the route that matches the question:

- **[Pattern lifecycle](./pattern-lifecycle.md)** covers identity, manifests, admission,
  contribution, and revision continuity.
- **[Stasis and return](stasis-and-return.md)** covers Live and Durable Stasis, checkpoints,
  re-admission, terminal cleanup, and recovery limits.
- **[Anonymization, taint, and egress](anonymization.md)** covers the local Privacy Cut,
  information-flow labels, Portal admission, quarantined return, and the boundary that makes
  subsidized remote reasoning usable.
- **[Delegated agents](delegated-agents.md)** covers the typed delegated station, `AgentJob`
  boundary, containment, and the present deterministic, no-network, effect-free reference
  adapter.

Repository coding-agent choreography is separate: the
[tracked workflow playbooks](https://github.com/hexanomicon/lychd/tree/main/.agents/workflows) own
contributor procedure only, never Weaver or Pattern law.
