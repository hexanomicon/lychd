---
title: 20. Agents
icon: material/robot-outline
---

# :material-robot-outline: 20. Agents

!!! abstract "Context"
    A model call is not an Agent. An Agent is one typed cognitive step whose instructions and
    result contract remain stable while the selected model, generation settings, tools, and
    authority arrive for the particular step. This permits the Vessel to change intelligence
    without relocating policy, identity, or durable execution into an adapter.

## Requirements

- An Agent must be distinct from a model, Graph, Pattern, Persona, Posture, and Lens.
- Its stable recipe, available capability, fresh dependencies, output contract, and result limits
  must be inspectable and separately owned.
- Tools and delegation must not acquire authority through prompt text, construction, or a model
  result; durable truth remains at domain, Graph, identity, consent, and persistence boundaries.

## Considered Options

| Option | Decision | Why |
| --- | --- | --- |
| Put model, credentials, tools, and workflow in one prompt-defined actor | Rejected | It erases capability admission, tool policy, durability, and attribution boundaries. |
| Make Pydantic AI the dispatcher and workflow ledger | Rejected | It owns the inner model/tool loop, not LychD's control plane. |
| Typed spec with late-bound capability | Selected | It keeps cognitive construction stable and binds per-step authority at the Dispatcher seam. |

## Decision

