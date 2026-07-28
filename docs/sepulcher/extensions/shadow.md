---
title: Shadow
icon: material/brightness-6
---

# :material-brightness-6: Shadow Realm

_Status: doctrine ahead of code — the selectable `simulation` package contributes only a Rune
schema; the Shadow Composition and execution contract do not ship. Law:
[ADR 31](../../adr/31-simulation.md). Current truth:
[source map](./index.md#the-federation-of-fifteen)._

**Extension form:** Shadow is the possibility-lineage Domain invoked from Weaver Patterns. Graph
supplies fan-out, the Tomb executes unsafe payloads, Riddle evaluates, and promotion remains
external to the branch. Search strategies, lenses, workspace backends, and simulated-tool
providers may vary without creating a second workflow or live-effect authority.

> _"Choice is the fracture where probability enters the law."_

The Shadow Realm names two related things:

1. The Domain contract for speculative, non-authoritative branch lineages.
2. A planned Composition that may use the
   **[Tomb](../../adr/14-workers.md#2-the-doctrine-brain-in-the-vessel-hands-in-the-tomb)**
   execution substrate when a branch contains unsafe work.

**The Shadow** is the Deliberative Extension Domain of the system, governed by
**[ADR 31 (Simulation)](../../adr/31-simulation.md)**. It creates room for explicit alternatives,
measurement, and rejection. It does not prove a psychological “System 2,” require MCTS, or grant
the model a hidden faculty of doubt.

Shadow is also the present simulation-field of an active branch. To the Agent acting inside it, the branch is the current world: context, files, tools, traces, and feedback are all immediate. To the Sepulcher as a whole, that same world is still Vikalpa until measured and promoted. This distinction keeps the system honest: every experience inside Shadow may be operationally real while remaining ontologically untrusted.

!!! abstract "The Crucible of Albedo"
    In the alchemical map of [Transcendence](../../divination/transcendence/index.md), the Shadow Realm is the crucible of **Albedo** (Whitening).

    Raw model output is *Nigredo*—mixed, chaotic, often hallucinatory. The Shadow Realm is where these timelines are generated safely, so the Magus can perform Whitening: reject noise, keep truth.

## I. The Rite of Speculation

The process is a dance between intent, simulation, and judgment:

1. **Intent:** The Magus submits an invocation at the **[Altar](../../divination/altar/)**.
2. **Dispatch:** A Weaver Pattern establishes the branch lineage. Unsafe effects alone are routed
   through the **[Vessel](../vessel/index.md)** into **The Tomb**.
3. **Dreaming:** Graph fan-out and the selected search strategy produce candidates; Tomb executors
   run only serialized unsafe payloads in isolated workspaces.
4. **Vision:** Candidate futures are returned as artifacts for review.

Nothing in this stage is primary reality. Destructive failures in Shadow remain confined to simulation branches and do not alter durable state.

Shadow produces candidate futures and structural evidence. Identity congruence and final promotion remain downstream gates. In the Ouroboros, Shadow supplies the motion that will later return through Riddle, Mirror, Memory, and HitL; it does not decide what the motion means.

Typical outcomes:

- Timeline A: passes partially, poor quality.
- Timeline B: fast but structurally wrong.
- Timeline C: verified and promotable.

## II. The Simulation Engine (Phantasma)

While a standard **[Agent](../../adr/20-agents.md)** call returns one typed result, a Shadow Pattern
may evaluate multiple candidates sequentially or in parallel. Branch count, search method, and
physical workspace use are explicit policy choices.

### A. Expansion (Branching)

- The extension uses **[Graph (ADR 24)](../../adr/24-graph.md)** primitives (broadcast/spread) as
  the engine of **the Call**, opening movements within **the Flux** to navigate the **Possibility
  Space**.
- Each branch the Lich generates here is precisely **Vikalpa** — honest speculation: internally coherent, structurally plausible, and carrying no confirmed correspondence to reality. Vikalpa does not claim to be true. It exists to be judged. The Shadow Realm is the space where Vikalpa is held safely long enough for Viveka (the Dual-Gate) to determine which candidates have crossed into Pramāṇa and which are Viparyaya in disguise. See **[The Lich](../lich/index.md)** for the full cognitive taxonomy.
- For open-ended strategy work, Shadow may first run cheap, text-only idea branches through isolated operational lenses. These seed branches widen the pool without creating filesystem debris; only review-selected candidates become physical timelines.
- A bounded policy may spawn $N$ branch timelines for complex intents.
- Pure reasoning branches may remain typed graph state; only unsafe execution is physically
  performed in the `lychd-tomb` container.
- Filesystem-changing branches may receive a Jujutsu workspace in the `shadow/` region of the
  **[Lab (13)](../../adr/13-layout.md)**.
- Each unsafe job uses an isolated job-scoped directory and declares its artifacts.

### B. Scrying the branch (evaluation)

Candidate reduction may use several independent gates:

1. **Structural evidence:** Deterministic tests, linters, and outcome checks execute in the proper
   plane; the Tomb executes but does not judge.
2. **Riddle claims:** **[Riddle](./riddle.md)** owns calibrated evaluation and comparative claims.
3. **Mirror congruence:** **[Mirror](./mirror.md)** may score identity fit when the Pattern asks for
   it; congruence is neither correctness nor authority.

These gates reduce the candidate space. Live
**[Sovereign Consent (ADR 25)](../../adr/25-hitl.md)** or an eligible, explicit preauthorization
permits the owning promotion boundary to make the final decision.

### C. Pruning

- Failed branches become eligible for cleanup only after required evidence and provenance have
  been retained.
- The workspace/runtime owner reclaims resources according to lease and retention policy.
- A selected search provider may use MCTS, beam search, best-of-$N$, debate, or another bounded
  strategy. Its heuristic never becomes proof.

## III. The Temporal Collapse (HitL)

When a branch reaches a verified state:

1. The Magus reviews the Vision via **[Sovereign Consent (ADR 25)](../../adr/25-hitl.md)**.
2. One timeline is selected.
3. An authorized promotion owner applies the selected effect using the ordinary Snapshot,
   verification, and rollback law. Shadow supplies the candidate; it does not merge it.
4. The **[Phylactery](../phylactery/index.md)** records the decision and evidence. Eligibility for
   Karma is a separate Memory policy decision, not an automatic reward for being selected.

The machine simulates candidate value; the Magus defines promotable value.

## IV. Infrastructure Reality (Extension Form)

Shadow is a first-class Extension Domain in the doctrine and a designed execution boundary; its
general Composition is not delivered.

- **Domain:** Shadow owns possibility identity, branch lineage, and the rule that branches emit
  candidates rather than live effects.
- **Composition:** A Weaver Pattern owns the executable score.
- **Runtime:** `lychd-tomb` is one untrusted execution plane for unsafe payloads, not Shadow
  itself.

### The Doctrine: Brain in the Vessel, Hands in the Tomb

The **Shadow Realm** is speculative state and workspace topology, never a container. The **Tomb is
a brainless executor.** It does not run agent logic, graph state machines, or LLM provider calls.
It receives serialized script payloads (Python code, CLI commands) via the SAQ queue, executes them
in the `nono` sandbox, and returns untrusted `stdout`/`stderr` plus declared artifacts. Safe
planning, graph control, policy checks, and review packaging remain in the
**[Vessel](../vessel/index.md)**; only unsafe hand-work enters Tomb.

If code executing in the Tomb needs LLM reasoning, it routes back through the Vessel via the "Ask the Brain" protocol defined in **[Security (09)](../../adr/09-security.md)**. The Tomb never holds LLM credentials or communicates directly with providers.

This section describes the concrete implementation boundary of the Shadow Realm concept. The full doctrine is defined in **[Workers (14)](../../adr/14-workers.md)**.

## V. Orchestration and Cost

Shadow is one of the highest-cost rituals in the Sepulcher.

- **Priority:** The admitting Pattern and policy declare logical priority; the
  **[Orchestrator](../../adr/23-orchestrator.md)** alone governs physical readiness and
  preemption.
- **Providers:** The **[Dispatcher](../../adr/22-dispatcher.md)** resolves declared capabilities.
  Portal egress is never inferred merely because local silicon is constrained.
- **Budgeting:** Pattern budgets and any economic limits from **[Toll](./toll.md)** still apply.

### Simulation Policy Layer (Future Direction)

Shadow Simulation requires an explicit strategy contribution consumed by its Weaver Pattern. It
may decide, per admitted work item:

- Which branch/search strategy the already selected Pattern will use.
- Which optional evaluators or congruence gates the Pattern invokes.
- Which effect class each branch declares.
- Which capability requirements, budgets, and branch bounds the Pattern requests.

**Why this matters:**

- Prevents branch-strategy logic from being scattered across simulation/runtime code.
- Makes workload-specific simulation behavior configurable and testable.
- Aligns with extension-first architecture and future workflow growth.

This strategy cannot select a rival Weaver, start containers, choose an unadmitted Portal, or grant
itself authority. Weaver owns the Pattern, Dispatcher owns semantic grants, Orchestrator owns
iron, Ward owns policy enforcement, and the Tomb remains an execution substrate.

!!! warning "Temporal Latency"
    Shadow is not for sub-second reflexes. It is deliberative construction labor and may run for minutes or hours.

!!! tip "Feeding the Soulforge"
    Do not discard required failure evidence as waste. A governed curation Pattern may propose
    paired successes and failures as candidate material for **[Soulforge](./soulforge.md)**.
    Selection alone neither grants corpus eligibility nor explains why the Magus chose; factual
    claims retain their own evidence burden.
