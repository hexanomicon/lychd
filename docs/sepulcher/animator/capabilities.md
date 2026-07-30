---
title: Capabilities
icon: material/lightning-bolt-circle
---

# :material-lightning-bolt-circle: Capabilities

Every [Animator](./index.md) declares what it can do as one or more **capabilities**. A capability
is the typed thing a caller requests; the Animator is the endpoint that may serve it. Its stable
identity is:

```text
{animator}:{family}:{model_id}
```

That key passes between registry, Dispatcher, Orchestrator, Graph, and events. Mutable runtime
handles do not cross a pause.

## Identity: Family and Modalities

Two axes describe a capability:

- **family** names the kind of service: `chat`, `vision`, `embedding`, `stt`, `tts`,
  `tool_execution`, or `rerank`;
- **modalities** name admitted and emitted content: `text`, `image`, or `audio`.

There is deliberately **no audio family**. Speech uses the `stt` and `tts` families. A chat model
that hears remains `chat` with `audio` input; one that sees remains `chat` with `image` input. The
dedicated `vision` family—the Eye—must be declared explicitly.

Resolution requires an exact family. An optional model must match exactly; every requested input
modality must be present; and tools require `supports_tools = true`. Unknown support is not
permission.

## Dynamic Is Not Ready

`is_dynamic` is a fixed property of how a capability becomes ready:

- `is_dynamic=False`: a reachable endpoint is warm because the server binds after its pinned model
  loads. Portals and single-model local servers use this shape.
- `is_dynamic=True`: the runtime can be reachable while this model still needs in-process
  activation. llama.cpp router mode and ExLlamaV3 through TabbyAPI use this shape.

The live **phase** answers a different question:

| Phase | Meaning |
| :--- | :--- |
| `COLD` | Unit down or endpoint unreachable. |
| `ACTIVATABLE` | Dynamic runtime up; this model is not loaded. |
| `WARMING` | Activation or readiness convergence is in flight. |
| `WARM` | Requests are accepted now. |
| `ERROR` | Probe or runtime reported a terminal fault. |
| `UNKNOWN` | No conclusive observation exists. |

`is_active` covers `WARM` and `WARMING`. `runtime_started` also includes `ACTIVATABLE`, which
matters when the host transition boundary revalidates stale state.

The [Nexus](../../divination/altar/nexus.md) projects `WARM` as **active**, `WARMING` as
**warming**, dynamic `ACTIVATABLE` as **awaited**, `COLD` or fixed `ACTIVATABLE` as **cold**, and
`ERROR` as **fault**.

## What Dispatch Does Next

After refreshing the selected record:

| Observation | Result |
| :--- | :--- |
| `WARM`, admission open | Issue a grant and register its lease. |
| `COLD`, `ACTIVATABLE`, or `WARMING`, lifecycle managed | Request a hardware transition; hold no lease while waiting. |
| The same phases, lifecycle shared | Settle unavailable. |
| `ERROR` | Settle unavailable with the observed reason. |
| unresolved `UNKNOWN` | Probe again, then settle unavailable. |

The Dispatcher never starts, stops, loads, or evicts an Animator. It raises a handle-free
transition request; the Orchestrator re-fetches canonical state and owns convergence.

One absolute `warmup_timeout_s` deadline bounds readiness. `estimated_ready_ms` may delay the first
probe, but that delay and every later polling sleep are capped to the remaining budget. An
estimate never creates a second timeout.

## Declaration, Observation, and Proof

Soulstone `[[models]]` blocks and Portal model declarations synthesize immutable capability
specifications. Declaration controls routing. For local runtimes, an adapter probe may enrich an
open runtime fact or downgrade readiness; it may not invent an undeclared model or family. A Portal
with no model declarations yields no capability.

Observation proves only the latest readiness fact. A `WARM` grant proves that admission and
binding succeeded at that moment; it does not prove quality, privacy, cost, or long-term
reachability. Those policies must enter before grant through their owning contracts.

[Dispatcher (22)](../../adr/22-dispatcher.md) owns matching and leases;
[Orchestrator (23)](../../adr/23-orchestrator.md) owns transition and containment; and
[State of Work](../../state-of-the-work.md#animator-dispatch-spine) records the delivered spine.
