---
title: Companion
icon: material/cellphone-link
---

# :material-cellphone-link: Companion

An admitted phone is a Familiar body. Companion is the mobile-client and device-session
Composition over one exact admitted phone or similarly personal Familiar body: local interaction, notifications,
connectivity, privacy, configuration, extensibility, and reconnect behavior belong to this
application. The contract does not claim that a mobile client is already delivered.

[Familiar](../familiar/index.md) supplies the embodiment foundation: the device body, hardware
capabilities, local safety and stop law, and any physical effect boundary. Companion supplies the
configurable mobile client and its device experience. An [Avatar](../avatar/index.md) may project
the Lich through Companion just as it may project through a drone, car, hand, or another Familiar
body; the projection does not become the identity or authority of the target.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `companion.mobile` revision `2` |
| **Patterns** | `companion.admit_device@2` and `companion.open_session@2` |
| **Application begins with** | one exact `FamiliarBody@2` revision and capability epoch for a mobile device, enrolled application, current Principal, declared purpose, configuration and admitted device-feature profile, capture/playback policy, privacy and retention policy, reconnect policy, and visible stop path |
| **Application can return** | an immutable `CompanionDevice@2`, settled `CompanionSession@2`, committed text, optional synthesized speech, local delivery facts, or explicit partial/non-completion |
| **Application stops before** | owning Persona identity, replacing Familiar hardware authority, ambient capture, mobile administration, approval by voice alone, or direct authority over deferred external effects |

Revision `2` supersedes the Designed-only `companion.mobile` revision `1` and its `@1` contracts.
It makes an exact admitted Familiar body the prerequisite instead of treating Companion as the body
itself. No Portfolio registry or Run used revision `1`, so there is no executable migration;
historical references retain their old meaning.

Companion owns the bounded device session, local interaction state, physical capture and playback
controls, disclosure indicators, configuration, admitted device-feature bindings, reconnect
behavior, and the distinction between text committed by LychD and speech actually delivered by the
device. Familiar retains hardware admission, capability truth, local safety, physical effect
authority, and stop behavior. Echo owns each speech attempt, its media custody and derivation, and
its capture/transcription/synthesis/delivery chronology; a Companion button or indicator does not
duplicate that ledger.

`CompanionDevice@2` pins the exact Familiar body revision and capability epoch. A revoked body,
changed safety or stop contract, or missing required microphone, speaker, display, secure storage,
notification, or connectivity capability invalidates admission for a new session and settles an
affected live session according to its pinned downgrade/stop policy. Companion never guesses that
a replacement handset or changed body is the same admitted device.

## Mobile client

The first client target is native Android under `clients/android/**`, planned as a sleek Kotlin and
Jetpack Compose application. The Android client projects Companion's contract and owns platform
integration and local UI state; it does not acquire Composition records, policy, effect authority,
or finish judgment. [State of Work](../../state-of-the-work.md#composition-portfolio-delivery)
owns the undelivered Portfolio boundary.

Companion is not a thin transport wrapper. Its configurable device experience is part of the
Composition boundary: capability requirements, local routes, presentation settings, privacy
controls, and admitted device-feature bindings are explicit inputs to a bounded session. Concrete
features may arrive through extension packages, but Companion does not own an “extension set” or
turn those packages into application truth. The client implementation may change without changing
the Companion domain contract.

This independent `CompanionSession@2` lifecycle is why Companion remains a Composition rather than
only a Familiar profile or Android view: disclosure, local interaction state, offline draft,
commit, playback, reconnect, expiry, and revocation have their own reusable finish and recovery
law. The phone remains a Familiar body underneath it.

## Communion route

**Communion** remains the name of one bounded mobile interaction route inside Companion. It carries
one deliberate utterance from an enrolled client and returns a committed result, optionally spoken
aloud. Communion is therefore a route/profile, not a separate Composition.

| Layer | Owner |
| --- | --- |
| Mobile client, local session, configuration, device-feature bindings, physical controls/indicators, reconnect, and disclosure | Companion |
| Device body, hardware capabilities, physical safety, local stop, and physical effect receipts | Familiar |
| Foreground utterance route | Communion inside Companion |
| Speech-attempt admission, audio custody, transcription, synthesis, delivery/playback chronology, and revocation | Echo |
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
