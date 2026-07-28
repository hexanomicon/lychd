---
title: Extensions
icon: material/hubspot
---

# :material-hubspot: The Federation of Extensions

> _“An organ may extend the body. It does not inherit the body's authority.”_

The Federation is a jurisdiction map, not a list of working features.
[State of the Work](../../state-of-the-work.md) is the sole current-delivery record; the Function
column below names intended responsibility unless a current source-map note says otherwise.

LychD proves extension law on its own body. The Core remains a narrow kernel for routing and
state; the Fifteen name the principal directions in which that body may grow. They are
**Extension Domains**, not promises of interchangeable plugins.

This architecture is governed by the
**[Extension Protocol (ADR 05)](../../adr/05-extensions.md)**. LychD's first in-process extension
boundary is assimilation, not a premature compatibility promise.

Read that boundary narrowly: pre-v1 in-process organs are composed with the body they join; durable compatibility is reserved for surfaces that LychD explicitly versions and tests.

Two maps meet here without becoming synonyms:

| Term | Meaning |
| :--- | :--- |
| **Extension Domain** | One of the Fifteen user-facing jurisdictions and directions of growth. |
| **Extension package** | Concrete built-in or Crypt code selected through `register(context)`. |
| **Manifestation** | The form a Domain takes in one body: Core office, selectable built-in, governed Composition, managed provider, external attachment, or dormant design. |
| **Provider** | A concrete engine or service behind a typed contract; it never inherits domain authority merely by being selected. |
| **Contribution** | A typed addition admitted through a shaped store owned by the receiving domain. |

A [Reference Composition](../../compositions/index.md) is a complete application assembled from
Patterns, existing offices, providers, and optional contributions. It may manifest part of an
Extension Domain without becoming a sixteenth member of the Fifteen. Conversely, a singular Core
office such as the Weaver can remain an Extension Domain even though replacing that authority
would fork system truth.

Each Domain has a fantasy, a discipline, and a jurisdiction:

- **The Watchers** see and remember.
- **The Threshold Rites** secure the border.
- **The Cognitive Organs** think, judge, simulate, and evolve.
- **The Sovereign Hands** reach beyond the local machine into the Forest, the Swarm, and the Infinite Naught.

Read this section as operated doctrine: what each Extension means to the Magus, how it may
manifest, where its authority ends, and what the present body can honestly do. Read ADR 05 for
package assimilation and each linked ADR for technical selection and law.

## The Federation of Fifteen

Fifteen official Extension Domains describe the planned growth of the Daemon. A Domain name is
stable user-facing language; its manifestation may change with profile and maturity. Near-term
built-in packages live under `src/lychd/extensions/builtin/` and evolve atomically with the Core.
Private Crypt packages may live under `~/.local/share/lychd/extensions/` as explicitly selected,
coupled source trees. Future Forge-composed repository pinning will own reproducibility; the
location alone creates neither a lock receipt nor a stable third-party API contract.

Source-map note: doctrine names are not package slugs. A placeholder source directory is not
delivery, and absence of a package does not erase a Domain's accepted jurisdiction.

