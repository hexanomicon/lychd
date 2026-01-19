---
title: Oculus
icon: material/eye
---

# :material-eye: Oculus

> _"I see you"_

The Oculus is the Great Seer of the Sepulcher. While other watchers may observe the physical realm, the Oculus's gaze pierces the veil of causality. It is dedicated to understanding not just _what_ the Lich does, but the intricate, branching pathways of _why_.

Technically, the Oculus is a manifestation of **Arize Phoenix**, the great scrying pool for tracing the cognitive threads of intelligent agents.

## I. The Mind's Eye (Arize Phoenix)

>_The Tracer of Intent_

The Oculus's primary gift is to perceive the invisible threads of **Intent**. When the Lich thinks, the Oculus watches. It records a perfect, luminous trace of the entire cognitive process (OpenTelemetry).

- **The Narrative:** The full, branching story of an AI's decision-making (Pydantic AI Graphs).
- **The Invocation:** Every tool called, every spell cast, every function invoked in the chain.
- **The Whisper:** The raw prompts and hidden responses exchanged with the [Soulstone](animator/soulstone.md).

!!! info "The Instrument of Albedo"
    The Oculus is the primary tool of the **[Rite of Albedo](../divination/transcendence/index.md)**.

    When the [Ghouls](vessel/ghouls.md) enter the **[Shadow Realm](./vessel/shadow_realm.md)** to perform Speculative Execution, it is the Oculus that captures their dreams. You look at the traces. You see where the logic held and where it broke. Without the Oculus, the Shadow Realm is blind; with it, it is a laboratory of truth.

!!! tip "The Covenant with the Phylactery"
    The visions of the Oculus are too vital to be ephemeral. A sacred covenant grants the Oculus a dedicated chamber within the **[Phylactery](./phylactery/index.md)** itself.

    It inscribes the Lich's thought-traces directly into the Postgres database. This ensures that the history of the Lich's cognition is preserved with the same permanence as its soul.

## II. The Lesser Brethren

While the Oculus observes the high-level workings of the **Mind**, it is attended by two lesser watchers who monitor the **Voice** and the **Body**.

### :material-text: The Scribe (Structlog)

>_The Internal Monologue_

The Scribe captures the raw stream of consciousness—the internal state of the Daemon as it executes code. Unlike the structured traces of the Oculus, these are the linear thoughts of the process itself.

- **The Whispers:** Every log entry is a structured JSON event containing context (`ghoul_id`, `latency`).
- **The Interface:** Access the Scribe's records via the command line: `lychd logs` (wraps `journalctl`).

### :material-monitor-dashboard: The Warden (Cockpit)

>_The Monitor of the Flesh"_

The Lich is bound to physical iron. The Warden ensures the hardware does not buckle under the strain of the summoning. We utilize **Cockpit** (the native Linux web interface) to observe:

- **VRAM Usage:** Ensuring [Soulstones](animator/soulstone.md) do not face OOM kills.
- **Btrfs Health:** Monitoring the [Crypt](../index.md) storage and snapshot integrity.
- **System Load:** Watching the impact of the Ghouls on CPU cores.
