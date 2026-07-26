# Frontend Scope

## Trigger

Load this scope before creating, editing, reviewing, or diagnosing anything under `frontend/**`,
the compiled Altar assets, browser API/SSE projection, Svelte, SvelteKit, Vite, or native CSS.

## Authorities

- [ADR 15](../../docs/adr/15-frontend.md) owns the browser architecture, framework boundary,
  styling law, build topology, and forbidden SvelteKit server surface.
- [State of the Work](../../docs/state-of-the-work.md#altar-and-observability) owns the delivered
  Altar boundary.
- [CONTRIBUTING.md](../../CONTRIBUTING.md) owns commands and implementation conventions.
- `frontend/package.json`, `frontend/package-lock.json`, `frontend/svelte.config.js`, and
  `frontend/vite.config.ts` own the executable frontend toolchain.
- The [official Svelte AI instructions](https://svelte.dev/docs/ai/instructions),
  [skills guidance](https://svelte.dev/docs/ai/skills), and
  [Svelte best practices](https://svelte.dev/docs/svelte/best-practices) are the upstream syntax
  and validation references. They do not override ADR 15.

## Cheapest Probes

- Components and reactivity: the target `.svelte` or `.svelte.ts` file, its direct callers, and the
  relevant official rune/component documentation.
- Routes and navigation: `frontend/src/routes/`, `frontend/svelte.config.js`, and ADR 15.
- API and events: `frontend/src/lib/api/`, the matching Litestar controller/contracts, and the
  generated OpenAPI document.
- Styling: `frontend/src/app.css` and ADR 15's Styling Boundary.
- Tooling: `frontend/package.json`, `frontend/package-lock.json`, `Makefile`, and the exact Node
  version in `.nvmrc`.

## Required Svelte Workflow

For every task that creates, edits, or reviews a `.svelte`, `.svelte.ts`, or `.svelte.js` file:

1. Use callable Svelte MCP tools when available: discover sections first, then retrieve every
   relevant documentation section.
2. If those tools are unavailable, use the official CLI at the version recorded in this scope:

    ```bash
    npx --yes @sveltejs/mcp@0.1.25 list-sections
    npx --yes @sveltejs/mcp@0.1.25 get-documentation '$state,$derived,$effect'
    ```

3. Fetch only the sections relevant to the task. Prefer current official documentation over model
   memory, old examples, blogs, or Svelte 3/4 training data.
4. Run the official autofixer on every changed Svelte component or module and resolve its issues
   and suggestions before finishing:

    ```bash
    npx --yes @sveltejs/mcp@0.1.25 svelte-autofixer \
      frontend/src/lib/components/Example.svelte --svelte-version 5
    ```

5. Run `npm --prefix frontend run check` and the focused Vitest suite. Run
   `npm --prefix frontend run build` when routes, configuration, CSS, or packaged assets change.

Do not generate a Playground link for code written into the repository. Do not make a user-level
MCP installation a hidden prerequisite. The versioned `npx` command is the portable fallback and
must not become an application dependency.

## Project Drift Gates

- New code uses Svelte 5 runes and current event/snippet syntax; no legacy stores, `$:`,
  `export let`, `on:`, or slots.
- Use `$derived` for computation. `$effect` is an external-synchronization escape hatch, not a
  state-propagation mechanism.
- Keep runes in components and explicitly presentation-owned `.svelte.ts` modules. Generated
  contracts, transport, validation, reducers, and domain logic remain ordinary TypeScript.
- Do not let reactive proxies cross Fetch, SSE, IndexedDB, structured-clone, or extension
  boundaries.
- SvelteKit owns static client routing only. Server routes, server loads, form actions, remote
  functions, SSR, and a JavaScript production server remain forbidden even when generic SvelteKit
  guidance recommends them.
- Styling remains native CSS. Do not add Tailwind, Sass, a project-owned PostCSS configuration, or
  a second styling vocabulary.
- Preserve Litestar as the only API, authorization, mutation, persistence, and production-server
  authority.

## Escalate

Escalate when official Svelte advice conflicts with ADR 15, the static SPA cannot express a
required behavior, a proposed library requires a server/runtime or unsafe HTML boundary, the
autofixer recommendation would change project semantics, or a renderer concern would move
authority into the browser.
