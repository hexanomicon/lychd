---
title: 10. Litestar Framework
icon: material/star-shooting-outline
---

# :material-star-shooting-outline: 10. Litestar Web Framework

!!! abstract "Context and Problem Statement"
    The LychD "Vessel" requires a modern, async-first Python web framework. The framework must not only be performant but must also actively reduce boilerplate, scale cleanly from a small service to a large application, and offer a cohesive ecosystem for common web development needs.

## Decision Drivers

- **Architectural Scalability:** The framework must provide natural patterns for organizing a growing codebase without introducing awkward workarounds for issues like circular imports.
- **Persistence Layer Efficiency:** The framework must provide a first-class integration with SQLAlchemy that minimizes code duplication between database models (the source of truth) and API data transfer objects (DTOs).
- **Integrated Tooling:** The framework should offer well-maintained, first-party plugins for essential concerns like structured logging, asset bundling, and ORM integration.

## Considered Options

!!! failure "Option 1: Django"
    A mature, feature-rich framework.

    - **Pros:** Powerful and well-known.
    - **Cons:** Not async-first, and its monolithic structure is unsuitable for LychD's more focused, service-oriented design.

!!! failure "Option 2: FastAPI"
    A popular, high-performance framework.

    - **Pros:** Fast and widely adopted.
    - **Cons:** Its design presents two significant drawbacks for this project:
        - **Bound Route Decorators:** Tying route decorators to the application instance (`@app.get`) complicates multi-file application structure.
        - **Pydantic-Only Serialization:** Requires manual definition of Pydantic models for API schemas, leading to a violation of the DRY principle by duplicating field definitions already present in SQLAlchemy models.

!!! success "Option 3: Litestar"
    A modern framework focused on performance and architectural quality.

    - **Pros:** Directly addresses the shortcomings of other frameworks with a superior design.
        - **Standalone Route Decorators:** Decoupling decorators from the application instance enables a clean, composable `Router` system.
        - **Automated DTO Generation:** Provides `SQLAlchemyDTO` helpers that automatically derive Pydantic-compatible DTOs from SQLAlchemy models.
        - **Rich Plugin Ecosystem:** Offers high-quality, first-party plugins for SQLAlchemy (`Advanced Alchemy`), `structlog`, and frontend tooling like Vite.

## Decision Outcome

We will adopt **Litestar** due to its superior architectural design and focus on developer efficiency.

Its automated DTO generation via `SQLAlchemyDTO` is a decisive feature that directly solves the most common source of boilerplate in database-backed APIs. Furthermore, its well-designed router composition and first-party plugin ecosystem (especially `Advanced Alchemy` for repositories and `structlog` for logging) provide the robust foundation needed for the LychD project.

## Consequences

!!! success "Positive"
    - **Scalability:** The codebase will be more scalable and maintainable.
    - **Velocity:** Development will be faster and less error-prone due to the drastic reduction in boilerplate code.
    - **Cohesion:** We gain a cohesive, well-integrated toolchain for logging, persistence, and other common concerns, directly from the framework's ecosystem.

!!! failure "Negative"
    - **Community Size:** Litestar has a smaller community than FastAPI. This is an acceptable trade-off for its superior engineering and architectural alignment with our project goals.
