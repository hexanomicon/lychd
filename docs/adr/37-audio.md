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

Audio admission is **Partial**. The core can carry immutable audio `ArtifactRef` metadata, project
audio media types to the `audio` modality, and declare `stt` and `tts` capability families.

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
| **Ear** | An `stt` capability transcribes bounded audio. |
| **Voice** | A `tts` capability synthesizes bounded speech. |
| **Audio-capable Mind** | A `chat` capability declaring audio input/output; it remains chat. |
| **Listener** | Device capture, codecs, and optional voice-activity detection. |
| **Mind** | Ordinary reasoning; speech creates no separate reasoning identity. |

There is no `audio` capability family. Audio is a modality; `stt`, `tts`, and `chat` name
different service kinds.

## Capture and custody

Capture authority is explicit, visible, time-bounded, and revocable. Consent to one utterance is
not permanent microphone access; device indicators and server state must agree whether capture is
armed, active, stopped, or failed.

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

The Pattern supplies family, modality, classification, priority, and authority. The
[Dispatcher](22-dispatcher.md) chooses exact `stt`, `tts`, or `chat`; an unwarm managed provider
uses ordinary Graph Stasis and [Orchestrator](23-orchestrator.md) readiness. Echo may not preempt,
revoke another grant, make its own continuing session, or silently select a remote provider. A
Portal needs egress eligibility, consent where required, and a cost bound. Local execution does
not remove capture, retention, or tool authority; source influence persists under [Context
privatization](21-context.md#privatization-and-the-privacy-cut).

## Streaming without pretending a socket is a protocol

Record-and-send is the minimum. Half-duplex may stream one response after capture closes.
Full-duplex additionally owes simultaneous capture/playback, VAD, barge-in, echo cancellation,
and contested turn ownership.

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

## Consequences and acceptance

Echo distinguishes generation, delivery, and playback and lets independent Ears, Voices, Minds,
and Listeners compose. The cost is sensitive custody, storage/retention pressure, and timing,
cancellation, and egress races.

It cannot move beyond its schema seam until evidence proves visible capture consent, custody,
hostile-audio limits, modality forwarding, local and Portal policy, STT/TTS conversion, transcript
provenance, delivery/playback receipts, interruption, retention/deletion, and disconnect recovery.
