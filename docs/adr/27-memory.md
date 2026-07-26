---
title: 27. Memory
icon: material/brain
---

# :material-brain: 27. Memory: The Archive

!!! abstract "Context and Problem Statement"
    Reasoning within a sovereign system is physically restricted by the volatile context window of active model requests, preventing the accumulation of historical experience or the refinement of behavioral instinct. Reliance on fragmented, retrieval-less reasoning creates a "Cognitive Ceiling" where the machine fails to maintain systemic coherence over long-term strategic tasks. Furthermore, the adoption of external vector database solutions introduces architectural disjunction and the risk of "Logic Sync Drift," where relational metadata and high-dimensional states fall out of alignment during system restores or snapshots. A unified memory strategy is necessary to provide high-fidelity recall and self-directed evolution while maintaining a sovereign, single-node infrastructure.

## Requirements

- **Unified Substrate:** Mandatory integration of high-dimensional storage within the primary relational database to ensure atomic backups and eliminate operational complexity.
- **Anatomical Partitioning:** Mandatory division of the database into logical chambers (schemas) to isolate Relational State, Vector Karma, System Traces, and Task Queues.
- **Standardized Embedding Interface:** Adoption of a unified API for generating vectors across pluggable local and remote providers, utilizing the Pydantic AI `Embedder` class.
- **Capability-Driven Recall:** Treatment of text-to-vector conversion as a functional capability, allowing the machine to manifest specialized hardware containers for heavy ingestion rituals.
- **Asynchronous Ingestion:** Offloading of document partitioning and embedding to background labor to prevent blocking the primary cognitive reasoning loop.
- **Karma-Based Evolution:** Provision of a mechanism to inscribe attributed, consecrated outcomes
  as prioritized semantic context to shift the model's Bayesian Prior toward patterns the Magus
  selected. Consecration preserves provenance and judgment; it does not make memory infallible.
- **Agentic Tool Integration:** Manifestation of memory as a dynamically granted tool within the arsenal, rather than a hardcoded context injection.
- **Logical Domain Isolation:** Mandatory support for partitioned vector namespaces to facilitate isolated memory domains for different users, personas, or speculative timelines.
- **Sovereign Retrieval Thresholds:** Implementation of a "Hard Refusal" policy where the machine refuses to guess if retrieval confidence is below a defined mathematical limit.
- **Dimension Locking:** Mandatory sealing of vectors with the active model's signature to prevent drift when swapping embedding providers.
- **Standardized Semantic Schema:** Adoption of a proven third-normal-form (3NF) schema for storing entity facts, process attributes, and knowledge graph triples to ensure interoperability with existing memory protocols.
- **Metabolic Engine Contract:** Memory framework must be integrated as a wrapped substrate driver, not as an autonomous execution loop, preserving Orchestrator and Dispatcher authority.
- **Identity-Scoped Attribution:** Every memory write and recall path must carry an `entity_id` bound to the active Sigil to prevent cross-identity contamination.
- **Consent-Governed Sharing:** Expertise, priors, and reinforced memory remain owned by the Sigil that cultivated them unless an explicit shared-memory or publication policy grants broader access.
- **Curator Loop:** Memory lifecycle must include a periodic curation pass that classifies records into promote/keep/archive/prune classes using explicit quality signals.
- **Training-Grade Harvestability:** Stored memory must be directly queryable as structured, attributed records (facts, triples, provenance, identity/role/workflow vertex) so the **[Soulforge (ADR 33)](./33-training.md)** can mine consecrated Karma into training manifests via direct `SELECT`/`JOIN` — never by scraping a recall API.

## Considered Options

!!! failure "Option 1: Specialized Vector Databases (Qdrant / Milvus / Pinecone)"
    Deploying a dedicated service to manage semantic embeddings.
    - **Cons:** **Logical Disjunction.** External stores introduce the risk of "Sync Drift" where memory and state fall out of alignment during system failures. Managing a secondary stateful service increases the attack surface and fragments the system's atomic **[Snapshot (ADR 07)](./07-snapshots.md)** strategy. Cloud-only providers violate the **[Iron Pact (ADR 00)](./00-license.md)** of local sovereignty.

