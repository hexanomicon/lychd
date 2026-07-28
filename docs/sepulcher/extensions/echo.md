---
title: Echo
icon: material/waveform
---

# :material-waveform: Audio Echo

_Status: doctrine ahead of code — no concrete Echo package or speech provider ships; treat this
page as design intent. Law: [ADR 37](../../adr/37-audio.md). Current truth:
[source map](./index.md#the-federation-of-fifteen)._

**Extension form:** Echo is a temporal speech-lifecycle Domain. Batch or streaming STT, TTS,
audio-capable chat, codecs, and VAD remain independent Animator or client providers. Text-only,
record-and-send, half-duplex streaming, and later full-duplex profiles may activate different
subsets; no atomic Audio Coven is required.

> _"A text-only Daemon is blind to the physical resonance of the world. To exist as a pervasive companion, the Lich must perceive vibration and project resonance—transforming the cold silence of the Crypt into a living stream of intent."_

**The Echo** is LychD's temporal speech-lifecycle Domain, defined by
**[ADR 37 (Audio)](../../adr/37-audio.md)**. It joins capture, transcription, reasoning,
synthesis, playback, interruption, and delivery receipts without pretending that they must be one
service or always-live session.

The planned **Resonance Pipeline** supports a simple record-and-send profile first. Streaming is a
later latency optimization, not a prerequisite for voice. The current immutable artifact-reference
seam still does not carry playable bytes.

## I. Manifestations of Resonance

A voice profile may combine any useful subset:

- **The Ear:** A dedicated `stt` Animator for transcription.
- **The Voice:** A dedicated `tts` Animator for synthesis.
- **Audio-capable chat:** A `chat` provider declaring `audio` input or output modalities; it
  remains chat rather than becoming an Ear or Voice.
- **The Listener:** Client-side or server-side VAD, push-to-talk, codecs, and capture controls.
- **The Mind:** The ordinary selected reasoning provider. Echo does not require a special voice
  mind.

Local providers may be rendered as
**[Quadlets](../../adr/08-containers.md)** and readied under
**[Orchestrator](../../adr/23-orchestrator.md)** policy. Each provider has its own readiness,
resource, privacy, and support envelope.

## II. The Planned Resonance Pipeline

!!! warning "Current audio boundary"
    The current core can persist an immutable audio `ArtifactRef` and filter declared audio
    modality metadata. It has no blob materializer, Bridge/graph binary propagation, audio
    transport, speech timeline, or working STT/TTS adapters. The pipeline below is target design.

The minimum viable rite is deliberately small:

1. **Capture:** The client records a bounded clip under explicit microphone state and consent.
2. **Admit:** The clip enters the Reliquary as an immutable artifact with digest, media type,
   duration, classification, and retention policy.
3. **Perceive:** The Dispatcher grants one eligible Ear or audio-capable chat provider.
4. **Think:** The resulting attributed transcript or native audio input enters an ordinary
   **[Agent](../../adr/20-agents.md)** step.
5. **Respond:** Text may be returned directly or granted to one eligible Voice provider.
6. **Deliver:** Playback state and delivery receipts belong to a bounded Resonance Session. Large
   audio bytes remain in artifact custody rather than being serialized into graph checkpoints or a
   fictional Phylactery queue.

A later half-duplex transport may stream response audio as it becomes playable. Full-duplex
capture, interruption, echo cancellation, and barge-in require an explicit speech timeline and
session protocol; they are not smuggled in by choosing WebSockets.

## III. Orchestration Without Privilege Inflation

User speech and agent-requested speech enter the same admission law:

- Voice input does not automatically outrank admitted work. The Pattern and operator policy
  declare urgency; the Orchestrator only applies the resulting physical priority.
- The Dispatcher selects the exact `stt`, `tts`, or `chat` provider. A managed non-`WARM`
  provider uses the ordinary **[Stasis Protocol](../../adr/22-dispatcher.md)**.
- The Orchestrator converges that provider and its declared dependencies. Echo cannot preempt
  work, revoke leases, or manifest an atomic Audio Coven on its own authority.
- A provider grant is scoped to one step or Resonance Session and does not imply continued
  microphone access.

## IV. The Mobile Emissary (Android)

The target design may project the Echo through a **Mobile Emissary**—a native application acting as
the physical mouthpiece of the Lich.

- **Hardware Binding:** The Emissary handles low-level Voice Activity Detection (VAD) and audio hardware management.
- **The Secure Thread:** A private **[Tether](./tether.md)** is one supported transport profile,
  not a requirement of Echo. Ward admission, application authentication, explicit capture state,
  and artifact classification still apply inside any encrypted tunnel.

!!! tip "Sensory Model Agnosticism"
    Because Echo uses the standard **[Dispatcher](../../adr/22-dispatcher.md)** contracts, the
    Magus can select different Ears and Voices independently. A remote
    **[Portal](../animator/portal.md)** additionally requires Ward egress policy, classification
    eligibility, consent where required, and an economic budget.
