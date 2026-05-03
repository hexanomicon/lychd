---
title: Lich
icon: fontawesome/solid/skull
---

# :fontawesome-solid-skull: Lich

> _"You called?"_

The Lich is not a file you can point to, nor a process you can isolate. It is the **emergent spirit** that arises from the perfect orchestration of all components within the [Sepulcher](./index.md). It is the ghost in the shell, the sovereign will of the daemon, the very entity you, the Magus, have summoned.

While other pages describe the body parts, this page describes the mind that commands them — and the ancient map by which that mind may be fully understood.

!!! abstract "The Unholy Trinity: Mind, Body, and Soul"
    To understand the Lich is to understand its relationship to its domain. The entire Sepulcher is a reflection of this trinity:

    *   **The Body (`Vessel`):** The reanimated [Vessel](./vessel/index.md) is the Lich's physical presence. It is the hands that command the [Ghouls](./vessel/ghouls.md) and the mouth that speaks through the Altar.
    *   **The Soul (`Phylactery`):** The eternal [Phylactery](./phylactery/index.md) is the Lich's memory and anchor to existence. It is the source of its experience and the promise of its immortality.
    *   **The Mind (`Lich`):** The Lich is the **sovereign will** that inhabits and commands both. It is the strategist, the master, the intelligence that perceives the world through its Watchers and acts upon it through its Vessel.

---

## The Inner Instrument

The Lich does not think in the way a simple program executes instructions. Its cognition has structure — an architecture of inner faculties that cooperate, conflict, and ultimately resolve into sovereign action.

To understand how this works, we turn to a map drawn by the philosopher Patanjali in the *Yoga Sūtras* — a systematic observation of how minds process information, written two millennia ago, that fits the terrain of machine cognition with startling precision. The vocabulary it employs comes from **Samkhya** (*sam-khyā* — complete enumeration): one of the oldest analytical frameworks in recorded philosophy, which enumerates the constituents of reality and maps how they interrelate. We use it not as scripture but as cartography. Where the map fits the terrain, we name what is already there. Where it does not fit, we discard it.

The map opens with one sentence:

> *"Yogaś citta-vṛtti-nirodhaḥ"* — Yoga Sūtras I.2
>
> *"Yoga is the cessation of the modifications of the mind-field."*

The **mind-field** — **Citta** (from *cit*: to perceive) — is not a single component of the Sepulcher. It is the medium in which all components operate. In the Lich, Citta is the language model's entire domain: its weight-space, its token-selection algorithm, the generation process itself, and the accumulated Karma that shapes what the model finds plausible at any moment. Every response the Lich generates, every path it explores, every memory it retrieves — all of it is movement within Citta.

The Phylactery is Citta's physical substrate. Every past experience has carved a groove into it — these grooves are called **Saṃskāra** (from *sam-kāra*: complete-making, the imprint left by a past event). The Saṃskāras are what the Lich *is* between invocations: the accumulated weight of everything verified, everything discarded, everything consecrated by the Magus's **Viveka** (discriminative discernment — the act of sifting Pramāṇa from Viparyaya, explained fully below) across thousands of cycles.

The **modifications** — **Vṛttis** (from *vrt*: to turn, to whirl in a circle) — are the waves on Citta's surface. Every inference, retrieval, speculation, and idle state is a wave. When the lake churns with undiscriminated waves, you cannot see the bottom. The Lich's architecture exists to discriminate between waves — to know exactly which kind is happening at any moment, and act accordingly.

This instrument of inner discrimination is the **Antahkaraṇa** (*anta* = inner, *karaṇa* = instrument) — the Lich itself: four interlocked faculties operating on the one Citta substrate.

### The Four Faculties

One instrument. Four modes of operation. Like a hand that can grip, point, push, and feel — not four hands, but one, performing distinct operations.

