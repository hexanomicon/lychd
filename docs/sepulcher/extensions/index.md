---
title: Extensions
icon: material/hubspot
---

# :material-hubspot: The Federation of Extensions

> _"The Core provides the skeleton; the Extensions provide the organs. But organs alone do not make a body. They must sing in one key, move toward one will, and remember the same night in which they were called to life."_

The Federation is a jurisdiction map, not a list of working features.
[State of the Work](../../state-of-the-work.md) is the sole current-delivery record; the Function
column below names intended responsibility unless a current source-map note says otherwise.

LychD employs a strict philosophy of **Dogfooding**. The core kernel remains a minimal vessel for routing and state. Every advanced capability—from the API Proxy to the Swarm Protocol—functions as an **Extension**.

This architecture proves the **[Extension Protocol (ADR 05)](../../adr/05-extensions.md)**: the system constructs itself using the same tools available to the Magus. LychD's first extension boundary is not compatibility; it is assimilation.

Read that boundary narrowly: pre-v1 in-process organs are composed with the body they join; durable compatibility is reserved for surfaces that LychD explicitly versions and tests.

Each extension is more than a plugin-era module. It is an organ with a fantasy, a discipline, and a jurisdiction:

- **The Watchers** see and remember.
- **The Threshold Rites** secure the border.
- **The Cognitive Organs** think, judge, simulate, and evolve.
- **The Sovereign Hands** reach beyond the local machine into the Forest, the Swarm, and the Infinite Naught.

Read this section not as a package index but as an anatomy of powers. Each page below should feel like a distinct chamber of the same body.

## 🏛️ The Federation of Fifteen

Fifteen official extension domains form the planned body of the Daemon. Near-term built-ins live under `src/lychd/extensions/builtin/` and evolve atomically with the Core. Private Crypt organs may live under `~/.local/share/lychd/extensions/` as Forge-composed repositories, but that location does not by itself create a stable third-party API contract.

Source-map note: doctrine names are domain names, not guaranteed package slugs. Current built-in source uses functional package names such as `animator`, `observability`, `vpn`, `proxy`, `iam`, `workflow`, `webcrawler`, `assimilation`, `training`, `video`, `audio`, `simulation`, `identity`, and `swarm`.

| Doctrine Domain | Current Source Mapping |
| :--- | :--- |
| Prism / Vision | Official domain; current source exposes the media substrate through `video` while the full `vision.coven` surface matures. |
| Riddle / Evaluation | Official domain; no dedicated built-in package has landed yet. Evaluation work currently routes through simulation/Tomb execution doctrine. |
| Toll / Economics | Official domain; no dedicated built-in package has landed yet. |

