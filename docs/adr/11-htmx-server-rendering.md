---
title: 11. HTMX & SSR
icon: material/language-html5
---

# :material-language-html5: 11. HTMX and Server-Rendered HTML for Web UI

!!! abstract "Context and Problem Statement"
    The LychD project necessitates a web user interface, [The Altar](../divination/altar.md), to facilitate user interaction and observation of the daemon's operations.

## Decision Drivers

- **Architecture Cohesion:** The interface must not function as a distributed system. Business logic and application state must reside exclusively on the server to prevent synchronization issues and logic duplication.
- **Modern Interactivity:** The architectural pattern must deliver dynamic interactivity (partial page updates) without introducing the complexity of a full Single Page Application.
- **Operational Simplicity:** The frontend complexity—specifically the volume of custom JavaScript and client-side build tooling—must be minimized.
- **Self-Contained Artifacts:** The build process must be hermetic. Frontend assets must be compiled locally without runtime dependencies on external CDNs.

## Considered Options

!!! failure "Option 1: Single Page Application (SPA)"
    Develop a separate frontend application using a framework like React, Vue, or Svelte.

    - **Pros:** Enables highly complex, application-like client-side state interactions.
    - **Cons:** **Architectural Bifurcation.** This approach creates a "thick client"—a second, complex, stateful application that must be developed and maintained alongside the server. It necessitates the duplication of routing, validation, and state management logic. This separation is antithetical to the project's goal of a cohesive, server-authoritative system.

!!! success "Option 2: Server-Rendered Hypermedia"
    Adopt a server-centric architecture where the backend responds with HTML fragments rather than JSON. Interactivity is achieved by swapping these fragments into the DOM.

    - **Pros:** **Radical Simplification.** Eliminates the need for client-side routing and state management. The frontend becomes a stateless view layer—a direct reflection of the server's truth.
    - **Cons:** Less suitable for applications with heavy offline requirements or extremely complex client-side graphical manipulation (e.g., canvas editors).

## Decision Outcome

The web interface is implemented using a **Server-Rendered HTML** architecture. The stack is designed to be lightweight, declarative, and server-authoritative.

The technology stack consists of:

- **HTMX:** The primary engine for interactivity. It enables the frontend to request HTML fragments from the server and update the DOM dynamically. Litestar's native HTMX integration is leveraged to handle these requests efficiently.
- **AlpineJS:** A minimal JavaScript framework utilized for strictly local, ephemeral UI state (e.g., toggling modals or dropdown menus).
- **TailwindCSS:** Utilized for utility-first styling.

**Build Pipeline:**
Contrary to traditional server-side rendering, this approach utilizes a modern asset pipeline. **Vite** and **PostCSS** are integrated into the build process to compile, bundle, and minify assets, ensuring a professional, optimized, and self-contained delivery artifact.

### Consequences

!!! success "Positive"
    - **Development Velocity:** Frontend features can be implemented rapidly without the overhead of creating API serializers, client-side fetch logic, or state stores.
    - **Unified Logic:** All validation and business rules remain on the server. The UI cannot drift out of sync with the backend because it is generated *by* the backend.
    - **Performance:** The initial page load is fast (HTML is pre-rendered), and subsequent interactions are lightweight (swapping small HTML fragments), avoiding the massive JavaScript bundles typical of SPAs.

!!! failure "Negative"
    - **Component Reusability:** Unlike React/Vue components which are highly portable, the UI components in this architecture are tightly coupled to the backend templating language (Jinja2).
    - **Unfamiliar Paradigm:** Modern web developers are often trained exclusively in the SPA model. This architecture requires a shift in thinking back to Hypermedia-as-the-Engine-of-Application-State (HATEOAS).
