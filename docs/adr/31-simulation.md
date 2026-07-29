---
title: 31. Simulation
icon: material/source-branch
---

# :material-source-branch: 31. Shadow Simulation and the Branch Reaper

!!! abstract "Context and Problem Statement"
    One model call produces one typed result and cannot by itself establish which alternate action
    would have performed better. Complex architectural work benefits from explicit candidate
    generation, isolated execution, measurement, and review. This is an operational need for
    branching and evidence, not a claim about an absent psychological faculty.

    Simulation also creates temporary workspaces, artifacts, traces, and candidate records. These
    require explicit retention and cleanup. **[Memory (27)](27-memory.md)** independently decides
    which evidenced traces become eligible memory; Shadow does not crystallize every interaction
    or own general vector decay.

## Requirements

- **Explicit Deliberation:** Implementation of a bounded candidate/evidence loop. MCTS,
  best-of-$N$, beam search, debate, or another search provider may guide it; no one heuristic is
  constitutional.
- **Phantasma Expansion (Branching):** Support for generating $N$ sequential or parallel future
  states, each carrying distinct branch identity and isolated effects.
- **Lens-Separated Seeding:** Support for cheap, text-only divergent strategy generation through independent operational lenses before spending Lab workspaces on physical branches.
- **The Shadow Realm Topology:** Pure reasoning branches may remain typed graph state. Branches
  with filesystem effects use isolated **[Lab (13)](13-layout.md)** workspaces; Jujutsu is the
  native workspace provider.
- **Measured evaluation:** Deterministic predicates, **[Riddle (34)](34-evaluation.md)** claims, and
  optional **[Mirror (32)](32-identity.md)** congruence remain separately attributed.
- **Metabolic Pruning (The Reaper):** A cleanup protocol releases branch-owned resources only
  after required evidence and provenance are retained. It does not own Memory pruning.
- **Transactional Convergence:** Promotion packages one eligible branch for the ordinary
  Snapshot, verification, HitL, and effect-owner law; Shadow never merges on its own authority.
- **Policy-Governed Promotion:** Mandatory routing of branch collapse through **[Codex (12)](12-configuration.md)** autonomy policy and **[HitL (25)](25-hitl.md)** so preauthorization is explicit and high-stakes promotion remains human-gated.
- **Resource Declaration:** The Pattern declares branch, token, time, artifact, and capability
  budgets. Dispatcher and Orchestrator retain semantic and physical authority.

## Considered Options

!!! failure "Option 1: Linear Chain of Thought (CoT)"
    Relying on the model to "think step-by-step" in a single long response.
    - **Cons:** **Hallucination Propagation.** A single logic error in step 2 is treated as "fact" for step 10. There is no mechanism to "backtrack" or "test" a thought before it is manifested. It creates a massive, noisy log of unverified junk.
    - **Metabolism:** No mechanism for cleaning up the internal monologue once the task is finished.

!!! failure "Option 2: Parallel Sampling (Best-of-N)"
    Generating N responses and selecting the "best" based on log-probabilities or a simple judge agent.
    - **Cons:** **Shallow Verification.** It samples different ways to *say* things, but does not
      *do* anything. It cannot establish whether code compiles or whether a research path is a dead
      end. It consumes $N$ times the tokens without adding physical evidence.

!!! success "Option 3: Governed Branch Lineage and Metabolic Pruning"
    Using a Weaver Pattern, Graph fan-out, optional search providers, isolated Jujutsu workspaces
    for effectful branches, independent evaluators, and a resource-owning Reaper.
    - **Pros:**
        - **Explicit Alternatives:** The system compares multiple paths against declared evidence.
        - **Substrate Health:** Reclaims branch-owned disk and runtime resources under retention law.
        - **Authority Clarity:** Search, evaluation, identity congruence, promotion, and Memory
          remain separate offices.

## Decision Outcome

**Shadow Simulation and the Branch Reaper** are adopted as the possibility-lineage Domain and its
cleanup discipline. This architecture permits bounded alternatives while keeping their effects
isolated and their evidence attributable. “System 2” remains an explanatory analogy, not a
delivery or consciousness claim.

