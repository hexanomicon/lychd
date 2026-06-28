---
title: 15. Frontend
icon: material/language-html5
---

# :material-language-html5: 15. Frontend: The Altar

!!! abstract "Context and Problem Statement"
    LychD operates as a server-authoritative system where the "Truth" resides exclusively within the **Vessel (11)** and the **Phylactery (06)**. Traditional Single Page Application (SPA) architectures foster a "Cockpit" anti-pattern, bifurcating logic between a Python server and a JavaScript client, which introduces state synchronization fragility and cognitive bottlenecks. A scrying interface is required that moves beyond manual monitoring to become a point of high-level deliberation and **Consent**, supporting the rich interactivity of **Generative UI** without surrendering routing, validation, or durable state to a client-side application runtime.

## Requirements

- **Server-Side Verification:** Mandatory logic unification; all validation, state management, and routing must reside on the server to prevent architectural bifurcation.
- **Multi-Page Instrument Map:** The primary Altar application is an MPA with top-level instruments matching the Hexanomicon map: Bridge, Scrying, Nexus, Loom, Reliquary, and Bindings.
- **Hypermedia-Driven Scrying:** Adoption of the HATEOAS pattern, where the server returns HTML fragments representing distilled outcomes rather than raw data.
- **Generative UI Protocol:** Capability to dynamically render interactive components (forms, diff-views, checklists) based on the schema of an Agent's tool call, allowing the interface to evolve with the machine's capabilities.
- **Predictive State Streaming:** Support for Server-Sent Events (SSE) to animate the machine’s internal states and "Predictive" drafts in real-time, sharing state between the Python kernel and the DOM.
- **Extension Template Discovery:** Provision of a formal mechanism for Extensions to register Jinja2 templates and visual components that are automatically assimilated into the interface at boot time.
- **Island Architecture:** Support for optional "Islands of Interactivity" (Alpine.js or Vite-compiled Svelte) to allow specialized, high-fidelity tools to be mounted as non-critical extension components.
- **Hermetic Asset Strategy:** Prioritization of local, self-contained asset compilation (Vite) to ensure the interface remains functional in air-gapped or isolated environments.

## Considered Options

!!! failure "Option 1: Heavy SPA Frameworks (React / Vue / SvelteKit / full-app Svelte)"
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
        -   **Speed:** HTMX provides SPA-like responsiveness with near-zero client-side overhead.

!!! success "Accepted Refinement: Svelte Instrument Islands"
    Mounting small Svelte components inside server-rendered Altar slots when an instrument needs rich local interaction but must not own routing, persistence, validation, or authorization.

    -   **Pros:**
        -   **Graph Ergonomics:** Tools such as the Weaver lens can use mature component ecosystems like Svelte Flow without turning the Altar into a separate application.
        -   **Vite Continuity:** Svelte compiles through the existing Vite asset contract instead of requiring a separate frontend service.
        -   **Bounded State:** The island owns viewport state, selection, drag gestures, and temporary edits; the Vessel still owns workflow truth and consent.

## Decision Outcome

**The Altar** is implemented as a **Server-Rendered Hypermedia** interface. Its primary role is Intent offering, observation, consent, and the **Rite of Consecration**, with control surfaces expressed through typed ritual forms rather than a generic cockpit model.

The Altar application is multi-page by instrument. The top navigation is the canonical user-facing map: **Bridge**, **Scrying**, **Nexus**, **Loom**, **Reliquary**, and **Bindings**. Each instrument owns its page and local layout; HTMX provides fragment motion inside those pages rather than collapsing the whole application into one thick client shell.

!!! note "The Altar names the whole surface; the chat instrument is the Bridge"
    Earlier drafts used *Altar* for both the entire web surface and its conversational instrument. That overload is resolved: **Altar** denotes the whole scrying surface, and the natural-language instrument within it is the **Bridge**. The graph instrument remains the **Loom**. Every route, template directory, and doc reference SHALL honor this split.

This decision rejects Svelte as a full Altar application shell, not Svelte as a component compiler. Svelte is permitted as an island runtime when the interface surface is intrinsically interactive enough that Alpine would become a miniature framework by accident.

### 0. Instrument Boundaries

The Altar's top-level pages divide work by responsibility:

- **Bridge:** where natural-language Intent is offered and routed into direct answers, jobs, workflows, artifacts, approvals, or other instruments.
- **Scrying:** live visualization of active Invocations, workflow progress, logs, trace fragments, and waiting decisions.
- **Nexus:** visualization of Orchestrator state, queues, Covens, Portals, Animator availability, and hardware pressure.
- **Loom:** Weaver Pattern browsing and design, including Mermaid, Pydantic AI graph renderings, and future graph-editing islands.
- **Reliquary:** durable inspection of generated artifacts, reports, retained evidence, and blessed outputs.
- **Bindings:** user-facing settings, provider references, identity bindings, privacy policy, approval policy, and Altar preferences.

Each instrument is bound to the subsystem that owns its truth. The correspondence is load-bearing: an instrument never holds authority of its own, it projects the authority of its owning subsystem.

| Instrument | Owning Subsystem ADR | Data Authority |
| :--- | :--- | :--- |
| **Bridge** | **[Agents (20)](20-agents.md)** | Agent runs and sessions |
| **Scrying** | **[Observability (29)](29-observability.md)** | The Oculus and live graph runs (**[Graph (24)](24-graph.md)**) |
| **Nexus** | **[Orchestrator (23)](23-orchestrator.md)** | Physical Coven, Portal, and hardware state |
| **Loom** | **[Weaver (28)](28-workflow.md)** / **[Graph (24)](24-graph.md)** | Workflow patterns and graph topology |
| **Reliquary** | **[Phylactery (06)](06-persistence.md)** / **[Memory (27)](27-memory.md)** | Durable artifacts and consecrated Karma |
| **Bindings** | **[Codex (12)](12-configuration.md)** | Rune configuration and policy |

The Bridge page itself may use a left session rail for conversation history, session settings, pinned context, and Coven requests. That rail is local to the Bridge, not global navigation. A right-side inspector is optional and contextual; it appears for selected messages, artifacts, approvals, workers, or log lines rather than serving as a permanent dashboard. On narrow screens, these rails collapse into drawers or separate views.

Coven switching is a cross-instrument concern. The Bridge may show active Coven status or accept a request, but availability, background-worker pressure, warming, sleeping, manual swaps, and queue tradeoffs are Nexus responsibilities.

### 1. The Scrying Stack

The Altar utilizes a "Thin Client" stack designed for maximum substrate integration:

- **HTMX:** The primary engine for state transitions. It swaps HTML fragments into the DOM, allowing the Magus to "zoom" into specific cognitive processes without a page reload.
- **Alpine.js:** Used for small ephemeral UI state (e.g., toggling a sidebar). It remains the default for simple local behavior but should not grow into instrument-level application logic.
- **Svelte Islands:** Optional Vite-compiled components mounted into server-rendered slots for instruments whose client-side interaction is substantial: graph navigation, drag selection, local layout, canvas-like editing, and dense live inspection.
- **Svelte Flow (`@xyflow/svelte`):** A permitted island dependency for Weaver and graph-shaped Scrying views. It renders node/edge projections of workflow state; it does not become the workflow authority.
- **Jinja2:** The templating engine that renders fragments, utilizing the directory structure defined in the **[Layout (13)](13-layout.md)**.
- **Vite:** The supported asset pipeline and dev/build contract for the Altar. Package manager or runtime substitutions are acceptable only when they preserve Vite compatibility and the Litestar integration surface.
- **Tailwind CSS:** A utility-first styling engine. The final CSS is synthesized by scanning the templates of both the Core and all active Extensions.

### 2. Generative UI Patterns (The AG-UI Protocol)

The Altar adopts the **Agentic Generative UI (AG-UI)** philosophy but implements it via Server-Side Rendering (HTMX) to maintain substrate purity.

- **Dynamic Component Rendering:** When an Agent utilizes a tool (e.g., `create_plan`), the **Vessel** does not return raw JSON state to a client-side framework. Instead, it renders a specialized **Jinja2 fragment** (e.g., `<div id="plan">...</div>`) that is swapped directly into the chat stream via HTMX.
- **Predictive State:** The Altar subscribes to the Agent's thought stream via Server-Sent Events (SSE). If the Agent is "drafting" a document, the UI updates a live preview window in real-time, utilizing shared state between the Python kernel and the DOM.
- **Tool-Based Interaction:** Approvals use dynamically generated forms based on the Pydantic schema of the pending tool call, allowing precise parameter editing before execution.
- **Island Hydration:** A Svelte island may receive a typed snapshot and an SSE stream for local rendering. Any mutation that would affect durable state must return to the Vessel as a typed intent and pass server-side validation before the projection changes from speculative to authoritative.

