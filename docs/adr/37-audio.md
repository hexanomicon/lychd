---
title: 37. Audio
icon: material/headphones
---

# :material-headphones: 37. The Audio Echo

!!! abstract "Context and Problem Statement"
    A text-only Daemon cannot participate in spoken interaction. Speech-to-Text (STT),
    Text-to-Speech (TTS), and audio-capable chat introduce artifact custody, privacy, latency,
    interruption, and hardware concerns that plain text does not. A record-and-send exchange is a
    valid baseline; streaming is an optional latency profile whose additional session semantics
    must be explicit.

## Requirements

- **Independent Manifestation:** STT, TTS, audio-capable chat, VAD, codec, and reasoning providers
  remain independently selectable. A Coven may group compatible local services but is not the
  unit of semantic dispatch.
- **Policy-Owned Priority:** Incoming audio has no intrinsic preemption authority. The admitting
  Pattern and operator policy declare priority; the **[Orchestrator (23)](23-orchestrator.md)**
  applies physical readiness law.
- **The Stasis Trigger:** Integration with the **[Dispatcher (22)](22-dispatcher.md)**. If an Agent proactively invokes an audio tool (e.g., `speak_text`) while the hardware is "Cold," it must raise the `HardwareTransitionRequired` signal to freeze the graph via the **[Stasis Protocol (22)](22-dispatcher.md)**.
- **Artifact Custody:** Captured and synthesized audio bytes remain immutable Reliquary artifacts;
  graph checkpoints and run rows carry references and timeline state, not media blobs.
- **Profiled Transport:** Record-and-send is the minimum profile. Half-duplex response streaming
  and later full-duplex conversation require a bounded Resonance Session, speech timeline,
  interruption law, and delivery receipts; WebSocket is one transport option.
- **Portal/Soulstone Duality:** Local and remote providers share semantic family contracts, while
  Ward policy, classification, consent, economics, and readiness remain provider-specific.

## Considered Options

!!! failure "Option 1: Frontend-Only Processing (Browser APIs)"
    Utilizing the browser's native Web Speech APIs.

    - **Cons:** **Privacy Ceiling.** Browser-based STT often routes data through corporate clouds, violating the **[Iron Pact (00)](00-license.md)**.

!!! success "Option 2: Record and Send"
    Treating a bounded utterance as an immutable artifact, then returning text or synthesized audio.

    - **Pros:** Small transport surface, explicit capture boundary, simple retries, and a viable
      first Android/Web client.
    - **Cons:** Turn-taking is less fluid than a mature streaming session.

!!! success "Option 3: Profiled Resonance"
    Extending the baseline with independent speech providers and optional half/full-duplex
    transports managed through the ordinary Dispatcher, Stasis, and Orchestrator laws.

    - **Pros:**
        - **Telepresence:** Collapses the perception-cognition-action loop to sub-second latencies.
        - **Hardware Safety:** The Orchestrator readies only the selected managed providers and
          declared dependencies.
        - **Delivery Honesty:** Artifact receipts and timeline state distinguish generated,
          delivered, played, interrupted, and expired audio.

## Decision Outcome

**The Echo** is adopted as the temporal speech-lifecycle Extension Domain. Dedicated providers use
`stt` and `tts` families; `audio` remains an input/output modality, not a capability family. Echo
does not require an atomic Audio Coven or one mandatory transport.

!!! warning "Current audio floor is schema and admission, not a stream"
    The implemented core can declare and filter `audio` modality metadata on capabilities and can
    carry an immutable audio `ArtifactRef` in an `Intent`. It does not yet materialize artifact
    bytes into Pydantic AI input, propagate them through the Bridge graph, expose an audio
    transport, persist a speech timeline, or register working STT/TTS adapters. No concrete Echo
    package exists. Sections below specify the Domain that may consume the current schema seam;
    they are not an available voice interface.

!!! note "The Two-Axis Law: No Audio Family"
    A **family** names a routable service kind; **modalities** name what a capability admits. There
    is **no `audio` family**. A chat model that hears is not a distinct family member: it is a
    **[Dispatcher (22)](22-dispatcher.md)** `chat` capability carrying
    `audio ∈ modalities_in`, satisfying spoken input in place. The dedicated audio families remain
    `stt` (the Ear) and `tts` (the Voice)—routable service kinds for transcription and synthesis
    that can be selected independently.

### 1. Planned Resonance Manifestations

Echo may manifest through independently registered capabilities. Local providers may be rendered
as **[Quadlet services (08)](08-containers.md)**:

- **The Ear (`stt.container`):** A high-performance Speech-to-Text service (e.g., Faster-Whisper).
- **The Voice (`tts.container`):** A streaming Text-to-Speech service (e.g., Piper).
- **Audio-capable chat:** A `chat` provider declaring `audio` input or output.
- **The Listener:** Client/server VAD, codec, and capture controls.
- **The Mind:** The ordinary selected reasoning provider; Echo requires no special voice mind.

### 2. The Planned Resonance Pipeline

The minimum profile establishes a bounded, recoverable exchange:

- **Capture and admit:** A client records one bounded utterance and places it under immutable
  artifact custody with digest, media type, duration, classification, and retention.
- **Perceive and think:** One eligible Ear or audio-capable chat provider produces attributed input
  for an ordinary Agent step.
- **Respond:** Text may be returned directly or granted to one Voice provider.
- **Deliver:** A Resonance Session records generated, delivered, played, interrupted, expired, and
  retryable states. Media bytes remain artifact references.
- **Stream later:** Half-duplex output streaming may reduce time-to-first-audio. Full duplex adds
  VAD, barge-in, echo cancellation, and explicit turn/interruption semantics.

### 3. Orchestration Without Privilege Inflation

User-initiated and Agent-initiated speech use the same law:

1. The Pattern admits a bounded speech operation with authority, priority, modality, and
   classification.
2. The **[Dispatcher (22)](22-dispatcher.md)** selects the exact `stt`, `tts`, or `chat`
   capability.
3. If a selected managed provider is non-`WARM`, the ordinary Stasis handshake asks the
   Orchestrator to converge it. Echo cannot preempt work or revoke leases.
4. A grant is scoped to one step or Resonance Session. It does not imply continued microphone
   access.

### 4. Sensory Dispatching (Portals & Soulstones)

The Echo utilizes the **[Dispatcher (22)](22-dispatcher.md)** to resolve capabilities:

- **Soulstones:** Local services may reduce egress but still require explicit artifact and capture
  policy.
- **Portals:** Remote services require classification eligibility, Ward egress policy, consent
  where required, and an economic budget.
- **Abstraction:** Semantic request/response contracts are stable; privacy, latency, readiness,
  cost, and support claims remain provider-specific.

## Consequences

!!! success "Positive"
    - **Progressive Immersion:** The record-and-send floor can grow into streaming without
      replacing the semantic contract.
    - **Delivery Evidence:** Session receipts state what was generated and delivered without
      promising that a human heard it.
    - **Truthful Readiness:** The Stasis Protocol represents a non-ready managed provider without
      pretending that the speech operation already completed.

!!! failure "Negative"
    - **VRAM Hunger:** Some combinations of STT, TTS, and reasoning providers can challenge
      mid-range GPUs.
    - **Storage Pressure:** Retained audio artifacts require explicit expiry and quota policy.
    - **Session Complexity:** Full-duplex speech adds interruption and timing races absent from
      record-and-send.
