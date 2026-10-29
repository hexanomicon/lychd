---
title: 15. Frontend
icon: material/language-html5
---

# :material-language-html5: 15. Frontend

!!! abstract "Context and Problem Statement"
    The Altar gives a browser form to conversation, bounded Run evidence, capability transitions,
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
- Atlas, Orb, Nexus, and Loom are work routes; Bridge is a shell-owned conversation panel available
  beside every work route. Existing Bridge URLs retain explicit server fallbacks and exact session,
  Run, consent and focused-application navigation. Generated UI is closed descriptors, never model-
  or extension-supplied HTML, JavaScript, Svelte, or imports.
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
| Bridge | Session selection, single-active-Run text admission, reconstruction, semantic stream, consent, closed fragments, and bounded Creation investigation intake/report focus | Partial: text only; live reconstruction and tokens are process-local. |
| Orb | Paged Run catalogue, parallel graph field, and bounded selected-Run evidence feeds with gaps, capture labels, and links | Partial: no complete trace store, nested subworkflow identity, or annotation. |
| Nexus | Timestamped capability observations, non-binding plan preview, typed request, and ticket stream | Partial: observations and tickets are process-local and not restart-complete. |
| Loom | Immutable Scroll/Pattern-revision graph and station/permission outline | Partial: fixed registry reader without independent Spell identities, editing, teaching, or publication. |

The shell owns navigation, source identity, pending-consent count, transient notices, and the
persistent Bridge presentation. Each other instrument owns its route-local presentation.
`/scrying`, `/reliquary`, `/bindings`, and ambiguous unversioned Loom detail are deliberately absent
from the route contract. Scrying names Orb's act. Artifact references and configuration
observations let the browser show context without acquiring custody or configuration authority.

The browser shell retains drafts by exact session and the last explicit Bridge session path
for its own lifetime. The global Bridge control opens that session without a Run hint.
The global Orb link opens the parallel Run field at `/orb`. Until an explicit Bridge session
path is selected, its global link stays at `/bridge`;
the server's default session does not establish browser navigation memory. This is recoverable
navigation state, not a durable dossier or execution truth. Cross-instrument links preserve an
explicit Run and selected event where supported; Orb's contextual Bridge return focuses that
Run's turn. A selected historical consent event may also carry a bounded Consent reference to
that exact session and Run. Orb retains only the syntactic historical reference, without resolving
current status, review, or decision authority. Bridge resolves the exact Consent and requested Run
against its currently authorized session snapshot; a missing, settled, foreign, or unbound request
is visibly unavailable and never falls back to another request. Request focus belongs to that
navigation and does not recur on stream refresh. An event return preserves the originating Run
and selected record. A stale or unavailable selection is reported, never silently replaced with
another Run.

[Circle](../divination/altar/circle.md) is likewise not a separate instrument or route in the present
contract. One Bridge séance may contain many Invocation/Run projections; a future Circle focus may
compose authorized Loom, Nexus, and Orb lenses around exactly one of them without importing their
authority into browser state. The current run strip is only its delivered seed.

### Creation investigation within Bridge

The existing `/bridge` route may focus the protected public-source Creation investigation through
an explicit `investigation` query: `new` opens intake; a case UUID selects retained state. This is
Bridge admission and a Composition-owned reply, not a sixth instrument or ordinary chat turn.
Creation creates its own admission and Session. Orb keeps the exact returned Run's retained
evidence; Atlas next steps remain recorded text, never queued admission. The global Bridge link
continues to return to the last explicit ordinary session without this focus. Investigation
navigation must preserve ordinary session drafts, unresolved offerings and consent state.

Only the case UUID belongs in navigation. Source text and the immutable submitted body remain
transient browser-document state, without hidden durable storage. Once POST may have left,
freeze its UUID/body; an ambiguous result never causes automatic retry or a new UUID. Explicit
Check reads that case, and a 404 while admission may still be in flight does not resolve the
ambiguity. Identical replay is an explicit action available only while the original body remains;
reload cannot reconstruct it from a UUID. Editing authorizes a deliberately different request.

The browser uses generated Creation transport and existing authentication/Origin/CSRF gates.
The local role owns its cases; navigation grants no authority. Case reads use current authority
through awaited storage, guard late responses against changed selection, and clear protected
material on refusal. The detail read may perform existing expiration and transport retained
operational records; it is not the non-mutating Orb metadata feed. Render only validated retained
request, candidate, citations and separate verdict as text. Run completion, native case status,
external assessment and owner disposition remain distinct. Later changes require explicit
Refresh; viewing grants no continuation, cancellation, feedback mutation or successor action.

