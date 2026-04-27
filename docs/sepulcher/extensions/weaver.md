---
title:  Weaver
icon: material/state-machine
---

# :material-state-machine: Weaver

> _"An Agent is a single note. The Weaver is the composition. It binds reflex, memory, sequence, and pause into a coherent movement of thought across the silence of the Void."_

**The Weaver** is the Workflow Extension of the LychD system. It is the implementation of **[ADR 28 (Workflow)](../../adr/28-workflow.md)**—the executive function that governs stateful, multi-step reasoning.

While the **[Graph](../../adr/24-graph.md)** provides topology (nodes and edges), the Weaver provides **tempo, sequencing, preparation, and execution planning**. It governs movement between steps, coordinates the **[Long Sleep](../../adr/22-dispatcher.md)** during hardware or execution-plane transitions, and ensures each step is hydrated with the correct context and constraints.

The Weaver prepares and synchronizes the field of cognition. It does not determine truth, identity, or final promotion. Evaluation, consent, and durable authority remain separate responsibilities.

## 🎼 The Workflow

A workflow in LychD is a stateful graph definition registered via the Extension Context, not a static script.

```python
# A simple Workflow: Research -> Draft -> Review
@weaver.workflow(name="deep_research")
async def research_workflow(ctx: WorkflowContext, topic: str):
    # Step 1: The Scout (Parallel Spreading)
    sources = await ctx.step(
        agent="researcher",
        intent=f"Find sources for {topic}",
        tools=["browser_navigate"]
    )

    # Step 2: The Synthesis (Memory Weaving)
    draft = await ctx.step(
        agent="writer",
        intent="Synthesize these sources.",
        context={"sources": sources}
    )

    # Step 3: The Judgment (HitL)
    approved = await ctx.consecrate(draft)
````

A workflow defines the **shape of the work**, but not necessarily every execution choice. That distinction matters as workflows become more adaptive.

## 🧠 The Archivist (Memory Weaving)

The Weaver solves the "Amnesia Problem" of stateless agents. Before invoking a step, it performs **Memory Weaving**.

1. **The Scry:** It queries the **[Phylactery Archive](../../adr/27-memory.md)** for vectors, traces, and prior outcomes relevant to the current step.
2. **The Injection:** It retrieves relevant **Karma** and project-specific context and injects them into the Agent's **[RunContext](../../adr/21-context.md)**.
3. **The Result:** The Agent wakes with the relevant past already activated, rather than rebuilding context from zero at each step.

This makes workflows cumulative rather than forgetful.

## 🗺️ The Policy Layer (Execution Planning)

As workflows become more complex, the Weaver may consult an explicit **policy/planning layer** before execution. This layer does not replace the workflow. It determines **how a workflow should run for a given work item**.

Per work item, policy may decide:

* which workflow shape to use
* which extensions participate:

    * **[Shadow](./shadow.md)**
    * **[Mirror](./mirror.md)**
    * **[Scout](./scout.md)**
    * or others
* which execution plane to use or reuse
* whether to prefer:

    * local **Soulstones**
    * remote **Portals**
    * pause / preempt / defer behavior
* how to map workload class to:

    * branch count
    * resource budget
    * simulation depth

This keeps orchestration logic from being scattered across runtime glue, simulation code, and extension-specific decision branches.

The policy layer is:

* **selection and planning logic only**
* not direct container control
* not a security boundary
* not a secret-bearing authority surface

Final execution authority remains with the **[Vessel](../vessel/index.md)** and the **[Orchestrator](../../adr/23-orchestrator.md)**. **[Shadow](./shadow.md)** remains the execution substrate for unsafe or speculative work.

## ⏸️ The Fermata (Stasis & Resilience)

The Weaver is the guardian of the **Stasis Protocol**.

* **Persistence:** Every transition between steps is committed to durable state. If the system fails during Step 2, the workflow resumes at Step 2, not Step 0.
* **Hardware Pacing:** If one step uses **[Vision](../../adr/36-vision.md)** and the next uses **[Audio](../../adr/37-audio.md)**, the Weaver pauses the workflow while the **[Orchestrator](../../adr/23-orchestrator.md)** performs the Coven Swap. The mind waits for the body without losing continuity.
* **Execution-Plane Continuity:** If a later step must move from trusted control-plane logic into untrusted **[Shadow](./shadow.md)** execution, the Weaver preserves continuity across that transition as well.

The result is a workflow that survives delay, reconfiguration, and interruption without degenerating into procedural chaos.

## 🕵️ The Censor (Data Hygiene)

When a workflow involves external **[Legion Nodes](../../adr/42-legion.md)** or **[Portals](../../adr/22-dispatcher.md)**, the Weaver activates the **Censor**.

* **Scrubbing:** It scans outgoing artifacts for sensitive patterns defined by the system's security and identity posture.
* **Anonymization:** It replaces sensitive entities with safe placeholders before they leave the Sepulcher.
* **Re-Identification:** When results return, the Weaver can rebind internal meaning without exposing raw internal truth to the outside world.

This allows workflows to collaborate beyond the local machine without dissolving the **[Sovereignty Wall](../../adr/09-security.md)**.

## 🔀 Synchronization and Flow Shape

The Weaver governs the rhythm of multi-step reasoning through the primitives supplied by the graph layer.

* **Sequential Flow:** ordered, dependent steps
* **Broadcasting:** the same input is sent to multiple specialists
* **Spreading:** a collection is fanned out into parallel sub-work
* **Join / Reduce:** parallel results are recombined into one verified continuation
* **Deferred Pause:** work may sleep while waiting for:

    * hardware transition
    * human approval
    * remote peer response
    * expensive background labor

This makes the Weaver the executive planner of movement rather than the owner of meaning.

## 👁️ The Visible Score

The Weaver produces a visible structure of work.

* **Graph Visibility:** active workflows can be rendered as Mermaid diagrams or similar execution views.
* **Step Visibility:** the Magus can see:

    * which step is active
    * which branch is waiting
    * which memory was injected
    * where the workflow paused
* **Operational Clarity:** this turns orchestration from a hidden implementation detail into an inspectable surface at the **[Altar](../../divination/altar.md)**.

!!! tip "Execution Planning Without Drift"
As simulation, orchestration, and extension participation become more adaptive, keep planning logic in the Weaver's policy layer rather than scattering it across Shadow, runtime adapters, or graph step implementations. The workflow should describe the work. The policy layer should decide how to run it. The Orchestrator and Vessel should decide what may actually happen.
