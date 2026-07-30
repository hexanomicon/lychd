# Frontend Scope

## Trigger

Load this scope before creating, editing, reviewing, or diagnosing anything under `frontend/**`,
compiled Altar assets, browser API/SSE projection, Svelte/SvelteKit, Svelte Flow, Vite, or native
CSS.

## Authorities

- [ADR 15](../../docs/adr/15-frontend.md) owns browser architecture, styling, build topology, and
  the forbidden SvelteKit server surface.
- [State of Work](../../docs/state-of-the-work.md#altar-and-observability) owns the delivered
  Altar boundary.
- [CONTRIBUTING.md](../../CONTRIBUTING.md) owns commands and implementation conventions.
- `frontend/package.json`, `frontend/package-lock.json`, `frontend/svelte.config.js`, and
  `frontend/vite.config.ts` own executable toolchain behavior.
- [Svelte scope](svelte.md) owns official Svelte documentation, MCP/autofixer use, framework
  syntax, and Svelte Flow probes. Upstream advice never overrides ADR 15.

## Cheapest Probes

- Components or reactivity: continue through [Svelte scope](svelte.md), then inspect the target
  file and direct callers.
- Routes or navigation: `frontend/src/routes/`, Svelte configuration, then ADR 15.
- API or events: `frontend/src/lib/api/`, generated OpenAPI types, and the matching Litestar
  controller/contract.
- Styling: `frontend/src/app.css`, the affected component, and ADR 15's Styling Boundary.
- Tooling: package manifest, lockfile, `Makefile`, and `.nvmrc`.

For optional agent, observability, graph, or streaming comparisons, use the
[agent and observability UX](references.md#agent-and-observability-ux) map only after ADR 15 and
current contracts are understood.

## Required Svelte Workflow

For every Svelte, SvelteKit, Svelte Flow, `.svelte`, `.svelte.ts`, or `.svelte.js` task, load
[Svelte scope](svelte.md) after this file and complete its official documentation and autofixer
workflow before project verification. Do not duplicate or bypass that workflow here.

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