The report may explicitly load the existing protected historical feedback projection. It starts
not loaded and performs no automatic read on mount, selection or later changes. The server's
current assessment and decision IDs select current judgments; a newer assessment cannot inherit
an older hold. Empty unassessed, external not-assessed, review-required, refused and unavailable
states remain distinguishable. Selection changes and teardown fence and abort owned reads;
current-authority refusal clears protected feedback. Render the current report, owner reason and
supplied annotation coverage as escaped text, validating unknown dictionary fields before display.
Native acceptance, external assessment and owner disposition confer no browser execution or
promotion authority. An explicit reload uses current read authority; disclosure appends no feedback.

### Public notes within Bridge

The `/bridge` route may focus explicit public-note work through one `notes` query:
`manage` opens metadata, `new` opens intake, and a record UUID selects exact metadata. Invalid,
duplicate or simultaneous investigation/note focus is unavailable without effect. The focus keeps
ordinary Session drafts, unresolved offerings and Consent separate; the conversation rail is not
an Archive source list. Only mode/record identity enters navigation, never note text or a request
body. This adds no instrument or automatic conversation-to-memory admission.

Reload recovers the authorized configured profile and bounded all-lifecycle metadata pages from
the server. Exact-record reads work independently of the loaded page, so the browser need not own
record custody. The management API provides no public-note text for preview or prefilled editing.
A correction supplies complete new text under a different immutable source revision and needs
separate promotion. Revocation retains the minimum source identity; it does not erase earlier
answers or backups.

An independent authorized current-default projection identifies the admission engine's actual
Pattern and complete managed-profile match. Show requested, not requested, unavailable and failed
states distinctly. Configuration is neither readiness nor the next routed Run; a historical Run
retains its own admitted profile. Browser revision checks or fetching conversation history cannot
supply this projection.

Every intake freezes its UUID, exact UTF-8 digest, observation time and public declaration before
submission. Only an explicit identical intake replay may reuse that retained body; navigation,
refresh or failure starts no retry or replacement UUID. A metadata match recovers a source record,
not proof of which intake occurrence committed. Lifecycle actions pin the record and expected
version, with no optimistic state or replay. After an uncertain response, Check reads current
metadata; an unchanged version or missing record cannot establish that an in-flight action failed.
A newer version establishes current state, not causal authorship. A fresh explicit decision may
use the recovered version without reclassifying the earlier occurrence as successful or rolled back.

Drafts and frozen bodies remain transient to the browser document, with departure/reload warnings.
GETs are abortable and late responses remain fenced by selection, profile and lifetime. Current
authority refusal clears protected material. The focus uses generated transport, existing local
Origin/CSRF/access gates, escaped text, semantic forms, keyboard controls and visible uncertainty.
Intake, metadata and lifecycle management create no browser ledger, consent authority, recall
operation or model request.

A separate explicit preparation section may operate on the exact selected public-note revision.
It discovers configured generation metadata without preparing anything. **Register configured
generation** is a named shared-generation mutation using that exact reference; it neither embeds
nor reactivates a retired generation. **Check preparation** is a protected metadata-only POST for
the exact generation and source reference. Neither opening, navigation, checking nor promotion
registers a generation or derives a note automatically.

**Prepare this promoted revision** requires an explicit review of the current profile, generation
and full source reference and may incur one local embedding operation under Archive authority.
It sends no source text from the browser, activates no model and chains no recall or answer Run.
Its existing request has no occurrence UUID or caller attempt-version precondition; row and attempt
versions describe latest durable state, not authorship or the cost of one HTTP invocation. A lost
response stays unknown after a status check. A further explicit preparation decision may repeat
compute even with the identical body; only the server can establish eligible completed replay.
DB-observed expiry does not prove cancellation or stop earlier work.

Frozen preparation references and status remain document-local. Historical status after a
lifecycle change needs the original exact source reference; reload cannot invent an old lifecycle
version. Local preparation and note-write gestures are serialized. Profile, generation, selection,
operation and lifetime fences reject stale responses; current authority refusal clears protected
management and preparation display. Departure or read abortion grants no cancellation or rollback
claim. Preparation adds no browser ledger, bulk/background worker, automatic retry or readiness
service.

The separate `recall` notes focus is an explicit sources-only consumer of Archive's schema2
semantic API. Opening, typing, navigation and metadata refresh perform no semantic query or source
resolution. Authorized profile/configured-generation discovery is metadata only; it establishes
neither semantic opt-in, an active registered generation, eligible derivations nor runtime warmth.
The operator separately prepares the runtime, generation and promoted sources under their current
owners. Recall never activates, registers, derives, falls back or changes ordinary Bridge3.