LychD uses in-process **Pydantic AI**, at lockfile-pinned `pydantic-ai-slim==1.25.1`. The
[State](../state-of-the-work.md#pydantic-ai-v1-adapter) owns present adapter evidence; its
[v2 migration](../state-of-the-work.md#pydantic-ai-v2-migration) is Designed.
A v2 adapter must set `end_strategy` explicitly: allowing sibling mutating tools to finish is a
security change requiring review, not a library upgrade.

An Agent joins immutable `AgentSpec`, process-local `AgentForge`, a step-scoped model-shaped
`CapabilityGrant`, fresh `LychDDeps`, and a declared output union. This is the delivered model path;
ADR 22's general grant union does not turn every service into an Agent dependency. The boundaries
are deliberate:

| Concern | Owner |
| --- | --- |
| Instructions, output types, retry ceiling, optional declared toolsets | `AgentSpec` |
| Construction and process-local cache | `AgentForge` |
| Model, settings, runtime toolsets, capability lease | [Dispatcher](./22-dispatcher.md) and `CapabilityGrant` |
| Workflow order, persistence, suspension, recovery | [Graph](./24-graph.md) |
| Permission to act | [Security](./09-security.md), Sigil, grant, and tool handler |
| Durable identity and attribution | [Mirror](./32-identity.md) |
| Consequential human authority | [HitL](./25-hitl.md) |

Pydantic AI owns the inner loop, never a second dispatcher, identity system, ledger, or control
plane.

## The Agent specification

`AgentSpec` is frozen and hashable, with `name`, `instructions_key`, `instructions`,
`output_types`, optional `toolset_names`, `writes`, `retries`, and default `max_tokens`.
`AgentForge.agent_for(spec)` selects a registered builder and caches by the whole specification;
changing any field makes a distinct entry, while an unknown name or toolset fails construction.

`build_agent` binds no model. It can bind named construction-time toolsets, but omits a mutating
set when `writes` is false. Absence is the first gate; a present tool still checks live Sigil,
grant, input, and domain policy at the handler.

### The First One

The delivered Bridge Agent, `THE_FIRST_ONE_SPEC`, returns `BridgeReply | DeferredToolRequests`,
has no construction-time toolsets, and cannot request transition of the substrate leased to it.
Its stable instructions receive the Context Orchestrator's floor at run time. `BridgeReply` is text
plus `FragmentCall`s: each names a Vessel-owned registry entry and parameters, never markup, and
the registry validates it before projection. `Bottleneck` represents contradiction, missing input,
policy block, or unavailable dependency, but while Bridge can settle it as workflow state, it is
not in The First One's current output union.

## Late-bound capability

For each Bridge inference step, the current workflow asks the Dispatcher for a v1 `chat` grant
containing capability specification and state, step/run lease, resolved generation profile, a
required hydrated Pydantic AI model, and agent-loop toolsets only when the capability explicitly
declares `supports_tools = true`. The grant exposes neither its Animator nor Connector. Bridge
passes `grant.model`, `grant.model_settings()`, and `grant.toolsets` to
`agent.run_stream_events`. Agent specifications therefore name neither endpoint nor credential;
no fictitious model/tool-provider pair is needed.

One spec can run with any admitted model meeting the adapter contract. A foreign framework is not
an in-process Agent by analogy: it remains a typed delegated runtime or Animator boundary until a
later ADR admits a versioned interface.

A **coding agent** is a delegated runtime when an external process owns an iterative planner/tool
loop and receives an exact repository or workspace projection under an `AgentJob` `read`,
`candidate`, or `verify` profile. One native Agent step using a remote model is instead a Portal-
backed Agent call; a sovereign node accepting a public task is A2A. These classifications follow
labor and authority, not the model brand. A coding agent may obtain cognition through a local
capability or its job-scoped Provider Gate, but every child remote payload remains a separate
Security-admitted Portal attempt. The outer job never conveys provider credentials, a general
network route, authoritative checkout, or promotion authority.

The same byte-time rule applies inside a native Agent loop: validation repair, tool-result follow-
up, changed history, or another model round creates another canonical payload and therefore another
Portal road decision/EgressDecision. One grant or first-round approval never authorizes the whole
loop's future payloads.

At that boundary the trusted Portal adapter or job-scoped Provider Gate freezes the canonical
child body and presents it to Spellweaver's road-decision service under the pinned parent placement
policy. It must obtain a fresh road decision, a consumer-specific Cut when transformation is
required, and the byte-time EgressDecision before sending. A native model loop or Coffin runtime
cannot mint, cache, widen, or reuse them; inability to obtain the full chain refuses that round.

Provider Portals route their declared alias through the matching Pydantic AI provider or
model-profile resolver, including unsupported-setting filtering. OpenRouter, LiteLLM, and Ollama
use their provider resolvers; Google's OpenAI-shaped endpoint uses the Google model profile over
the OpenAI transport. Generic OpenAI-compatible endpoints and local runtimes instead select
LychD's conservative inline-schema, non-strict-tool profile. OpenRouter ids must retain their
`provider/model` namespace. Under the pinned adapter, Google, LiteLLM, and Ollama aliases are
Chat-only; Responses is admitted only for OpenAI, OpenRouter, or an explicitly compatible generic
endpoint. This does not claim a native Gemini transport or providers outside the registered
aliases.

## Run dependencies

Every step receives fresh, frozen `LychDDeps`:

| Field | Contract |
| --- | --- |
| `sigil` | Acting identity and scopes. |
| `grant` | Capability grant for this step. |
| `dispatcher` | Narrow grant-service port for tools. |
| `orchestrator` | Narrow lifecycle-transition port. |
| `context` | Context Orchestrator for the assembled floor. |
| `run_id`, `step_id` | Correlation identities. |
| `priority` | Admitted run priority. |

It carries no database session, raw settings, or secret. The control plane consumes credentials to
construct connectors; persistence and domain services remain narrow ports rather than cognitive
smuggling.

## Typed results and truth

Pydantic validation establishes shape, not the truth of prose, an effect's validity, claim
identity, or permission to publish or promote. Deterministic validators, domain handlers, Sigil,
grant, receipts, evaluation, HitL, and the Phylactery retain those proofs. A typed falsehood is
still false. `AgentSpec.retries` bounds validation repair; tool argument repair may use Pydantic
AI retries, while policy refusal and missing premises settle explicitly rather than demand success
without bound.

### Mechanical cognitive postures

A **Posture** bounds instructions, output schema, model settings, and tool grant. Expansion,
review, repair, and red-team work belong in separate runs when one proposal would otherwise grade
itself. A **Lens** is a Posture template for [Simulation](./31-simulation.md)'s isolated Shadow
branch. A **Persona** is a durable revisioned identity that may wear Postures. Persona names the
actor; Posture constrains this act; Lens diversifies a simulation. These are enforceable contracts
only where types, grants, settings, and Graph placement preserve the claimed separation.

A local Privacy Agent is a Posture at an explicit Spell placement. It receives bounded raw material
to produce a sanitized candidate and findings, but no Portal tool or declassification authority;
its confidence is not permission. Deterministic control comes first, policy can require an
independent verifier, and Security's trusted Portal Egress Gate makes the exact decision.

## Streaming, history, and limits

`pump_agent_events` streams one hop: text starts and deltas become raw Oculus token events, while
the final result supplies typed output and Pydantic AI history. The workflow serializes complete
history and the new suffix separately for settlement or suspension. Bridge reserves the grant's
output allowance and passes the remainder as Pydantic AI's input-usage limit. Pre-request counting
occurs only when a model implements `count_tokens`; the delivered OpenAI-compatible models do not,
so their provider-reported limit is post-response rather than a guaranteed preflight fence.
ADR 21 owns the separate character governor.

LychD does not yet share one `UsageLimits` object across a child-Agent tree. Future nested native
Agents need explicit budgets. Opaque delegates receive serialized limits through their own grant;
they inherit no `RunContext`, live toolsets, provider objects, or leases.

## Consent suspension

The delivered deferred substrate allows one model round to return exactly one approval request and
no external deferred calls. It serializes suffix and call identifiers—not a live
`DeferredToolRequests` object—plus the capability key, durable toolset id and type, tool name,
project-owned effect id and revision, and prepared-definition digest. Resume reacquires a fresh
grant and refuses execution if that binding changed before supplying `DeferredToolResults`;
approval-required tools without an effect id and revision cannot park. The tool owner must revise
the effect revision whenever executable semantics change without changing the prepared definition.
Multiple approvals and generic `CallDeferred` labor fail truthfully because the record cannot
represent them. No tracked production toolset currently originates an approval request; the
executable path is exercised by test-injected toolsets only. Delegated labor is a separate Graph
node with its own job and trust boundary; ADR 25 owns durable consent ordering and recovery.

## Artifacts and multimodality

Agents may return immutable `ArtifactRef` metadata. LychD does not yet materialize authorized
blobs as Pydantic AI binary content. Image, audio, and other bytes require a Vessel-owned
materializer enforcing authorization, media constraints, and provenance; metadata is not payload.

## Correspondence

The Agent is where **the Call** becomes bounded labor and **the Blade** gives its answer form. A
model opens possibilities and a schema cuts a result; neither crowns itself true. [The Lich's First
Invocation](../sepulcher/lich/index.md#the-first-invocation) owns the mythic correspondence.

## Consequences

!!! success "Positive"
    Definitions survive model and hardware change; outputs, dependencies, retries, and tools stay
    inspectable; the same Agent can use a deterministic offline model.

!!! failure "Negative"
    Schemas and tools need deliberate maintenance, adapter compliance is required, and suspension,
    recursive budgets, artifacts, and foreign delegation need explicit LychD machinery.

## Verification

`tests/agents/test_factory.py`, `test_the_first_one.py`, `test_bridge_chat_graph.py`,
`test_consent_resume.py`, and `test_state_serializable.py` exercise construction, cache identity,
tool absence, typed output, grants, streaming, settlement, continuation, and the durable Graph
boundary. Dependency, message-schema, deferred-API, or stream changes require those tests and
State to move before this law claims new behavior.
