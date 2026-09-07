---
title: Companion
icon: material/cellphone-link
---

# :material-cellphone-link: Companion

Press to speak, inspect the words, and submit a bounded handoff. Later, an exact settled result can appear as text and optionally speech. Companion owns this mobile device experience—including privacy, disclosure, configuration, reconnect, and the difference between committed text and sound the handset actually delivered.

The phone itself is a [Familiar](../familiar/index.md) body. [Avatar](../avatar/index.md) may present the Lich through it. Those relations grant neither body authority to the client nor identity to the screen.

## Contract

`companion.mobile` revision `3` publishes `companion.admit_device@3`, `companion.open_session@3`, `companion.submit_turn@1`, and `companion.present_result@1`. Admission binds exact `FamiliarBody@3` and capability epoch, its Ward-owned device/application `Principal` and `Credential` generation, initiating Principal/current object-scoped `Authority Grant`, purpose, configuration/feature profile, capture/playback, privacy/retention, reconnect, and visible stop.

Results are immutable `CompanionDevice@3`, settled `CompanionSession@3`, `CompanionTurnHandoff@1`, and `CompanionPresentationReceipt@1`, optionally synthesized speech/local delivery, or exact partial/non-completion. Persona changes, ambient capture, mobile administration, voice-only approval, and direct deferred external effects remain outside the contract.

The enrollment order is fixed:

1. Ward owns enrollment and grants before either Composition acts.
2. Familiar admits the body, hardware, capabilities, local safety, and stops.
3. Companion pins those exact body, credential, and policy generations in its device record.

Revoked or changed facts prevent new admission and invoke the live session's downgrade/stop policy. So does a missing required microphone, speaker, display, secure storage, notification, or connectivity capability. A replacement handset or credential is no guessed continuation.

## Mobile client

The first target is native Android, planned in Kotlin/Jetpack Compose under `clients/android/**`. The client owns platform integration and local UI state while Composition records, policy, effects, and finish judgment remain native domain truth. [State of Work](../../state-of-the-work.md#composition-portfolio-delivery) owns the undelivered boundary.

Capability requirements, local routes, presentation/privacy settings, and admitted feature bindings are explicit session inputs. Extension packages may supply features without becoming an application-owned extension set. This independent disclosure, draft, commit, playback, reconnect, expiry, and revocation lifecycle is why Companion is a Composition rather than just a Familiar profile.

## Communion route

**Communion** is the bounded foreground interaction route inside Companion. [Utterance](utterance.md) follows its separately settled submission and presentation handoffs: submission does not admit destination work, and presentation begins from an already-settled result. A Product promising one live capture-to-result journey needs a named [Suite](../products-and-suites.md#compositions-relate-without-nesting) to coordinate the separate Invocations.

## Boundaries

Push-to-talk is the initial visible, foreground, revocable activation. Companion owns physical controls and indicators, local state, configuration, features, and reconnect. Echo owns speech admission, audio custody and derivation, the chronology of transcription, synthesis, delivery and playback, and revocation.

Stop speaking and cancel session are separate controls. A spoken response or microphone indicator grants no consequential authority. Text remains visible before or beside speech.

Raw voice is `restricted`; transcripts and replies are at least `private`. Audio is ephemeral by default, and recording supplies no training permission. Malformed, stale, replayed, unordered, and oversized frames fail closed.

[Utterance](utterance.md) follows the handoff; [Return](return.md) handles reconnect and custody.

Revision `3` supersedes Designed revision `2` with exact Ward enrollment and independently versioned handoff/presentation Patterns. Revision `2` had replaced revision `1`'s body claim with an exact Familiar dependency. No registry or Run used them; historical meanings remain unchanged without executable migration.

[Composition Portfolio](../index.md) · [Echo](../../sepulcher/extensions/echo.md) · [Ward](../../sepulcher/extensions/ward.md)
