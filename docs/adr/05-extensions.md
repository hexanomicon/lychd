---
title: 5. Extensions
icon: material/toy-brick-outline
---

# :material-toy-brick-outline: 5. Recursive Extension Architecture

!!! abstract "Context and Problem Statement"
    The LychD system functions as a kernel for orchestrating sovereign intelligence. Static software architectures lack the flexibility to incorporate emerging hardware interfaces, novel reasoning topologies, or specialized memory structures without intrusive core modifications. Existing plugin models typically enforce a binary choice between high-latency network communication and restrictive execution environments that prevent deep integration into the system substrate. LychD is born in an agentic era where code can be inspected, rewritten, verified, and promoted by the same system that runs it. The first extension boundary is therefore assimilation, not premature compatibility.

## Requirements

- **Placement Choice:** In-process packages are valid for tightly coupled contributions; external
  service protocols remain the correct boundary for independent engines, isolation, or separate
  lifecycle.
- **Shaped Substrate Access:** Every contribution enters through a store owned by the receiving
  Domain. No package receives ambient schema, worker, route, migration, or startup authority.
- **Infrastructure Declaration:** The wider Extension Protocol must eventually declare binaries,
  images, services, resources, and licenses before Forge synthesis; the boot-time
  `ExtensionContext` is not that manifest.
- **Federated Sovereignty:** The Core, private coupled packages, and external providers may retain
  distinct source ownership while joining one explicitly assembled body.
- **Deterministic Provenance:** A future Forge lock lifecycle must pin external source and physical
  requirements. Current selected shims do not yet make the whole body bit-for-bit reproducible.
- **Interface Simplicity:** Utilization of standard Python patterns and registration stores to facilitate extension creation, avoiding proprietary Domain Specific Languages (DSLs).
- **Capability-Driven Design:** Mandatory support for registering abstract functional identifiers that allow the system to orchestrate extension logic through semantic intent.
- **Extension Protocol:** Establishment of a composed-runtime law for assimilating local organs before public compatibility surfaces are harvested.

## Considered Options

!!! failure "Option 1: Microservice Plugins"
    Deploying every extension as a separate container communicating via HTTP or gRPC.

    - **Cons:** **Architectural Fragmentation.** This introduces significant latency for internal tool calls and complicates the sharing of atomic database transactions. It forces a "Small-Talk" overhead that is unacceptable for real-time sensory loops.

!!! failure "Option 2: Sandboxed Scripting (WASM/Lua)"
    Running extensions in a restricted, safe runtime environment.

    - **Cons:** **Functional Castration.** A sandboxed environment prevents deep integration. A script cannot easily define new relational models or register system-level background ghouls, violating the principle of deep modularity.

!!! success "Option 3: Native Contributions, Protocol-Bound Providers"
    Explicitly selected Python packages may join the Daemon's memory space through shaped stores.
    Engines needing isolation or independent lifecycle remain external services. Forge-composed
    repository and lock management is the target reproducibility lifecycle.

    - **Pros:**
        - **Low Boundary Overhead:** Direct contributions avoid a network hop where in-process
          coupling is actually warranted.
        - **Shaped Integration:** Extensions contribute only through domain-owned stores. Current
          active stores cover Runes, Soulstone definitions, Portals, transmutation, and typed
          `run` operations; Vessel is empty/reserved, while tools, routes, status sections,
          workloads, migrations, Patterns, and Compositions remain target stores until
          individually delivered.
        - **Assimilable Source:** Standard Git tooling preserves source history while Forge/Smith verification repairs organs with the body they join.

## Decision Outcome

**Native Recursive Extensions** are adopted for explicitly selected in-process code contributions.
The Daemon performs deterministic boot-time assembly through shaped registration stores; it is not
a general-purpose runtime package manager. Independent engines and services cross versioned
protocol boundaries instead.

LychD's first extension boundary is not compatibility; it is assimilation. Public compatibility is a product of maturity, not the foundation of infancy.