!!! failure "Option 2: Retrieval-Layer Frameworks (Mem0 / Letta)"
    Adopting a high-level memory framework as the system of record, storing and recalling experience through its `add()` / `search()` surface.

    !!! note "2026 reassessment — rejected on fit, not capability"
        Earlier drafts rejected Mem0 as cloud-bound and Neo4j-dependent. **Both objections are now stale:** Mem0 v3 runs fully local on `pgvector` (no graph database, no managed cloud required), and its single-pass ADD-only algorithm posts strong recall benchmarks (LoCoMo, LongMemEval). *As a retrieval layer, Mem0 is a genuine contender.* It is declined here purely on architectural fit.

    - **Cons:** **The substrate is not yours to mine.** Mem0 owns its records behind an `add()` / `search()` API, and its v3 schema is shaped for internal multi-signal *retrieval* (vector + BM25 + opaque entity-linking), not for external harvesting. But LychD does not consume memory by recall alone — the **[Soulforge (ADR 33)](./33-training.md)** *mines* it: a Ghoul must `SELECT` stabilized Karma by `entity_id`, confidence, reinforcement, and its identity/role/workflow vertex to weave a training manifest. A retrieval black box forces us to reconstruct the structured facts and triples it deliberately hides, and assumes the extraction/dedup/decay lifecycle loop that LychD reserves for its own **[Orchestrator (ADR 23)](./23-orchestrator.md)**, **[Dispatcher (ADR 22)](./22-dispatcher.md)**, and Curator. The retrieval win is real; it just is not the axis LychD is optimizing.

!!! failure "Option 3: Pipeline-Heavy RAG (Haystack / LlamaIndex)"
    Implementing complex, multi-service ingestion and retrieval pipelines.
    - **Cons:** **Operational Overload.** These systems are designed for distributed enterprise clusters. On a single node, the CPU and RAM tax of their orchestration layers is prohibitive and contradicts the requirement for a lean, sovereign kernel.

!!! success "Option 4: Integrated pgvector Archive + Memori Metabolic Engine"
    Leveraging native `pgvector` inside PostgreSQL and Memori for asynchronous fact/triple extraction, while keeping lifecycle control in LychD.
    - **Pros:**
        - **Substrate Purity:** Memory becomes a logical chamber within the existing database, governed by the same transactional and snapshot laws as the rest of the machine.
        - **Atomic Session Cohesion:** Memori's SQLAlchemy adapter binds to the *same async session* as the Vessel, so a memory write commits inside the same transaction and lands in the same Phylactery snapshot — not merely the same engine reached over a side connection. This is what makes **[Reanimation (ADR 07)](./07-snapshots.md)** bit-perfect.
        - **Harvestable Karma:** Memori writes an inspectable 3NF schema (`memori_entity_fact`, `memori_knowledge_graph` triples, process attribution) directly into our own tables. The Soulforge Crucible can `SELECT`/`JOIN` consecrated Karma with its semantic vertex intact — memory is feedstock the **[Forge (ADR 33)](./33-training.md)** reads, not a recall API it must scrape.
        - **Metabolic Lift:** Memori solves extraction/deduplication of facts and triples asynchronously, avoiding custom pipeline sprawl, while LychD retains Curator, decay, and lifecycle authority.
        - **Standardization:** Pydantic AI’s native `Embedder` remains the runtime embedding contract for reasoning and retrieval.

## Decision Outcome

**Pgvector** is adopted as the definitive storage engine, utilizing the **Memori** framework as the underlying "Memory Fabric." The system adopts Memori’s schema and asynchronous augmentation logic while maintaining absolute control over the execution lifecycle via the LychD Orchestrator.

The deciding criterion is **substrate ownership, not retrieval accuracy**. A pure-recall workload would now justify either framework — Mem0 v3's local retrieval is competitive. But because the **[Soulforge (ADR 33)](./33-training.md)** transmutes verified Karma into LoRA weights, memory must be a structured, attributed substrate LychD owns and mines in SQL, not a retrieval service it queries. Memori writes that substrate into our own session and exposes its facts and triples as plain tables; a retrieval-layer framework would keep them behind its API. That single difference — *mined, not recalled* — is why Memori is selected.

