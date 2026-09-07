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
    Current material includes a narrow Karma row only. `CandidateArchivePort`, intake adapters,
    processing state, production PostgreSQL Archive, runtime ingestion, namespace authorization,
    promotion, embedding/retrieval/index, Curator, and non-empty Karma context are not delivered.
    State owns the boundary.

## Framework boundary and Memori

[Memori](https://github.com/MemoriLabs/Memori) is a maintained comparison source, not an installed
LychD subsystem. Its explicit entity/process/session attribution, raw-conversation versus derived
augmentation stages, idempotent conversation creation, bounded background writer queue, and drain
operation are useful implementation patterns. A pinned source checkout may support design review;
it grants no runtime or schema authority.

LychD does not adopt transparent LLM-client interception, retain every conversation, automatically
extract claims, or inject recall into every prompt. Those conveniences cross Archive's admission,
privacy, correction, and Context authority. A future LychD-owned `CandidateArchivePort` must admit
attributed raw candidates and separately identified derivatives, preserve source lineage and
anti-reingestion identity, and expose bounded processing state. The exact retry and stale-write
rules remain design requirements. Embeddings, recall, curation, promotion, RAG injection, and
training remain later consumers with their own evidence.

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

Every write and recall request names its namespace before retrieval begins. A namespace may
belong to a Principal, Persona, Composition, shared body or published corpus; each has an explicit
identity and policy. Current Sigils lack a stable `entity_id`. Archive must not invent `Sigil.id`
or claim delivered isolation across identities.

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
artifacts, models and services still requires their own owners. Schema deployment, HNSW and
lexical or hybrid indexes remain implementation work, not current delivery.

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
expose its index state and remain invisible to vector recall until its generation is complete.
Retries are idempotent by source revision and derivation specification.

## Curation and sediment {#memory-layering-sediment-not-dump}

A versioned Curator weighs source quality, verification, correction, contradiction, use outcome,
recency, expiry and Riddle findings. Access, repetition, similarity and praise can affect salience
only under declared policy; they do not establish truth.

The Curator may promote, retain or archive a record; revoke it and invalidate derivatives; or
record supersession and contradiction without rewriting history. An anchor has an owner and a
review rule, so it remains corrigible. Batch curation stages revisions and leaves active Agent
Context unchanged. Mirror, Context and Riddle may consume these records while the Curator retains
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

Archive can supply structured input to Soulforge. Corpus admission separately selects exact
revisions and checks privacy, license, deduplication, splits and holdout. Findings and feedback
may nominate material for review, but cannot automatically change Karma, rank or weights.

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

Archive intake remains **Designed**: there is no candidate-admission port or volatile adapter.
Partial acceptance requires one bounded class proving authorized ingestion, provenance candidate,
compatible embedding, namespace recall, threshold miss, correction, staged promotion,
deletion/index cleanup, restoration, and reproducible receipt. State records delivery.
