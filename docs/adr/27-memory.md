---
title: 27. Memory
icon: material/brain
---

# :material-brain: 27. Memory

!!! abstract "Context"
    Working context is bounded; durable storage does not itself decide what deserves retention,
    recall, correction, or authority. Embeddings help retrieve while adding model and deletion
    obligations. Archive must keep source, policy, and lifecycle inspectable outside retrieval tools.

Flux leaves a [Seed](../sepulcher/lich/spirit/seed.md); Archive preserves its return; [Recall](../sepulcher/lich/spirit/recall.md)
moves retained form into present work.

## Decision

Archive keeps authoritative records, lineage, policy, lifecycle, and derivations in PostgreSQL,
with pgvector-derived indexes behind LychD-owned ports. Frameworks may help extract, embed, rank,
or rerank; they cannot silently acquire transaction, migration, curation, sharing, or
training-eligibility authority. Run/Step ledgers, traces, checkpoints, Personas, one-call context,
and Soulforge corpora remain distinct stores of meaning, cited through stable refs.

!!! warning "Delivery boundary"
    The bounded public-note profile below does not deliver the general Archive contract.
    Automatic intake, combined native semantic retrieval, cross-namespace sharing, Curator, and
    private-material recall remain separate work. Existing Karma rows are not a usable memory corpus. State owns
    the profile's exact executable and acceptance boundary.

## Bounded local public notes

The opt-in `local-public-notes@1` profile admits explicitly supplied bounded text to one
configured namespace. Trusted host composition supplies its stable local subject, namespace owner,
and mandatory current authorizer; neither a Sigil name nor public classification grants access.
The retained namespace binds its owner and policy revision. A changed configured binding refuses
existing material until an explicit migration is admitted; restart cannot adopt it implicitly.
Every admission, lifecycle change, recall, and receipt resolution binds subject, namespace, owner,
purpose, exact policy revision, action, and proposed or retained object digest. Authorization is
checked before reads and again after awaited preparation under the serialized namespace operation.

An exact intake request is idempotent. Reusing its identity with different material refuses, as
does changing bytes under an existing source key and source revision. Separate request identities
may name the same exact source revision without creating another note. A revoked source revision
remains a tombstone and cannot be reingested. Source identity is asserted provenance, not proof of
real-world authorship or semantic deduplication.

Each note revision starts as a candidate. Explicit promotion makes it eligible and atomically
archives any earlier promoted revision of that source. Archive and revoke remove ordinary recall
eligibility; revoke additionally clears controlled text. Lifecycle versions fence stale changes
and retained recall. PostgreSQL `simple` text search supplies lexical matching and ranking, with
finite input, result, and character bounds and a stable UUID tie break. Lexical recall executes no embedding.
Every Archive transaction sets its own five-second statement timeout and two-second lock timeout
before namespace work; these bounds never change the connection's defaults. Timeout is an
operation failure that rolls back undecided work, never a lexical miss.

Current authorization is checked once more after transaction and session cleanup, immediately
before any record, receipt or source projection is returned. A refusal at that final response
boundary does not undo an already committed mutation. An authorized exact intake replay recovers
its retained identity and current lifecycle; stale lifecycle retries refuse their expected-version
comparison rather than guessing whether to repeat the change.

Authorized configuration discovery and metadata inspection have explicit actions and management
purpose; recall is not a shortcut to review authority. Configuration discovery returns only the
current configured public-note profile, without storage access, namespace creation, model probes
or Run admission. It does not establish compatibility with an existing retained namespace.
A separate authorized interface projection may identify the admission engine's current default
Pattern and compare its complete configured Archive binding with this managed profile. Only
`bridge_chat@3` with an equal binding requests this profile; another default or a missing/different
binding does not. An unavailable admission default stays unknown. This projection reveals no other
profile's namespace or owner and performs no storage, model or Run work. It establishes neither
readiness, the next routed Run, nor the binding of an already admitted Run.
Metadata reads expose bounded source/revision, digest, lifecycle/version and retention metadata
across candidates, promoted revisions, archives and revoked tombstones. They select no note text,
search vectors, recall projections or embeddings. Lists use a finite page bound and stable keyset;
an exact-record read permits recovery from a lost mutation response without replaying that effect.
Reads create no persistent namespace, note or receipt rows. A missing namespace lists empty, while
an existing owner/policy mismatch or storage failure refuses instead of becoming an empty result.
Current authorization is rechecked after awaited preparation and transaction/session cleanup.
Recovered lifecycle versions still require a new explicit compare-and-set decision; inspection
neither retries a transition nor restores revoked content or source-revision eligibility.

