---
title: 37. Audio
icon: material/headphones
---

# :material-headphones: 37. Audio

!!! abstract "Context"
    Speech has a timeline. Capture may precede a word, synthesis may succeed while delivery fails,
    and interruption may race with both. Treating audio as text with an attachment erases consent,
    privacy, and reception.

## Status

Audio admission is **Partial**. The current v1 compatibility spine can carry immutable audio
`ArtifactRef` metadata, project audio media types to the `audio` modality, and declare `stt` and
`tts` capability families. Those labels prove schema only, not a working transcription or
synthesis call.

It cannot capture, upload, store, authorize, materialize, transcode, or play audio bytes. Bridge
does not forward audio modality into dispatch. No speech timeline, streaming transport, working
STT/TTS adapter, Echo package, or Audio Coven ships. [State of
Work](../state-of-the-work.md#audio-admission) owns this boundary.

## Decision

**Echo** is the speech-lifecycle Domain. Its first profile is **record and send**: one explicit,
bounded utterance becomes an immutable artifact, then an admitted provider returns text or another
audio artifact.

| Role | Contract |
| --- | --- |
| **Ear** | `echo.transcribe@1` transcribes bounded audio; current v1 projects the `stt` family. |
| **Voice** | `echo.synthesize@1` synthesizes bounded speech; current v1 projects the `tts` family. |
| **Audio-capable Mind** | A `model.chat@1` profile declaring audio input/output; current v1 projects `chat`, and it remains chat. |
| **Listener** | Device capture, codecs, and optional voice-activity detection. |
| **Mind** | Ordinary reasoning; speech creates no separate reasoning identity. |

There is no `audio` capability family. Audio is material; current `stt`, `tts`, and `chat` are v1
compatibility families, while the Designed general-service path uses exact interfaces, profiles,
operations, and call/session grants.

## Engine, model, protocol, and language

Speech integration keeps four axes separate:

| Axis | Owns |
| --- | --- |
| **Engine/runtime** | Execution of explicitly supported model families on declared CPU or accelerator backends. |
| **Model profile** | Exact checkpoint or voice, digest, capabilities, languages, license, and measured resource envelope. |
| **Connector dialect** | Request, response, health, discovery, and cancellation shapes exposed by one endpoint. |
| **Language policy** | Ordered input and output preferences, explicit request overrides, detection permission, and fallback behavior. |

A shared file format or OpenAI-compatible route does not make an unknown model architecture
loadable. Engine support means that the exact family has a loader, preprocessing, decoding, and
tested execution path. Likewise, two servers exposing `/v1/audio/transcriptions` or
`/v1/audio/speech` may accept different fields and provide different streaming or cancellation
semantics; each admitted endpoint declares and proves its dialect.

The first planned local engine profile is **audio.cpp** behind the bounded OpenAI audio batch
subset. It is one initial runtime choice, not a new universal audio abstraction and not evidence
that every audio.cpp family works. Its Rune must pin the runtime revision, model family,
checkpoint and digest, backend and device, declared and verified languages, license, and the exact
`stt` or `tts` behavior admitted by a bake. The first record-and-send slice admits no second local
speech runtime and no automatic runtime fallback. Echo owns the current candidate models and
promotion criteria; delivery remains Not yet.

Language is neither a host-global switch nor a property inferred from the engine. An explicit
request language wins, then the admitted Principal or Persona preference, then model-supported
detection when policy allows it. A model may route a language only after declaring it; a
**verified** language additionally passed the relevant LychD bake. STT detection never silently
authorizes translation, and TTS may not substitute another language or voice when the selected
output locale is unavailable. Translation is a separate semantic act.

## Capture and custody

Capture authority is explicit, visible, time-bounded, and revocable. Consent to one utterance is
not permanent microphone access; device indicators and server state must agree whether capture is
armed, active, stopped, or failed.

Voice cloning is not implied by TTS support. A cloning request separately binds the authorized
speaker or source, reference-audio custody, permitted words and use, model and license, and the
derived voice artifact. A convincing result grants no Persona, Principal, or attribution
authority.

Reliquary custody binds recording or synthesis identity, digest, media type, byte size, validated
duration/codec facts, classification, Principal, retention, and derivation from recording,
transcript, or request. Bytes never enter a Graph checkpoint, queue payload, event envelope, or
log—only references and bounded timeline state do. Decoders and transcoders treat them as hostile:
format, duration, channels, sample rate, decompression, parser resources, and metadata are bounded
before provider use.

## Record, send, account

```text
explicit capture → immutable source artifact → eligible Ear or audio-capable Mind
→ attributed transcript or native observation → ordinary Agent step → optional Voice
→ delivery receipt
```

A transcript retains source, available time regions, provider and revision, language assumptions,
and uncertainty; it interprets a recording rather than replacing it. Synthesized audio is a new
artifact. “Generated” says bytes were produced, not that a client received, buffered, played, or
completed them.

The Pattern supplies exact interface/operation, material facts, classification, priority, and
authority. The [Dispatcher](22-dispatcher.md) chooses an exact Ear, Voice, or Mind profile; current
v1 can express only the `stt`, `tts`, or `chat` compatibility projection. For an otherwise eligible
managed binding that is not `WARM`, Dispatcher returns `HardwareTransitionRequired`; the requesting
Run enters Graph Stasis while [Orchestrator](23-orchestrator.md) converges readiness, then
re-dispatches. In current source, however, even `WARM` v1 `stt` and `tts` declarations fail closed
at grant issue because neither has a typed call surface; readiness convergence cannot turn those
labels into Ear or Voice. Echo may not preempt, revoke another grant, make its own continuing
session, or silently select a remote provider. A Portal needs egress eligibility, consent where
required, and a cost bound. Local execution does
not remove capture, retention, or tool authority; source influence persists under [Context
privatization](21-context.md#privatization-and-the-privacy-cut).

## Streaming without pretending a socket is a protocol

Record-and-send is the minimum. Half-duplex may stream one response after capture closes.
Full-duplex additionally owes simultaneous capture/playback, VAD, barge-in, echo cancellation,
and contested turn ownership.

Voice-activity detection answers whether speech is present; it does not prove that an activation
phrase was spoken. The first profile therefore uses visible push-to-talk. A future wake-word
backend belongs to the Listener and emits a bounded activation event; it is neither an `stt`
Animator nor ambient permission to retain or transcribe surrounding audio.

A **Resonance Session** keeps one monotonic timeline for segments and attempts: capture
armed/active/stopped/failed; transcription and synthesis in progress/settled/generated; delivery
offered/accepted/failed; playback started/completed/interrupted/unknown; and cancellation, expiry,
or retry. WebSocket, WebRTC, or another transport can carry these records but supplies none of
their semantics. Reconnect resumes by acknowledged sequence and artifact identity, never by
guessing from a live socket.

Cancellation names its scope: stopping playback need not erase an artifact, revoking capture stops
new input, and cancelling an Invocation settles every admitted provider and transport attempt.
A future mobile Emissary can own physical capture, playback, route selection, and low-level state;
a private Tether still supplies transport, not application authority, classification, or consent.

## Application-owned live audio

Echo's Resonance Session owns speech chronology; it does not absorb musical performance or every
application that carries sound. A Composition such as [Riffmaw](../compositions/riffmaw/sessions.md)
may own a domain session and musical-clock overlay, but every live route still obeys Audio custody,
transport, interruption, and uncertain-playback law.

Monitoring, recording, retention, analysis, transformation, remote transmission, and machine
response are independently admitted scopes. A visible armed input proves none of the others. A
live route binds an exact route and clock epoch, monotonic and sample-frame mapping, sequence,
scheduled window, absolute deadline, cancellation fence, and output acknowledgement. Late or stale
frames are rejected locally after expiry, disconnect, cancellation, or epoch change; a restarted
device, peer, model, or plug-in requires reconciliation and a newly admitted live Invocation.

The realtime callback never waits on a model, disk, network, control-plane action, or unsafe
plug-in operation. Declared direct or otherwise safe monitoring, output limiting, feedback
protection, safe bypass, and immediate local stop remain available without model cooperation.
Model and planning work occurs outside that callback and may emit only through the deadline fence.
PCM, MIDI streams, device handles, and plug-in state never enter Graph checkpoints or events; only
artifact references, bounded sequence state, epochs, and receipts cross the durable seam.

A tempo or phase protocol does not establish audio transport or a shared sample clock. A remote
audio link does not establish recording consent. Each application records mappings, drift,
resampling, loss, jitter, latency, discontinuity, and uncertainty rather than naming two devices
“synchronized” by assertion.

## Consequences and acceptance

Echo distinguishes generation, delivery, and playback and lets independent Ears, Voices, Minds,
and Listeners compose. The cost is sensitive custody, storage/retention pressure, and timing,
cancellation, and egress races.

It cannot move beyond its schema seam until evidence proves visible capture consent, custody,
hostile-audio limits, modality forwarding, local and Portal policy, STT/TTS conversion, transcript
provenance, delivery/playback receipts, interruption, retention/deletion, and disconnect recovery.