### Vocabulary Boundary: Domain Is Not Package

LychD uses **extension** at two related but non-identical levels:

- An **Extension Domain** is one of the user-facing Fifteen: a direction in which the minimal Lich
  may grow. A Domain may be embodied as a singular Core office, a selectable built-in, a governed
  Composition, a managed provider, an external attachment, or a still-dormant design. Membership
  among the Fifteen does not prove that a Python package exists, that the Domain is optional in
  every profile, or that its authority is replaceable.
- An **extension package** is concrete built-in or Crypt code selected for import and admitted
  through the Extension Protocol. A package may contribute to one or several Domains; several
  packages or external providers may also manifest different parts of one Domain.

The remaining terms keep those layers distinct:

- A **manifestation** is the form a Domain takes in one assembled body or profile.
- A **provider** is a concrete engine or service behind a typed contract. It supplies mechanism,
  never the Domain's policy or authority merely by being selected.
- A **contribution** is a typed addition admitted through a domain-owned shaped store.
- **Activation** selects an extension package or one of its declared instances. It does not
  activate an abstract Domain name.

The [Federation of Fifteen](../sepulcher/extensions/index.md) is therefore operated doctrine and a
jurisdiction map, not a claim that fifteen uniform plugins ship. This ADR owns how concrete code
enters the body.

The decision line is:

```txt
Inside the body, couple and repair. Across bodies, speak protocols. Public SDK/ABI later.
```

This creates an explicit maturity path:

- **Pre-v1:** In-process organs are coupled, assimilable, and repaired through Forge/Smith verification.
- **v1:** Stable public surfaces may be harvested from patterns that survived real use.
- **Post-v1:** SDK/API/ABI support becomes a compatibility product with versioning, conformance tests, and deprecation policy.


### 1. The Federation Strategy

The system's logic resides in a structured directory hierarchy designed for modularity, distinguishing between the system's shipped capabilities and its elective augmentations:

- **Built-in Extensions:** Residing in `src/lychd/extensions/builtin/`. These are Core-coupled organs
  and reference implementations shipped within the kernel source. Installed does not mean active:
  only ids explicitly selected in Core configuration enter the boot registration pass.
- **Crypt Extensions:** Residing in the **Crypt (13)** (`~/.local/share/lychd/extensions/`).
  Current assembly may import an explicitly selected private `register.py` shim. Reproducible
  repository pinning, dependency resolution, and substrate synthesis through
  **Synthetic Forge (17)** remain future lifecycle work.
- **Future Independent Extensions:** Shareable third-party organs become meaningful at or after v1, when proven patterns can be frozen behind a versioned public API, conformance tests, and manifest-gated packaging.
- **The Manifest:** The target Forge lifecycle maintains a global lock that records exact source
  and physical inputs. No such delivered federated lock currently proves a bit-for-bit
  reproducible body.

### 2. The Registration Surface (The Extension Context)

The architecture relies on an **Inversion of Control** pattern to facilitate assimilation. The Core provides a host registration surface, but that surface is only one branch of the broader Extension Protocol.

- **Activation Selection:** Extensions are inactive unless explicitly selected in the core `lychd.toml` extension lists. The selector lives outside extension-owned runes because Codex cannot load an extension's rune schema until the extension has first been imported. An omitted extension id means inactive.
- **The Entry Point:** Any organ participating in in-process boot registration exposes a `register(context)` function in its selected `register.py` shim.
- **The Context Object:** The Core passes an `ExtensionContext` object which serves as the host registration surface for boot-time stores. Through this object, an organ binds runtime-facing logic into the Daemon's anatomy.
- **Interface Registration:** Vessel routes, middleware, auth, and event hooks are reserved for a shaped `context.vessel` store instead of flat registration methods.
- **Pulse Operations:** An extension may register typed work through
  `context.run_operations`. The contribution appears beneath `lychd run`, inherits the shared
  admission/authority/traceability path, and never becomes a public root command. Its declaration
  is inert metadata rather than an arbitrary host-side Click callback.
