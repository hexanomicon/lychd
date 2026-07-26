---
title: Altar
icon: fontawesome/solid/dungeon
---

# :fontawesome-solid-dungeon: Altar

The **Altar** is LychD's local web surface. Its accepted architecture is a static Svelte 5/SvelteKit
client projecting generated Litestar API and semantic event truth. Litestar serves its compiled
fallback and remains the sole production authority. Its conversational instrument is the
**Bridge**. The navigation also names Nexus, Loom, Scrying, Reliquary, and Bindings, but a visible
door is not proof that the instrument behind it is complete. [State of the
Work](../../state-of-the-work.md#altar-and-observability) owns what can answer now.

!!! danger "Temporary local-browser boundary"
    Before using the Altar, use a dedicated browser profile on the same host, keep the listener on
    literal `127.0.0.1`, and do not publish, reverse-proxy, tunnel, or port-forward its port. Do not
    enable the SAQ UI or open `/schema/scalar`. Loopback and the fixed `magus:*` Sigil are not caller
    authentication or browser-origin isolation. Follow the canonical [browser and bind
    boundary](../../state-of-the-work.md#local-browser-bind-boundary) and the full warning in [The
    Awakening](../../summoning.md#the-awakening).

> _“At the high place, Intent is offered, truth is witnessed, and judgment returns to the hands
> that must bear it.”_

The glass is a projection, never a second mind or source of authority. Live execution remains in
the [Vessel](../../sepulcher/vessel/index.md) and committed truth in the
[Phylactery](../../sepulcher/phylactery/index.md); where a supported flow asks, the Altar carries
one typed consent or refusal intent back into that body. Svelte owns presentation mechanics only.

## The doors that answer now

Three instruments have useful but bounded implementations:

- **Bridge — conversation and consent.** It supports local sessions, a New Séance action, message
  submission, pending consent cards and decisions, session inspection, and per-run process-local
  event streaming. It does not provide durable cross-process delivery, a general multi-approval
  round, or a continuous feed of the Lich's thoughts. [Current Bridge
  boundary](../../state-of-the-work.md#bridge-surface)
- **[Nexus](./nexus.md) — orchestration projection.** It renders Coven state, transition plans,
  process-local swap tickets, and settled outcomes. It is not yet a general resource, queue, VRAM,
  or hardware-pressure dashboard. [Current Nexus
  boundary](../../state-of-the-work.md#nexus-transition-board)
- **[Loom](./loom.md) — workflow projection.** It renders diagrams from the fixed workflow registry
  and exposes their plain-text Mermaid source. It is a viewer, not a general Weaver editor or
  workflow-mutation surface. [Current Loom
  boundary](../../state-of-the-work.md#loom-workflow-views)

## The doors still being shaped

These routes preserve the intended instrument map, but each currently opens an honestly marked
unbuilt shell:

- **[Scrying](./scrying.md)** has no useful trace query, timeline, health read model, or native
  observability backend yet. [Current Scrying
  boundary](../../state-of-the-work.md#scrying-instrument)
- **[Reliquary](./reliquary.md)** has no artifact upload, byte custody, authorized retrieval,
  retention, or provenance backend yet. [Current Reliquary
  boundary](../../state-of-the-work.md#reliquary-instrument)
- **[Bindings](./bindings.md)** has no useful binding inventory, grant control, lease control, or
  mutation backend yet. [Current Bindings
  boundary](../../state-of-the-work.md#bindings-instrument)

## The observing boundary

The native **Oculus** is LychD's intended evidence plane and future Altar-facing observability
surface. It does not yet provide native ingestion, a durable query/read model, retention, or a
working Svelte Scrying projection. [Current Oculus
boundary](../../state-of-the-work.md#native-oculus)

**Phoenix** remains an optional Arize-owned external Eye. LychD does not require it for Oculus and
does not currently prove application trace export to it. [Current Phoenix
boundary](../../state-of-the-work.md#phoenix-eye)

## Enter through the Bridge

After the four observations in [Summoning](../../summoning.md) agree on this host—and only while the
temporary browser boundary above holds—open:

```text
http://127.0.0.1:7134/
```

The bare root redirects to `/bridge`. On a fresh Phylactery, choose **New Séance**, offer one
bounded Intent, and answer an inline consent card only if the run asks. If the page does not answer
or first life is incomplete, close it and return to [The
Awakening](../../summoning.md#the-awakening); do not weaken containment to make it work.

> _Enter by the **Bridge**. Offer one bounded Intent. Witness what the body returns._
