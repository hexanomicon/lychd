# Frontend Scope

## Trigger

Load this scope before creating, editing, reviewing, or diagnosing anything under `clients/web/**`,
compiled Altar assets, browser API/SSE projection, Svelte/SvelteKit, Svelte Flow, Vite, or native
CSS.

## Authorities

- [ADR 15](../../docs/adr/15-frontend.md) owns browser architecture, styling, build topology, and
  the forbidden SvelteKit server surface.
- [State of Work](../../docs/state-of-the-work.md#altar-and-observability) owns the delivered
  Altar boundary.
- [CONTRIBUTING.md](../../CONTRIBUTING.md) owns commands and implementation conventions.
- `clients/web/package.json`, `clients/web/package-lock.json`, `clients/web/svelte.config.js`, and
  `clients/web/vite.config.ts` own executable toolchain behavior.
- [Svelte scope](svelte.md) owns official Svelte documentation, MCP/autofixer use, framework
  syntax, and Svelte Flow probes. Upstream advice never overrides ADR 15.

## Cheapest Probes

- Components or reactivity: continue through [Svelte scope](svelte.md), then inspect the target
  file and direct callers.
- Routes or navigation: `clients/web/src/routes/`, Svelte configuration, then ADR 15.
- API or events: `clients/web/src/lib/api/`, generated OpenAPI types, and the matching
  `src/lychd/interface/api/` or `src/lychd/interface/web/` handler and domain contract. Add
  [Build scope](build.md) when those backend sources or tests change.
- Styling: `clients/web/src/app.css`, the affected component, and ADR 15's Styling Boundary.
- Tooling: package manifest, lockfile, `Makefile`, and `.nvmrc`.

For optional agent, observability, graph, or streaming comparisons, use the
[agent and observability UX](references.md#agent-and-observability-ux) map only after ADR 15 and
current contracts are understood.

## Required Svelte Workflow

For every Svelte, SvelteKit, Svelte Flow, `.svelte`, `.svelte.ts`, or `.svelte.js` task, load
[Svelte scope](svelte.md) after this file and complete its official documentation and autofixer
workflow before project verification. Do not duplicate or bypass that workflow here.

## Locked frontend decisions

[ADR 15 §Decision lock and reopening gate](../../docs/adr/15-frontend.md#decision-lock-and-reopening-gate)
closes preference-driven stack selection:

- Svelte 5 with static SvelteKit is the browser framework; Litestar remains the only production
  server and durable authority.
- Node 24.18 and npm 11.16 are the only JavaScript build grammar. Do not introduce Bun, a second
  lockfile, or command paths whose runtime changes by invocation.
- Native semantic CSS and custom properties are the styling language. Refactor ownership and
  cascade layers instead of adding Tailwind, Sass, project-owned PostCSS, or a parallel token set.
- Loom and Orb share one DOM renderer adapter. Share ordinary immutable TypeScript contracts,
  semantic projections, and folding, never renderer stores, framework state, or one another's
  authority.
- Nexus remains a native semantic control board and inherits no renderer; its data is a hierarchy
  that folds by disclosure. A body map needs a measured topology requirement and the same gates.
- XYFlow is the admitted candidate for that one renderer once a released version passes ADR 15's
  authority and lifecycle matrix; that matrix measures retained heap after forced collection on
  every supported engine, not live observer counts.
- Loom editing is gated on contract, not renderer: no served position, no layout document, and no
  keyboard connect path in XYFlow. Loom is a read-only computed layout until authority owns layout
  and mutation intent, and Loom owns the keyboard connect path above the renderer.
- Sigma plus Graphology and cosmos.gl are mapped, not admitted, and reopen only on a measured field
  that folding cannot bound. G6 was evaluated and rejected. No candidate ships zoom-driven
  aggregation, including every commercial alternative surveyed.
- Folding follows declared structure (Run, station subject, occurrence, event; delegated jobs as
  groups), never geometric or computed clustering. It is presentation only and never edits retained
  sequence truth. Bounded progressive loading is a Vessel contract, not a renderer feature.

Do not reopen these choices for an article, poll, community or hiring claim, model-training prior,
toy example, line count, bundle comparison, or isolated microbenchmark. A comparison task requires
the exact product-shaped failure and matched acceptance receipt named by ADR 15; otherwise proceed
within the selected stack.

## Project Drift Gates

- SvelteKit is a static client router. Server routes, server loads, form actions, remote
  functions, SSR, and a JavaScript production server are forbidden.
- Litestar remains the only API, authorization, mutation, persistence, and production-server
  authority. Use generated transport contracts; do not handwrite browser mirrors.
- The browser may own connection mechanics, backoff, filters, selection, and transient layout. It
  may not infer durable Run, execution, consent, readiness, or publication truth from connection,
  animation, or renderer state.
- Native CSS and custom properties are the only styling vocabulary. Do not add Tailwind, Sass,
  project-owned PostCSS, or a parallel token system.
- Keyboard operation, visible focus, semantic labels, non-color distinctions, reduced motion, and
  an accessible list/table or inspector alternative remain first-class. Animation must correspond
  to a typed event or be visibly marked as projection; layout motion must preserve spatial memory.
- Type uses shape, icon, and label; phase uses treatment; load uses bounded secondary marks.
- Do not move secrets, provider credentials, unsafe HTML trust, domain policy, or durable state
  into the browser.

## Verify

For frontend changes, run:

```bash
make frontend-check
```

This regenerates the Litestar OpenAPI contract and browser client before checking and testing it.
Run `make frontend-build` when routes, configuration, CSS, dependencies, or packaged assets
change. Documentation-only routing changes require `git diff --check` on the changed scope files.

## Escalate

Escalate when upstream advice conflicts with ADR 15, the static SPA cannot express required
behavior, a library requires a server/runtime or unsafe HTML boundary, graph scale cannot meet
accessibility or performance needs, or a renderer/browser concern would acquire domain authority.
