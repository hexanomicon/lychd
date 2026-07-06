---
title: 11. Backend
icon: material/star-shooting-outline
---

# :material-star-shooting-outline: 11. Backend: The Vessel

!!! abstract "Context and Problem Statement"
    The LychD architecture requires a modern, async-first Python web framework—referred to as **The Vessel**—to serve as the system's backbone. Python is retained as the foundational substrate due to its unmatched AI ecosystem and agility, delegating concurrency to the architectural level (async routing + background workers) rather than switching to Go, Rust, or Elixir. Traditional frameworks often enforce patterns that lead to code duplication or structural rigidity, such as circular imports caused by bound decorators. To achieve a truly modular and federated system, a solution is required that inherently reduces boilerplate, facilitates a decoupled "Plugin" architecture, and scales cleanly from a lightweight management tool to a high-concurrency server capable of handling massive cognitive state dumps without CPU bottlenecking.

## Requirements

- **Architectural Scalability:** The framework must support an unbound router system, allowing routes to be defined in isolation and "registered" without circular dependency issues.
- **Federated Logic Assimilation:** The system requires a formal **Extension Context** registration surface to allow disparate organs to graft runtime-facing logic onto the Vessel without coupling themselves to a global `app` object.
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
        -   **Automated DTOs:** Native support for generating API schemas directly from persistence models, ensuring the Database remains the single source of truth without writing Pydantic schemas multiple times.
        -   **Advanced Alchemy Repository Pattern:** Out-of-the-box async Repository patterns (`SQLAlchemyAsyncRepository`) provide robust, type-safe CRUD operations, pagination, and UUID handling without writing raw SQL or repetitive session logic.
        -   **Built-in HTMX & Telemetry:** First-class support for returning HTMX fragments natively (aligning with the **[Frontend (15)](15-frontend.md)** Altar strategy) and built-in OpenTelemetry for tracing Agent "Thought Traces" (aligning with the **[Observability (29)](29-observability.md)** Oculus strategy).
        -   **Plugin Protocols:** First-party support for `InitPluginProtocol` and `CLIPluginProtocol` allows for elegant, context-aware bootstrapping.
        -   **Native msgspec Integration:** Offers the high-performance serialization required for the system's binary transmutation strategy.

## Decision Outcome

**Litestar** is adopted as the foundational web framework for the Vessel. It provides the structure required for a federated system where logic is treated as a set of pluggable organs.

### 1. The Modular Registry (The Extension Context)

The application rejects the use of a global `app` object. Instead, logic is assimilated via a registration protocol:

- **The Context:** During boot, the system initializes an `ExtensionContext`. It is the host-provided registration surface for selected organs, not the whole Extension Protocol defined in **[ADR 05](./05-extensions.md)**.
- **Assembly:** The current source exposes `context.vessel` only as a reserved store. Route, middleware, auth, and event bundles must be shaped there before the application factory may collect them. This preserves the no-global-`app` rule without flattening Vessel concerns onto `ExtensionContext`.

### 2. The Initialization Protocol (Duality)

Application logic is encapsulated within custom initialization plugins that implement the framework's native protocols:

- **Server Context (Deep Awakening):** When executed by an ASGI server, the plugin initializes heavy infrastructure, including background **[Ghouls (14)](14-workers.md)**, observability exporters, and the full connection pool to the Phylactery.
- **CLI Context (Lightweight Manifestation):** When executed as a management tool, the plugin skips web-related infrastructure and injects custom management commands directly into the command group, ensuring near-instantaneous response times.

### 3. High-Performance Transmutation

To ensure the Vessel can handle the massive execution history and cognitive state dumps stored in the **[Phylactery (06)](06-persistence.md)**, the backend is configured for binary efficiency.

- **msgspec Integration:** The framework utilizes `msgspec` as its primary serialization engine.
- **Binary Hooks:** The Vessel leverages the custom codec hooks defined in the persistence layer. This allows the backend to receive raw binary JSONB from the database and pass it directly to the interface without intermediate string encoding, bypassing the "Double Encoding" CPU tax.
- **The Tomb** config is a generated runtime envelope with only task-safe fields.
- **The Tomb** config is derived data, never an alternate source of truth.
- **The Tomb** schema forbids secret fields and infrastructure authority fields.
- Provider/API keys are never serialized into **Tomb** payloads.
- **The Tomb** cannot override queue, network, or authority policy.