| Name | Domain | Sigil | Function | ADR |
| :--- | :--- | :--- | :--- | :--- |
| **[The Oculus](./oculus.md)** | **Observability** | :material-eye-outline: | Native evidence and Scrying jurisdiction; Phoenix may remain an optional external Eye. | **[29](../../adr/29-observability.md)** |
| **[The Tether](./tether.md)** | **VPN** | :material-shield-link-variant-outline: | Establishes a WireGuard tunnel for secure, remote access. | **[39](../../adr/39-vpn.md)** |
| **[The Veil](./veil.md)** | **Proxy** | :material-shield-key-outline: | Manages automated **TLS** and shields the Vessel via Caddy. | **[40](../../adr/40-proxy.md)** |
| **[The Ward](./ward.md)** | **IAM & Auth** | :material-shield-account-outline: | Governs Sigils and Scopes to secure the **Inner Circle**. | **[38](../../adr/38-iam.md)** |
| **[The Weaver](./weaver.md)** | **Workflow** | :material-tune-vertical: | Orchestrates multi-step **Patterns** and weaves memory into context. | **[28](../../adr/28-workflow.md)** |
| **[The Scout](./scout.md)** | **Web acquisition** | :material-navigation-variant-outline: | Coordinates separately authorized web-acquisition effects; no Scout runtime is available yet. | **[30](../../adr/30-webcrawler.md)** |
| **[The Smith](./smith.md)** | **Assimilation** | :material-hammer-wrench: | Drafts code and executes the autonomous **Evolution** of the system. | **[35](../../adr/35-assimilation.md)** |
| **[The Soulforge](./soulforge.md)** | **Training** | :material-anvil: | Transmutes Karma into model weights via **LoRA** fine-tuning. | **[33](../../adr/33-training.md)** |
| **[The Riddle](./riddle.md)** | **Evaluation** | :material-help-rhombus-outline: | Evaluates model performance in the agentic harness. | **[34](../../adr/34-evaluation.md)** |
| **[The Toll](./toll.md)** | **Economics** | :material-cash-register: | Enforces **x402** payments and trades VRAM for Tithes. | **[41](../../adr/41-x402.md)** |
| **[The Prism](./prism.md)** | **Vision** | :material-pyramid: | Manages the **Vision Coven** to perceive and analyze pixel data. | **[36](../../adr/36-vision.md)** |
| **[The Echo](./echo.md)** | **Audio** | :material-waveform: | Operates the **Resonance Pipeline** for real-time speech. | **[37](../../adr/37-audio.md)** |
| **[The Shadow](./shadow.md)** | **Simulation** | :material-brightness-6: | Deliberative reasoning engine that projects potential futures. | **[31](../../adr/31-simulation.md)** |
| **[The Mirror](./mirror.md)** | **Identity** | :material-mirror: | Maintains persistent **Personas** and shifts Bayesian Priors. | **[32](../../adr/32-identity.md)** |
| **[The Legion](./legion.md)** | **Swarm** | :material-account-multiple-plus: | The Magus's army of Thralls. | **[42](../../adr/42-legion.md)** |


---

## 🧬 Anatomy of the Flesh

Every extension, from simple script to complex multi-module architecture, adheres to the laws of the Federation.

### I. The Extension Protocol

An in-process organ participates in the composed runtime image. Pre-v1 organs are intentionally coupled: they may import LychD internals, expose `RuneConfig` subclasses, and rely on Forge/Smith verification when the Core changes. One branch exposes schema classes the Codex can load through explicit stores. Another governs optional in-process boot registration through `register(context)` when an organ binds runtime-facing logic.

Inside the body, couple and repair. Across bodies, speak protocols. Public SDK/ABI later.

### Ia. Compatibility Tiers

Not every organ promises the same stability:

- **Built-in Direct:** Core-maintained organs in `src/lychd/extensions/builtin/`. They may import internals because they evolve with the Core.
- **Private Coupled:** Magus-owned local organs that intentionally import internals for speed and power. They are valid local work, but refactors may break them.
- **Future Independent Product:** Shareable organs that target a future versioned public API and conformance suite. This is harvested at v1+ from patterns that survived real use.

Use the private coupled tier when local velocity matters more than long-term compatibility. Use an external-service Animator when the organ needs a true isolation boundary today. Treat independent in-process compatibility as future product work, not current doctrine.

### II. The Genetic API (ExtensionContext)

The `ExtensionContext` is the host-provided root of explicit registration stores
used during boot-time extension assembly. It is not the whole Extension
Protocol. Each store names a boundary that Core is willing to extend. Store
implementations live with the layer that owns their meaning: rune stores in
Codex/runes, Animator stores in the animation domain, and future Vessel stores
in the Vessel boundary.

Extension activation is selected before rune loading. The core `lychd.toml`
uses lists, so every extension is inactive unless named:

```toml
[extensions]
builtins = []
crypt = ["my-private-organ"]
```

This selector decides which organs are imported and allowed to register schemas,
runtime hydrators, and registration stores. Extension-owned runes then configure the
selected organ's instances; they do not decide whether the organ exists.

Fresh Codex inscription keeps `builtins` empty and writes commented catalog
examples. Adding an id activates that organ on the next assembly pass; removing
one deactivates it.

