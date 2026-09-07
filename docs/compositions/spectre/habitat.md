---
title: Admitting a VR Habitat
icon: material/virtual-reality
---

# Admitting a VR Habitat

A participant may need a seated experience with captions; another may require a bounded room-scale space. Habitat admission establishes which exact virtual place can support the requested experience and how it must make exit available.

## Bind the place and its capabilities

`spectre.admit_habitat@1` begins with exact world/scene reference, engine/runtime capability snapshot, reference-space policy, comfort, accessibility, retention, and exit policy. It returns immutable `VRHabitat@1` or refusal.

The record binds a world/build and capability epoch: adapter/runtime revision; requested, required, granted, missing, and revoked features; admitted spatial context/reference-space policy; comfort/accessibility; retention; disclosure; and exit. It does not own source project, engine build, headset, reference-space handle, multiplayer service, or persistent world.

Required capabilities refuse admission when missing; optional ones become explicit downgrades. Hands, haptics, room bounds, eye/face tracking, passthrough, anchors, and body tracking cannot be inferred from “VR.” Changed world/build digest, required features, reference-space, comfort/accessibility, retention, or exit contract requires a new Habitat revision or epoch. Runtime restart alone does not rewrite it.

## Admit the space the participant will use

[OpenXR reference spaces](https://registry.khronos.org/OpenXR/specs/1.1/man/html/XrReferenceSpaceType.html) distinguish view-relative, seated/local, floor-relative, and room-scale arrangements. Pin required floor/stage bounds, recenter and reference-space-change policy, permitted locomotion, and downgrade/refusal when the runtime cannot supply them. Runtime handles and observed bounds remain volatile provider facts.

Seated, standing, captioned, controller-free, companion-screen, and audio-led routes enter only when explicitly supported. An Encounter records each person's actual modality. A flat/audio companion route can support access without claiming equivalent spatial tracking, reference space, haptics, privacy, or embodiment. Every admitted modality must preserve visible exit and its declared recovery path.

[Foundry](../foundry/index.md) may supply an exact world/build/profile and playtest evidence; it retains project, controllers, derivatives, build judgment, and playability. Blockworld keeps persistent-world effects, and [Reach](../reach/index.md) keeps external social events, audience, platform delivery, and replies. Avatar may independently bind a Lich presentation to the Habitat, without owning runtime, locomotion, tracking, or entry.

Prism and [Kinesis](../../sepulcher/extensions/prism/kinesis.md) retain spatial and motion sources. The [media ownership comparison](../choosing-a-home.md#media-owners-do-not-follow-file-extensions) follows separately admitted speech, music, dialogue, and sound handoffs; a shared VR runtime does not merge their judgments.

## First integration hypothesis

The design uses [OpenXR 1.1](https://registry.khronos.org/OpenXR/) as protocol baseline; an adapter still enumerates the actual runtime and extensions. Its first engine candidate is [Godot](https://docs.godotengine.org/en/4.7/tutorials/xr/setting_up_xr.html), with a standalone Quest 3 application as the smallest hardware hypothesis. [WiVRn](https://github.com/WiVRn/WiVRn) and [Monado](https://monado.freedesktop.org/) remain later Linux/FOSS-first candidates; SteamVR/vendor runtimes are optional compatibility profiles. These are hypotheses, not newly proved hardware compatibility.

The minimum profile requires stereo view, head pose, a tested action/input profile, explicit reference space, visible exit, and runtime-loss handling. Additional tracking, passthrough, anchors, haptics, and room bounds remain optional and honestly absent when unavailable. Revision one's scope did not promise multiplayer, persistent social worlds, full-body embodiment, eye/face tracking, mixed-reality mapping, or a production hardware profile.

Continue with [Encounter](encounter.md) for participants, chronology, interruption, and exit, or return to [Spectre](index.md).
