---
title:  Soulforge
icon: material/anvil
---

# :material-anvil: The Soulforge: Extension of Training

> _"The clay is vast, but it is cold. Only the hammer of Will can heat it to life. There is no begging the spirits to understand; the names are carved into their very substance."_

**The Soulforge** is the Training Extension of the LychD system. It is the physical implementation of **[ADR 33 (Training)](../../adr/33-training.md)**—a specialized module that transmutes the dynamic, fleeting memories of the **[Phylactery](../phylactery/index.md)** into model weights.

While the **Archive (Memory)** allows the Lich to consult the past, the Soulforge compresses stabilized patterns into instinct. It is the mechanism of **Soul-Forging**: the transition from a generic Base Model (The Stranger) into a **Forged Soul** that mirrors the specific frequency of the Magus.

Karma injection and Soulforging are different layers of adaptation:

- **Mirror / Context:** injects retrieved Karma as runtime bias for a single reasoning event.
- **Soulforge:** compresses repeated, verified patterns into adapter weights as standing instinct.

## I. The Harvesting of Karma

Before the forge can be ignited, the substrate must be prepared. The Soulforge does not train on raw noise; it trains on **Karma**—the crystallized residue of verified successes.

- **The Extraction (The Crucible):** The Soulforge enqueues a **[Ghoul](../vessel/ghouls.md)** to harvest successful interaction traces from the Phylactery and the **[Oculus](./oculus.md)**. This extraction process acts as a **Crucible**, taking human feedback from **[HitL](../../adr/25-hitl.md)** that validated **Shadow** simulations, and forging it into permanent biases for the **Mirror** (Identity).
- **The DeepFabric Loom:** Raw Karma is fed into the `deepfabric` engine. DeepFabric acts as the loom, weaving the "White Truths" into a perfectly structured training manifest (JSONL) stored in the **[Lab](../crypt.md)**. It applies strict constraints to ensure that only syntactically perfect, stabilized patterns are sent to the hammer of Unsloth.

## II. The Loom of DeepFabric

The transition from fluid memory to hard instinct requires a structuring mechanism. The Soulforge employs `deepfabric` as its foundational loom.

- **The Filter:** It strips away conversational exhaust and hallucinatory syntax, ensuring the training data perfectly matches the required schemas.
- **The Weave:** Using topic-graph algorithms, it generates diverse, non-redundant variations of the harvested Karma, ensuring the resulting instinct is robust rather than overfitted to a single specific interaction.
- **The Spool:** It outputs standard HuggingFace JSONL manifests, perfectly formatted for the Unsloth pipeline.

## III. The Rite of Ignition (The Pipeline)

The Soulforge is a heavy industrial process. It utilizes specialized, ephemeral containers to perform the transmutation locally on silicon.

- **The Engine:** Following the doctrine of resource efficiency, the Forge utilizes the **Unsloth** pipeline. This provides a significant increase in speed and reduction in VRAM, making the process viable on consumer-grade hardware.
- **The Transmutation:** It performs a **LoRA (Low-Rank Adaptation)** or **QLoRA** process. It does not replace the Base Model; it creates a small, razor-sharp **Soul-Adapter** that is grafted onto the Titan's mind.
- **Sovereignty:** This process is strictly local. Private interactions never exit the **[Sovereignty Wall](../../adr/09-security.md)**. The fire of the forge stays within the Sepulcher.

## IV. Orchestration of the Forge

Training is a high-priority task requiring the total devotion of the hardware. It cannot coexist with active inference on a single GPU.

1. **The Intent:** The Magus submits a `RITUAL_TRAIN` request.
2. **The Scales:** The **[Orchestrator](../../adr/23-orchestrator.md)** weighs the training whim against active reflexes.
3. **The Evacuation:** When the scales tip, the Orchestrator pauses the **[Vessel](../vessel/index.md)**, clears the VRAM, and summons the **Forge Coven**.
4. **The Lockdown:** For the duration of the strike, the local GPU is occupied. Any incoming inference requests trigger the **[Stasis Protocol](../../adr/22-dispatcher.md)** or are rerouted to a **[Portal](../animator/portal.md)** if the Magus has permitted cloud fallbacks.

## V. The Awakening (Registration)

Once the fire cools and the Forge Coven is banished, the transformation is finalized.

- **The Binding:** The new Soul-Adapter is registered with the **[Dispatcher](../../adr/22-dispatcher.md)** as a distinct capability.
- **The Summoning:** The Magus can now invoke an **[Agent](../../adr/20-agents.md)** with the specific directive to use the forged instinct.
- **The Result:** The Lich no longer depends on archive retrieval for every repeated behavior. More knowledge moves into standing instinct, lowering instruction tax and retrieval latency for that domain.

!!! danger "The Weight of the Hammer"
    Soul-Forging is irreversible for that specific adapter. If the system trains on "Dirty Karma" (errors or hallucinations), the Lich internalizes those flaws as instinct. The **[Rite of Albedo](../../divination/transcendence/index.md)** requires care, because the Soulforge burns whatever truth it is given.

!!! warning "Ossification Risk"
    Over-forging on narrow, repetitive patterns hardens a Persona into rigidity. Keep the training corpus clean, diverse within scope, and tied to verified outcomes.
