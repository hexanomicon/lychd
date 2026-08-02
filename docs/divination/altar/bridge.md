---
title: Bridge
icon: material/bridge
---

# :material-bridge: Bridge

The **Bridge** is the operating conversation: the Magus offers a bounded Intent, follows its
result, and decides a supported consent request. It carries conversation without becoming Weaver,
Oculus, artifact custody, or authority over anything mentioned in a reply.

Enter through:

```text
http://127.0.0.1:7134/bridge
```

The current Altar is a contained same-host surface: keep the listener on literal `127.0.0.1`, use a
dedicated browser profile, and do not proxy, tunnel, or port-forward it. Begin with the
[Altar boundary](index.md) if that containment is not already in place.

## One crossing at a time

The delivered Bridge supports:

- local sessions and **New Séance**;
- text submission with one retry-stable request identity, one canonical Run, and held-turn repair;
- process-local semantic event streaming;
- pending consent cards and decisions;
- session inspection;
- closed, server-validated GenUI fragments retained through terminal refresh, with inert key-only
  compatibility for older rows that never enters a current renderer; and
- a per-turn run strip linking exact run evidence into the [Orb](orb.md).

The run strip names the Run, Pattern revision, canonical status, and current activity. It does not
show evidence freshness or a structured **Why waiting?** explanation. A spinner, elapsed clock, or
open stream is never promoted into workflow progress.

Bridge is not a general run dashboard, workflow editor, annotation canvas, or ambient view of
every Agent. Loom owns Pattern projection; Orb owns evidence; Nexus owns physical transitions.

## Continuity without invented memory

Visible turns and model history are different records. A user turn may appear immediately, but
only a settled agent turn appends one complete Pydantic AI history unit. Provider hops inside that
unit are normalized to the owning LychD run, so a consent return cannot survive without its
originating tool call. Replaying the same settled Run outcome is a no-op; reusing its Run/role
identity for different visible content, state, or fragments fails closed.

A later invocation takes the newest whole turns within configured turn and character budgets,
validates typed messages, then rebuilds the Stable Floor under the capability actually granted.
Consent resume keeps the current call chain whole and re-bounds older settled turns under the new
grant.

An admitted user turn is not a completed answer. Until a matching agent turn settles, a terminal
failed or cancelled Run remains visible as a Run projection. Its durable status outranks a lagging
process-local stream, and delayed recovery snapshots cannot replace a newer cursor/generation.
Cancelling a Run immediately clears the selected session's consent cards and count, then refetches
authoritative session truth. A failed refetch leaves those actions revoked rather than displaying
stale authority.

This is bounded conversational continuity. It is not Archive retrieval, full-session replay,
cross-process event durability, or proof that concurrent turns serialize.

## Consent is not a suggestion

The server validates the request, descriptor, reference, and decision. A conversational proposal
never carries executable authority. Approval applies to the exact pending request presented; it
does not widen the Agent's tools, mutate another object, or grant a later effect.

The current boundary supports the existing consent round. Run admission has a durable database
delivery outbox, but general multi-approval flows, notifications, and durable token/event delivery
remain absent.
[State of Work](../../state-of-the-work.md#bridge-surface) owns the exact boundary.

## Designed crossings

Two useful movements remain designed:

- **Pin and Ask** would attach an authorized typed reference—such as an exact Pattern revision and
  node, Run event, transition, or artifact revision—to a new Intent. The composer must preview
  identity, included/summarized/unavailable/redacted material, and permission; the Vessel must
  reauthorize the reference at admission. A pin grants neither retrieval nor mutation by itself.
- **Propose in Loom** would turn selected conversation into an attributable charcoal candidate
  against an exact base Pattern. The candidate would remain inert until Weaver's future draft
  contract validates and publishes a new revision.

Neither exists today. Copying prose or a canvas coordinate is not a typed reference, and natural
language does not round-trip into executable workflow law.

For the movement that does exist:

```text
offer Intent
→ inspect the admitted Run
→ answer consent when asked
→ receive the settled result
→ follow its exact Orb evidence
```
