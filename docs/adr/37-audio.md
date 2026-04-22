---
title: 37. Audio
icon: material/headphones
---

# :material-headphones: 37. The Audio Echo

!!! abstract "Context and Problem Statement"
    A text-only Daemon remains blind to the physical resonance of the world. To exist as a pervasive companion, the Lych requires sensory organs capable of perceiving vibration (Speech-to-Text) and projecting resonance (Text-to-Speech). Standard HTTP request-response patterns introduce unacceptable latency. Furthermore, these heavy acoustic models require significant VRAM, creating a conflict with reasoning engines. A specialized pipeline is required to treat voice as a real-time stream while managing the physical costs of the sensory apparatus.

## Requirements

* **Atomic Coven Manifestation:** Mandatory grouping of STT (Ear), TTS (Voice), and Logic models into a single **[Coven (08)](08-containers.md)** to ensure hardware synchronicity.
* **The Reflex Priority:** Incoming user audio must be treated as a **Reflex**, signaling the **[Orchestrator (23)](23-orchestrator.md)** to immediately preempt or pause background rituals to free VRAM.
* **The Stasis Trigger:** Integration with the **[Dispatcher (22)](22-dispatcher.md)**. If an Agent proactively invokes an audio tool (e.g., `speak_text`) while the hardware is "Cold," it must raise the `HardwareTransitionRequired` signal to freeze the graph via the **[Stasis Protocol (22)](22-dispatcher.md)**.
* **Resonance Buffering:** Capability to queue synthesized audio if the client socket is disconnected, ensuring the Magus hears the "missed whispers" upon reconnection.
* **Biometric Streaming Transport:** Provision of a real-time, bidirectional streaming protocol (WebSockets) to minimize the latency between perception and response.
* **Portal/Soulstone Duality:** Support for both local inference (**Soulstones**) for sovereignty and cloud providers (**Portals**) for high-fidelity synthesis, managed transparently by the Dispatcher.

## Considered Options

!!! failure "Option 1: Frontend-Only Processing (Browser APIs)"
    Utilizing the browser's native Web Speech APIs.

    -   **Cons:** **Privacy Ceiling.** Browser-based STT often routes data through corporate clouds, violating the **[Iron Pact (00)](00-license.md)**.

!!! failure "Option 2: Asynchronous File Processing"
    Treating audio as a standard file attachment.

    -   **Cons:** **The Walkie-Talkie Latency.** The multi-second delay destroys the "Flow of Consciousness."

!!! success "Option 3: The Audio Coven (Stateful Resonance)"
    Deploying specialized audio containers as a dynamically activated operational state, exposed via a real-time WebSocket pipeline and managed via the Stasis Protocol.

    -   **Pros:**
        -   **Telepresence:** Collapses the perception-cognition-action loop to sub-second latencies.
        -   **Hardware Safety:** The Orchestrator ensures VRAM-heavy audio models are only resident when a vocal communion is active.
        -   **Delivery Assurance:** Uses the Resonance Buffer to prevent lost speech during connectivity drops.

## Decision Outcome

**The Echo** is adopted as the Audio Extension. It manifests the `audio.coven` and registers both **Animators** (Stream Providers) and **Tools** (Discrete Capabilities).

### 1. The Audio Coven (Body)

The Echo manifests as a collection of **[Quadlet services (08)](08-containers.md)**:

* **The Ear (`stt.container`):** A high-performance Speech-to-Text service (e.g., Faster-Whisper).
* **The Voice (`tts.container`):** A streaming Text-to-Speech service (e.g., Piper).
* **The Mind:** A lower-tier Reasoning Soulstone (e.g., 1B-8B model) optimized for conversational reflexes.

### 2. The Resonance Pipeline (Buffer & Stream)

The Echo establishes a persistent WebSocket loop:

* **Streaming:** When connected, audio tokens are piped instantly from Agent to TTS to Client.
* **The Resonance Buffer:** If the WebSocket is closed or unstable, the synthesized audio bytes are not discarded. They are serialized into the **[Phylactery Queue (06)](06-persistence.md)**.
* **Playback:** Upon reconnection, the Echo flushes the buffer, delivering the "missed whispers" in sequence before resuming live streaming.

### 3. The Dual-Mode Orchestration

The Echo interacts with the **[Orchestrator (23)](23-orchestrator.md)** in two distinct ways:

#### Mode A: The Reflex (User Initiated)

When the Magus speaks:

1. The **Vessel** detects the handshake.
2. It sends a **High-Priority Signal** to the Orchestrator.
3. The Orchestrator **Preempts** background jobs and manifests the `audio.coven`.

#### Mode B: The Tool (Agent Initiated)

When a text-based Agent decides to speak:

1. The Agent calls `generate_speech(text)`.
2. The **[Dispatcher (22)](22-dispatcher.md)** checks the target service.
3. If **COLD**: It triggers the **Stasis Protocol**. The Agent freezes. The Orchestrator performs the swap. The Agent wakes up and speaks.

### 4. Sensory Dispatching (Portals & Soulstones)

The Echo utilizes the **[Dispatcher (22)](22-dispatcher.md)** to resolve capabilities:

* **Soulstones:** Local, free, private (Whisper/Piper).
* **Portals:** Remote, high-fidelity, paid (Deepgram/ElevenLabs).
* **Abstraction:** To the Agent, the `stt` and `tts` capabilities are identical regardless of the provider.

## Consequences

!!! success "Positive"
    - **Conversational Immersion:** The streaming pipeline collapses the sensory gap.
    - **Delivery Guarantee:** The Resonance Buffer ensures no words are lost to network jitter.
    - **Logical Safety:** The Stasis Protocol prevents the Agent from crashing if it tries to speak while the audio engine is cold.

!!! failure "Negative"
    - **VRAM Hunger:** Running STT, TTS, and reasoning models simultaneously can challenge mid-range GPUs.
    - **Storage Pressure:** A large Resonance Buffer of unconsumed audio can bloat the database if the user remains offline for extended periods.