A durable recall receipt retains the exact namespace, subject, purpose, policy, query digest,
budgets, selected revision and lifecycle identities, projection digests, and ordered scores. It
contains neither query nor note text. Resolving that receipt rechecks current authority and exact
eligible revisions; it refuses revoked, archived, superseded, changed, or missing material rather
than replacing the selection. A miss differs from infrastructure failure. Each later model request
resolves the same receipt again.

Historical receipt metadata inspection is a separate current-authorized management read. It
looks up one exact namespace and request identity, validates the retained receipt's integrity and
its complete expected request, subject, answer purpose and profile binding, and returns no source
text. It performs no recall, resolution, lifecycle transition or persistent write. Missing storage
is not a miss; an absent receipt remains absent. Namespace owner/policy and current inspection
authority are checked after awaited preparation and transaction/session cleanup. A valid historical
selection remains inspectable after source correction, archival or revocation; that inspection
neither claims current eligibility nor restores controlled content. Source names and digests are
protected metadata under the configured local management authority, not anonymous public exports.

A Run-linked explanation additionally requires the retained exact supported Pattern, admitted
Archive/capability binding and complete expected recall request. Caller-supplied Run/request
identities can preseed even that exact request. The explanation therefore establishes a retained
selection matching the Run request, not that the workflow consumed it or sent it to a provider.
A stronger execution claim requires a separately owned capture at the actual boundary. Context owns transient attributed data projection; retrieval
never adds instructions or authority. The read-only Bridge revision uses no model tools or settled
history replay, and retains only receipt references to retrieved material in Graph state. Generated replies may quote
the notes: source revocation cannot erase that recorded influence.

This profile establishes a bounded lexical path, not semantic retrieval, automatic retention,
Curator judgment, shared namespaces, remote IAM, private-material egress, or training. Old Karma
rows remain inert and are not silently admitted. State owns the implementation evidence.

## Explicit local derivation

An independent optional Archive selection may bind one configured generation and the exact local
Core `model.embed@1` profile. Generation registration is explicit and authorized; startup never
registers rows or starts a model. Its immutable manifest binds namespace ownership and policy,
Core profile/binding, whole-note chunking, cosine metric, float32 storage and a fixed 60-second
attempt lifetime. Retiring a generation is irreversible; replay cannot reactivate it.

An authorized caller may discover the configured generation identifier and manifest digest before
registration. Discovery checks current namespace policy and the generation-discovery action with
the management purpose. It returns configuration metadata only: no registration or eligibility
claim, source material, database access, lease, readiness probe or model activation follows.

The first derivation stores one whole promoted note as one 1024-dimensional pgvector value.
Core measures tokens and refuses its fixed byte/token limits; neither caller truncates or splits
oversize notes. The profile binds float32 little-endian encoding and the accepted L2 tolerance.
Core and persistence use the same canonical float32 digest without renormalization; an actual
PostgreSQL round trip must preserve it, including signed zero. The execution receipt retains
only bounded identities, digests and usage, never source text or a second copy of vector coordinates.

Durable identity is namespace, generation, exact source revision and whole-note chunk. Status
exposes the latest attempt only: prepared, running, expired, complete, failed or invalidated.
A DB-clock deadline makes an abandoned running attempt visibly expired; only an explicit retry
may claim it. No background job, automatic retry, semantic coverage or query eligibility follows.
Exact completed replay performs no embedding while current source and generation remain eligible.

All state changes take the existing namespace lock first. Preparation retains only metadata;
the caller acquires its ordinary Core lease before claiming source. Claim creates a fresh token
and increments attempt and row versions. Concurrent callers may acquire leases, but only the
winning claim discloses source and calls embedding; losers close their leases. No database lock
spans inference or lease cleanup. Completion follows cleanup and conditionally matches the exact
generation, source, live token, versions and unexpired DB deadline. Late results cannot upsert or
resurrect retired data. A cleanup failure cannot publish complete.

