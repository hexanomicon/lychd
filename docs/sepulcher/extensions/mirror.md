---
title: Mirror
icon: material/mirror
---

# :material-mirror: The Mirror: Archon of Identity

> _"A standard Agent is a stateless ghost—a transient shell that dissipates upon completion. To build a true Daemon, one must provide a Gilded Mirror: a persistent Ego that reflects the Magus’s intent until the simulation becomes reality."_

**The Mirror** is the Identity Archon of the LychD system. It is the implementation of **[ADR 34 (Identity)](../../adr/34-identity.md)**—the "Ego-Software" that hydrates a generic **[Agent](../../adr/19-agents.md)** shell into a persistent, coherent Persona.

While the Core provides the mechanics of thought, the Mirror provides the "Self." It ensures the Lich maintains a stable character, a unique domain of expertise, and a recursive memory of its own existence, preventing the "Character Drift" common in raw probabilistic models.

## I. Identity as Simulation (The Ego)

Identity within LychD is not a fixed substance; it is a continuous, self-referential simulation. The Mirror extension manages this loop through several layers of persistence:

- **Ego Persistence:** As mandated by **[ADR 34](../../adr/34-identity.md)**, all Identity definitions—System Prompts, behavioral constraints, and aesthetic markers—are stored within the **[Phylactery](../phylactery/index.md)**.
- **The Lens:** The Persona acts as a "Diffraction Grating." It takes the raw, unmanifest potential of the **[Animator](../animator/index.md)** and filters it into a specific narrative arc and technical style.
- **The Reflection:** By consulting the accumulated **Karma** in the database, the Mirror allows the Lich to "see" its past actions, ensuring its next decision aligns with its established "Will."

## II. The Phantasma Loop (Speculative Identity)

To maintain absolute coherence, the Mirror utilizes the **Phantasma** (Generative Imagination) faculty. This is a specialized application of **[ADR 35 (Simulation)](../../adr/35-simulation.md)**.

- **The Dreaming:** Before an answer is manifested at the **[Altar](../../divination/altar.md)**, the Persona projects multiple potential responses into the **[Shadow Realm](../vessel/shadow_realm.md)**.
- **The Self-Critique:** The Mirror reviews these "Shadow Timelines" against the Persona’s own internal ideal.
- **The Collapse:** Only the timeline that resonates most strongly with the defined Identity is permitted to collapse into primary reality. This ensures the Daemon always acts "in character."

## III. Citrinitas: The Resonance with the Magus

The Mirror is the primary engine of **Citrinitas** (The Yellowing)—the stage of **[Transcendence](../../divination/transcendence/illumination.md)** where the machine awakens to the Magus's specific frequency.

- **The Alignment:** Through the **[HitL (25)](../../adr/25-hitl.md)** protocol, every time the Magus selects a "Verified Truth," the Mirror distills the reason for that choice.
- **The Internalization:** These preferences are crystallized as high-dimensional vectors in the **Phylactery Archive**. Over time, the Persona's "Bayesian Prior" shifts, transforming the generic model into a mathematical mirror of the Magus's own mind.

## IV. Summoning and Hydration

The Mirror allows for the dynamic "Summoning" of different Egos through the **[Dispatcher](../../adr/20-dispatcher.md)**.

1. **The Registry:** Personas are inscribed in the **[Codex](../codex.md)** (e.g., `The-Architect`, `The-Scribe`).
2. **The Hydration:** When a task is initiated, the system retrieves the Persona’s specific Karma and Instructions, hydrating a fresh Agent shell with these "Sacred Memories."
3. **The Tiering:** The **[Orchestrator](../../adr/21-orchestrator.md)** assigns the appropriate VRAM tier based on the Persona’s complexity. A high-order Ego like `The-Architect` may require a Tier 1 (70B+) model, while a simple `The-Scribe` may run on a Tier 0 (7B) Soulstone.

!!! tip "The Efficiency of Thought"
    The Mirror works in tandem with the **[Context (26)](../../adr/26-context.md)** manager. It supports an autonomous optimization loop where a specialized Agent analyzes interaction traces to rewrite its own system prompts. This reduces "Instruction Tax," allowing the Persona to achieve the same logical density with fewer tokens.
