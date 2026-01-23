---
title: 24. Memory
icon: material/brain
---

# :material-brain: 24. Memory: The Archive

!!! abstract "Context and Problem Statement"
    An Agent without long-term memory is restricted to the volatile context window of a single request, preventing the accumulation of historical wisdom or the refinement of behavioral instinct. Traditional Vector Database solutions often introduce "Logic Sync Drift," where relational metadata in the primary database becomes inconsistent with high-dimensional vector states following system failures or partial restores. Furthermore, intrusive memory frameworks typically enforce proprietary execution loops that hijack agentic autonomy and ignore local hardware constraints. To achieve self-directed evolution, the system requires a unified memory strategy that provides enterprise-grade retrieval while maintaining a sovereign, single-node infrastructure and ensuring the persistent "Self" survives across reanimations.

## Requirements

- **Unified Substrate Sovereignty:** Mandatory integration of high-dimensional storage within the primary database to ensure atomic backups and eliminate the operational complexity of external stateful services.
- **Anatomical Partitioning:** Mandatory division of the database into logical chambers (schemas) to isolate Relational State, Vector Karma, System Traces, and Task Queues.
- **Standardized Embedding Interface:** Adoption of a unified API for generating vectors across pluggable local and remote providers.
- **Capability-Driven Intelligence:** Treatment of text-to-vector conversion as a first-class functional **Capability**, allowing the machine to manifest specialized hardware covens for heavy ingestion tasks.
- **Asynchronous Ingestion Rituals:** Offloading of document partitioning and embedding to background labor to prevent blocking the primary cognitive reasoning loop.
- **Karma-Based Evolution:** Provision of a mechanism to inscribe consecrated outcomes (verified truths) as prioritized semantic context to shift the model’s Bayesian Prior toward success.
- **Agentic Tool Integration:** Manifestation of memory as a dynamically granted **Tool** within the Agentic Arsenal, rather than a hardcoded context injection.
- **Logical Domain Isolation:** Mandatory support for partitioned vector namespaces to facilitate isolated memory domains for different users, personas, or speculative timelines.

## Considered Options

!!! failure "Option 1: Specialized Vector Databases (Qdrant / Milvus / Pinecone)"
    Deploying a dedicated service to manage embeddings.
    - **Cons:** **Logical Disjunction.** External stores introduce the risk of "Sync Drift" where memory and state fall out of alignment. Managing a secondary stateful service increases the attack surface and fragments the system's atomic **[Snapshot (07)](07-snapshots.md)** strategy. Cloud-only providers violate the **[Iron Pact (00)](00-license.md)** of local sovereignty.

!!! failure "Option 2: Intrusive Memory Frameworks (Letta / Mem0)"
    Utilizing high-level frameworks that provide managed episodic memory and long-term state loops.
    - **Cons:** **Architectural Interference.** These frameworks act as "Intrusive Agents"—they enforce proprietary execution loops that conflict with the system's type-safe cortex and the physical hardware management of the **[Orchestrator (21)](21-orchestrator.md)**.

!!! failure "Option 3: Pipeline-Heavy RAG (Haystack / LlamaIndex)"
    Implementing complex, multi-service ingestion and retrieval pipelines.
    - **Cons:** **Operational Overload.** These systems are designed for distributed enterprise clusters. On a single node, the CPU and RAM tax of their orchestration layers is prohibitive and contradicts the requirement for a lean, sovereign kernel.

!!! success "Option 4: Integrated Postgres (pgvector) + Pydantic AI"
    Leveraging the native vector extension within the Phylactery chambers coupled with a standardized embedder interface.
    - **Pros:**
        - **Substrate Purity:** Memory becomes a logical chamber within the database, governed by the same transactional and snapshot laws as the rest of the machine.
        - **Physical Cohesion:** Relational metadata and high-dimensional embeddings exist within the same storage engine, ensuring bit-perfect synchronization.
        - **Standardization:** Utilizes Pydantic AI’s native `Embedder` class, making memory perfectly compatible with the system's reasoning cortex.

## Decision Outcome

**Pgvector** is adopted as the definitive storage engine for the Archive. The database, referred to as the **Phylactery**, serves as the metaphysical anchor of the Lich, separating the permanent storage of memory from the pluggable logic of its creation.

### 1. The Anatomy of Memory (The Chambers)

To maintain organizational and transactional purity, the Phylactery is divided into four sacred chambers:

1. **`public` (The State):** Relational data for user state, active extensions, and the **[Codex (12)](12-configuration.md)**.
2. **`vectors` (The Karma):** The high-dimensional embedding space storing verified thoughts and outcomes organized by namespace.
3. **`traces` (The Eye):** Dedicated storage for the machine's reasoning history and observability data.
4. **`queue` (The Labor):** The persistence layer for the **[Workers (14)](14-workers.md)**, ensuring background labor is transactional with state changes.