Memory is treated as sedimented experience rather than mere storage. Structured events capture the
instrumented portion of **the Flux**—the project correspondence for active **Vṛttis**—through the
agentic graph: model calls, tool use, retries, routing choices, OS pressure, protocol handshakes,
and worker outcomes.

Retention does not itself perform remembering. A retained, attributable record with future recall
value is a candidate **Seed** (**Bīja**): conditioning that still has the power to shape a later
Flux. Retrieval finds a candidate and **[Context](21-context.md)** makes the selected form
available; **the Spirit completes ReCall** (**Smṛti**) only when that form becomes active in
present cognition again. Over time, stored Karma reveals semantic relationships and repeated
return deepens conditioning (**Saṃskāra**). **[Mirror](32-identity.md)** reflects those
relationships into identities.

Valid evidence enters through direct measurement, inference, and trusted testimony (**Pramāṇa**: measured, reasoned, witnessed). The critical architectural implication is that memory is faithful to its source, not to truth. A groove carved by valid evidence re-surfaces as reliable instinct. A groove carved by misconception (**Viparyaya**) re-surfaces as confident bias — with identical authority, identical fluency, and no internal signal that it is wrong. This is why identity-scoped isolation and the Curator Loop are non-negotiable: without active curation, an Archive that accumulates freely drifts toward groove-dominance, surfacing old wrong-knowing as though it were hard-won truth. The full cognitive map is described in **[The Lich](../sepulcher/lich/index.md)**.

This boundary is social as well as technical. If a person's history, expertise, and reinforced priors are stored in their Phylactery, that substrate cannot be treated as automatically owned by an employer, customer, or platform. Organizational sharing must occur by explicit policy, consent, or publication surface — never by silent assimilation into a central memory.

### 0. Build-vs-Buy Posture (Glue, Not Surrender)

LychD adopts a hybrid strategy:

- **Buy the hard metabolism:** fact/triple extraction and graph normalization from Memori.
- **Keep sovereign control:** orchestration, queueing, policy, identity, and tool binding remain first-class LychD concerns.
- **Integration shape:** Memori is wrapped as a substrate driver behind LychD interfaces (not exposed as a black-box runtime policy engine).

This resolves the "build vs glue" crossroads while preserving ADR boundaries.

### 1. Substrate Bootstrap (The Inscription)

At Phylactery initialization:

1. Ensure Postgres extension `pgvector` is enabled.
2. Initialize Memori against the same SQLAlchemy/Session substrate used by the Vessel.
3. Execute Memori storage build/migration to ensure core tables (including `memori_entity_fact` and `memori_knowledge_graph`) exist in the unified substrate.

Failure to satisfy `pgvector` capability is a hard startup error for memory-enabled deployments.

### 2. The Anatomy of Memory (Chambers)

To maintain organizational and transactional purity, the Phylactery is divided into four sacred chambers:

!!! warning "Target topology"
    The first migration currently creates the seven core tables and pgvector extension on the
    configured default schema/search path; SAQ likewise owns default `saq_*` tables. Dedicated
    `vectors`, `traces`, and `queue` schemas, Memori bootstrap, and transactional memory ingestion
    are not part of the implemented foundation yet.

- **`public` (The State):** Relational data for user state, active extensions, and the **[Codex (ADR 12)](./12-configuration.md)**.
- **`vectors` (The Karma):** The high-dimensional embedding space storing verified thoughts and outcomes organized by namespace.
- **`traces` (The Eye):** Dedicated storage for the machine's reasoning history and observability data.
- **`queue` (The Labor, planned isolation):** The future schema/role boundary for
  **[Workers (ADR 14)](./14-workers.md)**. V1 SAQ uses its default tables and a compensated,
  reconciled run-row/enqueue split rather than a shared transaction.

### 3. The Standardized Embedding Pipeline

The system adopts the Pydantic AI **`Embedder`** class as its primary interface.

- **The Capability:** Embedding is treated as a functional capability. It is provided by specialized **[containers (ADR 08)](./08-containers.md)** (e.g., `sentence-transformers`) within an Embedding Coven.
- **Local Preference:** The system defaults to local embedding containers to ensure sensitive data never leaves the Sepulcher.
- **Querying:** `embed_query()` is utilized for real-time semantic search and retrieval.
- **Inscription:** `embed_documents()` is used by background labor to process artifacts into vectorized outcomes.

