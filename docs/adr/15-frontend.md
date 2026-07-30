---
title: 15. Frontend
icon: material/language-html5
---

# :material-language-html5: 15. Frontend

!!! abstract "Context and Problem Statement"
    The Altar gives a browser form to conversation, selected-Run evidence, capability transitions,
    and Pattern inspection. It is a disposable projection: Litestar and the Phylactery retain
    validation, policy, lifecycle, and durable mutation. Static output removes a production
    server; it does not make browser state authoritative or the loopback surface safe for hostile
    remote use.

## Requirements

- Litestar owns validation, caller scope, consent, persistence, workflow movement, and every
  durable mutation. The retired Jinja, HTMX, Alpine, and island paths are not compatibility APIs.
- Browser contracts derive from Altar-controller OpenAPI. Framework-neutral TypeScript owns
  generated types, transport, runtime validation, and event reduction.
- SvelteKit supplies static routes and layouts only: no SSR, server loads/routes, form actions,
  remote functions, or JavaScript production server.
- A snapshot plus event cursor must reconstruct browser state. Connection, animation, and canvas
  layout never prove execution.
- Bridge, Orb, Nexus, and Loom are separate routes with explicit server fallbacks. Generated UI is
  closed descriptors, never model- or extension-supplied HTML, JavaScript, Svelte, or imports.
- Native CSS includes keyboard access, visible focus, non-colour cues, reduced motion, named
  regions, and visible unknown/error states.

## Considered Options

| Option | Decision | Why |
| --- | --- | --- |
| Server-rendered hypermedia with Svelte islands | Rejected | It preserves two projection contracts; historic hypermedia is evidence, not a supported surface. |
| React 19 with Vite | Viable, not selected | Svelte's compiled reactivity fits these fine-grained projections without a project-owned store convention; React could later render the same protocol. |
| Plain Svelte SPA | Rejected | Components alone do not establish the selected route, layout, fallback, deep-link, and static-build conventions. |
| Svelte 5 with static SvelteKit | Selected | Svelte supplies the view language; SvelteKit and `adapter-static` supply the client router and static artifact. |

## Decision Outcome

