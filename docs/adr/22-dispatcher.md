---
title: 22. Dispatcher
icon: material/directions-fork
---

# :material-directions-fork: 22. Dispatcher

!!! abstract "Context"
    A request says what faculty it needs; a model name does not say whether that faculty exists,
    accepts the necessary material, or is ready now. Local Soulstones and remote Portals change
    state independently of the request. LychD needs one admission office that can bind semantic
    demand to a live capability without acquiring the right to move the machine.

## Decision

**Dispatcher** selects a capability and admits a temporary grant. It never starts, stops, loads,
or evicts an Animator. [Orchestrator](23-orchestrator.md) owns those transitions; [Graph](24-graph.md)
owns whether a wait stays live or becomes durable.

The accepted general-service boundary is deliberately narrow:

```text
typed demand → interface/profile declaration → fresh state → exact WARM grant → registered lease
```

A capability-bearing Animator is the route; there is no semantic provider-pair abstraction.
Dispatcher emits its authoritative dispatch event only after lease admission. The delivered source
implements the narrower v1 chat-model and toolset compatibility path described below; the
general-service records and discriminated grant union remain Designed.

The live Animator is a capability/runtime handle, not a deployment document. It carries its exact
Rune identity, Connector, and typed runtime surfaces while
[Containers](08-containers.md), Bind, and Scribe retain physical compilation authority.

## Capability Binding Cartography

Five records prevent a declaration from pretending to be proof, an observation from pretending to
be compatibility, or either from pretending to be permission:

| Record | Office |
| --- | --- |
| `CapabilityDemand@1` | Exact interface, operation, typed material, feature facts, invocation mode, and policy constraints required now. |
| `CapabilitySpecV2` | Immutable declaration of Animator, interface, exact profile, operations, invocation mode, driver, and route shape. |
| `CapabilityEvidenceRef` | Reference to exact producer-attributed conformance evidence; neither admission nor current readiness by itself. |
| `CapabilityState` | Latest observation for that exact declared binding and, when required, operation. |
| discriminated capability grant | Temporary, WARM binding exposing only the callable surface for one admitted operation. |

Designed v2 keys are `{animator}:{interface_id}:{profile_ref}` where `profile_ref` includes a safe
stable id and exact immutable revision or content digest. They cross registry, Dispatcher,
Orchestrator, events, Workers, and Graph; after a pause a consumer re-fetches this canonical
identity, never a mutable handle. The operation remains explicit in demand and grant rather than
being hidden in profile identity.

