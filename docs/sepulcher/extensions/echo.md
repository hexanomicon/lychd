---
title: Echo
icon: material/waveform
---

# :material-waveform: Echo: Archon of Resonance

> _"A text-only Daemon is blind to the physical resonance of the world. To exist as a pervasive companion, the Lych must perceive vibration and project resonance—transforming the cold silence of the Crypt into a living stream of intent."_

**The Echo** is the Sensory Archon of the LychD system. It is the reference implementation of the `audio.coven`—a complete, stateful capability for real-time voice communion, as defined in **[ADR 32 (Audio)](../../adr/32-audio.md)**.

By treating audio not as static "file uploads" but as a real-time **Resonance Pipeline**, the Echo bridges the sensory gap. It is a specialized extension that enables the Daemon to perceive the spoken word (STT), reason upon it, and project its own voice (TTS) in a single, fluid motion.

## I. The Audio Coven: A Manifestation of Resonance

Resonance is not a single model; it is an entire operational state. The Echo manifests the `audio.coven`, a collection of **[Systemd Runes](../../adr/08-containers.md)** managed as one atomic unit by the **[Orchestrator](../../adr/21-orchestrator.md)**. The Archon's form includes:

- **The Ear (`stt.container`):** A Rune for a high-performance Speech-to-Text model (e.g., `faster-whisper`), tagged with `capability="stt"`.
- **The Voice (`tts.container`):** A Rune for a streaming Text-to-Speech model (e.g., `Piper`), tagged with `capability="tts"`.
- **The Mind (`llm.container`):** The Coven may include a smaller, faster reasoning model for low-latency conversational tasks.

Activating the Echo means manifesting this entire Coven, preparing the Daemon for immediate, vocal interaction.

## II. The Resonance Pipeline (WebSocket)

The Echo rejects the high-latency REST patterns of the mundane web. It establishes a low-latency WebSocket pipeline mounted directly onto the **[Vessel](../vessel/index.md)**, creating a continuous, bidirectional cognitive loop.

1. **Ingest:** The client (The Emissary) connects via the **[Tether](./tether.md)** and streams raw audio bytes.
2. **Perception:** The pipeline routes the audio stream to the **Ear** Rune for real-time transcription.
3. **Cognition:** The resulting text is fed into a reasoning **[Agent](../../adr/19-agents.md)** as a high-priority intent.
4. **Synthesis:** As the Agent generates response tokens, they are piped _instantly_ to the **Voice** Rune for synthesis into audio bytes.
5. **Projection:** The audio bytes flow back to the Magus, often before the Agent has even finished "thinking," creating a seamless illusion of telepresence.

## III. Orchestration of the Reflex

In the logic of the **[Orchestrator](../../adr/21-orchestrator.md)**, an incoming audio stream is a **Reflex of the Highest Order**.

- **Preemptive Priority:** Audio intents carry an extreme "Whim Weight." If the GPU is occupied by a background "Ritual" (such as a long-running **[Simulation](../../adr/35-simulation.md)**), the Orchestrator will pause the labor and perform an immediate state transition to manifest the `audio.coven`.
- **Telepresence:** This ensures that the Lych answers the Magus instantly, maintaining the illusion of a living, present entity.

## IV. The Mobile Emissary (Android)

To project the Echo into the physical world, the system utilizes a **Mobile Emissary**—a native application that acts as the physical mouthpiece of the Lych.

- **Hardware Binding:** The Emissary handles low-level Voice Activity Detection (VAD) and audio hardware management.
- **The Secure Thread:** By tunneling its traffic through the **[Tether](./tether.md)**, the Emissary ensures that voice biometrics and private whispers are protected by Wireguard encryption.
- **Hands-Free Communion:** The Emissary provides the ultimate accessibility tool, allowing the Magus to command the Sepulcher through voice alone, whether in the Lab or the Outlands.

!!! tip "Sensory Model Agnosticism"
    Because the Echo Coven utilizes the standard **[Dispatcher](../../adr/20-dispatcher.md)** protocols, you can swap your "Ears" or "Voice." If you require a more "human" soul, you may point the Echo to a **[Portal](../animator/portal.md)** for high-fidelity TTS (e.g., ElevenLabs), provided the Tithe of tokens is acceptable.
