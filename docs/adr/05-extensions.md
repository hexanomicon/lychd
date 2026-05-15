---
title: 5. Extensions
icon: material/toy-brick-outline
---

# :material-toy-brick-outline: 5. Recursive Extension Architecture

!!! abstract "Context and Problem Statement"
    The LychD system functions as a kernel for orchestrating sovereign intelligence. Static software architectures lack the flexibility to incorporate emerging hardware interfaces, novel reasoning topologies, or specialized memory structures without intrusive core modifications. Existing plugin models typically enforce a binary choice between high-latency network communication and restrictive execution environments that prevent deep integration into the system substrate. This creates a functional disconnect between the stable core and the evolving requirements of agentic capabilities. A foundational architecture is required to define how external logic and infrastructure intents are assimilated into the Daemon’s physical and cognitive anatomy.

## Requirements

- **Native Execution Speed:** Mandatory execution of capabilities within the kernel’s memory space to eliminate the serialization overhead and latency of network-based plugin systems.
- **Deep Substrate Authority:** Provision of a mechanism for extensions to define persistent relational schemas, register background ghouls, and integrate with the system startup lifecycle.
- **Infrastructure Declaration:** Mandatory capability for extensions to declare their own physical requirements, specifically container blueprints and functional capability tags.
- **Federated Sovereignty:** Treatment of the Core and its Extensions as a "Federation" of independent components, each maintaining its own version history and repository.
- **Deterministic Provenance:** Mandatory implementation of a federated lockfile to ensure the system’s exact composition is trackable and bit-for-bit reproducible.
- **Interface Simplicity:** Utilization of standard Python patterns and registration hooks to facilitate extension creation, avoiding proprietary Domain Specific Languages (DSLs).
- **Capability-Driven Design:** Mandatory support for registering abstract functional identifiers that allow the system to orchestrate extension logic through semantic intent.
- **Extension Protocol:** Establishment of a structural law to integrate independent logic and infrastructure intents into the Daemon’s anatomy without compromising system-wide stability.

## Considered Options

!!! failure "Option 1: Microservice Plugins"
    Deploying every extension as a separate container communicating via HTTP or gRPC.

    - **Cons:** **Architectural Fragmentation.** This introduces significant latency for internal tool calls and complicates the sharing of atomic database transactions. It forces a "Small-Talk" overhead that is unacceptable for real-time sensory loops.

!!! failure "Option 2: Sandboxed Scripting (WASM/Lua)"
    Running extensions in a restricted, safe runtime environment.

    - **Cons:** **Functional Castration.** A sandboxed environment prevents deep integration. A script cannot easily define new relational models or register system-level background ghouls, violating the principle of deep modularity.

!!! success "Option 3: Native Recursive Extensions"
    Extensions are Python packages loaded directly into the Daemon's memory space, managed as independent Git repositories within a unified Federation.

    - **Pros:**
        - **Zero-Latency:** Direct execution within the kernel's event loop enables high-velocity reasoning.
        - **Total Integration:** Extensions can manipulate any part of the system's anatomy, from the persistence layer to the web router.
        - **Individual Versioning:** Standard Git tooling handles the evolution of each organ independently.

## Decision Outcome

**Native Recursive Extensions** are adopted as the standard for system evolution. The Daemon functions as a **Runtime Package Manager**, coordinating a collection of independent repositories into a single, cohesive organism.


### 1. The Federation Strategy

The system's logic resides in a structured directory hierarchy designed for modularity, distinguishing between the system's shipped capabilities and its elective augmentations:

- **Built-in Extensions:** Residing in `src/lychd/extensions/builtin/`. These are core features and reference implementations shipped within the kernel's source tree. They are grafted into the memory space during every boot cycle, providing high-velocity baseline capabilities without requiring a substrate rebuild.
- **Independent Extensions:** Residing in the **Crypt (13)** (`~/.local/share/lychd/extensions/`). Each subdirectory is a standalone Git repository containing its own dependency manifests (`pyproject.toml`). These require the **Synthetic Forge (17)** to resolve dependency conflicts and manifest a new physical substrate.
- **The Manifest:** The Daemon maintains a global lockfile that records the specific commit hash of every active repository (both Built-in and Independent). This ensures the Federation is a deterministic body that can be captured, snapshotted, and restored as a single, bit-for-bit reproducible unit.

### 2. The Registration Surface (The Extension Context)

The architecture relies on an **Inversion of Control** pattern to facilitate assimilation. The Core provides a host registration surface, but that surface is only one branch of the broader Extension Protocol.

- **The Entry Point:** Any organ participating in in-process boot grafting exposes a `register(context)` function in its root package.
- **The Context Object:** The Core passes an `ExtensionContext` object which serves as the host registration surface for boot-time grafting. Through this object, an organ binds runtime-facing logic into the Daemon's anatomy.
- **Interface Grafting:** The active source surface accepts unbound `Router` objects and standalone `Controller` classes for the Vessel.
- **Schema Exposure:** Configuration discovery is not a method on the `ExtensionContext`. Organs surface schema classes that satisfy the Codex discovery shape, allowing new rune families to be recognized without inheriting from mutable Core ABCs.
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
- Built-in organs may expose `RuneConfig` subclasses directly.
- Independent organs surface schema classes matching the Codex discovery shape.
- Structural presence is the discovery signal; no extra registration calls are required.
- The loader remains singular and authoritative for all runic TOML parsing and validation.