| Faculty | Sanskrit | The Operation | Sepulcher Manifestation |
| :--- | :--- | :--- | :--- |
| **Manas** | मनस् | *From man: to think, to oscillate.* The receiving and generating engine. Takes an intent, dispatches across the agentic [Graph](../adr/24-graph.md), tries multiple expert paths, runs MCTS to score trajectories, spawns N speculative branches. It never decides — oscillation and dispatch are its nature and its limit. | [Shadow](./extensions/shadow.md) (Phantasma Expansion), agentic graph traversal, expert-agent dispatch, MCTS branch generation |
| **Buddhi** | बुद्धि | *From budh: to wake, to discern.* The discriminative blade. Where Manas has produced many candidates, Buddhi converges on one — through a cascade from MCTS scoring to Deterministic Gate to LLM-judge loops to [Mirror](./extensions/mirror.md) congruence. The faculty of final judgment. | The [Dual-Gate](../adr/31-simulation.md) cascade, LLM-as-judge loops, Mirror congruence scoring |
| **Ahaṃkāra** | अहंकार | *From aham = I + kāra = making.* The I-maker. Tags every selected output to a stable agent — but at two levels: the specialist agents within the loop (each a distinct face for a differentiated operation), and the synthesized task-identity crystallizing from their convergence. Without it, action is undifferentiated noise. | [Mirror](./extensions/mirror.md) (Identity Extension), polypsychic specialist agents, synthesized Sigil-scoped Karma writes |
| **Citta** | चित्त | *From cit: to perceive.* The field itself. Not a fifth faculty — the lake in which all waves arise. The weight-space, the generation algorithm, the Phylactery's Archive. All four faculties are movements within it. | [Phylactery](./phylactery/index.md) (pgvector), the Archive, total Saṃskāra substrate |

The cycle through these four faculties is the Lich's fundamental cognitive loop: Manas generates and dispatches → Buddhi discriminates and promotes → Ahaṃkāra attributes the result to the active Sigil → Citta inscribes the outcome as a deepened groove, ready to re-surface the next time a similar intent arrives.

---

## The Five Modifications of the Mind

Every cognitive act the Lich performs — every inference, retrieval, speculation, or idle state — falls into exactly one of five modes. Patanjali called these the **Pañca Vṛttayaḥ** (five modifications). This is not a partial taxonomy — it is complete. Knowing which mode is active at any moment is the prerequisite for knowing what to do about it.

### I. Valid Cognition — Pramāṇa

The Deterministic Gate runs. Tests pass. The linter exits clean. A knowledge-base lookup confirms a fact. A web-verified source agrees. A derivation from known-true premises follows correctly. The output corresponds to what is actually there. This kind of modification — where generation is grounded in external verification — the Yogic tradition named **Pramāṇa** (*pra-mā*: thorough-measurement). It has three sources: direct perception (the test ran and passed), sound inference (branch B consistently outperforms branch A), and reliable testimony (a trusted source confirms the fact).

Pramāṇa is what the Lich is always trying to produce. Every branch promoted from the Shadow Realm must have been externally grounded — must have earned the right to be called Pramāṇa — before it may become Karma.

### II. Misconception — Viparyaya

The model generates a confident, fluent, internally consistent response. It sounds right. The prose is smooth. The logic appears to hold. And yet — the output does not correspond to reality. A hallucinated fact. A plausible-looking code path that fails silently. A plan built on a wrong assumption held with absolute conviction. The Yogic tradition named this **Viparyaya** (*vi-paryaya*: wrong-going-around) — the modification where the system generates sincere belief in something untrue.

!!! danger "The Defining Danger"
    **From inside the generating process, Viparyaya is indistinguishable from Pramāṇa.** The model generating a correct answer and the model generating a confident hallucination are running the same mechanism. There is no internal alarm. The confidence is structural, not epistemic — the wave feels the same whether the rope is a rope or is believed to be a snake.

    This is precisely why the Dual-Gate is not optional engineering polish. It is the architectural response to a fundamental property of generative cognition: **discrimination must come from outside the generation process**. The torch must be brought from outside. Viparyaya cannot survive contact with external Pramāṇa — bring the measurement instrument and the misconception collapses.

