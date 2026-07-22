---
title: Altar
icon: fontawesome/solid/dungeon
---

# :fontawesome-solid-dungeon: Altar

> _"Altus - the high place. From here, the Magus acts as the Arbiter: intent is offered, candidate futures are weighed, and only witnessed truth is allowed to harden."_

Access the Altar at **`http://localhost:7134`**.

The Altar maps the instruments; [State of the Work](../../state-of-the-work.md) is the sole record
of which can answer now.

The first screen (index) is **the Bridge**: a full-page terminal-chat surface where the Magus speaks his Intent and the Vessel resolves it into the proper rite. It is both the captain's bridge of the Sepulcher and the bridge between Magus and Machine.

A simple question may return a direct answer. A deeper request may become a Ghoul job, Weaver workflow, Scrying stream, Reliquary artifact, Nexus routing concern, or approval wait.

## The Six Instruments

The running Altar is organized around six instruments:

- **Altar:** offer Intent from the Bridge.
- **[Scrying](./scrying.md):** observe live workflows, logs, traces, and approval waits.
- **[Nexus](./nexus.md):** inspect orchestration, queues, Covens, Portals, and hardware pressure.
- **[Loom](./loom.md):** browse and design Weaver workflow Patterns.
- **[Reliquary](./reliquary.md):** inspect artifacts, outputs, reports, and blessed results.
- **[Bindings](./bindings.md):** manage user-facing settings, provider references, policy surfaces, and preferences.

These names form the Altar's navigation map.

## The Bridge

The Bridge is the Altar's default chamber. Its main surface holds the transcript, active output, worker responses, approval prompts, and the input where Intent is offered.

Natural language is the primary interface. The Magus describes the desired outcome; the Vessel resolves the Intent behind the surface through typed handling, Dispatcher policy, Weaver Patterns, and server-side validation.

The left rail belongs to the current Altar session rather than global navigation. It groups local surfaces such as:

- **Conversation History:** past conversations and Invocations.
- **Session Settings:** temperature, behavior preferences, and other controls scoped to the current session.
- **Pinned Context:** selected files, notes, memories, or artifacts brought into the current Intent field.
- **Coven Request:** a lightweight way to request a different Coven, Animator, or capability for this session.

Coven control is deliberately limited here. The Altar may show the active Coven or allow a request, but deep availability, queue pressure, warming, sleeping, and manual intervention belong in the [Nexus](./nexus.md). If a requested Coven is occupied by background work, Nexus is where the Magus inspects the tradeoff.

A contextual inspector may appear when a selected message, artifact, approval, worker, log line, or branch needs detail. It is a detail surface, not a second dashboard.

!!! abstract "The Sanctum of Interaction"
    The Altar is not a static page, but a living conduit. Its surface shifts and updates in real-time to reflect the Lich's inner state. Its core functions are:

    1. **The Offering Plate (Input):** This is where you submit **Intents**. The Altar receives *Desire* rather than hand-written implementation. ("Refactor this module," "Analyze this log," "Plan the deployment.")
    2. **The Scrying Threshold (Observation):** When Intent becomes active work, the Altar exposes enough state to follow the rite and opens the path to [Scrying](./scrying.md), where the live run, logs, traces, and approval waits become inspectable.
    3. **The Judgment Seat (Consecration):** When the Ghouls return from the **[Shadow Realm](../../sepulcher/extensions/shadow.md)** with potential timelines, they present them here.

!!! info "The Collapse of the Wavefunction"
    This is the Altar's most critical purpose.

    The Lich may present three different implementations of a feature.
    - *Timeline A:* Elegant but incomplete.
    - *Timeline B:* Functional but ugly.
    - *Timeline C:* The hallucinations of an unmeasured oracle.

    At the Altar, you perform the **Consecration**. You select, edit, and bless.

    By choosing one timeline you collapse the alternatives: the chosen path is written to disk and recorded in the **[Phylactery](../../sepulcher/phylactery/index.md)** as Karma; the rejected paths are discarded (their traces may be kept for learning). Your selection is the external judgment the daemon cannot perform on itself — the act the [cognitive map](../../sepulcher/lich.md) calls **Viveka**.

!!! tip "Spectral Threads (Server-Sent Events)"
    The Altar maintains a constant, ethereal connection to the Vessel. Through **Server-Sent Events (SSE)**, the thoughts of the Lich are pushed to your glass in real time. You watch the daemon think without refreshing the page.
