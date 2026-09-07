---
title: 15. Frontend
icon: material/language-html5
---

# :material-language-html5: 15. Frontend

!!! abstract "Context and Problem Statement"
    The Altar gives a browser form to conversation, selected-Run evidence, capability transitions,
    and Pattern inspection. It is a disposable projection: Litestar and the Phylactery retain
    validation, policy, lifecycle, and durable mutation. Static output needs no JavaScript production
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
- Atlas, Bridge, Orb, Nexus, and Loom are separate routes with explicit server fallbacks. Generated UI is
  closed descriptors, never model- or extension-supplied HTML, JavaScript, Svelte, or imports.
- Circle is the Invocation-shaped focus within Bridge, not a separate instrument or a claim
  that the current run strip already composes every owning projection.
- Native CSS includes keyboard access, visible focus, non-colour cues, reduced motion, named
  regions, and visible unknown/error states.
- The Altar ships one canonical built-in appearance, **LychD Dark**. Its semantic colour boundary
  must remain closed enough for a future validated operator palette override without promising a
  second built-in theme, arbitrary CSS, or extension-owned UI.
- The Altar keeps a replaceable localization boundary for interface copy, accessibility labels,
  pluralization, locale-sensitive formatting, and text direction. Interface locale never rewrites
  Intent, model output, artifacts, or evidence.
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
| Svelte 5 with static SvelteKit | Selected and reaffirmed | Svelte supplies the view language; SvelteKit and `adapter-static` supply the client router and static artifact while framework-neutral TypeScript owns transport and projection contracts. |

## Decision Outcome