One explicit submission freezes a fresh request UUID, exact query/namespace/generation, user-supplied
finite minimum similarity and visible result/character bounds. It may compose recall with exact
receipt-digest resolution in that same gesture. Display only the resulting currently authorized,
ordered source projection with source/revision identity, similarity and coverage/omissions;
similarity grants no answer-confidence or truth claim. Selection time and resolution time stay
distinct. Source bodies, queries and request bodies never enter navigation or browser persistence.

After an unknown query outcome, an explicit check may inspect only the frozen full request without
inference or hydration. An absent receipt does not establish that an in-flight query failed. A
recovered selection needs explicit current-source resolution; there is no automatic recall retry
or exactly-once inference claim. Current refusal/profile change/lifetime replacement fence late
responses and clear protected projections. Waiting is HTTP presentation state, not a durable Run;
leaving or aborting a request does not claim to cancel model work or undo retained selection.

### Scavenger finite observation application

`/scavenger` is an application working view within the Altar, separate from the five
operator instruments. Its optional `observation` query contains only a retained admission UUID.
Opening or refreshing it reads protected application state; it never acquires a source.
The selected Scavenger 3 / observe_market 2 configuration owns the finite Bazoš PC RSS profile;
omission is visibly unconfigured, not ready or silently routed to chat.

Explicit submission supplies every CampaignSeed fact and a literal initial filter. Freeze the
request UUID and complete body before sending. An uncertain response remains unconfirmed;
only an explicit Check or identical replay may reconcile it, never an automatic retry or new UUID.
Request bodies and private drafts remain document-local, without URL, storage or Bridge history
copies. Leaving/reloading warns about unresolved actions and cannot imply cancellation.

The canonical seed document is also supplied as protected text for exact display: JSON number
parsing in a JavaScript client must not round retained 64-bit budget or preference facts. It is
rendered as escaped text and is subject to the same custody, clearing and deletion boundary.
Scavenger routes opt out of generic request/response body capture, including operator-enabled
body diagnostics, and their responses forbid HTTP storage. SQL parameter diagnostics are hidden; SQL engine result-row diagnostics are disabled even at a
requested DEBUG level. Application transaction/decoder failures expose closed reasons without
payload-bearing exception chains.

The protected field presents source/time/coverage/omissions, all occurrences and local filtered
counts, duplicates, missing titles and unassessed facts. Item locators are inert displayed text,
with no prefetch or preview. Re-filtering uses the server's versioned literal projection over the
same retained digest; changing the filter does not acquire. Current pending, consent, unavailable,
unknown and deleted states remain distinct, including empty field versus zero matches.

The existing native consent card and Core verdict endpoint retain review-binding and current
caller authority; the application adds no decision authority. Run cancellation remains an explicit
Run action. Deletion is a separate confirmed exact-digest action and is offered only for a supplied
terminal disposition. Unknown custody cannot be cleared by deletion or by a new request. Current
refusal clears protected content, and changed selection/teardown fences late reads. No browser
connection, refresh, rendering, configuration observation or Run completion substitutes for native
consumer commitment. State owns delivery, including any unqualified browser or restart boundary.

### User-specific working interfaces

