---
title: Walking Communion
icon: material/account-voice
---

# :material-account-voice: Walking Communion

> _The road should not sever the Communion._

Walking Communion gives the Magus a narrow way to speak from the road without pretending that a
phone is an altar, a voice is an identity, or a spoken “yes” is authority. Its Android Mobile
Emissary carries one deliberate utterance over the Tether/Echo path and receives a committed result
in text before it is optionally heard.

| Maturity | Accepted Reference Composition — architecture, not delivery; [State of Work](../state-of-the-work.md) owns what runs |
| --- | --- |
| Identity | `walking.communion` revision `1` |
| Principal Pattern | `communion.voice_turn@1` |
| First route | foreground Android push-to-talk into a bounded destination Invocation |

It is not an always-on listener, emergency service, voice-only consent system, administrative
console, deferred command runner, or a second Lich.

## Who holds which boundary

| Concern | Owner |
| --- | --- |
| Capture permission, foreground PTT, frame sequence/digest/final/retry, playback | Mobile Emissary |
| Private reachability | Tether |
| App/device proof, scopes, revocation, object policy | Ward |
| Bounded audio, transcription, synthesis, ephemeral media custody | Echo |
| Intent admission, route, Pattern revision, logical priority | Weaver |
| Delivery and crash pickup | Workers |
| Ear/Mind/Voice capability selection | Dispatcher |
| Residency and lease transitions | Orchestrator |
| Run, result, transcript policy, and receipts | Phylactery plus the owning Composition |
| Domain effect and consent | destination Composition and HitL |

The client is intentionally thin. It holds an application key separately from its tunnel key,
performs challenge-response for short-lived scopes, shows text before or alongside speech, and
offers a local barge-in distinction between **stop speaking** and **cancel the Run**. It holds no
secrets for providers, database, durable workflow, or deferred executor. A tunnel key proves
transport possession only; it does not identify the current person/app, authorize an object, or
make a stolen device safe.

## One utterance, not an immortal session

Raw frames and live sockets never become Graph checkpoint state. The bounded path is:

```text
foreground PTT → authenticated bounded audio → transcription → preview or clarification
→ idempotent Intent → destination Invocation → committed text → optional speech
```

`communion.voice_turn@1` admits, normalizes, classifies a read-only route, clarifies or routes,
invokes Bridge or a destination, commits text, requests optional speech, and ends. A media session
may carry several turns, but every consequential utterance has its own id, pinned revision, Run,
authority, budget, and terminal outcome. Speech delivery is merely a projection: synthesis,
playback, or reconnect failure cannot erase the Principal-bound text result.

Early destinations are Bridge, note capture, and narrow read-only status. A cross-Composition
effect is a typed destination admission, not a privilege inherited through voice or a Suite edge.

## Privacy, consent, and failure

Raw voice is `restricted`; transcript and reply are at least `private`. Audio is ephemeral by
default and not training material. Portal speech requires explicit opt-in—there is no quiet
privacy fallback. Malformed, oversized, stale, duplicate, out-of-order, or replayed frames fail
shut. Low confidence produces clarification, never a guessed consequential command.

Voice cannot approve administration, purchase, publication, world rollback, or health treatment.
The destination must normalize the requested action and obtain fresh visual or touch consent. An
offline client fails visibly closed; an optional encrypted local recording is a short-lived draft
requiring review and send after reconnection, never an automatic deferred effect. Always-on capture
is a separately governed surveillance capability, not a configuration switch here.

Reconnect queries the committed result by Principal and `utterance_id`; it neither resends audio
nor replays an Intent or stale speech. Mobile protocol, codec, challenge, Intent, Pattern, and
result schemas version independently. A safe overlap is required. Incompatible parked work ends
honestly and a new visible utterance is required.

## Lifecycle and smallest proof

Communion owns enrolled-device metadata, revocation, session envelope, utterance/result correlation,
and delivery acknowledgement. The destination owns the note, project, world task, or other domain
record it admits. Retention distinguishes raw audio, transcript metadata, authentication audit, and
destination data. The Principal may inspect retained Communion metadata, delete its own history,
and revoke an enrollment; destination export/deletion stays with its owner.

The smallest proof is a fifteen-second local Android route for one enrolled adult: isolated voice
endpoint, separate app-key challenge, local Ear → text Mind → Voice, one active turn per device,
ephemeral audio, durable text, and reconnect by utterance id. Tests cover stolen tunnel key,
revoked app key, replay, object guessing, frame/transcript injection, disconnect, expiry, and
locked-device playback. No public proxy, Portal, ambient capture, mobile approval, administration,
or medical promise belongs in it.

Continue with [Echo](../sepulcher/extensions/echo.md), [Tether](../sepulcher/extensions/tether.md),
[Ward](../sepulcher/extensions/ward.md), and [Workflow](../adr/28-workflow.md).