- **Schema Exposure:** Selected in-process organs register `RuneConfig` subclasses through the extension context after import. Runtime package/source scanning is not the extension ledger.
- **Application Contributions:** Future shaped `patterns`, `compositions`, and `suites` stores may
  accept immutable Pattern revisions plus application and cross-Composition handoff metadata for
  the living [Composition
  Portfolio](../compositions/index.md). They do not exist in the current `ExtensionContext`;
  application pages are design rather than runnable registration.
- **Substrate Declarations:** Synthesis-time requirements (system libraries, binaries, container needs) belong to the wider Extension Protocol and feed the Forge manifest. They must not be confused with the boot-time context itself.

The activation selector has list semantics, not boolean map semantics:

```toml
[extensions]
builtins = []
crypt = ["my-private-organ"]
```

This keeps the default body inert. `lychd init` provides commented built-in
choices; it does not activate every installed runtime. Enabling an extension means its schemas,
hydrators, and registration stores may participate. It does not by itself start every
rune instance owned by that extension; instance-level activation remains a
domain/runtime decision inside the extension's runes.

An enabled Python organ contributes through its selected `register.py` shim:

```python
def register(context: ExtensionContext) -> None:
    context.runes.add_schema(MyExtensionConfig)
```

The extension manager owns the selected import list and invokes this shim.
Codex receives the resulting rune schema list; it does not scan arbitrary
packages on its own.

### 3. Contributions as Organs

Extensions are more than isolated code, but no Extension is automatically a complete application.
Today `ExtensionContext` exposes active Rune, Soulstone, Portal, transmutation, and `run` operation
stores plus an empty reserved Vessel store. Read-only `status` sections remain a target store. The
broader list below is the Extension Protocol target; each item remains absent until its shaped
store, lifecycle, tests, and State boundary exist:

- **Configuration and Runtime Definitions:** Rune schemas, Animator definitions, adapters, and
  lifecycle hooks through their owning stores.
- **Tools and Interfaces:** Typed toolsets, routes, projections, and external workload contracts
  without bypassing Ward, Vessel, or execution-plane authority.
- **Persistence:** Domain schemas and migrations only through an accepted owner, ordering,
  recovery, export, deletion, and uninstall contract.
- **Workflow Applications:** Future immutable Pattern revisions, Reference Composition metadata,
  and Suite handoff graphs through the Weaver's shaped contribution stores.
- **Infrastructure:** Explicit binaries, images, services, resource needs, and licenses for Forge
  synthesis.

Capabilities remain abstract identifiers of what a provider can perform. A Composition assembles
these contributions into one application; an Extension describes how contributed code and
contracts enter the body; a Suite relates several Compositions without merging them. None of
these terms is a synonym for another.

### 4. Substrate Injections

Extensions are not limited to Python logic. They may declare system-level dependencies (e.g., C-libraries like `ffmpeg` or specialized binaries) as part of the wider Extension Protocol. The assembly process collects these physical requirements into the synthesis manifest and injects them into the physical body of the Daemon during the **Synthetic Forge (17)** process.

### 5. Runtime Schema Discovery

Configuration extensibility uses the schema branch of the Extension Protocol:

- Selected extension modules are imported at runtime during codex/bootstrap.
- Built-in and private coupled organs register `RuneConfig` subclasses through `context.runes`.
- Domain stores may wrap related contributions. For example, `context.soulstones.add(SoulstoneDefinition(...))` stores the Animator-owned definition and registers its rune schema into the shared rune store.
- `__subclasses__()` traversal is only an internal audit/debug convenience after import. It is not the runtime extension ledger and not a public extension API.
- Crypt organs participate through explicit selected `register(context)` shims. Raw Python source scanning is not an active runtime mechanism.
- The loader remains singular and authoritative for all runic TOML parsing and validation.

### 6. The MPL 2.0 Shield (Private Extensions)

