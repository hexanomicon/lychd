---
title: Soulforge
icon: material/anvil
---

# :material-anvil: The Soulforge: Extension of Training

> _Training begins before the first weight moves._

**Soulforge** binds an admitted corpus, base-model digest, objective, Recipe, Training Run,
evaluation, and candidate weights into immutable lineage. Its tools may change; its evidence must
survive the strike.

Soulforge is **Designed**; the passages below have no operational training or serving path yet.
[State of Work](../../../state-of-the-work.md#soulforge-training) records delivery, and
[ADR 33](../../../adr/33-training.md) owns the law and complete record schemas.

Soulforge may run during an admitted idle resource window, but sleep supplies no training or
consolidation contract. The forge instead follows the explicit passage below.

## The Four Passages {#iv-orchestration-of-the-forge}

| Route | Receives | Leaves behind | Refuses |
| :--- | :--- | :--- | :--- |
| [Corpus admission](./corpus.md#admit-one-snapshot) | Training Intent and nominated records | Corpus Admission, exact membership, negative ledger, and sealed holdout | Missing provenance, authority, privacy clearance, relevance, or a viable uncontaminated holdout |
| [Dataset compilation](./corpus.md#compile-without-leakage) | One admitted snapshot | Immutable Dataset Manifest with preserved lineage and splits | Unadmitted material, split drift, or holdout leakage |
| [Training run](./training-run.md) | Manifest, base digest, objective, Recipe, and resource request | Training Run receipt and frozen Candidate Bundle | Unpinned inputs, a refused resource window, or unknowable retry state |
| [Candidate handoff](./candidate-handoff.md) | Frozen bundle and evaluation contract | Riddle Outcomes and an externally owned Promotion Decision | Trainer self-grading, mutable custody, or unowned serving |

Each passage needs its own admission: [Orchestrator](../../../adr/23-orchestrator.md) decides the
physical transition; passing independent [Riddle](../riddle/capability-claims.md) evaluation
establishes eligibility; owning policy and required Magus/[HitL](../../../adr/25-hitl.md) authority decide
promotion. The serving owner alone registers and routes the exact promoted digest.

Observation may trigger rollback or lineage invalidation. It cannot rewrite an earlier record,
erase completed effects, or remove learned influence from weights already produced.
