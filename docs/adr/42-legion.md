---
title: 42. Legion
icon: material/sitemap
---

# :material-sitemap: 42. Legion

!!! abstract "Context"
    One Magus may own other machines, accelerators, robots, and embedded bodies. Delegation must
    extend cognitive continuity without turning every body into another Master, sharing the
    Phylactery, or allowing a scheduler to override physical truth known by the destination.

## Decision

**Legion** is the distributed-embodiment Domain: an owned-node profile over future
[Intercom](26-a2a.md). A **Legionnaire** in mythic language is a **Node Agent** in engineering.
It is neither a Master-shaped Vessel, remote database client, universal shell, nor foreign A2A peer.

| Jurisdiction | Master | Node Agent |
| --- | --- | --- |
| Cognitive truth | Principals, policy, consent, sessions, memory, Graphs, Runs, routing | None |
| Delegation state | Fleet ledger and transactional outbox | Crash-safe command/result journal |
| Identity | Enrols and revokes nodes | Unique rotating node-scoped credential |
| Physical truth | Ranks fresh advertisements and requests outcomes | Observes, reserves, admits, actuates, refuses |
| Evidence and artifacts | Authorizes manifests and aggregates bounded projection | Produces freshest evidence; verifies/publishes admitted material |

No Node Agent receives Master Postgres, queues, filesystem, Phoenix, container control, wallet
keys, Master Sigil, or other Soul-level service. Its residue only deduplicates messages, fences
reservations/effects, replays results, and reconciles recovery.

## A durable semantic delegation

The first channel should be node-initiated so the node needs no public listener. A mutually
authenticated stream or long poll carries a versioned, audience-bound, replay-safe envelope;
transport identity is evidence for Ward, not application permission.

1. Master parks cognition, writes delegation attempt/outbox intent, then publishes.
2. Node authenticates, persists and deduplicates before acknowledgement, and returns a typed
   decline or a fenced reservation.
3. Node records execution and terminal result before a replayable receipt.
4. Master resumes only when task, node, Master epoch, node session, delegation fence, and result
   digest match the admitted attempt.

Delivery is at least once. Requests name a typed capability, constraints, and expected outcome,
never shell commands, systemd/Podman action, GPU ordinal, filesystem path, database operation, or
Reactor instruction. Observable handling is idempotent; consequential external effects also bind a
stable effect identity, node-local effect receipt, and explicit reconciliation. Late results cannot
authorize blind retry elsewhere; results use the principal-bound channel or Master pull, never a
task-supplied callback URL.

## The body decides what fits

An advertisement is an expiring scheduling hint, not a reservation or permission. It can expose
semantic capability, provisioned artifact digest, coarse capacity, health, queue pressure, and
evidence age. Before acceptance the node takes a coherent local snapshot, validates device
identity, VRAM/host-memory headroom, topology, health, thermals, compatibility, active
reservations, and safety margin, then takes a fenced local reservation. Only that reservation may
enter admission closure, lease drain, narrow actuation, readiness, compensation, and containment.
After decline Master may ask another eligible node but never overrides local refusal.

Every consequential message binds Master epoch, node boot/session, delegation attempt/fence,
reservation generation, and local transition precondition. A stale command remains evidence but
cannot admit resources, actuate, release newer reservation, or wake cognition. During partition,
local policy may finish admitted bounded work and spool its result; Master rejects a superseded
fence. Master restore closes fleet admission, advances its epoch, and reconciles signed node
receipts before new delegation. Reconnection alone is not settlement. Cancellation, expiry,
revocation, version skew, duplicate delivery, and ambiguous effects remain explicit states.

## Evidence and artifact boundary

Nodes emit bounded, signed, versioned evidence batches with node/boot identity, monotonic sequence,
occurrence/send/receive times, schema/redaction class, gaps, decision references, reservations,
transitions, and outcomes. [Oculus](29-observability.md) may project freshness and clock
uncertainty; only fresh local evidence, local reservation, and actuator preconditions authorize
physical work. Signatures attribute bytes, not truth or safety.

The first profile advertises only models/runtimes already provisioned at exact content digests.
Missing material makes placement infeasible; it never triggers an implicit URL/Master-path fetch,
download, or Portal fallback. Later artifact transfer needs classified content-addressed manifests,
bounded resumable chunks, integrity checks, quotas, provenance/license policy, atomic publication,
and corruption quarantine. Results remain typed quarantined observations until admitted.

## Delivery and consequences

This Covenant is **Designed**, not a fleet. No node role, enrollment, durable delegation,
advertisement, local reservation, fencing, artifact transfer, durable spool, cancellation,
settlement, or fleet-evidence path ships. [State of Work](../state-of-the-work.md#legion-federation)
owns that boundary; [Legion](../sepulcher/extensions/legion.md) owns operated doctrine.

Safe delivery proves fresh resource evidence, deployment variants, and fenced admission on one host;
then disjoint Master/Node assemblies with negative composition tests; credential-backed Ward;
durable Intercom and node journal; partition, replay, cancellation, restore, version-skew, artifact,
and two-node GPU behaviour; and finally fleet projection.

Legion grows one cognitive continuity without sharing Soul authority, but deliberately costs node
identity, journals, fencing, reconciliation, evidence, and proof of native resource intelligence on
one host before fleet placement is honest.