!!! note "The Projection Law"
    Generative UI means the agent **chooses and parameterizes** server-rendered fragments drawn from a registry the Vessel owns. It never means the model emits markup. Model output is never interpreted as HTML, script, or DOM content swapped into the page. The DOM projects Vessel truth; it never decides it.

!!! note "Runtime Surface Contract"
    Server-rendered fragments may expose stable semantic attributes and roles so agents, tests, and the Magus can verify the visible artifact at runtime. This contract is evidence, not authority: the Vessel and Phylactery own truth; the DOM is a machine-readable projection of that truth.

    Verification surfaces should be explicit enough to drive both human review and automated probes: fragment identifiers, declared state, accessible roles, and clear verdict states (`PASS`, `FAIL`, `BLOCKED`, `SKIP`) when a fragment is itself a verification view. `BLOCKED` means the artifact could not be observed; it is not a failed behavior and never a pass.

### 3. The Ritual of Consent

The Altar is the primary coordinate for high-level deliberation.

- **Visions:** The backend does not present raw log streams. Instead, it sends HTML fragments containing Agent-distilled summaries of speculative processes.
- **Consecration:** The Magus interacts with "Decision Fragments"—simple, server-validated forms that trigger the system's internal reflex arcs, merging speculative logic into the primary reality.

#### The Seat of Consent

Consent has a fixed home. A pending **`DeferredToolRequests`** raised by the **[Agents (20)](20-agents.md)** layer renders **inline within the Bridge session that raised it**, where the Magus first offered the Intent. A global **pending-consents sigil** is visible from every instrument, so an approval awaiting the Magus is never hidden behind whichever page is active. The **Vision** artifact of **[HitL (25)](25-hitl.md)** is the rendered body of the approval—the distilled evidence on which consent is granted or withheld. Approval and denial are ordinary hypermedia POSTs; the client holds no authority over the decision, only over its presentation.

### 4. The Extension Lens & Islands

To maintain the **[Federation (05)](05-extensions.md)**, the Altar functions as a discovery engine:

- **Discovery:** During the extension registration pass, future Altar stores may collect the coordinates for extension-owned visual templates.
- **Grafting:** Once shaped, the Vessel can consume those registered template roots, allowing extensions to inject new scrying fragments into the Altar's layout without core modifications.
- **Islands:** If an extension requires complex client-side logic (e.g., a real-time data visualization or an interactive node-map), it may mount an "Island"—a small, isolated JavaScript or Svelte bundle—into an HTMX-driven page. TypeScript is optional and encouraged for these richer islands, but it is not required for the baseline HTMX/Alpine surface.
- **Graph Lenses:** Weaver-grade graph views may use Svelte Flow when the island contract is explicit: the component owns presentation mechanics, while the extension and Vessel own workflow state, mutation rules, persistence, and consent.

### 5. Queues, Whims, and Coven Pressure

The instrument map provides real-time visibility into the **Orchestrator's Intent Queues** without turning the Bridge into an all-purpose control room.

- **Bridge:** Shows the active Coven status and may accept a Coven or capability request for the current session.
- **Scrying:** Shows which Invocations, Ghoul jobs, and workflow steps are active, paused, failed, or awaiting Magus decision.
- **Nexus:** Shows queue pressure, "Inertia" weights, "Whim" multipliers, available Covens, Portals, hardware pressure, and why a swap is pending or denied.
- **Manual Flip:** A privileged Nexus component may trigger a **Coven Swap**, providing the Override required to break logical loops or prioritize specific work when policy allows.

### Consequences

!!! success "Positive"
    - **Physical Minimalism:** The UI consumes minimal RAM and CPU, leaving the hardware entirely to the labor of the machine.
    - **Cognitive Clarity:** By focusing on summarized "Visions," the Altar prevents user overwhelm.
    - **Atomic Consistency:** The UI and backend cannot drift out of sync because the "View" is simply a fragment of the "State."
    - **Generative Flexibility:** The interface can evolve its own controls based on the changing needs of the Agent without deploying new frontend code.
    - **Instrument Depth:** Rich tools such as the Weaver graph can use Svelte/Svelte Flow where hypermedia alone would force awkward local state.

!!! failure "Negative"
    - **Macro Complexity:** Reusing visual components across extensions requires disciplined use of Jinja Macros.
    - **Paradigm Shift:** Developers must abandon "Application" thinking and adopt "Hypermedia" thinking, focusing on the flow of fragments rather than the flow of raw data.
    - **Boundary Discipline:** Svelte islands must be prevented from quietly becoming a second application shell.
    - **Bundle Weight:** Graph-focused islands add JavaScript cost and must remain opt-in per instrument.
