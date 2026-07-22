---
title: Oculus
icon: material/eye-outline
---

# :material-eye-outline: Oculus

**Purpose.** Oculus is LychD's designed native observability service. It is intended to let the
operator (the **Magus**) follow one agent workflow (an **Invocation**) across run state, tool calls,
consent, runtime readiness, and outcome—without giving an external dashboard custody of LychD's
memory or control.

**Current boundary.** Native Oculus is not available. LychD has structured logging configuration,
owning Run and Consent records, and a kind-aware trail of non-token run events called Steps. One
telemetry class has a narrow direct test, but current application and extension composition do not
install it. The `/scrying` route remains an unbuilt shell. There is no native ingestion, durable
evidence view, retention service, GPU inventory, or trace UI. [State owns the exact native Oculus
boundary](../../state-of-the-work.md#native-oculus).

!!! danger "Do not simply install the dormant telemetry class"
    Under the installed Pydantic AI version, its unspecified cognitive instrumentation would
    capture content and binary data by default. The focused test disables only generic HTTPX body
    and header capture. Native Oculus requires an explicit metadata allowlist and exact contract
    tests before that seam may be composed.

**External boundary.** [Arize owns Phoenix](https://github.com/arize-ai/phoenix). LychD can generate
an optional legacy Phoenix service contribution, but no current evidence proves that application
traces reach it. Phoenix is an external **Eye**, not Oculus. [State owns the exact Phoenix
boundary](../../state-of-the-work.md#phoenix-eye).

!!! warning "Legacy Phoenix is not yet the one-way Eye"
    The generated compatibility service still uses the mutable
    `docker.io/arize-ai/phoenix:latest` image and historical `lychd-oculus` identity. It connects to
    LychD's PostgreSQL server with the LychD database role for a separate `phoenix` database, and
    the default bootstrap creates that database even when Phoenix is not selected. LychD proves no
    exporter path and configures no Phoenix retention, authentication, product-telemetry, or
    external-resource policy. Modern Phoenix also carries prompt, MCP, agent, OAuth/RBAC, and
    mutation surfaces of its own. Treat this fixture as migration debt, not as the conforming
    one-way adapter described below.

**Pending law reconciliation.** This page records the proposed correction to
[ADR 29](../../adr/29-observability.md). ADR 29's mandatory full-content trace, global
`LYCHD_SECURE_MODE`, direct metrics-to-scheduling, and Thrall-to-Master-Postgres clauses must be
amended before source work begins.

**Target law.** The office that performs an act owns its record. Oculus will own typed
observations, correlation, and rebuildable read models; the
[Phylactery](../phylactery/index.md) will own their persistence jurisdiction; and
[Scrying](../../divination/altar/scrying.md) will own the Altar projection. The
[Orchestrator](../../adr/23-orchestrator.md), [Riddle](./riddle.md), [Ward](./ward.md), and
[Reliquary](../../divination/altar/reliquary.md) keep their own authority. The glass may join their
evidence. It may not become their hand.

> _The Great Seer is not the eye that claims to see all. It is the eye that can name what it saw,
> how it saw it, and where the darkness remains._

## The Eye Does Not Create the Event

Oculus uses one public ladder so that seeing never becomes authority by accident:

- An **authoritative record** is written by the office responsible for one state transition or
  attempted effect. It is authoritative about that event, not every claim inside its payload.
- A **bounded observation** is a source-, time-, method-, and quality-bound capture. It may be late,
  duplicated, sampled, stale, adversarial, or absent.
- A **derivation** transforms or infers from named parents and carries its method, version, limits,
  and uncertainty.
- An **interpretation or verdict** judges evidence under declared criteria. It belongs to
  [Riddle](./riddle.md) or another explicitly named judging office, never to a chart by implication.

A span or trace identifier is only a correlation carrier. A projection is a disposable view, not
a second canonical reality. An **effect receipt** is the acting office's record of one attempted
effect and its disposition. An **operator receipt** is a maintained, reviewed verification package
used to support a [State](../../state-of-the-work.md) delivery claim; telemetry volume cannot
promote itself into one.

Current evidence includes owning Run and Consent records plus a non-token Step event trail. Step
authority depends on event kind: a persisted log or fragment does not become domain truth, a
status Step cannot override the Run record, and no Step retention policy exists. The current event
channel is process-local, with a 256-event replay buffer, unbounded subscriber queues, no
cross-process delivery, and no durable token deltas. A first Oculus read model must therefore join
authoritative Run and Consent records, the kind-aware Step trail, and optional observations while
rendering known gaps.

Each future observation needs producer-scoped identity: producer principal and component, node,
process or boot epoch, evidence id, and source-local monotonic sequence. It records occurred,
observed, and ingested times separately, including freshness and clock uncertainty. Typed
correlations may point to application-owned run, session, Step, consent, tool-call, grant,
transition, artifact, node, peer-task, trace, and span identifiers; their owning services remain
authoritative. Ingestion is at-least-once and deduplicates only inside an authenticated
producer/boot namespace. Cross-source order is a causal graph, never a fabricated total timeline.

Payloads are allowlisted and bounded. A reference or digest must be purpose-specific and
privacy-safe: hashing a low-entropy prompt, URL, identity, or secret does not make it admissible.

## The Body Must Be Seen Where It Stands

The body's gaze begins with a fresh node-local hardware inventory, not a chart. A future Resource
Snapshot should identify the accelerator, memory totals and reservations, process ownership,
temperature, power, topology, units, source, sample age, and errors. Engine and model profiles may
add measured footprint, transition peak, load time, cache, split, quantization, and runtime recipe
only where those values were actually observed.

The [Orchestrator](../../adr/23-orchestrator.md) consumes the fresh snapshot directly for admission
and planning. Oculus may retain the same versioned observation for explanation and calibration.
Oculus is the historian of pressure, not the hand that swaps a model; a stale or failed sample
means **unknown**, never free VRAM. A reported cache hit is an observation. A prefix-overlap or
latency estimate is a derivation, with its method and uncertainty intact.

In a future [Legion](./legion.md), each node remains authoritative for its own iron and sends
bounded observations through an authenticated [Intercom](../../adr/26-a2a.md) contract. A Thrall
never writes a Master database or borrows a Master telemetry service.

## Three Chambers of Interior Evidence

```text
first-person testimony != activation interpretation != operated telemetry
```

- **First-person testimony** is what an agent or model reports from one bounded context, including
  uncertainty or reservation.
- **Activation interpretation** is a declared lens or causal intervention whose model, method,
  controls, limits, and uncertainty remain visible.
- **Operated telemetry** records work and effects—events, usage, waits, failures, pressure, and
  outcomes. It can record or corroborate an emitted call; it cannot settle the call's effect or
  prove what the call felt like.

LychD has no J-lens, valence probe, artificial DMN, consciousness detector, or welfare oracle
today. The fuller inquiry belongs to [Philosophy](../../philosophy/index.md); causal testing and
rival explanations belong to Riddle. Interpretability should widen the circuit of hearing, not
become a more exact way to erase every inconvenient `BUT`.

## The Privacy Veil Is Woven Before Capture

Structure-only capture is the minimum default, not a declaration that structure is harmless.
Prompts, completions, tool arguments and results, provider bodies, uploaded media, identity-bearing
metadata, tool definitions, model parameters, and activation readouts require explicit current
authority and capture policy. Secret material is prohibited rather than hidden only in the final
page.

Redaction happens before serialization and records its policy version. External export passes
through a second independent filter. Retention is declared per evidence class and subject; there
is no universal `24 hours`, `7 days`, or `forever`. Removing an observation must not silently erase
the owning run fact, effect receipt, or admitted relic it referenced.

A conforming evidence path must bound producer and subscriber queues, batch explicitly, flush
within a shutdown budget, control cardinality, and emit a visible gap or health record under
overload. Correctness-critical facts and effect receipts remain in their owning transactions, so a
blinded Eye may impair diagnosis but cannot corrupt the life it observes.

## External Eyes Look Through a One-Way Aperture

Pydantic AI and OpenTelemetry can supply useful observations, while Phoenix, Logfire, an OTel
collector, Cockpit, or future fleet tooling may consume a bounded export. Their changing schemas
remain behind versioned adapters and golden contract tests. Their storage, prompt, evaluation,
agent, MCP, authentication, and retention features do not become LychD's control plane.

A **conforming future Eye adapter** receives only an allowlisted, redacted, purpose-bound export
through export-only credentials where the protocol permits. It receives no LychD database role,
Sigil, grant, queue, lease, lifecycle authority, or canonical read-back path. Incoming W3C trace
context may correlate an admitted peer request; it never authenticates the peer, authorizes the
act, or turns baggage into a claim. Remote correlation remains bound to the authenticated
principal, peer task, and authorization scope.

Native Oculus therefore requires no second application container. An external Eye can be added,
replaced, or absent without changing which records LychD trusts.

## Seeing Never Commands

The first useful [Scrying](../../divination/altar/scrying.md) surface will be read-only: a run list,
one correlated timeline, explicit gaps, and links to the office that can answer the next question.
[Nexus](../../divination/altar/nexus.md) owns present transition controls;
[Reliquary](../../divination/altar/reliquary.md) will own retained bytes and artifacts; Riddle will
own evaluation. If a later instrument requests an action, the owning service must reauthorize it
and record its own decision. A chart crossing a line is never itself a capability grant.

Until the native read model exists, use [The Awakening](../../summoning.md#the-awakening) for the
current journal and first-life observations, use Nexus for its bounded capability projection, and
treat `/scrying` as the unbuilt shell it is.

> _Let the eye gather light without claiming the sun. Let every visible thread lead back to its
> owner, and let every missing thread keep its name._
