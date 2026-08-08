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
- Circle is the Invocation-shaped focus within Bridge, not a fifth authority surface or a claim
  that the current run strip already composes every owning projection.
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
| Loom | Immutable Scroll/Pattern-revision reader, station/permission outline, optional Mermaid lens | Partial: fixed registry reader without independent Spell identities, editing, teaching, or publication. |

The shell owns navigation, source identity, pending-consent count, and transient notices; an
instrument owns route-local presentation. `/scrying`, `/reliquary`, `/bindings`, and ambiguous
unversioned Loom detail are deliberately not routes. Scrying is Orb's act, not a fifth instrument.
Artifact references and configuration observations are contextual projections, not browser custody
or configuration authority.

[Circle](../divination/altar/circle.md) is likewise not a fifth instrument or route in the present
contract. One Bridge séance may contain many Invocation/Run projections; a future Circle focus may
compose authorized Loom, Nexus, and Orb lenses around exactly one of them without importing their
authority into browser state. The current run strip is only its delivered seed.

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
and dependencies. Runtime and exporter share the same deterministic JSON-only OpenAPI
configuration; generated controller errors use Litestar's JSON `status_code`, `detail`, and
optional `extra` fields. The exporter does not run `create_app()` or its middleware, exception
handlers, lifespan, database, SAQ, or security configuration. The chain is:

```text
Altar controllers → frontend/openapi.json → openapi-typescript
  → frontend/src/lib/api/openapi.d.ts → aliases + openapi-fetch
```

Controllers own operation identifiers. Release regeneration and clean-source preflight expose
schema drift; a local command may rewrite tracked output, whose diff still needs review. SSE stays
outside `openapi-fetch`: Zod schemas, constrained to generated types, validate version,
identifiers, sequence, kind, and envelope. Kind-specific interpretation remains explicit because
run `payload` is currently a broad string-keyed record, not a generated discriminated schema.
Operations that raise a real not-found response explicitly publish the shared `FrameworkError`
schema; generated clients never infer success-only behavior for those paths.

Bridge is text JSON only: no voice upload, file/media admission, audio output, or streaming voice.
Its named JSON SSE envelope carries `schema_version`, `run_id`, producer-stable `event_id`, `seq`,
`kind`, `occurred_at`, and `payload`; kinds are `token`, `status`, `node`, `dispatch`,
`transition`, `fragment`, `consent`, `log`, `done`, and `resync`. The server observes
browser-managed `Last-Event-ID`, sends keepalives, and projects its process-local bus. Terminal
runs receive `resync`, not invented token replay.

The client seeds from the snapshot cursor, serially validates and reduces events, ignores applied
sequence numbers, and refetches on gap or `resync`. Its initial cursor is reducer state: the
current `EventSource` constructor does not send an explicit cursor. A run or ticket identity
mismatch, invalid data, or failed authoritative refetch permanently closes that channel. Bridge
and Nexus immediately mark the projection stale and attempt one bounded authoritative recovery;
a second failure remains visibly stale rather than animated as live. Each Bridge Run projection
retains its applied cursor and a browser-local authority generation; a delayed recovery may replace
that Run only while both still match the request it began from. Ordinary transport errors remain
transient while `EventSource` reconnects. Durable terminal Run status overrides a lagging
process-local channel, and only a retained agent turn retires that terminal projection from the
selected session. Token deltas and channels are neither durable nor cross-process; retained
structural Step evidence is best-effort. Nexus uses its own versioned transition envelope with the
same retention boundary and completion-driven single-flight polling. Closing a channel fences
already-queued callbacks, so an event from a superseded ticket cannot overwrite the replacement
identity. Orb pagination likewise merges only when both the requested and current snapshot still
name the same Run; its Loom link additionally requires the entire valid pinned manifest to equal the
registered revision, as worker replay does.

Component destruction advances the same local authority boundary. A request that settles after
teardown cannot attach a stream, mutate component state, schedule another poll, or navigate. Loom
uses its load generation for this rule; Bridge and Nexus additionally fence stream callbacks and
timers.

### Closed rendering, readable form

The Vessel validates `FragmentCall`s through a closed Pydantic registry and emits inert descriptors.
Svelte maps admitted kinds to compiled renderers and exposes unknown descriptors explicitly.
`{@html}` is forbidden and statically guarded. Invalid or unknown model fragments are dropped and
logged before settlement; client fallback merely contains malformed or newer descriptors. Settled
turns retain the complete validated descriptor, including props, so terminal refresh reconstructs
the same compiled component rather than preserving only its key. Legacy rows that predate descriptor
retention are normalized to inert schema-zero key-only descriptors with empty props; they remain
readable through an explicit inert fallback and never enter a current-version component renderer.

