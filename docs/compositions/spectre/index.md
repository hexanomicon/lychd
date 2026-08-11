---
title: Spectre
icon: material/ghost-outline
---

# :material-ghost-outline: Spectre

Spectre is the Virtual Reality (VR) Composition. **VR is its Habitat:** one admitted virtual place
binding an exact world or scene to a runtime capability snapshot, reference space, comfort and
accessibility policy, and visible exit. Spectre opens one bounded **Encounter** inside that Habitat
and brings its participants back with an honest account of what happened.

An Avatar may be projected into the VR Habitat. When a participant meets the Lich through that
Avatar, the bounded meeting is a Spectre Encounter; Avatar remains the separate Composition that
owns presentation and projection membership. The name follows _spectre_ as an appearance or
apparition: what is seen may be compelling without becoming identity, physical truth, or
authority.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `spectre.virtual_reality` revision `1` |
| **Patterns** | `spectre.admit_habitat@1` and `spectre.enter_encounter@1` |
| **Application begins with** | for Habitat admission, an exact world or scene reference, engine/runtime capability snapshot, reference-space, comfort, accessibility, retention, and exit policy; for an Encounter, one admitted `VRHabitat@1`, participants, purpose, consent, and an optional exact Avatar-owned `ProjectionBinding@1` reference |
| **Application can return** | an immutable `VRHabitat@1` or settled `SpectreEncounter@1`: completed, safely exited, interrupted, refused, or unresolved, with provider facts and external world or effect receipt references |
| **Application stops before** | content or world authorship, persistent-world authority, headset/runtime ownership, raw tracking archives, Persona or Avatar ownership, generic multiplayer, public release, or a claim that presence was physical |

Spectre owns the durable VR Habitat binding and epoch: exact world or scene references; requested,
required, negotiated, missing, and revoked VR capabilities; admitted spatial context; reference
space; and comfort, accessibility, retention, and exit policy. The source world, engine project,
runtime, and device remain outside that record.

Each Encounter owns its participants, purpose, consent changes, focus, pause, recenter,
interruption, exit, recovery chronology, significant semantic interactions, and terminal
judgment. An OpenXR `XrSession`, game process, socket, device handle, or pose stream is volatile
provider state, never the durable Habitat or Encounter.

## VR Habitat and Encounter

Spectre is not a generic home for every spatial, rendered, or game experience. A Habitat says
where a VR meeting can occur and which local capabilities and safety policies govern it; an
Encounter says who met there, for what bounded purpose, what semantically happened, and how they
left. One Habitat may admit many separately identified Encounters without turning into one endless
session.

This reusable application truth remains stable even while the first packaged use, hardware
profile, and richer Patterns are still being discovered. Revision one deliberately promises no
multiplayer, persistent social world, full-body embodiment, eye or face tracking, mixed-reality
mapping, or production hardware profile.

| Neighbour | Retained authority |
| --- | --- |
| [Foundry](../foundry/index.md) | project, engine-native world, controllers, build candidate, and playtest evidence |
| [Blockworld](../blockworld/index.md) | persistent authoritative world, mission, inventory, lease, and verified world effects |
| [Avatar](../avatar/index.md) | Lich presentation profile, Morphe selection, projection membership into this VR Habitat, and aggregate projection settlement; the Encounter only references the exact binding |
| [Reach](../reach/index.md) | external social event, Habitat audience, delivery, and bounded social turn |
| Prism Form and Kinesis | spatial assets, rigs, morph targets, technical motion, retargeting, and provenance |
| Echo and Riffmaw | capture, speech timeline, cloning/synthesis, playback, and produced sonic assets |
| VR engine and OpenXR runtime | scene graph, rendering, physics, per-frame tracking, input, haptics, compositing, and device lifecycle |

Typed participant, Avatar, world, artifact, interaction, and receipt references may cross these
seams. Spectre receives no ambient engine console, filesystem, raw tracking database, microphone,
world mutation, or body authority.

## Representative journey: meet the Lich in VR

1. The Magus admits one `VRHabitat@1` from an exact VR world or scene, OpenXR runtime capability
   snapshot, reference space, retention rule, comfort policy, and visible exit. Missing optional
   hand, haptic, or room-scale support becomes an explicit downgrade; a missing required
   capability refuses the Habitat.
2. Avatar independently admits one `ProjectionBinding@1` targeted at the Habitat. Spectre cannot
   create or revise the Avatar profile, Morphe, Persona, binding, or other simultaneous
   projections.
3. A participant enters that Habitat for one declared purpose and meets the Lich through that
   projection. Spectre opens a new `SpectreEncounter@1` referencing the exact binding rather than
   resuming an ambient endless session.
4. Spectre records semantic VR events, focus loss, pause, recenter, interruption, and exit while
   high-rate pose and device state remain volatile inside the engine/runtime path.
5. On visible exit or runtime loss, Spectre settles the Encounter. Avatar separately settles that
   projection binding from Spectre's attributed result; neither Composition claims the
   other's records or authority.

## First integration hypothesis

[OpenXR 1.1](https://registry.khronos.org/OpenXR/) is the protocol baseline: a future adapter must
enumerate the selected runtime and extensions rather than infer support from the standard.
[Godot](https://docs.godotengine.org/en/4.7/tutorials/xr/setting_up_xr.html) is the first engine
candidate. A standalone Quest 3 OpenXR application is the smallest first hardware hypothesis;
[WiVRn](https://github.com/WiVRn/WiVRn) or
[Monado](https://monado.freedesktop.org/) provide later Linux/FOSS-first routes, while SteamVR or a
vendor runtime remains an optional compatibility profile rather than architecture law.

The minimum proving profile needs a stereoscopic view, head pose, one tested action/input profile,
one explicit reference-space policy, visible exit, and runtime-loss handling. Hand, eye, body,
face, passthrough, spatial anchors, haptics, and room bounds are optional capabilities and remain
honestly absent when the selected runtime cannot supply them. High-rate head, hand, gaze, and
device state stays inside the engine/runtime path; only admitted artifacts and semantic encounter
events cross into durable LychD records.

The first fixture is synthetic and network-disabled: one Habitat admitting a seated Encounter and
a separate bounded room-scale Encounter, a static or head-and-hands Avatar, capability downgrade,
focus loss, recenter, exit request, abrupt runtime loss, restart, consent revocation, and complete
export/deletion. It proves the Habitat and Encounter contracts, not headset compatibility, comfort
for every participant, content quality, multiplayer, or delivery.

Related: [Foundry World](../foundry/world.md) · [Blockworld](../blockworld/index.md) ·
[Avatar](../avatar/index.md) · [Vision](../../adr/36-vision.md) ·
[Audio](../../adr/37-audio.md) · [Composition Portfolio](../index.md)
