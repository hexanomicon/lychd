---
title: 42. Legion
icon: material/sitemap
---

# :material-sitemap: 42. The Legion: Sovereign Expansion

!!! abstract "Context and Problem Statement"
    LychD begins as one source-sovereign host, but an operator may own other machines,
    accelerators, robots, and embedded bodies. One cognitive continuity must be able to delegate
    bounded work across that iron without turning every node into a second Master, sharing the
    Phylactery, or letting a central scheduler override physical truth known only by the
    destination body.

    Legion therefore needs two truths at once: the Master owns cognitive continuity and fleet
    delegation; every enrolled Node Agent remains the sole authority over its local hardware.

## Requirements

- **One cognitive authority:** The Master owns principals, policy, sessions, memory, Graph runs,
  consent, fleet routing, delegation, and the Phylactery.
- **Distinct node identity:** Every Node Agent has an immutable `node_id` and one unique,
  rotating, node-scoped credential. Nodes never share the Master Sigil or wildcard authority.
- **No shared state plane:** Nodes receive no direct access to Master Postgres, queues, Phoenix,
  filesystem, container control, wallet keys, or other Soul-level services.
- **Local physical authority:** A node observes its own devices, validates fresh capacity and
  safety evidence, admits or declines work, fences a local reservation, and alone invokes its
  Orchestrator and Reactor.
- **Semantic delegation:** The Master requests a typed capability and constraints, never shell,
  Systemd, Podman, GPU ordinals, filesystem paths, database operations, or arbitrary Reactor
  commands.
- **Durable, replay-safe protocol:** Delegation, acceptance, cancellation, expiry, result, and
  ambiguous outcomes survive process and network failure with explicit identities and fences.
- **Bounded evidence and artifacts:** Results are typed, quarantined observations. Artifact
  movement is content-addressed, policy-admitted, integrity-checked, and never an implicit URL
  fetch.
- **Refusal and reconciliation:** A body may reject work that does not fit. Partitions, duplicate
  delivery, restore, stale commands, and version skew remain explicit states.

## Considered Options

!!! failure "Option 1: Full LychD against the Master's services"
    Boot the same Vessel on every node, point it at the Master's Postgres and Phoenix, share a
    Master credential, and consume common queues.

    This gives every body Soul-level authority, permits cross-node job theft and false recovery,
    removes per-node revocation, and turns one compromised machine into compromise of the whole
    Sepulcher.

!!! failure "Option 2: Central cluster control"
    Kubernetes, Ray, Slurm, or another central scheduler treats nodes as interchangeable workers
    and owns their hardware transitions.

    Such systems may be useful inside a future provider, but they cannot replace node-local
    evidence, reservations, refusal, or LychD's authority contract. Commodity-LAN tensor
    parallelism is also different from delegating semantic work.

!!! failure "Option 3: Stateless webhooks or remote shell"
    Direct HTTP callbacks omit durable delivery and fencing; remote shell gives the Master
    unbounded implementation authority over another body. Neither survives replay, partitions,
    cancellation, or ambiguous effects honestly.

!!! success "Option 4: Owned Node Agents over the Intercom law"
    Legion is a trusted owned-node profile over the future
    **[Intercom (26)](26-a2a.md)** envelope. A distinct Node Agent persists commands,
    reservations, execution, results, and evidence locally while the Master maintains the
    delegation ledger and cognitive continuity.

## Decision Outcome

**Legion is adopted as a distributed-embodiment Domain manifested through a bounded owned-node
protocol and deployment profile.** An enrolled body is a **Thrall** in the mythic register and a
**Node Agent** in engineering. It is not a second Master-shaped Vessel, a remote database client,
a universal shell, or a foreign A2A peer.

### 1. Split the Authorities

| Jurisdiction | Master | Node Agent |
| :--- | :--- | :--- |
| Cognitive truth | Principals, policy, Runs, Graphs, memory, consent | None |
| Delegation state | Fleet routing, task ledger, transactional outbox | Local command/result journal |
| Identity | Enrolls and revokes each node | Unique rotating node credential |
| Physical truth | Ranks fresh advertisements, requests outcomes | Observes, reserves, admits, actuates, refuses |
| Evidence | Aggregates a bounded fleet projection | Owns freshest local evidence and signed spool |
| Artifacts | Authorizes manifests and destinations | Verifies digest, policy, capacity, and publish |

