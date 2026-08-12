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
- Every executable software dependency in the supported client, build, and renderer path is
  locally operable FOSS under OSI-approved terms; non-code data may use reviewed
  public-domain-equivalent terms such as CC0. Proprietary services and source-available-only
  packages are not admitted. Dependency closure, licence compatibility, and notices are reviewed
  with [Packaging](17-packaging.md) before admission.

## Considered Options

| Option | Decision | Why |
| --- | --- | --- |
| Server-rendered hypermedia with Svelte islands | Rejected | It preserves two projection contracts; historic hypermedia is evidence, not a supported surface. |
| React 19 with Vite | Rejected under current requirements; eligible only through the reopening gate | Its explicit external-store and renderer-change seams are useful, but they do not by themselves establish domain intent, lifecycle safety, static routing, or lower whole-system maintenance. |
| Plain Svelte SPA | Rejected | Components alone do not establish the selected route, layout, fallback, deep-link, and static-build conventions. |
| Svelte 5 with static SvelteKit | Selected and reaffirmed | Svelte supplies the view language; SvelteKit and `adapter-static` supply the client router and static artifact while framework-neutral TypeScript retains authority. |

## Decision Outcome

The canonical Altar is a Svelte 5 static SPA. `clients/web/src/routes/+layout.ts` sets `ssr = false`
and `prerender = false`; `adapter-static` writes `index.html` and assets to `src/lychd/public`.
Litestar redirects `/` to `/bridge`, admits the instrument/deep-link shells, and mounts hashed
assets at `/_app`. New Svelte uses runes, current event attributes, snippets, and native CSS.
`+page.server.*`, `+layout.server.*`, `+server.*`, private server modules, form actions, remote
functions, and a SvelteKit production server are forbidden. Node 24.18 and npm 11.16 are build
pins; Litestar/Granian alone serves production requests. Installed tools, lockfile, generated
output, and focused tests are evidence; [State](../state-of-the-work.md#altar-and-observability)
owns delivery.

### Decision lock and reopening gate

The frontend stack was re-examined as a greenfield choice against React 19 with Vite, Node versus
Bun, native CSS versus Tailwind, one versus separate Loom and Orb renderers, and a Rust/Wasm
frontend. Popularity, hiring pool, model-training volume, community enthusiasm, source-line count,
bundle size, and isolated microbenchmarks do not decide this Covenant. The review reaffirmed one
coherent boundary:

- **Svelte 5 with static SvelteKit remains the Altar framework.** React's more explicit effect
  diagnostics and React Flow's tagged renderer changes are real advantages, but renderer changes
  are not domain commands. They did not establish that Svelte cannot preserve the same authority,
  recovery, accessibility, route, and release contracts with less total maintenance.
- **Node 24.18 with npm 11.16 remains the only verified JavaScript build grammar.** Bun is not a
  supported installer, runner, or runtime: adding it beside Node/npm would create a second runtime,
  lock, and command meaning without replacing the accepted path. Reopening requires one complete
  matched repository receipt that replaces or passes every Vite, Vitest, browser, notice, and
  release gate—not install speed.
- **Native semantic CSS remains the only styling vocabulary.** A large stylesheet is repaired by
  token, base, shared-chrome, graph-seam, and instrument ownership—not by adding Tailwind's scanner,
  utility grammar, or a parallel cascade truth.
- **Loom and Orb share one DOM renderer.** A second renderer buys a second adapter, semantic twin,
  teardown audit, licence review, and browser-quirk tail; no measured workload requires that cost.
  They share immutable TypeScript contracts, identities, commands, selection/camera protocols,
  telemetry, folding, and a model-derived semantic twin. They do not share instrument view models,
  and shared code never lets one instrument's authority reach the other.
- **Nexus remains a native semantic control board.** Its cards, preview, ticket, and inspector are
  primary. The first trial for a future body map is a read-only Svelte DOM/SVG projection; it does
  not need an editor or dense-graph engine without a measured topology requirement.

This choice is closed to preference-driven reconsideration. Articles, polls, hiring arguments,
framework enthusiasm, toy examples, and an isolated speed or size result are discovery leads, not
reopening evidence. Reopen the Svelte decision only when an executable product-shaped receipt
shows that the accepted stack cannot meet a required security, packaging, accessibility,
deep-link, recovery, lifecycle, or measured workload contract and a named replacement passes that
same contract. A replacement must also preserve every existing Litestar route, generated API,
focus-reset, asset-mount, API-404, notice, and release-artifact gate.

The XYFlow line is admitted for Loom under a corrected gate. Its [shared pan/zoom
implementation](https://github.com/xyflow/xyflow/blob/main/packages/system/src/xypanzoom/XYPanZoom.ts)
creates a `ResizeObserver` that its destroy path does not disconnect, and upstream declares that
omission deliberate: `destroy()` also runs to pause zooming during a user selection, so
disconnecting there would leave the extent cache stale. Under the
[observer-lifetime rule](https://drafts.csswg.org/resize-observer/#resize-observer-lifetime) an
observer dies only when it holds no scripting reference **and** observes no target, so an
unreferenced observer that still observes is retained by the specification alone. Collection
therefore depends on the engine holding its target weakly, which Blink does; Gecko and WebKit are
unverified. Counting live observers still measures upstream intent rather than retained memory, but
the specification does not by itself clear this path. The gate is measured retained heap: repeated
mount, replacement, settlement, and HMR cycles followed by forced collection must show no growth on
every supported engine, and reasoning does not substitute for that measurement. A candidate must
also prove,
through public APIs and without a maintained fork, private-store access, whole-flow remount, or
renderer-state authority, that drag, keyboard movement, resize, measurement, selection, connect,
reconnect, delete, rejection, and resync preserve the authoritative semantic twin.

Loom is an editor, not a dense field. Its registered Scrolls place five and three stations today,
over six and two permitted edges, and stay in the tens to low hundreds under any admitted Suite
grammar. Orb is bounded by folding rather than by
volume. Neither workload justifies a dense engine, and a dense engine supplies neither Loom's drag,
connect, reconnect, and handle grammar nor a DOM-native accessible twin.

Loom's editing admission is separately gated on contract, not on renderer. The served semantic score
carries no position, and the Scroll grammar declares no layout document, so no drag may be admitted
before authority owns layout and mutation intent. Until then Loom is a read-only projection over a
computed layout. XYFlow also has no keyboard path to create a connection; its connection handles are
not focusable. Loom therefore either owns that path above the renderer or admits editing without it,
and admitting editing without it would break the keyboard twin this Covenant requires.

### Folding, not scale

A rendered field is bounded by folding at every camera scale. Folding is a legibility rule first: a
field no reader can read is not evidence, and no engine repairs that. The bounded rendered set is
its consequence, and it is what keeps a DOM renderer sufficient.

Folding follows structure the authority already declares—for Orb, Run, then station subject, then
occurrence, then event, with delegated jobs as their own declared groups. A group states its
membership count, carries its declared name, and remains selectable and expandable through the same
typed identities. Geometric or computed clustering is not admitted: proximity would assert a
relation no authority declared, and a group must never be readable as evidence LychD did not record.

Folding is presentation only. It never merges, omits, or reorders retained sequence truth, and an
unexpanded group whose members were never served is an explicit unknown, exactly like a sequence
gap. Bounded expansion remains a Vessel contract: authority serves what was asked for, and the
browser holds only what it was served. Folding belongs to Loom and Orb through their shared supply;
Nexus folds by disclosure in its own board and inherits no renderer.

### Deferred dense renderers

Sigma with Graphology and cosmos.gl are mapped, not admitted, and are reopened only by a measured
field that folding cannot bound—not by node count alone. Both are FOSS: Sigma's closure is MIT
throughout; cosmos.gl became admissible only after moving to the OpenJS Foundation under MIT, its
predecessor having carried non-commercial terms that failed this Covenant outright.

The mapping is recorded so a later review starts from evidence rather than from preference. Neither
ships zoom-driven aggregation, and neither does any commercial alternative surveyed; aggregation is
LychD-owned under every candidate, which is why it is specified above as a supply rule instead of a
selection criterion. Sigma re-indexes its whole graph when a node is dropped, and eviction is the
operation bounded expansion is made of. cosmos.gl has no removal path for links, so an edge-touching
patch rebuilds the whole link set, and its identity-keyed streaming API is published only under the
non-commercial tier its maintainers also sell. Neither handles WebGL context loss, and neither
carries any accessibility surface, so the semantic twin would be built twice and kept in sync
forever. G6 was evaluated and rejected outright: its own published maximum-scale demonstration
fails, its combo collapse is a pointer-triggered action over hand-declared groups rather than
zoom-driven aggregation, and its teardown discards its own context while asynchronous work still
holds it.

Admission would still require realistic scale, incremental patch, camera/selection recovery,
WebGL-context loss, teardown, complete semantic-twin, licence, and notice receipts, and any admitted
graph structure would remain a disposable projection cache, never Run truth. Custom WebGPU or a
narrow Rust/Wasm worker is an escalation only after profiling proves that this path cannot meet the
same contract; it is not a route to rewriting the browser shell.

### The four instruments

| Instrument | Browser contract | Current limit |
| --- | --- | --- |
| Bridge | Session selection, single-active-Run text admission, reconstruction, semantic stream, consent, and closed fragments | Partial: text only; live reconstruction and tokens are process-local. |
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

Loom and Orb share one framework-neutral graph-projection supply in ordinary immutable TypeScript:
stable server identities and revisions, validated snapshots and ordered deltas, semantic nodes and
relations, declared fold groups and their membership counts, presentation-local selection and
viewport intents, and revision-fenced mutation intents. Folding and the semantic twin derive from
this supply, so both survive a renderer change and neither is owned by a dependency. Each instrument
derives its own view model over one shared renderer adapter. The supply contains no runes,
reactive proxies, XYFlow, Sigma, or Graphology objects, renderer geometry, or durable policy.
Mutating Loom gestures become explicit server commands; authority replaces the structural
projection after acceptance, rejection, gap recovery, or resync, while local camera, selection,
and focus are restored only while their identity and generation remain valid. A complete keyboard
and screen-reader twin derives from the same supply. This reuse is not a universal Graph or domain
model.

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
Altar controllers → clients/web/openapi.json → openapi-typescript
  → clients/web/src/lib/api/openapi.d.ts → aliases + openapi-fetch
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
uses its load generation for this rule; Orb aborts owned snapshot and pagination reads as it
advances that generation; Bridge and Nexus additionally fence stream callbacks and timers.

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
turn-retention gate before publication. Within one Bridge session, process-local admission permits
that exact replay but refuses a different message while any prior Run remains nonterminal; terminal
ledger truth admits the next turn without a separate active marker. The fixed visible `Magus` Sigil
is local bootstrap context, not an authenticated person. Applying a refreshed root snapshot for the
same canonically selected session preserves the unsent draft; only an actual selected-session
identity change clears it.

Nexus retains an ambiguous transition request UUID per target, so inspecting another target cannot
discard the only safe retry identity. A lost-ticket conflict retains that UUID and refuses a fresh
physical launch; only a definitive non-conflict client rejection clears that target. Authoritative
refresh rebinds the inspector to the exact request id so a settled ticket cannot leave stale
pre-refresh transition detail selected. Board
refresh remains single-flight, but a refresh requested while one is in flight marks a dirty trailing
pass; the settling read cannot erase a newer invalidation.

Extensions have no UI source, template, script, import, or third-party sandbox surface.
`@xyflow/svelte` is admitted for Loom but not installed; State owns delivery. Loom's optional
locally bundled Mermaid diagram runs in strict
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
The [decision lock](#decision-lock-and-reopening-gate) is the exhaustive reopening rule. A build,
security, or renderer task applies that gate rather than starting another framework comparison.

## Consequences

!!! success "Positive"
    One generated protocol and Svelte projection replace the hybrid stack; snapshots, cursors,
    stable identities, and visible gaps keep loss explicit.

!!! failure "Negative"
    The SPA needs JavaScript, process-local streams cannot recover token history, and browser
    accessibility, lifecycle, root-asset, performance, and hostile-browser receipts remain open.
