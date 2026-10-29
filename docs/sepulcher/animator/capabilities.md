---
title: Capabilities
icon: material/lightning-bolt-circle
---

# :material-lightning-bolt-circle: Capabilities

Suppose the work needs a recording transcribed. Choosing a model or endpoint is not yet enough:
the caller needs a contract for the inputs it may send and the typed result it can receive.
A **capability** names that exact, versioned contract at an [Animator](./index.md). Begin with the
operation, then establish which service can perform it. Model, endpoint, container, tool, Rune,
Coven, and application purpose each contribute a different part of that decision.

The interface/profile design described below remains **Designed** until source, migrations, adapters, tests and
operator receipts establish delivery.

## The delivered v1 surface

Current `CapabilitySpec` identifies a capability by `{animator}:{family}:{model_id}`. It uses
seven closed families, coarse input/output modality strings, and one compatibility grant class.
For `chat`, that grant contains a hydrated Pydantic AI model and only explicitly declared
agent-loop toolsets. For `tool_execution`, a non-empty toolset surface is required. The remaining
five labels route metadata but fail closed when a grant is issued.

This proves the narrow chat/model path, toolset compatibility, and readiness mechanics. It does
not yet give the transcription example an executable v1 route, nor establish visual, embedding,
rerank, service-job, or host-tool execution. [State of Work](../../state-of-the-work.md#animator-dispatch-spine)
records the delivered boundary.

A capability carries the `registrant_id` assigned to its runtime or Portal definition during
extension assembly. The same identity accompanies its granted specification and Nexus response
row. It identifies the contributing package, separately from the Provider and capability key; it
grants no authority. Direct adapter injection without registration reports `None` rather than
claiming Core ownership.

## Interface, profile, and operation

For the designed interface/profile path, distinguish the contract you need from the exact
implementation that can fulfill it and the act you are requesting now:

| Record | Question it answers | Example |
| --- | --- | --- |
| `CapabilityInterfaceRef` | Which versioned request-and-return contract is requested? | `model.chat@1`, `echo.transcribe@1`, `prism.image@2`, `prism.scanner@1`, `scout.search@1` |
| `CapabilityProfileRef` | Which exact implementation closure can perform it? | one model and weights, Comfy graph, native parser, engine toolchain, language set, limits, and licenses at an immutable revision/digest |
| **operation** | Which admitted act within that interface is requested now? | `generate`, `edit`, `transcribe`, `segment`, `retarget`, `search`, `validate` |

For the transcription example, the interface tells the caller which request and result schemas,
operations, facets, failures, and recovery meanings apply. Its owner validates those domain
requirements. A profile identifies an exact implementation that can meet them by pinning code,
model, weights, runtime, workflow or graph, configuration, dependencies, licenses, language and
format support, resource evidence, and proved limits. Finally, an operator Rune chooses a
concrete deployable instance and references those admitted definitions. A contract, a tested
implementation, and a running instance answer different questions.

Image input may enrich `model.chat@1`; it does not become precise Sight. Audio output from a chat
model does not become an eligible speech synthesizer. A Comfy graph that can produce an image and
a video exposes two proved interfaces or operations only when each contract closes. `tool` is not
an interface that means every side effect.

## Capability demand

`CapabilityDemand@1` asks for:

- exact interface and operation;
- typed input and output contract references, required facets, formats, language, and limits;
- required feature facts such as tools, token streaming, audio-frame streaming, progress,
  cancellation, timestamps, seeds, masks, or live clocks—never one ambiguous
  `supports_streaming` bit;
- optional exact or eligible profile revisions;
- invocation mode: `model_round`, `call`, `durable_job`, or `live_session`;
- source classification, local-only or eligible Portal policy, purpose, consent, and cost ceiling;
  and
- run, station-attempt, deadline, priority, and reservation requirements.

The interface owner validates domain constraints before demand and after return. Core matches
the resulting exact declared and admitted facts. For example, accepting a motion format cannot
establish that its skeleton satisfies the requested retarget map; that compatibility must already
be expressed in the domain contract.

## Declaration, evidence, observation, and grant

Four records keep assertion, proof, readiness, and permission distinct:

| Record | Office |
| --- | --- |
| `CapabilitySpecV2` | Immutable Animator declaration of interface, profile, operations, I/O contracts, invocation mode, driver/dialect, provenance, evidence, resource, and lifecycle intent. |
| `CapabilityEvidenceRef` | Exact producer-attributed conformance evidence supporting that profile's claims; the target contract owner separately admits or promotes it. |
| `CapabilityState` | Latest observation for the exact Animator/interface/profile binding and, where necessary, its operations. |
| discriminated capability grant | Temporary WARM binding to one operation and one callable surface under an exact lease. |

Declaring a route in a Rune makes it a candidate for selection; evidence establishes what its
exact implementation can do. That evidence closes over code, weights, workflow, dependencies,
dialect, licenses, language or format corpus, hardware profile, and measured limits.

The target interface/profile owner admits or promotes the evidence under its policy. Drift can
produce findings and Assimilation can repair foreign craft, but neither thereby acquires that
owner's decision. Dispatcher consumes the admission when matching a request; it does not become
a benchmark judge.

A grant exposes neither its Animator nor its Connector. The designed union separates four
callable surfaces:

| Grant | Live surface | Typical use |
| --- | --- | --- |
| `ModelGrant` | Pydantic AI model and admitted agent-loop toolsets | chat or reasoning round |
| `CallGrant` | typed call driver | bounded STT/TTS, OCR, deterministic service, search, or another immediate call |
| `JobGrant` | typed submit, status, cancellation, result, and reconciliation driver | image, video, Form, Kinesis, Comfy, engine, or paid asynchronous work |
| `SessionGrant` | typed bounded live-session driver | later audio, vision, motion, game, or device sessions |

Once granted, the caller receives only the operation surface it needs. A `ModelGrant` cannot
be treated as a job driver, a `JobGrant` contains no arbitrary HTTP client, and a `SessionGrant`
confers no source-device or world effect beyond its interface. This keeps the technical ability
to call a service within the admitted act. Live models, connectors, SDK clients, iterators,
sockets, sessions, and grants never enter Graph checkpoints or delegated payloads.

## Readiness is not compatibility

The six observed phases remain:

| Phase | Meaning |
| --- | --- |
| `COLD` | managed unit down or endpoint unreachable |
| `ACTIVATABLE` | dynamic runtime up; exact profile not loaded |
| `WARMING` | activation or readiness convergence in flight |
| `WARM` | exact admitted binding currently accepts its proved operation set |
| `ERROR` | probe or runtime reported a terminal fault |
| `UNKNOWN` | no conclusive fresh observation exists |

`is_dynamic` remains a deployment trait: a reachable runtime may still need profile activation.
It is not a readiness, quality, or capacity claim.

Liveness of one URL, process, `/health`, or `/models` route does not prove every declared model,
dialect, operation, language, or profile warm. A fixed single-profile runtime may share one
readiness observation only when the pinned adapter proves those surfaces are inseparable. A probe
may downgrade or invalidate a declaration; it cannot invent one. Conformance evidence survives a
temporary cold state, while a warm observation never substitutes for conformance.

## Dispatch and lease

The Dispatcher resolves one `CapabilityDemand@1` deterministically against eligible admitted
specifications and fresh state. Before grant it applies source, Sigil, local/Portal, egress,
purpose, consent, cost, and reservation policy owned by their proper boundaries. Selection is not
quality ranking unless a separately admitted policy supplies comparable evidence.

| Observation | Result |
| --- | --- |
| eligible `WARM`, admission open | issue the exact discriminated grant and register its lease |
| managed `COLD`, `ACTIVATABLE`, or `WARMING` | return a handle-free hardware transition request |
| the same phases on a shared or unmanaged service | settle unavailable |
| `ERROR` | settle unavailable with the observed reason |
| unresolved `UNKNOWN` | probe once under deadline, then settle unavailable |

Dispatcher never starts, stops, loads, evicts, submits an effect, or waits on a provider job.
[Orchestrator](../../adr/23-orchestrator.md) owns readiness convergence. The interface owner or
Worker invokes the granted surface. A waiting Graph holds no live grant. Runtime models and
toolsets are bound only while issuing an admitted grant. Capability, specification, and state
reads expose detached declarations and observations. The registry keeps runtime handles private;
callers obtain model and toolset bindings only through the scoped grant path. Control-plane
activation and readiness operations do not expose a second public binding route.

### One process generation

One loaded `AnimatorRegistry` is one sealed process generation. Successful loading is one-shot;
changing declarations, runtime adapters, or exact Portal definitions requires constructing a new
application generation rather than mutating the live registry underneath admitted Runs. A failed
staged first load publishes nothing and remains retryable; it does not leave a partly sealed
catalogue.

### Calls, durable jobs, and live sessions

A short call keeps a process-local lease for its duration. An asynchronous effect can outlive
that process, so it needs a different return path: persist `ServiceJobAttempt@1` before the first
submit, allowing timeout or death to reconcile the same request instead of repeating it.

If the work uses managed resident or scarce local resources, the attempt also receives an exact
Orchestrator-visible reservation and fence. Live work needs a bounded session record. Current
process-local leases cannot supply these guarantees, which is why durable service work remains
Designed.

There is no universal `SessionAttempt` yet. Echo Resonance, Riffmaw Jam, LiveSight,
LiveKinesis, and Foundry Playtest each own their chronology, clocks, epochs, participants,
queues, stopping, reconciliation, and evidence. Core's future `SessionGrant` supplies only exact
technical admission, lease/reservation, and late-output fencing requirements. A common mechanical
session envelope may be accepted only after those owners expose genuinely shared invariants; until
then their records remain distinct and Designed.

## Stable identity

The designed v2 key is:

```text
{animator}:{interface_id}:{profile_ref}
```

`profile_ref` is a safe stable id plus exact immutable revision or content digest; an unversioned
mutable label is not a profile reference. The selected operation is pinned in the demand and grant
rather than multiplied into endpoint identity. Mutable provider handles, deployment paths, and
floating tags are not keys.

Identity components are ASCII lowercase slugs with digits, dots, underscores, and hyphens; colon,
whitespace, path separators, controls, and empty components are forbidden. An interface ends in an
integer `@revision`. A profile reference is `profile-id@revision` or
`profile-id@sha256-<lowercase-hex>`; the referenced record still carries the full digest. Parsing is
structural, never a split of an unrestricted provider string.

Existing v1 keys remain legible only through an explicit compatibility projection from exact
family/model pairs to exact interfaces and profiles. A migration never silently reinterprets a
persisted key, and no unknown family is converted to a generic service.

## Runes, Runes in groups, and placement

A Soulstone or Portal Rune will declare first-class `[[capabilities]]` entries referencing exact
interface, profile, driver, dialect, evidence, resource, and containment definitions. Current
`[[models]]` blocks remain compatibility sugar for the proved model interfaces; non-model services
never invent a model id or LLM generation overlay merely to load.

One Rune may belong to several [Covens](coven.md). A Coven names compatible local services that may
rise together; it does not choose semantic capability, reserve resources, schedule a job, pool
VRAM, or authorize a Portal. Current conflict domains remain the conservative executable law.

To decide whether several capabilities fit together, the later `ResourceEnvelopeRef` would retain
measured idle, active, and transition-peak GPU memory, host RAM, disk, devices and topology,
bandwidth, warm-up and unload time, concurrency, and measurement conditions. A `PlacementProfile`
would relate these exact envelopes and required headroom on one host or a Legion topology.

A future `CapabilitySetRequest@1` could then ask Orchestrator to converge several exact bindings
in one serialized desired-world transaction. Serialization cannot make physical effects atomic.
Drain, attestation, compensation, restoration, and containment still govern partial change; a
Coven becomes neither another scheduler nor a promise of unproved hardware rollback.

## Composition boundary

A capability supplies an exact technical interface; a Spell defines the semantic action at a
Pattern station. The [consuming Composition](../../compositions/index.md) retains application records,
judgment, policy, and effects. Domain jobs and results may share grants, attempt recovery, and
artifact custody without collapsing into a generic `MediaJob`, `tool_execution`, or universal
OpenAI adapter.

[Connectors](connectors.md) owns invocation dialects and the current chat-only implementation
boundary. [Dispatcher (22)](../../adr/22-dispatcher.md) owns matching and leases;
[Orchestrator (23)](../../adr/23-orchestrator.md) owns physical readiness; and [Workers
(14)](../../adr/14-workers.md) owns durable attempt settlement.