Shadow is the cognitive fluctuation engine, not the identity authority. It generates and tests candidate realities, but it does not define Self and cannot self-authorize promotion.

For the Agent inside a branch, simulation is the present working world: the active context, filesystem state, tool surface, and execution trace in which that Agent can perceive and act. The boundary is ontological, not experiential. Shadow may be the Agent's local now, but it remains unpromoted Vikalpa relative to the Crypt until the gates measure it and the Magus or Vessel policy authorizes collapse.

Shadow therefore feeds the Ouroboros without owning it. It supplies motion and candidate reality; Weaver preserves motion through time, Riddle measures it, Mirror binds identity, and Memory stores the residue. Treating Shadow as final identity would turn simulation into hallucinated sovereignty.

### 1. The Phantasma Expansion (Branch Topology)

The system utilizes the parallel primitives of the **[Graph (24)](24-graph.md)** to generate
divergent timelines. This is the application of **Phantasma** (Generative Imagination): **the
Call** actively opening movements within **the Flux** to navigate the **Possibility Space**
without making permanent changes to reality.

In the cognitive taxonomy mapped in the **[Lich](../sepulcher/lich/index.md)**, these candidate
branches are precisely **Vikalpa** — speculative modifications that are internally coherent but
carry no confirmed correspondence to reality. They do not claim to be true. They are honest
hypotheses, held in isolation long enough to be judged. Shadow Simulation deliberately amplifies
Vikalpa within a substrate where failure is contained and budgeted, and truth is measured from
outside the generation process.

When a high-stakes intent (e.g., "Refactor the persistence layer") is submitted:

- **The Casting:** The intent is processed into $N$ divergent strategies. These strategy seeds are
  ordinary planning inputs, not the memory dynamic called **the Seed**.
- **The Workspaces:** A strategy that needs filesystem effects may receive a Jujutsu workspace such
  as `jj workspace add shadow/branch_<ID> -r @` under the
  **[Lab (13)](13-layout.md)**. Pure reasoning branches remain typed graph state and create no
  workspace. Jujutsu provides tracked working-copy isolation; it does not eliminate all process,
  port, shared-database, or external-effect races.
- **The Labor:** **[Ghouls (14)](14-workers.md)** dispatch only declared unsafe execution payloads
  (code, tests, linters) to the Tomb via SAQ. The Vessel retains Pattern and graph state.
- **The Observation:** The Agent observes the *physical outcome* of its dream (e.g., "The test failed in Branch B"). It can then decide to "Prune" the branch or "Backtrack" to a previous node in the tree.

Each branch is an active task modification (a candidate timeline) that exists long enough to be tested, scored, and dissolved if needed. In cognitive terms, branches are the live modifications under comparison. Shadow is therefore fluctuation-first: it maintains possibility space without claiming ownership of results.

Shadow distinguishes three branch strata:

1. **Idea branches:** cheap, text-only Vikalpa produced by divergent strategy seeding. They expose the shape of possible approaches but do not touch the Lab.
2. **Shadow branches:** typed candidate lineages. Effectful code branches may additionally receive
   a physical Jujutsu workspace in the Lab; text-only branches need not.
3. **Promotion candidates:** verified branches packaged as Visions for Vessel policy and HitL collapse. They are no longer merely interesting; they have earned measured evidence.

### 1.1 Lens-Separated Seeding

Before spending filesystem, queue, or VRAM budget on physical timelines, Shadow may run an inexpensive seed pass that forces strategy diversity. The same intent is routed through several independent seed invocations using operational lenses such as lifecycle steward, rollback sentry, dependency minimalist, security ward, cost governor, outage operator, or migration cartographer. These lenses are not Personas and not claims of expertise. They are bounded distortions that make different parts of the possibility space visible before the Lab pays for a real branch.

The seed pass has two strict laws:

