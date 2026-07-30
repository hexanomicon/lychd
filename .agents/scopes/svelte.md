# Svelte Scope

## Trigger

Load this scope after [`frontend.md`](frontend.md) for Svelte, SvelteKit, Svelte Flow, `.svelte`,
`.svelte.ts`, `.svelte.js`, client routing, reactive presentation state, or graph/canvas work.

## Authority Order

1. [ADR 15](../../docs/adr/15-frontend.md) and [`frontend.md`](frontend.md) own LychD's browser
   boundary and project gates.
2. [`frontend/package.json`](../../frontend/package.json), lockfile, and configuration own installed
   behavior and versions.
3. Current official [Svelte AI instructions](https://svelte.dev/docs/ai/instructions),
   [skills guidance](https://svelte.dev/docs/ai/skills), documentation, and
   [best practices](https://svelte.dev/docs/svelte/best-practices) own framework syntax and
   diagnostics.
4. Current official Svelte Flow documentation and source own renderer behavior.
5. Local examples, shelf snapshots, and model memory are probes only.

## Mandatory AI Workflow

For every `.svelte`, `.svelte.ts`, or `.svelte.js` analysis or change:

1. Use callable official Svelte MCP tools when available.
2. Start with `list-sections`; choose sections by `use_cases`, then retrieve every relevant
   section with `get-documentation`.
3. Load the official `svelte-core-bestpractices` guidance.
4. Inspect the installed Svelte/Svelte Flow versions before applying version-sensitive guidance.
5. Run `svelte-autofixer` on every changed Svelte file until no actionable issue or suggestion
   remains.
6. Return to [`frontend.md` § Verify](frontend.md#verify) for project checks.

When callable tools are unavailable, use the pinned portable fallback:

```bash
npx --yes @sveltejs/mcp@0.1.25 list-sections
npx --yes @sveltejs/mcp@0.1.25 get-documentation '<relevant,sections>'
npx --yes @sveltejs/mcp@0.1.25 svelte-autofixer <path> --svelte-version 5
```

The fallback version is `0.1.25`; change it only as an intentional scope update. Do not install the
MCP package as an application dependency, make a user-level MCP installation a hidden
prerequisite, or generate a Playground link for repository code.

The optional local shelf starts at
[`../references/svelte-stack.md`](../references/svelte-stack.md). Its absence is non-blocking.
When callable tools are unavailable and the shelf exists, read its official
`svelte-code-writer` and `svelte-core-bestpractices` skill files completely before Svelte analysis
or edits, then use the pinned CLI for task-specific documentation and autofixing. Shelf absence
must never make the repository unbuildable.

## High-Signal Svelte 5 Law

- New code uses runes and current event/snippet syntax, not `$:`, `export let`, `on:`, slots,
  `<svelte:component>`, or `<svelte:self>`.
- Use `$state` only when changes update a template, `$derived`, or `$effect`; prefer `$state.raw`
  for large API/graph objects replaced as units.
- Compute with `$derived` or `$derived.by`. `$effect` is only for external synchronization, not
  state propagation; prefer handlers, bindings, attachments, context, or `createSubscriber`.
- Treat props as changing inputs and derive dependent values.
- Use stable identities, never array indices, for changing nodes, edges, events, and artifacts.
- Snapshot or unwrap reactive values before Fetch, SSE, IndexedDB, structured clone, workers, or
  third-party boundaries.
- Keep runes in components and presentation-owned `.svelte.ts` modules. Use typed context for
  subtree-owned interactive state. Contracts, transport, validation, reducers, and domain logic
  remain ordinary TypeScript.

## Task Routing

### Components and reactivity

Inspect the target and direct callers, then retrieve only the exact rune, template, event,
context, attachment, TypeScript, testing, and best-practice sections involved.

### SvelteKit navigation

Read project configuration first. Probe only relevant routing, link, snapshot, shallow-routing,
adapter-static, and SPA-mode sections. Server topics require an explicit ADR 15 reopening.

### API and live events

Start from the generated OpenAPI type, matching Litestar contract/controller, and semantic event
reducer. Apply the browser authority and accessibility gates in [`frontend.md`](frontend.md).

### Svelte Flow

Inspect the installed version, read the official AI index, and retrieve only the matching
guide/API sections. Route renderer access through one LychD-owned adapter:

- map server DTOs to explicit presentation nodes/edges;
- keep domain identity separate from renderer identity and coordinates;
- reconstruct identical semantic state after reconnect/backfill; and
- target annotations by stable server identity.

Do not parse Mermaid as the Svelte Flow contract, persist its internal store as Pattern/Run truth,
let layout assign semantics, or let Loom gestures and Orb animation become publication,
execution, or evidence. Profile node/edge counts and update frequency with realistic event volume.

### Styling and motion

Retrieve only the component styling/motion sections involved, then apply the native-CSS,
non-color, focus, keyboard, reduced-motion, and projection gates in
[`frontend.md`](frontend.md).

## Verify

Complete the MCP/documentation/autofixer workflow above, then run the exact project gates in
[`frontend.md` § Verify](frontend.md#verify). This scope adds no second command sequence.

## Escalate

Escalate when official documentation conflicts with ADR 15, installed versions make official
guidance ambiguous, a server-only feature appears necessary, or MCP/autofixer advice would change
intended semantics. Route browser-authority, unsafe-HTML, accessibility, performance, and static
SPA conflicts through [`frontend.md` § Escalate](frontend.md#escalate).