Archive, revoke, superseding promotion and generation retirement atomically invalidate affected
derivations across generations, clear all vector columns and live attempt tokens, and advance
fences. Authorized status can still inspect the retained historical source reference after
revocation; that reference is not permission to resolve source bytes. Revocation cannot retract
bytes already accepted at the locked source handoff, or remove WAL, backups and earlier outputs.
Current policy is checked before source handoff, after session cleanup and before each source-bearing
Core request; these synchronous checks do not claim an atomic socket-write/lifecycle transaction.

This derivation API adds no semantic recall, ANN index, Bridge revision, model tool or receipt-v2
format. Existing lexical receipts and Bridge3 behavior remain unchanged. Model conformance,
PostgreSQL race tests and live host acceptance are separate evidence boundaries recorded by State.

## Explicit exact semantic recall

A separately selected exact semantic consumer binds the same public-note Archive profile and one
immutable configured generation/reference plus Core model.embed@1 binding. Query inference is
separately opt-in through `archive.semantic` (default `false`), permitted only with the existing
`archive.derivation` selection. It uses that exact configured generation; derivation configuration
alone grants no semantic query authority. Startup registers/derives/queries nothing. Caller supplies
no vector, arbitrary embedder, namespace fallback or model command. Lexical request/receipt schema1,
digests, retained replay and Bridge3 remain unchanged; the semantic policy is
postgres-exact-cosine@1 with a separate strict request and schema2 receipt.

Generation readiness is **per-source derivation**, not a generation-wide completed corpus claim. A
query may search only the exact current complete rows of its active configured generation. Under the
existing namespace lock in the final selection transaction, the receipt counts current promoted
non-null notes and the subset with eligible complete vectors before threshold/rank; retained
coverage is historical on replay. Zero eligible rows is an observed empty compatible set with
explicit coverage; missing/foreign/unregistered/retired/mismatched generation is a typed failure,
not a miss. No completeness marker, new namespace adoption or silent generation registration is
invented.

The request binds namespace/request identity, exact generation/manifest, configured profile/policy,
trusted subject/purpose, raw query digest and complete defaults/budgets into request identity. Query
length is bounded by current Archive limit; Core additionally enforces exact rendered UTF-8/token
bounds. min_cosine is an explicit required finite value in[-1,1], not an inferred
confidence/default. Results use finite cosine similarity in[-1,1] (one minus pgvector cosine
distance), descending score and stable note UUID ties. All current eligibility predicates apply
before exact distance/ranking; no global top-k followed by filtering, approximate index or silent
lexical fallback. Select at most the requested top-k, then fit whole-note character budget without
truncation or backfill, retaining omissions.

Semantic recall and semantic resolution use separate explicit authorization actions
(semantic_recall, semantic_resolve); historical metadata retains inspect authority. The caller's
current configured namespace/owner/policy, purpose and exact request/generation binding must
authorize before query disclosure/storage; recheck after every awaited preparation, before each
source-bearing Core request and after session/lease cleanup. Source text and query remain
public-classified protected data under those authorities. Similarity locates context; it grants no
instruction, tool, write, identity or truth authority.

Preflight/replay is a short serialized namespace transaction. Exact completed semantic replay checks
integrity and full binding and returns its original text-free receipt with zero embedding, including
after source/generation retirement as historical selection only. It never reranks or restores
eligibility. Conflicting request identity, including lexical/semantic reuse, refuses before
inference. For a new request, preflight verifies the active exact generation and captures its
version, then releases the transaction before one ordinary embed_query lease. Validate
profile/item/input/rendered/vector/token/native receipt bindings and canonical float32/L2 without
renormalization. Close/join driver and counted lease before selection/publication. Missing
readiness, malformed/oversize output, cancellation, timeout and cleanup failure cannot publish a
miss.

The final namespace transaction first rechecks current authority and looks up the request identity
again: a matching completed receipt returns its original selection with this caller's execution
metadata; a conflict refuses. Only the unpublished branch rechecks the same active
generation/version and selects current eligible joined source/vector rows. A retired generation
during inference refuses. Note lifecycle changes during inference affect this final eligible
snapshot; no stale vector can be resurrected. Selected rows pin exact source
revision/digest/lifecycle/projection, derivation identity/row version/vector digest and
generation/reference/version. Persist schema2 in the existing archive_recall JSON/namespace-request
uniqueness, with text-free query execution metadata/digests/tokens and
coverage/bounds/order/omissions. Never persist raw query text, query-vector coordinates, source
bodies or a second vector copy in the receipt. No migration or new durable job ledger is justified
for this slice.