### 2. The Standardized Embedding Pipeline

The system adopts the Pydantic AI **`Embedder`** class as its primary interface.

- **The Capability:** Embedding is treated as a functional **Capability**. It is provided by specialized **[Runes (08)](08-containers.md)** (e.g., `sentence-transformers`) within an Embedding Coven.
- **Local Sovereignty:** The system defaults to the `SentenceTransformerEmbeddingModel` for local Runes, ensuring sensitive data never leaves the Sepulcher.
- **Querying:** `embed_query()` is utilized for real-time semantic search and retrieval.
- **Inscription:** `embed_documents()` is used by background ghouls to process artifacts into vectorized outcomes.

### 3. The Learning Ritual (Ingestion)

Learning is an orchestrated background ritual that separates the storage (the database) from the compute (the model).

- **The Labor:** A background **[Ghoul (14)](14-workers.md)** partitions text and identifies the need for the `embedding` capability. It negotiates with the **[Orchestrator (21)](21-orchestrator.md)** to manifest the required Coven.
- **The Inscription:** The Ghoul generates vectors and performs a bulk insert into the `vectors` chamber, updating HNSW indexes for sub-second concept-based retrieval.
- **The Seal of Provenance:** Every summary generated by the **Smith (27)** must be inscribed with a SHA-256 hash of its source document.
- **The Mentat Refusal:** If a retrieval ritual returns a similarity score below the **Sovereign Threshold**, the Agent is physically barred from "guessing." It must return a **Hard Refusal**: *"The Archive contains no truth regarding this intent."*


### 4. The Concept of Karma (The Pattern)

Memory is not a static log; it is a growing crystal of verified truth.

- **Crystallization:** Verified artifacts and consecrated choices from the **[Creation Workflow (16)](16-creation.md)** are inscribed as **Karma**.
- **Bayesian Prior Shift:** This Karma is injected into the working memory of subsequent reasoning rituals, shifting the machine's internal probability distribution toward the patterns of behavior previously verified by the Magus.

### 5. The Pattern of Reanimation

The primary function of the Phylactery is to house the **Pattern** of the Lich—the immutable record of its state.

- **Substrate Independence:** While inference engines are ephemeral processors, the Phylactery is the soul.
- **Instant Reanimation:** If the system substrate is moved or rebuilt, the state preserved in the chambers allows for an instantaneous reanimation, restoring the Daemon’s memory, persona, and active **[Graph (22)](22-graph.md)** tasks exactly as they were.

### 6. The Retrieval Lens (The Granted Tool)

Memory is manifested as a dynamic power granted to an **[Agent (19)](19-agents.md)** by the **[Dispatcher (20)](20-dispatcher.md)**.

- **The Grant:** A `query_archive(query, domain_id)` tool is injected into the arsenal only when the required Embedding Coven is active.
- **The Execution:** Calling this tool triggers high-priority intent resolution. The query is embedded on-the-fly, and the Phylactery performs a similarity search, returning the relevant "Karma" as a structured context block.

### 7. Algorithmic Memory Evolution

The Archive is a programmable space. Extensions can modify the "Retrieval Rites" of the Daemon:

- **Index Rites:** Extensions register background **[Ghouls (14)](14-workers.md)** to perform alternative indexing (e.g., Knowledge Graphs or Hybrid search).
- **Tool Injection:** Developers can register new tools that utilize the **`Embedder`** interface to query the database in novel ways, which are then distributed to the Agent's arsenal via the **[Dispatcher (20)](20-dispatcher.md)**.
- **Substrate Agnosticism:** By utilizing the Pydantic AI **`Embedder`** class, the retrieval logic remains decoupled from the specific embedding model, allowing the system to swap local for cloud providers (or vice-versa) based on the **[Sovereignty Wall](20-dispatcher.md)**.

### Consequences

!!! success "Positive"
    - **Atomic Stability:** The entire state of the machine (State, Memory, and Work) is captured in a single, consistent snapshot of the database directory.
    - **Sovereign Extensibility:** New memory strategies can be implemented as Extensions that manipulate the existing chambers without requiring new infrastructure.
    - **Physical Purity:** By rejecting intrusive external frameworks, LychD maintains absolute control over its own execution loops and hardware utilization.

!!! failure "Negative"
    - **Index Build Pressure:** Large-scale ingestion generates significant I/O pressure when rebuilding HNSW indexes, potentially impacting real-time performance.
    - **Dimensional Complexity:** Determining optimal chunk overlaps and vector dimensions remains a manual optimization task for the Magus to ensure retrieval precision.
