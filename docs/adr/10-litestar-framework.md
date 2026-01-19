---
title: 10. Litestar Framework
icon: material/star-shooting-outline
---

# :material-star-shooting-outline: 10. Litestar Web Framework

!!! abstract "Context and Problem Statement"
    The LychD "Vessel" requires a modern, async-first Python web framework to serve as the application's backbone. The framework selection is critical, as it dictates the architectural patterns for the entire project.

    Common frameworks often enforce patterns that lead to code duplication (manual DTO definition) or structural rigidity (circular imports with bound decorators). A solution is required that inherently reduces boilerplate, facilitates modular architecture, and scales cleanly from a prototype to a production system.

## Decision Drivers

- **Architectural Scalability:** The framework must support a decoupled router system that allows for modular file organization without introducing circular dependency issues.
- **Persistence Efficiency (DRY):** The framework must offer mechanisms to minimize code duplication between database models (the source of truth) and API schemas (DTOs).
- **Integrated Tooling:** The framework should provide a cohesive, maintained ecosystem of plugins for essential cross-cutting concerns (logging, ORM integration, asset bundling) rather than relying entirely on disparate third-party libraries.
- **Performance:** The solution must be built on modern ASGI standards and support high-throughput asynchronous execution.

## Considered Options

!!! failure "Option 1: Django"
    A mature, "batteries-included" monolithic framework.

    - **Pros:** Extremely feature-rich with a vast ecosystem.
    - **Cons:** Historically synchronous design requires adapters for async code. The monolithic architecture imposes a heaviness unsuitable for the project's lean, service-oriented design goals.

!!! failure "Option 2: FastAPI"
    A popular, high-performance micro-framework.

    - **Pros:** Excellent performance and massive adoption.
    - **Cons:** **Architectural Friction.**
        - **Bound Route Decorators:** Tying decorators to the application instance (`@app.get`) complicates modular application structure.
        - **Manual DTOs:** Relying solely on Pydantic models requires manual re-definition of fields already present in the database models, violating the DRY principle and increasing maintenance burden.

!!! success "Option 3: Litestar"
    A modern, opinionated framework prioritized around architectural patterns and developer ergonomics.

    - **Pros:** Directly addresses the specific friction points of other options:
        - **Unbound Decorators:** Enables a clean, composable `Router` system independent of the app instance.
        - **Automated DTOs:** The `SQLAlchemyDTO` utility automatically derives API schemas from database models, eliminating significant boilerplate.
        - **First-Party Ecosystem:** Includes high-quality integrations for SQLAlchemy (`Advanced Alchemy`), `structlog`, and frontend tooling.

## Decision Outcome

**Litestar** is adopted as the foundational web framework.

The selection is driven primarily by its superior handling of data transfer objects (DTOs) and its modular routing architecture. The ability to automatically generate API schemas from SQLAlchemy models via `SQLAlchemyDTO` removes the single largest source of boilerplate in Python API development. Furthermore, the `Advanced Alchemy` extension provides a robust repository pattern implementation out of the box.

## Consequences

!!! success "Positive"
    - **Codebase Maintainability:** The decoupled routing architecture prevents circular imports and encourages a clean separation of concerns.
    - **Development Velocity:** Automated DTO generation drastically reduces the amount of code required to expose a database model as an API endpoint, minimizing the surface area for bugs.
    - **Cohesive Ecosystem:** Reliance on first-party plugins for logging and database integration ensures these critical components are version-compatible and maintained alongside the core framework.

!!! failure "Negative"
    - **Niche Adoption:** Litestar has a significantly smaller community and ecosystem compared to FastAPI or Django. Finding solutions to edge-case problems may require deeper investigation.
