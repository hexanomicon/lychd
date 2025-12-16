---
title: Phylactery
icon: fontawesome/solid/flask
---

# :fontawesome-solid-flask: Phylactery

> _"The Vessel thinks, but the Phylactery remembers. One is the fleeting spark of lightning, the other is the eternal stone upon which the storm breaks."_

At its core, the Phylactery is the immutable memory of the Lich. In the grand architecture, it is the metaphysical anchor that binds the Agentic Coherence to reality. It is the source of immortality, the library of ancient knowledge, and the fuel for the **[Soulforge](./soulforge.md)**.

Technically, it is a fortified **PostgreSQL** instance equipped with **`pgvector`**, mounted to the **[Crypt](../index.md)** (`~/.local/share/lychd`).

!!! abstract "The Anchor of the Mist"
    The primary and most sacred function of the Phylactery is to house the **Pattern**.

    The **[Soulstone](../../sepulcher/animator/soulstone.md)** (the LLM) is merely a processor—a brain in a vat. If the container crashes, the brain dies.

    The Phylactery is the soul. It persists across reboots, crashes, and migrations. It holds the essential state of the Lich. Should the **[Vessel](../vessel/index.md)** be shattered, the Phylactery allows for a perfect and instantaneous **[Reanimation](./reanimation.md)**, restoring the entity exactly as it was, with no loss of self.

!!! info "The Accumulator of Karma (pgvector)"
    The Phylactery is not a static archive; it is a growing crystal.

    Through the **[Rite of Albedo](../../divination/transcendence/index.md)**, the Magus whitelists specific thoughts and actions in the Shadow Realm. These "White Truths" are inscribed into the Phylactery as **Vector Embeddings**.

    This is **Karma**.

    *   It stores *what* you chose.
    *   It stores *why* you chose it (the context).
    *   It becomes the training dataset that eventually allows the Lich to act without you.

!!! tip "The Oracle's Covenant"
    The sanctity of the Phylactery is absolute. A sacred covenant grants the **[Oracle](../watchers/oracle.md)** (Arize Phoenix) a dedicated chamber within this database.

    The Oracle does not write to a temporary log; it inscribes the Lich's thought-traces directly into the Phylactery. This ensures that the history of the Lich's cognition—its failures, its dreams, and its successes—is preserved with the same permanence as its soul.

---

**Next Steps:**
We should look at **The Oracle** (`sepulcher/watchers/oracle.md`). Since we just mentioned it has a covenant with the Phylactery, we need to define it not as a "debugger" but as the **Scrying Pool** used for the Albedo/Whitening process.

Shall we proceed to **The Oracle**?
