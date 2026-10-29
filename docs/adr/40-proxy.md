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

Veil runs as a separately managed service, forwarding admitted routes over the local service
network to Vessel or another explicitly named backend. Validated Runes define ports, domains,
certificate issuer, backend identity, and transport policy. Port `80` may handle ACME challenge
or redirect, and port `443` admitted TLS, with collisions detected at binding. Internal or
offline deployments may use operator-provided certificates or a separately accepted internal issuer.

If Veil is projected through Quadlet, its future Rune may embed the code-level `QuadletConfig`
value under `quadlet`. Veil remains the Domain identity and owns its ingress fields and compiler;
it is not another Stone, Animator, or opening for raw Quadlet/systemd text.

## Gateway placement

Veil may share the Core host or manifest on an optional separate
[Gateway Host](../sepulcher/gateway.md). The Gateway is a deployment trust role rather than another
Extension Domain or Composition. **Home** places it on operator-controlled local iron and forwards
only to an exact private Core backend. **Remote** places it off-site and may use one Tether peer and
route to that same narrow backend. RPi and VPS are substrate and placement choices, not
architectural identities.

Both placements compile the same typed route contract and keep the same application authority
behind it. The Gateway receives only edge certificates, route material, one backend service
credential, optional tunnel material, and bounded transport evidence. Its firewall denies general
LAN and arbitrary egress only as defense in depth. Policy outside that host—a router/firewall,
L3-switch ACL, or cloud-network rule—plus the receiving Core firewall enforces the public listener
and exact declared Gateway identity and backend flow. It does not trust the Gateway host to preserve
its own rules. Same-host, Home, and Remote are selected by exact deployment profiles, never an
`ingress`, `gateway`, `rpi`, or `vps` toggle.

TLS termination gives Veil custody of the admitted route's plaintext, including headers and
credentials carried inside that transport. A second encrypted hop to Core does not remove that
custody. The route contract therefore binds permitted content classes, the authentication proof
visible at the edge, request/response logging and retention, and compromise consequences. A
Gateway forbidden private Context cannot terminate a route carrying it: that route stays closed
unless a separately accepted protocol keeps the protected payload and reusable application
authority encrypted end to end to Core. Edge signatures alone cannot independently authenticate
an end user after that edge is compromised.

## Reach deployment edges

The [Reach deployment matrix](../compositions/reach/deployments/index.md) selects exact routes, not
an `ingress` toggle. Home-only and standalone outbound VPS have no inbound application listener and
therefore no Veil. `reach.edge-home.public@1` binds a private home Veil only to its Tether address
and routes exact event-admission, delivery-claim, settlement, and unauthoritative-health operations
to an isolated edge adapter. It never exposes a public listener. A later callback-only profile may
route an authenticated update only to isolated Intercom ingress for one existing outbound task.
A full A2A server is a separate profile with its own Ward, inbox/outbox, Workers, quotas, and
result route.

The Reach VPS Discord edge is a platform adapter, not a Gateway Host merely because it is remote;
that profile's Veil remains the private home ingress named above.

Neither profile may forward hostile bytes directly to the Reach core, Discord edge, or outbound
credential gate. Every route names its methods, media types, compressed and expanded body limits,
time/stream ceilings, backend, exposure tier, authentication precondition, and adapter revision; a
wildcard path is forbidden. Veil receives edge certificates and routing material only, never bot,
provider, A2A application, corpus-write, database, or delivery authority.

## Compile the admitted ingress routes {#compiled-ingress-not-shared-text}

Core and extensions contribute typed route intent: host/route match, backend service and port,
protocol/streaming behaviour, body/timeout/header limits, application-authentication preconditions,
and permitted public, Tether, or local exposure tier. The compiler rejects ambiguous ownership,
overlapping exclusive routes, unknown backends, unbounded raw directives, and ports outside the
admitted service topology. It renders complete Caddy configuration in staging, validates it, then
inscribes transactionally. The Scribe owns the generated projection; contributions remain separate
and attributable.

## Caller authority at the backend {#transport-is-never-application-authority}

Transport establishes an endpoint and protects bytes through TLS; routing selects a backend.
Caller authentication and effect permission remain with Ward and Vessel, which enforce Sigils,
Grants, consent, and rate policy. A2A keeps its own authentication and replay defence. Tether,
mTLS, forwarded metadata, Nostr, or another signature scheme may contribute evidence only under
its owner's authentication decision. None can mint a Sigil or administrator.

Veil may impose coarse connection, header, and traffic limits. It is neither full DDoS defence nor
application validation, and receives only a narrow path to registered HTTP backends—not database,
model, Reactor, systemd, container, application-secret, or arbitrary-egress authority.

## Certificate failure and delivery

Certificate state belongs in declared durable storage and account keys in declared secret
boundaries. Validate before every configuration/certificate activation; rollback restores the prior
generated projection. Renewal failure preserves the last valid configuration and degrades
readiness before expiry. Public ACME also needs a resolvable domain and reachable challenge path
or configured DNS provider. Without them, the public entrance stays unavailable while the local
Vessel continues. Reconciliation closes removed routes.

This Covenant is **Designed**. No proxy provider, public listener, certificate lifecycle, edge
compiler, hardening, or trusted-proxy policy ships. Generated deployment is IPv4-loopback-only and
the browser boundary is unsafe to publish: no ad hoc reverse proxy, tunnel, or port-forward may
stand in for the missing contract. [State of Work](../state-of-the-work.md#proxy-veil) owns the
delivery boundary.

Operating Veil adds certificate, DNS, firewall, abuse, and availability duties alongside its
dedicated remote-transport role. A loopback-only deployment avoids those duties.