Consent appears in its Bridge context and the shell count. The client submits one typed
approve/deny intent with the configured CSRF header; the Vessel rechecks identity, state, scope,
and idempotency before resume. Snapshot application versions selected-Bridge consent authority, so
an older decision response cannot overwrite a newer snapshot; after Run cancellation the selected
Bridge immediately revokes its visible consent cards and count, then refetches its snapshot. Root
route cancellation uses the selected snapshot session as that authority rather than a route prop. A
failed refetch cannot restore the revoked local authority. Instrument attention
events are invalidation hints only: the shell always re-reads the cross-session status endpoint and
request-version fences overlapping reads, so an arriving local count never becomes global truth.
Bridge message submission likewise retains one client UUID across an ambiguous response, and durable
Run admission maps that identity to exactly one canonical Run. A replay repairs an unresolved held
turn-retention gate before publication. The fixed visible `Magus` Sigil is local bootstrap context,
not an authenticated person. Applying a refreshed root snapshot for the same canonically selected
session preserves the unsent draft; only an actual selected-session identity change clears it.

Nexus retains an ambiguous transition request UUID per target, so inspecting another target cannot
discard the only safe retry identity. A lost-ticket conflict retains that UUID and refuses a fresh
physical launch; only a definitive non-conflict client rejection clears that target. Authoritative
refresh rebinds the inspector to the exact request id so a settled ticket cannot leave stale
pre-refresh transition detail selected. Board
refresh remains single-flight, but a refresh requested while one is in flight marks a dirty trailing
pass; the settling read cannot erase a newer invalidation.

Extensions have no UI source, template, script, import, or third-party sandbox surface.
`@xyflow/svelte` is not installed. Loom's optional locally bundled Mermaid diagram runs in strict
security mode; its textual station/permission score remains visible and authoritative on rendering
failure. Plain-text source lives below `/api/v1/loom/source/workflows/{workflow}` and
`/api/v1/loom/source/patterns/{pattern_id}/{revision}` so every legal two-segment exact Pattern route
remains addressable. Mermaid source is not Pattern data. A later renderer must isolate DTO identity from
renderer coordinates, treat geometry and motion as disposable, deny publication/execution from a
read-only view, and keep a keyboard-operable outline, list, table, or timeline.

Native CSS uses custom properties, cascade layers, media queries, semantic classes, and state
attributes. Type, label, icon, shape, and copy carry meaning without colour; the stylesheet has a
skip link, visible focus, hidden labels, narrow layout, and `prefers-reduced-motion`. Inspectors
restore their live opener after closing when one exists; deep links use router focus reset.
Tailwind, Sass, project-owned PostCSS, and a parallel styling vocabulary are forbidden. Transitive
Vite packages in the lockfile are not a styling API.

### Build boundary, security, and reopening

Development runs Vite on `127.0.0.1:5173`, proxying `/api` and `/schema` to the loopback Vessel.
Production serves static Bridge, Orb, Nexus, and Loom shells; unknown APIs and retired paths stay
404. Every operation that raises a runtime not-found across those verticals declares the shared JSON
`FrameworkError` contract. `npm ci`, OpenAPI and notice generation, compilation, and Python build share a release source.
Audit verifies source identity, compiled `index.html`, and archive notices—not a real browser or
running image. Only `src/lychd/public/_app` is broadly mounted; the two known root artifacts,
`/altar-lightning.svg` and `/THIRD_PARTY_NOTICES.txt`, have narrow typed Litestar handlers.

The Altar is loopback-only. Defaults use same-origin CORS, accept only explicit loopback Origin
exceptions, constrain Host to literal loopback authorities, and expose schema JSON without remote
documentation assets. CSRF remains an unsafe-method layer, not authentication; ordinary requests
still receive the fixed bootstrap Sigil. The foreground launcher can expose configuration the app
cannot observe, security-header and production-browser receipts are absent, and no remote
principal exists. Remote, proxied, tunneled, direct-image-public, and untrusted-browser use remains
unsupported.

Focused checks cover Svelte/TypeScript; frontend API, cursor, remount, stream, focus-return, and
GenUI tests; Python routes, controllers, consent, SSE, fixed root assets, and four instruments;
guards for unsafe HTML, server modules, styling, and misplaced runes; plus static build and archive
audit. They do not establish Playwright against `create_app()`, full keyboard/a11y behavior,
hostile-browser security, performance budgets, Node-free production image, or durable
cross-process events.
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
