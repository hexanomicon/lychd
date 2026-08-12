---
title: Capabilities
icon: material/lightning-bolt-circle
---

# :material-lightning-bolt-circle: Capabilities

A **capability** is the exact versioned service contract a caller may request from an
[Animator](./index.md). It says what operation and typed material may cross a grant; it is not a
model name, endpoint, container, tool, Rune, Coven, or application purpose.

The currently delivered spine is narrower: `CapabilitySpec` uses the key
`{animator}:{family}:{model_id}`, seven closed families, coarse input/output modality strings, and
one compatibility grant class. `chat` grants carry a hydrated Pydantic AI model and only explicitly
declared agent-loop toolsets; `tool_execution` grants require a non-empty toolset surface. The other
five family labels remain routing metadata and fail closed at issue. That v1 shape supports the
proved chat/model path, narrow toolset compatibility, and readiness mechanics. It does not prove
executable audio, visual, embedding, rerank, service-job, or host-tool routes. [State of
Work](../../state-of-the-work.md#animator-dispatch-spine) owns that boundary.

The accepted general service design below is **Designed** until source, migrations, adapters,
tests, and operator receipts promote it.

## Interface, profile, and operation

Three identities prevent a model catalogue from becoming an unsafe universal router:

| Record | Question it answers | Example |
| --- | --- | --- |
| `CapabilityInterfaceRef` | Which versioned semantic ABI is requested? | `model.chat@1`, `echo.transcribe@1`, `prism.image@1`, `prism.scanner@1`, `scout.search@1` |
| `CapabilityProfileRef` | Which exact implementation closure can perform it? | one model and weights, Comfy graph, native parser, engine toolchain, language set, limits, and licenses at an immutable revision/digest |
| **operation** | Which admitted act within that interface is requested now? | `generate`, `edit`, `transcribe`, `segment`, `retarget`, `search`, `validate` |

The interface owner defines request and result schemas, operations, typed facets, failure and
recovery meaning, and domain-specific validation. A profile pins exact code, model, weights,
runtime, workflow or graph, configuration, dependencies, licenses, language and format support,
resource evidence, and proved limits. The operator Rune chooses a concrete deployable instance and
references those admitted definitions.

Image input may enrich `model.chat@1`; it does not become precise Sight. Audio output from a chat
model does not become an eligible speech synthesizer. A Comfy graph that can produce an image and
a video exposes two proved interfaces or operations only when each contract closes. `tool` is not
an interface that means every side effect.

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

Core matches exact declared and admitted facts. It does not interpret an OCR ontology, choose a
creative image model, judge Slovak speech quality, decide a retarget map, or infer that a wider
format can satisfy a narrower domain contract. The interface owner validates those constraints
before demand and after return.

## Declaration, evidence, observation, and grant

Four records keep assertion, proof, readiness, and permission distinct:

| Record | Office |
| --- | --- |
| `CapabilitySpecV2` | Immutable Animator declaration of interface, profile, operations, I/O contracts, invocation mode, driver/dialect, provenance, evidence, resource, and lifecycle intent. |
| `CapabilityEvidenceRef` | Exact producer-attributed conformance evidence supporting that profile's claims; the target contract owner separately admits or promotes it. |
| `CapabilityState` | Latest observation for the exact Animator/interface/profile binding and, where necessary, its operations. |
| discriminated capability grant | Temporary WARM binding to one operation and one callable surface under an exact lease. |

A Rune declaration is routing intent, not quality proof. Admitted evidence closes exact code,
weights, workflow, dependencies, dialect, licenses, language or format corpus, hardware profile,
and measured limits. Riddle may produce findings but cannot promote; Assimilation may repair
foreign craft but does not own every capability. The target interface/profile owner admits or
promotes evidence under its policy. Dispatcher consumes that decision without becoming a benchmark
judge.

The source implementation currently exposes only the narrow compatibility grant described above;
it never exposes its Animator or Connector. The designed grant union is:

| Grant | Live surface | Typical use |
| --- | --- | --- |
| `ModelGrant` | Pydantic AI model and admitted agent-loop toolsets | chat or reasoning round |
| `CallGrant` | typed call driver | bounded STT/TTS, OCR, deterministic service, search, or another immediate call |
| `JobGrant` | typed submit, status, cancellation, result, and reconciliation driver | image, video, Form, Kinesis, Comfy, engine, or paid asynchronous work |
| `SessionGrant` | typed bounded live-session driver | later audio, vision, motion, game, or device sessions |

The grant contains only its exact operation surface. A `ModelGrant` cannot be cast to a job driver;
a `JobGrant` supplies no arbitrary HTTP client; a `SessionGrant` grants no source-device or world
effect not present in its interface. Live models, connectors, SDK clients, iterators, sockets,
sessions, and grants never enter Graph checkpoints or delegated payloads.

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
Worker invokes the granted surface. A waiting Graph holds no live grant.

Immediate calls retain a scoped process-local lease only during use. Every asynchronous effect,
local or remote, must persist `ServiceJobAttempt@1` before first submit so timeout or process death
can reconcile the same request rather than repeat it. Work on managed resident or scarce local
substrate additionally transfers an exact Orchestrator-visible reservation and fence to that
attempt; live work uses a bounded session
record. Current process-local leases cannot provide those guarantees, so durable service work
remains Designed.

There is no universal `SessionAttempt` yet. Echo Resonance, Riffmaw Jam, LiveSight,
LiveKinesis, and Foundry Playtest each own their chronology, clocks, epochs, participants,
queues, stopping, reconciliation, and evidence. Core's future `SessionGrant` supplies only exact
technical admission, lease/reservation, and late-output fencing requirements. A common mechanical
session envelope may be accepted only after those owners expose genuinely shared invariants; until
then their records remain distinct and Designed.

## Runes, Runes in groups, and placement

A Soulstone or Portal Rune will declare first-class `[[capabilities]]` entries referencing exact
interface, profile, driver, dialect, evidence, resource, and containment definitions. Current
`[[models]]` blocks remain compatibility sugar for the proved model interfaces; non-model services
never invent a model id or LLM generation overlay merely to load.

One Rune may belong to several [Covens](coven.md). A Coven names compatible local services that may
rise together; it does not choose semantic capability, reserve resources, schedule a job, pool
VRAM, or authorize a Portal. Current conflict domains remain the conservative executable law.

The later `ResourceEnvelopeRef` records measured idle, active and transition-peak GPU memory, host
RAM, disk, devices and topology, bandwidth, warm-up and unload time, concurrency, and measurement
conditions. A `PlacementProfile` relates exact envelopes and required headroom under one host or
Legion topology. A future `CapabilitySetRequest@1` may ask Orchestrator to converge several exact
bindings through one serialized desired-world transaction. Physical effects are not atomic: the
request uses those profiles and existing drain, attest, compensation, restoration, and containment
law rather than turning a Coven into a second scheduler or promising rollback that hardware cannot
prove.

## Composition boundary

A capability answers "which exact technical interface can be invoked now?" A Spell answers "which
semantic action belongs at this Pattern station?" A Composition answers "which reusable records,
policy, judgment, effects, and outcomes own the work?" A Product answers "which profession or
market receives that capability, through which supported use cases and operator promise?" Sharing
a capability or packaging a Product never merges those offices.

Scanner, Image, Video, Sight, Form, Kinesis, Scout, Echo, and Foundry retain their distinct domain
jobs and results. They reuse discriminated capability-backed or direct-tool execution binding,
Connector dialects where applicable, `ServiceJobAttempt@1`,
artifact custody, Stasis, cancellation, and recovery mechanics; they do not collapse into one
`MediaJob`, generic `tool_execution`, or universal OpenAI adapter.

[Connectors](connectors.md) owns invocation dialects and the current chat-only implementation
boundary. [Dispatcher (22)](../../adr/22-dispatcher.md) owns matching and leases;
[Orchestrator (23)](../../adr/23-orchestrator.md) owns physical readiness; and [Workers
(14)](../../adr/14-workers.md) owns durable attempt settlement.
