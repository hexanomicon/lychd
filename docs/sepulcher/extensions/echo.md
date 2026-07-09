---
title: Echo
icon: material/waveform
---

# :material-waveform: Audio Echo

_Status: doctrine ahead of code — the built-in `audio` package is where this lands; treat this page as design intent. Law: [ADR 37](../../adr/37-audio.md). Current truth: [source map](./index.md#the-federation-of-fifteen)._

> _"A text-only Daemon is blind to the physical resonance of the world. To exist as a pervasive companion, the Lich must perceive vibration and project resonance—transforming the cold silence of the Crypt into a living stream of intent."_

**The Echo** is the planned Audio Extension of the LychD system. It is the reference design for a
future Audio Coven—a stateful capability for real-time voice communion defined in
**[ADR 37 (Audio)](../../adr/37-audio.md)**.

The planned **Resonance Pipeline** treats audio as a real-time stream rather than a static file. It
will connect speech-to-text (STT), agent reasoning, and text-to-speech (TTS) without claiming that
the current immutable artifact-reference seam already carries playable bytes.

## I. The Audio Coven: A Manifestation of Resonance

Resonance is not a single model; it is an entire operational state. The future extension will group
local **[Soulstones](../animator/soulstone.md)** rendered as
**[Quadlet services](../../adr/08-containers.md)** and readied under
**[Orchestrator](../../adr/23-orchestrator.md)** policy. The target form includes:

- **The Ear (`stt.container`):** A Soulstone for a high-performance Speech-to-Text model (e.g., `faster-whisper`), tagged with `capability="stt"`.
- **The Voice (`tts.container`):** A Soulstone for a streaming Text-to-Speech model (e.g., `Piper`), tagged with `capability="tts"`.
- **The Mind (`llm.container`):** The Coven may include a smaller, faster reasoning model for low-latency conversational tasks.

## II. The Planned Resonance Pipeline (Buffer & Stream)

!!! warning "Current audio boundary"
    The current core can persist an immutable audio `ArtifactRef` and filter declared audio
    modality metadata. It has no blob materializer, Bridge/graph binary propagation, audio
    WebSocket, resonance buffer, or working STT/TTS adapters. The pipeline below is target design.

The Echo will establish a low-latency WebSocket pipeline mounted onto the
**[Vessel](../vessel/index.md)**.

1. **Ingest:** The client connects via the **[Tether](./tether.md)** and streams raw audio bytes.
2. **Perception:** The pipeline routes the audio stream to the **Ear** Animator for real-time transcription.
3. **Cognition:** The resulting text is fed into a reasoning **[Agent](../../adr/20-agents.md)**.
4. **Synthesis:** As the Agent generates response tokens, they are piped _instantly_ to the **Voice** Animator.
5. **The Resonance Buffer:** If the WebSocket is closed or unstable, the synthesized audio bytes are not discarded. They are serialized into the **[Phylactery Queue](../../adr/06-persistence.md)**. Upon reconnection, the Echo flushes the buffer, delivering the "missed whispers."

## III. Dual-Mode Orchestration

The target Audio extension will use the **[Orchestrator](../../adr/23-orchestrator.md)** in two
distinct modes.

### Mode A: The Reflex (User Initiated)

When the Magus speaks:

- **The Signal:** The extension sends a **High-Priority Signal** to the Orchestrator.
- **Preemption:** The Orchestrator **Preempts** any running background jobs (e.g., pausing a crawler), drains the current Coven, and manifests the `audio.coven` immediately.

### Mode B: The Tool (Agent Initiated)

When a text-based Agent decides to speak:

- **The Call:** The Agent invokes the `generate_speech` tool.
- **The Stasis:** If the Audio Coven is **COLD**, the **[Dispatcher](../../adr/22-dispatcher.md)** triggers the **[Stasis Protocol](../../adr/22-dispatcher.md)**. The Agent freezes, the Orchestrator swaps the hardware, and the Agent wakes up to speak.

## IV. The Mobile Emissary (Android)

The target design may project the Echo through a **Mobile Emissary**—a native application acting as
the physical mouthpiece of the Lich.

- **Hardware Binding:** The Emissary handles low-level Voice Activity Detection (VAD) and audio hardware management.
- **The Secure Thread:** By tunneling its traffic through the **[Tether](./tether.md)**, the Emissary ensures that voice biometrics and private whispers are protected by WireGuard encryption.

!!! tip "Sensory Model Agnosticism"
    Because the Echo Coven utilizes the standard **[Dispatcher](../../adr/22-dispatcher.md)** protocols, the Magus can swap the system's "Ears" or "Voice." If a more human timbre is required, the Echo may point to a **[Portal](../animator/portal.md)** for high-fidelity TTS (e.g., ElevenLabs), provided the Tithe of tokens is acceptable.
