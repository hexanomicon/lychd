---
title: Ward
icon: material/shield-account-outline
---

# :material-shield-account-outline: The Ward: Extension of Authority

**Purpose:** The Ward is LychD's remote identity and authorization jurisdiction. It is the circle
of salt that decides who is speaking, which thing they may touch, and which effect they may cause.

**Current boundary:** LychD has a frozen `Sigil` carrying a name and scopes, scope-matching guards,
and a middleware seam. On the present local surface, that middleware reads no credential and stamps
ordinary requests with the fixed `magus:*` Sigil. It does not distinguish callers. The `iam`
package contains no working organ, and there is no principal or credential registry, authenticated
session, object policy, delegation, revocation, or IAM audit path. [State records the local Sigil
floor](../../state-of-the-work.md#local-sigil-authority) and the [remote IAM
boundary](../../state-of-the-work.md#remote-iam).

**Law:** [ADR 38 — IAM](../../adr/38-iam.md), under the defense-in-depth law of
[ADR 09 — Security](../../adr/09-security.md).

> _"A sovereign mind must have boundaries. The Ward is the circle of salt that lets a voice reach
> the Lich without mistaking that voice for the will of the Magus."_

The Ward preserves one sovereign continuity while allowing many lawful faces: family, work,
services, foreign peers, and owned nodes need different authority, not different souls. That promise
begins by keeping four marks distinct.

| Mark | Office |
| --- | --- |
| **Principal** | The stable human, service, peer, or owned-node subject to whom actions and objects are attributed. |
| **Credential** | Revocable proof presented by that subject. A key or certificate is evidence of possession, not policy. |
| **Sigil** | The secret-free authority context LychD carries through one admitted request or run. |
| **Authority Grant** | A current, bounded authorization decision over an action, object, audience, lifetime, and delegation chain. |

## I. The Circle of Salt

The mature Ward must authenticate before it authorizes, then authorize again where power is
actually exercised.

- **Resolution:** validate one supported credential protocol and resolve it to an enrolled,
  immutable principal. Unknown keys receive no authority.
- **Object policy:** bind sessions, runs, consents, streams, artifacts, memories, tasks, leases, and
  administrative reads to an owner or an explicit shared policy in the same persistence query.
- **Effect policy:** evaluate the current principal, action, object, assurance, delegation,
  revocation epoch, and policy generation before each protected tool or side effect.
- **Capability discipline:** reduce what an Agent can see, then enforce the decision again inside
  the effect handler. Hiding a tool from a model is defense in depth, not the only lock.
- **Revocation and witness:** expire credentials and sessions, invalidate cached grants, constrain
  queued or sleeping work, and emit redacted, immutable security events under the future
  [Oculus](./oculus.md) evidence contract.

Authentication sessions remain distinct from Bridge conversations. Historical Sigils and scopes
may explain why an old act was admitted; they may not keep that authority alive after revocation.

## II. The Three Thresholds

The Ward, [Veil](./veil.md), and [Tether](./tether.md) form one threshold without becoming one organ.

- The **Veil** may terminate TLS, canonicalize hostile ingress, and reject traffic outside a typed
  route and resource policy.
- The **Tether** may establish an encrypted path from an enrolled device and narrow which services
  that path can reach.
- The **Ward** still authenticates and authorizes every HTTP, SSE, WebSocket, callback, A2A, and
  administrative action that crosses either path.

Neither a tunnel address nor a proxy header may mint a Sigil, widen an Authority Grant, skip object
policy, or turn the current bootstrap identity into remote authentication. mTLS and Nostr signatures
may later be credential adapters; neither auto-enrolls an empowered principal.

!!! danger "The Counterfeit Master"
    The current `magus:*` Sigil belongs only to the contained local bootstrap profile. There is no
    remote Master token and no safe universal credential to share. Forwarding the current Vessel
    through a proxy or VPN would bless every reachable request with that local authority label.

## III. Gates Before the Intercom Opens

Remote authority remains sealed until all of these gates agree:

1. Stable principal, credential, authentication-session, role or permission, delegation,
   revocation, recovery, and audit contracts exist with a zero-authority default.
2. One credential protocol is implemented end to end; issuer, audience, expiry, replay, rotation,
   compromise, and one-time bootstrap behavior fail closed.
3. Every session, run, consent, stream, artifact, memory, peer task, and administrative effect has
   owner-aware query and negative cross-principal tests.
4. Worker claim, Stasis resume, consent, capability acquisition, and effect execution re-authorize
   against current policy instead of trusting a stored scope bag.
5. The host inventories every route, stream, callback, plugin, and extension contribution; every
   non-public surface carries explicit backend policy that extension code cannot remove.
6. The hostile-browser and hostile-HTTP contract passes with exact Host and Origin admission,
   secure sessions, request limits, trusted-proxy handling, revocation races, and two-principal
   noninterference.
7. The future Intercom binds task, context, artifact, callback or pull channel, resource lease, and
   result receipt to the authenticated peer principal. Peer-declared scopes never enter a local
   Sigil unchanged.
8. A peer cannot supply an arbitrary callback URL. Prefer a durable principal-bound pull channel;
   any later callback destination is pre-enrolled to that principal and revalidated for scheme,
   host, port, DNS/IP resolution, redirects, and forbidden local or metadata networks both when
   admitted and when connected.

**Safe next act:** keep LychD inside the same-host boundary and follow
[The Awakening](../../summoning.md#the-awakening). Do not proxy, tunnel, port-forward, or remotely
publish the current Vessel.
