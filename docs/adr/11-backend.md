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

`src/lychd/app.py:create_app()` is the production Vessel composition root. It creates one Litestar
application with `AppInit`; imports and route declarations do not mutate a pre-existing app.
Core controllers and the compiled Altar fallback are collected there. Extensions are selected
explicitly, receive a host-created context, and contribute shaped records rather than arbitrary
route or middleware mutation. There is no delivered extension route bundle.

The host Click CLI works without constructing an application graph. Help, `init`, `bind`,
lifecycle commands, and ordinary operator commands do not build the ASGI application. The
`database` command delegates lazily to Litestar, while the managed image owns application startup.

### Process and listener boundary

The runtime is one Granian/Litestar process and one event loop. A shared launcher explicitly owns
the application's lifespan around an embedded Granian no-lifespan ASGI worker. Required startup
or closure failure and unexpected HTTP-worker termination propagate as process failure. The HTTP
worker and every admitted Python ASGI callback, including post-response background work, must
retire before application services close; successful process exit cannot conceal a
failed application shutdown. Signals request ordinary worker retirement and do not certify its
completion. The user manager retains its outer stop-timeout and forced-stop semantics.

The managed Vessel image selects its fixed internal `0.0.0.0:8000` listener behind generated
loopback-only host publication. There is no host-native Vessel launcher, alternative native bind
generation or host Core test deployment. The image entrypoint and `create_app()` preserve the
single-process/no-reload policy and reject unsupported upstream supervisor or alternate-listener
configuration. Existing images must be rebuilt to acquire changed runtime behavior.

The read-only developer fixture also runs in the explicit container test/development image,
with a fixed internal listener and loopback-only host publication. Its test records and security
remain separate from production authority. Direct application construction inside an OCI test
process is an in-process test technique, not another deployment profile.

The old native-only signed-stop profile is removed. Container startup and shutdown still own the
application lifespan and propagate failure; public active installation-stop completion remains
unavailable until its own authenticated container lifecycle is implemented and qualified.

The run-event bus, cancellation coordinator, services, and SAQ workers are process-local. This is a correctness boundary, not a
scalability claim or permission to use another launcher.

### Outbound HTTP clients

Core-owned general-purpose HTTP clients and operator scripts use HTTPX2. Clients, transports,
request/response objects and caught exceptions stay in the same library family. Preserve each
adapter's destination and credential binding, disabled ambient proxies and redirects, bounded
I/O, retry policy and cancellation/uncertain-outcome semantics. Construct owned async clients
and network transports through `lychd.lib.http`, including implementations in native extensions,
Composition adapters, and operator scripts. Its explicit factories disable ambient configuration
and redirects, retain zero automatic connection retries, and require the caller's timeout.
Pool limits, base URL, headers, request hooks, and injected transports remain explicit inputs;
each adapter owns its client's lifetime. A supplied custom transport retains responsibility for
its wire behavior and admission; client-level options cannot secure a transport that ignores them.
The shared mechanism supports HTTP and HTTPS without granting destination or disclosure authority.
Network-owning clients and transports receive an explicit verified TLS context, loaded from the
maintained certifi bundle. Ambient CA and TLS key-log environment variables cannot change that
context. This retains the migrated clients' public-root trust without inheriting HTTPX2's
system-store environment behavior; the model factory uses the same policy. Candidate images
must retain the declared CA dependency and certificate verification.

Factories return native HTTPX2 objects: this is one construction policy, not a dependency-neutral
HTTP protocol. Protocol adapters retain response decoding, streaming, error translation, effect
fences and uncertain-outcome semantics. The existing JSON helper keeps its control-plane-specific
normalization; it is not a universal response contract. Application and domain consumers depend
on typed operations such as transcription or message delivery rather than arbitrary HTTP sends.

Legacy HTTPX remains a testing dependency for Litestar's test clients and RESPX mock values.
Litestar also requires it transitively in the production dependency graph; its presence does
not authorize new Core-owned uses. HTTPX2 test interception crosses the HTTPCore2 boundary
without changing process-wide imports. Protocol-specific transports retain their own authority
contracts rather than inheriting permissions from the HTTP client.

## Lifespan and ownership

Production initialization creates the typed Settings generation, selected extension assembly, and
validated Rune registry; installs routes, middleware, framework plugins, and dependency providers;
then enters its lifespan. Startup crosses these boundaries in order:

1. Wait for the Host Reactor fence and connect both queues.
2. Build durable dependencies and services; hydrate runtime registry material off the event loop,
   then obtain any missing initial capability observations before recovery. Metadata-only binding
   does not satisfy readiness; an existing observation is not automatically replaced or made WARM.
3. Recover durable authority, including preauthorization policy, cancellation, terminal evidence
   and checkpoints, orphaned Runs, consent, delegated waits, and pending delivery.
4. Start the maintenance relays, then publish the shared run substrate and `app.state.services`.

Durable startup must recover PostgreSQL authority before admitting work. A failed or degraded
required reconciliation aborts startup before workers can claim work or HTTP can resolve services.
The memory profile permits best-effort reconciliation because it has no cross-process state to
recover; that exception does not weaken durable startup. [Workers (14)](14-workers.md) owns the
exact recovery order and settlement law.

