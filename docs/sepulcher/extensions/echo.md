---
title: Echo
icon: material/waveform
---

# :material-waveform: Audio Echo

> _"A text-only Daemon is blind to the physical resonance of the world. To exist as a pervasive companion, the Lych must perceive vibration and project resonance—transforming the cold silence of the Crypt into a living stream of intent."_

**The Echo** is the Audio Extension of the LychD system. It is the reference implementation of the `audio.coven`—a complete, stateful capability for real-time voice communion, as defined in **[ADR 37 (Audio)](../../adr/37-audio.md)**.

By treating audio not as static "file uploads" but as a real-time **Resonance Pipeline**, The Echo bridges the sensory gap. It is a specialized extension that enables the Daemon to perceive the spoken word (STT), reason upon it, and project its own voice (TTS) in a single, fluid motion.

## I. The Audio Coven: A Manifestation of Resonance

Resonance is not a single model; it is an entire operational state. The extension manifests the `audio.coven`, a collection of **[Systemd Runes](../../adr/08-containers.md)** managed as one atomic unit by the **[Orchestrator](../../adr/23-orchestrator.md)**. The form includes:

- **The Ear (`stt.container`):** A Rune for a high-performance Speech-to-Text model (e.g., `faster-whisper`), tagged with `capability="stt"`.
- **The Voice (`tts.container`):** A Rune for a streaming Text-to-Speech model (e.g., `Piper`), tagged with `capability="tts"`.
- **The Mind (`llm.container`):** The Coven may include a smaller, faster reasoning model for low-latency conversational tasks.

## II. The Resonance Pipeline (Buffer & Stream)

The Echo rejects the high-latency REST patterns of the mundane web. It establishes a low-latency WebSocket pipeline mounted directly onto the **[Vessel](../vessel/index.md)**.

1. **Ingest:** The client connects via the **[Tether](./tether.md)** and streams raw audio bytes.
2. **Perception:** The pipeline routes the audio stream to the **Ear** Rune for real-time transcription.
3. **Cognition:** The resulting text is fed into a reasoning **[Agent](../../adr/20-agents.md)**.
4. **Synthesis:** As the Agent generates response tokens, they are piped _instantly_ to the **Voice** Rune.
5. **The Resonance Buffer:** If the WebSocket is closed or unstable, the synthesized audio bytes are not discarded. They are serialized into the **[Phylactery Queue](../../adr/06-persistence.md)**. Upon reconnection, the Echo flushes the buffer, delivering the "missed whispers."

## III. Dual-Mode Orchestration

In the logic of the **[Orchestrator](../../adr/23-orchestrator.md)**, audio operates in two distinct modes.

### Mode A: The Reflex (User Initiated)

When the Magus speaks:

- **The Signal:** The extension sends a **High-Priority Signal** to the Orchestrator.
- **Preemption:** The Orchestrator **Preempts** any running background jobs (e.g., pausing a crawler), drains the current Coven, and manifests the `audio.coven` immediately.

### Mode B: The Tool (Agent Initiated)

When a text-based Agent decides to speak:

- **The Call:** The Agent invokes the `generate_speech` tool.
- **The Stasis:** If the Audio Coven is **COLD**, the **[Dispatcher](../../adr/22-dispatcher.md)** triggers the **[Stasis Protocol](../../adr/22-dispatcher.md)**. The Agent freezes, the Orchestrator swaps the hardware, and the Agent wakes up to speak.

## IV. The Mobile Emissary (Android)

To project the Echo into the physical world, the system utilizes a **Mobile Emissary**—a native application that acts as the physical mouthpiece of the Lych.

- **Hardware Binding:** The Emissary handles low-level Voice Activity Detection (VAD) and audio hardware management.
- **The Secure Thread:** By tunneling its traffic through the **[Tether](./tether.md)**, the Emissary ensures that voice biometrics and private whispers are protected by Wireguard encryption.

!!! tip "Sensory Model Agnosticism"
    Because the Echo Coven utilizes the standard **[Dispatcher](../../adr/22-dispatcher.md)** protocols, you can swap your "Ears" or "Voice." If you require a more "human" soul, you may point the Echo to a **[Portal](../animator/portal.md)** for high-fidelity TTS (e.g., ElevenLabs), provided the Tithe of tokens is acceptable.
