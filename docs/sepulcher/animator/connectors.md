---
title: Connectors
icon: material/connection
---

# :material-connection: Connectors and Dialects

A **Connector** turns one admitted Animator endpoint into callable runtime surfaces. It speaks a
wire or process dialect; it does not decide what an application means, whether an artifact may
leave, which model is good, whether a long job may be repeated, or when a local service should
rise. Those decisions remain with the capability interface, owning Domain, policy gates, Workers,
Dispatcher, and Orchestrator.

The current implementation is narrower than this designed office. Its
`OpenAICompatibleConnector` hydrates only Pydantic AI Chat Completions or Responses model
surfaces, projects its configured model catalogue, and exposes agent-loop toolsets. That catalogue
is not necessarily a live discovery result. It is an available **OpenAI model
connector**, not a universal implementation of every API beneath an `/v1` root. Audio, Images,
Videos, OCR, Scout, Form, Kinesis, engine jobs, and live sessions have no delivered connector.

## Five boundaries that must not collapse

| Boundary | Owns | Does not own |
| --- | --- | --- |
| **Capability interface** | versioned semantic request and result contract | transport, model choice, deployment, or application judgment |
| **Capability profile** | exact model, tool, graph, workflow, configuration, limits, licenses, and proved operations | endpoint lifecycle or wire behavior |
| **Dialect driver** | request encoding, authentication shape, response decoding, errors, progress, cancellation, and reconciliation for one exact protocol | provider truth beyond that proved subset |
| **Runtime adapter** | Rune hydration, process/container plan, readiness probe, optional in-runtime activation, and control-plane facts | semantic routing or job meaning |
| **Animator** | one addressable local Soulstone or remote Portal bearing those surfaces | Composition records, Graph, policy, or effect authority |

One runtime adapter may expose several dialect drivers. One driver may serve several admitted
profiles. Sharing a URL, SDK, container, or Python base class does not merge their contracts.

## OpenAI compatibility is per dialect

"OpenAI-compatible" without a named surface is not a compatibility claim. The designed dialect
register treats these independently:

| Dialect | Typical office | Compatibility must prove |
| --- | --- | --- |
| `openai.chat-completions@1` | message rounds and tool calls | message parts, model settings, tool schema, streaming events, usage, finish reasons, and errors |
| `openai.responses@1` | Responses-style model rounds | item types, tool lifecycle, state/reference behavior, streaming events, usage, and unsupported fields |
| `openai.audio-batch@1` | finite transcription, translation where supported, and speech synthesis | multipart/audio encodings, language and voice fields, timestamps, output formats, limits, and errors |
| `openai.images@1` | image generation and editing | operation routes, image/reference counts, masks, sizes, formats, progress, result retrieval, and revised prompts |
| `openai.videos-job@1` | asynchronous video generation and editing | submit, durable provider id, status, progress, cancellation request, result retrieval, expiry, and reconciliation |

Endpoint names are only evidence inputs. Each provider profile records exact routes and methods;
supported operations and fields; required and rejected parameters; media encodings and limits;
authentication; whether "streaming" means token deltas, audio frames, progress, previews, or
partial artifacts; error and rate-limit mapping; idempotency support; cancellation semantics;
provider-job lookup; retention and expiry; and the conformance bake that established those facts.
An omitted fact is unsupported, not silently forwarded in an `extra_body` bag.

A service may implement only part of a dialect. That partial profile is legitimate when every
opening and refusal is explicit. It must not inherit a family logo's optional fields, endpoints,
streaming, cancellation, or error semantics. A later server release receives a new profile and
evidence rather than mutating the old claim.

## Native calls, durable jobs, and sessions

Not every useful service resembles OpenAI:

- a **call driver** performs one bounded request and returns one typed result;
- a **job driver** submits an effect, polls or receives progress, requests cancellation, fetches
  results, and reconciles the same provider identity after disconnect or restart;
- a **session driver** opens one bounded, epoch-fenced live exchange with declared clocks, queues,
  drops, reconnect, consumers, and stopping law; and
- an **agent model connector** hydrates a Pydantic AI `Model` and optional agent-loop toolsets.

FFmpeg, Blender, Godot, native parsers, and similar finite local programs are normally delivered by
a Worker into a trusted executor or, for hostile material/code, a Tomb; a Worker task in the Vessel
is not containment. They are not fake network models. A wrapper service may still be an Animator when its
independent lifecycle, queue, resource residency, or remote boundary justifies one; the same typed
job interface remains outside its private transport.

`ToolConnector` and Pydantic AI toolsets remain an agent-loop convenience. They cannot establish a
Scout Search grant, media effect, filesystem right, browser session, Blender job, payment,
publication, or another host authority. An agent-facing tool calls a host-owned typed handler;
raw provider toolsets never become an effect boundary merely because the model can name them.

## Probe truth

Three observations remain separate:

1. **Link liveness:** some endpoint or process answered.
2. **Profile readiness:** the exact declared profile and operation can accept work now.
3. **Dialect conformance:** the pinned implementation passed its offline or live bake.

`GET /models` can establish limited endpoint and inventory evidence. It cannot prove Images,
Audio, Videos, cancellation, a declared model absent from the returned inventory, or every profile
behind that URL. A fixed runtime may project all declared profiles warm only when its adapter can
prove that the exact pinned deployment binds them as one inseparable ready unit. Otherwise each
profile or operation needs its own probe result or remains unavailable.

A probe may downgrade or invalidate a declaration. It may not invent an interface, operation,
profile, dialect, model, language, or permission. Portal probes make no payload egress and grant no
later egress authority.

## Durable job handoff

A live connector handle never enters Graph state. Before any local or remote asynchronous effect is
submitted, the owning Worker persists `ServiceJobAttempt@1` under the complete
[Workers law](../../adr/14-workers.md#service-job-attempts-designed). That owner pins request,
idempotency, the discriminated capability-backed or direct-tool execution binding,
provider/executor identity, artifacts, managed local reservation when needed, progress,
cancellation, usage/cost, results, and reconciliation without making the Connector a second ledger.

Only after that pre-submit record exists may the selected capability driver or direct executor
receive the idempotency identity and persist the returned provider/executor job identity when one
exists. The parent Run may then enter owner-specific durable service wait without retaining a
Connector, grant, socket, response iterator, tensor, process, or provider SDK object. Re-admission
rebinds the exact capability or Resolution Lock/ToolProfile as applicable and reconciles the same
attempt. An unknown remote, paid, or local tool effect is never repeated merely because a client
timed out.

## Egress and secrets

A Portal grant proves only that one eligible runtime route was selected. Before any bytes leave,
Security re-evaluates the exact canonical payload digest, classification, destination, purpose,
consent, transformation receipts, cost, and expiry. A changed crop, prompt, attachment, retry,
fallback, or derived artifact requires a fresh decision. Connector code receives the narrow secret
reference or mounted value required by its exact driver; it cannot enumerate the Codex, borrow a
different provider credential, or return secrets in diagnostics.

[Capabilities](capabilities.md) owns semantic matching and grant variants. [Soulstone
Runes](soulstone/rune.md) declare concrete local instances; [Portals](portal.md) declare remote
ones; [Coven](coven.md) owns compatible local grouping; and [State of
Work](../../state-of-the-work.md#animator-dispatch-spine) keeps the delivered chat/model boundary.
