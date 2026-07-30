---
title: Loom
icon: material/vector-polyline
---

# :material-vector-polyline: Loom: The Visible Score

The **Loom** is a read-only browser for exact published **Pattern** revisions. It exposes the
Weaver-authored possibility: a declared semantic score with immutable manifest identity. It does
not execute, edit, publish, or follow a live Run.

## Composition, Pattern, Loom, Invocation

- A **Pattern** is the immutable workflow score identified by `pattern_id`, `revision`, and
  `digest`.
- The **Loom** projects that score.
- An **Invocation**, shown elsewhere as a Run, performs a Pattern.

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

For the selected Pattern, confirm:

- header: `title`, `description`, `pattern_id@revision`, and publication `published`;
- **Semantic score**: station count, permission count, and each node's `label`, `key`, `kind`, and
  permitted next station;
- **Immutable identity**: `checkpoint`, 64-character `digest`, `trigger`, and the plain-text
  Mermaid `source`.

Choose **Reveal** or **Hide** under **Diagram lens** for the optional static diagram. The semantic
score remains primary. The diagram does not highlight a live node or subscribe to execution.

When Orb opens Loom with `?run={run_id}`, Loom keeps **Return to Run in Orb** only if that Run's
pinned manifest is exact and its Pattern id and revision match the displayed score. Selecting
another Pattern drops the query. `run` is review context, never part of Pattern identity.

## The Designed Map

No Portfolio, Composition hierarchy, node inspector, live occurrence overlay, nested Pattern,
Suite, draft, or editor map is delivered. A node with kind `delegate` receives a distinct glyph;
that mark does not prove a provider-backed runtime executed.

## Charcoal, Law, and Publication

The current Loom shows only `published` revisions. There is no charcoal candidate, layout document,
**Propose**, **Run**, **Publish**, drag, connect, or mutation action.

## Before the Loom May Accept Executable Drafts

Executable drafts are outside the current contract. Loom cannot change the registry, revise a
manifest, migrate a checkpoint, invoke a Pattern, or execute a Suite.
