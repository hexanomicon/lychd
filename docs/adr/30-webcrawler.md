---
title: 30. Webcrawler
icon: material/spider-thread
---

# :material-spider-thread: 30. Webcrawler: The Scout

!!! abstract "Context and Problem Statement"
    The LychD exists within a hermetic Sepulcher, yet the requirements of **[Assimilation (35)](35-assimilation.md)** and general cognition necessitate the ingestion of external data from the "Forest" (the Internet).

    A strict tradeoff exists: standard HTTP requests are lightweight but blind to the JavaScript-heavy reality of the modern web (SPAs). Conversely, headless browsers offer perfect fidelity but impose a massive "Resource Tax" (RAM/CPU) that can destabilize the primary inference loop. A "One-Size-Fits-All" approach is either too weak to see the truth or too heavy to move swiftly.

## Requirements

- **Tactical Duality:** Implementation of a two-handed approach—a **Skirmisher** (Lightweight/Fast) for static content and a **Siege Engine** (Heavy/Complete) for dynamic applications.
- **Structural Fidelity:** The capability to interpret JavaScript, solve CAPTCHAs, and navigate complex DOMs when necessary.
- **Markdown Transmutation:** Automated conversion of chaotic HTML/CSS into clean, hierarchical Markdown to minimize the **[Context (20)](21-context.md)** token tax.
- **Orchestrated Ingress:** The heavy Siege Engine must be treated as a **[Systemd Quadlet service (08)](08-containers.md)** subject to the **[Orchestrator (22)](23-orchestrator.md)**. It cannot be summoned if the system is under extreme VRAM/RAM pressure (e.g., during Training).
- **Isolation:** Execution of the browser engine within a dedicated, unprivileged container to prevent host-level exploitation via malicious JavaScript.
- **Recursive Utility:** Provision of raw documentation to **[The Smith (35)](35-assimilation.md)** to enable the autonomous construction of new extensions.

## Considered Options

!!! failure "Option 1: Pure Procedural Scraping (HTTPX Only)"
    Relying exclusively on standard Python libraries.

    - **Pros:** Zero resource footprint; sub-second latency.
    - **Cons:** **Functional Blindness.** Fails to render client-side JavaScript (React/Vue). The Agent remains blind to 40% of the modern web, including critical documentation sites that load content dynamically.

!!! failure "Option 2: External Ingestion APIs (Firecrawl / Tavily)"
    Outsourcing the hunt to third-party cloud scrapers.

    - **Pros:** Perfect fidelity; external handling of proxy rotation.
    - **Cons:** **The Breach of Sovereignty.** Violates the **[Iron Pact (00)](00-license.md)**. Sending navigation intents reveals the Magus's interests to a third party. It introduces a subscription capability tax on basic reading.

!!! success "Option 3: The Scout (Dual-Mode)"
    A sovereign extension that wields both a lightweight library and a containerized browser, dynamically selecting the tool based on the target's complexity.

    - **Pros:**
        - **Efficiency:** 90% of requests use the Skirmisher (Zero Cost).
        - **Capability:** The Siege Engine is available for the 10% of hard targets.
        - **Safety:** Heavy browsing is orchestrated, protecting the system from resource exhaustion.

## Decision Outcome

**The Scout** pattern is adopted. The capability is implemented as a specialized extension that manifests two distinct tools for the **[Dispatcher (22)](22-dispatcher.md)**.

### 1. The Skirmisher (The Left Hand)

This is the default mode of interaction. It runs directly within the **[Vessel (11)](11-backend.md)** or **[Ghoul (14)](14-workers.md)** process.

- **Mechanism:** `httpx` (Network) + `trafilatura` (Extraction).
- **Cost:** Negligible RAM/CPU.
- **Use Case:** Reading technical documentation, blogs, RSS feeds, and raw text files.
- **Orchestration:** Ignored. The Agent can wield this tool freely without checking hardware state.

### 2. The Siege Engine (The Right Hand)

This is the heavy artillery. It runs in a dedicated container service (`web.coven`).

- **Mechanism:** Headless Chromium (Playwright) managed by the system.
- **Cost:** High RAM usage (1GB+) and significant CPU spikes.
- **Use Case:** Single Page Applications (SPAs), taking Screenshots for **[Vision (36)](36-vision.md)**, and navigating complex authentication flows.
- **The Internet Airlock (Security):** Browsers executing arbitrary JavaScript are high-risk targets for 0-day exploits. By isolating the Siege Engine in `web.coven`, a malicious website breakout is trapped in an empty shell with **no database credentials** and no mounted user files. The blast radius is zero.
- **Orchestration:** **Subject to the Law.**
    - When an Agent requests `browser_navigate(use_siege=True)`, the **Dispatcher** queries the **Orchestrator**.
    - If the system is performing a high-priority ritual (e.g., **[Soulforge (33)](33-training.md)**), the request is denied or queued to prevent OOM failure taking down other containers.

### 3. The Lens (Transmutation)

Raw HTML is poison to an LLM. The Scout acts as a filter.

- **The Scribe:** Whether gathered by the Skirmisher or the Siege Engine, all content passes through a normalization pipeline.
- **The Output:** Chaotic DOMs are transmuted into structured **Markdown**. Navigation bars, ads, and footers are surgically removed.
- **The Result:** The Agent receives pure semantic meaning, reducing context usage by up to 80% compared to raw HTML.

### 4. Integration with The Laboratory

Data acquired by the Scout is not just ephemeral context; it is material for construction.

- **For The Smith:** When **[The Smith (35)](35-assimilation.md)** encounters an unknown library, it deploys the Scout to ingest the documentation. The resulting Markdown is stored in the **[Lab (13)](13-layout.md)** as a reference manual for code generation.
- **For Memory:** General inquiries are partitioned and inscribed into the **[Archive (27)](27-memory.md)**, allowing the Lych to "remember" the internet without re-crawling it.

## Consequences

!!! success "Positive"
    - **Sovereign Intelligence:** The machine can update its own knowledge base without external dependencies.
    - **Resource Logic:** By defaulting to the Skirmisher, the system remains fast and light. By gating the Siege Engine, it remains stable.
    - **Physical Isolation:** Browser exploits are trapped within the ephemeral container service, unable to touch the host kernel.

!!! failure "Negative"
    - **Maintenance Burden:** The Siege Engine requires regular updates to keep pace with the "Arms Race" of anti-bot measures (Cloudflare Turnstile, etc).
    - **Latency:** The Siege Engine introduces a "Cold Start" penalty if the Chromium container is not already warm.
