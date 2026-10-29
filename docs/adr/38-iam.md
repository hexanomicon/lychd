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

An instance may serve one person, a family or household, an organization, or another group.
Several people or organizations can share it under explicit access and sharing policy; one
person or organization can also use or operate several instances. These are use contexts, not
exclusive runtime modes. No organization or tenant is required for every installation.
Single-user operation is the smallest case rather than a one-person-per-instance invariant.

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

A user-facing profile may combine permission assignments with application defaults and named client
views. Users of one installation may therefore receive different apps, screens, navigation,
workflow views, and approval controls. Ward still decides access to each protected surface,
record, and action. A durable profile or Role assignment informs that decision without becoming
a perpetual Grant, and permission to open a screen grants no blanket access to its objects.

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

Persistence queries enforce the owner or explicit sharing policy of sessions, Runs, consents,
streams, artifacts, memories, tasks, leases, and administrative records. An unrestricted read
followed by result filtering is too late. Shared memory needs an explicit relation with purpose,
audience, retention, and revocation; sharing a model or database grants no access.

Delegation records issuer, delegate, audience, scope, object, expiry, depth, and revocation.
Revocation invalidates credentials, sessions, cached grants, and affected sleeping or pending work;
recovery starts at zero authority. Neither a universal remote Master token nor ambient fallback is
permitted.

Typed credential adapters may verify passkeys, API credentials, signed peer envelopes, client
certificates, or later protocols. They do not mint local Sigils or compete as policy authority.
Extensions cannot remove Ward from a protected route, create a universal Sigil, or turn
peer-declared scope directly into local power. Audit retains the admitted evidence and decision
generations without exposing credential secrets.

## Host-enrolled candidate profile

The inactive `host-opaque-candidate@1` service foundation admits explicit trusted-host
composition only. The host supplies the existing Phylactery session factory and stable issuer
UUID; it alone enrolls immutable human/service/peer/node Principals and changes exact assignments.
A human enrollment creates a distinct shared User relation. Enrollment creates no permission.
No application route, middleware, browser or existing Bridge conversation selects this profile.

An enrollment returns a freshly random 256-bit opaque credential once. PostgreSQL retains only
its SHA-256 digest, exact issuer/protocol/audience, lifetime and revocation generation. A successful
one-time exchange creates a separate random authentication Session secret and marks the credential
exchanged under the Principal lock. Session tokens are bearer possession evidence within their
bounded lifetime; they do not authorize an object by themselves. Unknown credentials, issuer or
audience mismatch, expiry, repeated exchange and revocation refuse. The host must retain secrets
in its credential owner; this service does not read an ambient credential or repair a lost token.

Each protected publication freshly resolves the Session, Credential and Principal, then queries
one exact subject/action/candidate UUID/audience/purpose assignment. Assignments permit only
candidate inspect, admit, read or decide in this namespace; they do not authorize actual custody,
adoption, repository writes, activation or an existing application object. Policy changes advance
the Principal policy generation; mandatory expected-generation binding fences prepared work.
Principal, credential and Session revocations are monotonic, and no cache or historical Grant
can bypass fresh resolution after restart.

This profile requires actual transactional PostgreSQL/asyncpg READ COMMITTED operation. Each
Session must bind every Ward model to one AsyncEngine; pre-bound AsyncConnection and differing
Ward model binds refuse. Before application SQL, admission checks the checked-out DBAPI connection
is not in AUTOCOMMIT, then checks `SHOW transaction_isolation` is exactly `read committed` and the
actual asyncpg connection is inside a server transaction. Other or unknown states refuse. SHOW
alone is insufficient in AUTOCOMMIT, where row locks immediately release. Admission changes neither
caller engine configuration nor transaction isolation. This statement-snapshot prerequisite
allows child Credential/Session reads after acquiring the Principal lock to see revocations committed
while discovery or lock acquisition waited. REPEATABLE READ can retain a snapshot from the earlier
Session lookup even if locking an unchanged Principal succeeds, so it is not admitted here.

