---
title: 38. IAM
icon: material/account-check-outline
---

# :material-account-check-outline: 38. IAM

## Context

The contained loopback surface requires a dedicated local HTTP Basic credential before assigning
one fixed `magus:*` Sigil. It proves possession of the operator's local credential and exercises
scope grammar and guards; it cannot serve remote people, services, peers, or owned nodes.
Remote use needs one authority that can identify a presenter, validate its evidence,
decide its requested object and action, and remain current when an effect occurs.

## Decision

LychD adopts the **Ward** as its singular Core-coupled IAM and authorization authority. New
Principals start with zero power; network arrival, proxy headers, mTLS, and tunnel membership may
be evidence but never application authority.

| Record | Office |
| --- | --- |
| **Principal** | Immutable identity of a human, service, peer, or owned node. |
| **User** | LychD's shared human-account abstraction bound to a human Principal, not an application-specific person record. |
| **Credential** | Revocable proof bound to one Principal, issuer, protocol, audience, and lifecycle. |
| **Session** | Authentication continuity, distinct from a Principal, Sigil, Grant, or Bridge conversation. |
| **Sigil** | Secret-free request/Run context carrying Principal identity and bounded claims. |
| **Role** | Named policy bundle that may help evaluate authority; never an ambient object grant. |
| **Authority Grant** | Current decision over Principal, action, object, audience, lifetime, policy generation, and delegation chain. |

A Sigil propagates attribution and bounded claims. It is not a bearer secret, and its historical
scope bag is not current authorization. Roles cannot turn route access into ownership of every
object served there.

## People, accounts, and instances

One logical LychD instance may serve an individual, a family or household, an organization, or
another group of people. Several people or organizations may use the same instance under explicit
access and sharing policy. Conversely, one person or organization may operate or use several
instances. These are use contexts, not mutually exclusive runtime modes or a requirement to create
an organization or tenant for every installation. Single-user operation is the smallest case, not
a one-person-per-instance invariant.

Ward owns the common User account and its binding to a Principal; Compositions reference that
identity while retaining their own domain records and policies. A represented person, such as a
care recipient or employee, need not have an account. Linking that record to a User does not itself
grant access. A person may use only a client of a shared instance and need no LychD of their own;
an enrolled device or service remains distinct from the human for whom it acts.

