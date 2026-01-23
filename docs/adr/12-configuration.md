---
title: 12. Configuration
icon: material/cog-box
---

# :material-cog-box: 12. Configuration: The Codex

!!! abstract "Context and Problem Statement"
    Configuration fragmentation creates "Environmental Dissonance"—a state where the machine’s intent is scattered across disparate files, environment variables, and hardcoded logic. In a system bridging the Host and the Container, this leads to structural blindness where the CLI and the Vessel disagree on the location of the **Phylactery (06)** or the state of the network. Without a centralized, type-safe arbiter, the system is prone to "Port Singularities" (collisions) and "Permission Paradoxes," resulting in unrecoverable boot failures and insecure secret handling.

## Requirements

- **Resource Arbitration:** Mandatory validation that no two services (Core or Extensions) claim the same TCP port before the awakening process begins.
- **Environmental Symmetry:** Provision of identical configuration paths and logic regardless of whether the execution occurs on the Host or within the Container.
- **Type-Safe Inscription:** Strict validation of types and required fields at load-time to prevent "Silent Failures" and runtime crashes.
- **Secure Secret Sequestration:** Implementation of a mechanism to handle sensitive credentials (API keys, DB passwords) using specialized types that prevent accidental leakage in logs or traces.
- **Atomic Initialization:** Capability to generate a fully commented, up-to-date configuration scroll on first run by introspecting the system's internal schemas.
- **Extensible Schema Anatomy:** Support for nested settings models that allow Extensions to graft their own configuration sections onto the primary scroll.

## Considered Options

!!! failure "Option 1: Hardcoded Path Logic"
    Defining static paths for different environments (e.g., `/app/config` for containers and `~/.config` for host).
    -   **Pros:** Explicit and simple to implement.
    -   **Cons:** **High Cognitive Load.** Requires maintaining branching logic throughout the codebase. It breaks if the system is executed in a non-standard environment or shifted to a different directory.

!!! success "Option 2: Unified Symmetric Architecture"
    Designing a configuration system coupled with a strict **Port Arbiter** and symmetric volume mapping.
    -   **Pros:**
        -   **Symmetry:** By mounting host volumes to predictable container targets, the same configuration paths remain valid in both contexts.
        -   **Safety:** The application refuses to boot if a port conflict is detected mathematically, rather than crashing unpredictably at runtime.
        -   **Validation:** Utilizing Pydantic ensures that invalid types or missing required fields are caught instantly.

## Decision Outcome

A formal configuration architecture is adopted, centered around **The Codex**—a directory acting as the single source of truth for user intent.

### 1. The Codex and The Prime Directive

The configuration resides in a dedicated directory structure governed by a primary manifest.

- **The Codex:** The root directory at `~/.config/lychd/`.
- **The Prime Directive (`lychd.toml`):** The central scroll containing the system's logic and secrets. It is the primary source of truth.
- **The Secret Ward:** While `.env` files are supported as overrides, the system prioritizes `lychd.toml`. To ensure security, this file must be treated with a `600` permission. Sensitive values (like `secret_key` or `db_password`) are automatically generated with secure random defaults on first run if they are not provided, ensuring the system is "Secure by Default."
- **Symmetric Volume Mapping:** The **Hand (18)** ensures that `~/.config/lychd/` on the host is mapped to the same path inside the container. This "Symmetry" allows the code to resolve its Law without context-aware path translation.

### 2. The Settings Model (Pydantic-Settings)

The core of the configuration system is implemented via `pydantic-settings`, providing a robust, type-safe interface for all components.

- **Layering:** Settings are resolved in a strict order: Hardcoded Defaults $\to$ `lychd.toml` $\to$ Environment Variables (using a `__` nested delimiter, e.g., `DB__PORT`).
- **SecretStr Protection:** All credentials utilize the `SecretStr` type. This ensures that passwords and keys are never printed in plain text within the **Oculus (28)** traces or system logs.
- **Binary Transmutation Hook:** The configuration model includes a private hook to the database engine. When initialized, it injects the binary codec required to prepend the `\x01` version header to **msgspec**-serialized bytes, enabling high-performance JSONB storage in the **Phylactery (06)**.

### 3. The Port Arbiter (System & Dynamic)

To prevent the "Port Singularity"—where multiple services fight for the same socket—the configuration model implements a strict, multi-layered validator.

- **The Reserved Map:** The arbiter maintains a hardcoded map of all critical system ports:
    - `7134`: Vessel (The primary Web Server)
    - `5432`: Phylactery (The PostgreSQL engine)
    - `6006/4318`: Oculus (Observability UI and OTLP collector)
    - `5173`: Vite (The asset development server)
- **Dynamic Soulstone Inspection:** The arbiter extends its search into the `soulstones/` directory of the Codex. It parses the `port` definition of every **Soulstone (08)** intent.
- **Collision Detection:** At boot time, the settings model aggregates the Reserved Map and the Dynamic Soulstones into a single collision plane. If any two entities—whether a core service and a soulstone, or two soulstones—claim the same integer, the system raises a `ValueError` immediately.
- **Fail-Fast Doctrine:** This ensures that configuration errors are caught during the "Incantation" (Loading) phase, preventing the **Hand (18)** from writing invalid **Runes (08)** that would cause the host init system to enter a crash loop.

### 4. Recursive Configuration Grafting

The settings architecture is designed to support the **Federation (05)** through a modular schema.

- **Nested Models:** The root `Settings` class is composed of domain-specific models (e.g., `DatabaseSettings`, `LogSettings`).
- **Late-Binding Validation:** This pattern allows the system to validate the entire physical reality of the Sepulcher in one pass. Every component, from the core database to a third-party extension's inference container, is subject to the same strict validation laws.
- **Self-Documenting:** The `lychd init` command generates a fully commented TOML file based on these schemas, ensuring the Magus always has a valid blueprint for the machine.

### Consequences

!!! success "Positive"
    - **Operational Clarity:** The Host/Container configuration paradox is solved via physical symmetry rather than code complexity.
    - **System Stability:** Port conflicts and type errors are caught at configuration load time (sub-second), preventing unrecoverable crashes during container startup.
    - **Secure Provenance:** Automatic secret generation and the use of `SecretStr` provide a secure-by-default posture for both the Magus and the Machine.
    - **Self-Documenting:** The `lychd init` command generates a fully commented TOML file based on the system's actual code schemas.

!!! failure "Negative"
    - **Mount Discipline:** The system relies on the **Hand (18)** to correctly map the Codex volume. If the mapping is interrupted, the application reverts to defaults or fails to start.
    - **Permission Sensitivity:** Storing secrets in a TOML file requires the user to maintain strict filesystem permissions (`600`) to prevent local data exposure.
