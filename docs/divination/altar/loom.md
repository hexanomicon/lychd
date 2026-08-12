---
title: Loom
icon: material/vector-polyline
---

# :material-vector-polyline: Loom: The Visible Scroll

The **Loom** is a read-only browser for exact source-registered **Pattern** revisions—the immutable
**Scrolls** read by Spellweaver. It exposes each declared station and permitted edge under one
manifest identity. In the future grammar, each semantic station places an exact **Spell** contract;
the current manifests do not yet carry that independent identity. Loom does not execute, edit,
publish, teach, or follow a live Run.

## Composition, Scroll, Loom, casting

- A **Scroll** is one immutable Pattern revision identified by `pattern_id`, `revision`, and
  `digest`.
- A **Spell** is one independently named semantic action; one Scroll-local station places it.
- The **Loom** projects that Scroll.
- An **Invocation** opens a Circle; casting performs the Scroll within it; the Run carries durable
  ledger truth.

A station or permission states what the published score allows; it is not evidence that a Run
entered that station or completed that edge.

## What the Loom renders now

Open:

```text
http://127.0.0.1:7134/loom
```

The current catalogue contains `bridge_chat@1` and `delegated_rite@1`. The rail shows each Pattern
title and `pattern_id@revision`. `/loom` selects the catalogue default and replaces the URL with
its exact route, currently `/loom/bridge_chat/1`. Browser deep links require both id and revision:
`/loom/{pattern_id}` is not accepted.

For the selected Scroll, confirm:

- header: `title`, `description`, `pattern_id@revision`, and the current UI label `published`;
- **Semantic score**: station count, permission count, and each node's `label`, `key`, `kind`, and
  permitted next station;
- **Immutable identity**: `checkpoint`, declared `entry` station, reviewed `implementation`
  revision, 64-character `digest`, `trigger`, and the plain-text Mermaid `source`.

The source links use `/api/v1/loom/source/patterns/{pattern_id}/{revision}`. Current-revision
convenience source uses `/api/v1/loom/source/workflows/{workflow}`. Keeping source below this longer
namespace leaves every legal `/api/v1/loom/{pattern_id}/{revision}` identity available, including a
revision literally named `source`.

Choose **Reveal** or **Hide** under **Diagram lens** for the optional static diagram. The semantic
score remains primary. The diagram does not highlight a live node or subscribe to execution.

When Orb opens Loom with `?run={run_id}`, Loom keeps **Return to Run in Orb** only if that Run's
pinned manifest is valid and equal in full to the registered score. Matching only its digest,
Pattern id, or revision is insufficient. Selecting another Pattern drops the query. `run` is review
context, never part of Pattern identity.

## The Designed Map

No Portfolio, Composition hierarchy, independent Spell catalogue, compatibility negotiation,
teaching surface, node inspector, live occurrence overlay, nested Pattern, Suite, draft, or editor
map is delivered. A station with kind `delegate` receives a distinct glyph; that mark does not
prove a provider-backed runtime executed or establish an independent Spell contract.

A future grey Spell placement belongs only to an inert candidate/resolution report with a redacted
status such as missing contract, missing implementation, incompatible, unauthorized, or revoked.
The whole Scroll must remain `castable=false`; no grey placeholder may enter the executable Graph.

## Renderer admission

No graph editor or XYFlow dependency is delivered. The Altar remains Svelte; a future Loom
renderer is a replaceable projection behind framework-neutral TypeScript views of validated Scroll
snapshots and mutation-intent contracts, not a reason to move Pattern truth into a component store
or reopen the frontend by preference.

XYFlow is the admitted candidate for the one DOM renderer Loom shares with [Orb](./orb.md), under
the [Frontend Covenant's lifecycle gate](../../adr/15-frontend.md#decision-lock-and-reopening-gate).
A released candidate must use only public APIs, show no retained heap growth after repeated
replacement and forced collection on every supported engine, and preserve one authority-derived
semantic score through drag, keyboard, resize, selection, connect, reconnect, delete, rejection, and
resync. Renderer arrays and geometry remain drafts. Failure rejects the dependency; only matched
evidence that Svelte cannot satisfy the whole Altar contract while a replacement can is evidence to
reopen the framework.

Loom is an editor at editor scale. `bridge_chat@1` places five stations over six permitted edges,
including a self-edge and a diamond; `delegated_rite@1` places three. Both stay in the tens to low
hundreds under any admitted Suite grammar, so a DOM-node renderer is the fit. A
dense engine would cost Loom the drag, connect, reconnect, and handle grammar it exists to provide,
and would supply no accessible twin.

Two gates stand between that renderer and an editing Loom, and neither is a renderer defect. The
served score carries no position and the Scroll grammar declares no layout document, so until
authority owns layout and mutation intent, Loom projects a computed layout and admits no drag.
XYFlow also exposes no keyboard path to create a connection, because its connection handles are not
focusable; Loom owns that path above the renderer rather than shipping an editor its keyboard twin
cannot operate.

## Charcoal, Law, and Publication

The current Loom shows only source-registered revisions and labels them `published`; that label is
not evidence of a durable publication store. There is no charcoal candidate, layout document,
**Propose**, **Run**, **Publish**, drag, connect, or mutation action.

## Before the Loom May Accept Executable Drafts

Executable drafts are outside the current contract. Loom cannot change the registry, revise a
manifest, migrate a checkpoint, invoke a Pattern, or execute a Suite.