### 4. Automated Data Integrity

To ensure the persistence layer remains the single source of truth, the Vessel utilizes `SQLAlchemyDTO` factories from Litestar's native DTO system. When the **[Phylactery (06)](06-persistence.md)** schema changes, the API schema auto-projects it. There are no manually maintained Pydantic "shadow schemas" for ORM models in the Vessel codebase.

### 5. Dual-Plane Trust Delta

Backend scope is now explicitly control-plane only.

- Vessel owns API, orchestration, control-plane queue policy, persistence access, and promotion authority.
- Vessel agents can plan, score, route, validate, and gate HitL.
- When a Vessel-side agent needs unsafe execution, it serializes only the hand-work into a Tomb job; the agent itself does not migrate into the Tomb.
- **The Tomb** mounts only task/workspace/artifact regions with minimal write scope.
- Suggested **Tomb** regions:
    - `~/.local/share/lychd/tomb/jobs/` — one subdirectory per SAQ job to prevent file collisions between concurrent Ghouls
    - `~/.local/share/lychd/tomb/workspaces/`
    - `~/.local/share/lychd/tomb/artifacts/`
    - `~/.local/share/lychd/tomb/cache/`
- **The Tomb** must not mount writable Codex, provider secrets, or host trigger/signaling paths. If a job profile needs configuration-shaped facts, the profile receives no Codex mount by default or a read-only/sanitized projection.
- **The Tomb** may receive a narrow queue-only SAQ/Postgres execution credential for execution-plane job claiming, acknowledgement, and retry bookkeeping, but no control-plane database authority.
- **The Tomb** runs no agent logic, graph runners, or LLM calls. It is a brainless executor. See **[Workers (14)](14-workers.md)** for the full doctrine.

### 6. The Four Covenants of the Vessel

These are non-negotiable implementation laws for all code written against the Vessel. They are the direct consequence of choosing Litestar to support the federated, decoupled extension architecture. Agents and human contributors must adhere to them without exception.

#### I. The Unbound Routing Law

!!! warning "Forbidden"
    `@app.get(...)`, `@app.post(...)`, or any decorator that binds a route directly to the application instance. This couples the route to a specific `app` object at import time and blocks later `context.vessel` collection.

**Mandate:** All routes must be defined in standalone `Controller` classes or unbound `Router` instances. Once `VesselStore` grows route bundles, the application factory can collect those unbound objects at boot; they must have zero knowledge of the application object at definition time.

```python
# ✅ Correct — unbound, collectable
from litestar import Controller, get, Router

class RuneController(Controller):
    path = "/runes"

    @get("/")
    async def list_runes(self) -> list[RuneDTO]: ...

router = Router(path="/api", route_handlers=[RuneController])

# Future VesselStore shape, once route bundles are active:
# context.vessel.http.add_router(router)
```

#### II. The DTO Mandate (Death to Boilerplate)

!!! warning "Forbidden"
    Writing a standalone `class RuneRead(BaseModel): ...` that mirrors fields already defined on a SQLAlchemy ORM model. This creates maintenance drift: every schema change in the **[Phylactery (06)](06-persistence.md)** must be manually replicated.

**Mandate:** Use Litestar's `SQLAlchemyDTO` factories to derive read/write/patch schemas directly from ORM models. The database model is the single source of truth; the DTO is a projection of it.

```python
# ✅ Correct — schema derived from ORM, no duplication
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto import DTOConfig

class RuneReadDTO(SQLAlchemyDTO[RuneModel]):
    config = DTOConfig(exclude={"secret_field"})

class RuneWriteDTO(SQLAlchemyDTO[RuneModel]):
    config = DTOConfig(include={"name", "runic", "config"})
```

#### III. The Repository Law (Advanced Alchemy)

!!! warning "Forbidden"
    Raw `session.execute(select(RuneModel).where(...))` calls inside route handlers or agent tools. This tightly couples data access to the HTTP request lifecycle and makes the same queries unavailable to background **[Ghouls (14)](14-workers.md)** and reasoning graphs that operate outside the web context.

