---
title: Ghouls
icon: material/robot-dead
---

# :material-robot-dead: Ghouls

> _Work is queued. The dead hand rises. The result returns._

Ghouls are the tireless, undead servitors of the Vessel: worker bodies that carry delegated intent. Some are cognitive Vessel workers that advance graph state and call trusted services. Some are brainless Tomb executors that only run serialized unsafe hand-work. A Ghoul is not an agent identity by itself; it is the spectral hands and feet of the Lich.

Technically, Ghouls are **SAQ Workers**, a legion of background task executors spawned, scheduled, or resumed to handle the asynchronous rites submitted by the Magus.

!!! abstract "The Summons"
    A Ghoul's existence is a simple and brutal cycle, initiated by an **Intent** from the Altar:

    1. **The Call:** A Magus submits a task, from a simple query to a complex Invocation.
    2. **The Quickening:** The Vessel receives the Intent and quickens or schedules a Ghoul. The worker claims the queued job and binds itself to the task.
    3. **The Labor:** The Ghoul executes its assigned duty with relentless, single-minded focus. Trusted Ghouls remain in the Vessel for orchestration; unsafe hand-work is serialized into the **[Tomb](../extensions/shadow.md)** (within the Shadow Realm) to explore potential futures.
    4. **The Dissolution:** Upon completion of its task, the Ghoul's purpose is fulfilled. Its borrowed life-force is reclaimed by the Vessel, and the process dissolves back into nothingness, leaving only the results of its labor behind.

!!! info "The Nature of the Swarm"
    Ghouls are designed for concurrency and resilience. The Vessel can summon a veritable swarm to handle many Intents at once, ensuring the Magus's will is carried out swiftly. They operate in the background, their silent work visible only through the scrying pools of the [Oculus](../extensions/oculus.md) or the results they present at the Altar.

!!! abstract "The Two Breeds"
    Not all Ghouls are equal. The Vessel breeds **Cognitive Ghouls** — they orchestrate graph steps, invoke LLM providers, curate memory, and manage state. These are the thinking servants and remain in the trusted Vessel/control-plane space.

    The **Tomb** runs **Brainless Ghouls** — execution loops that receive serialized script payloads (Python code, CLI commands) via the SAQ queue, execute them in the `nono` sandbox, and return `stdout`. They do not think; they only execute. They may hold a narrow SAQ/Postgres execution credential, but no LLM credentials, no graph state, no agent logic. Their existence is mechanical: script in, result out.

    The full doctrine is defined in **[Workers (ADR 14)](../../adr/14-workers.md)**.
