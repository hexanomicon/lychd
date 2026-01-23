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
- **Deep Assimilation Protocol:** Establishment of a protocol to integrate external logic and infrastructure intents into the Daemon’s anatomy without compromising system-wide stability.

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
        - **Sovereign Versioning:** Standard Git tooling handles the evolution of each organ independently.

## Decision Outcome

**Native Recursive Extensions** are adopted as the standard for system evolution. The Daemon functions as a **Runtime Package Manager**, coordinating a collection of independent repositories into a single, cohesive organism.

### 1. The Federation Strategy

The system's logic resides in a structured directory hierarchy designed for modularity:

- **The Sphere:** All external logic resides in a dedicated `extensions/` directory. Each subdirectory is a standalone Git repository containing its own dependency manifests (`pyproject.toml`).
- **The Manifest:** The Daemon maintains a global lockfile that records the specific commit hash of every active repository. This ensures the Federation is a deterministic body that can be captured, snapshotted, and restored as a single unit.

### 2. The Registration API (The Hook)

The architecture relies on an **Inversion of Control** pattern to facilitate assimilation. The Core provides a hook, and the Extension declares its existence and requirements.

- **The Entry Point:** Every valid extension must expose a `register(context)` function in its root package.
- **The Context Object:** The Core passes a `Context` object which serves as the "Genetic API" for grafting. Through this object, the extension integrates itself into the Daemon's anatomy:
    - **Relational Grafting:** Inscribing new tables into the unified database.
    - **Infrastructure Grafting:** Declaring new container and hardware requirements.
    - **Cognitive Grafting:** Registering new reasoning steps or agents into the cortex (detailed in later covenants).

### 3. Capabilities as Organs

Extensions are more than isolated code; they are functional "Organs" of the Daemon.

- **The Contract:** An extension registers a set of **Capabilities**—abstract identifiers of what the extension can perform (e.g., specific sensory tasks or logic operations).
- **The Manifestation:** If an extension requires specific hardware or environment states to fulfill its capabilities, it must declare these needs during the registration phase.
- **Evolutionary Scaling:** This ensures the Daemon's senses and skills are pluggable. The Core provides the skeleton; the Extensions provide the organs that animate it.

### 4. Substrate Injections

Extensions are not limited to Python logic. They may register system-level dependencies (e.g., C-libraries or specialized binaries). The system's assembly process identifies these requirements during the registration phase and injects them into the physical body of the Daemon during the forge process.

### Consequences

!!! success "Positive"
    - **High-Velocity Performance:** Capabilities execute without network overhead, enabling real-time feedback loops.
    - **Standardization:** Extensions are standard Python projects, requiring no proprietary packaging formats.
    - **Coherent Evolution:** Extensions feel like native parts of the application. The system can iterate over the registered extensions to perform synchronized database migrations or physical substrate rebuilds.

!!! failure "Negative"
    - **Systemic Risk:** A poorly written extension can crash the entire Daemon, as it runs within the same memory space and shares database connections.
    - **Disciplined Conventions:** Extensions must strictly adhere to the folder structure and registration protocols to be recognized by the Federation.
