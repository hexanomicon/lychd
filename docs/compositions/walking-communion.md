---
title: Communion
icon: material/account-voice
---

# :material-account-voice: Communion

Communion is the reference mobile route into an admitted LychD Pattern. It is a Portfolio
companion rather than a Composition: speaking on the road is an ingress and result-projection path,
while the selected application or Core owner keeps the purpose, records, judgment, and effects.

The route carries one deliberate utterance from an enrolled Android client, returns committed text,
and may then speak that text. It does not turn a phone into the Altar, a tunnel key into identity,
or a spoken “yes” into authority.

## Route contract

| | |
| --- | --- |
| **Profile** | `walking.communion` revision `1` |
| **Begins with** | foreground push-to-talk from one enrolled application and current Principal |
| **Carries** | bounded audio, one typed Intent, correlation, and a committed text result |
| **Returns** | text first, with optional synthesized speech as a projection |
| **Stops before** | ambient capture, emergency monitoring, mobile administration, deferred effects, or voice-only consent |

The route owns no application Pattern. After transcription and review, a designed caller and
channel policy produces an admitted Intent for an eligible application purpose; Weaver then routes
that Intent to an exact registered Pattern. The channel does not acquire application purpose
merely because it can carry many purposes, and live Portfolio selection remains Designed.

## One utterance

1. The foreground client opens push-to-talk and binds a fresh utterance identity, frame sequence,
   byte and duration ceilings, codec profile, and expiry.
2. Tether may provide private reachability. Ward separately proves the application, device,
   Principal, current scopes, and object authority; possession of either key proves only its own
   boundary.
3. Echo admits bounded frames, produces an attributed transcript, and drops raw audio under the
   selected retention policy. Low confidence asks for clarification.
4. The client shows the transcript when policy requires review, then submits one idempotent Intent.
5. Weaver routes the admitted Intent to an exact registered Pattern. Its owning Composition or
   Core surface performs any domain-specific clarification, consent, work, and recovery.
6. The committed text result becomes the durable answer. Speech synthesis and playback may fail or
   be interrupted without erasing it.

```text
push-to-talk → authenticate → transcribe → preview or clarify
→ typed Intent → admitted Pattern → committed text → optional speech
```

## Divided authority

| Boundary | Owner |
| --- | --- |
| capture, frame transport, playback, and local interruption | Mobile Emissary |
| tunnel reachability | Tether |
| device, Principal, scopes, and revocation | Ward |
| bounded audio, transcription, synthesis, and media custody | Echo |
| Intent, Pattern, Run, and delivery | Weaver, Workers, and Phylactery |
| domain records, consequential effects, and consent | destination application or Core owner and its effect owners |

The thin client carries no provider, database, workflow, or host-lifecycle credential. It
distinguishes **stop speaking** from **cancel the Run**, and text remains visible before or beside
audio. The first proving targets are Core routes—Bridge conversation, note capture, and narrow
read-only status—not Portfolio Compositions. A future Composition route remains unavailable until
its Pattern and application selection are actually registered. None of these routes grants
administrative or purchase authority.

## Privacy and recovery

Raw voice is `restricted`; transcript and reply are at least `private`. Audio is ephemeral by
default and is never training material merely because it was captured. Portal speech requires an
explicit, exact egress decision. Malformed, stale, duplicate, replayed, out-of-order, or oversized
frames fail closed, and a transcript cannot smuggle instructions around destination policy.

Reconnect asks for the committed result by Principal and utterance identity. It does not resend
audio, replay the Intent, or deliver an expired command. An optional offline recording is a
short-lived draft that requires review after reconnection; it never becomes an automatic queued
effect. Enrollment revocation and destination export or deletion remain separate owner actions.

## Proving the mobile route

Use a fifteen-second local Android fixture for one enrolled adult: separate tunnel and application
keys, local speech recognition, one text-capable destination, optional synthesis, ephemeral audio,
durable text, and reconnect by utterance id. Test a stolen tunnel key, revoked application key,
replay, object guessing, transcript injection, disconnect, expiry, and locked-device playback. No
public proxy, Portal, ambient capture, mobile approval, administration, or medical promise enters
the proof.

Continue with [Echo](../sepulcher/extensions/echo.md), [Tether](../sepulcher/extensions/tether.md),
[Ward](../sepulcher/extensions/ward.md), or the [Composition Portfolio](index.md).