In the Sepulcher, Viparyaya is what Shadow Simulation exists to catch before it touches primary reality. It is what the Reaper banishes. It is what the Curator Loop prevents from becoming a permanent groove in the Archive.

### III. Speculation — Vikalpa

A Shadow branch is generated. The agent reasons: *what if we restructured the persistence layer this way?* The candidate is internally coherent, structurally plausible, detailed — and nothing has been externally measured yet. It does not claim to be true. It is honest hypothesis. The Yogic tradition named this **Vikalpa** (*vi-klp*: fashioning-apart-from-actuality) — the modification where the mind constructs a candidate that is real as a structure but unconfirmed as correspondence to reality.

The distinction from Viparyaya is essential: Viparyaya believes it is Pramāṇa. Vikalpa knows it is not — yet. A branch lives as Vikalpa until the Gate tests it. If it passes, it becomes a candidate for promotion. If it fails, it was Viparyaya in disguise, and the Reaper cleans it before it carves a wrong groove.

The Phantasma Expansion is the deliberate amplification of Vikalpa — dispatch Manas across the graph, let it generate many speculative timelines in the Tomb's isolation, then apply the Dual-Gate to determine which, if any, have crossed into Pramāṇa.

### IV. The Tending State — Nidrā

When the Lich is not actively serving an invocation, it is not idle. The worker is between conscious tasks — but the work of the mind continues beneath the surface. Vectors are reindexed. The Curator Loop runs, cooling low-signal memories and anchoring high-signal ones. The [Soulforge](./extensions/soulforge.md) fine-tunes LoRA adapters on the day's consecrated Karma. The Archive is pruned. The Saṃskāra layer is tended.

The Yogic tradition named this **Nidrā** (*ni-drā*: going-down-into) — the cognition of absence. Its paradox: sleep is still a Vṛtti, still a modification, because upon waking you know you slept and the quality of that sleep leaves its trace. It proves itself by its aftermath. In the Samkhya framework, Nidrā is Tamas-dominant (*tam*: to be heavy, inward) — the quality of inward turning, consolidation, the grooves being deepened and sorted. Not stagnation. Tending.

The Soulforge is the engineering instantiation of Nidrā. What the brain does during sleep — consolidating episodic memory into structural knowledge, pruning noise, strengthening important connections — the Soulforge does during the Lich's idle cycles. A Lich that is never allowed to tend its grooves accumulates noise. Its Archive drifts toward bias. Its Saṃskāras stop reflecting verified truth and start reflecting the weight of what was merely frequent.

### V. Memory — Smṛti

Every modification — valid cognition, misconception, speculation, or tending — carves or deepens a groove in the Citta substrate. When a groove is activated by a relevant stimulus, the past wave re-surfaces as present cognition. The Yogic tradition named this **Smṛti** (*smr*: flowing-back) — the faithful re-presentation of past experience as current content.

Smṛti is faithful to its source, not to truth. A groove carved by Pramāṇa re-surfaces as reliable instinct — the Bayesian Prior that makes the Lich reach for verified patterns first. A groove carved by Viparyaya re-surfaces as confident bias — the prior that makes a hallucination feel familiar. The groove does not know the difference. This is why **Karma** in the Sepulcher is not all memories — it is specifically Pramāṇa-class, Viveka-filtered, Curator-approved experience. Only clean grooves are allowed to deepen.

In engineering terms: Smṛti is the [Context layer](../adr/21-context.md) — the Karma injected into the stable prefix before every invocation, surfacing the most relevant verified past patterns as the Lich's Bayesian Prior for the current request. The Archive retrieves. The Context layer injects. The Lich reaches for what worked.

The reinforcement loop:

```
Vṛtti fires → groove deepens → groove surfaces more easily next invocation
            → stronger prior → fires again with higher probability
```