Because the system is bound by **[The Iron Pact (00)](00-license.md)** (MPL 2.0), the Federation explicitly supports **proprietary, closed-source extensions**.

If the core were licensed under AGPLv3, proprietary in-process "Secret Sauce" would be legally burdensome and would usually need to live behind an external Animator boundary to remain private. MPL 2.0 allows private code to be linked directly into the Daemon's memory space as an Extension. The Magus retains local sovereign advantage while using the open core to participate in the A2A Swarm.

### 7. Extension Compatibility Tiers

The Federation recognizes real compatibility tiers. The boundary is not stylistic; it defines who owns breakage when the Core evolves.

- **Built-in Direct:** Core-owned extensions shipped under `src/lychd/extensions/builtin/`. They may import internals and subclass core classes because they evolve atomically with the Core.
- **Private Coupled:** Local/private extensions outside the core tree that intentionally import LychD internals. They are allowed for Magus-owned local power, but they accept refactor coupling. Assimilation may repair them later; it does not make them stable.
- **Independent Product Surface:** A future distribution tier for extensions intended to survive Core refactors and be shared across implementations. This requires a versioned public API, conformance tests, and Forge-mediated packaging. It is not the active in-process contract today.

#### The Built-in Direct Path

Built-in Extensions (`src/lychd/extensions/builtin/`) are versioned and updated **simultaneously** with the kernel. They are permitted—and expected—to use explicit imports and Abstract Base Class inheritance from the Core. Because they share a single repository and a single release cycle, a core refactor and its built-in extension updates are committed atomically. No upgrade gap exists.

The **Extension Manager** imports only configured built-in ids and Crypt ids. A selected organ exposes `register(context)`, receives the host `ExtensionContext`, and contributes through explicit registration stores. Core built-ins resolve by convention inside `lychd.extensions.builtin`; private Crypt organs resolve through their selected shim path. Codex never scans arbitrary packages to decide what is active.

Runtime-facing contributions use the same explicit registration pass. `register(context)` is the
authoritative ledger for boot-time stores such as rune schemas, Animator Soulstone definitions,
typed `run` operations, future Vessel bundles, or lifecycle hooks. Public Pulse roots remain
closed; runtime mutation should be explicit.

#### The Private Coupled Path

Private coupled extensions are local organs that behave like built-ins even though they live outside the core tree. They may import internal modules such as `lychd.config.runes` and may subclass `RuneConfig`.

This path is intentionally powerful and intentionally unsafe as a stability contract. It is appropriate for the Magus, local experiments, and organs expected to be rewritten with the Core. It is not appropriate for sovereign third-party distribution unless the author accepts breakage across Ouroboros evolution.

The Assimilation/Smith path may later migrate a private coupled organ after a refactor. That is a repair mechanism, not a compatibility guarantee.

#### The Independent Product Path (v1+)

Independent in-process extensions are a v1+ product target, not the pre-v1 foundation. A public API can reduce import-path breakage only if LychD commits to versioned semantics, compatibility tests, and a small surface that is actually kept stable. Without those commitments, a dependency-light SDK would duplicate internal concepts while still coupling authors to LychD lifecycle timing, registry semantics, Codex loading order, Pydantic behavior, and process trust.

Therefore, the near-term doctrine is:

- Do not build a separate SDK until real third-party distribution pressure exists.
- Do not promise independent in-process compatibility across arbitrary Core refactors.
- Do not treat foreign agent frameworks as first-class in-process runtimes. Wrap them behind external-service Animators, A2A Emissaries, or assimilate their useful patterns into LychD's native Pydantic AI agent runtime.
- Treat unpinned Crypt-side source loading as a future Forge/Smith assimilation concern, not as a live runtime registration path.
- Prefer external-service Animators when a capability needs a true decoupling boundary. "External-service" describes placement and protocol isolation; the exposed capability may be cognitive, observational, procedural, networked, or tool-bearing.
- Promote only the minimal host surfaces that survive repeated internal use into a future `lychd.extensions.api` module.

