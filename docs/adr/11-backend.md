---
title: 11. Backend
icon: material/star-shooting-outline
---

# :material-star-shooting-outline: 11. Backend: The Vessel

!!! abstract "Context and Problem Statement"
    The LychD architecture requires a modern, async-first Python web framework—referred to as **The Vessel**—to serve as the system's backbone. Traditional frameworks often enforce patterns that lead to code duplication or structural rigidity, such as circular imports caused by bound decorators. To achieve a truly modular and federated system, a solution is required that inherently reduces boilerplate, facilitates a decoupled "Plugin" architecture, and scales cleanly from a lightweight management tool to a high-concurrency server capable of handling massive cognitive state dumps without CPU bottlenecking.

## Requirements

- **Architectural Scalability:** The framework must support an unbound router system, allowing routes to be defined in isolation and "registered" without circular dependency issues.
- **Federated Logic Assimilation:** The system requires a formal **ExtensionContext** protocol to allow disparate extensions to graft routers, dependencies, and middleware onto the Vessel at runtime.
- **Persistence Efficiency (DRY):** Mandatory minimization of code duplication between database models and API schemas through automated Data Transfer Object (DTO) generation.
- **High-Throughput Serialization:** The backend must natively support high-performance binary serialization (e.g., `msgspec`) to integrate with the **[Phylactery's (06)](06-persistence.md)** binary transmutation hooks.
- **Extensible Initialization:** The framework must support a formal plugin protocol for the injection of configuration and lifecycle hooks at boot time.
- **Dual-Mode Bootstrapping:** The architecture must handle two distinct operational realities—a heavy **Server Mode** for asynchronous rituals and a lightweight **CLI Mode** for system management—within a unified entry point.

## Considered Options

!!! failure "Option 1: Django"
    A mature, monolithic framework.
    -   **Cons:** **Historical Heaviness.** Its synchronous origins require complex adapters for modern async workflows. The monolithic nature is ill-suited for the project's lean, service-oriented requirements and makes extension isolation difficult.

!!! failure "Option 2: FastAPI"
    A popular micro-framework.
    -   **Cons:** **Structural Friction.** Bound decorators tie routes directly to the application instance, complicating modular organization. The lack of deep integration with the persistence layer requires manual re-definition of every field for every API endpoint, violating the DRY principle.

!!! success "Option 3: Litestar"
    A modern framework prioritized around architectural patterns and developer ergonomics.
    -   **Pros:**
        -   **Unbound Decorators:** Enables a composable Router system where logic is collected by the application factory.
        -   **Automated DTOs:** Native support for generating API schemas directly from persistence models.
        -   **Plugin Protocols:** First-party support for `InitPluginProtocol` and `CLIPluginProtocol` allows for elegant, context-aware bootstrapping.
        -   **Native msgspec Integration:** Offers the high-performance serialization required for the system's binary transmutation strategy.

## Decision Outcome

**Litestar** is adopted as the foundational web framework for the Vessel. It provides the structure required for a federated system where logic is treated as a set of pluggable organs.

### 1. The Modular Registry (The ExtensionContext)

The application rejects the use of a global `app` object. Instead, logic is assimilated via a registration protocol:

- **The Context:** During boot, the system initializes an `ExtensionContext`. This object is passed to every extension's `register()` hook.
- **Assembly:** The application factory iterates through these registered objects, collecting `Router` instances, `Middleware`, and `Dependencies`. These are then grafted onto the Vessel to assemble the final API surface. This prevents circular imports and allows for the seamless addition of new interfaces.

### 2. The Initialization Protocol (Duality)

Application logic is encapsulated within custom initialization plugins that implement the framework's native protocols:

- **Server Context (Deep Awakening):** When executed by an ASGI server, the plugin initializes heavy infrastructure, including background **[Ghouls (14)](14-workers.md)**, observability exporters, and the full connection pool to the Phylactery.
- **CLI Context (Lightweight Manifestation):** When executed as a management tool, the plugin skips web-related infrastructure and injects custom management commands directly into the command group, ensuring near-instantaneous response times.

### 3. High-Performance Transmutation

To ensure the Vessel can handle the massive execution history and cognitive state dumps stored in the **[Phylactery (06)](06-persistence.md)**, the backend is configured for binary efficiency.

- **msgspec Integration:** The framework utilizes `msgspec` as its primary serialization engine.
- **Binary Hooks:** The Vessel leverages the custom codec hooks defined in the persistence layer. This allows the backend to receive raw binary JSONB from the database and pass it directly to the interface without intermediate string encoding, bypassing the "Double Encoding" CPU tax.

### 4. Automated Data Integrity

To ensure the persistence layer remains the single source of truth, the Vessel utilizes automated DTO utilities. This allows the system to generate request and response schemas dynamically from existing models, ensuring that the API cannot drift out of sync with the underlying data structures.

### Consequences

!!! success "Positive"
    - **Extension Sovereignty:** The unbound routing system allows extensions to function as independent entities that are cleanly assimilated at runtime.
    - **Physical Performance:** The integration of `msgspec` and binary transmutation hooks ensures the system remains responsive even when processing megabytes of cognitive trace data.
    - **Startup Velocity:** Lazy-loading heavy plugins ensures the CLI remains usable for rapid infrastructure tasks.

!!! failure "Negative"
    - **Learning Curve:** The focus on class-based controllers and DTOs represents a paradigm shift for developers accustomed to simpler micro-frameworks.
    - **Ecosystem Scale:** While growing, the community is smaller than its competitors, requiring more reliance on the framework's internal plugin suite.
