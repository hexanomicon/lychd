---
title: Coven
icon: material/swap-horizontal-bold
---

# :material-swap-horizontal-bold: Coven: Named Runtime Grouping

> _Under one name, the Coven gathers its fires._

Use a **Coven** to give compatible local services one operator name. When two or more
[Soulstones](./soulstone/index.md) share a group, binding emits a named systemd target for them.
A Soulstone requests membership through `groups`. It declares hardware incompatibility separately
through `[concurrency].conflict_domains`; grouping services cannot decide which ones may coexist
or be evicted.

One member emits no target. Different groups create no coexistence promise. Members' effective
conflict sets must not overlap; an internally conflicting Coven fails closed. The current Rune
schema has no `alliances` setting and rejects that field.

One Rune may participate in more than one formation:

```toml
name = "echo"
groups = ["conversation", "studio"]
```

That still names one service instance. Starting `lychd-coven-conversation.target` and
`lychd-coven-studio.target` does not
create two copies, and common membership does not prove the complete union fits. The compiled
conflict graph remains the executable coexistence law.

The later [capability and resource design](capabilities.md#runes-runes-in-groups-and-placement)
would let a `CapabilitySetRequest@1` use that name as an operator convenience. Orchestrator would
first expand it and validate every member against measured envelopes and placement profiles.
Membership itself supplies no resources, routing, lease, or egress authority. Even a serialized
convergence has non-atomic physical effects: partial change still needs compensation, restoration,
and containment.

!!! warning "Operator break-glass surface"
    Starting or stopping a generated Coven target directly propagates through its compatible
    Animator targets. This bypasses Orchestrator admission, lease drain, stale-world validation,
    readiness, and compensation. Reserve it for host administration or recovery.


<span id="what-the-nexus-shows"></span>
<span id="the-transition-contract"></span>
<span id="inspect-and-request"></span>
<span id="queue-and-routing-context"></span>
<span id="switching-settings"></span>
<span id="tune-with-intent"></span>

For inspection, activation requests, priority, switching settings, and Reactor outcome recovery,
continue to [Runtime transitions](runtime-transitions.md). The old operation fragments remain here
so existing links still find that passage.
