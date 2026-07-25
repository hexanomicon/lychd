---
title: Scrying
icon: material/crystal-ball
---

# :material-crystal-ball: Scrying

**Purpose.** Scrying is the intended Altar instrument for following one Invocation through visible
evidence: what moved, what waited, what failed, and what the body can prove about why.

**Current boundary.** The `/scrying` route now returns the full Altar shell, marks this instrument
as active, shows the shared pending-consent sigil, and renders an explicit unbuilt placeholder. It
does not query runs or traces, attach to a Scrying event stream, calculate health, or provide a
native Oculus read model. [State owns the exact Scrying
boundary](../../state-of-the-work.md#scrying-instrument).

**Law.** Scrying is a projection, never a second source of truth. The
[Oculus](../../sepulcher/extensions/oculus.md) owns the evidence model and future read service; the
[Phylactery](../../sepulcher/phylactery/index.md) owns committed run truth at its supported
boundaries; the [Weaver](../../sepulcher/extensions/weaver.md) owns Pattern movement;
[Context](../../adr/21-context.md) owns the active cognitive field; and the
[Mirror](../../sepulcher/extensions/mirror.md) owns identity continuity. The glass may reveal their
evidence. It may not impersonate any of them.

> _“The eye gathers light. The pool gives the light a surface. Neither invents what stands before
> it.”_

## The Pool and the Eye

The **Oculus** is the observing organ. **Scrying** is the disciplined act of looking through it at
the Altar. This distinction protects the Work from a subtle corruption: a beautiful display can
feel more authoritative than the event it depicts. In LychD, the image always points back to the
run, step, grant, consent record, transition, or retained trace that produced it.

Scrying is therefore not a continuous transcript of a hidden inner voice. It is the legible causal
shape of work: an Intent entering a run, graph movement becoming steps, a tool call meeting
validation, a lease meeting physical pressure, a decision entering stasis, and an outcome returning
with evidence. Where evidence is absent, the instrument must show absence rather than complete the
vision from inference.

The Weaver's design reserves a lower-case **Scry** before a reasoning step: it would retrieve
relevant Karma into Context. That memory-preparation path is not implemented today. Capitalized
**Scrying** names the intended operator-facing observation of an Invocation. One would prepare the
field; the other would witness its movement.

## What the Instrument Must Eventually Reveal

Before this instrument can claim usefulness, its owned service and projections must make several
relations explicit:

- one selected Invocation, with stable run and step identities
- current, terminal, waiting, and unknown conditions stated without color alone
- correlation from run to graph step, tool call, consent, capability grant, transition, and
  retained evidence where those records exist
- a visible distinction between process-local live signals and durable facts that can survive a
  restart
- validator-known failure shape, including the required state, observed state, and whether retry
  is lawful
- privacy, redaction, retention, and content-capture boundaries before a trace is displayed or
  exported
- an explicit path to [Nexus](./nexus.md) for physical transition evidence, to
  [Loom](./loom.md) for Pattern topology, and to [Reliquary](./reliquary.md) for a retained output

The canonical Svelte route may own selection, layout, pan/zoom, filters, and other temporary
presentation state. It may not own run transitions, persistence, authorization, or consent.
Snapshots and semantic JSON SSE come from the Vessel; model output is never interpreted as markup.
Graph rendering remains behind one LychD-owned adapter so the Oculus evidence contract is not
coupled to Svelte Flow or another canvas library.

## Witness Without Possession

The deepest purpose of Scrying is not surveillance. It is answerability. A recurrent system can
repair only what it can return to with enough identity and evidence to say: _this occurred here,
under this authority, with this consequence_. The Magus does not gain omniscience at the pool. The
Magus gains a bounded view whose limits are visible.

Until that reflection is backed by an Oculus read model, use the instrument that can answer now:

> _[Return to the Altar map and enter through the Bridge](./index.md#enter-through-the-bridge) with
> one bounded Intent._
