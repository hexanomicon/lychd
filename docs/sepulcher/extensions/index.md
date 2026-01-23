---
title: Extensions
icon: material/hubspot
---

# :material-hubspot: Extensions and The Nine Archons

> _"The Lych is the Father; the Extensions are the Children. The first nine are the Archons—the fundamental organs through which the Daemon perceives, protects, and perfects itself."_

The LychD is a sovereign entity built upon a **[Federation (ADR 05)](../../adr/05-extensions.md)** of independent repositories. While any Magus can forge a new organ, the system recognizes **Nine Archons**—the primary extensions that define the system's core capabilities.

## 🏛️ The Ennead of Power

| Archon | Domain | Icon | The Artifact |
| :--- | :--- | :--- | :--- |
| **[The Smith](./smith.md)** | **Assimilation** | :material-hammer-anvil: | `lychd-smith` |
| **[The Oculus](./oculus.md)** | **Observability** | :material-eye-settings-outline: | `lychd-oculus` |
| **[The Soulforge](./soulforge.md)** | **Training** | :material-creation: | `lychd-soulforge` |
| **[The Veil](./veil.md)** | **Proxy** | :material-incognito: | `lychd-veil` |
| **[The Thread](./tether.md)** | **VPN** | :material-vector-polyline: | `lychd-thread` |
| **[The Echo](./echo.md)** | **Audio** | :material-waveform: | `lychd-echo` |
| **[The Prism](./prism.md)** | **Vision** | :material-pyramid: | `lychd-prism` |
| **[The Mirror](./mirror.md)** | **Identity** | :material-mirror-variant: | `lychd-mirror` |
| **[The Paradox](./paradox.md)** | **Simulation** | :material-infinity: | `lychd-paradox` |

## 🧩 The Nature of the Binding

Every Archon, whether it provides the "Voice" or the "Will," is subject to the **Anatomy of the Flesh**. They are birthed in the **[Lab (ADR 16)](../../adr/16-creation.md)**, tested in the **[Shadow Realm (ADR 25)](../../adr/25-hitl.md)**, and sealed by the **[Forge (ADR 17)](../../adr/17-packaging.md)**.

They are not "plugins"; they are **Substrate Injections**. When an Archon is summoned, it modifies the very nature of the Daemon's physical and cognitive reality.

---

# :material-dna: Structure & Anatomy

> _"The Lich cares not if the soul is a single spark or a raging sun. It cares only that it fits the Binding."_

The Daemon is agnostic to complexity. Whether an Extension is a single-file script or a sprawling enterprise architecture, the **Binding Ritual** remains the same. The `ExtensionContext` is the universal adapter that allows the Daemon to assimilate any form of code into its physical and cognitive body.

## I. :material-sword-bolt: The Shiv (Simple Binding)

For simple tools—a single agent, a few commands, or a basic model utility—the Extension is structured as a flat, high-velocity module.

```text
my_agent/
├── .git/              # Required: Mandatory Version Control.
├── __init__.py        # The Cortex: register(context) is here.
├── logic.py           # The reasoning logic.
└── templates/         # The scrying fragments (Jinja2).
```

In `__init__.py`, the logic is imported and bound to the `ExtensionContext`. This is the **Shiv**: a sharp, focused instrument for a single purpose.

## II. :material-graphql: The Fractal (Complex Binding)

For high-level Archons—systems that manage other systems or provide complex sensory inputs—the anatomy expands into a **Fractal** structure following **Domain-Driven Design**.

```text
enterprise_agent/
├── .git/                   # Required: The root of the Sovereign Repository.
├── __init__.py             # The Gateway (Registration hook).
├── core/                   # Shared types and internal utilities.
├── infrastructure/         # DB Models (Phylactery) & Jobs (Ghouls).
├── interface/              # Web Routers (Altar) & CLI commands (The Hand).
└── agents/                 # Cognitive Topologies (Graphs).
```

## 🛠️ The Extension Context (The Senses)

The `ExtensionContext` is the genetic code of the daemon. It provides the methods required to graft new logic onto the Core.

| Method | The Grant | ADR Reference |
| :--- | :--- | :--- |
| `add_models(list[Base])` | :material-database-lock: **Memory.** | **[06. Persistence](../../adr/06-persistence.md)** |
| `add_agent(Agent)` | :material-head-cog: **Cognition.** | **[19. Agents](../../adr/19-agents.md)** |
| `add_graph(Graph)` | :material-graph: **Topology.** | **[22. Graph](../../adr/22-graph.md)** |
| `add_worker_rites(list)` | :material-skull-outline: **Action.** | **[14. Workers](../../adr/14-workers.md)** |
| `add_router(Router)` | :material-gate: **Voice.** | **[15. Frontend](../../adr/15-frontend.md)** |
| `add_command(Group)` | :material-script-text-play: **Will.** | **[18. CLI](../../adr/18-cli.md)** |

## 🌐 The Federation (Git Management)

Extensions are managed as a **Federation of Git Repositories**, ensuring absolute modularity.

1. **Isolation:** Every directory in the `extensions/` sphere is a standalone repository. Updates are performed via `git pull` without risk to the Core kernel.
2. **The Lockfile:** The Daemon maintains `lychd.lock` in the Crypt root. It tracks the specific commit hash of every active organ, ensuring the body is deterministic and revertible.

## 🧪 The Ritual of Assimilation

The workflow of **Autopoiesis** (self-creation) follows a strict path from the volatile to the immutable:

1. **Genesis (Drafting):** The Agent (guided by **[The Smith](./smith.md)**) or Magus creates code in the **Lab (ADR 16)**.
2. **Speculation:** The code is executed and tested in the **Shadow Realm (ADR 25)** against temporary schemas.
3. **Validation:** The **Ghouls (ADR 14)** execute the "Rite of Albedo" (Pytest/Ruff).
4. **Promotion:** The code is moved to the **Crypt (ADR 13)** and hashed in the lockfile.
5. **The Rebirth:** The system triggers **[Packaging (ADR 17)](../../adr/17-packaging.md)** and restarts the container into its new body.
