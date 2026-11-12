---
title: Altar
icon: fontawesome/solid/dungeon
---

# :fontawesome-solid-dungeon: Altar

Bring a piece of work to the **Altar**, then follow it beyond the reply. You can keep a project's
concerns beside its conversation, inspect the evidence behind a result, read the score that guided
the Run, and examine any recorded change to the iron. Each instrument answers a different part of
that inquiry.

## Bring one Intent

Begin with [Summoning](../../summoning.md), including its four observations of the bound body
and first reply. Before starting services, read its [closure limitation](../../summoning.md#close-the-rite):
`lychd stop` currently refuses an active Vessel, so the trial needs a separately authorized
recovery plan. Summoning does not supply a working end-to-end start/stop procedure.

For startup and local access, follow [The Awakening](../../summoning.md#the-awakening). With the
Vessel running under that trial boundary, open the Altar in a dedicated profile on the same host:

```text
http://127.0.0.1:7134/
```

Before entering, retrieve the dedicated local credential in a private terminal with `lychd access`
and answer the browser's authentication dialog as described in
[The Awakening](../../summoning.md#the-awakening). Keep the password out of URLs and command lines.
The root opens **Orb**, with the Bridge dock on the left in a fresh wide layout. On a narrow
window, the edge chevron opens the dock. Saved dock preferences remain in use.
Choose **Bridge** in the masthead to open the full conversation workspace. On a fresh Phylactery,
choose **New Séance** in Bridge and offer a bounded Intent.
Answer an inline consent card only when the Run asks for judgment.

Keep the listener on literal loopback, with no ad hoc proxy, tunnel, or forwarding. The separate
[single-owner access candidate](../../deployments/tumbleweed/access.md) is an explicit qualification
experiment, not shared remote access. Loopback and the
fixed `magus:*` Sigil alone do not authenticate a caller. The separate credential proves local
possession; it supplies no remote person identity or hostile-browser isolation. The full current
boundary lives in [The Awakening](../../summoning.md#the-awakening); [State of
Work](../../state-of-the-work.md#altar-and-observability) records the delivered surface.

## Carry the Run with you

Follow one admitted conversation turn from your offered request to its result. Its **Run**
identity lets you find the same act in each instrument. The conversation, or séance, can hold
many such turns.

Each admitted turn opens a [Circle](./circle.md): one Invocation. Within that Circle, the
**casting** performs an exact **Scroll**, the workflow score; its Run keeps durable execution
identity. Keep that identity in view when changing instruments.

| What you need to establish | Instrument |
| --- | --- |
| What was offered, what judgment is pending, and what settled? | [Bridge](./bridge.md) |
| What did this conversation contain, and which words should we carry into later work? | [Séances](./seances.md) within Bridge |
| What can we draw, develop, organize and return to across conversations? | [Atlas](./atlas.md), including [Canvas](../../compositions/canvas/index.md) authoring |
| Which stations and paths does this exact Scroll permit? | [Loom](./loom.md) |
| What was observed about readiness or a physical transition? | [Nexus](./nexus.md) |
| Which Runs are before us, what evidence is arriving, and where does capture run out? | [Orb](./orb.md) |

The masthead orders **Bridge**, **Atlas**, **Loom**, **Nexus**, **Orb**, and **Applications**.
Bridge opens the full conversation workspace, with **Browse séances** for retained inspection.
Atlas opens the project catalogue, with **New canvas** and **Open Canvas →**. LychD's own Canvas
stays pinned first. **Applications** opens other admitted applications, including Scavenger market.
Hover, click, or keyboard focus opens the menu.

Atlas gives a larger undertaking continuity across conversations and Runs, and can begin before
either exists. Inside Bridge, a Circle gathers one Invocation. Its current form is a compact
per-turn Run disclosure: supplied status, complete identity, evidence and declared-score links,
and eligible cancellation. Circle is the Invocation-shaped pinnacle within Bridge; a composed
Circle workspace is not yet delivered.

Start with **Look into the Orb** beside a Bridge result. Keep the same Run identity as you inspect
capture limits and gaps, compare its pinned score in Loom, or follow an exact physical-transition
correlation into Nexus. The leaf guides explain each step. That shared identity keeps an
observation attached to the work that prompted your question.

For several Runs, open `/orb`. Its parallel field combines a paged catalogue with at most three
bounded live lenses on one canvas. Zoom or explicit detail controls reveal supplied Run, station,
occurrence, and record identities. Deeper subworkflow structure needs an identity from its owner;
the view cannot infer it.

Nexus inspection changes no lifecycle state. **Preview** is nonbinding; **Request transition**
performs a real maximum-priority mutation. Read the [Nexus guide](./nexus.md) before making that
request.

## Return to Bridge

Choose **Bridge** in the masthead to return to the last explicitly selected conversation in this
browser document. **Browse séances** opens the catalogue. The dock's **Open Séance** opens the
current conversation for inspection, and **Continue in Bridge** explicitly selects an inspected
conversation for live exchange.

## Keep Bridge beside the work

Use the named **Bridge** control at the work area's edge to open or collapse the panel. New layouts start
on the left at a compact width; valid saved side and width preferences remain in use. Drag its divider to
change its width, or focus the divider and use its arrow keys. The **⇄** control chooses the
other side. A wide window makes room beside the panel; a narrow window opens it as a
modal sheet with Escape and a return to the opener. Layout preferences may be remembered in this
browser; conversation drafts and unresolved requests retain their existing open-document boundary.

Switching instruments keeps the selected conversation. Collapsing Bridge does not cancel its
Run, submit a draft or approve a request. The context label identifies the work you are viewing;
it does not transmit the work to a model. Exact Bridge session, Run and consent links remain
valid, including links from Orb. Investigation and public-note focus stay distinct from the
ordinary conversation. Read [Bridge](bridge.md) for those operations and recovery boundaries.

## The surface and its owners

Execution belongs to the [Vessel](../../sepulcher/vessel/index.md), committed truth to the
[Phylactery](../../sepulcher/phylactery/index.md), and physical readiness to the Orchestrator.
The Altar projects those accounts so the Magus can inspect and act through their admitted seams.

The delivered interface is English-only and uses **LychD Dark**, with no locale selector or
palette override. Future [locale](../../adr/15-frontend.md#interface-locale-and-content-language)
and [palette](../../adr/15-frontend.md#canonical-appearance-and-bounded-palette-configuration)
contracts belong to the Frontend Covenant; interface choices preserve retained source content.

## Presentation direction

The graphite frame leaves black spatial surfaces to the work. Neutral primary actions, a quiet
purple instrument identity, cyan manipulation controls, and green observed activity have distinct
roles. Bridge gives the conversation room on its route and offers a compact composer beside
other work. Séances gives retained conversations room for reading. Atlas opens the project
catalogue and Canvas drawing boards. Loom reads as a declared score, Nexus as a readiness
inspection board, and Orb as an evidence field. The future
[Atlas memory map](atlas.md#the-shared-memory-map) describes how the instruments can refer to the
same retained knowledge.
Canvas's **Selection tools** unfold when ink or nodes are selected, or can be opened directly.
Identity and history unfold as needed, while uncertainty,
consent, capture limits, and physical consequences stay beside the choices they qualify.
[Frontend's reading hierarchy](../../adr/15-frontend.md#reading-hierarchy-and-visual-direction)
owns this shared design. Each instrument's **Reading direction** explains its current composition,
further targets, and a practical acceptance case.

Follow [Atlas's concerns and citations](atlas.md#reading-direction),
[Bridge's conversation and recovery](bridge.md#reading-direction),
[Orb's parallel evidence field](orb.md#reading-direction), [Nexus's preview and observations](nexus.md#reading-direction),
or [Loom's declared score](loom.md#reading-direction). Current controls and the boundaries of
graph expansion remain those described in the operating sections and [State of
Work](../../state-of-the-work.md#altar-and-observability).

Artwork supports the entrance rather than repeating behind work on every instrument. The existing
empty-Bridge scene has a retained [asset notice](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/assets/altar/NOTICE.txt)
and [generation prompt](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/assets/altar/working-altar.prompt.md).
They distinguish the generated Altar scene, the authorized character reference, and their terms.
The source distribution retains [third-party notices](https://github.com/hexanomicon/lychd/blob/main/THIRD_PARTY_NOTICES.md);
their custody does not require a permanent footer competing with the work.
