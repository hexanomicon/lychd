---
title: Companion
icon: material/cellphone-link
---

# :material-cellphone-link: Companion

Companion is the mobile Familiar Composition. It defines the bounded LychD application contract
for a phone or similarly personal device: local interaction, notifications, connectivity, privacy,
configuration, extensibility, and reconnect behavior belong to this form. The contract does not
claim that a mobile client is already delivered.

[Familiar](../familiar/index.md) supplies the embodiment foundation: the device body, hardware
capabilities, local safety and stop law, and any physical effect boundary. Companion supplies the
configurable mobile client and its device experience. An [Avatar](../avatar/index.md) may project
the Lich through Companion just as it may project through a drone, car, hand, or another Familiar
body; the projection does not become the identity or authority of the target.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `companion.mobile` revision `1` |
| **Patterns** | `companion.admit_device@1` and `companion.open_session@1` |
| **Application begins with** | one Familiar-backed mobile device, enrolled application, current Principal, declared purpose, local capability snapshot, configuration and extension set, capture/playback policy, privacy and retention policy, reconnect policy, and visible stop path |
| **Application can return** | an immutable `CompanionDevice@1`, settled `CompanionSession@1`, committed text, optional synthesized speech, local delivery facts, or explicit partial/non-completion |
| **Application stops before** | owning Persona identity, replacing Familiar hardware authority, ambient capture, mobile administration, approval by voice alone, or direct authority over deferred external effects |

Companion owns the bounded device session, local interaction state, capture and playback controls,
disclosure indicators, configuration, supported extensions, reconnect behavior, and the distinction
between text committed by LychD and speech actually delivered by the device. Familiar retains
hardware admission, capability truth, local safety, physical effect authority, and stop behavior.

## Mobile client

The first client target is native Android under `clients/android/**`, planned as a sleek Kotlin and
Jetpack Compose application. The Android client projects Companion's contract and owns platform
integration and local UI state; it does not acquire Composition records, policy, effect authority,
or finish judgment. [State of Work](../../state-of-the-work.md#composition-portfolio-delivery)
owns the undelivered Portfolio boundary.

Companion is not a thin transport wrapper. Its extensibility and configurability are part of the
Composition boundary: device capabilities, local routes, presentation settings, privacy controls,
and admitted extensions are explicit inputs to a bounded session. The client may change without
changing the Companion domain contract.

## Communion route

**Communion** remains the name of one bounded mobile interaction route inside Companion. It carries
one deliberate utterance from an enrolled client and returns a committed result, optionally spoken
aloud. Communion is therefore a route/profile, not a separate Composition.

| Layer | Owner |
| --- | --- |
| Mobile device implementation, local session, configuration, extensions, capture/playback, reconnect, and disclosure | Companion |
| Device body, hardware capabilities, physical safety, local stop, and physical effect receipts | Familiar |
| Foreground utterance route | Communion inside Companion |
| Speech capture, transcription, synthesis, custody, and revocation | Echo |
| Lich presentation profile and projection membership | Avatar |
| Android UI and platform integration | `clients/android/**` |

## Boundaries

Companion uses foreground, visible, revocable interaction. Push-to-talk is the initial activation
contract. A local microphone indicator proves neither permanent recording permission nor authority
to invoke an application effect. A spoken “yes” is never sufficient authority for a consequential
effect.

The device keeps text visible before or beside audio, distinguishes **stop speaking** from **cancel
the session**, and fails closed on malformed, stale, replayed, out-of-order, or oversized frames.
Raw voice remains `restricted`; transcripts and replies are at least `private`; captured audio is
ephemeral by default and is never training material merely because it was recorded.

Companion may carry an Avatar projection and may hand a typed request to another Composition, but it
does not merge that Composition's records or effects into the mobile session. A Familiar body, VR
Habitat, social turn, or external effect retains its own admission, consent, observation, and
settlement.

- [Utterance](utterance.md) follows one bounded Communion route from capture to committed result.
- [Return](return.md) fixes mobile custody, reconnect, revocation, and proof.

Related: [Avatar](../avatar/index.md) · [Familiar](../familiar/index.md) ·
[Echo](../../sepulcher/extensions/echo.md) · [Tether](../../sepulcher/extensions/tether.md) ·
[Ward](../../sepulcher/extensions/ward.md) · [Composition Portfolio](../index.md)
