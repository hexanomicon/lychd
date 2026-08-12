---
title: 40. Proxy
icon: material/key-chain
---

# :material-key-chain: 40. Proxy

!!! abstract "Context"
    A remote entrance needs TLS, protocol handling, route composition, and certificate lifecycle
    outside the Vessel. It must not become a second authority plane or let one extension rewrite
    another's edge policy.

## Decision

**Caddy** is the default engine of the optional **Veil** extension. Without admitted remote ingress
the Vessel remains at its local boundary; enabling Veil makes no route public by implication.

Veil is a separately managed service forwarding admitted routes to the Vessel or another explicitly
named backend over the local service network. Validated Runes own ports, domains, certificate
issuer, backend identity, and transport policy. Port `80` may handle ACME challenge/redirect and
port `443` admitted TLS; binding detects collisions. Internal or offline deployments may use an
operator-provided certificate or separately accepted internal issuer.

If Veil is projected through Quadlet, its future Rune may embed the code-level `QuadletConfig`
value under `quadlet`. Veil remains the Domain identity and owns its ingress fields and compiler;
it is not another Stone, Animator, or opening for raw Quadlet/systemd text.

## Reach deployment edges

The [Reach deployment matrix](../compositions/reach/deployments/index.md) selects exact routes, not
an `ingress` toggle. Home-only and standalone outbound VPS have no inbound application listener and
therefore no Veil. `reach.edge-home.public@1` binds a private home Veil only to its Tether address
and routes exact event-admission, delivery-claim, settlement, and unauthoritative-health operations
to an isolated edge adapter. It never exposes a public listener. A later callback-only profile may
route an authenticated update only to isolated Intercom ingress for one existing outbound task.
A full A2A server is a separate profile with its own Ward, inbox/outbox, Workers, quotas, and
result route.

Neither profile may forward hostile bytes directly to the Reach core, Discord edge, or outbound
credential gate. Every route names its methods, media types, compressed and expanded body limits,
time/stream ceilings, backend, exposure tier, authentication precondition, and adapter revision; a
wildcard path is forbidden. Veil receives edge certificates and routing material only, never bot,
provider, A2A application, corpus-write, database, or delivery authority.

## Compiled ingress, not shared text

Core and extensions contribute typed route intent: host/route match, backend service and port,
protocol/streaming behaviour, body/timeout/header limits, application-authentication preconditions,
and permitted public, Tether, or local exposure tier. The compiler rejects ambiguous ownership,
overlapping exclusive routes, unknown backends, unbounded raw directives, and ports outside the
admitted service topology. It renders complete Caddy configuration in staging, validates it, then
inscribes transactionally. The Scribe owns the generated projection; contributions remain separate
and attributable.

## Transport is never application authority

TLS authenticates the configured endpoint and protects bytes; path routing chooses a backend.
Neither identifies a caller or permits an effect. Ward and Vessel authenticate callers and enforce
Sigils, Grants, consent, and rate policy. A2A retains its own authentication and replay defence.
Arrival through Tether, mTLS, forwarded metadata, Nostr, or another signature scheme may contribute
evidence only under its owning authentication decision; none can mint a Sigil or administrator.

Veil may impose coarse connection, header, and traffic limits. It is neither full DDoS defence nor
application validation, and receives only a narrow path to registered HTTP backends—not database,
model, Reactor, systemd, container, application-secret, or arbitrary-egress authority.

## Certificate failure and delivery

Certificate state and account keys live in declared durable and secret boundaries. Validation
precedes every configuration/certificate activation; rollback restores the prior generated
projection. Renewal failure preserves the last valid configuration and degrades readiness before
expiry. A public ACME Veil needs a resolvable domain plus reachable challenge path or configured
DNS provider; without them the public entrance remains unavailable and the local Vessel continues.
Removed routes close during reconciliation.

This Covenant is **Designed**. No proxy provider, public listener, certificate lifecycle, edge
compiler, hardening, or trusted-proxy policy ships. Generated deployment is IPv4-loopback-only and
the browser boundary is unsafe to publish: no ad hoc reverse proxy, tunnel, or port-forward may
stand in for the missing contract. [State of Work](../state-of-the-work.md#proxy-veil) owns the
delivery boundary.

Veil gives remote transport a dedicated owner, while adding certificate, DNS, firewall, abuse, and
availability duties that do not exist on loopback.