Enrollment and authorization are local to the receiving instance. The same human may have
different accounts, roles, and working interfaces in personal, household, and workplace instances.
Shared names, organization membership, or a common operator do not link identities or transfer
credentials, grants, memory, or trust automatically. Sovereign task delegation between instances follows
[A2A](26-a2a.md); adding Users is neither A2A nor [Legion's](42-multinode.md) distribution of one
control plane across physical nodes.

Groups and organizational memberships may supply explicit policy relationships without replacing
individual attribution. Direct Principal assignments remain possible without either. Several
Principals may receive the full administrative powers defined by an installation, using separate
credentials. Policy must state whether those powers include content access or the ability to
change access policy. The trusted host operator remains distinct from an application administrator;
shared use does not promise isolation from that operator or from trusted in-process extensions
under [Security](09-security.md).

## Profiles and working interfaces

A user-facing profile may compose permission assignments with application defaults and named
client views. The same installation need not offer every User the same apps, screens, navigation,
workflow views, or approval controls. Ward decides access to protected surfaces, records, and
actions; a durable profile or Role assignment is an input to that decision, not a perpetual Grant.
Permission to open a screen does not confer access to every object it can display.

Compositions own the meaning of their working views and application policy; Products may package
them. [Spellweaver](28-workflow.md) owns the admitted score and workflow state, not User accounts or
screen layout. An offered action must satisfy both current authorization and the workflow's
declared state and transition rules. A presentation profile cannot silently rewrite a Scroll,
widen its authority ceilings, or change a running Invocation.

Clients render the authorized projection for the selected account, instance, work context, and
device capabilities. Restricted data must be excluded before delivery, not merely hidden in the
client. [Frontend](15-frontend.md#user-specific-working-interfaces) owns browser projection; mobile
experiences such as [Companion](../compositions/companion/index.md) use the same identity boundary
without becoming the global profile authority. Application-specific actions, resources, and policy
inputs require explicit Ward integration; package registration alone grants no such integration.

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

## Trusted local custody {#trusted-local-custody}

The Designed [Reliquary profile](06-persistence.md#reliquary-custody-designed)
`same-host-trusted-bootstrap@1` accepts a subject only from trusted host composition. It requires
a mandatory injected current authorizer for import, quarantine inspection, admission, read, hold,
hold release, and deletion. Each decision names the actual subject, store and object, complete
record binding, trusted owner, action and purpose. The query also carries the typed subject of
that action: the import proposal, proposed hold UUID and reason, exact retained hold and digest
for release, admission evidence, or deletion request and hold-release basis. A policy must be
able to distinguish two holds on the same artifact; an action label and opaque digest alone do
not identify what it is allowing. There is no permissive fallback from Sigil name, scope bag,
ownership alone, network location, or caller identity headers.

The protected operation completes any awaited preparation before its final authorization check.
Under its serialized operation boundary, it checks authority immediately before admission or
tombstone publication and before handing bytes to a consumer. Prior receipts are audit evidence,
not reusable grants. Revocation or a changed decision during preparation must prevent disclosure
or the protected mutation.

This is a local composition seam, not a second IAM service. It enrolls no credential and supplies
no Ward session, remote authentication, delegation or deployed revocation service. Substituted
authorizers in tests establish consultation and refusal behavior only; they do not prove
credential-backed authority or containment against hostile same-UID code.

## Trusted local Archive profile

The opt-in `local-public-notes@1` Archive profile admits one explicitly configured namespace and
public notes only. Trusted host composition supplies a stable local subject and a mandatory current
authorizer. Every operation binds the actual subject, retained owner, namespace, purpose, action,
policy revision, and exact proposed or retained object digest. Public classification, ownership,
loopback arrival, or a Sigil scope bag does not supply a permissive fallback. The authorizer is
consulted before protected reads, after awaited preparation under the serialized namespace
boundary, and immediately before handing a retained projection to a consumer. Old receipts are
evidence, not reusable grants; restart injects a current authorizer again.

This is an explicit trusted-host composition profile, not credential enrollment, remote Principal
resolution, a Ward session, cross-namespace sharing, or isolation from trusted same-process code.
An unconfigured profile has no Archive authority. The separate read-only Bridge revision can
consume authorized notes but grants no model tool or effect authority.

Optional local derivation requires separate generation-registration, generation-retirement,
derive and status actions with dedicated purposes. Recall or ingestion permission alone does not
authorize embedding. Authority binds the configured generation and exact source/attempt identity;
post-commit response refusal does not claim rollback. Status contains no text, vector coordinates
or live token and can report an invalidated historical reference under current authority.

Source eligibility linearizes under the shared namespace lock. Current authority is checked again
after database cleanup and before each tokenizer/embedding request. No lock spans inference, so
later revocation cannot retract accepted source bytes; it does atomically invalidate controlled
vectors and fence late completion. A caller-supplied Run UUID is attribution, never a Run grant,
relationship assertion or authority to emit events into that Run.

## Trusted local Scout profile

The Designed opt-in Scout profile binds one authenticated local operator to a host-owned subject
and authentication generation in the single control process and event loop. Its mandatory current
host authorizer separately decides public-locator classification, review disclosure/judgment,
Fetch, Extract and transient material consumption. Every decision binds the actual subject,
retained Run and request, exact preparation, purpose, policy revision, revocation generation,
expiry and applicable budget. Neither a caller-supplied Run UUID nor a matching Sigil name/scope
bag supplies authority. [Security](09-security.md#target-and-disclosure-basis) owns the declaration
and disclosure basis; [Scout](30-webcrawler.md#attempt-layers-and-crash-semantics) owns attempts
and reservations. Raw acquired material remains transient, and this profile admits no remote
model inference.

After awaited preparation, a mandatory synchronous gate checks current authority, consumes the
finite reserved counters and hands off each actual socket connect/send without yielding between
check and handoff. DNS and TLS output cross this gate too. Policy updates and revocation serialize
with it on the same loop; a transport thread, separate worker or permissive transport default is
outside this profile. Revocation fences later handoffs but cannot retract kernel-accepted bytes.

Run cancellation and shutdown synchronously fence affected attempts before awaited containment.
Observed worker failure first fences its exact retained delivery claim before any settlement
await; a stale worker cannot fence a successor's claim. A Run-wide failure fence follows verified
current ownership. Every fence is monotonic: completion of a cancellation election or a
failed database/broker operation cannot reopen it. Containment must then close owned sockets and
stop/reap children. A granted consent is historical judgment; the pending-only decision operation
does not revoke it. Withdrawal uses Run cancellation or current host-policy revocation. Restart
injects current authority again and never restores a live permit from a receipt.

This local composition seam supplies no remote Principal enrollment, Ward session, cross-process
revocation or isolation from trusted same-process code. Runtime activation remains Designed until
the complete assembly and its effectful refusal, revocation and recovery evidence are delivered.

## Outbound peer authority profile

The Designed [outbound public-text profile](26-a2a.md#peer-task-jsonrpc-1) introduces narrowly
enrolled peer Principals, credentials and current task authority under Ward. The local initiating
operator, local workload signing credential and remote result-verification credential are distinct.
Actual local password possession establishes the initiating marker; its public fields, Sigil,
endpoint, TLS certificate and a key repeated in a card establish no enrollment or permission.

Trusted host composition supplies one explicit bootstrap policy; empty or missing action,
purpose, content, task, peer or endpoint selectors deny. Enrollment, source classification,
submit, poll, cancellation/reconciliation, result consumption, rotation and revocation are
separate protected operations. Each checks the real current authentication marker before a
protected query and rechecks current exact object/action authority after awaits. The dedicated
public-text declaration binds complete text, source/influence facts, subject/authentication
generation, purpose, category, peer/task target and policy generation. It is an operator assertion,
not automatic declassification of inherited private material.

Peer identity is immutable. Credential versions retain issuer, protocol, audience, public-key
binding, validity, assurance and lifecycle; private key bytes remain in the trusted secret owner.
Acknowledged retirement and policy/revocation generations survive restart and cannot be rolled
back by configuration removal, reappearance or a new label. Rotation adds a version and never
re-enrolls a retired key implicitly. Missing or incompatible durable current state refuses.
An uncertain mutation is not reported as successful; the current owner remains fenced until its
retained outcome is reconciled. Restart begins without live grants and requires fresh current
bootstrap and operator authentication rather than restoring a historical marker.

The [native public peer profile](26-a2a.md#native-public-peer-station) separately protects Run
admission, adoption and resume. The host retains only live per-Run permissions bound to the actual
marker and immutable canonical source/task/target. Explicit fresh authentication may reauthorize
that same retained relation; a first send also reaffirms its exact original public source. It
creates no new semantic task, expiry, credential or capacity. Missing live permission pauses
contact and native resume. Trusted local cancellation always remains possible; it grants no
remote cancellation or reconciliation permission.
An independently authorized local-evidence inspection may show retained Run/task identities,
local closure and remote uncertainty despite a peer revocation or uncertain peer mutation. It
requires the actual current operator marker and explicit inspection selectors, returns no source
or result body, and grants no remote contact, result consumption, adoption or resume permission.

This first profile has one control process and event loop for policy mutation, network handoff
and result admission. Revocation fences local authority before awaiting persistence. The final
current policy, credential, task fence, expiry and finite budget check and each actual socket
handoff do not yield. No database lock spans the network. This proves no cross-process revocation,
hostile same-UID isolation, human account system, incoming-task IAM or public remote browser route.

## Thresholds and delivery

[Veil](40-proxy.md) owns hostile ingress and trusted-proxy canonicalization; [Tether](39-vpn.md)
owns private reachability. Ward authenticates and authorizes traffic arriving through either.
The credential-gated `magus:*` context remains confined to the same-host operator profile and is
never a remote credential. Its dedicated password is unavailable to shared-Pod model services;
rotation replaces that secret and restarts the Vessel. No cookie, network-origin header, or
unauthenticated bootstrap route supplies fallback authority.

This Covenant records **Designed** law. No credential-backed Principal, remote session, object
authorization, delegation, revocation, tenant isolation, or IAM audit service ships.
[State of Work](../state-of-the-work.md#remote-iam) owns the exact boundary.

## Consequences

Remote surfaces can share a runtime without sharing records or power. The cost is
Principal-aware repository and effect-handler tests, plus revocation and deferred-work
reconciliation as first-class lifecycle work. Tunnels, proxies, and provider SDKs never substitute
for application authority.
