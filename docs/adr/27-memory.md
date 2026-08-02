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

LychD adopts PostgreSQL Archive with pgvector-derived indexes behind LychD-owned ports. PostgreSQL
owns authoritative records, lineage, policy, lifecycle, and derivations; frameworks may extract,
embed, rank, or rerank but cannot silently own transaction, migration, curation, sharing, or
training eligibility. Run/Step ledgers, traces, checkpoints, Personas, one-call context, and
Soulforge corpora stay distinct and cite by stable ref.

!!! warning "Delivery boundary"
    Current material includes a narrow Karma row plus an effect-free `CandidateArchivePort` and
    loop-local adapter for attributed raw candidates, attempt-bound derivatives,
    anti-reingestion identities, and finite attempt-fenced processing state. There is no production PostgreSQL adapter, runtime ingestion,
    namespace authorization, promotion law, embedding/retrieval/index, Curator, or non-empty Karma
    context. State owns the boundary.

## Framework boundary and Memori

[Memori](https://github.com/MemoriLabs/Memori) is a maintained comparison source, not an installed
LychD subsystem. Its explicit entity/process/session attribution, raw-conversation versus derived
augmentation stages, idempotent conversation creation, bounded background writer queue, and drain
operation are useful implementation patterns. A pinned source checkout may support design review;
it grants no runtime or schema authority.

LychD does not adopt transparent LLM-client interception, retain every conversation, automatically
extract claims, or inject recall into every prompt. Those conveniences cross Archive's admission,
privacy, correction, and Context authority. The delivered first seam is a narrow LychD-owned
`CandidateArchivePort`: it admits attributed raw candidates and separately identified derivatives,
preserves source lineage and anti-reingestion identity, and exposes bounded processing state.
Retry increments a monotonic attempt; stale settlement and derivatives from an older attempt are
refused. A derivative cannot predate its raw source observation, and ordinary reads expose it only
while its source is `PROCESSING` or `PROCESSED` at that exact current attempt. Retrying or failing
the source therefore hides old derivatives and refuses their idempotent replay. A new current
attempt for the same raw source may replace an older attempt's derivation key with new,
current-attempt output; the key remains permanently bound to that raw-source lineage and cannot
migrate after the old output becomes stale. Stale identity therefore does not permanently poison
the source's semantic retry key. Its
only adapter is volatile, loop-local memory with no runtime wiring. Embeddings, recall, curation,
promotion, RAG injection, and training remain later consumers with their own evidence.

## The Archive record

One immutable revision names stable record/revision, namespace owner/subject, kind/lifecycle,
content or immutable ref, source/producer/observation/transformations, creation-observation-validity-
expiry-supersession-contradiction-retention times, classification/sharing/deletion authority,
quality/evaluator evidence, related Session/Run/Invocation/Pattern/Persona/artifact refs, and
derived representations.

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

Write and recall name namespace before retrieval. A namespace may be Principal, Persona,
Composition, shared body, or published corpus, but id/policy are explicit. Current Sigils lack a
stable entity_id: Archive must not invent Sigil.id or claim delivered cross-identity isolation.
Default is no cross-namespace recall. Sharing identifies source, consumer, purpose, record/field
classes, duration, onward disclosure, revocation. Similarity, organization, delegation, and model
do not grant it. Authorize candidates before content or embeddings leave owner boundary.

## Embeddings are derived data

A vector inherits source chunk Privacy Label and deletion lineage; opacity never authorizes remote
embedding. Context owns labels and Security declassification. Each derived representation records
source revision/chunk, embedder identity/revision/digest/configuration, dimension/distance,
normalization/chunking/preprocessing, creation/status/quality receipt, and index generation.
Incompatible spaces never compare. New embedder creates a new generation; old may remain policy-
queryable during proved migration, then retires, never overwritten/mixed. pgvector makes one
governed DB backup target, not a coherent snapshot of artifacts/models/services. Schemas, HNSW,
lexical/hybrid indexes are deployment work, not current claim.

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

Workers may partition/embed; Dispatcher picks eligible capability and Orchestrator readiness, but
neither decides worth. Extractor facts/relations/summaries/preferences are attributed claims with
source excerpt/ref. Authoritative record and derivation may commit separately: asynchronous vector
work exposes honest index state and stays invisible to vector recall until complete generation;
retry is idempotent by source revision and derivation spec.

## Curation and sediment {#memory-layering-sediment-not-dump}

Versioned Curator considers source quality, verification, correction, contradiction, use outcome,
recency, expiry, and Riddle findings. Access, repetition, similarity, and praise are not truth;
they can affect salience only by declared policy. Curator may promote, retain, archive, revoke and
invalidate derivatives, or relate supersession/contradiction without rewriting history. Anchors have
owner/review rule, not immortality. Batch curation stages revisions and never changes active agent
context. Mirror, Context, and Riddle may use records but do not become Curator.

## Recall

One contract serves Pattern context or authorized tool: bind caller/namespace/purpose/policy/query
and result/token budget; authorize fields/classes; choose compatible lexical/vector/relational/hybrid
plan; retrieve/rerank versionedly; enforce threshold/diversity/recency/contradiction; return bounded
provenance/lifecycle/times/uncertainty; write receipt without hidden prompt as memory. Similarity is
position, not truth probability; threshold miss is no admissible result, not absence from world.
Context fits results and records omissions; model sees attributed prior, not instruction. Receipt
pins policy and returned revisions; later correction supersedes future queries and preserves earlier
Run influence.

## Continuity and deletion

Committed rows survive process death; Reanimation needs explicit Pattern and compatible revisions,
not restored thought or Persona. Deletion removes/quarantines controlled content/indexes, keeps
minimum anti-reingestion tombstone, invalidates dependent recall/evaluation, and identifies exported
or shared copies plus Soulforge descendants. It cannot erase influence in generated artifacts or
weights; those need their own decisions.

## Training boundary

Archive is structured Soulforge input, never corpus by default. Training selects exact revisions
and independently admits privacy/license/dedup/split/holdout. Findings/feedback may nominate
review, never automatic Karma/rank/weight change.

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

The current Partial claim covers only the candidate-admission contract and volatile adapter.
Broader Partial acceptance requires one class proving authorized ingestion, provenance candidate,
compatible embedding, namespace recall, threshold miss, correction, staged promotion,
deletion/index cleanup, restoration, and reproducible receipt. State records delivery.
