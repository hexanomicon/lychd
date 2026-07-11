---
title: Phylactery
icon: fontawesome/solid/flask
---

# :fontawesome-solid-flask: Phylactery

> _"The Vessel thinks, but the Phylactery remembers. One is the fleeting spark of lightning, the other is the eternal stone upon which the storm breaks."_

At its core, the Phylactery is the durable memory of the Lich. In the grand architecture, it is the metaphysical anchor that binds Agentic Coherence to reality. It is the source of continuity, the library of ancient knowledge, and the fuel for the **[Soulforge](../extensions/soulforge.md)**.

Technically, it is a fortified **PostgreSQL** instance equipped with **`pgvector`**. It resides within the **[Crypt](../crypt.md)**, protected by the atomic laws of the filesystem.

## 📜 The Anatomy of Memory

The first-light Phylactery uses the configured database's default schema/search path. Its mature
anatomy reserves sacred chambers, but only the first item and SAQ's default `saq_*` tables exist
today:

1. **`public` (The State):** The current reality. Migration `0001_phylactery_first_light` raises `session`, `run`, `run_checkpoint`, `step`, `consent`, `karma`, `soulstone_record`, and `codex_preauthorization`. The `run`/`step` tables are the run truth written by the **[RunLedger](../vessel/ghouls.md)**; `run_checkpoint` owns one complete durable graph history per run.
2. **`vectors` (The Karma, planned):** The high-dimensional embedding space where verified outcomes may be stored.
3. **`traces` (The Mind's Eye, planned):** The dedicated chamber for durable cognitive traces.
4. **`queue` (The Ghouls, planned isolation):** The future queue schema/role boundary. V1 SAQ
   creates its `saq_*` tables on the default search path and run-row/enqueue is not one transaction.

!!! abstract "The Anchor"
    The primary and most sacred function of the Phylactery is to house the **Pattern**.

    A model-backed **[Soulstone](../../sepulcher/animator/soulstone.md)** is a processor with no memory of its own: kill the container and nothing of the Lich is lost, because nothing of the Lich lived there. Continuity lives here.

    The Phylactery survives reboots, crashes, and migrations at each store's declared committed
    boundary. In the current foundation that means SAQ jobs, Postgres run/step rows, and one
    run-owned JSONB graph checkpoint document. Memory/persona/trace stores and a transactional
    graph/queue outbox remain later work. Volatile frames may be reconstructed or
    abandoned according to Graph, Worker, and policy law.

!!! info "The Accumulator of Karma"
    The Phylactery is not a static archive; it is a growing crystal. What the Magus **[consecrates](../../adr/25-hitl.md)** is inscribed here as **Karma** — what was chosen, and why — and becomes the dataset the **[Soulforge](../extensions/soulforge.md)** compresses into substrate instinct. The mechanism is law in [HitL (25)](../../adr/25-hitl.md) §4; the meaning lives in [Transcendence](../../divination/transcendence/index.md).
