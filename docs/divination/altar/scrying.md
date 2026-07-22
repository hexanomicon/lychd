---
title: Scrying
icon: material/crystal-ball
---

# :material-crystal-ball: Scrying

**Purpose:** Scrying is the intended Altar jurisdiction for observing live and recent work.

**Current boundary:** Today the Altar exposes only an honestly marked Scrying route and unbuilt
shell. It does not yet provide a useful trace query, timeline, health read model, or native
observability backend. [State records the current Scrying
boundary](../../state-of-the-work.md#scrying-instrument). The surface below is intended design, not
useful behavior available now.

## Surface Shape

Scrying should begin as a focused live-work page:

- a list or drawer of active and recent Invocations
- a main pane for the selected run's status, logs, trace fragments, outputs, and approval waits
- stable links from a run to its generated [Reliquary](./reliquary.md) artifacts
- clear transitions to [Nexus](./nexus.md) when a run is blocked by routing, queues, or hardware pressure

Later versions may render active graph traversal directly: nodes lighting as work enters, pauses, retries, branches, or waits for consent. Multiple active runs may be organized with tab-like views when the page needs to compare concurrent motion without losing the single selected run.

## Instrument Runtime

Scrying is server-authoritative. Litestar, the Vessel, and the Phylactery own routing, validation, persistence, authorization, and consent. The normal Scrying surface is rendered as Jinja fragments, moved by HTMX, and kept alive by Server-Sent Events.

Svelte is allowed here only as an instrument island. If a view becomes too interactive for Alpine without reimplementing a framework by hand, the Altar may mount a Vite-compiled Svelte component into a server-rendered slot. That component owns local presentation mechanics: selection, pan/zoom, drag gestures, temporary layout, viewport memory, and draft edits.

It does not own truth. State-changing actions from a Svelte island return to the Vessel as typed intents and become authoritative only after server-side validation and, when required, Magus consent.

## Weaver Flow Lens

The Weaver extension is the first strong candidate for a Svelte island. Workflow observation is graph-shaped: steps, branches, joins, pauses, retries, memory injections, and approval waits are easier to inspect as an interactive node/edge surface than as a pile of fragments.

For that instrument, Svelte Flow (`@xyflow/svelte`) is the preferred renderer to evaluate. It may render Weaver snapshots and live SSE updates, including node status, branch evidence, waiting approvals, and selected-step detail. It should not replace the Altar shell, introduce SvelteKit routing, or move workflow mutation rules into the browser.

The working shape is therefore:

- **Altar shell:** Litestar, Jinja, HTMX, SSE
- **Simple local behavior:** Alpine
- **Graph-dense instruments:** Svelte islands
- **Weaver graph rendering:** Svelte Flow, projection-only