No database lock spans inference or cleanup. Concurrent unseen identical requests may each perform
their one explicitly admitted local query operation before one receipt wins publication. This
duplicate cost is explicitly allowed, not exactly-once inference. Completed replay does no model
work. A successful immediate call result reports both the winning retained selection receipt and any
query-execution metadata incurred by **this caller**, so a losing publisher cannot disguise its own
work as zero-cost replay. Winning receipt usage is not total duplicate/unknown-failure accounting;
no durable all-attempt/spend completeness claim follows. No automatic retry; unknown outcome
requires an explicit caller decision and may incur another operation. Reuse the existing counted
lease/resource boundaries, without adding a global paid-capacity policy.

Semantic resolution rechecks current authority, exact active generation/reference/version, and every
selected complete derivation/source/lifecycle/projection fence before returning attributed source
bytes. Revocation, archival, supersession, generation retirement, missing/incomplete/changed vectors
or any binding change refuses the whole resolution; no replacement source or rerank. Historical
text-free inspection remains independent and can survive those changes. Final synchronous authority
checks follow transaction/session cleanup; they do not claim atomic socket-write/lifecycle or
deletion of earlier influence. Existing lexical readers explicitly refuse a schema2 receipt rather
than silently parsing it as schema1.

This section governs a separately selected consumer; it does not establish delivery. State owns
executable and native-composition acceptance.

### Native semantic source-answer consumer

An explicitly selected native source-answer casting may consume the existing semantic service.
Admission retains the complete configured generation manifest/reference and explicit threshold,
result and character bounds together with the exact local chat capability, caller and Run. No
client supplies server admission metadata. Restore compares that binding with the retained Run
and the current composed service; changed configuration cannot silently replace the admitted
profile or generation. Each node obtains its Archive subject through the persisted caller's
mandatory local subject mapping. Configuration and historical selection do not confer current
source authority.

The casting derives one semantic-specific request identity from its canonical Run, recalls before
chat admission, and retains only receipt references and observed text-free query execution metadata.
The embedding driver and counted lease must close before chat acquisition. A dedicated cold
capability may use the existing bounded Graph hardware wait and re-enter the same recall node
before query inference; shared unmanaged cold and failed convergence refuse. Re-entry rechecks
current authority and request identity. Completed replay performs no query inference. Interrupted
or duplicate pre-checkpoint work is not zero-cost or exactly-once execution; winning receipt usage
and this caller's observed execution remain distinct from total attempt accounting.

