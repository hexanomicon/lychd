---
title: Legion
icon: material/hexagon-multiple-outline
---

# :material-hexagon-multiple-outline: Legion

> _"One Phylactery to bind them all."_

**The Legion** is the Swarm Extension of the LychD system. It is the implementation of **[ADR 42 (Legion)](../../adr/42-legion.md)** — the Lich's personal army of Thralls, soulless Vessels bound to a single Phylactery, extending the imperator's reach across every machine the Magus owns.

Like the legions of antiquity, this is not a congress of equals. It is a hierarchy of command — many bodies, one brain, one undying will.

## I. The Thrall (The Soulless Lich)

The Legion's core unit is the **Thrall** — a LychD Vessel booted without a Phylactery (`LYCHD_MODE=thrall`).

- **No Soul:** The Thrall has no local Postgres. Its `DATABASE_URL` and `PHOENIX_ENDPOINT` point to the Master node. There is one Phylactery, and it binds them all.
- **Sovereign Body:** The Thrall runs its own **[Orchestrator](../../adr/23-orchestrator.md)** and generates its own **[Quadlets](../../adr/08-containers.md)**. It manages its own VRAM, its own Covens, its own thermal state. The Master cannot — and should not — manage remote Systemd units.
- **Smart Proxy:** The Thrall's sole execution pattern is the Smart Proxy. The Master's Dispatcher routes a capability request to the Thrall's Emissary via direct Vessel HTTP. The Thrall swaps the required model into VRAM, processes the prompt, and returns the result. No graph execution, no memory curation, no agent logic runs on the Thrall.
- **No Tomb:** A Thrall does not run a **Tomb** container. It is not an execution substrate — it is a self-managing inference endpoint.

## II. The Emissary Pattern (The Remote Instrument)

The Thrall obeys because it cryptographically verifies the intent originates from its own Magus — not because it is forced.

- **The Manifestation:** When a Thrall is registered in the **[Codex](../codex.md)**, the Legion manifests it within the local **[Dispatcher](../../adr/22-dispatcher.md)** as a standard **Tool**.
- **The Illusion:** To the local Agent, calling `ask_thrall(task)` is identical to calling a local function.
- **The Reality:**
    1. The request is serialized and signed with the **[Ward Sigil](./ward.md)**.
    2. It is transmitted via direct HTTP to the Thrall's Vessel API.
    3. The local Agent enters **[Stasis](../../adr/22-dispatcher.md)**, freeing local resources.
    4. Upon the Thrall's callback, the local Agent rehydrates to process the result.

## III. Command and Trust

- **Remote Mastery:** The shared Master Sigil grants `INTENT_UPDATE_SYSTEM` authority. The Master can force Coven transitions, trigger model swaps, and reconfigure state on any Thrall.
- **No Toll:** Resource sharing between Legion nodes does not require crypto-settlement. These are your machines.
- **Unified Telemetry:** All Thrall traces flow to the Master's Phoenix instance, providing a single observability dashboard for the entire Legion.
- **Active-Passive Resilience:** If the Master dies, Thralls become inert — they manage their own hardware but cannot accept cognitive work. The Master is restored from BTRFS snapshots. The Lich arises anew.