All these operations serialize on the permanent Principal row. After outside preparation,
publication first commits a uniquely identified `publication-attempt` in Ward's existing audit,
bound to the issuer, actual identities/generations and exact requested operation/policy generation.
An eligible attempt starts with unknown outcome. That transaction ends before a second transaction
reacquires the Principal lock and freshly checks all current evidence and database-clock expiry.
Only then may a trusted synchronous callback immediately hand off its projection without yielding.
Revocation or policy change between transactions prevents that handoff and retains refusal.
The attempt identity appears in callback attribution and error notes; it supplies no permit,
resume operation, deduplication or retry authority.

Eligible attempts conservatively remain unknown even when the callback returns: this seam has no
delivery oracle. Callback, commit or acknowledgement failures preserve the original exception and
retained attempt without implying that disclosure did not occur. No rollback can erase the initial
acknowledged attempt. A failed initial audit commit permits no handoff; acknowledgement loss can
still leave an unknown retained attempt. No exactly-once effect or automatic retry is admitted.

The same callback contract runs before preparation and at the store boundary. Detectable coroutine,
async-generator and generator functions or callable-object methods refuse. A callback must return
None; a returned coroutine is closed and a returned Task/Future cancelled before yielding, and any
non-None result fails with unknown outcome. No asynchronous return is awaited. These checks catch
composition mistakes: arbitrary trusted synchronous code can still schedule hidden work, block,
or hand off before raising, and is outside hostile containment. The callback permits only immediate
in-process projection handoff, with no await, blocking I/O or external effect. Attribution remains
secret-free historical context. A future consumer must integrate its own owner/sharing-aware
content query and exact content/operation binding; this assignment query supplies no object bytes.

Fixed audit events retain identities, exact operation and generations without token or payload
bytes. No cleanup or token recovery is admitted. The migration locks all Ward tables and refuses
downgrade while any identity, assignment, Session or audit remains. This inactive local foundation
supplies no remote ingress, general IAM activation, physical containment or native receipt.

## Closed inactive candidate operation

A separately composed, isolated trusted-host candidate consumer may connect Ward to physical
custody. This is distinct from `publish`: the projection callback above retains its no-I/O rule.
The fixed consumer owns one private candidate store and serializes access and shutdown before
entering custody. Its transaction-scoped synchronous authorizer queries the same Ward predicates,
exact assignments, generations and database clock at every physical custody gate while retaining
the Principal row lock. SQLAlchemy's synchronous transaction bridge may yield for database I/O;
ordinary filesystem I/O deliberately blocks inline. This profile promises neither production
event-loop responsiveness, deadlines nor hostile containment. Detached attribution, worker-thread
handoffs and caller-supplied inspectors cannot replace the live transaction.

The consumer binds exact retained bytes, candidate UUID, known selection/closure plan and assigned
participants. Inspection, import, structural admission, case binding, assessment and decision have
separate exact purposes. Every operation binds its expected current policy generation. Its private
authorizer expires on exit and cannot be returned as a Grant. Actual custody and Creation receipts
own effects; Ward's conservative attempt audit remains attribution with unknown outcome. There is
no shared filesystem/database transaction or automatic replay after uncertainty.

Native assessments require an assigned Principal distinct from the proposer. Creation retains
current-authorized attribution with the exact assessment/decision body. Only inactive hold/reject
decisions are admitted; no source write, executor, positive OwnerAdmission or activation follows.
Changed bytes, selection, policy, roles or custody identity invalidate affected preparation.

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

A model-free feed consumer binds the exact admitted Composition/Pattern, application request,
projection and custody profile in place of a model demand. CONSUME is required for deterministic
filtering too; no placeholder capability makes it a chat action. Consumer result adoption, read,
re-filter and deletion require their own current application authority. Fetch/Extract grants or a
historical consent cannot supply those decisions. The old page binding/review remains unchanged.

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

This Covenant records **Designed** law. The inactive local candidate profile above supplies no
registered application service. Remote Principal enrollment, remote sessions, general object
authorization, delegation, tenant isolation and deployed IAM remain undelivered.
[State of Work](../state-of-the-work.md#remote-iam) owns the exact boundary.

## Consequences

A runtime can serve remote surfaces while keeping their records and powers separate. Maintaining
that separation requires Principal-aware repository and effect-handler tests, with revocation and
deferred-work reconciliation treated as lifecycle work. Tunnels, proxies, and provider SDKs
cannot substitute for application authority.