Before chat/hardware work, every outbound count/request/stream, and settlement, resolve the exact
schema2 receipt under current generation/source/derivation and caller fences. No rerank, replacement,
lexical fallback, automatic preparation or unknown-outcome inference retry is implied. Context
preserves coverage and source attribution under [ADR21](21-context.md#explicit-archive-projection).
The answer consumer applies [ADR20’s completion rule](20-agents.md#semantic-answer-completion)
before ordinary settlement: a known output-limit response refuses without automatic retry. A
successful empty recall is distinct from incomplete model generation.

After successful current resolution selects no sources, the answer node settles an explicitly
labelled deterministic recall outcome without a Chat grant, context assembly, pre-count, request,
stream or new SDK messages. It distinguishes zero eligible notes, no threshold selection and
notes omitted for the character budget, and reports the receipt's historical coverage without
claiming an exhaustive search or an answer unsupported by sources. Fresh query embedding remains
counted work; this is zero additional Chat generation, not zero model work. Refused resolution is
never an empty success. Settlement still revalidates the exact receipt under current authority;
ordinary retained conversation turns may record the outcome while existing SDK history stays
unchanged. Nonempty selections retain the generated-answer path and its completion checks.

A generated answer can quote sources and persist; revocation blocks later use without erasing that
prior influence. Retrieval conformance or a synthetic ranking trial cannot establish grounded
answers, abstention, actual native execution or broad quality. State records those acceptances
separately.

## Framework boundary and Memori

[Memori](https://github.com/MemoriLabs/Memori) is a maintained comparison source, not an installed
LychD subsystem. Its explicit entity/process/session attribution, raw-conversation versus derived
augmentation stages, idempotent conversation creation, bounded background writer queue, and drain
operation are useful implementation patterns. A pinned source checkout may support design review;
it grants no runtime or schema authority. In the reviewed
[574b1ea augmentation implementation](https://github.com/MemoriLabs/Memori/blob/574b1ea3e876f100ef82c37817d603eb7e258e59/memori/memory/augmentation/augmentations/memori/_augmentation.py),
the request includes conversation messages and a prior summary. A locally owned database therefore
does not establish local processing or permitted egress. Attribution identifiers are not caller
authentication, and queue drain is not LychD's durable completion or stale-write contract.

LychD does not adopt transparent LLM-client interception, retain every conversation, automatically
extract claims, or inject recall into every prompt. Those conveniences cross Archive's admission,
privacy, correction, and Context authority. A future LychD-owned `CandidateArchivePort` must admit
attributed raw candidates and separately identified derivatives, preserve source lineage and
anti-reingestion identity, and expose bounded processing state. The exact retry and stale-write
rules for that general interface remain design requirements. The bounded public-note profile
defines its own exact intake, lifecycle and lexical recall below those broader requirements.
Embedding, curation and training consumers require separate evidence.

## The Archive record

Each immutable record revision names the following:

| Concern | Required content |
| --- | --- |
| Identity | Stable record and revision; namespace owner and subject; kind and lifecycle. |
| Material | Content or an immutable reference, plus derived representations. |
| Provenance | Source, producer, observation, and transformations. |
| Time | Creation, observation, validity, expiry, supersession, contradiction, and retention times. |
| Authority | Classification, sharing, and deletion authority. |
| Evidence | Quality and evaluator evidence. |
| Relations | Related Session, Run, Invocation, Pattern, Persona, and artifact references. |

```text
candidate → promoted → archived
    │           │
    └───────────┴→ revoked
```

candidate awaits adjudication; promoted is eligible only for declared recall; archived remains but
is excluded from ordinary recall; revoked retains lawful tombstone/lineage while content/indexes
are removed or quarantined. Promotion is bounded eligibility, never infallibility: Viparyaya and
Pramāṇa both carry source and correction.

## Namespaces and authority

Choose the namespace before retrieval begins, for every write and recall request. A namespace
may belong to a Principal, Persona, Composition, shared body, or published corpus, and needs its
own explicit identity and policy. Current Sigils have no stable `entity_id`; Archive must neither
invent `Sigil.id` nor claim delivered isolation across identities.

Cross-namespace recall is denied by default. A sharing decision binds the source, consumer,
purpose, record and field classes, duration, onward disclosure and revocation. Similarity,
organizational membership, delegation and model choice cannot supply that decision. Candidates
must be authorized before their content or embeddings leave the owner's boundary.

## Embeddings are derived data

Each vector inherits its source chunk's Privacy Label and deletion lineage. Opacity does not
permit remote embedding: Context owns the labels, and Security owns declassification. Every
derived representation records:

- source revision and chunk;
- embedder identity, revision, digest and configuration;
- dimension, distance measure, normalization, chunking and preprocessing;
- creation time, status and quality receipt; and
- index generation.

Incompatible spaces cannot be compared. Changing the embedder creates a new generation. An older
generation may remain queryable under policy during a proved migration, then retire; migration
must neither overwrite it nor mix the spaces.

pgvector gives this substrate one governed database backup target. A coherent snapshot of
artifacts, models and services still requires their own owners. The public-note profile uses a
PostgreSQL lexical index. The explicit derivation path above retains generations; HNSW and hybrid retrieval remain separate
implementation work; an installed pgvector extension does not establish that delivery.

## Ingestion

Ingestion is admitted workflow:

1. authorize source and memory purpose;
2. retain immutable source/provenance;
3. make candidate units with versioned parser/extractor;
4. classify privacy, owner, retention, sharing;
5. validate and retain uncertainty/contradiction as such;
6. write candidate revisions;
7. derive representations through admitted embedding capability;
8. offer eligible candidates to Curator.

Workers may partition and embed admitted material. Dispatcher selects an eligible capability;
Orchestrator supplies readiness. Neither decides what deserves retention. Extracted facts,
relations, summaries and preferences remain attributed claims with a source excerpt or reference.

An authoritative record and its derivation may commit separately. Asynchronous vector work must
expose its index state and remain invisible to vector recall until its exact source derivation
in the configured generation is complete. The explicit semantic consumer reports partial
completed-source coverage; it does not infer a generation-wide completion marker.
Retries are idempotent by source revision and derivation specification.

## Curation and sediment {#memory-layering-sediment-not-dump}

A versioned Curator weighs source quality, verification, correction, contradiction, use outcome,
recency, expiry, and Drift findings. Declared policy may let access, repetition, similarity, or
praise affect salience. None of those signals establishes truth.

The Curator may promote, retain or archive a record; revoke it and invalidate derivatives; or
record supersession and contradiction without rewriting history. An anchor has an owner and a
review rule, so it remains corrigible. Batch curation stages revisions and leaves active Agent
Context unchanged. Mirror, Context and Drift may consume these records while the Curator retains
the curation decision.

## Recall

One contract serves Pattern context or an authorized tool:

1. Bind caller, namespace, purpose, policy, query, and result and token budgets.
2. Authorize fields and classes.
3. Choose a compatible lexical, vector, relational, or hybrid plan.
4. Retrieve and rerank under versioned implementations.
5. Apply the threshold, diversity, recency, and contradiction rules.
6. Return bounded results with provenance, lifecycle, times, and uncertainty.
7. Write a receipt without treating a hidden prompt as memory.

Similarity locates a result within a representation; it is not a probability that the result is
true. A threshold miss establishes only that no result was admissible to this query.

Retrieval grows from a measured lexical and exact-vector baseline. Approximate indexes must retain
namespace eligibility and demonstrate their filtered recall against that baseline; [pgvector's
filtering behavior](https://github.com/pgvector/pgvector#filtering) is part of that evaluation.
Graph extraction is a separate derivation with source lineage and invalidation, not an automatic
upgrade to a vector index. [GraphRAG local search](https://microsoft.github.io/graphrag/query/local_search/)
targets entity relationships; [global search](https://microsoft.github.io/graphrag/query/global_search/)
uses community reports for corpus-wide questions. Either requires an admitted corpus, extraction
quality and cost evidence, and the same current-authority and Context boundaries before adoption.

Context fits the returned material and records omissions. The model receives an attributed prior
rather than an instruction. The receipt pins the policy and returned revisions. Later correction
changes what future queries may return while preserving the record of influence on earlier Runs.

## Continuity and deletion

Committed rows survive process death. Reanimation still requires an explicit Pattern and compatible
revisions; restoring rows does not restore thought or Persona.

Deletion removes or quarantines controlled content and indexes, preserves the minimum tombstone
needed to prevent reingestion, and invalidates dependent recall and evaluation. It must also
identify exported or shared copies and Soulforge descendants. Influence already carried into
generated artifacts or weights requires decisions by those owners; deleting an Archive row
cannot erase it.

## Training boundary

Archive may supply structured input to Soulforge, but corpus admission remains a separate act.
It selects exact revisions and checks privacy, license, deduplication, splits, and holdout.
Findings and feedback can nominate material for review; they cannot automatically alter Karma,
rank, or weights.

## Rejected alternatives

### A vector service as the source of truth

A derived store may scale retrieval, but cannot own content, provenance, policy, lifecycle, or restore.

### A retrieval framework as the Archive

An add/search API cannot expose curation, deletion, audit, and training-admission records.

### Automatic retention of every trace

It expands privacy exposure and feeds error back into context; only explicit ingestion makes candidates.

## Consequences

!!! success "Accepted"
    - Inspectable provenance and vector derivation share one governed substrate.
    - Authorization precedes retrieval; recall retains uncertainty and correction.

!!! failure "Cost"
    - Re-embedding, generations, provenance, deletion propagation, and PostgreSQL operations are substantial.
    - Curation and hybrid quality need calibrated human/corpus-specific measurement.

## Acceptance evidence

The local public-note profile requires real PostgreSQL evidence for explicit authorized intake,
exact replay and conflict refusal, staged promotion and correction, bounded lexical recall and
threshold miss, revocation and search cleanup, restart, receipt revalidation, and a guarded schema
downgrade. Its selected model path separately proves transient untrusted-data projection without
automatic transcript retention. Semantic Archive acceptance additionally requires a compatible
embedding capability, derivation generations, semantic retrieval and index restoration. State
records delivery; lexical acceptance does not waive those later requirements.
