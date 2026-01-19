---
title: 9. Configuration
icon: material/cog-box
---

# :material-cog-box: 9. Centralized Configuration and Application Bootstrapping

!!! abstract "Context and Problem Statement"
    The LychD system requires numerous configuration parameters, ranging from database credentials to filesystem paths. Scattering configuration logic throughout the codebase results in an unmaintainable, untestable, and error-prone architecture.

    Additionally, the application operates in distinct execution contexts—acting as both a high-performance web server and a lightweight command-line tool.

## Decision Drivers

- **Context-Aware Initialization:** The application entry point must distinguish between execution contexts (server vs. CLI), loading only the necessary components to optimize startup performance and avoid unnecessary overhead.
- **Centralization:** All configuration logic must reside in a single, well-defined location to ensure maintainability.
- **Type Safety:** Configuration values must be validated and parsed into typed data structures at startup to prevent runtime errors.
- **Hierarchical Resolution:** The system must support a clear loading hierarchy, prioritizing sources in specific order (e.g., Environment Variables > Configuration File > Defaults).
- **Secret Sanitization:** The configuration model must utilize distinct types (e.g., `SecretStr`) for sensitive credentials. This prevents the Agent from accidentally reading or exporting its own API keys during self-reflection or debugging tasks.

## Considered Options

!!! failure "Option 1: Ad-Hoc Configuration"
    Read configuration values from various sources (os.environ, hardcoded strings) directly where they are needed in the application logic.

    -   **Pros:** Low initial friction for trivial scripts.
    -   **Cons:** Fundamentally flawed for complex systems. Leads to tight coupling, difficulties in testing, and security risks due to scattered secret management.

!!! success "Option 2: A Unified, Multi-Stage Architecture"
    Design a formal, multi-stage process for configuration and initialization that strictly separates concerns.

    -   **Pros:** Enforces a robust application structure. Makes the system easy to reason about, test, and extend. Promotes performance by enabling lazy-loading of heavy components.
    -   **Cons:** Requires stricter architectural discipline and introduces initial boilerplate.

## Decision Outcome

A formal, four-stage architecture is adopted for application configuration and bootstrapping, establishing a clear data flow from raw constants to a fully initialized application.

1. **Stage 1: The Constants (`config/constants.py`)**
    - Defines the absolute, immutable ground truths (e.g., `CODEX_PATH`).
    - Adheres to XDG standards and utilizes `Final`-typed variables to ensure immutability.

2. **Stage 2: The Settings Model (`config/settings.py`)**
    - The core of the configuration system, implemented via **`pydantic-settings`**.
    - Defines a hierarchy of typed `BaseSettings` models.
    - Implements layered loading: **Environment variables override values found in the `lychd.toml` file.**
    - A singleton `get_settings()` function ensures consistent access throughout the lifecycle.

3. **Stage 3: The Components (`config/components.py`)**
    - Acts as a factory layer for higher-level application components.
    - Imports validated `Settings` data and instantiates library objects (e.g., `SQLAlchemyAsyncConfig`, `StructlogConfig`).
    - strictly separates the "what" (configuration data) from the "how" (runtime objects).

4. **Stage 4: The Bootstrap Plugin (`app.py`)**
    - The final orchestration layer. A central `create_app()` factory instantiates the Litestar application.
    - A dedicated plugin, `AppInit`, leverages Litestar's `InitPluginProtocol` and `CLIPluginProtocol`.
    - **Optimization:** `on_app_init` (server mode) loads the full web stack, while `on_cli_init` (command mode) loads only the minimal code required for commands. This prevents initializing the entire database engine just to execute `lychd --help`.

### Consequences

!!! success "Positive"
    - **Maintainability:** The entire configuration system is centralized, type-safe, and self-documenting.
    - **Separation of Concerns:** The clear separation into stages (constants -> settings -> components -> bootstrap) decouples configuration from application logic.
    - **Performance:** Context-aware bootstrapping ensures optimized startup times, keeping the CLI responsive.

!!! failure "Negative"
    - **Boilerplate:** The architecture introduces a degree of boilerplate code. This is an accepted trade-off for long-term stability.
