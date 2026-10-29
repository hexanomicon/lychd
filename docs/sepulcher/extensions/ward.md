---
title: Ward
icon: material/shield-account-outline
---

# :material-shield-account-outline: The Ward

> _At the circle's edge, a voice gives its name._

Recognizing a speaker draws only the first mark of a salt circle. Current policy and revocation
must close it around this exact effect. **Ward** is LychD's singular Core-coupled authority for
caller authentication and authorization.

The bounded outbound peer profile is **Partial**, with its boundary owned by [State of
Work](../../state-of-the-work.md#remote-iam). [Intercom's operator session](../intercom.md)
separates actual local operator authentication, workload signing identity and enrolled remote
peer credentials. It checks current object/action policy before contact and result consumption;
it provides no incoming remote login or human account system. The implemented [local Sigil and scope
floor](../../state-of-the-work.md#local-sigil-authority) is **Partial**: protected contained requests
must present the dedicated local HTTP Basic credential before receiving the fixed, secret-free
`magus:*` Sigil. This possession check does not distinguish people. Scope guards and consent
preauthorization exist; separate User accounts and the remote IAM path below remain Designed.

## One instance, different people and working views

A personal instance may admit friends; a household may share an instance administered by a parent;
a company may give employees different application views through browser or mobile clients. A
person or organization may also use several instances, with independently admitted accounts and
permissions in each. Users need not run a LychD themselves. [IAM's account and instance
contract](../../adr/38-iam.md#people-accounts-and-instances) owns these relationships.

An assigned profile may offer one person a task form and another a review screen for the same
work. Ward determines permitted access; the application owns the working views, Spellweaver the
workflow, and the client their presentation. A profile can package those choices without merging
their authorities. Follow [profiles and working interfaces](../../adr/38-iam.md#profiles-and-working-interfaces)
and the [deployment examples](../../compositions/products-and-suites.md#deployment-and-projection-are-different-axes).

## The marks inside the circle

Start with what the caller presents. A **Credential** is revocable evidence of possession.
Verification connects it to a **Principal**, the immutable human, service, peer, or owned node
to whom acts and objects belong. Core would then issue a secret-free **Sigil** carrying that
Principal and bounded claims through a request or Run.

Whether that Principal may perform this act now is a further decision. An **Authority Grant**
binds Principal, action, object, audience, lifetime, policy generation, and delegation chain.
Historical scopes can inform the decision but cannot replace current policy. An authentication
session is another distinct record, separate from these four and from the Bridge conversation.

In the designed path, a provider adapter verifies credential evidence while Ward retains policy
and Core retains Sigil issuance. Admission checks protocol, issuer, audience, expiry, replay,
revocation, and assurance, then resolves one enrolled Principal. An ownership-aware query decides
access to the route and named object and records credential, policy, and revocation generations.

An unknown credential or unresolved Principal receives no authority. Caller-supplied identity
or scope headers cannot fill the gap, and no Extension may remove Ward from a protected surface.

## Authority at the moment of consequence

Sessions, Runs, consents, streams, artifacts, memories, tasks, leases, and administrative records
carry an owner or explicit sharing policy in the persistence query. Filtering after an unrestricted
read is too late.

Immediately before a protected tool or effect, its handler rechecks the current Principal, action,
object, assurance, delegation, consent or preauthorization, policy generation, and revocation
epoch. It checks again after queueing, worker claim, Stasis, consent, resume, or another wait.
Narrowing the tools visible to an Agent helps; the handler remains the lock.

Revocation must invalidate Credentials, sessions, cached grants, and affected pending or sleeping
work. Recovery begins at zero authority: no universal remote Master token or ambient fallback
exists.

### The current preauthorization floor

The current preauthorization path checks permission in the conditional write that consumes it,
immediately before the effect is granted. It rechecks enabled state, source presence, expiry
against database time, and the remaining use budget.

At startup, synchronization marks removed Rune-owned policies `source_present = false` while
preserving operator enable/disable and usage state. An exact later reappearance may restore source
presence. Budget consumption and the consent record commit in one PostgreSQL transaction;
injected insert failure and removal/expiry races test rollback of that joint account.

## No borrowed authority

[Veil](veil.md) terminates TLS and canonicalizes hostile traffic; [Tether](tether.md) narrows
reachability. Their headers, addresses, certificates, signatures, or Tether arrival may
contribute evidence, but never mint a Sigil or application authority. [Mirror](mirror.md) preserves
operative identity and attribution; Ward authenticates and authorizes the initiating or approving
Principal. [Intercom](../../adr/26-a2a.md) peer scopes likewise cannot enter a local Sigil unchanged.

Keep the Vessel and Altar on same-host loopback. Do not proxy, tunnel, port-forward, or remotely
publish them. [ADR 38](../../adr/38-iam.md) owns Ward law; [Security](../../adr/09-security.md)
owns the wider boundary.
