---
title: The Praxis
icon: material/hammer-wrench
---

# :material-hammer-wrench: The Praxis

The Praxis is the manual for *doing things* with a running daemon. The
[Summoning](../summoning/index.md) got the Lich breathing; the Praxis is where you learn to
work it — connect providers, drive swaps, tune configuration, and diagnose faults.

Every guide here is task-first: a goal, the prerequisites, numbered steps, and a
verification. Concepts are explained once in the [Sepulcher](../sepulcher/index.md) and the
[Covenants](../adr/index.md); the Praxis links to them rather than re-explaining.

## I want to…

| Goal | Go to |
| :--- | :--- |
| Connect a remote provider (OpenAI, Gemini, …) | [Open a Portal](rites/open-a-portal.md) |
| Understand and drive coven swaps (warm/cold, priorities) | [Manage Covens](rites/manage-covens.md) |
| Understand the Codex layout and file precedence | [Runes: the Codex layout](runes/index.md) |
| Configure a local model service | [Soulstone Rune reference](runes/soulstones.md) |
| Configure a remote provider | [Portal Rune reference](runes/portals.md) |
| Tune routing, queues, and swap policy | [Orchestration reference](runes/orchestration.md) |
| Diagnose a fault | [Exorcism (troubleshooting)](exorcism.md) |

## The parts of the Praxis

- **Rites** — task guides. Each drives one outcome end to end.
- **Runes** — the configuration reference: the exact schema of every TOML declaration and
  setting under the [Codex](../sepulcher/codex.md).
- **Exorcism** — the troubleshooting guide: symptom → cause → cure.

!!! note "This section grows with the daemon"
    The Praxis is built wave by wave alongside the features it documents. Guides for
    consent, Kits, and workflows arrive as those features land.