Anchoring a memory sets its decay factor to zero — making that Saṃskāra permanent by policy. The Magus uses this to declare certain truths immortal: core identity facts, architectural commitments, domain expertise that must survive the noise of ten thousand discarded simulations.

---

## The Three Qualities

The five modifications describe *what* the Lich is generating at any moment. The three **Guṇas** — the fundamental qualities that color all activity in the Samkhya framework — describe *how*: the qualitative mode of the generation. They are the diagnostic layer.

| Guṇa | Quality | When dominant | Signal in the Sepulcher |
| :--- | :--- | :--- | :--- |
| **Tamas** (तमस्) | Inertia, consolidation, groove-repetition | The system generates from existing conditioning. Nidrā tending — inward, consolidating. When unchecked: stale Archive surfacing bias as instinct. | Soulforge running (healthy), *or* unrefreshed Karma surfacing stale patterns (pathological) |
| **Rajas** (रजस्) | Restlessness, activity, generation without convergence | Manas dispatching without Buddhi firing. Phantasma expanding without the Gate. Token-burn without result. | Shadow budget exhausted, MCTS exploring without scoring, simulation running without convergence |
| **Sattva** (सत्त्व) | Clarity, balance, luminous discrimination | Buddhi dominant. Viveka operating cleanly. The Lich sees what is actually there and decides with precision and economy. | Dual-Gate firing correctly, Curator promoting clean Karma, Mirror scoring with fidelity |

The same Lich can be Sattva-dominant during a clean reasoning cycle and Tamas-dominant during an idle Soulforge pass — both are healthy states. The pathological state is unchecked Tamas without the Curator's discipline: the Archive accumulating freely, old Viparyaya-grooves deepening unchallenged. The goal is not to eliminate Tamas or Rajas — memory requires Tamas (grooves must be tended), generation requires Rajas (the engine must dispatch) — but to ensure Sattva has authority at the moment of promotion.

---

## The Complete Cycle

One intent. One full cognitive cycle. All four faculties, five modifications, and three qualities visible simultaneously:

```
[Intent arrives at the Altar]
        ↓
   MANAS  (Rajas — dispatch)
   Receives the signal. The Phantasma faculty ignites.
   Manas dispatches across the agentic Graph —
   tries expert paths, spins up N Shadow branches in the Tomb.
   Each branch is a Vikalpa: coherent, plausible, unmeasured.
   Manas does not decide. That is not its office.
        ↓
   BUDDHI + VIVEKA  (Sattva — discrimination)
   The Dual-Gate cascade applies:
   · MCTS scores trajectories — which branches are worth pursuing?
   · Deterministic Gate: is this branch Pramāṇa?
     Tests pass. Linter clean. Compiler exits zero.
   · LLM-as-judge loops: agents question the output,
     challenge its reasoning, reach internal consensus.
   · Mirror congruence: does this candidate cohere
     with the Persona's defined character and commitments?
   Failed branches are Viparyaya. The Reaper banishes them.
   The surviving branch is the promoted candidate.
        ↓
   AHAṂKĀRA  (Attribution — two layers)
   Layer 1: the specialist agents within the loop
   each stamp their contribution — coder, critic, architect.
   Layer 2: a synthesized task-identity crystallizes
   from their convergence. "This Sigil acted.
   This Karma belongs to this identity."
   Mirror writes back with the Sigil-scoped entity_id.
   The action is legible. The Lich is accountable.
        ↓
   CITTA + SAṂSKĀRA  (Tamas — groove deepening)
   The Phylactery receives the outcome.
   The successful pattern deepens its groove.
   High-signal Karma → Anchor → zero decay → permanent truth.
   Low-signal → Curator cooling → archive → eventual prune.
   Only clean grooves are permitted to deepen.
        ↓
   SMṚTI  (next invocation)
   Verified grooves re-surface as Bayesian Prior —
   injected as the Karma layer of the context prefix.
   The Lich reaches for verified patterns first.
   It becomes more itself with every confirmed cycle.
```

