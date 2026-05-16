---
title: 5. Extensions
icon: material/toy-brick-outline
---

# :material-toy-brick-outline: 5. Recursive Extension Architecture

!!! abstract "Context and Problem Statement"
    The LychD system functions as a kernel for orchestrating sovereign intelligence. Static software architectures lack the flexibility to incorporate emerging hardware interfaces, novel reasoning topologies, or specialized memory structures without intrusive core modifications. Existing plugin models typically enforce a binary choice between high-latency network communication and restrictive execution environments that prevent deep integration into the system substrate. LychD is born in an agentic era where code can be inspected, rewritten, verified, and promoted by the same system that runs it. The first extension boundary is therefore assimilation, not premature compatibility.

## Requirements

- **Native Execution Speed:** Mandatory execution of capabilities within the kernel’s memory space to eliminate the serialization overhead and latency of network-based plugin systems.
- **Deep Substrate Authority:** Provision of a mechanism for extensions to define persistent relational schemas, register background ghouls, and integrate with the system startup lifecycle.
- **Infrastructure Declaration:** Mandatory capability for extensions to declare their own physical requirements, specifically container blueprints and functional capability tags.
- **Federated Sovereignty:** Treatment of the Core and its Extensions as a "Federation" of independent components, each maintaining its own version history and repository.
- **Deterministic Provenance:** Mandatory implementation of a federated lockfile to ensure the system’s exact composition is trackable and bit-for-bit reproducible.
- **Interface Simplicity:** Utilization of standard Python patterns and registration hooks to facilitate extension creation, avoiding proprietary Domain Specific Languages (DSLs).
- **Capability-Driven Design:** Mandatory support for registering abstract functional identifiers that allow the system to orchestrate extension logic through semantic intent.
- **Extension Protocol:** Establishment of a composed-runtime law for assimilating local organs before public compatibility surfaces are harvested.

## Considered Options

!!! failure "Option 1: Microservice Plugins"
    Deploying every extension as a separate container communicating via HTTP or gRPC.

    - **Cons:** **Architectural Fragmentation.** This introduces significant latency for internal tool calls and complicates the sharing of atomic database transactions. It forces a "Small-Talk" overhead that is unacceptable for real-time sensory loops.

!!! failure "Option 2: Sandboxed Scripting (WASM/Lua)"
    Running extensions in a restricted, safe runtime environment.

    - **Cons:** **Functional Castration.** A sandboxed environment prevents deep integration. A script cannot easily define new relational models or register system-level background ghouls, violating the principle of deep modularity.

!!! success "Option 3: Native Recursive Extensions"
    Extensions are Python packages loaded directly into the Daemon's memory space, managed as Forge-composed Git repositories within a unified Federation.

    - **Pros:**
        - **Zero-Latency:** Direct execution within the kernel's event loop enables high-velocity reasoning.
        - **Total Integration:** Extensions can manipulate any part of the system's anatomy, from the persistence layer to the web router.
        - **Assimilable Source:** Standard Git tooling preserves source history while Forge/Smith verification repairs organs with the body they join.

## Decision Outcome

**Native Recursive Extensions** are adopted as the standard for system evolution. The Daemon functions as a **Runtime Package Manager**, coordinating a collection of repositories into a single, cohesive organism.

LychD's first extension boundary is not compatibility; it is assimilation. Public compatibility is a product of maturity, not the foundation of infancy.

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

- **Built-in Extensions:** Residing in `src/lychd/extensions/builtin/`. These are core features and reference implementations shipped within the kernel's source tree. They are grafted into the memory space during every boot cycle, providing high-velocity baseline capabilities without requiring a substrate rebuild.
- **Crypt Extensions:** Residing in the **Crypt (13)** (`~/.local/share/lychd/extensions/`). Near-term Crypt organs are private coupled repositories unless they explicitly target a future versioned public API. They require the **Synthetic Forge (17)** to resolve dependency conflicts and manifest a new physical substrate.
- **Future Independent Extensions:** Shareable third-party organs become meaningful at or after v1, when proven patterns can be frozen behind a versioned public API, conformance tests, and manifest-gated packaging.
- **The Manifest:** The Daemon maintains a global lockfile that records the specific commit hash of every active repository. This ensures the Federation is a deterministic body that can be captured, snapshotted, and restored as a single, bit-for-bit reproducible unit.

### 2. The Registration Surface (The Extension Context)

The architecture relies on an **Inversion of Control** pattern to facilitate assimilation. The Core provides a host registration surface, but that surface is only one branch of the broader Extension Protocol.

