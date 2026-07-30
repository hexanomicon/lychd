---
title: Legion
icon: material/hexagon-multiple-outline
---

# :material-hexagon-multiple-outline: Legion

> _One Will may summon many hands._
>
> _No hand is given the soul merely to lend its strength._

**Legion** is the distributed-embodiment Extension Domain for operator-owned compute nodes. It
lets one Magus place bounded work across owned iron while every destination remains the sole
authority over its own hardware. Legion is **Designed**, not delivered: no working node
enrollment, delegation, reservation, fencing, artifact movement, or fleet evidence path exists
today. [State of Work](../../state-of-the-work.md#legion-federation) owns delivery truth;
[ADR 42](../../adr/42-legion.md) owns the accepted design.

## One continuity, sovereign bodies

An enrolled body is a **Legionnaire** in mythic language and a **Node Agent** in engineering.
Legion extends one Magus; it neither creates a second Master nor describes the
**[Necropolis](../../adr/26-a2a.md#legion-and-necropolis)** relation among foreign sovereign
peers.

The Master retains principals, policy, consent, sessions, memory, Graph continuity, routing, and
the delegation ledger. Each node alone observes its hardware, admits and reserves work, actuates,
recovers, and refuses. Its Node Agent holds an immutable `node_id`, one rotating node-scoped
credential, and a small crash-safe journal. It receives no Master Sigil and shares no Master
database, queue, filesystem, or infrastructure control plane.

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

During a partition, local policy may finish already admitted bounded work and spool its result. A
superseded fence makes that result inadmissible. After Master restore, fleet admission closes, the
epoch advances, and signed node receipts reconcile before delegation resumes. Reconnection alone
does not settle the past.

## Evidence and artifacts

Node evidence is bounded, signed, versioned, freshness-visible, and attributable. [Oculus](oculus.md)
may project it, but only fresh node-local evidence, a local reservation, and actuator
preconditions may authorize physical work. A signature attributes bytes; it does not make them
safe or true. Results and artifacts remain typed and quarantined until their own checks pass.

The first Legion profile admits only artifacts already present under exact content digests.
Missing material makes placement infeasible—never an implicit URL or Master-path fetch, download,
or Portal fallback. Later transfer requires separately admitted, content-addressed, bounded,
policy- and integrity-checked custody with atomic publication and corruption quarantine. ADR 42
owns the mechanics.
