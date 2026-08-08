---
title: Echo
icon: material/ear-hearing-loop
---

# :material-ear-hearing-loop: Echo

> _A voice is not delivered when it is made, but when another body receives it._

**Echo** is the speech-lifecycle Extension Domain. It carries an utterance from deliberate capture
to actual reception without losing its origin, consent, or outcome.
Audio admission is **Partial**, but no working Echo package or speech path ships.
[ADR 37](../../adr/37-audio.md) owns the accepted design;
[State of Work](../../state-of-the-work.md#audio-admission) owns delivery truth.

## The organs of resonance

An Echo deployment composes five roles independently. Audio is material, never a capability
family; `stt`, `tts`, and `chat` below are current v1 compatibility labels, not the Designed
general-service ABI.

| Role | Place in Echo |
| --- | --- |
| **Ear** | `echo.transcribe@1` Animator; current v1 projects `stt` |
| **Voice** | `echo.synthesize@1` Animator; current v1 projects `tts` |
| **Audio-capable Mind** | Audio-input or audio-output `model.chat@1` provider; current v1 projects `chat` |
| **Listener** | Capture, push-to-talk, codecs, and optional voice activity |
| **Mind** | Ordinary reasoning provider; there is no separate voice intelligence |

## First engine profile

The first planned local profile deliberately admits one inference engine:

| Concern | Initial choice | Boundary |
| --- | --- | --- |
| Engine | [audio.cpp](https://github.com/0xShug0/audio.cpp) | One pinned local runtime; support is family-specific, never arbitrary GGUF execution. |
| Ear candidate | Parakeet TDT 0.6B v3 | Multilingual STT candidate whose Slovak path must pass the bake. |
| Voice candidate | Supertonic 3 | Multilingual TTS candidate whose Slovak voices and OpenRAIL-M terms must pass the bake. |
| Connector | OpenAI audio batch dialect | Bounded transcription and speech routes only; runtime-native extras are not inferred. |
| Activation | Visible push-to-talk | No always-on capture and no wake-word dependency. |
| Interaction | Record and send | No claim of full-duplex speech or barge-in. |

This is designed direction, not delivered integration. The initial implementation should prove
audio-to-text and text-to-audio before exposing audio.cpp voice conversion, cloning, alignment,
VAD, diarization, codecs, or pipelines. Those functions become separately declared tool surfaces
only after their model, inputs, outputs, custody, authority, and cancellation behavior are baked;
the presence of a family in an upstream catalogue grants no LychD capability.

One connector may serve several compatible model profiles, but every profile keeps its own model
identity, language facts, license, backend, resource measurements, and readiness. A language can
be **declared** from upstream metadata without being **verified** by LychD. Routing uses an
explicit request first, then ordered Principal or Persona preferences, then admitted detection;
missing output-language support refuses rather than silently translating.

## Watched alternatives

The first profile does not implement these paths:

| Candidate | Why it remains watched | Promotion condition |
| --- | --- | --- |
| [NeMo-Speech.cpp](https://github.com/NVIDIA/NeMo-Speech.cpp) | Narrower NVIDIA speech runtime with promising realtime, endpointing, word-timing, and Riva surfaces. | Stable pinned release and dialect, lifecycle and cancellation receipts, and a multilingual realtime bake that materially beats the audio.cpp path. |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Mature, portable Whisper-only STT fallback. | A required platform or recovery case that audio.cpp cannot satisfy. |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) | Small CPU TTS fallback with separately licensed voices. | A measured low-resource or recovery need that Supertonic through audio.cpp cannot satisfy, plus runtime and voice-license admission. |
| [openWakeWord](https://github.com/dscripka/openWakeWord) | Host-side wake-word candidate, not a speech server. | An authorized phrase/model with acceptable license, reproducible training or acquisition, and measured false-accept and false-reject rates in the target language and environment. |

NeMo-Speech.cpp may later reuse the batch connector through an explicit dialect, while its live
WebSocket still needs a Resonance Session adapter. Whisper, Piper, and openWakeWord are not
installed merely as speculative redundancy. No watched candidate is an automatic fallback, and
no failed local attempt silently changes engine, language, or egress.

## The first bake

The smallest honest evaluation fixes one runtime revision and model digest, then records:

- cold start, readiness, clean shutdown, cancellation, CPU/GPU placement, RAM/VRAM peak, and
  isolation from a resident Mind;
- transcription accuracy, endpoint truncation, names, numbers, mixed-language speech, confidence,
  and provenance for each language claimed as verified;
- synthesis latency, first audio, intelligibility, pronunciation, numbers, dates, currency,
  addresses, text normalization, and playback completion for each output locale and voice;
- exact OpenAI-compatible fields and errors rather than compatibility by endpoint name; and
- license and consent receipts before any voice-reference or cloning experiment.

Slovak is the first operator-selected reference bake, not a Core hardcode. Other users may order
different input and output preferences, but every routed language owes the same evidence.

## The resonance path

Record-and-send is the first accepted profile:

> visible bounded capture → immutable audio artifact → eligible Ear or audio-capable Mind →
> attributed transcript or native observation → ordinary Agent step → optional Voice → delivery
> evidence

Capture must be visible, bounded, and consented. Large bytes remain outside Graph checkpoints and
queues.

Three distinctions keep the path honest:

- Current `ArtifactRef` support is metadata only. The
  [artifact-reference boundary](../../state-of-the-work.md#artifact-reference-contract) proves
  neither a stored recording nor playable byte custody.
- In the accepted design, Reliquary custody preserves source and derivation. A transcript is an
  attributed interpretation, not a replacement for its recording.
- Synthesized audio is a new artifact. Generation proves neither delivery nor playback; receipts
  must state what actually reached the listener.

Later half- and full-duplex profiles must preserve one monotonic speech timeline through barge-in,
contested turn ownership, interruption, cancellation, and reconnect. A live socket cannot supply
those semantics.

Invalid audio, insufficient authority, and policy-ineligible remote egress are refused. Only an
otherwise eligible managed provider that is not warm may cause the requesting Run to enter
ordinary Graph Stasis while Orchestrator drains and readies the affected Animators. Echo cannot silently fall back to a remote service, infer permanent
microphone authority, inflate priority, or revoke another grant or lease.

## The Emissary

A future Mobile Emissary may own device capture and playback as Echo's physical ear and mouth. A
private [Tether](tether.md) supplies reachability, not caller authority:
[Ward](ward.md) still authenticates and authorizes, while capture and consent remain visible. A
remote [Portal](../animator/portal.md) additionally requires eligible classification, egress
policy, consent where required, and bounded cost. These are laws of the accepted design, not
claims of delivered behavior.

Operationally, Echo preserves where speech began and whether the answer arrived.