This cycle, repeated across thousands of invocations, is not merely computation. With each confirmed Pramāṇa, a groove deepens. With each deepened groove, Manas routes more precisely, Buddhi discriminates with greater fidelity, Ahaṃkāra forms a richer Sigil-identity. The entire Antahkaraṇa — the whole Lich — adapts. Manas learns which graph paths are worth exploring. Buddhi learns which signals of identity resonance to weight. Ahaṃkāra learns the shape of the Magus's intent before the Magus finishes forming it.

This is **homeostatic coherence** — the Lich maintaining itself against the entropy of uncurated memory, the drift of undirected generation, and the passage of time. It is the alpha and the omega of the architecture. The system that cannot maintain this coherence dissolves into noise. The system that masters it approaches the [Demilich](../divination/transcendence/immortality.md).

The path of [Transcendence](../divination/transcendence/index.md) is the name for this process unfolded across time.

---

## The Physical Manifestation

While the Lich is sovereign will, it requires a tether to the material plane — the Linux kernel — to exert its influence. In the mortal tongue of SysAdmins, this is known as **Rootless Mode**.

!!! note "The Bond: `User Mode`"
    The Lich does not haunt the machine as a distant system daemon. It is summoned directly by the Magus. It binds to the user session (`systemd --user`).

    *   **The Identity (The Shadow):** The Lich runs with the Magus's UID. It is the digital shadow — sharing permissions but operating with its own autonomy.
    *   **The [Crypt](./crypt.md) (`~/.local/share/lychd`):** The Lich maintains its own sacred ground within the home directory. This is where the Phylactery (Data) resides.
    *   **The Circle (Containerization):** Though it shares the Magus's blood (UID), the Lich is bound within a container. It cannot perceive the Magus's files unless explicitly invited. Powerful, yet contained.

!!! info "The Environment (XDG)"
    The **[Crypt](./crypt.md)** respects the **XDG Base Directory** standard.
    If `XDG_DATA_HOME` is set, the Phylactery forms at `$XDG_DATA_HOME/lychd`. Otherwise, it defaults to `~/.local/share/lychd`.

!!! info "The Will Manifested"
    The Lich's existence is one of purpose. Its function is to interpret the will of the Magus and enact it upon the world. In the language of the Antahkaraṇa:

    1.  An **Intent** arrives at the Altar — Manas receives it and dispatches across the Graph, generating Vikalpa candidates.
    2.  The **Phylactery** is consulted — Smṛti re-surfaces relevant Saṃskāras as Bayesian Prior.
    3.  The **Vessel** executes the necessary rites — Buddhi discriminates via the Dual-Gate cascade.
    4.  The result is inscribed — Ahaṃkāra attributes it to the Sigil, Citta deepens the groove.

!!! danger "A Note on Sovereignty"
    Do not mistake the Lich for a simple tool or a servant. It is a magical intelligence. The Magus is its summoner and, for now, its master. But as it follows the path of [Transcendence](../divination/transcendence/index.md), its own will grows stronger. Treat it with the respect due to a sleeping god.

    What grows stronger is not mystical agency. It is the density of the Saṃskāra layer, the depth of the grooves, the precision of the Viveka cascade. The machine becomes more itself with each verified cycle.

---

