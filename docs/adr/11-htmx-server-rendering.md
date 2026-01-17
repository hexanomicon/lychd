---
title: 11. HTMX & SSR
icon: material/language-html5
---

# :material-language-html5: 11. HTMX and Server-Rendered HTML for Web UI

!!! abstract "Context and Problem Statement"
    The LychD project requires a web user interface, "The Altar," to serve as a window into the daemon's soul. It must allow users to observe and interact with the system's operations. The modern default for building such an interface is a Single Page Application (SPA) using a framework like React or Vue, which communicates with a headless backend via a JSON API.

    This SPA approach creates a "thick client"—a second, complex, stateful application that must be developed and maintained alongside the server. This introduces significant complexity, including client-side state management, routing, and a duplication of logic. This is antithetical to the LychD philosophy, which demands a simple, cohesive system where all core logic resides on the server.

## Decision Drivers

- **Simplicity:** Minimize frontend complexity, especially the amount of custom JavaScript.
- **Cohesion:** The UI should be a thin, stateless presentation layer, with all business logic and state managed exclusively on the server.
- **Interactivity:** The interface must still feel dynamic and modern, capable of handling real-time updates without full page reloads.
- **Self-Contained Build:** The frontend assets must be part of a local, version-controlled build process, with no reliance on external CDNs.

## Considered Options

!!! failure "Option 1: Single Page Application (SPA)"
    Use a framework like React, Vue, or Svelte.

    - **Pros:** Can create very fluid, application-like user experiences.
    - **Cons:** The complexity overhead is immense and unnecessary for this project's needs. It forces the creation of two separate applications instead of one unified system.

!!! success "Option 2: Server-Rendered Hypermedia"
    Use a server-centric approach where the server sends HTML, not JSON. Interactivity is achieved by requesting small HTML fragments from the server and swapping them into the current page.

    - **Pros:** Radically simplifies the frontend by eliminating client-side state management and routing. Logic is centralized on the server, making the system easier to reason about and maintain.
    - **Cons:** For extremely complex, state-heavy UIs (like an in-browser photo editor), this approach can be less suitable. This is not a concern for LychD's interface.

## Decision Outcome

We will build the entire web interface using a stack centered on **Server-Rendered HTML**. This ensures the frontend remains a simple, direct reflection of the server's state.

The chosen technology stack is:

- **HTMX:** The core library for providing modern, dynamic interactivity. Litestar provides first-class support and helpers specifically for working with HTMX.
- **AlpineJS:** A minimal JavaScript framework used for small, localized client-side behaviors (e.g., toggling a dropdown).
- **TailwindCSS:** A utility-first CSS framework for styling.

Crucially, this is not a retro approach. All frontend assets will be compiled and bundled locally using a modern toolchain (**Vite**, **PostCSS**). This creates a professional, self-contained, and performant build process with zero reliance on external CDNs for core functionality.

### Consequences

!!! success "Positive"
    - **Velocity:** Frontend development is drastically simplified, allowing for faster iteration.
    - **Maintainability:** The entire system's logic is centralized on the server, creating a more cohesive codebase.
    - **Performance:** The final user experience is lightweight and fast, with minimal JavaScript sent to the browser.

!!! failure "Negative"
    - **Learning Curve:** This architectural pattern is less common than the SPA model, which may present a learning curve for new contributors used to React/Vue.
