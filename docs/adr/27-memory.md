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
- **Karma-Based Evolution:** Provision of a mechanism to inscribe consecrated outcomes (verified truths) as prioritized semantic context to shift the model’s Bayesian Prior toward success.
- **Agentic Tool Integration:** Manifestation of memory as a dynamically granted tool within the arsenal, rather than a hardcoded context injection.
- **Logical Domain Isolation:** Mandatory support for partitioned vector namespaces to facilitate isolated memory domains for different users, personas, or speculative timelines.
- **Sovereign Retrieval Thresholds:** Implementation of a "Hard Refusal" policy where the machine refuses to guess if retrieval confidence is below a defined mathematical limit.
- **Dimension Locking:** Mandatory sealing of vectors with the active model's signature to prevent drift when swapping embedding providers.
- **Standardized Semantic Schema:** Adoption of a proven third-normal-form (3NF) schema for storing entity facts, process attributes, and knowledge graph triples to ensure interoperability with existing memory protocols.
- **Metabolic Engine Contract:** Memory framework must be integrated as a wrapped substrate driver, not as an autonomous execution loop, preserving Orchestrator and Dispatcher authority.
- **Identity-Scoped Attribution:** Every memory write and recall path must carry an `entity_id` bound to the active Sigil to prevent cross-identity contamination.
- **Curator Loop:** Memory lifecycle must include a periodic curation pass that classifies records into promote/keep/archive/prune classes using explicit quality signals.

## Considered Options

!!! failure "Option 1: Specialized Vector Databases (Qdrant / Milvus / Pinecone)"
    Deploying a dedicated service to manage semantic embeddings.
    - **Cons:** **Logical Disjunction.** External stores introduce the risk of "Sync Drift" where memory and state fall out of alignment during system failures. Managing a secondary stateful service increases the attack surface and fragments the system's atomic **[Snapshot (ADR 07)](./07-snapshots.md)** strategy. Cloud-only providers violate the **[Iron Pact (ADR 00)](./00-license.md)** of local sovereignty.

!!! failure "Option 2: Intrusive Memory Frameworks (Mem0 / Letta)"
    Utilizing high-level frameworks that provide managed episodic memory loops.
    - **Cons:** **Architectural Interference.** These frameworks act as "Intrusive Agents"—they enforce proprietary execution loops that conflict with the system's type-safe **[Graph (ADR 24)](./24-graph.md)** and the physical hardware management of the **[Orchestrator (ADR 23)](./23-orchestrator.md)**.

!!! failure "Option 3: Pipeline-Heavy RAG (Haystack / LlamaIndex)"
    Implementing complex, multi-service ingestion and retrieval pipelines.
    - **Cons:** **Operational Overload.** These systems are designed for distributed enterprise clusters. On a single node, the CPU and RAM tax of their orchestration layers is prohibitive and contradicts the requirement for a lean, sovereign kernel.

!!! success "Option 4: Integrated pgvector Archive + Memori Metabolic Engine"
    Leveraging native `pgvector` inside PostgreSQL and Memori for asynchronous fact/triple extraction, while keeping lifecycle control in LychD.
    - **Pros:**
        - **Substrate Purity:** Memory becomes a logical chamber within the existing database, governed by the same transactional and snapshot laws as the rest of the machine.
        - **Physical Cohesion:** Relational metadata and embeddings exist within the same storage engine, ensuring bit-perfect synchronization.
        - **Metabolic Lift:** Memori solves extraction/deduplication of facts and triples asynchronously, avoiding custom pipeline sprawl.
        - **Standardization:** Pydantic AI’s native `Embedder` remains the runtime embedding contract for reasoning and retrieval.

## Decision Outcome

**Pgvector** is adopted as the definitive storage engine, utilizing the **Memori** framework as the underlying "Memory Fabric." The system adopts Memori’s schema and asynchronous augmentation logic while maintaining absolute control over the execution lifecycle via the LychD Orchestrator.

Memory is treated as sedimented experience rather than mere storage. In cognitive topology, the entirety of the language space and the algorithm of selection/generation functions as the **Chitta** (the conditioned field or "chattering engine"). The database (`pgvector`) is only the physical substrate of this Chitta. The specific vectors, extracted facts, and reinforced traces stored within it are the **Smritis** (recollections). The Archive preserves these stabilized outcomes as layered imprints whose salience changes over time.

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

