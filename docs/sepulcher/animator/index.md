---
title: Animator
icon: fontawesome/solid/heart-pulse
---

# :fontawesome-solid-heart-pulse: Animator

> _“Cold iron offers no capability. An Animator is the address at which power answers.”_

An **Animator** is an addressable capability-serving endpoint that LychD can discover, probe, bind
through a typed adapter, and route by declared capability.

Inference is the most important Animator family today, but it is not the whole category and not limited to next-token text generation. A model server, energy-based scorer, world-model service, proof engine, speech engine, browser worker, tracing pool, metrics backend, remote API, or peer node can all be Animators when they expose a typed capability surface to the daemon.

An Animator is a **live, addressable service**, not an abstract concept. Every Animator is one of two placement forms:

- **[Soulstone](./soulstone.md)**: A local Quadlet/systemd-backed service running on the Magus's own iron (vLLM, llama.cpp, SGLang, Whisper, Playwright, Phoenix, or other local service engines).
- **[Portal](./portal.md)**: A live connection to a remote service or API (OpenAI, Anthropic, hosted tools, remote telemetry, peer LychD nodes, or other network providers).

Both satisfy the same **Animator Binding Contract**, exposing callable capability surfaces through connectors/adapters to the **[Dispatcher](../../adr/22-dispatcher.md)**, **[Orchestrator](../../adr/23-orchestrator.md)**, Graph, or extension that needs them. Whether the service lives on local iron or across the network, it obeys the same laws of identity, provenance, readiness, and capability.

## The Holy Contract

The Vessel does not care _where_ a capability comes from. It cares that the service can be found, checked, activated, and bound through a typed adapter. To enforce this, the Animator defines a strict **Contract of Existence**. Any entity that wishes to act through the Lich must possess a set of **Capabilities**.

!!! abstract "The Universal Tongue"
    The Lich speaks to services through **typed capability contracts**.

    The Animator standardizes all sources of power into a single typed runtime contract. In the current core, many cognitive connectors expose an **OpenAI-compatible surface** through Pydantic AI, while the same adapter pattern can bind non-cognitive services such as browsers, telemetry stores, dashboards, or peer nodes. OpenAI-compatible chat is a practical adapter surface, not the ontology of intelligence in LychD. This creates a powerful abstraction:

    - **Capability-Based Routing:** The Magus requests an intent (reasoning, vision, tools, metrics, browsing, trace search, peer delegation) and the system resolves a suitable Animator from the active substrate.
    - **Hot-Swappable Services:** A local service can be banished and a remote Portal summoned without changing the calling Agent or Graph logic.
    - **Adapter-Normalized Behavior:** Each Animator keeps its native protocol behind a connector while exposing the stable capability surface LychD can reason about.

## The Sources of Power

The Animator draws its energy from two distinct types of sources, inscribed in the **[Codex](../codex.md)**.

### :material-hexagon-slice-6: [Soulstones](./soulstone.md)

#### "The Trapped Spirit."

