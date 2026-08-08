---
title: Veil
icon: material/shield-key-outline
---

# :material-shield-key-outline: The Veil

A request arrives with `Host`, path, method, headers, and claims about its origin. The edge must
reject, canonicalize, or map those values before they reach an application. **Veil** is the optional
hostile-ingress Extension Domain outside the Vessel: it terminates TLS, handles protocols, admits
routes, and sends canonical metadata to an independently guarded backend.

Veil is **Designed**; [State of Work](../../state-of-the-work.md#proxy-veil) owns its delivery
boundary. Until the [local browser boundary](../../state-of-the-work.md#local-browser-bind-boundary)
changes, keep the Vessel and Altar on the same host—without an ad hoc reverse proxy, tunnel, or
port-forward.

## Admit the edge

[ADR 40](../../adr/40-proxy.md) selects Caddy as the default managed engine. An external edge
remains possible, but no compatibility profile ships.

Remote exposure is opt-in per route. Typed Runes name the host or route, backend, protocols,
limits, application-authentication preconditions, and exposure tier: public, through
[Tether](tether.md), or local. Everything else stays closed. The design rejects ambiguous or
overlapping ownership, unknown backends, non-admitted ports, and raw directives. Contributions
cannot shadow Core, remove authentication, expose a database or model API, select an arbitrary
upstream, or create a forward proxy. The complete configuration retains attribution and passes
Caddy validation in staging before transactional inscription.

Caller-supplied forwarding, identity, and client-certificate claims are discarded. Canonical
scheme, host, origin, and peer metadata may cross only an authenticated backend path the Vessel
explicitly trusts. That is designed behavior, not today's loopback service.

## Keep authority behind the route

TLS authenticates an endpoint and protects bytes; routing selects a destination. The [Ward](ward.md)
and Vessel still authenticate the caller and authorize the exact object and effect. mTLS, arrival
through Tether, or forwarded metadata may supply evidence, but cannot mint a Sigil, create an
administrator, or make the fixed bootstrap `magus:*` identity valid remotely.

An A2A Agent Card, Scroll, or teaching bundle remains application material after crossing Veil.
Veil may expose the admitted Intercom route locally, through Tether, or eventually publicly; it
cannot validate Spell compatibility, approve teaching, admit a casting, or settle its Run.

Before a browser-facing listener opens, Host and Origin admission, DNS-rebinding defenses, secure
sessions, local assets, request bounds, and protected diagnostics must pass hostile tests.
[State of Work](../../state-of-the-work.md#local-browser-bind-boundary) records the present
failures; [Security](../../adr/09-security.md) owns the deeper boundary. Proxying and TLS leave
those duties intact.

Veil may impose coarse traffic limits; egress, application validation, and complete DDoS defense
remain elsewhere. The edge receives only a narrow path to registered HTTP backends, never database,
model, Reactor, systemd, container, application-secret, or arbitrary-egress authority.

## Fail without opening another path

The design detects listener and route collisions before change. Certificate state and account keys
stay within declared durable and secret boundaries. Each transition validates before activation
and retains the prior projection for restoration. Renewal failure preserves the last valid
configuration while readiness degrades before expiry. If ACME prerequisites fail, the public Veil
stays unavailable while the local Vessel continues. Reconciliation closes removed routes.