The canonical Altar is a Svelte 5 static SPA. `clients/web/src/routes/+layout.ts` sets `ssr = false`
and `prerender = false`; `adapter-static` writes `index.html` and assets to `src/lychd/public`.
Litestar redirects `/` to `/bridge`, admits the instrument/deep-link shells, and mounts hashed
assets at `/_app`. New Svelte uses runes, current event attributes, snippets, and native CSS.
`+page.server.*`, `+layout.server.*`, `+server.*`, private server modules, form actions, remote
functions, and a SvelteKit production server are forbidden. Node 24.20 and npm 12.0 are build
pins; Litestar/Granian alone serves production requests. Installed tools, lockfile, generated
output, and focused tests are evidence; [State](../state-of-the-work.md#altar-and-observability)
owns delivery.

<span id="the-four-instruments"></span>

### The five instruments

| Instrument | Browser contract | Current limit |
| --- | --- | --- |
| Atlas | Versioned Projects, concerns, attributed judgments, decisions, next steps, and explicit activity references | Initial planning surface; no autonomous continuation or automatic coverage. |
| Bridge | Session selection, single-active-Run text admission, reconstruction, semantic stream, consent, and closed fragments | Partial: text only; live reconstruction and tokens are process-local. |
| Orb | One selected Run's ordered, paged structural evidence, gaps, capture label, and links | Partial: no index, tail, complete trace store, annotation, or multi-Run field. |
| Nexus | Timestamped capability observations, non-binding plan preview, typed request, and ticket stream | Partial: observations and tickets are process-local and not restart-complete. |
| Loom | Immutable Scroll/Pattern-revision reader, station/permission outline, optional Mermaid lens | Partial: fixed registry reader without independent Spell identities, editing, teaching, or publication. |

The shell owns navigation, source identity, pending-consent count, and transient notices; an
instrument owns route-local presentation. `/scrying`, `/reliquary`, `/bindings`, and ambiguous
unversioned Loom detail are deliberately not routes. Scrying is Orb's act, not another instrument.
Artifact references and configuration observations are contextual projections, not browser custody
or configuration authority.

The browser shell may retain drafts by exact session and the last selected Orb destination for
its own lifetime. This is recoverable navigation state, not a durable dossier or execution truth.
Cross-instrument links preserve an explicit Run and selected event where supported; returning to
Bridge focuses that Run's turn. A stale or unavailable selection is reported, never silently
replaced with another Run.

[Circle](../divination/altar/circle.md) is likewise not a separate instrument or route in the present
contract. One Bridge séance may contain many Invocation/Run projections; a future Circle focus may
compose authorized Loom, Nexus, and Orb lenses around exactly one of them without importing their
authority into browser state. The current run strip is only its delivered seed.

### Reading hierarchy and visual direction

The Altar's visual direction is a quiet observatory: the work supplies the focal point, while
restrained surfaces, typography, and fixed brand art supply identity. The five instruments keep
their single-word navigation labels. They do not become five copies of a dashboard, a universal
graph, or separate owners of the same action. Each has a different primary reading task:

| Instrument | Primary reading order | Role of a graph |
| --- | --- | --- |
| Atlas | Undertaking and next step; concerns and their current assessment basis; decisions and related activity | An optional selected-concern relation lens, preserving assessment citations separately from merely related references. |
| Bridge | Conversation and offered text; the exact Run's reply, consent or unresolved admission; next draft | No default graph. A future Circle composes authorized lenses around one Invocation. |
| Orb | Selected Run and capture limits; ordered evidence; selected record; bounded delegated jobs | Recorded subject lanes may aid reading order; they never invent elapsed time, causality, or a complete traversal. |
| Nexus | Snapshot and containment; observed capabilities; explicit preview and request; ticket and physical observations | A native board remains primary. Planned evictions and launches are more useful than an inferred topology map. |
| Loom | Exact registered revision and entry; stations and allowed successors; selected station; immutable identity | A read-only score can explain declared branches, joins, and loops, using the same permission data as its outline. |

This is the composition target, not a delivery claim or a second implementation specification.
The [Altar guides](../divination/altar/index.md#presentation-direction) own worked reading and
stress scenarios; [State](../state-of-the-work.md#altar-and-observability) distinguishes current
forms from later presentation work.

Use one dominant work area and disclose secondary identity, history, or raw records as needed.
Consent, unknown outcomes, capture gaps, containment, and preview consequences remain visible at
the point where they affect a choice. A selected inspector starts with the selected object's
identity and meaning, not an unexplained action. Preserve a valid opener on return, and give
keyboard users a focusable start of the detail plus a route back to the selected record. New
activity does not take a reader away from older work without an explicit return-to-latest action.

Reading text and controls use legible system typography; serif headings and monospace identities
have bounded roles. Reduce competing glow, nested frames, repeated metadata, and decorative
motion before adding more cards. Dense event reading and spacious conversation may use different
spacing within the same native CSS system. Essential meaning never depends on tiny captions,
colour, hover, or motion. Large illustration belongs at the empty entrance, away from operational
evidence and consent. Fixed art retains its own provenance; a quieter footer does not remove
licence or source-distribution obligations.

Graph and list are two views of the same supplied identities and relations. In Loom an edge means
only a declared permission: placement cannot invent a branch condition, read/write effect, or
observed transition. In Orb order and subject lanes describe retained records, with unknown
subjects and gaps explicit across the view. Equal spacing is ordinal unless a served timestamp
supports an explicitly labelled time axis. Job and Run sequences remain separate unless the
server supplies their correlation. In Atlas, the meaningful chain is concern, assessment, cited
reference, and activity destination; a shared destination cannot collapse the reference records
or make an uncited relation into evidence. A selected-concern list precedes any optional diagram
until the diagram demonstrably answers that same question better.

At narrow widths, start from a readable outline or list instead of shrinking a graph's labels.
Keep selection equivalent across views and preserve an explicit user choice where it remains
usable. The production renderer must satisfy the existing semantic-twin, lifetime, and editing
gates; a hand-drawn example is not its admission receipt. Unknown, stale, empty, filtered-empty,
denied, and failed reads remain distinguishable. Evaluation includes exact cross-instrument
return, keyboard-only reading, long text and identities, 320 CSS-pixel reflow, 400% zoom, reduced
motion, and contrast in bright and dim conditions. These checks do not promise remote-device
access, a second supported palette, or localization.

Implement in three bounded stages: improve hierarchy over existing contracts; admit the shared
Loom/Orb supply and renderer with equivalent semantic views; then add separately owned server
contracts where larger collections, complete fold membership, event seeking, physical impact
mapping, or restart recovery require them. Hidden DOM rows, geometric clustering, a new request
identity, or persuasive copy cannot supply those contracts.

### Atlas and continuity across Invocations

Atlas is the Altar's map of persistent undertakings. Its server-owned Project aggregate holds a
brief, concerns, attributed assessments and decisions, a proposed next action, and explicit
references to existing Bridge sessions or Runs. A Project may begin without a conversation or Run
and may describe continuing stewardship. Its identity survives individual Invocations. It owns
neither a reusable Composition or Pattern nor a Suite's live coordination.

The first Atlas is a native list and detail board. Bridge retains conversation and consent, Orb
retains execution inspection, Loom retains exact scores, and Nexus retains physical readiness.
References provide navigation between these instruments; membership is explicit, never inferred
from geometry, tags, prose similarity, or a selected browser tab. Linking a session or Run neither
injects the Project dossier into model Context nor changes execution ownership or permissions.

Project lifecycle is `active`, `paused`, or `closed`, with explicit reopening. These are planning
states: they neither cancel admitted Runs nor enforce a future admission pause. A proposed next
action is recorded text, not a queued Intent. Opening a reference performs navigation only.
Continuing a next action offers linked conversations or an explicit conversation chooser with an
inert Project return hint. Navigation never selects an unrelated latest conversation on behalf of
that Project. Multiple concern references to one conversation remain separate evidence relations
but share one continuation destination.

A concern states a question or acceptance condition. Its attributed assessments retain the
statement, criteria, and brief revision actually judged, the rationale, and any explicitly cited
Atlas references. A recorded `sufficient`, `insufficient`, or `disputed` judgment is the author's
assessment, never an automatic consequence of Run success. No assessment means `unassessed`.
Changing the brief or concern makes an older assessment visibly require review without erasing
its original basis. Decisions and assessments append; earlier judgments remain inspectable.
Board summaries distinguish current insufficient and disputed judgments from unassessed concerns
and stale assessments; none of these counts determines Project lifecycle or Run success.

Litestar validates every mutation under the caller's Sigil and Atlas write scope. The current
loopback bootstrap remains the security boundary, not multi-user authentication. Project reads
and writes are owner-scoped, reference admission checks the existing target, and foreign Project
identities are unavailable. Every mutation of an existing Project names its expected aggregate
version and a retry identity. An atomic version check refuses stale edits; exact retries cannot
duplicate a concern, decision, reference, or assessment. Failed or conflicting saves retain the
browser draft and require explicit reconciliation. Reads and mutation responses are fenced by
selected Project identity and component lifetime.

An unknown save outcome keeps its immutable retry payload even after a later middleware refusal.
A store-confirmed conflict carries `extra.code = atlas_write_rejected`; this follows the locked
replay check and permits draft comparison after an earlier lost response. An untagged refusal
does not establish whether that earlier write committed.

[Persistence](06-persistence.md#atlas-records) owns transactional retention and migration law;
[Atlas](../divination/altar/atlas.md) owns operation, and
[State](../state-of-the-work.md#atlas-projects) owns the delivered boundary. AI proposal generation,
automatic concern coverage, autonomous continuation, graph clustering, and implicit shared
Context remain outside this initial contract.

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

#### Snapshots, streams, and recovery

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

#### Teardown

Component destruction advances the same local authority boundary. A request that settles after
teardown cannot attach a stream, mutate component state, schedule another poll, or navigate. Loom
uses its load generation for this rule; Orb aborts owned snapshot and pagination reads as it
advances that generation; Bridge and Nexus additionally fence stream callbacks and timers.

### Closed rendering, readable form

#### Fragment descriptors

The Vessel validates `FragmentCall`s through a closed Pydantic registry and emits inert descriptors.
Svelte maps admitted kinds to compiled renderers and exposes unknown descriptors explicitly.
`{@html}` is forbidden and statically guarded. Invalid or unknown model fragments are dropped and
logged before settlement; client fallback merely contains malformed or newer descriptors. Settled
turns retain the complete validated descriptor, including props, so terminal refresh reconstructs
the same compiled component rather than preserving only its key. Legacy rows that predate descriptor
retention are normalized to inert schema-zero key-only descriptors with empty props; they remain
readable through an explicit inert fallback and never enter a current-version component renderer.

#### Consent and Bridge admission

Consent appears in its Bridge context and the shell count. The client submits one typed
approve/deny intent with the configured CSRF header; the Vessel rechecks identity, state, scope,
and idempotency before resume. Snapshot application versions selected-Bridge consent authority, so
an older decision response cannot overwrite a newer snapshot; after Run cancellation the selected
Bridge immediately revokes its visible consent cards and count, then refetches its snapshot. Root
route cancellation uses the selected snapshot session as that authority rather than a route prop. A
failed refetch cannot restore the revoked local authority. Instrument attention
events are invalidation hints only: the shell always re-reads the cross-session status endpoint and
request-version fences overlapping reads, so an arriving local count never becomes global truth.
The shell's attention link opens an explicit chooser of conversations with pending consent.
Per-session counts come from the server's consent-to-Run-to-session relation; the selected
conversation never presents the global count as its own attention.
Bridge message submission likewise retains one client UUID across an ambiguous response, and durable
Run admission maps that identity to exactly one canonical Run. A replay repairs an unresolved held
turn-retention gate before publication. Within one Bridge session, process-local admission permits
that exact replay but refuses a different message while any prior Run remains nonterminal; terminal
ledger truth admits the next turn without a separate active marker. The fixed visible `Magus` Sigil
is local bootstrap context, not an authenticated person. Applying a refreshed root snapshot for the
same canonically selected session preserves the unsent draft. Drafts and immutable unresolved
submission envelopes survive instrument navigation within the browser shell, separately for each
session. A later middleware refusal cannot establish that an earlier unknown admission did not
commit. Retry explicitly resends that same envelope; a new offering cannot replace it before
authoritative resolution. An in-flight response settles browser recovery state even if its view
has unmounted. Leaving the browser document warns while drafts or unresolved admissions remain;
this initial recovery state does not claim persistence across reload or browser termination.

#### Nexus request and refresh identity

Nexus retains an ambiguous transition request UUID per target, so inspecting another target cannot
discard the only safe retry identity. A lost-ticket conflict retains that UUID and refuses a fresh
physical launch; only a definitive non-conflict client rejection clears that target. Authoritative
refresh rebinds the inspector to the exact request id so a settled ticket cannot leave stale
pre-refresh transition detail selected. Board
refresh remains single-flight, but a refresh requested while one is in flight marks a dirty trailing
pass; the settling read cannot erase a newer invalidation.

#### Renderer and native CSS boundaries

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

### Decision lock and reopening gate

A greenfield review compared React 19 with Vite, Node with Bun, native CSS with Tailwind,
shared with separate Loom and Orb renderers, and a Rust/Wasm frontend. It reaffirmed the following
architecture. The renderer and editing admissions below govern prospective work; the current
instruments remain the narrower projections described above.

- **Svelte 5 with static SvelteKit remains the Altar framework.** React's more explicit effect
  diagnostics and React Flow's tagged renderer changes are real advantages, but renderer changes
  are not domain commands. They did not establish that Svelte cannot preserve the same authority,
  recovery, accessibility, route, and release contracts with less total maintenance.
- **Node 24.20 with npm 12.0 remains the only verified JavaScript build grammar.** Bun is not a
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

Reopening requires evidence of a failed product contract. Popularity, hiring pool, model-training
volume, community enthusiasm, articles, polls, toy examples, source-line count, bundle size and
isolated microbenchmarks may suggest an investigation; they cannot settle it. Reopen the Svelte
decision only when an executable product-shaped receipt
shows that the accepted stack cannot meet a required security, packaging, accessibility,
deep-link, recovery, lifecycle, or measured workload contract and a named replacement passes that
same contract. A replacement must also preserve every existing Litestar route, generated API,
focus-reset, asset-mount, API-404, notice, and release-artifact gate.

#### XYFlow admission

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

#### Loom workload and editing gate

Loom’s designed editing workload is a workflow score. The registered Bridge and delegated-rite
Scrolls place five and three stations over six and three permitted edges, respectively; the latter
includes the [delegate's durable re-entry loop](28-workflow.md#pattern-identity). Admitted Suite
grammar keeps this workload in the tens to low hundreds. Orb is bounded by folding rather than by
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

### Canonical appearance and bounded palette configuration

The canonical Altar has one complete built-in appearance: **LychD Dark**. Dark is the product
default and the only appearance Core currently designs, releases, and supports. The document and
native controls use a dark colour scheme; Core does not follow `prefers-color-scheme`, expose a
light/system selector, or create presentation state merely to imply choice. “Readable by day and
night” remains an acceptance target requiring contrast plus bright- and dim-environment browser
receipts, not a conclusion inferred from dark tokens.

The styling boundary nevertheless stays configurable in one deliberately narrow direction. A
future operator-local palette may provide a partial map over an allowlisted set of semantic colour
roles—for example page and panel surfaces, primary and secondary text, focus/rune, ready, active,
warning, refusal, borders, and decorative accent. Resolution starts from the complete pinned LychD
Dark palette, applies valid overrides, and falls back per missing value. The public configuration
names semantic roles rather than CSS variable or selector identities; Frontend owns their meaning,
while [Configuration](12-configuration.md) must admit any future typed source and precedence before
it is delivered.

An override value uses a restricted, resource-free colour grammar and cannot contribute selectors,
declarations, functions that fetch resources, `url()`, fonts, layout, visibility, opacity,
animation, HTML, Svelte, JavaScript, routes, or assets. Validation preserves required contrast,
visible focus, forced-colour behavior, non-colour status distinctions, and the legibility of
consent, refusal, fault, unknown, and evidence states. Missing roles inherit their canonical
values; an explicitly invalid map is refused before application rather than producing a
half-themed Altar.

Components, diagrams, and overridable artwork consume the resolved semantic palette or declare
themselves fixed LychD brand assets outside it. Mermaid, browser chrome, native controls, static
art, and generated surfaces cannot keep an undisclosed second palette. A future named palette
package may serialize this same finite map only after Extensions and Packaging admit its
provenance, licence, static build, compatibility, and accessibility receipts; it never opens a
runtime CSS plug-in surface.

Palette choice is local presentation configuration. It never changes a Run, Pattern, event,
artifact, consent, authority, status, or retained evidence, and it cannot remove their textual and
structural cues. The current implementation has only the fixed LychD Dark palette and no operator
override source; [State](../state-of-the-work.md#altar-and-observability) owns that boundary.

### Interface locale and content language

The future localization boundary uses ordinary framework-neutral message catalogues and
locale-aware formatters for Altar chrome. Canonical route, API, Pattern, Spell, Run, event, status, and field
identities remain stable and untranslated. Components consume message identities and typed
parameters; a translator or model never supplies HTML, Svelte, executable templates, or domain
keys. Catalogues are reviewed static client assets under the same FOSS, notice, CSP, and release
boundary as the rest of the Altar, not a runtime translation service.

The FOSS reference Altar deliberately targets English as its sole required interface locale. This
keeps the reference implementation, review surface, release evidence, and contributor obligation
small; it does not permit English grammar, word order, or left-to-right layout assumptions to enter
canonical identities or application contracts. A multilingual interface remains permitted future
work rather than a current Product goal. Another locale may enter later as an optional, reviewed
static catalogue and formatter contribution with exact compatibility, provenance, licence, and
accessibility evidence. It is not a skin, arbitrary client-code plug-in, or support claim merely
because a community translation exists.

Under that contract, locale resolution is explicit Altar choice, then an admitted Principal preference, then a browser
language hint, then an admitted operator default, then English. The current loopback `magus:*`
bootstrap is not an authenticated Principal and may retain only a presentation-local choice.
Applying a locale sets document `lang` and direction and governs dates, times, numbers,
pluralization, visible copy, and accessibility text. Every admitted locale owes fallback,
missing-message, overflow, keyboard, screen-reader, and bidirectional-layout receipts; a catalogue
claim alone does not establish support.

Interface locale is separate from content language. A Magus may use a Slovak Altar while reading
an English prompt, original Japanese evidence, or another language selected for speech, image,
video, or music. Changing locale never translates retained content. Translation is an explicit,
attributed semantic transformation that preserves source text, target language, implementation
revision, declared loss, and authority. Persona language or a model's detected language never
silently changes the Magus's interface. Speech input and output may support additional languages
while the Altar chrome remains English; speech capability does not imply an installed or supported
interface catalogue.

The delivered Altar remains English-only: it has no message catalogue, locale selector,
Principal-preference binding, or right-to-left receipt. Browser-native formatting that happens to
follow a device locale is not this contract; [State](../state-of-the-work.md#altar-and-observability)
owns the exact material boundary.

### Build boundary, security, and reopening

Development runs Vite on `127.0.0.1:5173`, proxying `/api` and `/schema` to the loopback Vessel.
Production serves static Atlas, Bridge, Orb, Nexus, and Loom shells; unknown APIs and retired paths stay
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
GenUI tests; Python routes, controllers, consent, SSE, fixed root assets, and the instruments;
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
