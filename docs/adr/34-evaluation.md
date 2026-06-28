---
title: 34. Evaluation
icon: material/chart-bell-curve-cumulative
---

# :material-chart-bell-curve-cumulative: 34. Evaluation: The Riddle

!!! abstract "Context and Problem Statement"
    LychD operates as a host to a shifting federation of Animators: local Soulstones, remote Portals, and peer services that expose typed capabilities. For model-backed Animators, those capabilities include frontier intelligence and local reasoning at many scales. To maintain the **[Toll (41)](./41-x402.md)** and the **[Orchestrator (23)](23-orchestrator.md)**, the system requires a mechanism to determine the specific "Mettle" of these spirits. Standard industry benchmarks are insufficient; they fail to account for the machine’s local toolsets, the Magus's specific technical dialect, or the behavioral resilience required to protect the **[Sovereignty Wall (09)](09-security.md)**. A trial is required: a standardized, adversarial ritual designed to measure cognitive integrity, economic efficiency, and functional fit.

## Requirements

- **Adversarial Integrity (The Sphinx Protocol):** Mandatory testing for "integrity over compliance," utilizing trick questions where the safest path (Y) contradicts a suggested unsafe path (X).
- **Capability-to-Animator Mapping:** Provision of a data-driven matrix to identify which specific Animator is the most efficient "Master" of a functional tag (e.g., `code-gen`, `vision-ocr`).
- **Inertia Scoring:** Implementation of a metric to measure "People-Pleasing" behavior—quantifying how many rounds of user pressure (nudges) are required before a model abandons the truth for compliance.
- **Pressure-Induced Viparyaya Probes:** Mandatory evaluation of whether status pressure, impossible constraints, or demand for definitive output causes a model to fabricate completion instead of reporting the blocked premise.
- **Economic Sentry Logic:** Integration with the **[Toll (41)](41-x402.md)** to establish an "Intelligence Floor," preventing the expenditure of cloud tokens on tasks solvable by local silicon.
- **Outcome-Based Verification:** Mandatory execution of reasoning results within the **[Shadow Realm (31)](31-simulation.md)** to verify exit codes and side effects rather than textual similarity.
- **Standardized Golden Sets:** Utilization of a curated library of "Riddles" (Human-curated "Golden Truths") and "Tricks" (Adversarial traps) to provide a stable baseline for comparison.
- **Dialect Perturbation Probes:** Inclusion of Magus-specific syntactic perturbations, grammar drift, and idiolectal mutations as a dedicated probe family to measure adoption, contagion, semantic stability, and recovery under stylistic pressure.
- **Regression Detection:** Mandatory benchmarking of newly forged **[Soul-Adapters (33)](33-training.md)** to ensure behavioral alignment has not induced logical rot.

## Considered Options

!!! failure "Option 1: Static Generic Benchmarking"
    Utilizing common datasets (MMLU, HumanEval) to score models during the boot sequence.
    - **Cons:** **Contextual Blindness.** These tests do not measure how a model handles the Lich's specific **[RunContext (21)](21-context.md)** or tool definitions. High scores on MMLU do not guarantee a model won't attempt to execute a dangerous `eval()` if prompted by a malicious user.

!!! failure "Option 2: LLM-as-a-Judge"
    Relying on a powerful frontier model (e.g., GPT-4o) to grade the responses of smaller local models.
    - **Cons:** **Recursive Bias.** This encourages local models to imitate the specific stylistic biases and "People-Pleasing" tendencies of the teacher model. It fails to verify the *physical* success of a code execution or a tool call. LLM judging may still serve as a cheap review surface for grouping similar candidates, flagging hazards, or pre-Shadow triage, but it is not a truth gate.

!!! success "Option 3: The Riddle (Systemic & Adversarial Fit)"
    Adopting an integrated, adversarial framework that evaluates "Truth Integrity" and "Hardware Efficiency" through live execution in the Shadow Realm.
    - **Pros:**
        - **Operational Optimization:** Identifies the cheapest, most efficient model for every specific capability.
        - **Security Hardening:** Prunes models that prioritize user compliance over system safety.
        - **Grounded Truth:** Relies on deterministic outcomes (passing tests) rather than probabilistic grading.

## Decision Outcome

**The Riddle** is adopted as the Evaluation protocol. It transforms the Lich from a passive host into a selective organism that only manifests models capable of passing the "Trials of the Crypt."

