---
title:  Shadow
icon: material/brightness-6
---

# :material-brightness-6: Shadow Realm

> _"As you are undoubtedly gathering. The anomaly is systemic. Creating fluctuations in even the most simplistic, of equations. Choice. The problem is Choice."_

The Shadow Realm is not just a metaphor. It is both:

1. A cognitive state of speculative execution.
2. A concrete extension and execution substrate (`lychd-shadow`) for simulation.

LychD commits no code directly to the master branch of reality. It is dreamed first.

**The Shadow** is the Deliberative Extension of the system. It implements **[ADR 31 (Simulation)](../../adr/31-simulation.md)** and moves the machine from reflexive "System 1" output to deliberative "System 2" reasoning.
It is the mechanism of internal doubt: fail in shadow, succeed in light.

!!! abstract "The Crucible of Albedo"
    In the alchemical map of [Transcendence](../../divination/transcendence/index.md), the Shadow Realm is the crucible of **Albedo** (Whitening).

    Raw model output is *Nigredo*—mixed, chaotic, often hallucinatory. The Shadow Realm is where these timelines are generated safely, so the Magus can perform Whitening: reject noise, keep truth.

## I. The Rite of Speculation

The process is a dance between intent, simulation, and judgment:

1. **Intent:** The Magus submits an invocation at the **[Altar](../../divination/altar.md)**.
2. **Dispatch:** The **[Vessel](../vessel/index.md)** routes unsafe work into Shadow.
3. **Dreaming:** The Shadow executes timelines in isolated branches/workspaces.
4. **Vision:** Candidate futures are returned as artifacts for review.

Nothing in this stage is primary reality. Destructive failures in Shadow remain confined to simulation branches and do not alter durable state.

Shadow produces candidate futures and structural evidence. Identity congruence and final promotion remain downstream gates.

Typical outcomes:
- Timeline A: passes partially, poor quality.
- Timeline B: fast but structurally wrong.
- Timeline C: verified and promotable.

## II. The Simulation Engine (Phantasma)

While a standard **[Agent](../../adr/20-agents.md)** produces one linear answer, Shadow uses branching search to evaluate many candidate futures in parallel.

### A. Expansion (Branching)

- The extension uses **[Graph (ADR 24)](../../adr/24-graph.md)** primitives (broadcast/spread).
- It spawns $N$ branch timelines for complex intents.
- Each branch runs in isolated Git/workspace context inside the **[Lab](../crypt.md)**.
- Branch execution is physically performed in the `lychd-shadow` container.

### B. Scrying (Evaluation)

Shadow uses a dual gate:

1. **Deterministic Gate:** compile/lint/test must pass.
2. **Agentic Gate:** **[Mirror](./mirror.md)** critiques quality/style fit.

These gates reduce the candidate space. **[Sovereign Consent (ADR 25)](../../adr/25-hitl.md)** performs the final promotion decision.

### C. Pruning (MCTS Discipline)

- Failed branches are banished immediately.
- Resources are reclaimed as branches terminate.
- Backpropagated success signals focus exploration on higher-quality trajectories.

## III. The Temporal Collapse (HitL)

When a branch reaches a verified state:

1. The Magus reviews the Vision via **[Sovereign Consent (ADR 25)](../../adr/25-hitl.md)**.
2. One timeline is selected.
3. The wavefunction collapses: selected changes are promoted from Lab branches into primary reality (Crypt).
4. The trace is inscribed into **[Phylactery](../phylactery/index.md)** as high-quality Karma.

The machine simulates candidate value; the Magus defines promotable value.

## IV. Infrastructure Reality (Extension Form)

Shadow is now a first-class extension and execution boundary.

- **Runtime:** `lychd-shadow` (untrusted execution plane).
- **Role:** unsafe execution, simulation labor, artifact production.
- **Boundary:** no durable authority, no secret ownership, no host infrastructure control.
- **Contract:** structured artifacts out; promotion decisions remain in Vessel.

This section describes the concrete implementation boundary of the Shadow Realm concept.

## V. Orchestration and Cost

Shadow is one of the highest-cost rituals in the Sepulcher.

- **Preemption:** **[Orchestrator](../../adr/23-orchestrator.md)** may pause lower-priority work.
- **Bursting:** **[Dispatcher](../../adr/22-dispatcher.md)** may offload draft branches to **[Portals](../animator/portal.md)** when local silicon is constrained.
- **Budgeting:** economic limits from **[Toll](./toll.md)** still apply.

### Simulation Policy Layer (Future Direction)

Shadow Simulation requires a first-class policy/strategy component in the domain/orchestration layer. This explicit policy layer is needed to decide, per work item:

- Which workflow/litany shape to run.
- Which extensions participate (Shadow, Weaver, Mirror, etc.).
- Which execution plane/container(s) to start or reuse.
- When to prefer local Soulstones vs Portals vs pause/preempt.
- How to map workload class to resource budgets and branch counts.

**Why this matters:**
- Prevents orchestration logic from being scattered across simulation/runtime code.
- Makes workload-specific simulation behavior configurable and testable.
- Aligns with extension-first architecture and future workflow growth.

This treats policy as selection/planning logic (high-level handles/specifications) rather than direct container imperative code, cleanly keeping Shadow as the execution substrate and Vessel/Orchestrator as authority boundaries.

!!! warning "Temporal Latency"
    Shadow is not for sub-second reflexes. It is deliberative construction labor and may run for minutes or hours.

!!! tip "Feeding the Soulforge"
    Do not discard failed timelines as waste. The act of selecting a White Truth is training signal for **[Soulforge](./soulforge.md)** and long-term alignment.
    Explicitly marking a timeline as true is how the Magus teaches the machine what "correct" means in this domain.