- **Nature:** Local, Containerized, Stateful. These are the engines running within the Sepulcher itself. A Soulstone is a runtime Animator backed by a **Soulstone Rune** in the Codex; the binding pipeline transmutes that Rune into physical Quadlet manifests and services (see **[Containers (08)](../../adr/08-containers.md)**). They belong to **Covens** when their lifecycle or resource profile requires coordinated state, and they are subject to the **[Orchestrator's](../../adr/23-orchestrator.md)** law of lifecycle ownership.

### :material-weather-hurricane: [Portals](./portal.md)

#### "The Rift to the Remote Sky."

- **Nature:** Remote, Ephemeral, Rented or Federated. These are connections to external services. They generate no Quadlet manifests and consume no local VRAM. They represent burst capacity, frontier reasoning, hosted tooling, remote telemetry, or peer labor, gated by the **[Sovereignty Wall](../../adr/09-security.md)** and resolved through Dispatcher policy.

## The Generation Profile

Model-backed Animators may possess a default generation profile defined in their schema. These parameters govern the stochastic nature of the "Word" when the Animator exposes cognitive capabilities. Non-model Animators ignore these fields unless their adapter explicitly maps them to a meaningful local protocol.

| Parameter | Core default | Description |
| :--- | :--- | :--- |
| `max_context` | unset | Declared context ceiling available to dispatch and context policy. |
| `max_tokens` | unset | Output-token ceiling passed to a supporting model adapter. |
| `temperature` | unset | Sampling temperature passed only when the Rune sets it. |
| `top_p` | unset | Nucleus-sampling threshold passed only when the Rune sets it. |

Unset fields remain provider-owned defaults; Core does not invent sampling values.

## Capabilities

Every Animator declares which **Capabilities** it can provide. A `Capability` is a typed runtime
contract surfaced through the Animator registry and the wider Extension Protocol. The
**[Dispatcher](../../adr/22-dispatcher.md)** queries active capabilities to resolve which Animator
satisfies an Agent's, Graph's, or extension's request.

Each capability carries an **`is_dynamic` flag** (a fixed property of the runtime) and projects a live **phase** (its current readiness), defined canonically in the **[Dispatcher (22)](../../adr/22-dispatcher.md)**:

- **`is_dynamic`**: `False` (ready as soon as the container's endpoint is reachable) or `True` (the container is up but the model needs an in-runtime activation step, e.g. a router `/models/load`).
- **`CapabilityPhase`**: the live readiness ladder — `COLD`, `ACTIVATABLE`, `WARMING`, `WARM`, `ERROR`, `UNKNOWN`.

The active core family registry currently includes cognitive and tool-oriented families:

| Capability Tag | Description | Example Providers |
| :--- | :--- | :--- |
| `chat` | Model conversation; image-capable chat remains `chat` with `image` in `modalities_in` | llama.cpp, vLLM, SGLang, OpenAI, Anthropic |
| `vision` | Dedicated vision analysis rather than conversational multimodal generation | OCR, detection, segmentation, and specialist vision services |
| `embedding` | Dense vector embeddings (`/v1/embeddings`) | llama.cpp, vLLM, OpenAI embeddings |
| `stt` | Speech-to-text: audio to transcript | Whisper (local), OpenAI Whisper API |
| `tts` | Text-to-speech: text to audio | Bark, Coqui, OpenAI TTS API |
| `tool_execution` | Sandboxed code or tool execution | `nono`-wrapped execution surfaces |
| `rerank` | Ranking or reranking of retrieved candidates | reranker models, hosted ranking APIs |

This registry is not a philosophical ceiling. Watcher families such as `metrics_query`, `trace_search`, `dashboard_render`, and network families such as `a2a_delegate` can become first-class when the schema and adapter layer know how to bind, probe, and route them. Future cognitive families may also include constraint scoring, state optimization, latent rollout, proof search, formal verification, or other energy/world-model-like services. Those capabilities may make individual graph nodes far stronger, but they still enter through the same Animator binding law instead of absorbing the daemon's persistence, authority, identity, and hardware boundaries. Not all Animators offer all capabilities. A single llama.cpp Soulstone in router mode can expose different capabilities depending on which model is currently loaded; a capability with `is_dynamic=True` moves along the phase ladder (`ACTIVATABLE` → `WARMING` → `WARM`) as models hot-swap, without restarting the container. The Orchestrator manages these transitions.

## The Galvanic Arc

The Animator is the circuit that governs the cycle of Request and Response for service-backed capabilities.

1. **Demand:** a Graph node or extension asks the
   [Dispatcher](../../adr/22-dispatcher.md) for a typed capability.
2. **Resolution:** the Dispatcher evaluates policy against registered declarations and live phase.
3. **Transition:** when a selected local capability needs a physical state change, the
   [Orchestrator](../../adr/23-orchestrator.md) alone may drive it.
4. **Grant:** once the capability is warm, the registry issues the bound runtime surface and its
   lease.
5. **Use and return:** the caller consumes that grant; outputs return through the caller's own
   typed contract and evidence path.

## Runtime Blueprint

For credential flow and runtime-specific configuration, see **[Portal](./portal.md)** and **[Soulstone](./soulstone.md)**.