The canonical Altar is a Svelte 5 static SPA. `frontend/src/routes/+layout.ts` sets `ssr = false`
and `prerender = false`; `adapter-static` writes `index.html` and assets to `src/lychd/public`.
Litestar redirects `/` to `/bridge`, admits the instrument/deep-link shells, and mounts hashed
assets at `/_app`. New Svelte uses runes, current event attributes, snippets, and native CSS.
`+page.server.*`, `+layout.server.*`, `+server.*`, private server modules, form actions, remote
functions, and a SvelteKit production server are forbidden. Node 24.18 and npm 11.16 are build
pins; Litestar/Granian alone serves production requests. Installed tools, lockfile, generated
output, and focused tests are evidence; [State](../state-of-the-work.md#altar-and-observability)
owns delivery.

### The four instruments

| Instrument | Browser contract | Current limit |
| --- | --- | --- |
| Bridge | Session selection, text admission, active-Run reconstruction, semantic stream, consent, and closed fragments | Partial: text only; live reconstruction and tokens are process-local. |
| Orb | One selected Run's ordered, paged structural evidence, gaps, capture label, and links | Partial: no index, tail, complete trace store, annotation, or multi-Run field. |
| Nexus | Timestamped capability observations, non-binding plan preview, typed request, and ticket stream | Partial: observations and tickets are process-local and not restart-complete. |
| Loom | Immutable Pattern-revision reader, station/permission outline, optional Mermaid lens | Partial: fixed registry reader, not Weaver editing or publication. |

The shell owns navigation, source identity, pending-consent count, and transient notices; an
instrument owns route-local presentation. `/scrying`, `/reliquary`, `/bindings`, and ambiguous
unversioned Loom detail are deliberately not routes. Scrying is Orb's act, not a fifth instrument.
Artifact references and configuration observations are contextual projections, not browser custody
or configuration authority.

### Projection law

> The Vessel emits validated snapshots, semantic events, and admitted mutation intents. The Altar
> projects them; it does not settle system truth.

The client has three replaceable layers: validated snapshot; ordered deltas reduced against its
cursor; and URL, selection, layout, draft, focus, and related presentation. Refresh, remount,
numeric gap, or `resync` replaces projection from a snapshot. An animation or open `EventSource`
is never commitment evidence.

Use `$state` only for template, `$derived`, or external-synchronization reactivity; use
`$state.raw` for large unit-replaced API objects, `$derived`/`$derived.by` for computation, and
`$effect` for DOM, browser, or network synchronization—not state propagation. Props change,
collections key by stable identity, and runes stay in components or presentation-owned
`.svelte.ts`. Snapshot or unwrap reactive values before Fetch, SSE, structured clone, IndexedDB,
worker, or extension boundaries. Generated contracts, Zod, Fetch wrappers, reducers, and domain
decisions remain ordinary TypeScript; a guard rejects runes in framework-neutral `.ts`.

### Typed JSON and semantic SSE

`scripts/export_openapi.py` builds a small schema application from production Altar controllers
and dependencies. It does not run `create_app()` or its middleware, lifespan, database, SAQ, or
security configuration. The chain is:

```text
Altar controllers → frontend/openapi.json → openapi-typescript
  → frontend/src/lib/api/openapi.d.ts → aliases + openapi-fetch
```

Controllers own operation identifiers. Release regeneration and clean-source preflight expose
schema drift; a local command may rewrite tracked output, whose diff still needs review. SSE stays
outside `openapi-fetch`: Zod schemas, constrained to generated types, validate version,
identifiers, sequence, kind, and envelope. Kind-specific interpretation remains explicit because
run `payload` is currently a broad string-keyed record, not a generated discriminated schema.

Bridge is text JSON only: no voice upload, file/media admission, audio output, or streaming voice.
Its named JSON SSE envelope carries `schema_version`, `run_id`, producer-stable `event_id`, `seq`,
`kind`, `occurred_at`, and `payload`; kinds are `token`, `status`, `node`, `dispatch`,
`transition`, `fragment`, `consent`, `log`, `done`, and `resync`. The server observes
browser-managed `Last-Event-ID`, sends keepalives, and projects its process-local bus. Terminal
runs receive `resync`, not invented token replay.

The client seeds from the snapshot cursor, serially validates and reduces events, ignores applied
sequence numbers, and refetches on gap or `resync`. Its initial cursor is reducer state: the
current `EventSource` constructor does not send an explicit cursor. Invalid data or failed
authoritative refetch closes the stream; transient error is shown while the browser reconnects.
Token deltas and channels are neither durable nor cross-process; retained structural Step evidence
is best-effort. Nexus uses its own versioned transition envelope with the same retention boundary.

### Closed rendering, readable form

The Vessel validates `FragmentCall`s through a closed Pydantic registry and emits inert descriptors.
Svelte maps admitted kinds to compiled renderers and exposes unknown descriptors explicitly.
`{@html}` is forbidden and statically guarded. Invalid or unknown model fragments are dropped and
logged before settlement; client fallback merely contains malformed or newer descriptors.

Consent appears in its Bridge context and the shell count. The client submits one typed
approve/deny intent with the configured CSRF header; the Vessel rechecks identity, state, scope,
and idempotency before resume. The fixed visible `Magus` Sigil is local bootstrap context, not an
authenticated person.

Extensions have no UI source, template, script, import, or third-party sandbox surface.
`@xyflow/svelte` is not installed. Loom's optional locally bundled Mermaid diagram runs in strict
security mode; its textual station/permission score remains visible and authoritative on rendering
failure. Mermaid source is not Pattern data. A later renderer must isolate DTO identity from
renderer coordinates, treat geometry and motion as disposable, deny publication/execution from a
read-only view, and keep a keyboard-operable outline, list, table, or timeline.

Native CSS uses custom properties, cascade layers, media queries, semantic classes, and state
attributes. Type, label, icon, shape, and copy carry meaning without colour; the stylesheet has a
skip link, visible focus, hidden labels, narrow layout, and `prefers-reduced-motion`. Tailwind,
Sass, project-owned PostCSS, and a parallel styling vocabulary are forbidden. Transitive Vite
packages in the lockfile are not a styling API. Fonts and assets package locally, but delivery is
proved only when a Litestar route and browser test exercise the public URL.

### Build boundary, security, and reopening

Development runs Vite on `127.0.0.1:5173`, proxying `/api` and `/schema` to the loopback Vessel.
Production serves static Bridge, Orb, Nexus, and Loom shells; unknown APIs and retired paths stay
404. `npm ci`, OpenAPI and notice generation, compilation, and Python build share a release source.
Audit verifies source identity, compiled `index.html`, and archive notices—not a real browser or
running image. Only `src/lychd/public/_app` is mounted: root assets such as `/altar-lightning.svg`
and `/THIRD_PARTY_NOTICES.txt` package successfully but lack matching Litestar handlers, so their
browser delivery is not proved.

The Altar is loopback-only. CSRF is only an unsafe-method control: defaults still allow wildcard
CORS, do not constrain Host, use a fixed bootstrap Sigil, and Scalar has mutable CDN assets.
Until Host, Origin, bind, authentication, local-asset, security-header, and hostile-browser
receipts exist, remote, proxied, tunneled, DNS-rebinding, and untrusted-browser use is unsupported.

Focused checks cover Svelte/TypeScript; frontend API, cursor, remount, stream, and GenUI tests;
Python routes, controllers, consent, SSE, and four instruments; guards for unsafe HTML, server
modules, styling, and misplaced runes; plus static build and archive audit. They do not establish
Playwright against `create_app()`, full keyboard/a11y behavior, hostile-browser security, root
asset delivery, performance budgets, Node-free production image, or durable cross-process events.
Reopen this renderer decision only for evidence that its static topology cannot meet a required
security, packaging, accessibility, deep-link, or measured event-performance contract, or an
upstream defect defeats an owned seam. Preference and hypothetical pages are not evidence; any
replacement preserves generated API, semantic events, closed GenUI, server authority, explicit
routes, and one production server.

## Consequences

!!! success "Positive"
    One generated protocol and Svelte projection replace the hybrid stack; snapshots, cursors,
    stable identities, and visible gaps keep loss explicit.

!!! failure "Negative"
    The SPA needs JavaScript, process-local streams cannot recover token history, and browser
    accessibility, lifecycle, root-asset, performance, and hostile-browser receipts remain open.