### 4. The Learning Ritual (Ingestion)

Learning is an orchestrated background ritual that separates the storage (the database) from the compute (the model):

1. A background **[Ghoul (ADR 14)](./14-workers.md)** partitions text and identifies the need for the `embedding` capability.
2. The Advanced Augmentation logic (inspired by Memori) extracts entities, relationships, and facts.
3. The **[Orchestrator (ADR 23)](./23-orchestrator.md)** manifests the required embedding service.
4. The Ghoul generates vectors and performs an atomic bulk insert into the `vectors` chamber, updating HNSW indexes for sub-second concept-based retrieval.
5. Extracted memory is first written as a candidate record with provenance and confidence metadata for later curator adjudication.

All ingestion writes are attributed:

- `entity_id` -> active Sigil identity.
- `process_id` -> calling subsystem (e.g., core, extension, simulation branch).

This attribution is mandatory for downstream isolation and pruning.

### 5. The Concept of Karma (The Stored Past)

Memory is not a static log; it is a sedimentation process:

- **Retention:** Structured events may be retained as candidate **Seeds** when they carry future
  recall value; a stored record is not yet the active ReCall.
- **Stored Past:** Verified, corrected, or consecrated outcomes become **Karma**: the past available for future reasoning rather than a raw event stream.
- **Prior Shift:** Retrieval may select relevant Karma and Context may make it available to a
  subsequent reasoning ritual; the Spirit ReCalls when that retained form begins shaping present
  Flux.
- **Identity Reflection:** **[Mirror](32-identity.md)** reflects semantic relationships among
  memory records into identities, while **[Context](21-context.md)** carries only the records and
  bindings authorized for the active Invocation.

### 5.1 Memory Layering (Sediment, Not Dump)

The Archive is managed as a layered substrate:

- **Active fluctuations:** transient traces and branch artifacts produced during live reasoning and simulation.
- **Stabilized outcomes (Karma):** verified results promoted for future reuse.
- **Deep impressions (Anchored facts):** policy-protected or identity-critical records that should resist decay.
- **Decay state:** salience metadata (`last_accessed`, reinforcement counters, confidence) used to cool, archive, or prune low-value records.

Reinforcement creates deep grooves in the substrate. Retrieval weight therefore approximates impression strength, not just recency.

### 6. The Continuity Pattern of Reanimation

The primary function of the Phylactery is to house the **continuity pattern** of the machine: the
durable records from which supported state can be reconstituted:

- **Substrate Independence:** Inference engines are ephemeral processors; the Phylactery is the
  continuity anchor and candidate seed-vault. It is neither a person's soul nor the whole Lich.
- **Declared Reanimation:** If the system substrate is moved or rebuilt, the state preserved in the chambers allows the Daemon to restore memory, persona, queues, and active **[Graph (ADR 24)](./24-graph.md)** tasks from their last valid committed boundaries. Volatile breath is reconstructed or abandoned according to graph, worker, and policy law.

### 7. The Retrieval Lens (The Granted Tool)

Memory is manifested as a dynamic power granted to an **[Agent (ADR 20)](./20-agents.md)** by the **[Dispatcher (ADR 22)](./22-dispatcher.md)**:

- **The Grant:** A `query_archive()` tool is injected into the arsenal only when the required Embedding Coven is active.
- **The Hard Refusal:** If a retrieval ritual returns a similarity score below the **Sovereign Threshold**, the Agent is physically barred from "guessing." It must return a hard refusal: *"The Archive contains no truth regarding this intent."*
- **Sigil Scope:** Retrieval MUST include `entity_id` scoping (or explicit policy-authorized shared scope) so one identity cannot read another identity’s Karma.
- **Shared Scope Is Exceptional:** Cross-persona or cross-organization recall is a deliberate grant, not the default shape of memory. The system begins from sovereignty and moves outward only by consent.
- **Cross-Identity Recall Is Hard-Gated:** Cross-identity recall is a hard-gated class under the **[Codex (ADR 12)](./12-configuration.md)** whose grant record is future work. Until that grant record is defined, **[Archive Gating (ADR 38)](./38-iam.md)** admits no exception, and every recall stays scoped to the active Sigil's `entity_id`.