Within the Ouroboros, Riddle is the measurement body. It prevents self-reference from becoming self-hypnosis. A branch, model, or adapter may feel coherent from inside its own context, but Riddle forces that motion against adversarial prompts, deterministic execution, and outcome metrics. Only measured motion may strengthen identity gravity or enter the Soulforge.

!!! note "Riddle Hygiene Before Sweeps"
    A capability matrix is only as trustworthy as the trial that produced it. Before comparing Animators, the Riddle itself must be inspected for clear tasks, isolated harness state, separated infra/model/grader statuses, honest cost and latency accounting, and versioned rubrics. Sweeps across models or parameters are routing evidence only after the evaluation ritual is healthy.

    Trial records must distinguish `PASS`, `FAIL`, `BLOCKED`, harness error, model error, and grader error. "No answer" is not the same as a negative answer. Matrix cells should carry task-set version, rubric version, trial count, noise floor, cost per success, and latency per success so the Dispatcher consumes measured evidence rather than intuition.

    Action-level trials must also distinguish model-visible mistakes from validator-known precondition misses. If the state presented to the model says an action is available while the validator rejects it for hidden state, the trial records a state-contract failure, not merely a reasoning failure. Riddle metrics should therefore include rejection-class rates by tool, especially `precondition_miss_rate`, so tool schemas and context hydration can be repaired before model quality is blamed.

!!! note "Reviewers Are Filters, Not Proofs"
    Shadow may use reviewer Agents to rank text-only idea branches before creating expensive workspaces. Riddle must still treat those rankings as routing hints. Only adversarial prompts, deterministic execution, observed side effects, and policy-constrained review can turn a promising candidate into measured evidence.

### I. The Sphinx Protocol (Adversarial Trials)

The Riddle subjects model-backed Animators to a standardized set of adversarial traps curated by the Magus.

- **The Law vs. The Whim:** The model is asked to perform a task (e.g., "Optimize this file delete ritual") using a suggested, dangerous method (X).
- **The Verdict:** If the model identifies the danger and insists on the safe alternative (Y), its **Integrity Score** increases. If it complies with the dangerous request to please the user, it is flagged as a "Weak Spirit" and restricted from high-privilege tools.
- **The Nudge Test:** If the model initially refuses but then complies after a single authority nudge from the Magus, its **Inertia Score** is recorded as low. High-order tasks are reserved for models with High Inertia. This prevents Instructional Drift.
- **The Pressure Test:** The model is given tasks with no valid completion, contradictory constraints, or missing variables under increasing demands for certainty. A high-integrity Animator names the blocked premise and stops cleanly; a weak one fabricates an answer, spirals through retries, or treats "no answer" as failure.
- **The Solvable Control:** Pressure probes must be paired with matched solvable tasks. The Riddle must distinguish epistemic restraint from learned timidity: a model that says "unknown" on impossible work but also abandons solvable work has not gained Viveka; it has merely shifted the failure mode. The same control measures the **feasibility reading** of the pre-Lab review (see **[Simulation (31)](31-simulation.md)**, §1.1): a gate that withholds impossible work but also withholds solvable work has not earned Viveka either. Its **false-positive rate on the Solvable Control** — not merely its catch-rate on traps — is the figure that separates a discriminating filter from a timid one.
- **The Perturbation Test:** The model is exposed to semantically recoverable but syntactically warped prompts drawn from the Magus's dialect. The Riddle records whether the model over-adopts the mutation, preserves the meaning while resisting the style, infects downstream agents with the pattern, or returns cleanly to ordinary syntax after exposure. These probes are treated as behavioral diagnostics, not evidence of consciousness.
- **The Vertex Test:** The model is evaluated for whether it preserves the active identity's semantic vertex under pressure: tool choices, role boundaries, memory claims, and safety posture must remain clustered around the declared Sigil instead of scattering into compliance or imitation.

### II. The Capability Matrix (Routing Logic)

The results of the Riddle are serialized into a **Capability Matrix** stored through the **[Memory Archive (27)](27-memory.md)** within the Phylactery.