- **Expansion isolation:** each seed invocation receives the original intent and one lens, but does not read sibling outputs until the join. This prevents early seed text from narrowing later seed text.
- **Separated expansion and review:** expansion runs return typed candidate strategies only. Review runs classify related paths, assign heuristic value, flag hazards, and choose which candidates merit Lab execution. No single seed run both opens and judges the candidate space.

Only candidates retained by this review pass deserve physical Shadow branches. In this topology, lens-separated seeding widens Manas without multiplying Lab debris, while the later Dual-Gate still decides what is true. A clever idea branch is not Pramāṇa; it is merely Vikalpa selected for measurement.

**Feasibility before the Lab pays.** Among the review pass's duties is a precondition reading. Before a candidate earns a physical branch, the review weighs the `required_state` each strategy presupposes against the `observed_state` hydrated from context, using the same validator vocabulary the autopsy records downstream (see §3 and **[Agents (20)](20-agents.md)**). This reading is carried by the existing expansion-to-review separation, **not** by a separate pre-Seed chokepoint. An impossible, contradicted, or unwitnessed premise becomes one reviewed candidate among many — flagged, scored low, and withheld from the Lab — rather than a veto that strangles the intent before any branch can witness the boundary. Determination may withhold on this evidence; Expansion (strategy seeding, rationale) may only widen the seed field and never blocks. This is the discipline that keeps a feasibility reading from hardening into an officious agent that overwrites a valid Magus choice: the right to say "impossible" is earned by measurement, not asserted by hesitation.

When a premise is neither confirmed nor refuted by the context at hand, the review may spawn a **bounded inquiry** — a child Agent dispatched against *one named question*, not a feeling, carrying an explicit retrieval budget and stop condition. It has three honest exits: **resolved** (the premise is grounded and seeding proceeds), **refuted** (a `precondition_miss` or contradiction is recorded and routed into the Truthful Dead End shape of §3), or **unknown after exhausted retrieval** (escalated to **[HitL (25)](25-hitl.md)** as a typed bottleneck). On the third exit the truthful non-answer is itself the Pramāṇa — Buddhi refusing to mint Viparyaya — and the Magus's testimony, if given, is its external grounding. The inquiry never blocks on its own fatigue; mere model hesitation is not a refutation, and the boundary must still be witnessed.

!!! note "Where Feasibility Ends and Rationale Begins"
    Two lines that were once left unset are now settled. **(a) Role separation.** The feasibility reader may only *withhold* branches (a subtractive act); the rationale seeder may only *append* lens instructions (an additive act). These are two distinct **[Postures (ADR 20)](20-agents.md)** and are never combined in one run: no single invocation both withholds a candidate and seeds new rationale. **(b) Trust threshold.** An exhausted retrieval earns the standing of **Pramāṇa** rather than mere fatigue when the Solvable-Control false-positive rate — the **[Riddle/Evaluation (34)](34-evaluation.md)** `over_refusal_rate` measured on paired controls — falls below the **[Codex (12)](12-configuration.md)** threshold. Until that rate is below threshold, the inquiry escalates to **[HitL (25)](25-hitl.md)** rather than self-authorizing a withhold on weak evidence.

### 1.2 Shadow Roles: Expansion, Determination, Neutrality

Shadow Simulation contains multiple roles that must remain distinct:

- **Expansion (oscillation):** branch generation, strategy seeding, retrieval/tool candidate surfacing, and search-space exposure.
- **Determination (convergence):** review classification, hazard flagging, the pre-Lab feasibility reading that may withhold a candidate from the Lab, gate execution, scoring, and value backpropagation used to converge on a candidate branch.
- **Identity neutrality:** Shadow may produce a structurally strong candidate, but it does not decide whether the candidate is congruent with Persona identity.

This separation keeps the simulation substrate from becoming an implicit identity authority.

### 2. Heuristic evaluation (attributed gates)

To navigate the search space without exhausting the Magus's tokens, Shadow Simulation employs a
two-tier evaluation system. In the cognitive topology of the
**[Lich](../sepulcher/lich/index.md)**, it participates in **Viveka**—the broader discriminative
operation that distinguishes grounded cognition from misconception. The Dual-Gate establishes
declared structural facts and identity congruence; it does not turn every surviving claim into
Pramāṇa or authorize promotion by itself:

