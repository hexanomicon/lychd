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

The boundary is deliberately narrow:

```text
requirements → declared capability → observed state → WARM grant → registered lease
```

A capability-bearing Animator is the route; the delivered path has no provider-pair abstraction.
Dispatcher emits its authoritative dispatch event only after lease admission.

The live Animator is a capability/runtime handle, not a deployment document. It carries its exact
Rune identity, Connector, and typed runtime surfaces while
[Containers](08-containers.md), Bind, and Scribe retain physical compilation authority.

## Capability Binding Cartography

Three records prevent a declaration from pretending to be an observation, or an observation from
pretending to be permission:

| Record | Office |
| --- | --- |
| `CapabilitySpec` | Immutable declaration of Animator, family, model, and route shape. |
| `CapabilityState` | Latest observation for that exact declared capability. |
| `CapabilityGrant` | Temporary, WARM binding with usable runtime surfaces. |

Keys are `{animator}:{family}:{model_id}`. They cross registry, Dispatcher, Orchestrator, events,
and Graph; after a pause a consumer re-fetches this canonical identity, never a mutable handle.

### Families and modalities

Families are exact: `chat`, `vision`, `embedding`, `stt`, `tts`, `tool_execution`, and `rerank`.
`modalities_in` and `modalities_out` describe material, not the family: image-capable chat is
still `chat`; visual analysis may be `vision`; there is no generic `audio` family.

A request matches only its exact family, optional exact model id, every required input modality,
and—when asked for—`supports_tools is True`. Unknown support never admits work.

### Declaration and observation

The declaration holds animator/runtime/source kind, family/model, surfaces, modalities, tool and
streaming support, generation profile, context limit, dynamic trait, and concurrency intent.
`is_dynamic` says a running local runtime may load a model; it is not readiness. The observed
phase is `COLD`, `ACTIVATABLE`, `WARMING`, `WARM`, `ERROR`, or `UNKNOWN`.

Soulstone declarations compile from Runes and selected adapters; probes update state and may fill
open runtime facts. An unknown local runtime stays passive unless an explicit adapter or
OpenAI-compatible alias gives it semantics. A Portal creates routes only for models declared in
its Rune; zero declarations mean zero routes. Portal routes are non-dynamic and non-dedicated.
Their default `probe = false` makes no discovery egress, and a readiness probe never authorizes
private transmission. That unprobed route is projected as `UNKNOWN` and unverified, never fabricated
as `WARM`, so it cannot receive a grant.

Soulstone adapter ownership is the adapter's exact declared runtime key; registration cannot claim
another adapter's runtime. Registry hydration is staged and rejects a runtime unless it retains the
exact input Rune and its name and id equal the Rune name. Every synthesized specification must then
name that Animator, the Rune's canonical runtime and source kind, and the canonical
`{animator}:{family}:{model_id}` key before any snapshot is published.

A probe is a total observation of the exact requested capability-key set. Duplicate, missing, or
foreign keys are contract failures; a successful result replaces that Animator's cached states as
one operation, while an exception, cancellation during the probe, or malformed result invalidates
the affected prior observations.
A failed full-registry refresh invalidates the full cached observation set rather than preserving
stale warmth. Initial
hydration probes the complete staged snapshot and publishes neither runtime nor state until every
result validates, so a failed first probe leaves the registry retryable. Portal egress probing is
selected only by the exact Portal definition's typed strategy.

## Resolution

`lease_grant` receives family, optional exact model, run id, priority, required input modalities,
and a tools requirement. It removes `ERROR` candidates and orders the rest deterministically:
open admission, active Animator, warm capability, Animator name, capability key. This is
readiness matching, not a judgment of quality, price, privacy, or correctness.

The chosen record is refreshed immediately before issue.
Capability specifications passed to activation or abandonment adapters and every persistent-
resident projection are deep snapshots; extension code cannot rewrite the canonical declaration
through those call surfaces. Animator Rune and group projections are likewise detached, and group
membership is returned as an immutable sequence. Connector model inventories are deep-copied on
admission and every registry projection, including inventories supplied by extension connectors.

| Observation | Result |
| --- | --- |
| `WARM`, admission open | Issue and register a grant. |
| `COLD`/`ACTIVATABLE`/`WARMING`, dedicated | `HardwareTransitionRequired`. |
| Those phases, shared or non-managed | `CapabilityUnavailable`. |
| `ERROR` | Unavailable with observed reason. |
| `UNKNOWN` | Re-probe; unavailable if still unresolved. |
| Drain closes during issue | Transition required, and only this race is translated. |

The transition signal contains capability key, Animator name, and optional ready estimate—no
connector, model, lease, or service handle. Graph may release its edge, ask Orchestrator to
converge, and dispatch afresh. Dispatcher never calls `activate_capability` or `await_warm`.

### The Grant Lease Doctrine

Registry issue permits only a `WARM` record. The frozen grant contains its specification and warm
snapshot, `GrantLease` identity/holder/issue time/scope, resolved generation profile, live
Animator, required hydrated model, and bound toolsets. `tool_execution` may have no model; every
other current family must hydrate one, or fails unavailable before later execution.
Specification and state accessors return defensive copies, including nested mutable values; only
the explicitly named runtime/model/tool handles remain live process objects.

The registry creates the identity; Dispatcher registers it in the process-local `LeaseLedger`.
Its context manager releases on ordinary exit, body failure, and observation failure. Duplicate
ids are defects. A closed drain gate is the sole issue failure that turns into Stasis.

Drain truth is absence of ledger leases on an Animator. Admission closes before drain waits, so
new work cannot enter an eviction set. A run waiting for its remedy owns no lease. `expires_at` is
recorded but unenforced: there is no renewal or distributed stale-grant fence. Grants contain
trusted live objects and may not enter Graph state, persistence, or delegated processes.

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
dispatch, because no typed egress admission path exists. This quarantine is not privacy-safe Portal
operation. Sigil visibility, Portal secure mode, Toll arbitration, Censor/Privacy
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
    - Local and remote routes share a grant shape without shared lifecycle authority.

!!! failure "Cost"
    - Registry and lease coordination are process-local.
    - Order ignores quality, price, privacy, and Sigil visibility; Portal sources are quarantined and incomplete probes can refuse a viable local route.
    - The matcher picks one candidate and does not score or explain alternatives.

## Verification

Dispatcher unit tests cover matching, deterministic preference, generation settings, and frozen
grants. The dispatch decision table covers every readiness row, grant/drain race, event ordering,
and release on failure; registry, Portal, adapter, and lease tests cover synthesis, opt-in probes,
hydration, and drain accounting. [State of Work](../state-of-the-work.md#animator-dispatch-spine)
owns delivery claims.