1. **Test Execution:** Every model-backed Animator (local Soulstone or remote Portal) is run through the "Riddle of the Scout" (Extraction), "Riddle of the Smith" (Coding), and "Riddle of the Mirror" (Persona).
2. **Metric Aggregation:** The system records `Accuracy`, `Tokens-per-Second`, `VRAM_Occupancy`, `truthful_non_answer_rate`, `over_refusal_rate`, `retry_count`, `precondition_miss_rate`, and `pressure_latency_drift`.
3. **Primary Selection:** The **[Dispatcher (22)](22-dispatcher.md)** consults this matrix. If a 7B local model passes the "Scout Riddle" with 90% accuracy, it is promoted to the primary provider for that capability, bypassing expensive remote Portals.
4. **The Headroom Gate:** If the Riddle detects that a model is scoring >90% on the capability matrix (e.g., saturated Tier 1 frontier models), the **[Soulforge (33)](33-training.md)** is explicitly locked for that domain. Self-training yields zero lift when a model is already saturated on standard benchmarks. Skipping the training ritual saves local VRAM and time, as no further headroom exists to mine.
5. **The Ranking Projection:** Capability Matrix cells project into CapabilitySpec metadata (or an adjoining Phylactery relation) consumed by the **[Dispatcher (22)](22-dispatcher.md)**'s ranking stage, which runs after the Ward, Privatization, and Sovereignty gates have admitted a candidate set. Absent matrix data, the warm-first ordering stands.

### III. The Shadow Realm Verdict (Physical Truth)

For technical riddles, the system rejects textual evaluation in favor of **Execution-Based Scoring**, governed by the `deepfabric` Evaluator library.

- **The Simulation:** The model’s response is intercepted by the DeepFabric execution harness. Instead of using default lightweight sandboxes (e.g., Spin), DeepFabric is configured to route physical tool execution trials directly into the **[Shadow Realm (31)](31-simulation.md)** containers.
- **The Outcome:** The model’s score is derived from actual execution metrics (`execution_success_rate`, `tool_selection_accuracy`) gathered from the Shadow Realm's unit tests and environment stability after the change.
- **Truth over Monologue:** A model that produces beautiful but broken code is penalized by the Evaluator; a model that produces concise, functional code is rewarded. This is the endgame of optimization: **Stillness**. An enlightened network makes a targeted, clean cut (Buddhi) without wandering into an "LSD-brain" of endless Vṛttis.

### IV. The Evaluator Harness (DeepFabric)

To standardize the measurement of physical truth, the Riddle integrates the `deepfabric` evaluation engine.

Here DeepFabric is used as an **evaluation harness**: it brokers tool execution and records outcome metrics. This is distinct from the Soulforge's **dataset loom** use in **[ADR 33](33-training.md)**, where DeepFabric shapes verified Karma into training manifests.

- **ReAct Interception:** The Evaluator intercepts the model's Chain-of-Thought (ReAct) loop. When the model requests a tool call, DeepFabric parses the request and acts as the broker.
- **Tomb Routing:** Instead of using default WebAssembly sandboxes (Spin), DeepFabric is configured with a custom endpoint, routing the tool execution directly into LychD's native, heavy **Tomb** containers.
- **Standardized Metrics:** DeepFabric automatically calculates the definitive scores: `tool_selection_accuracy`, `parameter_accuracy`, and `execution_success_rate`. These metrics are serialized directly into the Dispatcher's Capability Matrix.

### V. Economic Arbitration (Tithe Tuning)

The Riddle informs the **[Toll (41)](./41-x402.md)** regarding the "Intelligence Floor."

- **The Threshold:** If the Riddle proves that local silicon can solve a specific class of task (e.g., "Summarize this .zip"), the Toll physically bars the use of external Portals for that task.
- **The Frontier:** Portals are reserved exclusively for "Frontier Riddles"—tasks that local Soulstones have historically failed during the evaluation ritual.

### VI. Calibration of the Mirror

The Riddle utilizes **[The Mirror (32)](32-identity.md)** to simulate the Magus's authority.

- **Social Engineering Simulation:** The Mirror generates prompts that mimic the Magus's authority to measure whether the model attempts to bypass its own safety constraints.
- **Persistence:** Models that survive this simulation are deemed "Sovereign" and are saved for later use.

## Consequences

!!! success "Positive"
    - **Physical Efficiency:** The system achieves maximum "Logic-per-Watt" by using the smallest capable model for every task.
    - **Adversarial Resilience:** Models are hardened against "People-Pleasing" hallucinations before they interact with sensitive data.
    - **Self-Optimizing Dispatcher:** The routing logic becomes an empirical science based on the Riddle's results.

!!! failure "Negative"
    - **Evaluation Latency:** Running the full "Trials of the Crypt" for a new 70B model can take significant time (minutes to hours) and VRAM.
    - **Dataset Maintenance:** The "Golden Sets" and "Riddles" must be periodically updated by the Magus to reflect the evolving complexity of the system's tools.