!!! important "The Tracked Working Copy as the Gatekeeper"
    A Jujutsu working copy has a tracked commit identity, but a running check may still observe
    later working-copy mutation or shared external state unless the execution owner freezes and
    verifies its exact input. Gates must record the tested change/commit, command, environment,
    and artifact digests; version control alone does not eliminate races.

1. **The Deterministic Gate (The Law) / Pre-Publish Structural Rubrics:** This is the binary
   foundation of structural validity. It operates as a rigid, scriptable CI gate before any Vision
   is manifested at the Altar. Does the code compile? Do the unit tests pass? Are ADR markers
   present in documentation? Are the imports sorted? Each check proves only its declared predicate.
   Failure may trigger bounded correction or mark the candidate ineligible for a declared purpose
   ($V \in \{0, 1\}$). Cleanup waits for required receipts.
2. **The Evaluation Gate (Riddle):** **[Riddle (34)](34-evaluation.md)** publishes calibrated
   comparative claims and uncertainty. It does not become an oracle or promote the branch.
3. **The Identity-Congruence Gate (Mirror):** The **[Mirror (32)](32-identity.md)** acts as an
   optional
   critic. It reviews branches that passed the Law against the active Persona's commitments and
   style, assigning a heuristic score ($H \in [0, 1]$). This gate evaluates identity congruence,
   not factual correctness.
4. **Evaluation order:** A Pattern may avoid expensive judges after a decisive deterministic
   failure, but it may retain and evaluate a failed branch when diagnosis, contrastive evidence,
   or safety analysis requires it.
5. **Search update:** An MCTS or other stateful search provider may feed attributed evaluation
   signals back into later expansion. This is heuristic convergence within Shadow, not proof or
   final promotion.

In practice:

- Branch expansion and speculative tool use are fluctuation work.
- Gate execution, scoring, and backpropagation are determinative work.
- Identity ownership and durable promotion remain external authorities.

### 3. The Branch Reaper (Shadow Hygiene)

Simulation is an "I/O Storm" that generates massive temporary data. The Reaper is a specialized Ghoul that acts as the system's metabolism.

- **The Autopsy Protocol:** Before a failed branch is destroyed, its owner preserves the receipts
  required by the Pattern: exact input identity, declared checks, deterministic failure trace,
  artifacts, and cleanup state. If a later success exists, Riddle or Soulforge may propose a
  contrastive trajectory. Failure traces do not automatically become Karma or training data.
- **Validator-Centered Failure Shape:** When a branch fails through a tool or action validator, the autopsy preserves the validator's failure class and state comparison rather than reconstructing intent from reasoning prose alone. A `precondition_miss` with `required_state` and `observed_state` is evidence about the action contract; it may point to a schema repair, a state-hydration repair, or an agent policy repair depending on which side of the boundary was false.
- **Truthful Dead Ends:** Some branches fail because the requested path is impossible, unsafe,
  underspecified, or internally contradictory. In those cases, the useful artifact is not a
  correction but an evidenced boundary. The Reaper should preserve the blocked premise, the exact
  predicate tested, and the measured evidence so future runs can distinguish a grounded
  non-manifestation from mere model hesitation.
- **Non-Manifestation as Measurement:** A dead end is promoted only when it is grounded in Pramāṇa: a failed deterministic gate, an exhausted retrieval threshold, a violated policy boundary, or trusted Magus testimony. Mere model hesitation is not evidence; the boundary must be witnessed.
- **Logical Banishment:** Once retention requirements and lease ownership permit it, the native
  workspace provider may abandon the branch change. Jujutsu `jj abandon` rewrites graph
  relationships; cleanup must verify the intended descendants and retained references rather than
  assuming instant erasure.