### 8. Algorithmic Memory Evolution

The Archive is a programmable space. Extensions and Agents can modify the "Retrieval Rites" of the Daemon:

- **Schema Extensions:** Extensions can define their own relational tables and Alembic migrations within the user's namespace, allowing the mind to structure its own specialized memories.
- **Dimension Lock:** Every vector is sealed with a **Model Slug**. The retrieval tool filters results by the active embedding provider. If the Magus swaps embedders, a ritual triggers background re-indexing to prevent "Dimension Drift."
- **Reaper Coupling:** Pruning signals derive from access metadata (`last_accessed`, reinforcement counters), allowing the **[Branch Reaper (31)](31-simulation.md)** to purge low-signal memory without harming anchored knowledge.
- **Decay Semantics:** Decay is modeled as loss of salience rather than immediate deletion. Records may be down-ranked or moved to colder scopes before final pruning unless policy requires hard removal.

### 9. The Curator Loop (Good vs Garbage)

Memory curation is a separate background ritual from ingestion:

- **Phase A (Metabolism):** augmentation extracts candidate facts/triples from conversation traces and tool outcomes.
- **Phase B (Curation):** a periodic Curator Ghoul scores and classifies candidates using quality signals.

Quality signals include:

- Recency and repeated reinforcement (`last_accessed`, `mention_count`, successful recalls).
- Confidence and provenance (tool-verified facts outrank free-form claims).
- Consistency and contradiction checks (new claims that conflict with trusted anchored facts are quarantined).
- Identity relevance (facts weakly tied to current Sigil scope are down-ranked).

Lifecycle classes:

- **Promote:** stable, trusted facts eligible for Mirror prior hydration.
- **Keep:** useful working memory retained in hot storage.
- **Archive:** low-use but potentially useful memory moved to cold scope.
- **Prune:** low-signal, stale, or contradictory noise removed.

Anchors override decay and prune by policy. This preserves core identity truths while preventing semantic drift from conversational debris and simulates non-decaying core imprints within an otherwise metabolic memory system.

The Curator therefore manages sedimentation, not only deletion: it governs how experience cools from active fluctuation into reusable Karma, anchored fact, cold archive, or discard.

!!! note "Staged Memory Promotion"
    Curator output is staged and versioned before it becomes a future prior. A live run may write working memory, but batch consolidation should produce inspectable candidates or a new Archive version rather than silently mutating the active context underneath an Agent. Mirror, policy, and Context hydration decide when staged memories become active priors for a later run.

    The staged-promotion boundary is already provided by the `vectors` chamber (**[Persistence (ADR 06)](./06-persistence.md)**): Curator writes are born `speculative`; the Rite of Consecration (**[HitL (ADR 25)](./25-hitl.md)**) alone flips a record to `consecrated`; and the **[Soulforge (ADR 33)](./33-training.md)** mines only consecrated Karma. Staged promotion is therefore a status transition under explicit authority, never a silent overwrite of live memory.

!!! note "Curator Consolidation Is Not Shadow Dreaming"
    Batch consolidation of traces, transcripts, tool outcomes, and HitL feedback belongs to the Archive and Curator loop. Shadow Simulation dreams candidate futures; the Curator distills the verified past into staged memory candidates. Mirror may then decide whether those candidates strengthen the active Sigil's semantic vertex before Context hydrates them as priors.

## Consequences

!!! success "Positive"
    - **Atomic Stability:** The entire state of the machine (State, Memory, and Work) is captured in a single, consistent snapshot of the database directory.
    - **Sovereign Extensibility:** New memory strategies can be implemented as Extensions that manipulate the existing chambers without requiring new infrastructure.
    - **Physical Purity:** By rejecting intrusive external frameworks, absolute control over execution loops and hardware utilization is maintained.
    - **Truth Integrity:** The Hard Refusal ensures that reasoning is always grounded in verified or high-confidence data.

!!! failure "Negative"
    - **Index Build Pressure:** Large-scale ingestion generates significant I/O pressure when rebuilding HNSW indexes, potentially impacting real-time performance.
    - **Dimensional Complexity:** Determining optimal chunk overlaps and vector dimensions remains a manual optimization task for the Magus to ensure retrieval precision.
