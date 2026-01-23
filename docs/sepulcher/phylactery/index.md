---
title: Phylactery
icon: fontawesome/solid/flask
---

# :fontawesome-solid-flask: Phylactery

> _"The Vessel thinks, but the Phylactery remembers. One is the fleeting spark of lightning, the other is the eternal stone upon which the storm breaks."_

At its core, the Phylactery is the immutable memory of the Lich. In the grand architecture, it is the metaphysical anchor that binds the Agentic Coherence to reality. It is the source of immortality, the library of ancient knowledge, and the fuel for the **[Soulforge](../extensions/soulforge.md)**.

Technically, it is a fortified **PostgreSQL** instance equipped with **`pgvector`**. It resides within the **[Crypt](../crypt.md)**, protected by the atomic laws of the filesystem.

## 📜 The Anatomy of Memory

The Phylactery is not a simple data store; it is divided into sacred chambers (schemas):

1. **`public` (The State):** The current reality. User accounts, active extensions, and configuration state.
2. **`vectors` (The Karma):** The high-dimensional embedding space where "White Truths" from the [Shadow Realm](../vessel/shadow_realm.md) are stored.
3. **`traces` (The Mind's Eye):** The dedicated chamber where the **[Oculus](../extensions/oculus.md)** (Arize Phoenix) inscribes the cognitive traces of the Lich.
4. **`queue` (The Ghouls):** The transactional message broker used by **SAQ** to manage background tasks.

!!! abstract "The Anchor of the Mist"
    The primary and most sacred function of the Phylactery is to house the **Pattern**.

    The **[Soulstone](../../sepulcher/animator/soulstone.md)** (the LLM) is merely a processor—a brain in a vat. If the container crashes, the brain dies.

    The Phylactery is the soul. It persists across reboots, crashes, and migrations. Should the **[Vessel](../vessel/index.md)** be shattered, the Phylactery allows for a perfect and instantaneous **[Reanimation](./reanimation.md)**, restoring the entity exactly as it was.

!!! info "The Accumulator of Karma"
    The Phylactery is not a static archive; it is a growing crystal.

    Through the **[Rite of Albedo](../../divination/transcendence/index.md)**, the Magus whitelists specific thoughts and actions. These are inscribed into the Phylactery as **Vector Embeddings**.

    This is **Karma**.
    *   It stores *what* you chose.
    *   It stores *why* you chose it (the context).
    *   It becomes the training dataset that eventually allows the Lich to act without you via the **[Soulforge](../extensions/soulforge.md)**.