- **`public` (The State):** Relational data for user state, active extensions, and the **[Codex (ADR 12)](./12-configuration.md)**.
- **`vectors` (The Karma):** The high-dimensional embedding space storing verified thoughts and outcomes organized by namespace.
- **`traces` (The Eye):** Dedicated storage for the machine's reasoning history and observability data.
- **`queue` (The Labor):** The persistence layer for the **[Workers (ADR 14)](./14-workers.md)**, ensuring background labor is transactional with state changes.

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
5. Extracted memory is first written as candidate Karma with provenance and confidence metadata for later curator adjudication.

All ingestion writes are attributed:

- `entity_id` -> active Sigil identity.
- `process_id` -> calling subsystem (e.g., core, extension, simulation branch).

This attribution is mandatory for downstream isolation and pruning.

### 5. The Concept of Karma (The Pattern)

Memory is not a static log; it is a growing crystal of verified truth:

- **Crystallization:** Verified artifacts and interaction traces are inscribed as **Karma**.
- **Bayesian Prior Shift:** This Karma is injected into the working memory of subsequent reasoning rituals, shifting the machine's internal probability distribution toward the patterns of behavior previously verified by the Magus.

### 5.1 Memory Layering (Sediment, Not Dump)

The Archive is managed as a layered substrate:

- **Active fluctuations:** transient traces and branch artifacts produced during live reasoning and simulation.
- **Stabilized outcomes (Karma):** verified results promoted for future reuse.
- **Deep impressions (Anchored facts):** policy-protected or identity-critical records that should resist decay.
- **Decay state:** salience metadata (`last_accessed`, reinforcement counters, confidence) used to cool, archive, or prune low-signal records.

Reinforcement creates deep grooves in the substrate. Retrieval weight therefore approximates impression strength, not just recency.

### 6. The Pattern of Reanimation

The primary function of the Phylactery is to house the **Pattern** of the machine—the immutable record of its state:

- **Substrate Independence:** While inference engines are ephemeral processors, the Phylactery is the soul.
- **Instant Reanimation:** If the system substrate is moved or rebuilt, the state preserved in the chambers allows for an instantaneous reanimation, restoring the Daemon’s memory, persona, and active **[Graph (ADR 24)](./24-graph.md)** tasks exactly as they were.

### 7. The Retrieval Lens (The Granted Tool)

Memory is manifested as a dynamic power granted to an **[Agent (ADR 20)](./20-agents.md)** by the **[Dispatcher (ADR 22)](./22-dispatcher.md)**:

- **The Grant:** A `query_archive()` tool is injected into the arsenal only when the required Embedding Coven is active.
- **The Mentat Refusal:** If a retrieval ritual returns a similarity score below the **Sovereign Threshold**, the Agent is physically barred from "guessing." It must return a **Hard Refusal**: *"The Archive contains no truth regarding this intent."*
- **Sigil Scope:** Retrieval MUST include `entity_id` scoping (or explicit policy-authorized shared scope) so one identity cannot read another identity’s Karma.

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
- Consistency and contradiction checks (new claims that conflict with high-signal anchored facts are quarantined).
- Identity relevance (facts weakly tied to current Sigil scope are down-ranked).

Lifecycle classes:

- **Promote:** high-signal, stable facts eligible for Mirror prior hydration.
- **Keep:** useful working memory retained in hot storage.
- **Archive:** low-use but potentially useful memory moved to cold scope.
- **Prune:** low-signal, stale, or contradictory noise removed.

Anchors override decay and prune by policy. This preserves core identity truths while preventing semantic drift from conversational debris and simulates non-decaying core imprints within an otherwise metabolic memory system.

The Curator therefore manages sedimentation, not only deletion: it governs how experience cools from active fluctuation into reusable Karma, anchored fact, cold archive, or discard.

## Consequences

!!! success "Positive"
    - **Atomic Stability:** The entire state of the machine (State, Memory, and Work) is captured in a single, consistent snapshot of the database directory.
    - **Sovereign Extensibility:** New memory strategies can be implemented as Extensions that manipulate the existing chambers without requiring new infrastructure.
    - **Physical Purity:** By rejecting intrusive external frameworks, absolute control over execution loops and hardware utilization is maintained.
    - **Truth Integrity:** The Mentat Refusal ensures that reasoning is always grounded in verified or high-confidence data.

!!! failure "Negative"
    - **Index Build Pressure:** Large-scale ingestion generates significant I/O pressure when rebuilding HNSW indexes, potentially impacting real-time performance.
    - **Dimensional Complexity:** Determining optimal chunk overlaps and vector dimensions remains a manual optimization task for the Magus to ensure retrieval precision.
