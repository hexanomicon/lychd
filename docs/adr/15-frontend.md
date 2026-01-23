---
title: 15. Frontend
icon: material/language-html5
---

# :material-language-html5: 15. Frontend: The Altar

!!! abstract "Context and Problem Statement"
    The LychD operates as a server-authoritative system where the "Truth" resides exclusively within the **Vessel (11)** and the **Phylactery (06)**. Traditional Single Page Application (SPA) architectures foster a "Cockpit" anti-pattern, bifurcating logic between a Python server and a JavaScript client, which introduces state synchronization fragility and cognitive bottlenecks. A scrying interface is required that moves beyond manual monitoring to become a point of high-level deliberation and **Sovereign Consent**, supporting the rich interactivity of **Generative UI** without the dependency hell of client-side frameworks.

## Requirements

- **Server-Side Sovereignty:** Mandatory logic unification; all validation, state management, and routing must reside on the server to prevent architectural bifurcation.
- **Hypermedia-Driven Scrying:** Adoption of the HATEOAS pattern, where the server returns HTML fragments representing distilled outcomes rather than raw data.
- **Generative UI Protocol:** Capability to dynamically render interactive components (forms, diff-views, checklists) based on the schema of an Agent's tool call, allowing the interface to evolve with the machine's capabilities.
- **Predictive State Streaming:** Support for Server-Sent Events (SSE) to animate the machine’s internal states and "Predictive" drafts in real-time, sharing state between the Python kernel and the DOM.
- **Extension Template Discovery:** Provision of a formal mechanism for Extensions to register Jinja2 templates and visual components that are automatically assimilated into the interface at boot time.
- **Island Architecture:** Support for optional "Islands of Interactivity" (Alpine.js) to allow specialized, high-fidelity tools to be mounted as non-critical extension components.
- **Hermetic Asset Strategy:** Prioritization of local, self-contained asset compilation (Vite) to ensure the interface remains functional in air-gapped or isolated environments.

## Considered Options

!!! failure "Option 1: Heavy SPA Frameworks (React / Vue / Svelte)"
    Building a thick-client application that manages its own state and routing.
    -   **Cons:** **Architectural Bifurcation.** Duplicates validation logic and requires a complex, independent build chain. This model encourages the "Cockpit" mentality and makes extension injection nearly impossible without runtime patching of compiled bundles.

!!! failure "Option 2: Traditional Full-Page SSR"
    Returning complete HTML pages on every user interaction.
    -   **Cons:** **Sensory Friction.** Full-page reloads destroy the immersion of the scrying ritual and cannot support the real-time "Streaming Mind" requirements of an agentic system.

!!! success "Option 3: Hypermedia-Driven Altar (HTMX + Alpine.js)"
    A server-centric architecture utilizing HTML fragments and a thin interactive layer.
    -   **Pros:**
        -   **Unified Mind:** The UI state is a direct reflection of the Python backend.
        -   **Generative Agility:** Allows the server to "push" new UI components (like a specialized approval form) in response to an Agent's thought process.
        -   **Sovereign Speed:** HTMX provides SPA-like responsiveness with near-zero client-side overhead.

## Decision Outcome

**The Altar** is implemented as a **Server-Rendered Hypermedia** interface. It is designed not as a cockpit for control, but as a scrying pool for observation and the **Rite of Consecration**.

### 1. The Scrying Stack

The Altar utilizes a "Thin Client" stack designed for maximum substrate integration:

- **HTMX:** The primary engine for state transitions. It swaps HTML fragments into the DOM, allowing the Magus to "zoom" into specific cognitive processes without a page reload.
- **Alpine.js:** Used for ephemeral, local UI state (e.g., toggling a sidebar) and managing "Islands of Interactivity."
- **Jinja2:** The templating engine that renders fragments, utilizing the directory structure defined in the **[Layout (13)](13-layout.md)**.
- **Tailwind CSS:** A utility-first styling engine. The final CSS is synthesized by scanning the templates of both the Core and all active Extensions.

### 2. Generative UI Patterns (The AG-UI Protocol)

The Altar adopts the **Agentic Generative UI (AG-UI)** philosophy but implements it via Server-Side Rendering (HTMX) to maintain substrate purity.

- **Dynamic Component Rendering:** When an Agent utilizes a tool (e.g., `create_plan`), the **Vessel** does not return raw JSON state to a client-side framework. Instead, it renders a specialized **Jinja2 fragment** (e.g., `<div id="plan">...</div>`) that is swapped directly into the chat stream via HTMX.
- **Predictive State:** The Altar subscribes to the Agent's thought stream via Server-Sent Events (SSE). If the Agent is "drafting" a document, the UI updates a live preview window in real-time, utilizing shared state between the Python kernel and the DOM.
- **Tool-Based Interaction:** Approvals are not generic buttons; they are dynamically generated forms based on the Pydantic schema of the pending tool call, allowing for precise parameter editing before execution.

### 3. The Ritual of Consent

The Altar is the primary coordinate for high-level deliberation.

- **Visions:** The backend does not present raw log streams. Instead, it sends HTML fragments containing Agent-distilled summaries of speculative processes.
- **Consecration:** The Magus interacts with "Decision Fragments"—simple, server-validated forms that trigger the system's internal reflex arcs, merging speculative logic into the primary reality.

### 4. The Extension Lens & Islands

To maintain the **[Federation (05)](05-extensions.md)**, the Altar functions as a discovery engine:

- **Discovery:** During the registration hook, extensions provide the coordinates for their visual templates.
- **Grafting:** The Vessel scans these directories, allowing extensions to inject new scrying fragments into the Altar's layout without core modifications.
- **Islands:** If an extension requires complex client-side logic (e.g., a real-time data visualization or an interactive node-map), it may mount an "Island"—a small, isolated JavaScript bundle—into an HTMX-driven page.

### 5. The Scales of the Sovereign

The Altar provides a real-time scrying view of the **Orchestrator’s Intent Queues**.

- **The Scales:** Visualization of current "Inertia" weights and "Whim" multipliers. This allows the Magus to see exactly why the Sovereign is maintaining a specific Coven or why a swap is pending.
- **Queue Scrying:** A live stream of the **Ghoul (14)** labor force, showing which tasks are active, which are in "Stasis," and which are awaiting a hardware transition.
- **Manual Flip:** A privileged interface component to manually trigger a **Coven Swap**, providing the "Sovereign Override" required to break logical loops or prioritize specific work.

### Consequences

!!! success "Positive"
    - **Physical Minimalism:** The UI consumes minimal RAM and CPU, leaving the hardware entirely to the labor of the machine.
    - **Cognitive Clarity:** By focusing on summarized "Visions," the Altar prevents user overwhelm.
    - **Atomic Consistency:** The UI and backend cannot drift out of sync because the "View" is simply a fragment of the "State."
    - **Generative Flexibility:** The interface can evolve its own controls based on the changing needs of the Agent without deploying new frontend code.

!!! failure "Negative"
    - **Macro Complexity:** Reusing visual components across extensions requires disciplined use of Jinja Macros.
    - **Paradigm Shift:** Developers must abandon "Application" thinking and adopt "Hypermedia" thinking, focusing on the flow of fragments rather than the flow of raw data.