### 6. The MPL 2.0 Shield (Private Extensions)

Because the system is bound by **[The Iron Pact (00)](00-license.md)** (MPL 2.0), the Federation explicitly supports **proprietary, closed-source extensions**. 

If the core were licensed under AGPLv3, any private "Secret Sauce" would have to be built as a separate network Animator to avoid copyleft infection. The MPL 2.0 allows you to statically link your private code directly into the Daemon's memory space as an Extension. You retain your local sovereign advantage while using the open core to participate in the A2A Swarm.

### 7. The Dual-Path Extension Model

The Federation enforces a hard boundary between how Built-in Extensions and Independent Extensions are permitted to bind to the Core. This boundary is not a stylistic preference; it is a structural immune response to the fragility introduced by the **[Ouroboros Protocol (18)](18-evolution.md)**.

#### The Built-in Direct Path

Built-in Extensions (`src/lychd/extensions/builtin/`) are versioned and updated **simultaneously** with the kernel. They are permitted—and expected—to use explicit imports and Abstract Base Class inheritance from the Core. Because they share a single repository and a single release cycle, a core refactor and its built-in extension updates are committed atomically. No upgrade gap exists.

The **Built-in Loader** imports the entire `lychd.extensions.builtin` package tree at boot via `pkgutil.walk_packages`. ABC subclass detection fires automatically upon import; no procedural registration is required.

#### The Independent Protocol Path (Mandated Architecture)

Independent Extensions (`extensions/` in the Crypt) are **independent repositories** with independent release cycles. They must **never** import LychD internals.

!!! warning "The ABC Trap"
    Independent extension authors must never inherit from LychD base classes or import internal symbols (`from lychd import ...`). Any such coupling creates a hard dependency on a specific internal identifier. When the **[Ouroboros Protocol (18)](18-evolution.md)** rebases the Core, that identifier may be renamed, moved, or removed. The extension's import fails. The Daemon cannot load. A self-update becomes a self-lobotomy.

The correct contract for an Independent Extension is the **Extension Protocol**: a structural law, not an inheritance chain. Core protocol fragments are defined centrally in `src/lychd/extensions/` using Python's `@runtime_checkable Protocol`. In the current doctrine, that law is layered:

- **Schema Branch:** The Codex loader looks for schema classes exposing the discovery shape (today: `relative_path`, `singleton`, and related schema metadata). This is the branch concretely exercised by the independent Crypt scan in the current source.
- **Registration Branch:** Organs participating in in-process boot grafting expose `register(context: ExtensionContext)` and bind through the host-provided context surface.
- **Binary Branch:** Compiled `.so` organs may expose the same Python-visible shapes through PyO3 or equivalent bindings.

If these shapes are present, the organ is assimilable. The answer is independent of the module's origin, import history, or Python heritage.

**The Independent Loader** is mandated to use `importlib.machinery` (e.g., `SourceFileLoader` for `.py` files, `ExtensionFileLoader` for compiled `.so` artifacts) to load files directly from the Crypt path without requiring the extension to be installed as a Python package on `sys.path`. This decouples the loading mechanism from Python's packaging layer entirely.

#### Cross-Language ABI Support

Because the contract is a **memory shape** rather than an import tree, Independent Extensions are not restricted to Python. A module compiled from **Rust via PyO3** to a `.so` shared object can expose the same Python-visible schema classes and boot hook surface. The Independent Loader's `importlib.machinery.ExtensionFileLoader` loads it identically.

This is the **Active Architectural Standard**. LychD is designed from day one to assimilate high-performance binary organs. The ABI is one branch of the Extension Protocol; the implementation language is sovereign.

| Property | Built-in (Direct Path) | Independent (Protocol Path) |
| :--- | :--- | :--- |
| Location | `src/lychd/extensions/builtin/` | `extensions/` (Crypt) |
| Coupling | Direct internal API + explicit imports ✅ | Extension Protocol + structural shapes |
| Loader | `pkgutil.walk_packages` | `importlib.machinery` |
| Languages | Python | Python **and** Rust/PyO3 (`.so`) |
| Release Cycle | Atomic with Core | Independent |
| `from lychd import ...` | Permitted | **Forbidden** |

### Consequences

!!! success "Positive"
    - **High-Velocity Performance:** Capabilities execute without network overhead, enabling real-time feedback loops.

    - **Standardization:** Extensions are standard Python projects, requiring no proprietary packaging formats.

    - **Coherent Evolution:** Extensions feel like native parts of the application. The system can iterate over the registered extensions to perform synchronized database migrations or physical substrate rebuilds.

!!! failure "Negative"
    - **Systemic Risk:** A poorly written extension can crash the entire Daemon, as it runs within the same memory space and shares database connections.

    - **Disciplined Conventions:** Extensions must strictly adhere to the folder structure and registration protocols to be recognized by the Federation.
