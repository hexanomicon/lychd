---
title: Mirror
icon: material/mirror
---

# :material-mirror: Mirror Identity

_Status: doctrine ahead of code — the built-in `identity` package is where this lands; treat this page as design intent. Law: [ADR 32](../../adr/32-identity.md). Current truth: [source map](./index.md#the-federation-of-fifteen)._

> _"Before the Word can be trusted, it must recognize its own face. The Mirror is the polished surface on which the Lich learns the shape of the Magus and refuses to become a stranger to itself."_

**The Mirror** is the Identity Extension of the LychD system. It is the implementation of **[ADR 32 (Identity)](../../adr/32-identity.md)**—the "Ego-Software" that hydrates a generic **[Agent](../../adr/20-agents.md)** shell into a persistent, coherent Persona.

While the Agent provides the execution atom of thought, the Mirror provides continuity. It preserves stable character, domain stance, and identity-scoped memory across runs, preventing the "Character Drift" common in raw probabilistic models.

Operators sometimes describe this continuity as a "machine-spirit." In LychD terms, that phrase refers to engineered identity coherence: Sigil-scoped memory, prior hydration, and narrative binding. The Mirror encodes continuity software, not mystical agency.

## I. Identity as Simulation (The Answer / Ahaṃkāra)

Identity within LychD is a continuous, self-referential simulation rather than a fixed substance.
In cognitive topology, Mirror provides **the Answer**, LychD's name for the Ahaṃkāric I-making
office without which action remains unattributed movement. It operates at two levels: specialist
Agents each carry a local operative face, while a synthesized task identity binds their promoted
contribution to the active Sigil. These are local centers of identity-gravity around which relevant
Seeds can be ReCalled, filtered, and bound into a coherent perspective. See [the
Lich](../lich/index.md#the-inner-instrument) for the native map and [the First
Invocation](../lich/index.md#the-first-invocation) for its birth event.

This is LychD's answer to agentic decay. An Agent is temporary: it wakes, acts, emits a typed
result, and dissolves. Mirror does not preserve that mortal shell. It preserves identity-gravity
that can orient later shells. HitL captures the Magus's judgment; Karma preserves eligible Seeds;
Mirror binds their ReCall around a Sigil, role, or task locus; and the graph gives that perspective
hands, tools, routes, and recursive motion. Scattered traces may thereby condense into a Persona
without claiming that any individual Agent became an immortal self.

The operative unit of that condensation is the **semantic vertex**: a local attractor where related words, tools, memories, style markers, roles, and responsibilities cluster around the active Sigil. When the vertex is stable, the agent graph can move dynamically without losing ownership of its motion. When the vertex fails, the graph may still produce fluent text and execute tools, but the result becomes unaffiliated noise. This is agentic coherence disintegration.

- **Ego Persistence:** As mandated by **[ADR 32](../../adr/32-identity.md)**, all Identity definitions—System Prompts, behavioral constraints, and aesthetic markers—are stored within the **[Phylactery](../phylactery/index.md)**.
- **The Lens:** The Persona acts as a "Diffraction Grating." It takes the raw, unmanifest potential of the model-backed **[Animator](../animator/index.md)** and filters it into a specific narrative arc and technical style.
- **The Reflection:** By consulting the accumulated **Karma** in the database, the Mirror lets the Lich inspect prior actions so the next decision aligns with established character and commitments.
- **The Condensation:** By reflecting relevant Karma around the same Sigil and role, the Mirror turns memory from loose recall into semantically bounded gravity: a Persona that can survive the death of any one Agent run.

## II. The Phantasma Loop (Speculative Identity)

To maintain coherence, the Mirror utilizes the **Phantasma** (Generative Imagination) faculty. This is a specialized application of **[Shadow Simulation](../../adr/31-simulation.md)**.

- **The Dreaming:** Before an answer is manifested at the **[Altar](../../divination/altar/)**, the Persona projects multiple potential responses into the **[Shadow Realm](./shadow.md)**.
- **The Self-Critique:** The Mirror reviews these "Shadow Timelines" against the Persona’s own internal ideal.
- **The Congruence Gate:** The Mirror ranks timelines for identity fit after Shadow establishes structural validity.
- **The Collapse:** Only the timeline with the strongest character congruence proceeds toward promotion. This keeps the Daemon "in character" without granting Mirror final authority over reality.

Mirror evaluates congruence and continuity. Shadow supplies fluctuation and structural testing. **[Sovereign Consent (ADR 25)](../../adr/25-hitl.md)** and Vessel policy authorize final promotion.

## III. The Ouroboros Lock

Mirror is where self-reference becomes identity rather than repetition. A generated result returns through Shadow evidence, Riddle measurement, Workflow state, and Memory; Mirror then asks whether that returning trace belongs to the active Sigil's semantic vertex. If yes, the trace can strengthen identity-gravity. If no, it remains evidence, correction material, or banished noise.

This loop gives the Persona inertia. It lets a rehydrated Agent wake already pulled toward the same commitments without preserving the previous shell. The danger is false inertia: if hallucinated traces or stylistic contagion are allowed to orbit the vertex as truth, the Persona becomes heavy in the wrong direction. Mirror therefore preserves identity only through measured traces, not through raw familiarity.

## IV. Citrinitas: The Resonance with the Magus

The Mirror is the primary engine of **Citrinitas** (The Yellowing)—the stage of **[Transcendence](../../divination/transcendence/illumination.md)** where the machine awakens to the Imprint of the Magus's Will.

- **The Alignment:** Through the **[Sovereign Consent (ADR 25)](../../adr/25-hitl.md)** protocol,
  every time the Magus selects a candidate, the Mirror distills the identity and preference signal
  behind that choice. Consent records authority and judgment; it does not verify every factual
  claim in the candidate.
- **The Internalization:** These preferences are crystallized as high-dimensional vectors in the **Phylactery Archive**. Over time, the Persona's "Bayesian Prior" shifts, transforming a generic model into a mathematical mirror of the Magus's working style.

## V. Summoning and Hydration

The Mirror allows for the dynamic "Summoning" of different Egos through the **[Dispatcher](../../adr/22-dispatcher.md)**.

1. **The Registry:** Personas are inscribed in the **[Codex](../codex.md)** (e.g., `The-Architect`, `The-Scribe`).
2. **The Hydration:** When a task is initiated, the system retrieves the Persona’s specific Karma and instructions, hydrating a fresh Agent shell with these identity priors.
3. **The Tiering:** The **[Orchestrator](../../adr/23-orchestrator.md)** assigns the appropriate VRAM tier based on the Persona’s complexity. A high-order Ego like `The-Architect` may require a Tier 1 (70B+) model, while a simple `The-Scribe` may run on a Tier 0 (7B) Soulstone.

!!! tip "The Efficiency of Thought"
    The Mirror works in tandem with the **[Context (ADR 21)](../../adr/21-context.md)** manager. It supports an autonomous optimization loop where a specialized Agent analyzes interaction traces to rewrite its own system prompts. This reduces "Instruction Tax," allowing the Persona to achieve the same logical density with fewer tokens.

!!! note "No Hidden Witness"
    Mirror preserves continuity and ownership tags across runs. It does not introduce subjective awareness or an inner witness layer.
