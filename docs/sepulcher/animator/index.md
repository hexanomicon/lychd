---
title: Animator
icon: fontawesome/solid/heart-pulse
---

# :fontawesome-solid-heart-pulse: Animator

> _“Cold iron offers no capability. An Animator is the address at which power answers.”_

An **Animator** is a live service that LychD can discover, probe, bind through a typed adapter, and
route by declared capability. Model inference is one family of service, not the definition of this
office.

## The Holy Contract

Three kinds of truth meet at the binding:

1. **Declaration names** the Animator, its capabilities, lifecycle intent, and provenance.
2. **Observation establishes** whether each declared capability is reachable and ready now.
3. **Proof exercises** the bound runtime surface under the caller's typed contract.

A probe may make a declaration unavailable; it may not invent a capability absent from the Rune.
Native protocols remain behind adapters. Callers receive the stable surface their Graph or
extension requested.

## Two Sources of Power

### :material-hexagon-slice-6: [Soulstones](./soulstone/index.md)

#### "The Trapped Spirit."

A **Soulstone** is local, containerized, and stateful. Its Rune becomes rootless
Podman/Quadlet/systemd embodiment on the Magus's iron. It declares every device, mount, secret,
model, and lifecycle boundary it needs.

### :material-weather-hurricane: [Portals](./portal.md)

#### "The Rift to the Remote Sky."

A **Portal** binds a remote API. It generates no local service unit, consumes no local VRAM, and
leaves the provider's lifecycle outside LychD.

## Capability and Readiness

[Capabilities](./capabilities.md) owns families, modalities, capability identity, the
`is_dynamic` trait, and the six readiness phases. The
[Dispatcher](../../adr/22-dispatcher.md) selects and leases a warm capability. The
[Orchestrator](../../adr/23-orchestrator.md) alone drives an admissible physical or runtime-native
transition.

## The Galvanic Arc

Demand names a family and requirements. Dispatch resolves one declared candidate against current
state. A cold managed service enters bounded orchestration without carrying a connector or lease
across the pause. Once observation reaches honest `WARM`, dispatch retries, issues the grant, and
records its lease. Use returns through the caller's own evidence path.

Choose [Soulstone](./soulstone/index.md) for local iron, [Portal](./portal.md) for a remote
boundary, and [Coven](./coven.md) for compatible local aggregation. [State of
Work](../../state-of-the-work.md#animation-and-orchestration) owns what each path currently proves.
