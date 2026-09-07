---
title: Coven
icon: material/swap-horizontal-bold
---

# :material-swap-horizontal-bold: Coven: Named Runtime Grouping

> _“A Coven names what may rise together; it never decides what must sleep.”_

A **Coven** is a named systemd target emitted when two or more compatible
[Soulstones](./soulstone/index.md) share a group. Soulstone `groups` request membership;
`[concurrency].conflict_domains` separately declares finite-resource incompatibility. A Coven is
neither conflict nor eviction policy.

One member emits no target. Different groups create no coexistence promise. Members' effective
conflict sets must not overlap; an internally conflicting Coven fails closed. The current Rune
schema has no `alliances` setting and rejects that field.

One Rune may participate in more than one formation:

```toml
name = "echo"
groups = ["conversation", "studio"]
```

That still names one service instance. Starting `conversation.target` and `studio.target` does not
create two copies, and common membership does not prove the complete union fits. The compiled
conflict graph remains the executable coexistence law.

For later multi-capability placement, follow the [capability and resource
design](capabilities.md#runes-runes-in-groups-and-placement). A `CapabilitySetRequest@1` may use a
Coven as an operator convenience only after Orchestrator expands and validates every member
against measured envelopes and placement profiles. Membership grants no resources, routing, lease,
or egress authority. Convergence is serialized, while physical effects remain non-atomic and use
compensation, restoration, and containment after partial change.

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