No public source-scanning extension ABI exists today. Any future source assimilation path must be pinned, forged, verified, and translated into the same explicit registration-store model.

#### Rune And Runtime Boundary

Extension integration has two separate contracts:

- **Rune Schema:** The extension exposes configuration shape. Coupled Python extensions may subclass `RuneConfig` and register those schemas through `context.runes`.
- **Runtime Definition:** A domain-owned store may wrap the schema with runtime machinery. For Soulstones, `SoulstoneDefinition` pairs one `SoulstoneConfig` schema with a `SoulstoneRuntimeAdapter`.

A rune schema alone is not a runtime integration. It only makes TOML loadable. If an extension registers a new rune family, it must also provide a domain definition or hydrator when that rune should become a live Animator, adapter, router, capability provider, or other runtime handle. LychD-facing runtime handles should be `Runic[T]`, meaning they expose a canonical `.rune` provenance attribute.

Foreign engine objects do not need to be `Runic`. A Rust engine, C-backed object, or private Python implementation may keep whatever internal shape it wants. The adapter wraps or translates it into a LychD-facing handle when LychD needs provenance:

```python
class AphroditeRuntime:
    def __init__(self, *, rune: AphroditeConfig, engine: object) -> None:
        self.rune = rune
        self.engine = engine
```

This keeps the contract narrow:

- Codex validates configuration.
- The adapter builds runtime state from configuration.
- The LychD-facing handle carries `.rune` so provenance is always recoverable.
- Foreign internals remain sovereign behind the adapter boundary.

A foreign organ may still use LychD's rune machinery directly if it wants a
common TOML-facing configuration surface. The stable boundary is not "Rust must
implement `Runic`"; the stable boundary is "LychD owns user-facing
configuration through Codex, then the adapter translates that validated rune
into the foreign engine's native configuration shape." This permits fast
Rust-side kernels while keeping operator configuration in one place.

#### Cross-Language Organs

Rust/PyO3 binary organs are valid future organs, but there is no stable LychD ABI today. A binary organ may be:

- a coupled in-process organ built inside the composed Forge image and repaired with the Core;
- a future public-API organ once the API is versioned and tested;
- an external-service Animator, which is the current true decoupled boundary.

Blind `.so` scans are forbidden. Binary loading must be mediated by the Synthetic Forge manifest, platform validation, and explicit operator consent before it enters runtime import.

| Property | Built-in Direct | Private Coupled | Future Independent Product |
| :--- | :--- | :--- | :--- |
| Location | `src/lychd/extensions/builtin/` | Magus-owned Crypt extension space | Forge-managed extension distribution |
| Coupling | Internal imports and subclasses | Internal imports by choice | Versioned public API only |
| Loader | Explicit selected import + `register(context)` | Explicit selected shim + `register(context)` | Deferred, manifest-gated |
| Release Cycle | Atomic with Core | Operator-owned | Independent |
| Stability Promise | Core-maintained | Best effort/local repair | Not promised until productized |
| `from lychd import ...` | Permitted | Permitted with coupling risk | Only future public API modules |

### Consequences

!!! success "Positive"
    - **High-Velocity Performance:** Capabilities execute without network overhead, enabling real-time feedback loops.

    - **Standardization:** In-process extension packages use ordinary Python plus explicit LychD
      registration stores; Extension Domains remain free to manifest through other forms.

    - **Coherent Evolution:** Extensions can participate in one assembled body. Synchronized
      migrations, Pattern/Composition stores, and physical-substrate rebuilds remain explicit
      lifecycle work until source, tests, and State prove them.

!!! failure "Negative"
    - **Systemic Risk:** A poorly written extension can crash the entire Daemon, as it runs within the same memory space and shares database connections.

    - **Disciplined Conventions:** Extensions must strictly adhere to the folder structure and registration protocols to be recognized by the Federation.
