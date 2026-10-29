---
title: Legion
icon: material/hexagon-multiple-outline
---

# :material-hexagon-multiple-outline: Legion

> _One Will may summon many hands._

**Legion** is the distributed-embodiment Extension Domain for operator-owned compute nodes. It
lets one Magus place bounded work across owned iron while every destination remains the sole
authority over its own hardware. Legion is **Designed**; no operational node path is delivered.
[State of Work](../../state-of-the-work.md#legion-federation) records that boundary, and
[ADR 42 — Multinode](../../adr/42-multinode.md) owns the accepted design below.

## One continuity, sovereign bodies

An enrolled body is a **Legionnaire** in mythic language and a **Node Agent** in engineering.
Legion extends one Magus; it neither creates a second Master nor describes the
**[Necropolis](../../adr/26-a2a.md#legion-and-necropolis)** relation among foreign sovereign
peers.

The Master keeps the work's logical continuity: principals, policy, consent, sessions, memory,
Graph, routing, and delegation ledger. The node decides what may happen on its hardware. It
observes, admits, reserves, actuates, recovers, and can refuse.

A Node Agent carries an immutable `node_id`, a rotating node-scoped credential, and a small
crash-safe journal. This gives it its own accountable boundary rather than a copy of the Master.
It receives no Master Sigil and shares none of the Master's database, queue, filesystem, or
infrastructure control plane.

## Delegation through Intercom

Legion uses an owned-node profile over the future [Intercom](../../adr/26-a2a.md). A node-initiated
authenticated channel may avoid a public listener. Transport identity supplies evidence to Ward;
application permission is still a separate decision.

Delegation names a typed capability and expected outcome under declared constraints. It never
prescribes shell commands, Systemd or Podman operations, GPU ordinals, filesystem mutations,
database access, or Reactor instructions. The node chooses how to satisfy the request—or declines
it.

Delivery is at least once. Both sides therefore persist and deduplicate tasks and results, bind
consequential work to stable task and effect identities, and preserve explicit ambiguous
outcomes. Silence or a late result cannot authorize blind repetition of an external effect.

## The body decides what fits

A resource advertisement is an expiring scheduling hint, not a promise. Acceptance depends on a
fresh coherent local snapshot, compatibility and safety checks, and a fenced reservation. Only
that reservation may enter local admission closure, lease drain, actuation, readiness,
compensation, and containment.

After a decline, the Master may seek another eligible body. It cannot override a fresh refusal
from the machine that would bear the work.

## Fences against ghosts

Consequential messages bind Master epoch, node boot/session, delegation attempt/fence, reservation
generation, and transition precondition. Stale messages remain evidence but cannot act.

If the connection breaks, local policy may let already admitted bounded work finish and spool
its result. A superseded fence makes that result inadmissible. If the Master is restored, close
fleet admission, advance its epoch, and reconcile signed node receipts before resuming delegation.
Reconnection restores communication; it cannot by itself settle what happened while the accounts
were apart.

## Evidence and artifacts

Node evidence is bounded, signed, versioned, freshness-visible, and attributable. [Oculus](oculus.md)
may project it, but only fresh node-local evidence, a local reservation, and actuator
preconditions may authorize physical work. A signature attributes bytes; it does not make them
safe or true. Results and artifacts remain typed and quarantined until their own checks pass.

The first Legion profile admits only artifacts already present under exact content digests.
Missing material makes placement infeasible—never an implicit URL or Master-path fetch, download,
or Portal fallback. Later transfer requires separately admitted, content-addressed, bounded,
policy- and integrity-checked custody with atomic publication and corruption quarantine. The
[Multinode Covenant](../../adr/42-multinode.md) owns the mechanics.
