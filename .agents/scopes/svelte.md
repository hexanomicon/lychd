# Svelte Scope

## Trigger

Load this scope after [`frontend.md`](frontend.md) whenever a task creates, edits, reviews, or
diagnoses Svelte, SvelteKit, Svelte Flow, `.svelte`, `.svelte.ts`, `.svelte.js`, client routing,
reactive presentation state, or graph/canvas behavior.

## Authority Order

1. [ADR 15](../../docs/adr/15-frontend.md) owns LychD's browser boundary.
2. [`frontend/package.json`](../../frontend/package.json), lockfile, and configuration own installed
   behavior.
3. Current official Svelte documentation and tools own framework syntax and diagnostics.
4. Current official Svelte Flow documentation and source own renderer behavior.
5. Local examples and model memory are probes only.

Generic upstream guidance never authorizes SvelteKit server routes, server loads, form actions,
remote functions, SSR, a JavaScript production server, Tailwind, Sass, PostCSS, handwritten API
contracts, or browser-owned domain authority.

## Mandatory AI Workflow

For any `.svelte`, `.svelte.ts`, or `.svelte.js` analysis or change:

1. Use callable Svelte MCP tools when available.
2. Begin with `list-sections`.
3. Select sections by their `use_cases` and retrieve every relevant section with
   `get-documentation`.
4. Load the official `svelte-core-bestpractices` guidance.
5. Run `svelte-autofixer` on every changed Svelte file until no actionable issues or suggestions
   remain.
6. Run the project checks required by [`frontend.md`](frontend.md).

Portable fallback:

```bash
npx --yes @sveltejs/mcp@0.1.25 list-sections
npx --yes @sveltejs/mcp@0.1.25 get-documentation '<relevant,sections>'
npx --yes @sveltejs/mcp@0.1.25 svelte-autofixer <path> --svelte-version 5
```

Do not install the MCP package as an application dependency. Do not generate a Playground link for
code written into the repository.

When the operator-assigned local shelf exists, its progressive index is
[`../references/svelte-stack.md`](../references/svelte-stack.md). Its absence is non-blocking and
must never make the repository unbuildable.

When callable tools are unavailable but that shelf exists, read the local official
`svelte-code-writer` and `svelte-core-bestpractices` skill files completely before analyzing or
changing Svelte files, then use the pinned CLI for task-specific documentation and autofixing.

## High-Signal Svelte 5 Law

- Use runes and current event/snippet syntax; reject legacy `$:`, `export let`, `on:`, slots,
  `<svelte:component>`, and `<svelte:self>` in new code.
- Declare `$state` only for values whose changes must update a template, `$derived`, or `$effect`.
- Prefer `$state.raw` for large API/graph objects replaced as units rather than deeply mutated.
- Compute with `$derived` or `$derived.by`; do not use `$effect` to propagate state.
- Reserve `$effect` for external synchronization. Prefer event handlers, bindings, attachments,
  context, or `createSubscriber` where they express the job directly.
- Treat props as changing inputs; derive dependent values.
- Use stable identity keys, never array indices, for changing node, edge, event, and artifact lists.
- Snapshot or unwrap reactive data before Fetch, SSE, IndexedDB, structured clone, workers, or
  third-party boundaries.
- Use typed context for subtree-owned interactive state; keep contracts, transport, validation,
  reducers, and domain logic in ordinary TypeScript.
- Use native CSS and custom properties. Keep type distinguishable from state without relying on
  color alone.

## Task Routing

### Components and reactivity

Retrieve the exact official rune, template, event, context, attachment, TypeScript, testing, and
best-practice sections involved. Inspect the target file and direct callers before general source.

### SvelteKit navigation

Read project configuration first. Relevant upstream topics are routing, link options, snapshots,
shallow routing, adapter-static, and SPA mode. Server-side topics are forbidden unless the task is
explicitly an ADR 15 reopening.

### API and live events

Start from generated OpenAPI types, the matching Litestar contract/controller, and semantic event
reducers. The browser may own connection mechanics, backoff, transient layout, filters, and
selection; it may not infer durable execution truth from animation or connection state.

### Svelte Flow

Read the official Svelte Flow AI index and retrieve only the matching guide/API sections. Inspect
the installed package version before trusting the shelf snapshot.

Route all renderer access through one LychD-owned adapter:

- server DTOs become explicit presentation nodes and edges;
- stable domain identity remains separate from renderer identity and layout coordinates;
- Loom draft gestures never become publication or execution authority;
- Orb scrying animation never becomes evidence;
- reconnect/backfill must reconstruct the same semantic state;
- annotations target stable server identities, not canvas coordinates;
- keyboard, reduced-motion, list/table, and inspector alternatives remain first-class;
- node/edge counts and update frequency must be profiled with realistic event volume.

Do not parse Mermaid as the Svelte Flow data contract. Do not persist Svelte Flow's internal store
as the Pattern or run ledger. Do not allow a layout engine to assign semantic meaning.

### Styling and motion

Use native CSS tokens and semantic classes. Type uses shape/icon/label; phase uses treatment; load
uses bounded secondary marks. Respect `prefers-reduced-motion`, avoid layout motion that destroys
spatial memory, and ensure every pulse corresponds to a typed event or clearly marked projection.

## Verify

For changed Svelte files:

```bash
npm --prefix frontend run check
npm --prefix frontend run test -- <focused-test>
```

Also run `npm --prefix frontend run build` for route, configuration, CSS, dependency, or packaged
asset changes. Inspect `git diff --check` for documentation-only routing changes.

## Escalate

Escalate when official advice conflicts with ADR 15, a renderer wants to own domain state, graph
scale cannot meet accessibility/performance needs, a server-only SvelteKit feature appears
necessary, or the MCP/autofixer recommendation would change intended semantics.
