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

The runtime is one Granian/Litestar process and one event loop. The native launcher rejects
multi-worker and reload configuration. The launcher and `create_app()` call one pure server policy
which rejects server-visible worker/reload variables and detectable direct Litestar/Granian
arguments. Listener authority resolves explicit `--port`, then `LITESTAR_PORT`, `GRANIAN_PORT`,
and the configured server port; the native launcher publishes that result before Litestar loads
the application, and Host admission consumes the same value. The run-event bus, cancellation
coordinator, services, and SAQ workers are process-local. This is a correctness boundary, not a
scalability claim or permission to use another launcher.

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
The Nexus controller uses a profile-bound request-admission port before it creates a physical
transition task; PostgreSQL owns the cross-process uniqueness transaction while the controller
retains only short-lived ticket projection.
The system layer owns host adapters and lifecycle effects. [Persistence (06)](06-persistence.md),
[Configuration (12)](12-configuration.md), and [Security (09)](09-security.md) retain their
respective transaction, configuration, and trust laws.

## Interfaces rather than rows

Public endpoints use versioned Pydantic or dataclass DTOs and named operations. An explicitly
bounded `SQLAlchemyDTO` is permitted for a true CRUD projection, but ORM shape never becomes the
public API by accident. Includes, exclusions, aliases, nested depth, input rules, SSE envelopes,
and compatibility are interface contracts with tests.

Litestar owns typed HTTP/OpenAPI and JSON serialization. Runtime and offline export share one
JSON-only OpenAPI configuration. Controller validation and mapped application/repository failures
retain Litestar's declared JSON shapes rather than an undeclared Problem Details transform;
boundary middleware may still return its own non-API rejection. The static server delivers
compiled Svelte assets, not browser state or templates. Mermaid is sent as inert source for
client-side rendering. Structlog is present instrumentation; an uninstalled OpenTelemetry exporter
does not establish external tracing.

The process owns one async SQLAlchemy engine/session factory. Connection and signing secrets are
resolved only by their consuming component; Settings retain references, never secret contents.
The asyncpg hook registers separate binary codecs: JSONB adds and removes PostgreSQL's version
byte, while plain `json` passes its unversioned bytes directly. Focused hook tests pin both wire
shapes; this is a correctness contract, not a throughput claim.

## Trust boundary and evidence

The Vessel is the trusted control plane: HTTP admission, orchestration, persistence access,
runtime projection, and its static client. Its default browser seam admits literal loopback Host
authorities on the configured external port and detected listener port, same-origin requests, and
only explicitly configured loopback CORS origins. This does not authenticate the fixed bootstrap
Sigil. Wider browser controls and queue/execution isolation belong to
[Security (09)](09-security.md). Tomb is a designed, not delivered, execution plane; there is no
Tomb queue, executor, credential, mount, sandbox, or promotion authority here. Its delivery
boundary is maintained by [State of Work](../state-of-the-work.md#tomb-untrusted-execution).

Focused tests cover memory-profile composition and web contracts. A disposable two-boot receipt
exercises the real application factory, PostgreSQL, in-process SAQ, and asyncpg installation with an
offline model and HTTP test client; a focused disposable receipt round-trips both plain `json` and
JSONB through the same engine factory. Neither proves a real browser, inference engine, or deployed
host. [State of
Work](../state-of-the-work.md#current-evidence-envelope) owns the evidence envelope.

## Consequences

- Framework upgrades must reprove initialization, dependency injection, serialization, OpenAPI,
  and ordered shutdown.
- Current streaming and cancellation semantics require one process. A multi-process Vessel needs
  durable event and ownership protocols, not a changed worker count.
- Explicit DTOs may deliberately duplicate stable storage facts; migrations do not thereby set
  the HTTP compatibility contract.
