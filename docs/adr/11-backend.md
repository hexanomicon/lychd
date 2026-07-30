---
title: 11. Backend
icon: material/star-shooting-outline
---

# :material-star-shooting-outline: 11. Backend

!!! abstract "Context and decision"
    The Vessel is one explicitly composed Litestar application. Its HTTP, persistence, extension,
    and worker collaborators are assembled once, published only when whole, and retired in reverse
    dependency order.

## Decision

`src/lychd/app.py:create_app()` is the Vessel composition root. It creates one Litestar
application with `AppInit`; imports and route declarations do not mutate a pre-existing app.
Core controllers and the compiled Altar fallback are collected there. Extensions are selected
explicitly, receive a host-created context, and contribute shaped records rather than arbitrary
route or middleware mutation. There is no delivered extension route bundle.

The native Click CLI remains useful without an application graph. `serve` and `database` delegate
lazily to Litestar; help, `init`, `bind`, lifecycle commands, and ordinary operator commands do
not construct the ASGI application.

The runtime is one Granian/Litestar process and one event loop. `GRANIAN_WORKERS` other than one,
multiple worker requests, and reload supervision are refused because the run-event bus,
cancellation coordinator, services, and SAQ workers are process-local. This is a correctness
boundary, not a scalability claim.

## Lifespan and ownership

Application initialization creates the typed Settings generation, selected extension assembly, and
validated Rune registry; installs routes, middleware, framework plugins, and dependency providers;
then enters its lifespan. Lifespan waits for the Host Reactor fence, connects both queues, builds
durable dependencies and services, loads runtime registry material off the event loop, publishes
the shared run substrate, and attempts preauthorization and orphan/consent reconciliation.
`app.state.services` is published only after required construction succeeds. Reconciliation may
log a failure and continue; required setup cannot.

Any failed startup follows the same reverse order as shutdown: stop in-process workers, withdraw
the run substrate, close services, then disconnect queues. A collaborator therefore cannot outlive
what it reads. There is no hot-reload contract.

The application layer owns HTTP admission and dependency wiring. Domain code speaks ports,
repositories, and services; persistence adapters own SQLAlchemy sessions and explicit statements
needed for locking or aggregate transitions. Controllers never issue database queries directly.
The system layer owns host adapters and lifecycle effects. [Persistence (06)](06-persistence.md),
[Configuration (12)](12-configuration.md), and [Security (09)](09-security.md) retain their
respective transaction, configuration, and trust laws.

## Interfaces rather than rows

Public endpoints use versioned Pydantic or dataclass DTOs and named operations. An explicitly
bounded `SQLAlchemyDTO` is permitted for a true CRUD projection, but ORM shape never becomes the
public API by accident. Includes, exclusions, aliases, nested depth, input rules, SSE envelopes,
and compatibility are interface contracts with tests.

Litestar owns typed HTTP/OpenAPI and JSON serialization; the static server delivers compiled
Svelte assets, not browser state or templates. Mermaid is sent as inert source for client-side
rendering. Structlog is present instrumentation; an uninstalled OpenTelemetry exporter does not
establish external tracing.

The process owns one async SQLAlchemy engine/session factory. Connection and signing secrets are
resolved only by their consuming component; Settings retain references, never secret contents.
The current asyncpg binary codec is valid for JSONB. It also frames plain `json` as JSONB, which is
a known defect until separate codecs are proved against PostgreSQL. This ADR requires correctness
tests, not a throughput claim.

## Trust boundary and evidence

The Vessel is the trusted control plane: HTTP admission, orchestration, persistence access,
runtime projection, and its static client. Hostile-browser controls and queue/execution isolation
belong to [Security (09)](09-security.md). Tomb is a designed, not delivered, execution plane;
there is no Tomb queue, executor, credential, mount, sandbox, or promotion authority here. Its
delivery boundary is maintained by [State of Work](../state-of-the-work.md#tomb-untrusted-execution).

Focused tests cover memory-profile composition and web contracts. The real application-factory
plus PostgreSQL lifecycle test is still skipped, and asyncpg codec installation lacks direct
integration coverage. [State of Work](../state-of-the-work.md#current-evidence-envelope) owns the
evidence envelope.

## Consequences

- Framework upgrades must reprove initialization, dependency injection, serialization, OpenAPI,
  and ordered shutdown.
- Current streaming and cancellation semantics require one process. A multi-process Vessel needs
  durable event and ownership protocols, not a changed worker count.
- Explicit DTOs may deliberately duplicate stable storage facts; migrations do not thereby set
  the HTTP compatibility contract.
