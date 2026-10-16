---
title: 6. Persistence
icon: material/database
---

# :material-database: 6. Persistence

!!! abstract "Context"
    The Phylactery is LychD's jurisdiction for committed truth. It gives one body a transactional
    home for relational records, JSON documents, vectors, execution history, and recoverable graph
    state; it does not decide what a Domain record means.

## Decision

PostgreSQL is the single-node persistence backend. Ordinary application transactions
use async SQLAlchemy and `asyncpg`; the exceptional claim observer below uses one
disposable native `asyncpg` connection. The Phylactery alone owns connection and
engine construction, codecs, sessions and transaction boundaries, migration order,
and schema admission. Domains own record meaning and lifecycle; neither they nor
extension packages gain ambient migration authority.

In durable operation, **Phylactery means PostgreSQL**: the one database cluster assigned to an
application partition. It is not a generic storage facade, a repository of interchangeable
save/retrieve backends, or an abstraction that makes committed application truth backend-agnostic.
Domain repositories isolate SQL mechanics and permit bounded test substitutes and the explicitly
isolated, disposable [developer fixture](11-backend.md#isolated-developer-fixture-designed).
Neither makes a process-local or in-memory store a deployed Phylactery. LychD does not use loose
application-managed files as a shadow database around PostgreSQL transactions, constraints, and
migrations.

Future delegated-host attempt records and dispatch/closure tombstones belong to this Phylactery,
through an explicitly admitted schema and narrow typed store. The
[host handoff contract](14-workers.md#host-dispatch-and-irreversible-closure) owns their meaning;
AgentJob remains submission/adoption truth. Executor observations corroborate physical state,
not a second application ledger. This placement grants neither a guest database access nor a
host broad credentials, connection construction or migration authority. No host-attempt schema,
store or restore qualification is delivered by this decision.

### Schema admission

The `delegated-host-disposition@1` precursor stores one restrictive, create-once record per
AgentJob. The typed store owns exact canonical preparation bytes, their digest, optional one-time
dispatch identity and logical intake-closure tombstone; it serializes every mutation on the
existing AgentJob row. Database constraints retain complete-or-absent preparation and dispatch
fields and bound the preparation to two MiB. A restrictive ownership relation prevents ordinary
AgentJob or Run deletion from erasing no-reuse history. No cleanup operation is admitted; a
locked downgrade takes the strongest parent AgentJob table lock before the child table lock,
retains both through its guard and drop, and refuses any retained row. These records confer no
database access on a guest,
no host connection/migration authority, no positive owner authorization and no physical closure
or restore qualification.

The Archive `local-public-notes@1` profile retains its namespace binding, immutable attributed
note revisions, exact intake replay bindings, lifecycle versions, and text-free recall receipts in
separate PostgreSQL tables. All operations serialize on the namespace row, including recall and
receipt resolution, so promotion, correction and revocation share one decision order. The query
filters namespace and promoted lifecycle before lexical matching or content projection. Explicit
transaction-local statement and lock timeouts are five and two seconds respectively; a timeout
aborts the operation rather than becoming an empty result. Current authorization is rechecked
after transaction cleanup before response disclosure; refusing that response cannot undo a
committed mutation, whose retained replay identity and lifecycle version govern recovery. Explicit
revocation clears controlled text while retaining the minimal source identity and digest needed
to prevent replay. Existing Karma rows are neither migrated nor recalled by this profile.

The schema migration is transactional and linear. Downgrade takes exclusive table locks and
refuses while notes, replay bindings, receipts, or namespace bindings remain; it never interprets
rollback as permission to erase Archive history. Reconstruction uses retained rows and freshly
injected current authority, never process-local cache or a previous authorization receipt.

Optional Archive derivation adds immutable generation manifests/tombstones and one latest-attempt
row per exact source and generation. Composite namespace foreign keys prevent cross-namespace
pairs. A running row owns a token, version and fixed DB-clock expiry; a complete row alone owns
its vector. Source lifecycle changes and retirement clear vectors and invalidate attempts within
the same namespace transaction. Completion includes the exact source/generation/token/version/
deadline predicate and checks the canonical float32 digest after pgvector reload. Source inference
and lease cleanup happen outside database transactions. Status reads do not hydrate vectors.

Migration 0013 adds no extension or automatic backfill. The normal bootstrap migration-then-grant
sequence admits runtime DML on the new tables; runtime retains no DDL or extension privileges.
Downgrade locks namespace, source, generation and derivation tables before checking emptiness and
refuses any retained derivation history, including failed or retired tombstones. It never drops
pgvector or older Archive history to make rollback succeed.

Core owns the schema-admission seam across native and extension models. Every admitted model
derives from Core's `UUIDBase`; an extension explicitly calls `register_model(MyModel)` during
initialization; Core aggregates those references before Alembic derives migration order. Runtime
package scanning is not admission, and migration generation or application remains an explicit
release or operator act. Colliding models, table names, or migrations refuse before a schema is
changed.

### Database credentials and runtime authority

The configured `database.user` and administrative password retain the bootstrap/migration
identity, including an existing installation's `lich` owner. They never enter the Vessel.
The separate marked runtime role receives application-database CONNECT, public-schema USAGE,
table SELECT/INSERT/UPDATE/DELETE and sequence USAGE/SELECT; Alembic and SAQ version tables
remain read-only. It has no superuser, role/database creation, replication, BYPASSRLS, role
membership, schema CREATE, or application-object ownership. Every new application runtime connection must pass the same authority check:
SQLAlchemy installs it at connection creation, and the disposable claim observer
performs it before reading application records. SAQ verifies schema instead of
initializing or migrating it at worker startup.

The explicit migration gate verifies administrative identity and SCRAM TCP policy, refuses
unmarked or overprivileged existing runtime roles, provisions distinct credentials, applies
Alembic and SAQ migrations as administrator, grants runtime data access, and verifies that actual
runtime credential and queue schema before dependents start. Phoenix has a distinct marked role
for its dedicated database. Only known legacy administrator-owned Phoenix relations and enums
transfer to it; unrelated database owners refuse before mutation. PUBLIC database access is
revoked to keep these runtime roles out of one another's database. No general reassignment,
automatic demotion, database reset, or deletion is part of this gate.

The generated versioned HBA file is mounted read-only and selected explicitly on PostgreSQL
startup, covering existing as well as fresh PGDATA. TCP, including shared-Pod localhost, requires
SCRAM; local trust is confined to the private PostgreSQL-container Unix socket. An old MD5-only
administrator verifier cannot authenticate under this policy: startup of dependent services
fails closed until the operator converts that verifier through the private administrative path.
Preserved data and a known backup precede such operator repair; replacing a Podman secret cannot
change a password already stored by PostgreSQL.

The target chambers are deliberately logical rather than a claim of present deployment:

| Chamber | Responsibility |
| --- | --- |
| `public` | relational state, configuration, and extension registries |
| `vectors` | attributed vector material, including its trust status |
| `traces` | execution and observability traces |
| `queue` | durable work distribution |
| `verbatim` | JSONB exact values that must be consulted before semantic retrieval |

`vectors` status can distinguish, for example, speculative material from governed precedent;
consecration records authority, not universal factual truth.

### Default topology and scale seam

The default topology is one LychD host with one Phylactery—one PostgreSQL cluster—for its
application partition. Capacity scales up before it scales out: an operator may enlarge or
relocate the physical storage beneath the admitted `postgres/data` mount without changing
application authority. Member disks, filesystems, and volume topology remain host substrate rather
than domain or table-routing facts. The move must preserve [Layout](13-layout.md) identity and use
a PostgreSQL-consistent [capture or restore](07-snapshots.md); this decision promises no automatic
or online storage expansion.

#### Retention before expansion

Scale-up does not imply indefinite retention. Before automated retirement, every persisted record
class must declare its owning lifecycle, holds and terminal eligibility, compaction or archival,
deletion or tombstone and derivative handling, and operational maintenance. Age or disk pressure
alone grants no deletion authority. The [Reaper](31-simulation.md#the-branch-reaper) remains
Shadow-owned branch hygiene; it has no ambient authority to trim Phylactery records.

#### Storage placement inside one cluster

One cluster does not require every PostgreSQL object to occupy the same physical storage tier. A
measured later schema may use native partitioning and tablespaces to place identified relations,
indexes, or partitions across local SSD, NVMe, or HDD mounts while callers continue to query one
logical relation. This is physical placement inside one Phylactery, not an application storage
adapter, independent backup target, or shard. Before admission, [Layout](13-layout.md) and
[Containers](08-containers.md) must bind every durable mount, while [Snapshots](07-snapshots.md)
must capture and restore `PGDATA` and every tablespace at one PostgreSQL-consistent boundary. The
current topology admits only the `postgres/data` mount; this decision promises neither a partition
policy nor tablespace delivery.

#### Separate stores and application partitions

A future Domain may admit a separate, named store only by amending the smallest existing Covenant
that owns the responsibility and introducing its typed port. Such a store is not a Phylactery
backend, inherits no authority over Phylactery relational records or PostgreSQL transactions by
proximity, and must define its authorization, commit or handoff, retention and deletion, backup,
restore, and reconciliation contract. A filesystem path alone is storage geography, never
application authority.

This decision neither delivers nor promises sharding. A later amendment may assign different
whole application partitions to separate PostgreSQL Phylacteries, with routing completed before a
unit of work opens and typed handoffs between partitions. It admits no shared `PGDATA`, routing
implementation, table-level, row-level, or intra-partition sharding, and no cross-Phylactery
transaction. A [Portal](../sepulcher/animator/portal.md) remains a remote capability road, while
[Intercom](26-a2a.md) and [Legion](../sepulcher/extensions/legion.md) carry bounded work or references; none forms a
shared database fabric.

## Reliquary custody (Designed)

Reliquary is a separately named artifact store reached through one typed custody port. It is not
a Phylactery backend and shares no PostgreSQL transaction. Its first profile,
`same-host-trusted-bootstrap@1`, retains bounded immutable bytes supplied by trusted local
composition. The first consumer is Echo's canonical PCM inspector. This accepts a custody
contract; [State](../state-of-the-work.md#artifact-reference-contract) owns implementation evidence.

### Identity and quarantine

An import binds a store UUID and caller-owned request UUID to
`urn:lychd:artifact:<store-uuid>:<request-uuid>`. Only validated internal UUIDs determine storage
names; an arbitrary reference, producer label, path, or URL never supplies a filesystem component.
The first profile accepts immutable `bytes` of at most 1 MiB with declared `audio/wav` media type.
It accepts no source path, stream, URL, producer inode, or provider handle. A malformed WAV may
enter quarantine; it cannot pass the separate PCM admission check.

One immutable envelope commits the raw bytes with at most 16 KiB of canonical, versioned
metadata. The complete reference describes the raw payload, including its computed SHA-256 and
size. The record also retains its trusted owner, importing subject, store/profile and request
identity, import fingerprint, manual-retention basis, and audit time. Declared producer and source
claims remain bounded, attributed claims; missing provenance stays unknown. They cannot replace
trusted importing identity. Classification, ownership, provenance, and payload never mutate in
place; changed material needs a new identity. This profile creates no derivative graph.

Import success establishes quarantine only. Quarantine inspection, admission, ordinary read,
hold, hold release, and deletion are distinct object actions under
[IAM](38-iam.md#trusted-local-custody). Every lookup compares the full retained reference, including
identity and classification. Bounded metadata may be read internally to decide authority, but a
failed lookup or authorization discloses neither metadata nor payload. Reading a reference or
possessing an earlier decision never grants present access.

Echo's trusted admission handler retrieves the retained bytes under quarantine-inspection
authority and reruns its real PCM inspector. It does not accept a caller-constructed observation
as proof. A separate current admission decision permits an immutable receipt binding the complete
record, reference, inspector revision and measured facts. Structural success alone publishes no
admission. An admitted read checks current authority again before returning the retained bytes;
this proves neither speech eligibility nor provider compatibility.

### Publication and continuity

The caller supplies an isolated private root and retains its explicit binding: profile/schema,
store UUID, invoking UID, and root device/inode. No default XDG path or container mount is added.
[Layout](13-layout.md#publish-an-owned-object) governs safe ancestry, pinned descriptors and
no-clobber publication. One lifetime exclusive process lock and an internal operation lock
serialize all state transitions. The lock is an owned, regular `0600` single-link inode; ordinary
operation never replaces or removes it.

The envelope and immutable control receipts use the same publication mechanism: write a new
owned `0600` inode, flush and `fsync`, publish without replacement, re-attest the public identity,
remove only its exact owned private staging name, and sync the namespace before reporting
success. Every envelope, control, and lock read opens without following links or blocking on
special files, then checks the opened inode's type, owner, mode, link count and bounded size
before reading. A producer retains no write descriptor or hardlink to the owned copy.

An exact import retry with the same request fingerprint returns current retained custody after
fresh authorization. Different bytes or immutable metadata conflict without replacing the
original. A tombstone permanently forbids reuse. A lost response after a proved commit therefore
permits exact lookup; uncertain publication never permits blind replay.

Clean same-root restart verifies the retained root binding, bounded envelope metadata, control
bindings and file identities. Activation reads no payload region. Each later protected access
checks the complete retained record and current authority before reading payload bytes, then
verifies their size and digest before disclosure; reopening alone proves no payload integrity.
Unknown entries, unexplained private stages, extra aliases, malformed records, replacement or
uncertain settlement are preserved as typed recovery. A filename alone grants no cleanup
authority. The first profile need not guess how to repair every interrupted state automatically.

### Retention and deletion

Retention is manual. Up to sixteen distinct hold identities may be recorded over one artifact's
lifetime; exhausting that bound refuses another hold. Each immutable hold binds its UUID, reason,
subject and exact record. Hold authorization sees that proposed UUID and reason. Release names
the exact retained hold and its digest, exposes that target to current release authorization,
and cannot affect a later hold. Hold IDs are never reused; elapsed time releases nothing.

Hold changes and deletion share the serialized operation boundary. Any active hold refuses
deletion without changing bytes or policy. Deletion first publishes and directory-syncs a
permanent tombstone binding the retained record, exact payload identity, deletion request and
decision, and hold-release basis. That tombstone takes precedence over admission and denies both
ordinary and quarantine reads, even when physical cleanup fails.

Only then may the adapter retire the exact owned, regular, single-link payload identity and sync
the resulting namespace. Its result distinguishes payload absence, cleanup pending, and recovery
required. A fresh authorized retry may finish retirement of the recorded identity; it cannot
adopt a foreign replacement. Tombstones remain indefinitely and import identities cannot be
reused. This promises logical unavailability and observed local cleanup, not secure media erasure
or deletion of copies outside the store. Native Linux retirement remains a separate physical
verification obligation.

### Backup and restore boundary

This first profile supplies no export, clone activation, or restore-reactivation operation.
Copying a directory is not an admitted backup or restore. A known restoration, lost control
history, or uncertain continuity disables activation. Future restoration must enter an inactive
target and reconcile against separately retained, nonrollback deletion and hold authority;
without it, activation refuses. [Snapshots](07-snapshots.md#rehydration-and-reckoning) cannot revive
material merely because an older capture lacks a later tombstone.

Root UUID and inode checks establish ordinary binding continuity, not freshness against an
out-of-band in-place rollback. This trusted-host profile does not contain malicious processes
with the same UID or an operator rewriting its storage. Such behavior cannot be detected merely
by revalidating in-root hashes and is not claimed as protected recovery.

## Wire and work contracts

### Codecs and detached values

The async boundary uses the repository JSON serializer and deserializer. PostgreSQL binary `json`
is the JSON payload; binary `jsonb` prefixes it with the `\x01` format-version byte. The connection
hook registers separate codecs for those wire shapes. Focused hook tests pin their exact framing,
and a disposable PostgreSQL receipt round-trips both a plain `json` expression and JSONB through
the production engine factory. Avoiding an intermediate text conversion is not zero-copy storage.

The loop-confined Run-ledger adapter deep-detaches mutable Run records, nested manifests, and event
metadata on write and every public read. That matches the database adapter's value boundary: a
caller cannot mutate canonical truth through an object it was handed. This parity rule does not
turn the memory profile into durable evidence.

The same value boundary applies to loop-confined consent and Bridge-session stores. Censored
arguments, turns, fragments, and model-history values are detached both when retained and when
projected; mutating a submitted object or a read view cannot rewrite the store's canonical value.

### Atomic claims and checkpoints

Workers select pending work under row locks with `SKIP LOCKED`. Selection, ownership transition,
and all facts that establish the claim commit atomically: no two workers may own one labor unit.
The replaceable JSONB `run_checkpoint` is one unique, cascading row per `run`; it is recovery
state, not the ordered `run`/`step` ledger.

An exact Run claim first locks the Run by identity, then its exact delivery, in
the existing SQLAlchemy transaction. It proves the unclaimed prestate before any
mutation or autoflush can occur, retains the conditional Run and delivery updates,
and commits them atomically. A conditional mismatch after that locked proof is an
attempt failure. Queue selection's `SKIP LOCKED` rule does not govern these exact
identity reads.

After an eligible completed claim failure, the Phylactery may open one disposable
native `asyncpg` observer using the same configured endpoint, database, runtime
role, loaded runtime password, and connection-security policy. It executes the
existing `RUNTIME_AUTHORITY_QUERY` and `require_runtime_authority`; only exact
positive verification permits application reads. Authority refusal remains an
authority error. There is no administrative fallback, alternate endpoint, pool
checkout, connection reuse, or retry.

The observer starts one READ COMMITTED, READ WRITE transaction and takes bounded
blocking locks on the Run identity, then its exact delivery. Bound parameters and
the owned model identities define its narrow detached scalar projection. It issues
no application DML or claim commit. A skipped lock or a nonlocking `QUEUED` read
cannot establish claim loss.

One absolute five-second monotonic deadline covers connection establishment,
authority verification, transaction setup, both reads, detached-value construction,
any normal rollback, and synchronous handle termination. Each operation consumes
the remaining budget; nonzero server statement and lock limits must not round to
zero or restart that budget. An explicit cutoff check rejects incomplete or late
evidence before return.

Every acquired observer handle is synchronously terminated before completion and
never returned to a pool. Failure cleanup begins termination before graceful close
and does not await rollback or close during deadline unwind. No detached
application observer task is admitted.

This is a cooperative observation-acceptance boundary. It proves neither server
rollback completion nor universal resource reclamation. Startup and CancelRequest
transports, callbacks, and possible DNS executor work can remain library-owned
after cancellation. Acceptance on the admitted Linux profile requires adverse-
transport and connection-count recovery evidence for both startup and command
cancellation. [State of Work](../state-of-the-work.md#topology-a-local-runs) records
implementation and qualification status.

### Deployment authority and edge journals

One application partition has exactly one active Phylactery—one PostgreSQL cluster—and authority
epoch. PostgreSQL is never exposed, shared, synchronously replicated, dual-written, or failed over
across a WAN.
Backups and inactive migration restores are recovery artifacts, not live authorities. Moving
authority requires a quiesced, typed export/import that preserves schema, labels, dedupe and
external-effect identities; it never copies an unrelated home partition by implication.

A platform adapter on another host may own a bounded durable journal for immutable envelope bytes,
digests, external identities, attempt generations, and observed receipts. That journal proves only
transport or effect custody. It cannot admit or settle application truth, own a Run, Context, Ward
decision, Sigil, corpus judgment, or become a Phylactery replica. The authoritative body adopts
events and settlements through typed authenticated operations. Loss or ambiguity remains explicit
and never triggers silent application replay.

### Delivery and recovery identities

Each Run hop also owns one `run_delivery` row. Run admission or wait re-admission and its exact
delivery identity commit together; broker publication happens afterward under an idempotent key.
`HELD`, `PENDING`, `PUBLISHED`, `CLAIMED`, and `SETTLED` distinguish admission custody from broker
acknowledgement and execution ownership. One partial unique index permits only one unsettled
delivery per Run, while `(run_id, enqueue_seq)` permanently fences old workers. A process-owned
relay repairs publication without treating the broker as canonical Run truth.

Migration `0004` refuses both introduction and removal of that delivery authority while any Run is
nonterminal. PostgreSQL transactional DDL leaves the schema revision and outbox intact on refusal;
an operator must settle or explicitly fail the work before crossing the boundary. This is a narrow
delivery-schema compatibility fence, not a general application rollback mechanism.

#### Nexus request identities

Operator Nexus transitions reserve their caller-owned request id in `nexus_swap_request` before
launch. The unique request id and immutable first target are a durable duplicate-effect fence, not
a transition state machine: loss of the process-local ticket causes exact retries to refuse without
relaunch rather than inventing an outcome. Migration `0007` refuses downgrade while any request
identity remains; erase or archive is an explicit operator act, not an incidental rollback.
The downgrade holds an `ACCESS EXCLUSIVE` lock through the refusal check and table removal so a
concurrent old writer cannot create a request identity between inspection and DDL.

#### Consent and delegated-wait evidence

Consent waits persist their exact owner on `Run.consent_id`; newest-row ordering is not ownership.
Settled Consent rows require a decision principal and decision time, while terminal delegated jobs
require result evidence whose job and status match the durable row. Migration `0008` refuses an
upgrade that would have to infer an existing consent-wait owner or accept settled rows without that
evidence. Its downgrade refuses while any Run remains `AWAITING_CONSENT`, so exact ownership cannot
be erased underneath live work.

#### Native Consent bindings (Designed)

The [native review contract](25-hitl.md#required-review-for-native-actions-designed) adds explicit
`native_review_required` and optional `native_binding` fields to Consent. Existing rows retain a
false requirement and no binding, without rewriting their verdict or attribution. New native rows
retain the requirement and complete binding together; missing or unsupported binding cannot be
interpreted as legacy consent. Application decision updates preserve both fields.

Removing this schema must refuse while any required-native or native-bound Consent remains,
including settled history. The refusal check and schema removal hold a table lock that excludes
concurrent writes, so a new binding cannot arrive between them. Rollback cannot erase or detach
these records to make itself succeed; any custody or deletion decision is a separate owner act.
This is **Designed** compatibility law, not an executed migration receipt. It adds no native action
store and does not give Consent's Run lifecycle ownership of application recovery records.

#### Blockworld placement custody (Designed)

Blockworld's bounded placement keeps its admitted mission and native action in separate
application records. The action retains its frozen command, exact Pattern and preparation/review
identity, Consent identity, issuance disposition, judgment evidence used at issuance, and receipt
or exact non-completion. Its immutable Run and Consent identifiers are references, not cascading
ownership: deleting Core execution or Consent records cannot delete or detach this application
truth. The action's mission reference restricts mission deletion while an action remains.

Before issuance, a missing Run or Consent refuses the action. After issuance may have begun,
missing execution or Consent records permit only reconciliation of the retained action; they never
grant another issuance. Preparation, its Consent and any consumed bounded preauthorization share
one transaction. Conditional issuance serializes the mission cursor and action; verified receipt,
mission cursor and placement budget settle in one transaction. An uncertain commit is resolved by
retained identity before further mutation.

A terminal refusal before action creation is retained on the mission. Re-entry returns that result
without creating Consent, consuming preauthorization, or reopening placement.

This first schema has no automated retirement or deletion path. Removing it refuses while any
mission or action remains, including settled history. The refusal check and removal lock both
tables against concurrent writes in a fixed order. Export, explicit erasure, archival and
incompatible-record migration require a later owned operation; downgrade cannot erase or rewrite
retained records to make itself succeed.

### Atlas records

The initial Atlas Project is one versioned aggregate scoped to a Sigil. Its validated JSONB document
retains the brief, concern definitions, append-only assessments and decisions, and explicit
references to existing sessions and Runs. Assessments retain their judged text and revisions;
editing current requirements cannot rewrite their historical basis. Reference identities are
related activity, not copied execution evidence. A missing target remains an unavailable
reference rather than becoming a successful result.

Project mutation locks the owner-scoped aggregate and commits its new version together with a
request receipt. A receipt binds the exact request payload to its Project; reuse with different
content refuses. An exact replay returns current retained Project truth without repeating the
mutation. Creation similarly binds a caller-generated Project UUID to its initial payload.
The memory profile implements the same detached-value and replay behavior for bounded tests;
only PostgreSQL supplies restart persistence.

No Project, concern, assessment, decision, or reference deletion is admitted in the initial
surface. Closing a Project retains its records and does not cascade into sessions or Runs.
Migration `0009` adds Atlas without rewriting execution identity. Its downgrade takes an
exclusive table lock and refuses while any Project remains, preserving operator material across
an attempted rollback. Deployment migration remains an explicit operator act.

### Independent Concern retention

[Frontend](15-frontend.md#independent-concerns-decomposition-and-addressing) defines
Concerns with identity and authorization independent of optional Project membership. Their
definitions, attributed relation revisions, proposal provenance, and judged bases must survive
independently of a Project's lifecycle. Removing an association cannot erase the Concern or
reinterpret another context's judgment. Shared relations refer to retained identities rather than
copying a Concern's mutable definition into each Project.

Historical assessments retain the exact Concern, context, and relation basis they used. Source
and target locators bind the actual revision or content identity inspected; a mutable URL or an
unchanged Covenant number cannot substitute for that identity. Updates preserve prior bases and
use owner-scoped version checks and retry receipts. Migrating the initial Project aggregates must
preserve existing Concern, assessment, reference, and retry identities and their Project context;
it must not infer new shared identities from similar text. This requires a new explicit schema and
migration contract before delivery; migration `0009` supplies only the initial Project aggregate.

## Privacy and delivery boundary

Persistence is designed to retain the labels and lineage defined by
[Context](21-context.md#privatization-and-the-privacy-cut): defaults may originate in table or
column metadata, policy may refine them by row, subject, or namespace, and derivatives retain
their material sources and transformations. Checkpoints, history, memory, artifacts, and delegated
records retain the applicable label or omit sensitive content. Missing ORM annotation never makes
raw data public.

This is storage and information-flow support, not declassification. Context owns the Privacy Cut;
the trusted [Security Egress Gate](09-security.md#portal-privatization-and-egress) enforces the
resulting decision immediately before transmission. Dispatcher may provisionally refuse or bind a
capability, but it cannot declassify bytes. Exact label schema, row policy, and full production
persistence remain subject to the delivery boundary in
[State of Work](../state-of-the-work.md#phylactery-first-light).

### Reversible maps and the Privacy Vault

A reversible Privacy Cut persists no pseudonym map in Run, Graph checkpoint, receipt, event, or
general Phylactery row. Those records may hold one opaque `PseudonymMapLease@1` reference.

Mapping bytes require the Context-owned lease registry and rehydration port backed by a deployment-local
Privacy Vault with exact Cut/Run/attempt ownership, idempotent claim CAS, key epoch, TTL, access
audit, and one per-lease data-encryption key that never enters ordinary backup.

Expiry, revocation, consumption, or abandoned-work cleanup destroys that key; a restore drill proves any retained
ciphertext undecryptable and never claims physical erasure from opaque provider media. Loss or
expiry means rehydration is unavailable and never permits raw-history reconstruction.

The accepted Vault profile also contains transient plaintext: its map pages are unswappable or the
host swap is disabled, core/crash dumps and debugger attachment are disabled, buffers are bounded
and zeroized after use, and map material is excluded from traces and allocator diagnostics. A
deployment unable to verify those properties cannot enable reversible Cuts.

## Consequences

One logical state transition can share a PostgreSQL transaction, while write-heavy queue and trace
tables need workload-specific retention and autovacuum policy. The delivery outbox is transactional
with Run truth but not with the external SAQ transaction; its relay and exact keys close that gap.
Step/event publication still lacks a transactional outbox, and memory profiles do not have complete
behavioral parity with PostgreSQL repositories. The offline lifecycle receipt and its limits are
recorded in the [current evidence envelope](../state-of-the-work.md#current-evidence-envelope);
real host/model/browser operation remains unproved.
