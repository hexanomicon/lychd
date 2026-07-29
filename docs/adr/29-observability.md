---
title: 29. Observability
icon: material/telescope
---

# :material-telescope: 29. Observability

!!! abstract "Context and Problem Statement"
    An agentic runtime crosses deterministic infrastructure, probabilistic model behavior,
    asynchronous workflow, human consent, and external effects. Diagnosis requires structured
    evidence that can correlate those layers without turning telemetry into authority, raw content
    into a default payload, or a visual trace into hidden thought. LychD needs a native evidence
    office and Altar projection that remain useful without requiring a second application stack.

## Requirements

- **Owning-Office Truth:** The office that performs an act owns its authoritative record. Oculus
  owns bounded observations, correlation, and rebuildable read models; it never owns the run,
  consent, grant, transition, artifact, verdict, or hardware act it depicts.
- **Bounded Traceability:** Stable identities connect Intent, Pattern revision, run, lane, step,
  tool call, consent, capability grant, lease, transition, peer task, artifact, evaluation, and
  outcome where those records exist. Missing relations remain explicit gaps.
- **Privacy Before Capture:** Payloads are allowlisted, classified, bounded, and redacted before
  serialization. Prompts, completions, arguments, results, media, headers, secrets, and identity
  material are never mandatory trace content.
- **Rebuildable Projection:** A snapshot plus backfill and live tail can reconstruct the supported
  view after reconnect. Overload, retention loss, sampling, redaction, and stale observations
  produce visible gaps rather than inferred continuity.
- **Selected-Run First:** The first useful Orb view follows one authorized Run. A later
  multi-run attention field must remain bounded by explicit time, status, Pattern, authorization,
  and cardinality limits.
- **Mind and Body Without Merger:** Agent activity and physical resource state may be correlated
  while keeping their sources, clocks, freshness, authority, and uncertainty distinct.
- **Fresh Physical Authority:** The Orchestrator consumes fresh node-local resource truth through
  its owning contract. Oculus may retain the same observation for explanation; a telemetry store
  or chart is not a scheduling oracle.
- **Optional Interoperability:** OpenTelemetry and external viewers may consume bounded one-way
  exports without becoming a required container or LychD control plane.
- **A2A Correlation:** W3C Trace Context may correlate an admitted peer request. It never
  authenticates the peer, authorizes an effect, or turns baggage into a trusted claim.

## Considered Options

!!! failure "Option 1: The Cloud Native Suite (Prometheus / Grafana / Jaeger)"
    Deploying a mandatory monitoring stack adds several services, storage and retention policy,
    query languages, and another control surface before a personal daemon has proved the need. Such
    tools may remain optional external viewers or Watcher-class providers.

!!! failure "Option 2: Undifferentiated Persistence-Layer Logging"
    Storing every span, body, metric, and event as unbounded JSONB would confuse vendor telemetry
    with domain truth, make privacy and retention accidental, and couple the Phylactery schema to
    changing upstream payloads.

!!! success "Option 3: Native Oculus with Pluggable Eyes"
    A native Litestar evidence service projects LychD vocabulary through the Svelte Altar and may
    export bounded standards-based signals to optional external Eyes. It adds no second authority.

## Decision Outcome

**Oculus** is adopted as LychD's native evidence Extension Domain. Its canonical input is
structured LychD evidence connecting Intent, graph movement, tool use, consent, runtime pressure,
and outcome. The **Orb** is its Altar projection; **scrying** is the disciplined act of using that
instrument. Phoenix, Logfire, Cockpit, an OpenTelemetry
collector, or another viewer may be an external **Eye**; none owns run, identity, scheduling,
authorization, retention, or evidence semantics.

!!! warning "Implementation state"
    Native Oculus and the Svelte Orb projection are accepted but not complete. The repository
    ships `observability/phoenix` as an optional external Eye integration whose new default unit
    stem is `lychd-phoenix`. Existing operator configuration may retain the explicit legacy
    `name = "oculus"` until deliberately migrated; that compatibility value never turns Phoenix
    into native Oculus. The static Svelte Altar now has a bounded selected-Run Orb projection
    over the run/event records available to the current process. That projection is not native
    Oculus ingestion, durable evidence custody, a live trace service, or cross-process
    completeness. State of Work owns the exact delivery boundary.

### 1. Evidence Ownership and Correlation

Oculus uses four explicit classes:

1. An **authoritative record** is written by the office responsible for one state transition or
   attempted effect.
2. A **bounded observation** names its producer, subject, method, time, freshness, quality, and
   limits.