- **The Entry Point:** Any organ participating in in-process boot grafting exposes a `register(context)` function in its root package.
- **The Context Object:** The Core passes an `ExtensionContext` object which serves as the host registration surface for boot-time grafting. Through this object, an organ binds runtime-facing logic into the Daemon's anatomy.
- **Interface Grafting:** The active source surface accepts unbound `Router` objects and standalone `Controller` classes for the Vessel.
- **Schema Exposure:** Configuration discovery is not a method on the `ExtensionContext`. Near-term in-process organs expose `RuneConfig` subclasses after import; a provisional structural scan exists for Python source experiments, but it is not a public API or stability promise.
- **Substrate Declarations:** Synthesis-time requirements (system libraries, binaries, container needs) belong to the wider Extension Protocol and feed the Forge manifest. They must not be confused with the boot-time context itself.

### 3. Capabilities as Organs

Extensions are more than isolated code; they are functional "Organs" of the Daemon.

- **The Contract:** An extension registers a set of **Capabilities**—abstract identifiers of what the extension can perform (e.g., specific sensory tasks or logic operations).
- **The Manifestation:** If an extension requires specific hardware or environment states to fulfill its capabilities, it must declare these needs during the registration phase.
- **Evolutionary Scaling:** This ensures the Daemon's senses and skills are pluggable. The Core provides the skeleton; the Extensions provide the organs that animate it.

### 4. Substrate Injections

Extensions are not limited to Python logic. They may declare system-level dependencies (e.g., C-libraries like `ffmpeg` or specialized binaries) as part of the wider Extension Protocol. The assembly process collects these physical requirements into the synthesis manifest and injects them into the physical body of the Daemon during the **Synthetic Forge (17)** process.

### 5. Runtime Schema Discovery

Configuration extensibility uses the schema branch of the Extension Protocol:

- Extension modules are imported at runtime during codex/bootstrap.
- Built-in and private coupled organs may expose `RuneConfig` subclasses directly.
- `__subclasses__()` traversal is a schema-discovery convenience after import. It is not the runtime extension ledger and not a public extension API.
- Experimental Crypt-side Python source modules may expose Pydantic-compatible schema classes matching the Codex discovery shape, but this path is not a stable third-party contract.
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

The **Built-in Loader** imports the configured `lychd.extensions` package tree at boot via `pkgutil.walk_packages`. `RuneConfig.__subclasses__()` discovery fires automatically upon import. This is acceptable for schema registration because the code is already in-process and version-locked with the Core.

Runtime-facing contributions still use explicit registration when a host surface exists. `register(context)` is the authoritative ledger for boot-time grafting such as routers, controllers, factories, lifecycle hooks, or future command hooks. Schema discovery may remain structural; runtime mutation should be explicit.

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
- Treat Crypt-side source loading as a local/provisional assimilation mechanism unless the extension is pinned, forged, and verified with the composed runtime image.
- Prefer external-service Animators when a capability needs a true decoupling boundary. "External-service" describes placement and protocol isolation; the exposed capability may be cognitive, observational, procedural, networked, or tool-bearing.
- Promote only the minimal host surfaces that survive repeated internal use into a future `lychd.extensions.api` module.

The provisional structural scan currently exercises only a narrow schema branch for Python source modules. It is useful for experiments, but it is not the public compatibility product.

#### Rune And Runtime Boundary

Extension integration has two separate contracts:

- **Rune Schema:** The extension exposes configuration shape. Coupled Python extensions may subclass `RuneConfig`; provisional structural schemas must be Pydantic-compatible and expose a safe `relative_path`.
- **Runtime Hydrator:** A factory, adapter, or provider converts a validated rune into the runtime object LychD stores and operates.

A rune schema alone is not a runtime integration. It only makes TOML loadable. If an extension registers a new rune family, it must also provide a hydrator when that rune should become a live Animator, adapter, router, capability provider, or other runtime handle. LychD-facing runtime handles should be `Runic[T]`, meaning they expose a canonical `.rune` provenance attribute.

Foreign engine objects do not need to be `Runic`. A Rust engine, C-backed object, or private Python implementation may keep whatever internal shape it wants. The adapter wraps or translates it into a LychD-facing handle:

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
| Loader | Package import + subclass walk | Local import path chosen by operator | Deferred, manifest-gated |
| Release Cycle | Atomic with Core | Operator-owned | Independent |
| Stability Promise | Core-maintained | Best effort/local repair | Not promised until productized |
| `from lychd import ...` | Permitted | Permitted with coupling risk | Only future public API modules |

### Consequences

!!! success "Positive"
    - **High-Velocity Performance:** Capabilities execute without network overhead, enabling real-time feedback loops.

    - **Standardization:** Extensions are standard Python projects, requiring no proprietary packaging formats.

    - **Coherent Evolution:** Extensions feel like native parts of the application. The system can iterate over the registered extensions to perform synchronized database migrations or physical substrate rebuilds.

!!! failure "Negative"
    - **Systemic Risk:** A poorly written extension can crash the entire Daemon, as it runs within the same memory space and shares database connections.

    - **Disciplined Conventions:** Extensions must strictly adhere to the folder structure and registration protocols to be recognized by the Federation.
