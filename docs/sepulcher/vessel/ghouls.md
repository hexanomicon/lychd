---
title: Ghouls
icon: material/robot-dead
---

# :material-robot-dead: Ghouls

> _Work is queued. The dead hand rises. The result returns._

Ghouls are the tireless, undead servitors of the Vessel: worker bodies that carry delegated intent.
The implemented Ghouls are cognitive Vessel workers that advance graph state and call trusted
services. Brainless Tomb executors for serialized unsafe hand-work are the next trust-plane
topology, not current runtime wiring. A Ghoul is not an agent identity by itself; it is the spectral
hands and feet of the Lich.

Technically, Ghouls are **SAQ Workers**, a legion of background task executors spawned, scheduled, or resumed to handle the asynchronous rites submitted by the Magus.

!!! note "The run ghoul (v1)"
    In v1 the cognitive workers are not separate processes but **in-process ghouls** sharing the
    Vessel's event loop (Topology A: `QueueConfig.separate_process=False` and
    `SAQConfig.use_server_lifespan=False`, with startup owned by the application hook). Exactly one
    ASGI process is required while the live `RunEventBus` is process-local. Every workflow run is a
    SAQ job: `RunEngine.submit` enqueues `perform_run`, which is the only place a workflow graph
    executes. The **`RunLedger`** (the `run`/`step` tables) is the run's truth, and a semantic
    **`RunEvent`** bus carries its live trace to the Altar. See **[Workers (ADR 14)](../../adr/14-workers.md)**.

    Run jobs are enqueued with SAQ `timeout=0`, disabling the queue library's short default wall
    clock. The graph, model, and Orchestrator layers still apply their own meaningful bounded waits;
    this setting only prevents the broker from terminating ordinary long inference blindly.

!!! abstract "The Summons"
    A Ghoul's existence is a simple and brutal cycle, initiated by an **Intent** from the Altar:

    1. **The Call:** A Magus submits a task, from a simple query to a complex Invocation.
    2. **The Quickening:** The Vessel receives the Intent and quickens or schedules a Ghoul. The worker claims the queued job and binds itself to the task.
    3. **The Labor:** The Ghoul executes its assigned duty with relentless, single-minded focus.
       Trusted Ghouls remain in the Vessel. Unsafe hand-work must remain disabled until the planned
       **[Tomb](../extensions/shadow.md)** boundary exists; it must not execute inside the Vessel.
    4. **The Dissolution:** Upon completion of its task, the Ghoul's purpose is fulfilled. Its borrowed life-force is reclaimed by the Vessel, and the process dissolves back into nothingness, leaving only the results of its labor behind.

!!! info "The Nature of the Swarm"
    Ghouls are designed for concurrency and resilience. The Vessel can summon a veritable swarm to handle many Intents at once, ensuring the Magus's will is carried out swiftly. They operate in the background, their silent work visible only through the scrying pools of the [Oculus](../extensions/oculus.md) or the results they present at the Altar.

!!! abstract "The Two Breeds"
    Not all Ghouls are equal. The Vessel breeds **Cognitive Ghouls** — they orchestrate graph steps, invoke LLM providers, curate memory, and manage state. These are the thinking servants and remain in the trusted Vessel/control-plane space.

    The planned **Tomb** runs **Brainless Ghouls** — execution loops that receive serialized script
    payloads through a dedicated queue, execute them in the `nono` sandbox, and return bounded,
    untrusted results. They will hold a narrow execution credential but no LLM credentials, graph
    state, or agent logic. The Tomb unit, queue/profile, credential role, and loop are not
    implemented in v1.

    The full doctrine is defined in **[Workers (ADR 14)](../../adr/14-workers.md)**.
