---
title: 38. IAM
icon: material/account-check-outline
---

# :material-account-check-outline: 38. IAM

## Context

The contained loopback surface carries one fixed `magus:*` Sigil. It exercises scope grammar and
guards; it does not authenticate callers and cannot serve remote people, services, peers, or
owned nodes. Remote use needs one authority that can identify a presenter, validate its evidence,
decide its requested object and action, and remain current when an effect occurs.

## Decision

LychD adopts the **Ward** as its singular Core-coupled IAM and authorization authority. New
Principals start with zero power; network arrival, proxy headers, mTLS, and tunnel membership may
be evidence but never application authority.

| Record | Office |
| --- | --- |
| **Principal** | Immutable identity of a human, service, peer, or owned node. |
| **Credential** | Revocable proof bound to one Principal, issuer, protocol, audience, and lifecycle. |
| **Session** | Authentication continuity, distinct from a Principal, Sigil, Grant, or Bridge conversation. |
| **Sigil** | Secret-free request/Run context carrying Principal identity and bounded claims. |
| **Role** | Named policy bundle that may help evaluate authority; never an ambient object grant. |
| **Authority Grant** | Current decision over Principal, action, object, audience, lifetime, policy generation, and delegation chain. |

A Sigil propagates attribution and bounded claims. It is not a bearer secret, and its historical
scope bag is not current authorization. Roles cannot turn route access into ownership of every
object served there.

## Admission and effect-time authority

For every protected request, Ward validates credential protocol, issuer, audience, expiry, replay
defence, revocation, and assurance; resolves one enrolled Principal; mints a secret-free Sigil
from trusted local state; authorizes route and named object in one ownership-aware query; then
records credential, policy, and revocation generations. Unknown credentials, unresolved
Principals, and caller-supplied identity or scope headers receive no authority.

Before a tool or side effect runs, its owning handler checks current Principal, action, object,
assurance, delegation, consent or preauthorization, policy generation, and revocation epoch
again. Agent-visible tools can be narrower than the Grant; their handler remains authoritative.
Worker claim, Stasis resume, consent resume, queued work, and deferred peer work may not reuse a
stale scope snapshot.

## Objects, delegation, and revocation

Sessions, Runs, consents, streams, artifacts, memories, tasks, leases, and administrative records
carry an owner or explicit sharing policy enforced by the persistence query. Filtering a completed
result after unrestricted read is too late. Shared memory is an explicit relation with purpose,
audience, retention, and revocation; a common model or database grants nothing.

Delegation records issuer, delegate, audience, scope, object, expiry, depth, and revocation.
Revocation invalidates credentials, sessions, cached grants, and affected sleeping or pending work;
recovery starts at zero authority. Neither a universal remote Master token nor ambient fallback is
permitted.

Typed credential adapters may verify passkeys, API credentials, signed peer envelopes, client
certificates, or later protocols. They do not mint local Sigils or compete as policy authority.
Extensions cannot remove Ward from a protected route, create a universal Sigil, or turn
peer-declared scope directly into local power. Audit retains the admitted evidence and decision
generations without exposing credential secrets.

## Thresholds and delivery

[Veil](40-proxy.md) owns hostile ingress and trusted-proxy canonicalization; [Tether](39-vpn.md)
owns private reachability. Ward authenticates and authorizes traffic arriving through either.
Bootstrap `magus:*` remains confined to the same-host profile and is never a remote credential.

This Covenant records **Designed** law. No credential-backed Principal, remote session, object
authorization, delegation, revocation, tenant isolation, or IAM audit service ships.
[State of Work](../state-of-the-work.md#remote-iam) owns the exact boundary.

## Consequences

Remote surfaces can share a runtime without sharing records or power. The cost is
Principal-aware repository and effect-handler tests, plus revocation and deferred-work
reconciliation as first-class lifecycle work. Tunnels, proxies, and provider SDKs never substitute
for application authority.