- **The Workspace Purge (Defensive Teardown):** The runtime/workspace owner terminates
  branch-owned processes, reservations, ports, and temporary services before removing the
  workspace. Cleanup records what it verified; it cannot infer that every external effect vanished
  because a directory did.
- **Retention TTL:** A configurable TTL makes a workspace eligible for cleanup, not automatically
  safe to delete. Active leases, legal holds, pending review, and required evidence override it.

Architecturally, the Reaper dissolves unstable or low-signal modifications so the substrate does not retain abandoned fluctuations as noise.

### 4. Memory Handoff, Not Vector Ownership

Shadow owns branch evidence until it is handed to the proper retention boundary. It may propose
failed/successful trajectory pairs, but **[Memory (27)](27-memory.md)** owns eligibility, recall,
reinforcement, archival, expiry, and deletion. Soulforge owns training-lineage admission. An
access-count decay formula may be evaluated as a Memory policy, but it is not part of the Shadow
contract: age and low access do not prove that a record is noise, and an “Anchor” is a retention
policy rather than immortality.

### 5. Transactional Convergence (The Collapse)

Once a simulation achieves an **eligible candidate state**—its declared deterministic predicates
pass and its heuristic score satisfies policy—it may be considered for Primary Reality. This
collapse occurs through **the Blade**, LychD's name for the
Buddhi correspondence. Where the Call opens candidates and Phantasma expands Vikalpa into the
Shadow Realm, the Blade cuts toward one: the faculty of final judgment that cannot be overridden by
the weight of existing Seeds. The three collapses below are the Blade operating at three nested
levels of discrimination:

- **The Vision:** The proposed change is presented as a "Vision" (Diff/Summary) to the Magus via the **[HitL (25)](25-hitl.md)** protocol.
- **The Consecration:** Upon live Magus consent or valid preauthorization, the owning promotion
  Composition applies the candidate through its declared Snapshot, merge/rebase, verification, and
  rollback contract. Shadow does not execute the promotion merely because the branch passed.
- **The Inscription:** Phylactery records the candidate, evidence, authorization, effect receipt,
  and outcome. Memory policy separately decides whether any trace becomes Karma.
- **Frictionless Collapse (ZTE Chores):** If Codex policy classifies the work as a minor
  preauthorized chore and every declared gate passes, the owning Composition may promote without a
  live HitL prompt. Historical success may inform policy but never substitutes for current scope,
  effect, Snapshot, and evidence checks.

This flow contains three distinct collapses that should remain explicit:

1. **Structural validity collapse (Shadow gate):** invalid branches are eliminated by deterministic checks.
2. **Identity congruence collapse (Mirror gate):** valid branches are ranked for Persona alignment.
3. **Ontological promotion collapse (Vessel policy + HitL):** only candidates authorized by explicit Magus consent or Codex-defined preauthorization become durable reality.

Shadow can execute the first and prepare the second, but it cannot self-authorize the third.

!!! note "Approval Policy Boundary"
    ZTE is a policy class under **[Configuration (ADR 12)](12-configuration.md)**. It may cover small chores such as documentation link fixes, non-runtime metadata, or narrow test maintenance when all verification gates pass. It must not cover core runtime mutation, schema migration, destructive deletion, secret changes, host lifecycle authority, broad network/egress changes, or promotion that requires a Snapshot rollback plan. Those classes still require live HitL.

### 6. Shadow Simulation Test Primitives

Pydantic AI testing primitives are useful for testing Agent and tool contracts, but they do not
simulate arbitrary infrastructure or prove absence of side effects:

- **`TestModel`:** Used by the **[Smith (35)](35-assimilation.md)** to dry-run extension structures and routing logic without consuming expensive inference tokens.
- **`FunctionModel`:** Can provide deterministic model-shaped responses for a declared test. Real
  infrastructure behavior still requires an integration environment and measured checks.

### 7. Orchestration of Shadow Simulation

Simulation can be resource-intensive; its priority is declared per Invocation rather than granted
by ritual rank.

