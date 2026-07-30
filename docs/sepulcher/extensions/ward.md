---
title: Ward
icon: material/shield-account-outline
---

# :material-shield-account-outline: The Ward

> _The Ward lets a voice reach the Lich without mistaking that voice for the Will of the Magus._

Recognizing a speaker draws only the first mark of a salt circle. Current policy and revocation
must close it around this exact effect. **Ward** is LychD's singular Core-coupled authority for
caller authentication and authorization.

Remote Ward is **Designed**, with its boundary owned by [State of
Work](../../state-of-the-work.md#remote-iam). The implemented [local Sigil and scope
floor](../../state-of-the-work.md#local-sigil-authority) is **Partial**: ordinary contained requests
receive the fixed, secret-free `magus:*` Sigil; middleware reads no credential and distinguishes no
caller. Scope guards and consent preauthorization exist. No Ward provider, credential-backed
Principal, remote session, object authorization, delegation, revocation, tenant isolation,
recovery protocol, or IAM audit ships.

## The marks inside the circle

A Credential is revocable evidence of possession; a Principal names the immutable human,
service, peer, or owned node to whom acts and objects belong. After verification, Core would issue
a secret-free Sigil carrying that Principal and bounded claims through one request or Run. An
Authority Grant is the current decision over Principal, action, object, audience, lifetime, policy
generation, and delegation chain. Historical scopes are evidence, not live policy. An
authentication session remains distinct from all four and from a Bridge conversation.

In the designed Ward, provider adapters verify evidence without minting Sigils or becoming policy
authorities. Admission validates protocol, issuer, audience, expiry, replay, revocation, and
assurance; resolves one enrolled Principal; then authorizes the route and named object in an
ownership-aware query. The decision records credential, policy, and revocation generations. Unknown
credentials, unresolved Principals, and caller-supplied identity or scope headers receive zero
authority. No Extension may remove Ward from a protected surface.

## Authority at the moment of consequence

Sessions, Runs, consents, streams, artifacts, memories, tasks, leases, and administrative records
carry an owner or explicit sharing policy in the persistence query. Filtering after an unrestricted
read is too late.

Immediately before a protected tool or effect, its handler rechecks the current Principal, action,
object, assurance, delegation, consent or preauthorization, policy generation, and revocation
epoch. It checks again after queueing, worker claim, Stasis, consent, resume, or another wait.
Narrowing the tools visible to an Agent helps; the handler remains the lock.

The current preauthorization floor does not safely recheck expiry before a delayed effect, startup
synchronization may retain a removed rule, and budget consumption is not atomic with the consent
record. Revocation must invalidate Credentials, sessions, cached grants, and affected pending or
sleeping work. Recovery begins at zero authority: no universal remote Master token or ambient
fallback exists.

## No borrowed authority

[Veil](veil.md) terminates TLS and canonicalizes hostile traffic; [Tether](tether.md) narrows
reachability. Their headers, addresses, certificates, signatures, or Tether arrival may
contribute evidence, but never mint a Sigil or application authority. [Mirror](mirror.md) preserves
operative identity and attribution; Ward authenticates and authorizes the initiating or approving
Principal. [Intercom](../../adr/26-a2a.md) peer scopes likewise cannot enter a local Sigil unchanged.

Keep the Vessel and Altar on same-host loopback. Do not proxy, tunnel, port-forward, or remotely
publish them. [ADR 38](../../adr/38-iam.md) owns Ward law; [Security](../../adr/09-security.md)
owns the wider boundary.
