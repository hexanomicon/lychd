---
title: Bindings
icon: material/link-lock
---

# :material-link-lock: Bindings

**Purpose.** Bindings is the intended Altar instrument for making declared relationships legible:
which Rune owns a setting, which named reference points to a provider or identity, which policy
constrains it, and what rite would be required to change it.

**Current boundary.** The `/bindings` route now returns the full Altar shell, marks this instrument
as active, shows the shared pending-consent sigil, and renders an explicit unbuilt placeholder. It
does not list Runes or references, reveal configuration provenance, validate a proposal, edit the
Codex, run `lychd bind`, mint a grant, or control a lease. [State owns the exact Bindings
boundary](../../state-of-the-work.md#bindings-instrument).

**Law.** The [Codex](../../sepulcher/codex.md) is the editable configuration authority. Bindings
may eventually project that intent and submit typed proposals through the Vessel; it must never
become a second settings store or a generic key-value editor. The
[Phylactery](../../sepulcher/phylactery/index.md) owns committed runtime records, the
[Oculus](../../sepulcher/extensions/oculus.md) owns evidence, the
[Mirror](../../sepulcher/extensions/mirror.md) owns Persona continuity,
[Context](../../adr/21-context.md) owns the active cognitive field, and the
[Weaver](../../sepulcher/extensions/weaver.md) owns workflow Patterns. Seeing a relationship grants
no authority over its owner.

> _“A binding worthy of the name does not hide the knot. It names both ends, the law between them,
> and the hand permitted to loosen it.”_

## Binding and Bindings

The singular **Binding** is the existing command rite: `lychd bind` reads validated Codex Runes and
transmutes their intent into generated host manifests. The plural **Bindings** is this intended
Altar instrument: a view of the declared relationships that the rite may later manifest. The page
does not replace the command, and the command does not make this page an editor.

This distinction also separates declaration from live reality. A Portal reference in the Codex is
not proof that the Portal is reachable. A Soulstone Rune is not a running Animator. An identity
reference is not a caller credential. An approval policy is not a live grant. A generated Quadlet
is not the Rune that caused it. Bindings must show those seams rather than flatten them into a
single green “saved” state.

## What Must Be Visible Before Mutation

Before Bindings earns any write control, its read model must be able to show:

- the owning Rune family and exact configuration source for every projected field
- named secret references without ever displaying secret values
- the declared value separately from observed runtime state
- validation failures at the field and owning-policy boundary
- the expected effect of a proposal: reload, rebind, restart, later run only, or no current effect
- a server-computed, typed diff projected before any accepted change
- the authority and consent needed for the effect, checked again when the effect occurs
- the generated projections affected by a lawful bind, without inviting direct edits to them

On narrow screens, these relations should render as stacked field/source/effect fragments, not a
wide settings grid. Meaning must survive without color, hover, or a permanently open side panel.

## The Knot Does Not Own Its Ends

Bindings may one day place a provider reference, privacy threshold, Persona name, or Weaver
default beside one another. Their proximity is convenience, not transferred ownership. Mirror
owns identity continuity; Weaver owns Patterns; Context owns the active cognitive field; Oculus
owns evidence; and Ward owns the remote authorization jurisdiction. In current matter, the
Dispatcher issues warm grants through the LeaseLedger, while the Orchestrator consumes lease truth
for admission closure and drain before physical transitions. Bindings may propose a relation; the
owning subsystem must judge its effect.

Nor may Bindings teach the Magus to edit generated systemd or Quadlet files. Those are projections
that the next binding rite may replace. Change begins in one validated source and proceeds through
one visible diff, one authority decision, and one observable effect.

For the system that exists now, begin before the knot is pulled:

> _Open [the Codex anatomy](../../sepulcher/codex.md#the-anatomy-of-the-book) and identify the one
> Rune family that owns the change._
