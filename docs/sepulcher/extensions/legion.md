---
title: Legion
icon: material/hexagon-multiple-outline
---

# :material-hexagon-multiple-outline: Legion

**Purpose:** Legion is the intended coordination of operator-owned compute nodes: one cognitive
continuity may delegate bounded labor across many bodies, while every body remains the sole
authority over its own hardware.

**Delivery boundary:** LychD has no node role, enrollment, durable delegation protocol, expiring
resource advertisement, node-local reservation journal, fencing, artifact transport, or fleet
evidence path. There is no Legion endpoint or mode to enable.
[State of the Work owns the exact federation boundary](../../state-of-the-work.md#legion-federation).
[ADR 42](../../adr/42-legion.md) owns the accepted authority split and delivery order.

**Extension form:** Legion is a distributed-embodiment Domain manifested as an owned-node protocol
and deployment profile, not as a second scheduler or universal remote shell. Node Agent, robot,
accelerator, cluster, and transport implementations may vary only behind one delegation,
fencing, refusal, and reconciliation law; each destination body remains sovereign over its iron.

!!! danger "The false binding remains rejected"
    A Legion node must **not** run the Master application against the Master's Postgres, share a
    universal Master Sigil, consume the Master's queues, or write directly to the Master's Phoenix
    or observability store. Those ADR 42 mechanics would give every node Soul-level authority,
    permit cross-node job theft and false recovery, erase per-node revocation, and turn one
    compromised body into compromise of the whole Sepulcher. The aspiration survives; that
    topology does not.

> _One Will may summon many hands._
>
> _No hand is given the soul merely to lend its strength._
>
> _Each body keeps its gate, its memory of consequence, and its right to refuse the impossible._

In the mythic register, an enrolled owned node is a **Thrall**. In the engineering register, it is
a distinct **Node Agent**—not a second Master-shaped Vessel, not a remote database client, and not a
foreign A2A peer. Legion extends one Magus across owned iron; the **Necropolis** lets sovereign
strangers negotiate labor. They may share protocol primitives, but never authority profiles.

## I. One Continuity, Many Sovereign Bodies

The boundary is intentionally asymmetric:

- **Cognitive truth.** The Master owns principals and policy, sessions and memory, Graph runs and
  consent, fleet routing, delegation, and the Phylactery. A Node Agent owns none of those and holds
  no Master queue or Graph checkpoint.
- **Identity.** The Master enrolls and may revoke each node. A Node Agent holds one unique,
  rotating, node-scoped credential and immutable `node_id`—never the Master Sigil or `*`.
- **Physical truth.** The Master ranks fresh advertisements and requests semantic outcomes. The
  Node Agent observes local devices, admits or declines work, reserves resources, and alone invokes
  its local Orchestrator and Reactor.
- **Durable residue.** The Master owns the delegation ledger and transactional outbox. The Node
  Agent keeps a small crash-safe command, reservation, execution, result, and evidence journal—never
  a copy of the Master's soul.
- **Observation.** The Master aggregates a future fleet projection for the Orb. The Node Agent owns the
  freshest local evidence and a bounded signed spool.

The Master never sends shell, Systemd, Podman, filesystem, database, GPU-ordinal, or arbitrary
Reactor commands. It asks for a typed capability under declared constraints. The Node Agent decides
how—or whether—that request may inhabit its iron.

## II. The Intercom Carries Delegation

Legion should be a trusted owned-node profile over the future
**[Intercom](../../adr/26-a2a.md)** envelope, not an ad hoc direct-HTTP shortcut. Transport may begin
as a node-initiated mutually authenticated stream or long-poll so nodes require no public listener,
but transport identity is only evidence for the Ward; it is not application authorization.

The future protocol must be versioned, audience-bound, replay-safe, and durable:

1. The Master parks cognition, records a delegation task and matching outbox message, then publishes.
2. The Node Agent authenticates the envelope, persists and deduplicates it before acknowledging,
   and either accepts with a local reservation or returns a typed decline.
3. The node records execution and its terminal result before sending a replayable receipt.
4. The Master resumes a Graph only when task, node, Master epoch, node session, delegation fence,
   and result digest all match the admitted attempt.

Delivery is at least once. Observable task and result handling must be idempotent; the network must
never promise magical exactly-once effects. Cancellation, expiry, partitions, duplicate results,
and ambiguous outcomes remain explicit states rather than being translated into silence.

At-least-once command delivery is not permission to repeat an external effect. Consequential work
needs a stable effect identity, a node-local effect receipt and fence, and explicit reconciliation
of an ambiguous outcome. The Master must not retry it on another node merely because a result is
late.

Results return over the existing principal-bound channel or a durable Master pull. A task may not
name an arbitrary callback URL. Any later callback profile must be enrolled to the node principal
and revalidate scheme, host, port, DNS/IP resolution, redirects, and forbidden local or metadata
networks at admission and connection time.

A valid node signature proves which enrolled body produced the bytes; it does not make those bytes
safe or true. Results and artifacts remain typed, bounded, and quarantined until their parser,
content, provenance, and policy checks succeed. They do not enter prompts, memory, or tools merely
because the node is owned.

## III. The Body Decides What Fits

A fleet advertisement is an expiring hint. It may name semantic capabilities, pre-provisioned
artifact digests, coarse capacity, health, queue pressure, and evidence age. It cannot reserve a
GPU or authorize a transition.

After the Master selects a candidate, the destination must take a fresh coherent local snapshot,
validate device identity, VRAM and host-memory headroom, topology, health, thermals, artifact and
deployment-variant compatibility, active reservations, and safety margin, then acquire a fenced
local reservation. Only that reservation may enter the existing local sequence of admission
closure, lease drain, narrow actuation, readiness convergence, compensation, and containment.

The Master may try another authorized node after a decline; it may never override the body's
fresh refusal. Native resource intelligence must first be proved on one host. The present switch
policy counts evictees but does not know VRAM capacity, model footprint, placement, topology, or
transition peak; [State records that scheduler boundary](../../state-of-the-work.md#resource-aware-scheduling).

## IV. Fences Against Ghost Commands

Every consequential message must be bound to layered generations: a Master epoch, node boot and
session identity, delegation attempt and fence, node-local reservation generation, and the local
transition precondition. A stale command may be retained as evidence but may not admit resources,
actuate the host, release a newer reservation, or wake cognition.

If a node partitions after accepting bounded work, local policy may let that work finish and spool
its result; the Master does not accept it after its fence is superseded. If the Master is restored
from an older snapshot, fleet admission closes, the Master epoch advances, and signed node receipts
are reconciled before new delegation. “Thralls reconnect automatically” is not a recovery protocol.

## V. Oculus Sees the Legion; It Does Not Command It

Each node is intended to emit bounded, signed, versioned evidence batches carrying node and boot
identity, monotonic sequence, occurrence/send/receive times, schema and redaction class, gaps,
decision references, reservations, transitions, and outcomes. Nodes must not receive direct
Postgres, Phoenix, or other central observability write credentials.

Native **[Oculus](./oculus.md)** may retain and project this evidence with visible freshness and
clock uncertainty. Historical observations may improve ranking and calibration, but only fresh
node-local inventory, a local reservation, and the local actuator preconditions authorize physical
work. Optional external Eyes may consume bounded exports; they never become fleet truth.

## VI. Artifacts Cross by Digest

The first viable Legion should advertise only models and runtimes already provisioned under exact
content digests. A missing artifact makes a placement infeasible; it must not trigger an implicit
download or Portal fallback. Later transfer requires classified content-addressed manifests,
bounded resumable chunks, integrity verification, quotas, provenance and license policy, atomic
publish, and corruption quarantine. A task may never supply an arbitrary URL or Master filesystem
path for a node to fetch.

## VII. The Road to Many Bodies

The safe order is: correct ADR 42; build fresh resource evidence, deployment variants, and fenced
admission on one host; create disjoint Master and Node Agent assemblies with negative composition
tests; land credential-backed Ward identity; build the durable Intercom delegation and node journal;
prove partition, replay, cancellation, restore, version-skew, artifact, and two-node GPU behavior;
then add fleet scrying through the Orb. Alternative transports and automatic artifact distribution come only after
the authority protocol survives those trials.

> _Next act: read the [Legion delivery boundary](../../state-of-the-work.md#legion-federation).
> Implementation begins by proving fenced resource admission on one host—not by opening a port._
