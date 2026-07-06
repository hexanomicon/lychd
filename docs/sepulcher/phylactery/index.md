---
title: Phylactery
icon: fontawesome/solid/flask
---

# :fontawesome-solid-flask: Phylactery

> _"The Vessel thinks, but the Phylactery remembers. One is the fleeting spark of lightning, the other is the eternal stone upon which the storm breaks."_

At its core, the Phylactery is the durable memory of the Lich. In the grand architecture, it is the metaphysical anchor that binds Agentic Coherence to reality. It is the source of continuity, the library of ancient knowledge, and the fuel for the **[Soulforge](../extensions/soulforge.md)**.

Technically, it is a fortified **PostgreSQL** instance equipped with **`pgvector`**. It resides within the **[Crypt](../crypt.md)**, protected by the atomic laws of the filesystem.

## 📜 The Anatomy of Memory

The Phylactery is not a simple data store; it is divided into sacred chambers (schemas):

1. **`public` (The State):** The current reality. Its first light is delivered: migration `0001_phylactery_first_light` raises seven tables — `session`, `run`, `step`, `consent`, `karma`, `soulstone_record`, and `codex_preauthorization`. The `run`/`step` tables are the run truth written by the **[RunLedger](../vessel/ghouls.md)**.
2. **`vectors` (The Karma):** The high-dimensional embedding space where "White Truths" from the [Shadow Realm](../extensions/shadow.md) are stored.
3. **`traces` (The Mind's Eye):** The dedicated chamber where the **[Oculus](../extensions/oculus.md)** (Arize Phoenix) inscribes the cognitive traces of the Lich.
4. **`queue` (The Ghouls):** The transactional message broker used by **SAQ** to manage background tasks.

!!! abstract "The Anchor of the Mist"
    The primary and most sacred function of the Phylactery is to house the **Pattern**.

    A model-backed **[Soulstone](../../sepulcher/animator/soulstone.md)** is merely a processor: a brain in a vat. If the container crashes, the brain dies.

    The Phylactery is the soul-data anchor. It persists across reboots, crashes, and migrations. Should the **[Vessel](../vessel/index.md)** be shattered, the Phylactery allows **[Reanimation](./reanimation.md)** from committed boundaries: memory records, persona state, queues, graph checkpoints, traces, and completed outputs. Volatile frames may be reconstructed or abandoned according to Graph, Worker, and policy law.

!!! info "The Accumulator of Karma"
    The Phylactery is not a static archive; it is a growing crystal.

    Through the **[Rite of Albedo](../../divination/transcendence/index.md)**, the Magus whitelists specific thoughts and actions. These are inscribed into the Phylactery as **Vector Embeddings**.

    This is **Karma**.
    - It stores *what* the Magus chose.
    - It stores *why* the Magus chose it (the context).
    - It becomes the training dataset that lets the **[Soulforge](../extensions/soulforge.md)** compress stable patterns into substrate instinct, reducing explicit prompting while preserving the Magus's consecrating authority.