Any failed startup follows the same reverse order as shutdown: stop in-process workers, withdraw
the run substrate, close services, then disconnect queues. A collaborator therefore cannot outlive
what it reads. The application-owned queue plugin constructs both workers without the unused
batched heartbeat thread; Run invocations retain their own broker heartbeat. The required Altar
lifespan is the sole worker retirement owner; the queue plugin registers startup only.
There is no hot-reload contract.

### Isolated developer fixture (Designed)

One explicit developer entry may compose a disposable, read-only fixture for local browser work.
Production remains the default. The fixture is selected before ambient Settings sources, Rune or
extension discovery, or database and SAQ construction can run. It receives explicit Settings,
fresh fixture-only credentials, and empty Rune and extension assemblies; it reads no operator
configuration, secrets, or runtime control files.

The fixture shares the real controllers, dependency providers, OpenAPI, authentication, Host,
CORS, Origin, and CSRF boundaries. An additional admission guard refuses every unsafe HTTP
method before controller or domain admission, including unversioned routes. Valid credentials
do not permit fixture mutations. Reads remain free of execution and host effects. The common
pure server policy still requires one process, one event loop, and the fixed internal
`0.0.0.0:8000` TCP listener behind loopback-only host publication,
refusing reload, extra workers, alternate sockets, and a separate metrics listener. This fixture
grants no VPN, tunnel, or remote access.

Existing memory repositories retain one visibly labelled synthetic conversation and terminal
Run. Bridge and Orb project that same Run and link its exact registered Pattern revision into
Loom. Its terminal status is sample data, never evidence of graph, model, or host execution.
The real service graph receives a refusing implementation through the existing `RuntimeActuator`
port at construction; its queue collaborators also refuse execution. No model or delegated
runtime is registered, and omitted queue or runtime authority is reported unavailable.

A dedicated lifespan owns construction, warming the empty registry, seeding, publication, and
closure. It publishes services only after the fixture is whole, withdraws any publication on exit,
and closes constructed collaborators on shutdown or failed startup. It performs no Host Reactor
admission or durable recovery, connects no queues, and starts no workers or maintenance relays.
All fixture state ends with the process; durable operation retains the production startup and
recovery contract above.

This option admits a development composition, not a deployed Phylactery or production macOS
support. [State of Work](../state-of-the-work.md#current-evidence-envelope) owns its delivery and
receipt boundary; [CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#browser-development-and-its-backend)
owns the startup and browser workflow when supplied. This design alone establishes neither.

### Where implementation belongs

`lychd.lib` owns named, reusable mechanisms shared by Core, native extensions, and Composition
implementations. Extract a mechanism when concrete consumers establish its common contract;
grow that contract from observed needs. Keep its policy-independent plumbing separate from
application decisions, credentials, effect authority, and lifecycle ownership. A shared helper
creates neither a new service container nor a versioned extension SDK promise.

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

The public API is defined by versioned Pydantic or dataclass DTOs and named operations. A true
CRUD projection may use an explicitly bounded `SQLAlchemyDTO`, but its ORM shape must never become
the API accidentally. Includes, exclusions, aliases, nested depth, input rules, SSE envelopes,
and compatibility all belong to tested interface contracts.

Litestar owns typed HTTP/OpenAPI and JSON serialization. Runtime and offline export share one
JSON-only OpenAPI configuration. Controller validation and mapped application/repository failures
retain Litestar's declared JSON shapes rather than an undeclared Problem Details transform;
boundary middleware may still return its own non-API rejection. The static server delivers
compiled Svelte assets, not browser state or templates. Mermaid is sent as inert source for
client-side rendering. Structlog is present instrumentation; an uninstalled OpenTelemetry exporter
does not establish external tracing.

### Captured credentials and database wire values

The production process owns one async SQLAlchemy engine/session factory. Connection and signing secrets load
once with Settings as excluded `SecretStr` fields; consuming components read the captured values
without reopening environment variables or files. [Configuration (12)](12-configuration.md)
owns precedence, explicit reload, and secret-free serialization.
The asyncpg hook registers separate binary codecs: JSONB adds and removes PostgreSQL's version
byte, while plain `json` passes its unversioned bytes directly. Focused hook tests pin both wire
shapes; this is a correctness contract, not a throughput claim.

## Trust boundary and evidence

The Vessel is the trusted control plane: HTTP admission, orchestration, persistence access,
runtime projection, and its static client. Its default browser seam admits literal loopback Host
authorities on the configured external port and detected listener port, same-origin requests, and
only explicitly configured loopback CORS origins. Protected requests additionally require the
dedicated local possession credential before receiving the fixed bootstrap Sigil; Host and CORS
checks alone provide no authentication. This local gate supplies no remote person identity.
Wider browser controls and queue/execution isolation belong to
[Security (09)](09-security.md). Tomb is a designed, not delivered, execution plane; there is no
Tomb queue, executor, credential, mount, sandbox, or promotion authority here. Its delivery
boundary is maintained by [State of Work](../state-of-the-work.md#tomb-untrusted-execution).

Focused tests cover memory-profile composition and web contracts. An HTTP assembly fixture
uses the real factory and security configuration with memory services, without entering lifespan;
it proves Host, credential, CORS, Origin, and CSRF admission, not startup. A disposable two-boot receipt
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