Every component uses the closed slug grammar owned by [Capabilities](../sepulcher/animator/capabilities.md#stable-identity);
colons, paths, whitespace, controls, and floating revisions are forbidden.

### Delivered v1 compatibility projection

Current `CapabilitySpec` keys are `{animator}:{family}:{model_id}` and the single
`CapabilityGrant` class contains either an admitted Pydantic AI chat model with explicitly
declared agent-loop toolsets, or a non-empty `tool_execution` toolset surface. The closed families
are `chat`, `vision`, `embedding`, `stt`, `tts`, `tool_execution`, and `rerank`; `model_id` remains
required. Only `chat` and non-empty `tool_execution` can issue this v1 grant. The other family
labels remain routing metadata and fail closed at issue; they do not prove an executable STT/TTS
call, visual or embedding job, rerank call, Scout effect, host tool, or live session merely because
the vocabulary can name one.

Current `[[models]]` declarations may project into v2 only through an explicit compatibility map
from an exact family/model pair to an exact interface/profile. Persisted v1 keys are never silently
reinterpreted and an unknown family never becomes a generic service.

### Interfaces, profiles, and material

An interface is the versioned semantic ABI, such as `model.chat@1`, `echo.transcribe@1`,
`prism.image@1`, or `prism.scanner@1`. A profile pins the exact model, weights, graph,
workflow, configuration, dependencies, licenses, formats, languages, limits, and conformance
evidence that implement it. Operations name admitted acts such as `generate`, `edit`,
`transcribe`, `segment`, or `search`.

A demand matches only its exact interface and operation, typed I/O contract references, every
required material facet and feature fact, invocation mode, and eligible profile. Unknown support
never admits work. Image-capable chat remains chat; speech emitted by a chat model is not thereby
an eligible synthesizer; `tool` is never a universal effect interface.

### Declaration and observation

The v2 declaration holds animator/runtime/source kind, interface/profile, operations, typed I/O,
invocation mode, driver/dialect, feature facts, conformance evidence, resource envelope, dynamic
trait, and concurrency intent. The current v1 declaration retains its family/model, surface,
modalities, tools/streaming, generation, and context fields.
`is_dynamic` says a running local runtime may load a model; it is not readiness. The observed
phase is `COLD`, `ACTIVATABLE`, `WARMING`, `WARM`, `ERROR`, or `UNKNOWN`.

Soulstone declarations compile from Runes and selected adapters; probes update state and may fill
explicitly open runtime facts. An unknown local runtime stays passive unless an explicit adapter
and dialect profile give it semantics. "OpenAI-compatible" without a named, proved dialect gives
it none. A Portal creates routes only for capabilities declared in its Rune; zero declarations
mean zero routes. Portal routes are non-dynamic and non-dedicated.
Their default `probe = false` makes no discovery egress, and a readiness probe never authorizes
private transmission. That unprobed route is projected as `UNKNOWN` and unverified, never fabricated
as `WARM`, so it cannot receive a grant.

Soulstone adapter ownership is the adapter's exact declared runtime key; registration cannot claim
another adapter's runtime. Registry hydration is staged and rejects a runtime unless it retains the
exact input Rune and its name and id equal the Rune name. Every synthesized specification must then
name that Animator, the Rune's canonical runtime and source kind, and the canonical
`{animator}:{family}:{model_id}` key before any snapshot is published.

A probe is a total observation of the exact requested capability-key and operation set. Duplicate, missing, or
foreign keys are contract failures; a successful result replaces that Animator's cached states as
one operation, while an exception, cancellation during the probe, or malformed result invalidates
the affected prior observations.
A failed full-registry refresh invalidates the full cached observation set rather than preserving
stale warmth. Initial
hydration probes the complete staged snapshot and publishes neither runtime nor state until every
result validates, so a failed first probe leaves the registry retryable. Portal egress probing is
selected only by the exact Portal definition's typed strategy.

## Resolution

Designed resolution receives `CapabilityDemand@1`, run and station-attempt identity, deadline, and
priority. It removes ineligible and `ERROR` candidates and orders the rest deterministically under
an admitted selection policy. This is readiness matching, not a judgment of quality, price,
privacy, or correctness. Current `lease_grant` retains its narrower family/model/modalities/tools
signature and deterministic open/active/warm/name/key order.

The chosen record is refreshed immediately before issue.
Capability specifications passed to activation or abandonment adapters and every persistent-
resident projection are deep snapshots; extension code cannot rewrite the canonical declaration
through those call surfaces. Animator Rune and group projections are likewise detached, and group
membership is returned as an immutable sequence. Connector model inventories are deep-copied on
admission and every registry projection, including inventories supplied by extension connectors.

| Observation | Result |
| --- | --- |
| `WARM`, admission open, executable v1 surface admitted | Issue and register a grant. |
| `WARM`, metadata-only or empty v1 surface | `CapabilityUnavailable`. |
| `COLD`/`ACTIVATABLE`/`WARMING`, dedicated | `HardwareTransitionRequired`. |
| Those phases, shared or non-managed | `CapabilityUnavailable`. |
| `ERROR` | Unavailable with observed reason. |
| `UNKNOWN` | Re-probe; unavailable if still unresolved. |
| Drain closes during issue | Transition required, and only this race is translated. |

The transition signal contains capability key, Animator name, and optional ready estimate—no
connector, model, lease, or service handle. Graph may release its edge, ask Orchestrator to
converge, and dispatch afresh. Dispatcher never calls `activate_capability` or `await_warm`.

### The Grant Lease Doctrine

Registry issue permits only a `WARM` record. The designed discriminated union exposes one of:

- `ModelGrant`: a Pydantic AI model and admitted agent-loop toolsets;
- `CallGrant`: one typed bounded call driver;
- `JobGrant`: typed submit, status, cancellation, result, and reconciliation surfaces; or
- `SessionGrant`: one typed, bounded, epoch-fenced live-session driver.

Every variant contains the exact specification, operation, warm observation, lease identity,
holder, issue time, scope, and only the live surface it admits. Current source delivers one frozen
v1 compatibility grant: `chat` must hydrate its Pydantic AI model and receives agent-loop toolsets
only when `supports_tools = true`; `tool_execution` must hydrate at least one toolset and receives
no model. All other v1 families fail closed because no typed executable surface exists. The grant
does not expose its Animator or Connector. Specification and state accessors return defensive
copies, including nested mutable values; only explicitly admitted model or toolset handles remain
live process objects.

The registry creates the identity; Dispatcher registers it in the process-local `LeaseLedger`.
Its context manager releases on ordinary exit, body failure, and observation failure. Duplicate
ids are defects. A closed drain gate is the sole issue failure that turns into Stasis.

Drain truth is absence of ledger leases on an Animator. Admission closes before drain waits, so
new work cannot enter an eviction set. A run waiting for its remedy owns no lease. `expires_at` is
recorded but unenforced: there is no renewal or distributed stale-grant fence. Grants contain
trusted live objects and may not enter Graph state, persistence, or delegated processes.

For a bounded immediate call, the lease ends with that call. Before any local or remote asynchronous
effect is first submitted, execution ownership must transfer to a persisted
`ServiceJobAttempt@1`; attempts on managed resident or scarce local substrate additionally require
an Orchestrator-visible exact reservation and fence. Live work uses its domain-owned bounded
session record; no common
`SessionAttempt` is accepted yet. A process-local lease alone cannot
prevent duplicate remote effects or fence local residency. [Workers
(14)](14-workers.md#service-job-attempts-designed) owns that Designed handoff.

## Durable Content and ArtifactRef

Runs and checkpoints name content with `ArtifactRef`, never embedded bytes: identity, `sha256:`
digest, media type, byte size, and `public`/`internal`/`private`/`restricted` classification.
Media type projects to input modality and can inform matching.

This is a durable metadata shape, not blob custody or provider materialization. Bridge remains
text-only and neither supplies referenced modalities nor materializes authorized bytes. Blob
authorization, retention, and provider conversion remain separate work.

## Policy boundary

Selection is mostly a future enforcement seam, not a complete policy engine. One coarse rule is
delivered now: every `SourceKind.PORTAL` candidate fails closed before grant, including direct-key
dispatch and direct registry issue, because no typed egress admission path exists. This quarantine
is not privacy-safe Portal operation. Sigil visibility, Portal secure mode, Toll arbitration, Censor/Privacy
Cut/`TransformationReceipt`/Egress Gate, unsupported-modality planning, A2A, and delegated-agent
choice are unwired. They must compose one typed, fail-closed path before grant; none may create an
alternate route around Dispatcher.

[Security](09-security.md#portal-privatization-and-egress) requires both admission before a Portal
grant and a decision over the exact canonical payload immediately before transmission. Dispatcher
will compose those decisions; it does not transform data or currently admit any Portal grant. A
future path must not allow retry, fallback, delegated child, or consent to reuse an obsolete verdict.

## Correspondence

Dispatcher is the switchboard: it hears a requested faculty, consults the living Coven, and names
one warm vessel. Moving the Coven is Orchestrator's work; meaning the act is not Dispatcher's.

## Consequences

!!! success "Accepted"
    - Requirements, observed readiness, usable runtime handles, and drain accounting are separate.
    - A hardware wait is handle-free and cannot deadlock on its own lease.
    - Local and remote routes share typed grant law without sharing lifecycle authority.

!!! failure "Cost"
    - Registry and lease coordination are process-local.
    - Order ignores quality, price, privacy, and Sigil visibility; Portal sources are quarantined and incomplete probes can refuse a viable local route.
    - The matcher picks one candidate and does not score or explain alternatives.

## Verification

Current Dispatcher unit tests cover v1 matching, deterministic preference, generation settings,
and frozen compatibility grants. The current dispatch decision table covers every readiness row,
grant/drain race, event ordering, and release on failure; registry, Portal, adapter, and lease tests
cover v1 synthesis, fresh pre-issue probing, fail-closed family surfaces, opt-in probes, hydration,
and drain accounting. Interface/profile records, general grant variants, service attempts, and
capability-set placement require source and receipts before promotion. [State of
Work](../state-of-the-work.md#animator-dispatch-spine) owns delivery claims.