3. A **derivation** names its parent evidence, method and version, uncertainty, and invalidation
   boundary.
4. An **interpretation or verdict** judges evidence under declared criteria and belongs to Riddle
   or another explicitly named judging office.

A span, event, or correlation identifier carries relation; it does not transfer authority. Every
visible edge must distinguish its meaning, including containment, Pattern permission, correlation,
explicit causal parentage, waiting, grant or lease use, artifact production, lineage, declaration,
and evaluation. Temporal adjacency or a common trace id does not prove causality.

Evidence identity is producer-scoped. A conforming observation carries a producer principal and
component, node, process or boot epoch, evidence id, and source-local monotonic sequence. Occurred,
observed, and ingested times remain separate, with clock uncertainty where relevant. Cross-source
order is a causal partial order, never a fabricated global timeline.

Runtime correlation includes stable `run_id`, `lane_id`, `step_id`, `event_id`, `tool_call_id`,
peer-task, consent, grant, lease, transition, artifact, trace, and span identities where their
owning contracts provide them. A rejected or waiting operation should preserve
`failure_class`, `required_state`, `observed_state`, retryability, and the owning blocker relation
when known.

### 2. Native Service and External Eyes

Oculus contributes typed query/event routes and schemas through the shaped Vessel boundary.
The Orb consumes the generated SDK and semantic event contract; components do not query tables or
observability SDKs directly.

Pydantic AI and OpenTelemetry may supply observations behind versioned adapters and golden
contract tests. Generic HTTP instrumentation must not blanket-capture headers, bodies, prompts, or
administration credentials. An external Eye receives only an allowlisted, redacted, purpose-bound
one-way export and no LychD database role, Sigil, grant, queue, lease, lifecycle authority, or
canonical read-back path.

The current Phoenix fixture is migration debt, not proof of this contract: it uses a legacy unit
identity and LychD does not prove an application export, bounded credentials, retention policy, or
native read path through it.

### 3. Interior Evidence Without Mind Reading

Through the Orb, scrying may distinguish three chambers:

- **first-person testimony** — an Agent's deliberately emitted objective, progress summary,
  strategy summary, uncertainty, reservation, or bottleneck report;
- **operated telemetry** — recorded events, tool requests, validations, waits, retries, usage,
  failures, and outcomes; and
- **declared interpretation** — a named evaluation or interpretability method with its model,
  version, controls, limitations, and uncertainty.

None is hidden chain-of-thought. A progress statement is testimony, not proof of the action it
describes. A provider call is telemetry, not proof of what the call “felt like.” A model-written
explanation may be useful evidence while remaining answerable to its source and capture policy.

Context references, retrieved memories, prompt/completion content, tool arguments/results, and raw
provider exchanges may appear only when an explicit current capture policy admits them. Structure
must remain useful when content is unavailable, and **no evidence** must remain a first-class
state.

### 4. Delegated-Agent Evidence

Delegated runtimes are observable only at their admitted boundary. Oculus correlates the Graph
occurrence, `AgentJob`, capability grant, Coffin profile, Provider Gate decisions, normalized
adapter events, usage, artifacts, and terminal adoption. It does not claim access to the foreign
runtime's hidden planner, graph, subagent tree, or chain-of-thought.

Every field declares one of two provenance classes:

- **LychD-observed:** job lifecycle, process settlement, Gate allow/deny, filesystem/artifact
  effects, budget decisions, cancellation, and terminal adoption witnessed by LychD; or
- **provider-reported:** provider usage, session events, tool narratives, rate-limit metadata, and
  other facts parsed from the foreign protocol.

A bounded redacted raw JSONL or protocol trace may be retained as an artifact for diagnosis. It is
untrusted data: malformed lines, unknown event kinds, oversized payloads, embedded terminal
control, prompt injection, and credential-shaped values must be bounded, redacted, or quarantined
before normalization. Unsupported content becomes a visible gap. It never mutates the Graph,
authorizes a tool, settles a job, or becomes a training corpus by default.

The Altar projects this evidence through its existing instruments:

- **Bridge:** the offered delegated task and returned result or candidate artifact;
- **Loom:** the special macro-node, its typed contract, policy, and routes;
- **Orb:** actual activity, waits, denials, usage, quota posture, trace gaps, and artifacts; and
- **Nexus:** configured adapters, provider pools, Gate health, capacity, cooldown, and secret
  references without secret values.

No fifth delegated-agent control page is created. The projections remain read models of the owning
Graph, security, scheduling, and evidence records.

### 5. Orb Read Models

The first useful **[Orb](../divination/altar/orb.md)** target is:

