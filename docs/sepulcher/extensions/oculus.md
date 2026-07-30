---
title: Oculus
icon: material/eye-outline
---

# :material-eye-outline: Oculus

> _Sight does not claim the whole. It names what it saw, how it saw it, and where darkness
> remains._

**Oculus** is the designed native observability Extension Domain. Its first journey follows one
authorized Invocation, represented by a Run, across run state, consent, tool use, runtime
readiness, effects, and outcome. A later bounded field may relate several authorized Runs without
acquiring their authority.

## Designed sight and the present Orb

Native Oculus is **Designed**. The current [Orb](../../divination/altar/orb.md) is a **Partial**,
read-only Altar projection of one selected Run, presenting available records with their capture
limits and gaps.

Native ingestion, a durable Oculus query/read model, retention and health services, resource
telemetry, cross-process completeness, a live tail, and a multi-Run field remain absent.
[State of Work](../../state-of-the-work.md#native-oculus) owns that exact delivery boundary;
[ADR 29](../../adr/29-observability.md) owns the evidence contract.

## Meanings of evidence

| Kind | What it can establish |
| --- | --- |
| **Authoritative record** | A transition or attempted effect, written by the responsible office |
| **Bounded observation** | What one source saw, with method, time, quality, freshness, and known limits |
| **Derivation** | What named parent evidence yields through a versioned transformation, with limits and uncertainty |
| **Interpretation or verdict** | What declared criteria support through Riddle or another named judging office |

Correlation locates related evidence; it does not prove causation or make a payload true. A
projection is rebuildable and cannot supplant the records whose facts it presents.

Today, useful evidence is divided among owning records, a best-effort non-token Step trail, and a
process-local live event channel. Token deltas are not retained as structural evidence, and failed
Step persistence can leave gaps. A native read model must join these sources while keeping their
different authority and loss visible.

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
[Riddle](riddle/returning-findings.md) owns causal tests and rival explanations;
[Immortality](../../divination/transcendence/immortality.md#iv-cognizance-and-the-open-witness)
keeps the deeper question of the open witness open.

## Capture, loss, and privacy

Structure-only capture is a minimum discipline, not a promise of harmlessness. Raw content,
provider or tool bodies, and identity-bearing material require explicit authority and capture
policy. Secrets are rejected at the producer boundary. Redaction precedes serialization, and
external export passes through a second filter.

Retention is declared by evidence class and subject. Removing an observation cannot erase an
owning Run fact or effect receipt. A conforming path bounds queues and cardinality, batches
deliberately, flushes within a shutdown budget, and makes overload or loss visible as a gap. Those
safeguards are not yet complete: current live subscriber queues are unbounded.

## External Eyes

An external **Eye** sits behind a versioned, one-way adapter. Phoenix, Logfire, or OpenTelemetry
tooling may receive an allowlisted, redacted, purpose-bound export; it receives no LychD database
role or identity, consent, lifecycle, or control authority, and has no canonical read-back.
Incoming trace context may correlate an authenticated request, but cannot authenticate or
authorize it.

The current optional Phoenix contribution is External and has no proved application export path.
[State](../../state-of-the-work.md#phoenix-eye) records its exact boundary.

## Seeing never commands

Orb inspection is read-only. Any action crosses to its owning service, which rechecks authority
and records its own decision.