**Mandate:** All CRUD operations must use `SQLAlchemyAsyncRepository` from `advanced_alchemy`. The repository is injected via Litestar's dependency system, keeping the data access layer reusable across the HTTP layer, the SAQ worker layer, and the agent graph layer.

```python
# ✅ Correct — repository injected, decoupled from HTTP cycle
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from litestar import get
from litestar.di import Provide

class RuneRepository(SQLAlchemyAsyncRepository[RuneModel]):
    model_type = RuneModel

async def provide_rune_repo(db_session: AsyncSession) -> RuneRepository:
    return RuneRepository(session=db_session)

@get("/runes", dependencies={"repo": Provide(provide_rune_repo)})
async def list_runes(repo: RuneRepository) -> list[RuneReadDTO]:
    return await repo.list()
```

#### IV. The Native Response Law

!!! warning "Forbidden"
    Installing external HTMX middleware or a third-party OpenTelemetry integration library when Litestar provides these natively. External middleware for natively-supported features adds dependency weight and can conflict with Litestar's plugin lifecycle.

**Mandate:**
- **Altar (HTMX):** Use Litestar's `HTMXRequest` and `HTMXResponse` types. Use `HTMXPlugin` for global configuration. Return `Template` responses with `hx-swap` headers natively. The `litestar[htmx]` extra is a first-class dependency of the Vessel, not an optional add-on; the HTMX request/response surface is always present.
- **Oculus (Observability):** Use Litestar's built-in `OpenTelemetryPlugin` for tracing Agent Thought Traces. Do not introduce `opentelemetry-instrumentation-fastapi` or equivalent shims.
- **Graph Scrying (Mermaid):** Graph visualizations render client-side from the `stateDiagram-v2` source produced by `graph.mermaid_code()` (see **[Graph (24)](24-graph.md)**). The Vessel ships diagram source as text; there is no server-side image-rendering API.

```python
# ✅ Correct — native plugins, no external shims
from litestar.contrib.htmx.plugins import HTMXPlugin
from litestar.plugins.opentelemetry import OpenTelemetryPlugin, OpenTelemetryConfig
from litestar import Litestar

app = Litestar(
    plugins=[
        HTMXPlugin(),
        OpenTelemetryPlugin(config=OpenTelemetryConfig(tracer_provider=...)),
    ],
)
```

### Policy Table

| Dimension | Vessel (Trusted Control Plane) | The Tomb (Untrusted Execution Plane) |
| :--- | :--- | :--- |
| Secrets | Uses secrets for control-plane operations with redaction discipline. | Narrow queue-only SAQ/Postgres execution credential for execution-plane claim/ack/retry bookkeeping; no provider keys, Codex secrets, or control-plane credentials. |
| Mounts | Control-plane mount set. | Workspace-scoped mounts; optional read-only/sanitized Codex projection only. |
| Network | Internal services and allow-listed provider routes. | Tomb loop may use controlled queue/proxy connectivity; sandboxed `nono` execution has zero network. |
| Queue Ownership | Owns control-plane enqueue policy, durable rehydration, and promotion decisions. | Claims, acks, and retries execution-plane SAQ jobs only; no authority over control-plane queues. |
| Authority Boundaries | Decides dispatch and promotion. | Returns artifacts only; cannot commit durable state. |

### Consequences

!!! success "Positive"
    - **Extension Assimilation:** The unbound routing system allows coupled organs to be cleanly assimilated at runtime without a global `app` object.
    - **Physical Performance:** The integration of `msgspec` and binary transmutation hooks ensures the system remains responsive even when processing megabytes of cognitive trace data.
    - **Startup Velocity:** Lazy-loading heavy plugins ensures the CLI remains usable for rapid infrastructure tasks.

!!! failure "Negative"
    - **Learning Curve:** The focus on class-based controllers and DTOs represents a paradigm shift for developers accustomed to simpler micro-frameworks.
    - **Ecosystem Scale:** While growing, the community is smaller than its competitors, requiring more reliance on the framework's internal plugin suite.