1. an authorized run list;
2. one selected Invocation;
3. a correlated timeline with explicit gaps;
4. a read-only graph joined to the exact Pattern revision by stable identities;
5. live-versus-durable, freshness, redaction, retention, and unknown labels; and
6. links to the owning instrument for a Pattern, consent, grant, transition, artifact, or verdict.

Only after that model proves it reduces diagnosis time may Oculus expose a bounded multi-Invocation
attention query. “All active” means only authorized, observed active/waiting/terminal-recent work
inside explicit time, status, Pattern, pagination, and cardinality limits. Truncation, sampling,
stale producers, and gaps remain visible. This is an attention index, not omniscience and not a
claim that workflows form a literal neural network.

The Orb client may select, filter, lay out, and acknowledge events visually. Motion is not
evidence. A later annotation is a separate authorized record anchored to stable evidence identity;
it never edits the event or triggers retry, approval, cancellation, publication, or transition as
a side effect.

The current delivered subset starts at item 2: one direct selected-run URL, producer-local ordered
status/node/dispatch/transition evidence, exact Pattern correlation when the pinned manifest
validates, explicit retained bounds and gaps, and links to the owning Bridge, Loom, and Nexus
surfaces. It deliberately omits the run list, live tail, graph, durable Oculus read model,
artifacts, annotations, and multi-run attention field rather than simulating them in the client.

### 6. The Physical Body and Pulse

This subsection is target law for a conforming future physical-observation boundary. The current
Orchestrator and Nexus do not possess a general Resource Snapshot for VRAM, thermals, power,
process ownership, or system-wide pressure; current delivery is limited to declared capability
state and retained transition observations named in State of Work.

Physical truth begins with a fresh node-local Resource Snapshot owned by the physical runtime and
Orchestrator boundary. It names the device, capacity, reservations, process ownership,
temperature, power, topology, units, source, sample age, and errors only where observed. A stale or
failed sample means **unknown**, never free capacity.

The Orchestrator consumes the fresh snapshot directly for admission and planning. Oculus may retain
the same versioned observation for history and explanation. Engine and request adapters may add
measured usage, latency, token counts, queue depth, cache, memory pressure, and transition data with
their source and units. Estimates and trends remain derivations; they do not become grants,
reservations, Riddle verdicts, or automatic promotion thresholds.

In a future Legion, each node remains authoritative for its own iron and sends bounded observations
through an authenticated Intercom contract. A Legionnaire never writes directly to a Master's
Phylactery or borrows a Master's telemetry authority.

Prometheus, Grafana, Loki, Alloy, Cockpit, or similar tools may become optional Watcher-class
Animators when fleet scale, historical queries, alerting, or log volume justify them. They remain
replaceable consumers/providers and do not replace native owning records.

### 7. Privacy, Retention, and Failure

Structure-only capture is the minimum default, not a claim that structure is harmless. Every
evidence class declares capture purpose, allowed fields, classification, retention, visibility,
and export policy. Redaction occurs before serialization and records its policy version. External
export passes through a second independent filter. Secret material is prohibited rather than
merely hidden in the final page.

A conforming native Oculus must bound producer and subscriber queues and make cardinality,
batching, flush, and shutdown behavior explicit. Loss, overload, sampling, clock uncertainty, and
expired retention emit a visible gap or health record. The current process-local event broker
bounds replay retention but leaves live per-subscriber queues unbounded; slow-subscriber
backpressure is therefore not delivered yet. Correctness-critical facts and effect receipts stay
in the acting office's own transaction, so a blinded Oculus may impair diagnosis but cannot corrupt
execution truth.

Removing an observation must not silently remove an owning run fact, effect receipt, or admitted
relic that it referenced. A viewer cache is disposable and rebuildable from the supported snapshot
and event cursor.

## Consequences

!!! success "Positive"
    - LychD can correlate its own grants, transitions, consent, artifacts, evaluations, costs, and
      physical evidence without granting a vendor control-plane ownership.
    - Privacy, gaps, freshness, and uncertainty become part of the evidence contract rather than
      final-page decoration.
    - The selected-run-first path yields a useful diagnostic surface before a multi-run canvas.
    - External Eyes can be added, replaced, or absent without changing canonical truth.

!!! failure "Negative"
    - LychD owns the quality, retention, migration, accessibility, and performance of a
      domain-specific evidence service and trace explorer.
    - Stable cross-office identities and partial-order semantics require more design than logging
      arbitrary spans.
    - Optional instrumentation and external Eyes add their own overhead, privacy review, and
      compatibility work when enabled.