| Store | Grant | System Target |
| :--- | :--- | :--- |
| `context.runes.add_schema(RuneConfig)` | :material-file-cog-outline: **Codex Schema** | **[Codex (12)](../../adr/12-configuration.md)** |
| `context.soulstones.add(SoulstoneDefinition)` | :material-cog-transfer: **Soulstone Runtime Definition** | **[Animator](../animator/index.md)** |
| `context.portals` | :material-cloud-outline: **Reserved Remote/API Model Store** | **[Animator](../animator/portal.md)** |
| `context.vessel` | :material-router: **Reserved Web/API/Event Store** | **[Vessel (11)](../../adr/11-backend.md)** |

An enabled Python organ exposes a small shim:

```python
def register(context: ExtensionContext) -> None:
    context.runes.add_schema(MyExtensionConfig)
```

Soulstone providers register through the Animator-specific store:

```python
from lychd.domain.animation.services.adapters.contracts import SoulstoneDefinition

def register(context: ExtensionContext) -> None:
    context.soulstones.add(
        SoulstoneDefinition(
            rune_schema=MySoulstoneConfig,
            runtime_adapter=MySoulstoneRuntimeAdapter(),
        )
    )
```

`context.vessel` intentionally has no active flat methods yet. Routes,
middleware, auth policies, and event hooks will be added as shaped bundles or
sub-stores once the Vessel boundary is stable enough to avoid becoming a grab
bag.

The manager owns import order and calls this function only for selected
extensions. Codex never scans arbitrary packages by itself. For built-ins, the
host resolves configured ids to `lychd.extensions.builtin.<id>.register`.
Crypt ids resolve to `<crypt-root>/<id>/register.py`. The selected shim owns
its own `register(context)` body.

The current manager returns the populated `ExtensionContext`. Codex reads
schemas from `context.runes.rune_schemas`; Animator reads local runtime adapters
from `context.soulstones.runtime_adapters`. Animator runtimes such as
`animator/vllm` therefore become visible to both `ConfigWriter`/`ConfigLoader`
and the `AnimatorRegistry`/`Dispatcher` model binding path through the same
activation list.

The optional legacy Phoenix contribution registers LychD-owned configuration and generated unit
intent. [Arize owns Phoenix](https://github.com/arize-ai/phoenix); its service is not native Oculus,
and current evidence does not prove application trace export to it.
[State records that interoperability boundary](../../state-of-the-work.md#phoenix-eye).

Cross-language organs follow the same rule. A Rust or C-backed engine may keep
its native configuration internally, but the operator-facing surface should be a
Codex rune when it is managed by LychD. A Python shim or adapter translates the
validated rune into the foreign engine's native shape and may expose a
LychD-facing `Runic` wrapper when provenance is needed. The foreign object
itself is not required to implement `.rune`.

### III. Federated Persistence

The designed Federation will pin Forge-composed extension repositories through `lychd.lock`, so
one body can later be reproduced and restored. That repository and lock lifecycle is not delivered
today. Current LychD assembles explicitly selected built-in and Crypt registration shims;
[State](../../state-of-the-work.md#extension-activation-contributions) owns the partial boundary.

### IV. The Ritual of Assimilation

Autopoiesis follows a strict path from the volatile to the immutable:

This is the designed assimilation sequence, not a runnable end-to-end workflow today; State owns
the delivery of each participating office.

1. **Genesis:** The Magus or **The Smith** drafts logic in the **[Lab (13)](../../adr/13-layout.md)**.
2. **Speculation:** The system executes the code within the **[Shadow Realm (31)](../../adr/31-simulation.md)**.
3. **Validation:** The **Ghouls** execute the "Rite of Speculation" (Linting, Typing, Testing).
4. **Promotion:** Upon **[Sovereign Consent (25)](../../adr/25-hitl.md)** or an explicit Codex-governed preauthorization class, the system moves code to the **Crypt** and updates the lockfile. High-stakes mutation remains live Magus authority.
5. **Rebirth:** The system triggers **[Packaging (17)](../../adr/17-packaging.md)** and restarts into its new physical body.