| Name | Domain | Typical manifestation | Jurisdiction | ADR |
| :--- | :--- | :--- | :--- | :--- |
| **[The Oculus](./oculus.md)** | **Observability** | Native evidence office plus optional external Eyes | Correlates bounded observations without becoming canonical event authority. | **[29](../../adr/29-observability.md)** |
| **[The Tether](./tether.md)** | **Private reachability** | Managed WireGuard, external attachment, or private coupled provider | Narrows which enrolled devices can reach which services; never grants application authority. | **[39](../../adr/39-vpn.md)** |
| **[The Veil](./veil.md)** | **Hostile ingress** | Managed Caddy, external edge attachment, or private coupled provider | Terminates transport security and admits typed routes; never authenticates the application caller. | **[40](../../adr/40-proxy.md)** |
| **[The Ward](./ward.md)** | **IAM and authorization** | Singular Core-coupled backend authority with credential/policy adapters | Resolves principals and current object/effect authority. | **[38](../../adr/38-iam.md)** |
| **[The Weaver](./weaver.md)** | **Workflow** | Singular Core office receiving Pattern and Composition contributions | Owns Pattern validation, registration, admission, continuity, and logical time; each Composition owns its application purpose. | **[28](../../adr/28-workflow.md)** |
| **[The Scout](./scout.md)** | **Web acquisition** | Separately authorized effect providers assembled by Patterns | Acquires external material without converting contact into truth or further permission. | **[30](../../adr/30-webcrawler.md)** |
| **[The Smith](./smith.md)** | **Assimilation** | Smith Agent inside the governed Assimilation Composition | Produces attributable candidate organs; never promotes or reanimates itself. | **[35](../../adr/35-assimilation.md)** |
| **[The Soulforge](./soulforge.md)** | **Training** | Governed formation Composition with local or external trainer providers | Binds corpus, objective, recipe, run, and candidate-weight lineage. | **[33](../../adr/33-training.md)** |
| **[The Riddle](./riddle.md)** | **Evaluation** | Trial and calibration Composition with domain-contributed cases | Forms calibrated capability claims; never grants privilege or promotion. | **[34](../../adr/34-evaluation.md)** |
| **[The Toll](./toll.md)** | **Economics** | Governed middleware plus optional settlement adapters | Binds quote, authorization, settlement, delivery, and reconciliation. | **[41](../../adr/41-x402.md)** |
| **[The Prism](./prism.md)** | **Vision** | Visual lifecycle with independent Animator providers | Grounds visual observations and transformations to exact source regions and times. | **[36](../../adr/36-vision.md)** |
| **[The Echo](./echo.md)** | **Audio** | Speech-session lifecycle with independent Animator providers | Preserves temporal and causal speech semantics across capture, transcription, and synthesis. | **[37](../../adr/37-audio.md)** |
| **[The Shadow](./shadow.md)** | **Simulation** | Possibility-lineage office invoked by Weaver; Tomb executes unsafe payloads | Holds incompatible candidate worlds without letting one appoint itself reality. | **[31](../../adr/31-simulation.md)** |
| **[The Mirror](./mirror.md)** | **Identity** | Core-coupled identity binding with Persona/Posture contributions | Attributes acts to a versioned operative identity without minting caller authority. | **[32](../../adr/32-identity.md)** |
| **[The Legion](./legion.md)** | **Distributed embodiment** | Owned-node protocol/profile with node-local providers | Fences delegated work across bodies while each body retains authority over its iron. | **[42](../../adr/42-legion.md)** |


---

## Anatomy of the Flesh

Every concrete extension package, from a small registration shim to a coupled multi-module organ,
adheres to the Extension Protocol below. An Extension Domain may instead be Core-resident,
Composition-shaped, externally attached, or dormant; those forms do not acquire
`register(context)` merely because they belong to the Fifteen.

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
| future `context.patterns` | :material-state-machine: **Pattern Revision Contributions — designed, absent** | **[Weaver (28)](../../adr/28-workflow.md)** |
| future `context.compositions` | :material-source-branch: **Composition Metadata — designed, absent** | **[Composition Portfolio](../../compositions/index.md)** |

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

The Pattern and Composition rows are target stores, not attributes on the current
`ExtensionContext`. They become real only with shaped contracts, frozen assembly, collision and
compatibility checks, lifecycle tests, and a matching State boundary.

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
2. **Speculation:** A Weaver Pattern holds the candidate in the
   **[Shadow Realm (31)](../../adr/31-simulation.md)** and routes only unsafe payloads to the Tomb.
3. **Validation:** The **Ghouls** execute the "Rite of Speculation" (Linting, Typing, Testing).
4. **Promotion:** Upon **[Sovereign Consent (25)](../../adr/25-hitl.md)**, or only within an
   explicitly defined low-risk preauthorization class, the owning services may move code to the
   **Crypt** and update the lockfile. High-stakes mutation remains live Magus authority.
5. **Rebirth:** An authorized lifecycle office may request
   **[Packaging (17)](../../adr/17-packaging.md)** and a validated restart. Failure enters an
   explicit recovery state; automatic code-and-database rollback is not assumed.
