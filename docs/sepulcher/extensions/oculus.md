---

title:  Oculus
icon: material/eye-outline
---

# :material-eye-outline: Oculus

> _"see the Ghost that pull the strings. To command the Daemon, one must not only witness its actions but scry the invisible web of intent from which they are born."_

**The Oculus** is the Observability Extension of the LychD system. It is the implementation of **[ADR 29 (Observability)](../../adr/29-observability.md)**—the all-seeing eye that bridges the gap between the physical "Body" (hardware) and the probabilistic "Mind" (agent logic).

While traditional tools see only network latency, the Oculus grants the Magus the power to view the entire **Thought Trace**—the complete causal chain from a whispered intent to its final manifestation. It transforms the invisible chaos of agentic reasoning into a structured, scryable record.

## I. The Thought Trace (The Mind's Eye)

The primary gift of the Oculus is the ability to see a thought as it forms. It rejects simple logging in favor of a deep, structural understanding of the cognitive loop.

- **The Retina:** Upon awakening, the extension grafts a "retina" onto the **[Vessel](../vessel/index.md)** and the **[Ghouls](../vessel/ghouls.md)**. This is a set of OpenTelemetry hooks that capture the internal monologue of every **[Agent](../../adr/20-agents.md)**.
- **The Scrying Pool:** These captured traces are exported to a specialized **Oculus Rune** (a container running Arize Phoenix). This local, high-fidelity interface allows the Magus to visualize the full execution tree, including tool calls, validation retries, and the raw whispers exchanged with the **[Animator](../animator/index.md)**.
- **The Permanent Record:** The visions in the pool are not fleeting. The Oculus inscribes them into a dedicated `traces` chamber within the **[Phylactery](../phylactery/index.md)**, ensuring that every significant thought becomes a permanent, reviewable part of the Daemon's history.

## II. The Body's Health (The Physical Gaze)

A mind cannot exist without a body. The extension understands that cognitive failure is often rooted in physical strain. However, it rejects the "Prometheus Tax"—the extreme overhead of containerized monitoring daemons.

- **Grounded Truth:** The Oculus utilizes the host's native monitoring tools (e.g., **Cockpit**) to observe the physical state of the machine.
- **The Orchestrator's Sight:** This data is fed directly into the **[Orchestrator](../../adr/23-orchestrator.md)**. If the GPU VRAM pressure exceeds a critical threshold, the Oculus signals the Orchestrator to pause low-priority rituals (like **[Training](./soulforge.md)**) to prevent an OOM crash.

## III. The Privacy Veil

The Oculus sees all, and such power demands absolute discipline. It is bound by a sacred vow to protect the Magus's secrets.

- **The Redaction:** The extension respects the global `LYCHD_SECURE_MODE` toggle. When this mode is active, the telemetry provider draws a "Privacy Veil" over its sight.
- **Structure Over Substance:** This ensures that the _structure_ of the thought (latency, tool success, token counts) is preserved for debugging, while the _substance_ (sensitive prompts, private keys, or secret whispers) is physically redacted before ever leaving the application's memory.

## IV. Trace Hygiene (The Reaper's Bond)

The Oculus generates massive quantities of data. To prevent the Crypt from filling with the noise of the past, the extension clears its phylactery data.

- **TTL Enforcement:** Traces are tagged with a Time-To-Live.
    - _Standard Traces:_ Retained for 24 hours.
    - _Error Traces:_ Retained for 7 days.
    - _Consecrated Traces:_ Retained forever.
- **The Purge:** The Reaper periodically sweeps the `traces` chamber, banishing expired records to the Void to maintain the health of the Phylactery.

!!! failure "The Fragmented Gaze"
    The price for rejecting the "Prometheus Tax" is a fragmented dashboard. To correlate a slow Agent response (Mind) with high GPU utilization (Body), the Magus must look at two separate altars: the **Oculus Scrying Pool** and the host's **Cockpit** interface. This is the trade-off made to keep the Sepulcher lightweight and sovereign.