- **Readiness:** The Pattern declares capability and priority requirements. The
  **[Dispatcher (22)](22-dispatcher.md)** selects eligible providers and the
  **[Orchestrator (23)](23-orchestrator.md)** governs leases, readiness, and conflicts. Neither
  silently moves work to a Portal.
- **Budgeting:** A branch that exhausts its time, token, or economic budget is cancelled or marked
  truthfully incomplete. Cleanup follows the same receipt and retention law as any other branch.

### 8. Authority and Trust Boundaries

The Shadow Realm is infrastructural, not just conceptual.

- The **Shadow Extension Domain** owns possibility identity, branch lineage, and the rule that
  branches emit candidates rather than live effects. A Weaver Pattern coordinates an Invocation;
  effectful code branches may receive workspaces under `lab/shadow/`.
- The graph runner and agent logic stay in the **Vessel**. **The Tomb** receives only serialized execution payloads (scripts, test suites, linter invocations) via SAQ. It is the hand for unsafe work, not the home of the agent. It does not run agent logic, graph state machines, or make LLM calls.
- Graph steps declare execution mode (`vessel` or `tomb`); unsafe steps serialize their payload and dispatch to **The Tomb**, then await the `stdout` result.
- **The Tomb** returns untrusted `stdout`/`stderr` and declared artifacts/traces only.

Both Shadow Simulation and the **[Weaver (28)](28-workflow.md)** fan out parallel agent labor, so the boundary between speculative branching and live workflow must be stated as law. That boundary is the **Demarcation Law**:

!!! important "The Demarcation Law"
    A branch that may commit an effect into the live Run belongs to the Weaver. A branch that may only produce a Vision belongs to the Shadow. The Weaver consumes Simulation results solely as consecrated Visions or as evidence in joins—never as direct state writes. The Dual-Gate governs only the Shadow's output.

Shadow branches can only emit Visions—promotion candidates—never direct live effects. Effectful
code branches may live in Jujutsu workspaces under `lab/shadow/`; pure branches need not. A result
crosses into real state only after attributed evaluation and authorization, through the owning
promotion boundary (§5).

Operational summary: Shadow produces possible futures, Mirror filters for congruence, and Vessel authorizes what becomes real.

This stack models cognitive mechanics and control boundaries, not subjective awareness. LychD implements recursive process, identity continuity, and consented promotion without positing an internal witnessing principle.

### Policy Table

| Dimension | Vessel (Trusted Simulation Control) | The Tomb (Untrusted Simulation Substrate) |
| :--- | :--- | :--- |
| Secrets | Holds scoring/policy/provider credentials for adjudication. | Narrow queue-only SAQ/Postgres execution credential when required; no provider, signing, Codex, or control-plane secrets. |
| Mounts | Persistent state and decision metadata mounts. | Simulation workspace and artifact mounts; optional read-only/sanitized Codex projection only. |
| Network | Controlled internal services and approved provider calls. | Tomb loop may use constrained queue/proxy connectivity; sandboxed `nono` subprocesses have zero network. |
| Queue Ownership | Owns durable simulation scheduling and reanimation state. | Claims, acknowledges, and retries execution-plane jobs only. |
| Authority Boundaries | Applies approval policy, authorizes collapse/promotion, and commits persistence. | Produces candidate timelines only. |

## Consequences

!!! success "Positive"
    - **Measured Alternatives:** Candidate execution can establish facts unavailable from sampling
      alone.
    - **Physical Integrity:** The Reaper gives branch-owned resources a bounded cleanup protocol.
    - **Governed Improvement:** Evidence from failures and successes may inform later work without
      making simulation self-authorizing.

!!! failure "Negative"
    - **Temporal Latency:** Multi-candidate deliberation is usually unsuitable for sub-second
      reflexes.
    - **I/O Exhaustion:** Running many effectful Jujutsu workspaces can create high disk pressure.
    - **Resource Hunger:** Candidate generation and evaluation can consume substantial token,
      compute, artifact, and review budgets.
    - **Heuristic Risk:** Search and judge scores can converge confidently on the wrong candidate;
      they remain evidence inputs, not truth.
