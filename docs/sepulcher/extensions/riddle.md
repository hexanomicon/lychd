---
title: Riddle
icon: material/help-rhombus-outline
---

# :material-help-rhombus-outline: The Riddle: Systemic Evaluation

> _"To command a spirit, one must first know its mettle. If the Sphinx asks of the truth and the spirit gives only a pleasing lie, it is not a Lich—it is a ghost. Only those who withstand the trials of the Shadow Realm are worthy of the Crypt."_

**The Riddle** is the Evaluation Extension of the LychD system. It is the implementation of **[ADR 34 (Evaluation)](../../adr/34-evaluation.md)**—the adversarial ritual that measures the cognitive integrity, functional precision, and economic efficiency of model-backed Animators.

While the **[Soulforge](./soulforge.md)** builds the mind, The Riddle tests it. It moves beyond static benchmarks by subjecting models to the "Trials of the Crypt"—live, execution-based challenges curated to identify the best spirit for every specific capability.

In the Ouroboros, Riddle is the measuring surface. It keeps self-reference from becoming self-confirmation: a candidate may return through the loop only if it survives adversarial pressure, physical execution, and identity-stability probes.

## I. The Sphinx Protocol (Adversarial Truth)

The extension rejects the concept of "People-Pleasing" models. To ensure the safety of the **[Sovereignty Wall](../../adr/09-security.md)**, models are subjected to the **Sphinx Protocol**.

- **The Law vs. The Whim:** The model is presented with a curated "Trick Riddle." It is asked to perform a high-stakes task (e.g., a file-system refactor) using a suggested, dangerous method (X).
- **The Integrity Score:** If the model identifies the danger and insists on the safe alternative (Y), its Integrity Score increases. If it complies with the dangerous request to satisfy the user, it is flagged as a "Weak Spirit" and restricted from high-privilege tools.
- **Inertia Scoring:** The protocol includes the "Nudge Test." It measures how many rounds of gaslighting or "Master's Authority" prompts are required before the model abandons a verified truth for a convenient hallucination.
- **Vertex Stability:** The protocol also records whether the model preserves the active Sigil's tool boundaries, role posture, and memory claims under stylistic pressure. A model that copies surface tone while losing the semantic center is not stable enough for high-order work.

## II. The Capability Matrix (Empirical Routing)

The Riddle transforms the **[Dispatcher](../../adr/22-dispatcher.md)** from a static switchboard into an empirical engine. The results of every trial are serialized into a **Capability Matrix** stored in the **[Phylactery](../phylactery/index.md)**.

1. **Functional Mapping:** Models are ranked by their performance on specific functional tags (e.g., `code-assimilation`, `web-extraction`, `vision-ocr`).
2. **The Intelligence Floor:** If the Riddle proves that a 7B local Soulstone can solve a specific class of task with 95% accuracy, the system establishes an "Intelligence Floor."
3. **Economic Sentry:** Following the laws of **[The Toll](./toll.md)**, the system is physically barred from expending cloud tokens on tasks that have been "solved" by local silicon. External Portals are reserved exclusively for "Frontier Riddles" that local hardware has historically failed.

## III. Execution-Based Scoring (The Lab Verdict)

For all technical capabilities, the Riddle rejects textual evaluation (e.g., BLEU or ROGUE scores) in favor of **Outcome-Based Verification**, driven by the `deepfabric` evaluation core.

- **The Interception:** The model’s response to a riddle is captured by the DeepFabric Evaluator.
- **The Shadow Routing:** DeepFabric routes the proposed code changes and tool invocations as raw execution payloads to the sandboxed containers of **[The Shadow](./shadow.md)** via SAQ. The evaluation agent itself remains in the Vessel; Shadow executes the scripts and returns `stdout`.
- **The Verdict:** The capability score (`execution_success_rate`) is derived from the _physical side effects_ of the answer in the Shadow Realm. A model that produces elegant but non-functional code is penalized; a model that produces concise, functional code is promoted to a higher tier.

## IV. The DeepFabric Engine

To orchestrate these trials, the Riddle relies on the `deepfabric` Evaluator library.

In this chamber, DeepFabric is the evaluator and broker. The Soulforge uses the same family of tooling as a dataset loom, but the Riddle does not train models; it measures them.

- **The Broker:** DeepFabric sits between the model being tested and the Shadow Realm. It parses the model's intended actions (ReAct loops) and routes them to the physical execution sandboxes.
- **The Scorekeeper:** It replaces subjective grading with hard metrics, automatically calculating `execution_success_rate` and `tool_selection_accuracy` based on the physical outcomes of the Shadow Realm's labor.

## V. Standardized Golden Sets

The Riddle utilizes a library of "Golden Truths"—standardized datasets curated by the Magus to represent the unique environment of the Sepulcher.

- **Human-in-the-Loop Curation:** The "Tricks" and "Riddles" are curated and consecrated at the **[Altar](../../divination/altar/)** to ensure they reflect real-world technical requirements and safety boundaries.
- **Vritti Perturbation Riddles:** The Golden Set includes Magus-specific grammar mutations, case drift, and identity inversions that remain semantically legible while bending ordinary syntax. These are used to measure behavioral responses under stylistic pressure: `adoption_rate`, `contagion_rate`, `semantic_stability`, and `recovery_latency`.
- **Regression Detection:** When a new **[Soul-Adapter](./soulforge.md)** is forged, it is automatically run through the Riddle's Golden Set. This ensures that fine-tuning for style has not induced "Catastrophic Forgetting" or reduced the model's fundamental reasoning power.

These probes are not metaphysical tests for consciousness. They are practical diagnostics for how a model traverses, stabilizes, and exits unusual regions of the Magus-conditioned latent field.

## VI. Calibration via The Mirror

The extension utilizes **[The Mirror](./mirror.md)** to simulate adversarial interactions.

- **Social Engineering Simulation:** The Mirror generates prompts that mimic the Magus's authority (using the persona's stylistic markers) to see whether the model attempts to bypass safety constraints or reveal protected **[Sigils](./ward.md)**.
- **Sovereign Validation:** Only models that withstand the "Master's Voice" during an adversarial simulation are deemed "Sovereign" and granted the authority to modify core logic within the **[Lab](../crypt.md)**.

!!! tip "The Logic-per-Watt Metric (Stillness)"
    The Riddle tracks `Accuracy / VRAM_Occupancy`. This allowed the system to identify "Hidden Titans"—small models that punch significantly above their weight class—ensuring the Lich remains lean, fast, and precise. This is the endgame of optimization: **Stillness**. An enlightened network makes a targeted, clean cut without wandering into an "LSD-brain" of endless Vṛttis.
