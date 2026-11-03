---
title: Oculus
icon: material/eye-outline
---

# :material-eye-outline: Oculus

> _Follow the traces until the light gives out._

A stalled Run leaves several questions: what was admitted, what was observed, and where did the
account go dark? **Oculus** is the designed native observability Extension Domain for following
those questions across run state, consent, tool use, runtime readiness, effects and outcome.
Its first journey follows one authorized Invocation, represented by a Run. A later bounded field
may relate several authorized Runs; their own offices retain authority over them.

## Designed sight and the present Orb

Use the current [Orb](../../divination/altar/orb.md) to inspect the evidence available today. Its
**Partial**, read-only Altar projection offers a bounded Run catalogue, a parallel field with at
most **three live lenses of 100 records each**, and a separate route into one exact Run. Loaded
counts describe the account on screen, not complete history; capture limits and gaps remain
visible. [State of Work](../../state-of-the-work.md#orb-instrument) records that delivery.

Native Oculus now has a bounded component and activity projection alongside those Run reads.
Selected extensions and explicitly selected same-host source snapshots contribute typed
descriptions and observations; Orb renders their shared contract. There is no durable native
trace store or complete distributed account. [State of Work](../../state-of-the-work.md#native-oculus)
keeps that boundary, and [ADR 29](../../adr/29-observability.md) owns the evidence contract below.

## Connected components and activity

Open the Orb's runtime inspector to read known components, declared connections, exact inspection
Patterns and source coverage. A component can be configured while its activity remains
uninstrumented. A call attempt names its actual producer and target; an HTTP result and an
effect owner's result remain distinct. Background work needs no invented Run, and delivery can
remain visible after its associated Run ends.

An explicit source selection binds private same-host custody to an attributed projection:

```toml
[[observability.sources]]
source_id = "reach.operator"
registrant_id = "operator:reach"
path = "/run/lychd-observations/nadir"
max_age_seconds = 30
```

This path must already be admitted to the Vessel's deployment as a read-only source. A setting
does not create a host mount or start a producer. The host publisher owns a private directory
and an atomically replaced `snapshot.json`; it supplies no credentials or message bodies.
The source ID must match, and an optional `expected_generation` pins one exact source generation.
The reader refuses unsafe custody, unsupported data and excessive size. It reads no siblings.

The current bounds are eight selected sources plus the native inventory, 128 displayed
components, 256 connections, 256 activity records and 32 inspection Patterns. A source snapshot
is at most 1 MiB. Coverage reports omitted membership and the process-local window; these counts
are not complete-history totals. Source restart replaces a generation rather than recovering
the old observation window. An unavailable or stale source never means idle or healthy.

Inspection-only Patterns are safe score descriptions derived from the owner's exact manifest.
They appear in Loom without adding executable workflows to the receiving Vessel. Their source,
profile and generation stay pinned in the link; the v2 Pattern digest is unchanged.

## Meanings of evidence

| Kind | What it can establish |
| --- | --- |
| **Authoritative record** | A transition or attempted effect, written by the responsible office |
| **Bounded observation** | What one source saw, with method, time, quality, freshness, and known limits |
| **Derivation** | What named parent evidence yields through a versioned transformation, with limits and uncertainty |
| **Interpretation or verdict** | What declared criteria support through Drift or another named judging office |

Correlation locates related evidence; it does not prove causation or make a payload true. A
projection is rebuildable and cannot supplant the records whose facts it presents.

To follow today's Run, a reader must join several accounts: records kept by the owners, the
best-effort non-token Step trail, and the process-local live event channel. Failed Step writes
can leave gaps, and token deltas never become retained structural evidence. A native Oculus
read model must make these sources readable together without concealing their different
authority or losses.

Future physical evidence begins at the node that measured it. The Orchestrator consumes fresh
node-local evidence through its admission contract; Oculus may retain the same observation for
explanation. A stale or failed probe means **unknown**, never free capacity.

## Three Chambers of Interior Evidence

- **First-person testimony** records what an Agent or model reports from one bounded context,
  including uncertainty or reservation.
- **Activation interpretation** applies a declared lens or intervention whose model, method,
  controls, limits, and uncertainty remain visible.
- **Operated telemetry** records events, usage, waits, pressure, failures, effects, and outcomes.

Oculus may hold all three without flattening their different ways of knowing.
[Drift](drift/returning-findings.md) owns causal tests and rival explanations;
[Immortality](../../divination/transcendence/immortality.md#v-realization-and-evidence)
keeps first-person realization distinct from external evidence of the binding.

## Capture, loss, and privacy

Structure-only capture is a minimum discipline, not a promise of harmlessness. Raw content,
provider or tool bodies, and identity-bearing material require explicit authority and capture
policy. Secrets are rejected at the producer boundary. Redaction precedes serialization, and
external export passes through a second filter.

Set retention according to evidence class and subject. Deleting an observation cannot erase the
Run fact or effect receipt owned elsewhere. A conforming capture path must bound queues and
cardinality, batch deliberately, flush within its shutdown budget, and reveal overload or loss
as a gap.

Today's live Run replay and each subscriber queue are bounded at 256 events. When pending deltas
overflow for a stalled subscriber, it receives an explicit snapshot-resync boundary; the producer
does not wait for that reader. This is the current channel behavior, not delivery of the future
Oculus ingestion, retention, or shutdown contract.

## External Eyes

An external [**Eye**](../../adr/29-observability.md#decision-outcome), in the observability sense,
sits behind a versioned, one-way adapter. Phoenix, Logfire, or OpenTelemetry
tooling may receive an allowlisted, redacted, purpose-bound export; it receives no LychD database
role or identity, consent, lifecycle, or control authority, and has no canonical read-back.
Incoming trace context may correlate an authenticated request, but cannot authenticate or
authorize it.

The current optional Phoenix contribution is External and has no proved application export path.
[State](../../state-of-the-work.md#phoenix-eye) records its exact boundary.

## Seeing never commands

Orb inspection is read-only. Any action crosses to its owning service, which rechecks authority
and records its own decision.