The Node Agent owns no Master queue or Graph checkpoint. Its crash-safe residue is enough to
deduplicate commands, fence reservations and effects, replay results, and reconcile recovery—not
a copy of the Lich's soul.

### 2. The Intercom Carries Delegation

The first transport should be node-initiated so a Node Agent requires no public listener. A
mutually authenticated stream or long-poll may carry the messages, but transport identity is only
evidence for the Ward; it is not application authorization.

The protocol is versioned, audience-bound, replay-safe, and durable:

1. The Master parks cognition, records a delegation attempt and outbox message, then publishes.
2. The Node Agent authenticates the envelope, persists and deduplicates it before acknowledging,
   and accepts with a fenced reservation or returns a typed decline.
3. The node records execution and its terminal result before sending a replayable receipt.
4. The Master resumes only when task, node, Master epoch, node session, delegation fence, and
   result digest match the admitted attempt.

Delivery is at least once. Observable handling must be idempotent; consequential external effects
also require a stable effect identity, node-local effect receipt, and explicit reconciliation.
Late results never authorize blind retry on another node. Results return over the existing
principal-bound channel or durable Master pull, not an arbitrary callback URL supplied by a task.

### 3. The Body Decides What Fits

A fleet advertisement is an expiring scheduling hint, not a reservation or permission. It may
describe semantic capabilities, pre-provisioned artifact digests, coarse capacity, health, queue
pressure, and evidence age.

Before acceptance, the destination takes a coherent local snapshot; validates device identity,
VRAM and host-memory headroom, topology, health, thermals, deployment compatibility, active
reservations, and safety margin; then acquires a fenced local reservation. Only that reservation
may enter local admission closure, lease drain, narrow actuation, readiness convergence,
compensation, and containment. The Master may select another eligible node after a decline, but it
cannot override a body's fresh refusal.

### 4. Fences Against Ghost Commands

Every consequential message binds a Master epoch, node boot and session identity, delegation
attempt and fence, node-local reservation generation, and local transition precondition. A stale
command remains evidence but cannot admit resources, actuate the host, release a newer
reservation, or wake cognition.

After a partition, local policy may let already admitted bounded work finish and spool its result;
the Master rejects it if its fence has been superseded. Restoring the Master from an older
snapshot closes fleet admission, advances the Master epoch, and reconciles signed node receipts
before new delegation. Reconnection alone is not reconciliation.

### 5. Oculus Observes; It Does Not Command

Nodes emit bounded, signed, versioned evidence batches with node and boot identity, monotonic
sequence, occurrence/send/receive times, schema and redaction class, gaps, decision references,
reservations, transitions, and outcomes. They never receive central observability write
credentials.

Native **[Oculus (29)](29-observability.md)** may retain and project this evidence with visible
freshness and clock uncertainty. Historical observations can improve ranking; only current
node-local evidence, reservation, and actuator preconditions authorize physical work. Optional
external Eyes remain projections.

### 6. Artifacts Cross by Digest

The first Legion profile advertises only models and runtimes already provisioned under exact
content digests. A missing artifact makes placement infeasible and never triggers implicit
download or Portal fallback. Later transfer requires classified content-addressed manifests,
bounded resumable chunks, integrity verification, quotas, provenance and license policy, atomic
publish, and corruption quarantine.

## Delivery Boundary

This ADR accepts architecture, not a deployed fleet. LychD currently has no node role, enrollment,
durable delegation protocol, expiring advertisement, node journal, fencing, artifact transport,
or fleet evidence path. **[State of the Work](../state-of-the-work.md#legion-federation)** owns
that boundary; the **[Legion page](../sepulcher/extensions/legion.md)** owns its user-facing
doctrine.

The safe delivery order is: prove fresh resource evidence, deployment variants, and fenced
admission on one host; create disjoint Master and Node Agent assemblies with negative composition
tests; land credential-backed Ward identity; build durable Intercom delegation and the node
journal; prove partition, replay, cancellation, restore, version-skew, artifact, and two-node GPU
behavior; then add fleet scrying through the Orb.

## Consequences

!!! success "Positive"
    - One cognitive continuity can grow new bodies without sharing Soul-level authority.
    - Each machine preserves local safety, refusal, and recovery.
    - Transport, hardware, and artifact providers may evolve behind one delegation law.

!!! failure "Negative"
    - Node identity, journals, fences, reconciliation, and evidence make Legion deliberately more
      complex than direct HTTP.
    - The Master remains a cognitive single point of failure by design.
    - Native resource intelligence must be proven on one host before fleet placement is honest.