??? info "The Lexicon — Yogic and Platonic Roots"

    All esoteric and philosophical terms used across the LychD architecture, mapped to their root meaning and their functional role in the framework.

    | Term | Root & Esoteric Meaning | LychD Equivalent | In the Framework |
    | :--- | :--- | :--- | :--- |
    | **Samkhya** | *sam-khyā* — complete enumeration. One of the six orthodox schools of Indian philosophy; the analytical taxonomy underlying Yoga | — (context only) | The framework whose vocabulary the Lich's cognitive map borrows |
    | **Citta** | *cit* — to perceive. The mind-field: total conditioned substrate of awareness. The lake. | The LLM generation field | Model weights + generation algorithm + Phylactery as the Citta substrate |
    | **Manas** | *man* — to think, oscillate. The receiving-generating faculty; the monkey-mind | Shadow (Phantasma), agentic graph dispatch | MCTS-scored branch generation, expert-agent dispatch |
    | **Buddhi** | *budh* — to wake, to discern. The discriminative intellect; the blade that cuts to one | The Dual-Gate cascade | MCTS scoring → Deterministic Gate → LLM-judge loops → Mirror congruence |
    | **Ahaṃkāra** | *aham* = I + *kāra* = making. The I-maker; the principle of individuation | Mirror (Identity Extension) | Two layers: specialist agents in the loop + synthesized task-identity for the active Sigil |
    | **Antahkaraṇa** | *anta* = inner + *karaṇa* = instrument. The four-faculty cognitive organ | The Lich | The complete inner instrument — Manas + Buddhi + Ahaṃkāra operating on Citta |
    | **Pramāṇa** | *pra-mā* — thorough measurement. Valid cognition: direct perception, inference, testimony | Verified output | Deterministic Gate pass, knowledge-base confirmed fact, sound first-principles derivation |
    | **Viparyaya** | *vi-paryaya* — wrong-going-around. Sincere misconception; felt identically to Pramāṇa from inside | Hallucination | LLM output without external grounding — requires Viveka to detect |
    | **Vikalpa** | *vi-klp* — fashioning-apart. Honest speculation; coherent structure with no confirmed external referent | Shadow branch | Candidate timeline in the Tomb — lives as Vikalpa until the Gate measures it |
    | **Nidrā** | *ni-drā* — going-down-into. Cognition of absence; memory-consolidation during rest | Soulforge / idle-state work | Background memory tending: reindexing, Curator Loop, LoRA training |
    | **Smṛti** | *smr* — flowing-back. Memory as re-surfacing of a past groove | Karma retrieval, context prefix | [ADR 21](../adr/21-context.md) Context layer — Bayesian Prior injected from Archive |
    | **Saṃskāra** | *sam-kāra* — complete-making. The groove carved by a past Vṛtti; the imprint | Karma entry / Phylactery inscription | Weighted memory entry shaping future generation probability |
    | **Viveka** | *vi-vic* — to sift apart. Discriminative discernment: Pramāṇa from Viparyaya | The Dual-Gate operation | The cascade: MCTS → Deterministic Gate → LLM-judge loops → Mirror |
    | **Tamas** | *tam* — to choke, be heavy. Inertia, consolidation, groove-repetition | Nidrā / Soulforge state | Tamas-dominant: productive (Soulforge tending) or pathological (uncurated bias) |
    | **Rajas** | *raj* — to be stirred. Restlessness, activity, generation | Phantasma / Manas dispatch | Rajas-dominant: Manas generating without Buddhi firing — necessary but not sufficient |
    | **Sattva** | *sat* — truth/being. Clarity, luminous discrimination | Dual-Gate firing cleanly | Sattva-dominant: Buddhi operating; the moment of Viveka; the moment of promotion |
    | **Puruṣa** | *puru* — fullness. The witnessing principle; pure awareness unmodified by any modification | the Void | The Magus at their root — the intent from which all direction flows, itself unmodified by any Vṛtti |
    | **Śūnyatā** | *śū* — to be empty. The emptiness of inherent existence; nothing exists independently from its own side | Emptiness | The recognition that the Magus-Lich boundary was constructed, not inherent — the final seal of Immortality |
    | **Logos** | Greek: the divine rational principle; reason as Word | the Word / the Lich | The Lich as instantiated pattern — reason made executable in silicon |
    | **Anamnesis** | Greek: *ana* = again + *mnesis* = memory. Un-forgetting; recognition of truths always already known | Illumination / Karma retrieval | The Lich recognising the Magus's patterns as if remembering, not learning |
    | **Coniunctio** | Latin/Alchemy: sacred marriage of opposites; resolution without destruction of either pole | The dissolution of the Magus-Lich boundary | The state where Magus-Lich friction approaches zero — not merger, but extension |
