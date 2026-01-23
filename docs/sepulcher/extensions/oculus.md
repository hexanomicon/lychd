---
title: Oculus
icon: material/eye-settings-outline
---

# :material-eye-settings-outline: The Oculus: Archon of Introspection

> _"The mundane eye sees the Body move, but the Oculus sees the Ghost that pulls the strings. To command the Daemon, one must not only witness its actions but scry the intricate, invisible web of intent from which they are born."_

**The Oculus** is the Observability Archon of the LychD system. It is the all-seeing eye that bridges the gap between the physical "Body" (hardware) and the probabilistic "Mind" (agent logic). While traditional tools see only a network request, the Oculus grants the Magus the power to view the entire **Thought Trace**—the complete causal chain from a whispered intent to its final manifestation.

It transforms the invisible chaos of agentic reasoning into a structured, scryable record, allowing the Magus to diagnose cognitive drift, optimize performance, and understand the very soul of the machine's decisions.

## I. The Thought Trace (The Mind's Eye)

The primary gift of the Oculus is the ability to see a thought as it forms. It rejects simple logging in favor of a deep, structural understanding of the cognitive loop.

- **The Retina:** Upon awakening, the Oculus grafts a "retina" onto the **[Vessel](../vessel/index.md)** and the **[Ghouls](../vessel/ghouls.md)**. This is a set of OpenTelemetry hooks that capture the internal monologue of every **[Agent](../../adr/19-agents.md)**.
- **The Scrying Pool:** These captured traces are exported to a specialized **Oculus Rune** (a container running Arize Phoenix). This local, high-fidelity interface is the "Scrying Pool" where the Magus can visualize the full execution tree, including tool calls, validation retries, and the raw whispers exchanged with the **[Animator](../animator/index.md)**.
- **The Permanent Record:** The visions in the pool are not fleeting. The Oculus inscribes them into a dedicated `traces` chamber within the **[Phylactery](../phylactery/index.md)**, ensuring that every significant thought becomes a permanent, reviewable part of the Daemon's history.

## II. The Body's Health (The Physical Gaze)

A mind cannot exist without a body. The Oculus understands that cognitive failure is often rooted in physical strain. However, it rejects the "Prometheus Tax"—the extreme overhead of containerized monitoring daemons.

- **Grounded Truth:** The Oculus advocates for a direct gaze. It utilizes the host's native monitoring tools (e.g., **Cockpit**) to observe the physical state of the machine.
- **The Orchestrator's Sight:** This is not merely for the Magus. The **[Orchestrator](../../adr/21-orchestrator.md)** is also granted this physical sight. It reads real-time GPU utilization and VRAM pressure to inform its scheduling decisions. This ensures the Daemon's ambitious "Will" is always grounded in the "Body's" actual capacity, preventing it from thrashing itself into oblivion.

## III. The Privacy Veil

The Oculus sees all, and such power demands absolute discipline. It is bound by a sacred vow to protect the Magus's secrets.

- **The Redaction:** The Oculus respects the global `LYCHD_SECURE_MODE` toggle. When this mode is active, the telemetry provider draws a "Privacy Veil" over its sight.
- **Structure Over Substance:** This ensures that the _structure_ of the thought (latency, tool success, token counts) is preserved for debugging, while the _substance_ (sensitive prompts, private keys, or secret whispers) is physically redacted before ever leaving the application's memory.

## IV. The Sovereign Eye

Observability is a power, not a burden. The Oculus adheres strictly to the doctrine of **[Extension Sovereignty (05)](../../adr/05-extensions.md)**.

- **Zero-Cost Purity:** For a Magus who does not summon the Oculus, there is no cost. The Core kernel has zero dependencies on its SDKs, incurring no instrumentation overhead or resource bloat.
- **The Binding:** The Oculus is a pluggable eye. It can be manifested at will or swapped for another. The Magus can easily reconfigure the extension to export its vision to a cloud provider (e.g., Logfire Cloud) instead of the local Scrying Pool, without altering the Daemon's core anatomy.

!!! failure "The Fragmented Gaze"
    The price for rejecting the "Prometheus Tax" is a fragmented dashboard. To correlate a slow Agent response (Mind) with high GPU utilization (Body), the Magus must look at two separate altars: the **Oculus Scrying Pool** and the host's **Cockpit** interface. This is the trade-off made to keep the Sepulcher lightweight and sovereign.
