---
title: 32. Audio
icon: fontawesome/solid/headphones
---

# :fontawesome-solid-headphones: 32. Audio: The Echo

!!! abstract "Context and Problem Statement"
    A text-only Daemon remains blind to the physical resonance of the world, creating a sensory barrier for those in motion or focused elsewhere. To exist as a pervasive companion, the Lych requires sensory organs capable of perceiving vibration (Speech-to-Text) and projecting resonance (Text-to-Speech). Standard HTTP request-response patterns introduce unacceptable latency, destroying the illusion of telepresence. A specialized, low-latency pipeline is required to treat voice not as an asynchronous file exchange, but as a living, biometrically-sensitive stream of intent.

## Requirements

- **Atomic Coven Management:** Mandatory management of the entire audio processing stack (STT, TTS, and conversational model) as a single, atomic **[Coven (08)](08-containers.md)** to ensure hardware synchronicity.
- **Reflex Priority Logic:** Mandatory classification of audio intents as high-priority **Reflexes**, capable of preempting background **Rituals** via the **[Orchestrator (21)](21-orchestrator.md)**.
- **Biometric Streaming Transport:** Provision of a real-time, bidirectional streaming protocol (WebSockets) to minimize the latency between perception and response.
- **Agentic Loop Integration:** Mandatory integration of transcribed intent into a reasoning **[Agent (19)](19-agents.md)**, whose textual output is instantly synthesized into resonance.
- **Transport Sovereignty:** Physical restriction of sensitive biometric audio data to secure, peer-to-peer tunnels to prevent voice-pattern leakage to the public internet.
- **Capability Discovery:** Utilization of functional tags (e.g., `stt`, `tts`) to allow the system to remain model-agnostic while ensuring the physical body possesses the required senses.

## Considered Options

!!! failure "Option 1: Frontend-Only Processing (Browser APIs)"
    Utilizing the browser's native Web Speech APIs.
    -   **Cons:** **Privacy and Quality Ceiling.** Browser-based STT often routes data through corporate clouds, violating the **[Iron Pact (00)](00-license.md)**. It fails the requirement for a sovereign, self-contained sensory organism and results in a "robotic" identity.

!!! failure "Option 2: Asynchronous File Processing"
    Treating audio as a standard file attachment (Upload -> Transcribe -> Answer).
    -   **Cons:** **The Walkie-Talkie Latency.** The multi-second delay between speaking and hearing a response destroys the "Flow of Consciousness." It transforms a companion into a high-latency tool.

!!! success "Option 3: The Audio Coven (Streaming Resonance)"
    Deploying specialized audio containers as a dynamically activated operational state, exposed via a real-time WebSocket pipeline.
    -   **Pros:**
        -   **Telepresence:** Collapses the perception-cognition-action loop to sub-second latencies by streaming tokens directly from the reasoning Agent into the TTS engine.
        -   **Hardware Safety:** The Orchestrator ensures VRAM-heavy audio models are only resident when a vocal communion is active.
        -   **Total Sovereignty:** Keeps the entire sensory loop, including biometric data, within the Sepulcher.

## Decision Outcome

**The Echo** is adopted as the Sensory Extension, implemented as the `audio.coven`—a stateful capability for real-time, sovereign voice communication.

### 1. The Audio Coven (The Body)

The Echo manifests as a collection of **[Runes (08)](08-containers.md)** managed as a mutually exclusive operational state. A typical manifestation includes:

- **The Ear (`stt.container`):** A high-performance Speech-to-Text Rune (e.g., Faster-Whisper), tagged with the `stt` capability.
- **The Voice (`tts.container`):** A streaming Text-to-Speech Rune (e.g., Piper), tagged with the `tts` capability.
- **The Mind:** A lower-tier Reasoning Soulstone (e.g., 1B-8B model) that can inhabit VRAM alongside the sensory engines for rapid conversational reflexes.

### 2. The Resonance Pipeline (The Cortex)

The extension registers a dedicated WebSocket endpoint on the **[Vessel (11)](11-backend.md)**, establishing a continuous, bidirectional loop.

1. **Ingest:** Raw audio bytes are streamed from the client via the **[Tether (31)](31-vpn.md)**.
2. **Perceive:** The **Ear Rune** performs real-time transcription, feeding a stream of text into the reasoning **[Agent (19)](19-agents.md)**.
3. **Project:** As the Agent generates tokens, the **[Dispatcher (20)](20-dispatcher.md)** pipes them instantly into the **Voice Rune**.
4. **Respond:** The synthesized audio bytes are streamed back to the Magus, enabling the Lych to begin speaking before it has finished thinking.

### 3. Orchestration of the Reflex (The Will)

In the logic of the **[Orchestrator (21)](21-orchestrator.md)**, an incoming audio stream is a **Reflex of the Highest Order**.

- **The Tipping Point:** Connection attempts to the audio endpoint trigger an immediate intent for the `audio.coven`.
- **Preemption:** If the GPU is occupied by a background Ritual (e.g., training or batch ingestion), the Orchestrator's algorithm will preemptively pause the labor and execute a state swap to manifest the Echo.
- **Result:** This ensures the Daemon remains responsive to the Magus’s voice regardless of the system’s background workload.

### 4. Sensory Dispatching (The Grant)

The Echo utilizes the system's **Capability Discovery** to decouple logic from specific models.

- **Discovery:** The extension registers its Runes with functional tags. The Dispatcher automatically identifies these as the providers for "vocal-perception."
- **Dynamic Arsenal:** The `listen()` and `speak()` tools are injected into the Agent's **`RunContext`** only when the Orchestrator confirms the physical Coven is active.
- **Biometric Security:** To ensure privacy, the Echo pipeline is physically restricted to the **[VPN (31)](31-vpn.md)** interface, air-gapping biometric communion from the public internet.

### Consequences

!!! success "Positive"
    - **Conversational Immersion:** The streaming pipeline collapses the sensory gap, enabling natural, human-like interaction.
    - **Substrate Flexibility:** The Magus can upgrade "Ears" or "Voice" simply by updating a Rune in the Codex without modifying the agentic logic.
    - **Hardware Resonance:** The system maximizes the utility of limited VRAM by only loading the heavy sensory stack when vocal communion is active.

!!! failure "Negative"
    - **VRAM Hunger:** Running STT, TTS, and reasoning models simultaneously can challenge mid-range GPUs, potentially requiring the use of aggressive model quantization.
    - **Network Sensitivity:** Real-time audio is sensitive to jitter; poor connectivity can cause stuttering, requiring robust client-side buffering.
