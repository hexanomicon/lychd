---
title: Extensions
icon: material/hubspot
---

# :material-hubspot: The Federation of Extensions

> _"The Core provides the skeleton; the Extensions provide the organs. But organs alone do not make a body. They must sing in one key, move toward one will, and remember the same night in which they were called to life."_

LychD employs a strict philosophy of **Dogfooding**. The core kernel remains a minimal vessel for routing and state. Every advanced capability—from the API Proxy to the Swarm Protocol—functions as an **Extension**.

This architecture proves the **[Extension Protocol (ADR 05)](../../adr/05-extensions.md)**: the system constructs itself using the same tools available to the Magus.

Each extension is more than a plugin. It is an organ with a fantasy, a discipline, and a jurisdiction:

- **The Watchers** see and remember.
- **The Threshold Rites** secure the border.
- **The Cognitive Organs** think, judge, simulate, and evolve.
- **The Sovereign Hands** reach beyond the local machine into the Forest, the Swarm, and the Infinite Naught.

Read this section not as a package index but as an anatomy of powers. Each page below should feel like a distinct chamber of the same body.

## 🏛️ The Federation of Fifteen

Fifteen official extensions form the complete body of the Daemon. They reside in the `extensions/` directory, each a standalone repository within the Federation.

| Name | Domain | Sigil | Function | ADR |
| :--- | :--- | :--- | :--- | :--- |
| **[The Oculus](./oculus.md)** | **Observability** | :material-eye-outline: | Records the **Thought Trace** and monitors physical hardware health. | **[29](../../adr/29-observability.md)** |
| **[The Tether](./tether.md)** | **VPN** | :material-shield-link-variant-outline: | Establishes a Wireguard tunnel for secure, remote access. | **[39](../../adr/39-vpn.md)** |
| **[The Veil](./veil.md)** | **Proxy** | :material-shield-key-outline: | Manages automated **TLS** and shields the Vessel via Caddy. | **[40](../../adr/40-proxy.md)** |
| **[The Ward](./ward.md)** | **IAM & Auth** | :material-shield-account-outline: | Governs Sigils and Scopes to secure the **Inner Circle**. | **[38](../../adr/38-iam.md)** |
| **[The Weaver](./weaver.md)** | **Workflow** | :material-tune-vertical: | Orchestrates multi-step **Litanies** and weaves memory into context. | **[28](../../adr/28-workflow.md)** |
| **[The Scout](./scout.md)** | **Ingestion** | :material-navigation-variant-outline: | Wields a **Dual-Mode** browser to harvest internet knowledge. | **[30](../../adr/30-webcrawler.md)** |
| **[The Smith](./smith.md)** | **Assimilation** | :material-hammer-wrench: | Drafts code and executes the autonomous **Evolution** of the system. | **[35](../../adr/35-assimilation.md)** |
| **[The Soulforge](./soulforge.md)** | **Training** | :material-anvil: | Transmutes Karma into model weights via **LoRA** fine-tuning. | **[33](../../adr/33-training.md)** |
| **[The Riddle](./riddle.md)** | **Evaluation** | :material-help-rhombus-outline: | Evaluates the performance of the models in the agentic harness | **[34](../../adr/34-evaluation.md)** |
| **[The Toll](./toll.md)** | **Economics** | :material-cash-register: | Enforces **x402** payments and trades VRAM for Tithes. | **[41](../../adr/41-x402.md)** |
| **[The Prism](./prism.md)** | **Vision** | :material-pyramid: | Manages the **Vision Coven** to perceive and analyze pixel data. | **[36](../../adr/36-vision.md)** |
| **[The Echo](./echo.md)** | **Audio** | :material-waveform: | Operates the **Resonance Pipeline** for real-time speech. | **[37](../../adr/37-audio.md)** |
| **[The Shadow](./shadow.md)** | **Simulation** | :material-brightness-6: | Deliberative reasoning engine that projects potential futures. | **[31](../../adr/31-simulation.md)** |
| **[The Mirror](./mirror.md)** | **Identity** | :material-mirror: | Maintains persistent **Personas** and shifts Bayesian Priors. | **[32](../../adr/32-identity.md)** |
| **[The Legion](./legion.md)** | **Swarm** | :material-account-multiple-plus: | The imperator's army of Thralls. | **[42](../../adr/42-legion.md)** |


---

## 🧬 Anatomy of the Flesh

Every extension, from simple script to complex multi-module architecture, adheres to the laws of the Federation.

### I. The Extension Protocol

An independent organ must provide a valid `pyproject.toml` and the structural shapes required by the **Extension Protocol**. One branch exposes schema classes the Codex can discover. Another governs optional in-process boot grafting when an organ is actually loaded into the runtime. This layered handshake prevents organ rejection during the system boot sequence.

### II. The Genetic API (ExtensionContext)

The `ExtensionContext` is the host-provided registration surface used during boot-time grafting. In the current core it is intentionally narrow: it exists to bind in-process logic such as unbound routers or controller classes to the Vessel. It is not the whole Extension Protocol. Schema exposure, synthesis declarations, and binary compatibility live in other branches of that law.

| Method | Grant | System Target |
| :--- | :--- | :--- |
| `add_router(Router)` | :material-router: **Interface** | **[Vessel (11)](../../adr/11-backend.md)** |
| `add_controller(Controller)` | :material-view-list: **Interface** | **[Vessel (11)](../../adr/11-backend.md)** |

### III. Federated Persistence

The system manages extensions as a **Federation of Git Repositories**. The `lychd.lock` file in the Crypt root tracks the specific commit hash of every active organ, ensuring the system remains deterministic and revertible. The flesh may grow, but the binding must remain exact.

### IV. The Ritual of Assimilation

Autopoiesis follows a strict path from the volatile to the immutable:

1. **Genesis:** The Magus or **The Smith** drafts logic in the **[Lab (13)](../../adr/13-layout.md)**.
2. **Speculation:** The system executes the code within the **[Shadow Realm (31)](../../adr/31-simulation.md)**.
3. **Validation:** The **Ghouls** execute the "Rite of Albedo" (Linting, Typing, Testing).
4. **Promotion:** Upon **[Sovereign Consent (25)](../../adr/25-hitl.md)**, the system moves code to the **Crypt** and updates the lockfile.
5. **Rebirth:** The system triggers **[Packaging (17)](../../adr/17-packaging.md)** and restarts into its new physical body.
