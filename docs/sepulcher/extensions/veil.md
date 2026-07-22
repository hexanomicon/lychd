---
title: Veil
icon: material/shield-key-outline
---

# :material-shield-key-outline: The Veil: Extension of the Threshold

**Purpose:** The Veil is LychD's hostile-network ingress jurisdiction. It is the outer threshold
that will terminate transport security, admit only declared routes, and carry a canonical request
to an independently guarded Vessel.

**Current boundary:** The `proxy` package contains no working organ and is absent from the built-in
catalog. LychD generates only loopback host publications; it has no Caddy unit, public listener,
certificate lifecycle, route compiler, trusted-proxy policy, hardened remote profile, or proxy
test. The current browser boundary is not safe to publish through somebody else's reverse proxy.
[State records that browser boundary](../../state-of-the-work.md#local-browser-bind-boundary) and
the [Veil boundary](../../state-of-the-work.md#proxy-veil).

**Law:** [ADR 40 — Proxy](../../adr/40-proxy.md), constrained by
[ADR 09 — Security](../../adr/09-security.md) and the future [Ward](./ward.md).

> _"The Sepulcher is a sanctuary of silence. At the edge of the Forest, the Veil must turn noise
> into one narrow passage—without mistaking a protected passage for a trusted voice."_

The Veil is a threshold, not a crown. TLS can protect bytes in flight and authenticate the server
named by a certificate. It does not decide which caller may read a session, approve a consent,
command an Animator, or enter the [Intercom](../../adr/26-a2a.md).

## I. The Woven Threshold

The mature Veil must own a small, engine-neutral ingress contract:

- **Listeners:** exact address family, host address, protocol, port, exposure class, owner, and
  prerequisites for every public socket.
- **Routes:** exact host, path, methods, owning extension, backend service identity,
  authentication requirement, request limits, and streaming or WebSocket behavior.
- **Transport profiles:** explicit public ACME, operator-supplied certificate, or private-CA
  policy, with secret references, renewal, expiry, restore, rotation, and fail-closed behavior.
- **Proxy trust:** strip caller-supplied forwarding, identity, client-certificate, and trace headers;
  generate canonical scheme, host, origin, and peer metadata only across an authenticated backend
  channel the Vessel is configured to trust.
- **Finite passage:** default-deny routes plus header, body, time, connection, concurrency, stream,
  and coarse rate limits. Resource-heavy admission still belongs to authenticated application
  policy.
- **Reweaving:** compile one provenance-bearing generation, validate it, probe it, activate it
  atomically, retain a known-good rollback, and close removed routes on reconciliation.

Caddy may embody this contract, but raw `.caddy` fragments are not an extension API. An extension
must never be able to shadow a core route, expose a database or model port, choose an arbitrary
upstream, remove authentication, or open a forward proxy by contributing text.

## II. What the Veil Does Not Own

The Veil is not an outbound egress policy, a caller registry, an authorization engine, or a promise
of volumetric DDoS absorption. It may reject malformed or excessive traffic early, but the
[Ward](./ward.md) must independently authenticate the caller and authorize the exact object and
effect inside the Vessel. A hidden path is not a protected object. mTLS is a credential signal,
not application permission.

!!! danger "TLS Is Not a Sigil"
    Pointing Caddy, Nginx, a tunnel, or a port forward at the current loopback Vessel does not add
    caller authentication. The backend still stamps ordinary requests with the fixed `magus:*`
    bootstrap Sigil. Do not publish the Altar or API through an external proxy.

## III. Gates Before the Veil Is Drawn

No external listener opens until all of these gates agree:

1. The full production application passes its hostile-browser and hostile-HTTP contract: exact
   Host and Origin policy, DNS-rebinding defense, local assets, secure cookies, public-route
   inventory, request limits, and protected or disabled diagnostic surfaces.
2. Credential-backed Ward authentication, object authorization, effect-time reauthorization,
   revocation, and audit are active behind the edge. Edge checks may only narrow that policy.
3. Core owns typed `IngressListener`, `IngressRoute`, `BackendService`, `TLSProfile`, and
   `TrustedProxyPolicy` schemas with provenance, collision checks, and a default-deny compiler.
4. The operator explicitly selects a host-owned external bind and firewall plan. Rootless low-port,
   IPv4, IPv6, existing-proxy, and high-port profiles are proved rather than assumed.
5. The gateway is isolated from database, model, Reactor, container-control, and application-secret
   authority, with one narrow authenticated path to registered HTTP backends.
6. Certificate issuance, renewal, failure, restore, route reload, rollback, listener removal,
   forwarded-header spoofing, direct-backend bypass, SSE/WebSocket drain, and resource-exhaustion
   cases pass adversarial tests.
7. Intercom discovery or task routes remain absent until their principal-bound protocol,
   replay/idempotency law, durable inbox/outbox, artifact quarantine, and local admission contracts
   exist.

**Safe next act:** keep every LychD listener on the literal same-host boundary and follow
[The Awakening](../../summoning.md#the-awakening). Do not place a reverse proxy in front of the
current Vessel.