The [Ward account and profile contract](38-iam.md#profiles-and-working-interfaces) permits different
Users of one instance to receive different applications, navigation, screens, and workflow views.
The built-in operator instruments are not a compulsory interface for every household member,
guest, or employee. A shared client may select named working views, and a dedicated client may
present a narrower application experience; neither becomes a separate identity or effect authority.

The current Principal and objects determine which projection the server may supply. The client
then applies admitted presentation defaults and device affordances. A profile label, an open route,
or a hidden control grants no permission. Different working views preserve a Run's identity and
admitted score, and offer only actions allowed by both workflow state and current authority.

Client connection choice is not mobile-only. Browser and native clients may offer saved
instance/account selections and refresh their working interface during use. A browser may navigate
to an instance-served frontend or, where explicitly supported, select another backend within a
persistent client; dedicated fixed-instance clients remain valid. These are optional client
designs, not requirements for a universal client or simultaneous connections. Interface refresh
uses supported presentation contracts; it does not admit arbitrary remote UI code.

Selecting another account or instance is distinct from changing a working view, or reaching the
same verified instance through another network address. Each selected context uses its own
applicable credentials and current Ward authority. A switch does not itself transfer history,
admitted sessions, or active work, imply cancellation of server work, or authorize replay at the
new destination.

Client state must remain bound to the selected instance and account. Switching either, signing
out, or losing access clears or isolates affected drafts, cached records, subscriptions, and
pending presentation so another user cannot inherit them. Outstanding requests and callbacks
remain bound to their originating context: late results cannot populate another context, and
pending submissions cannot be retargeted by a connection change. Reconnect revalidates access
before receiving protected state or submitting work. These requirements do not turn the fixed local
bootstrap into a delivered multi-user browser surface; [State](../state-of-the-work.md#remote-iam)
retains that boundary.

### Reading hierarchy and visual direction

#### The shared workbench and Bridge dock

The top masthead presents Atlas, Orb, Loom and Nexus as icon-and-label navigation. Applications
is a bounded disclosure for Canvas and other admitted applications; hover, click and keyboard
focus can open it, Escape dismisses it, and moving into the menu keeps it reachable. Bridge is
an always-available conversation surface, not a competing top-level instrument tab. Existing
`/bridge` links remain valid compatibility and focus destinations; exact session, Run, consent,
Project, investigation and public-note intent must survive the composition change.

The dock's persistent edge chevron opens or collapses it; the masthead has no second toggle.
New layouts start on the left, preserving a valid saved side. It can occupy either side and resize through a pointer or keyboard
separator. A wide workbench allocates real width beside it; it does not cover the work. A narrow
workbench uses an explicitly modal overlay with focus containment, Escape and an opener return.
Width, side and collapsed state may be remembered as bounded local presentation preferences;
conversation text, attachment bodies, consent and request identities do not enter that store.
Resizing preserves the working view and Canvas camera scale instead of rearranging document
objects or fitting the board automatically. Collapsing the dock or changing an instrument neither
cancels a Run nor admits another offering. The selected conversation and its transient recovery
state remain alive across ordinary work-route changes. Current-authority refusal still clears
protected projections under the existing rules.

The canonical LychD Dark workbench uses an untextured black work plane, neutral graphite chrome,
icy-blue interaction and focus, restrained green confirmation/activity, and bounded deep-purple
secondary surfaces. Text stays neutral and readable. Icons supplement visible labels. Surfaces
use crisp geometry and restrained separators; status, consent and uncertainty remain explicit
words rather than colour or decorative motion. Canvas has no dotted background. Its optional
freehand lasso selects whole intersecting objects without adding the selection loop to source
ink; rectangle and semantic-list selection remain available. A selected scope is still only a
proposal boundary, never a model transmission or execution permission.

The Altar should read as a quiet observatory. Work holds the focal point; restrained surfaces,
typography, and fixed brand art provide identity around it. Its five instruments retain their
single-word names, with Bridge always available as the conversation dock. Their distinct reading
tasks determine their form, rather than a repeated dashboard or universal graph. No instrument
becomes another owner of an existing action:

| Instrument | Primary reading order | Role of a graph |
| --- | --- | --- |
| Atlas | Concerns, their decomposition and where they are addressed; current assessment basis; optional Project brief and next step | An optional selected-concern relation lens distinguishing decomposition, sources, addressing, and assessment citations. |
| Bridge | Conversation and offered text; the exact Run's reply, consent or unresolved admission; next draft | No default graph. A future Circle composes authorized lenses around one Invocation. |
| Orb | Parallel Run groups; selected Run and capture limits; ordered evidence; selected record; bounded delegated jobs | Zoom discloses supplied Run, station, occurrence, and record membership; declared permissions and observed records remain distinct. |
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
observed transition.

In Orb order and subject lanes describe retained records, with unknown
subjects and gaps explicit across the view. Equal spacing is ordinal unless a served timestamp
supports an explicitly labelled time axis. Job and Run sequences remain separate unless the
server supplies their correlation.

In Atlas, decomposition, source inspiration, and where a
concern is addressed remain distinct from the evidence chain: concern, assessment, cited
reference, and activity destination. A shared destination cannot collapse the reference records
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

### Canvas portable board authoring

[Canvas](../compositions/canvas/index.md) is the Composition for visual board authorship and
reviewed transformations. Its first `/canvas` profile is a browser authoring draft with explicit
portable document import/export. Native SVG captures actual ink and projects draft objects;
the existing Loom/Orb renderer and read-only contracts are unchanged. This bounded authoring
surface does not introduce a second graph engine or make layout a source of workflow meaning.

Canvas owns the file/proposal schemas and pure admission rules under its Composition source.
The browser holds disposable authoring state; it claims no server retention, publication,
execution or native media custody. Text remains native editable text, independent of optional
local PNG artwork. Imported bytes are bounded and validated; remote image URLs, SVG, HTML and
executable proposal content are unavailable. The real API exports the schemas for generated
client aliases and provides stateless CPU validation, not a board persistence service.

Selection capture binds exact object identities, world bounds and scene revision to source
geometry and a same-revision crop. Proposals may change selected objects and create explicit
connections to supplied context, while leaving other objects untouched. Preview is inert;
acceptance is atomic and reversible. Any committed edit invalidates an older proposal. Undo/redo
create fresh revisions. Arrangement is bounded, respects pins and measured dimensions, pauses
during gestures and records one deliberate edit. Keyboard object controls and reduced motion
remain equivalent ways to work. Model transport, microphone capture and generated imagery
are separate capabilities with explicit unavailable states until independently qualified.

### Atlas and continuity across Invocations

Atlas maps Concerns: what needs attention, how it decomposes, where it is addressed, and what
supports a judgment. A Concern can begin with an idea or question before any Project exists.
The independent Concern contract is [Designed](#independent-concerns-decomposition-and-addressing).
The initial server-owned Project aggregate holds a
brief, concerns, attributed assessments and decisions, a proposed next action, and explicit
references to existing Bridge sessions or Runs. A Project may begin without a conversation or Run
and may describe continuing stewardship. Its identity survives individual Invocations. It owns
neither a reusable Composition or Pattern nor a Suite's live coordination.

Atlas begins as a native list and detail board. References connect it to conversation and
consent in Bridge, execution inspection in Orb, exact scores in Loom, and physical readiness in
Nexus. Those links make navigation possible without changing ownership: membership must be
explicit, never inferred from geometry, tags, prose similarity, or a selected browser tab. Linking
a session or Run neither injects a Project dossier into model Context nor changes execution
permissions.

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

### Independent Concerns, decomposition, and addressing

A Concern has its own stable identity, authorization owner, revisioned statement, and optional
criteria. It can stand alone, concern an idea or an application, or participate in explicitly
associated Projects. Project membership is optional context; it does not establish Concern
identity or authorization. A shared Concern retains one identity across its relations. A materially
different question or acceptance basis gets a distinct Concern with an explicit derivation link.
Neither a Project nor a Conversation, Run, Composition, or Covenant is required to create one.

A dedicated Concern surface lets a reader begin with the question itself: inspect its meaning
and criteria, break it down, find what remains unaddressed, follow the parts to their destinations,
and inspect the judgments and evidence. A Project view gathers the same material in its brief's
context while preserving that independent entrance.

The relation contract distinguishes:

| Relation | Meaning |
| --- | --- |
| Decomposition | A parent question is developed into smaller Concerns, with a reason for each part and any remaining scope made explicit. |
| Addressing | An exact part of a proposal, decision, document, application contract, implementation, or procedure is intended to address a Concern, with its contribution and limits stated. |
| Source | A Concern was inspired by or derived from identified material, or is constrained by a rule explicitly adopted in its context. Inspiration and adopted obligation remain distinguishable. |
| Assessment citation | A judgment uses particular retained references as evidence against an exact Concern and context basis. |

Decomposition is acyclic and may share a child between parents. A view preserves those shared
identities instead of duplicating the questions. Decomposition does not imply complete partition,
execution order, or sufficiency: the parent retains its own criteria, unresolved remainder, and
judgment even when every child has a sufficient assessment. General relatedness is not a
decomposition or an addressing claim.

Addressing is many-to-many. Each relation retains its author, rationale, exact target locator and
revision or content identity, and whether it names proposed or accepted material. The map exposes
missing, partial, conflicting, unavailable, and changed targets without equating a link with
implementation or proof. Decisions can name the Concerns they address. For application design,
this account explains how the parts serve the Concerns and which needs still have no home. An idea
or ordinary application need not become a native LychD Composition to be mapped. When the target
is a native Composition or Pattern, [Workflow](28-workflow.md#concerns-and-application-design)
keeps its contract and publication authority with that owner.

An assessment binds the exact Concern revision and any context it judges. When it relies on
decomposition, child judgments, source obligations, or addressing relations, it retains those
specific revisions as part of its basis. Relevant changes require review while preserving the
original judgment. A judgment made for one Project's brief does not silently become a judgment
for another context. Summaries retain the difference between an addressing claim and assessed
sufficiency; child counts and completed Runs cannot create a coverage verdict.

Concerns are authored directly or proposed through decomposition or selected source material.
An idea or Project may develop its own Concerns and its own Covenants. A Concern may motivate a
Covenant; an adopted Covenant may in turn suggest further Concerns. LychD's Covenants are an
optional source of inspiration, with no default import or authority over unrelated work.
Other sources and Concerns without any Covenant remain equally admissible.

Seeding or spawning produces attributable proposals: the used source and exact revision or
content identity, the relevant passage, and the interpretation for the intended context remain
inspectable. Acceptance explicitly creates or revises the selected Concerns and relations;
regeneration proposes a comparison instead of overwriting authored meaning. A source change
requires review of affected derivations without silently rewriting them. Generated proposals do
not adopt a Covenant, assess coverage, publish an application, or admit execution by themselves.

[Persistence](06-persistence.md#independent-concern-retention) owns retention and
migration. The initial Project aggregate and activity-only references do not implement this
independent identity, relation model, or proposal flow; [State](../state-of-the-work.md#atlas-projects)
keeps that delivery boundary explicit.

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

Browser reconstruction has three replaceable layers. A validated snapshot provides the base;
ordered deltas advance its cursor; URL, selection, layout, draft, focus, and related presentation
sit above them. Refresh, remount, a numeric gap, or `resync` replaces the projection from a
snapshot. An animation or open `EventSource` supplies no evidence of commitment.

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
schema mismatches; a local command may rewrite tracked output, whose diff still needs review. SSE stays
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

The Bridge archive rail loads at most 50 session identities per page, ordered by exact creation
timestamp and stable identity. An opaque, validated keyset cursor and visible **Load more** retain
access to older conversations. Archive queries select metadata without hydrating other sessions'
turns or model history; pending-consent counts are grouped for the requested page. A selected
conversation remains independently addressable even outside that page. This bounds amplification
across the archive, not the selected conversation's retained turns, model history, or Run list;
those still load for the selected session and need a separate retention or history-pagination law.

HTTP Run event streams reserve process-local capacity before response headers: at most four per
Run and 32 per process. Excess streams receive `429` and `Retry-After`; closing, cancellation,
and failure before the first event all release the reservation. A stream limit never drops a
settled turn or changes Run execution. Existing bounded subscriber queues still replace overflow
with explicit `resync`, and browser reconnect uses its transport backoff.

The browser also bounds pending Run envelopes to 256 while an authoritative refetch is in flight.
Overflow closes that subscription and invokes bounded snapshot recovery; teardown clears pending
envelopes and fences late completion. A permanently closed native EventSource requires explicit
recovery rather than a claim that browser retries continue. This is an envelope-count limit, not
a payload-byte limit or a deadline for the snapshot request.

The client seeds from the snapshot cursor, serially validates and reduces events, ignores applied
sequence numbers, and refetches on gap or `resync`. Its initial cursor is reducer state: the
current `EventSource` constructor does not send an explicit cursor. A run or ticket identity
mismatch, invalid data, or failed authoritative refetch permanently closes that channel. Bridge
and Nexus immediately mark the projection stale and attempt one bounded authoritative recovery;
a second failure remains visibly stale rather than animated as live. Each Bridge Run projection
retains its applied cursor and a browser-local authority generation; a delayed recovery may replace
that Run only while both still match the request it began from. Ordinary transport errors remain
transient while `EventSource` reconnects. Durable terminal Run status overrides a lagging
process-local channel. Its retained agent answer and fragments take precedence over incomplete
live deltas while the captured stream cursor stays intact; absent a retained turn, live content
remains the fallback. Only a retained agent turn retires that terminal projection from the
selected session. Token deltas and channels are neither durable nor cross-process; retained
structural Step evidence is best-effort. Nexus uses its own versioned transition envelope with the
same retention boundary and completion-driven single-flight polling. Closing a channel fences
already-queued callbacks, so an event from a superseded ticket cannot overwrite the replacement
identity. Orb pagination likewise merges only when both the requested and current snapshot still
name the same Run; its Loom link additionally requires the entire valid pinned manifest to equal the
registered revision, as worker replay does.

Orb's catalogue reads metadata across Run statuses in newest-first creation-time/id pages, with
an opaque continuation cursor and at most 50 identities per request. It does not hydrate prompts,
manifests, or event histories. A selected snapshot supplies a workflow graph only when its full
pinned manifest equals the registered revision; a missing graph remains explicit.

Orb's separate retained-evidence SSE polls the ledger once per second, serving at most 100 records
per batch under the shared HTTP stream budget. Its versioned `evidence`, `reset`, and `settled`
envelopes bind Run identity, requested `after_seq`, delivered `cursor`, and the safe snapshot.
Live reads start at the snapshot's ledger head while history pagination keeps its own boundary.
`Last-Event-ID` overrides the initial query cursor on reconnect. Metadata-only updates may retain
the cursor; omitted sequence intervals remain explicit gaps. A future cursor requires snapshot
replacement. Ledger-terminal status drains the currently retained account before `settled` closes
the feed; this does not promise that every best-effort observation was retained. Token deltas and
private bodies never enter this feed. Slow readers delay their next bounded read without queuing
producer events. Disconnect closes the source and releases its reservation.

An optional Creation summary resolves the selected Run through its retained exact admission link.
The HTTP boundary checks current Creation read authority for every snapshot and stream poll; it
supplies only bounded metadata through a dedicated persistence read that cannot expire or settle
custody. Absence discloses neither case existence nor application configuration. Case status,
response adoption, native verdict, latest external assessment and current owner disposition stay
distinct from Run status. An earlier admission is explicitly historical: the supplied case-current
outcome may include later admissions. Metadata updates can retain the ledger cursor, and revocation
clears the summary. This does not extend terminal stream lifetime; later assessments or decisions
require an explicit authoritative refresh. Browser playback never rewinds this current metadata.

The parallel field opens at most three Run lenses and keeps at most 100 records in each. Its
counts describe loaded membership, and omitted older records remain available through selected-Run
pagination. Run changes, closed lenses, and teardown fence callbacks and abort owned reads.

#### Teardown

Component destruction advances the same local authority boundary. A request that settles after
teardown cannot attach a stream, mutate component state, schedule another poll, or navigate. Loom
uses its load generation for this rule; Orb aborts owned catalogue, snapshot, and pagination reads
and closes its streams as it advances that generation; Bridge and Nexus likewise fence stream
callbacks and timers.

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
The existing browser-shell workspace retains in-flight and uncertain consent verdicts by consent
id across refresh and navigation. Only the same verdict may retry after uncertainty, including a
later middleware refusal. Late responses invalidate their owning session for reconciliation;
newer snapshots retain authority. Unresolved decisions also trigger the document-unload warning.
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
physical launch. Only an initially definitive rejection clears that target; an earlier unknown
outcome survives later rejection. Leaving Nexus with in-flight or unresolved admission requires
explicit discard, while same-document inspector navigation retains the retry identity. Authoritative
refresh rebinds the inspector to the exact request id so a settled ticket cannot leave stale
pre-refresh transition detail selected. Board
refresh remains single-flight, but a refresh requested while one is in flight marks a dirty trailing
pass; the settling read cannot erase a newer invalidation.

#### Renderer and native CSS boundaries

Extensions have no UI source, template, script, import, or third-party sandbox surface.
Loom and Orb use one `@xyflow/svelte` adapter over their immutable semantic projections. Its
coordinates, camera, selection, and motion remain disposable presentation. The keyboard-operable
station outline, Run list, and record inspectors remain available when rendering fails. Neither
canvas admits publication, execution, connection editing, or durable layout mutation. Installation
does not discharge the lifecycle and semantic-twin admission gates below; State owns the receipt.
Plain-text source lives below `/api/v1/loom/source/workflows/{workflow}` and
`/api/v1/loom/source/patterns/{pattern_id}/{revision}` so every legal two-segment exact Pattern route
remains addressable. Exported Mermaid retains the exact Pattern key and revision in its title and
the manifest digest as inert source metadata. Mermaid source is not Pattern data or proof of
execution.

Recorded graph playback uses an explicit Run sequence cursor over loaded structural evidence.
It filters node observations and supplied Animator grant identities at that cursor, while current
Run status and connection state remain separately labelled. A grant records selection, not a
model-call duration or an Animator uptime interval. Missing lifecycle evidence remains unknown;
current Nexus readiness cannot fill a historical gap. Hover discloses semantic detail without
changing selection, cursor, authority, or the declared score.

#### Spatial Orb and tab observation history

Orb may select a spatial presentation inside the same shared renderer: compact typed marks,
stable Run territories, and curved relations on an unbounded black viewport. Territory membership
comes from the supplied Run, never proximity. Repositioning a mark changes only the current
adapter's disposable layout; it submits no Pattern or Run mutation. Loom retains its declared-score
presentation. Filters, disclosure and a semantic Run list remain available without canvas gestures.

An Animator identity supplied by a dispatch record may appear as a shared source mark. Its link
means **recorded selection** from that dispatch subject, not an active model call, traversal,
availability, or duration. A latest-record halo identifies a retained observation. Tool, Agent,
file, Portal and Soulstone shapes require their own supplied type; a station label or model name
cannot establish that type.

The parallel field may retain bounded immutable captures of projections actually received in the
current browser tab. Its bottom **Tab history** uses local observation time and declares the
available time window and capture count. Pause and seek hold one capture while ingestion
continues; LIVE resumes the newest account. Current connection and latest fetched Run status stay
separate from a captured graph. Capture playback does not reorder producer events, reconstruct
execution between observations, or claim complete wall-clock workspace history. It creates no
durable retention and disappears on reload. Closing a live lens ends its subscription without
rewriting an already authorized capture; the inspector distinguishes that historical lens from
current connection state. Current-authority refusal clears protected captures. A capture retained for inspection remains
explicit when it falls outside the bounded seek window.

Native CSS uses custom properties, cascade layers, media queries, semantic classes, and state
attributes. Type, label, icon, shape, and copy carry meaning without colour; the stylesheet has a
skip link, visible focus, hidden labels, narrow layout, and `prefers-reduced-motion`. Inspectors
restore their live opener after closing when one exists; deep links use router focus reset.
Tailwind, Sass, project-owned PostCSS, and a parallel styling vocabulary are forbidden. Transitive
Vite packages in the lockfile are not a styling API.

### Decision lock and reopening gate

A greenfield review compared React 19 with Vite, Node with Bun, native CSS with Tailwind,
shared with separate Loom and Orb renderers, and a Rust/Wasm frontend. It reaffirmed the following
architecture. The renderer qualification and editing gates below remain binding on the
read-only projections described above and any later expansion.

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

The shared XYFlow adapter remains subject to a measured qualification gate. Its [shared pan/zoom
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

Folding keeps a field readable at every camera scale. An unreadable field cannot serve as
evidence, regardless of the renderer. Bounding the rendered set follows from that reading rule
and is what keeps a DOM renderer sufficient.

Folding follows structure the authority already declares—for Orb, Run, then station subject, then
occurrence, then event, with delegated jobs as their own declared groups. Zoom may choose among
these levels; explicit detail controls provide the same operation without a zoom gesture. A group states
its loaded membership count, names any unknown total or unloaded members, carries its declared name,
and remains selectable and expandable through the same
typed identities. Geometric or computed clustering is not admitted: proximity would assert a
relation no authority declared, and a group must never be readable as evidence LychD did not record.

Folding is presentation only. It never merges, omits, or reorders retained sequence truth, and an
unexpanded group whose members were never served is an explicit unknown, exactly like a sequence
gap. Bounded expansion remains a Vessel contract: authority serves what was asked for, and the
browser holds only what it was served. Folding belongs to Loom and Orb through their shared supply;
Nexus folds by disclosure in its own board and inherits no renderer.
Current Pattern manifests do not supply nested subworkflow or parent-Run identities. A station,
delegated job, or shared name cannot manufacture that hierarchy; deeper nesting remains unavailable.

### Deferred dense renderers

Sigma with Graphology and cosmos.gl are mapped, not admitted, and are reopened only by a measured
field that folding cannot bound—not by node count alone. Both are FOSS: Sigma's closure is MIT
throughout; cosmos.gl became admissible only after moving to the OpenJS Foundation under MIT, its
predecessor having carried non-commercial terms that failed this Covenant outright.

The mapping gives later reviews an evidence base. Zoom-driven aggregation remains LychD's
responsibility: neither candidate, nor any surveyed commercial alternative, supplies it. That is
why aggregation is a supply rule above rather than a selection criterion. Sigma re-indexes its
whole graph on node removal, while bounded expansion requires eviction. cosmos.gl has no link
removal path, so any edge-touching patch rebuilds the whole link set; its identity-keyed streaming
API is published only in the separately sold non-commercial tier. Neither handles WebGL context
loss or supplies an accessibility surface, leaving a second semantic twin to build and synchronize
indefinitely. G6 was rejected outright: its published maximum-scale demonstration fails, combo
collapse is a pointer-triggered action on hand-declared groups rather than zoom-driven aggregation,
and teardown discards its context while asynchronous work still holds it.

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
principal exists. The [isolated developer fixture](11-backend.md#isolated-developer-fixture-designed)
may use its configured loopback Vite proxy under [Security's](09-security.md) bounded exception.
Remote access, production access through a proxy, tunnels, direct-image-public access, and
untrusted-browser use remain unsupported. Authenticated browser acceptance of the fixture
remains pending.

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
