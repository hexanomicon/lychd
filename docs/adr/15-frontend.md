---
title: 15. Frontend
icon: material/language-html5
---

# :material-language-html5: 15. Frontend: The Altar

!!! abstract "Context and Problem Statement"
    LychD needs one rich browser surface for conversation, live run inspection, orchestration,
    workflow graphs, artifacts, and configuration proposals. It also needs non-browser clients,
    beginning with the native Android Emissary. Server-rendered HTML therefore cannot remain the
    universal projection contract: the browser, Android, and future clients need the same typed
    semantic API and event vocabulary.

    The browser must become capable without becoming sovereign. Durable truth, validation,
    authorization, workflow movement, consent, and mutation remain in the **Vessel (11)** and
    **Phylactery (06)**. The Altar is a replaceable projection of that truth.

## Requirements

- **One Authority:** Litestar services own validation, authorization, persistence, workflow
  transitions, consent, and every durable mutation.
- **One Browser Language:** The canonical Altar uses one Svelte component model. Permanent
  Jinja/HTMX/Alpine/Svelte coexistence is forbidden.
- **Universal Protocol:** Versioned JSON APIs, OpenAPI schemas, and semantic JSON SSE serve the
  browser, native Android, and other admitted clients.
- **Generated Contracts:** TypeScript types, runtime schemas, route helpers, and the browser Fetch
  SDK derive from Litestar OpenAPI rather than handwritten mirror interfaces.
- **Static Production:** Production runs Litestar/Granian only. The Svelte application is a static
  build served from the Vessel; no JavaScript runtime becomes a second production server.
- **Replaceable Renderer:** Framework-specific reactivity remains inside the presentation
  boundary. Transport, schemas, validation, event reduction, and domain rules remain ordinary
  TypeScript that another renderer can consume.
- **Focused Instrument Map:** Bridge, Orb, Nexus, and Loom remain distinct, deep-linkable
  instruments under one application shell. Artifact references and orchestration-relevant
  declarations appear contextually without creating empty top-level authorities.
- **Live Projection:** Snapshots plus resumable SSE must project token flow, run movement,
  approvals, transitions, logs, and terminal outcomes without making the browser a ledger.
- **Closed Generative UI:** Models select and parameterize server-validated component descriptors.
  They never emit executable HTML, JavaScript, or arbitrary component imports.
- **Hermetic Operation:** Browser assets, schemas, and fonts are locally built and packaged for
  offline and air-gapped operation.
- **Auditable Interaction:** Keyboard operation, accessible names, visible error/unknown states,
  deep-link recovery, and real-browser behavior tests are part of the contract.

## Considered Options

### Option 1: Server-Rendered Hypermedia with Svelte Islands

Keep Jinja, HTMX, and Alpine as the shell and mount Svelte only for graph- or canvas-shaped
instruments.

This was the previous accepted design and produced useful Bridge, Nexus, and Loom slices. It is
rejected as the permanent architecture because Android makes the JSON contract mandatory anyway.
Keeping HTML as a second primary projection would make agents and the operator reason across:

1. Python view models and Jinja templates;
2. HTMX request, swap, polling, and out-of-band semantics;
3. Alpine local state;
4. Svelte island lifecycle and hydration; and
5. the JSON/OpenAPI contract required by native clients.

The domain logic can remain DRY, but two long-lived projection systems still duplicate presentation
contracts, error behavior, accessibility work, and end-to-end tests. Existing hypermedia routes
are migration evidence, not a compatibility promise.

### Option 2: React 19 with Vite

React can satisfy the architecture. Its strongest project-specific technical case is:

- a single TypeScript/JSX application with established client routing;
- explicit external-store integration through `useSyncExternalStore`;
- error boundaries and a mature concurrent rendering model;
- automatic memoization through the React Compiler; and
- clean consumption of the same generated Litestar SDK used by any TypeScript client.

It loses without relying on popularity, hiring, package count, or community size.

LychD's dominant browser workload is a changing projection of external state: token deltas,
ordered run events, graph movement, queue pressure, consent, and artifact progress. Correct React
requires an external event store, immutable cached snapshots, stable subscriptions, publication
batching, Effect discipline, and compiler-aware render boundaries. Those mechanisms are viable,
but they add a second optimization model beside the domain and event protocol.

React's own rules acknowledge the failure modes: parent state normally re-renders descendants,
Effect chains commonly create repeated updates, external-store snapshots require identity
discipline, and compiler memoization can affect Effect behavior across upgrades. Svelte does not
make bad architecture impossible, but its fine-grained runes express this workload with fewer
coordination mechanisms for the operator to audit.

React remains an admissible replacement technology if Svelte later fails the explicit reopening
criteria below. It is not the canonical Altar language.

### Option 3: Plain Svelte SPA

Plain Svelte supplies the component and reactivity model but not the canonical application router,
layouts, route errors, deep-link conventions, or route-level code splitting. Adding independent
packages or inventing those contracts would discard the benefit of a small standard surface.

### Option 4: Svelte 5 with SvelteKit Static SPA

Svelte 5 supplies explicit fine-grained reactivity through runes. SvelteKit supplies the official
router, layouts, navigation, route boundaries, and build conventions. `adapter-static` produces
ordinary assets that Litestar can serve without a JavaScript production process.

This option is accepted.

## Decision Outcome

The canonical Altar is a **Svelte 5 application using SvelteKit in static SPA mode**.

- New components use Svelte 5 runes only.
- SvelteKit owns presentation routing and layouts only.
- Server-side rendering is disabled for the Altar.
- `adapter-static` emits the production assets and fallback document.
- `+page.server.*`, `+layout.server.*`, SvelteKit form actions, remote functions, private server
  modules, and a SvelteKit production server are forbidden.
- Node.js 24 LTS is the canonical JavaScript development/build runtime; npm 11 owns dependency
  installation and script execution.
- Vite remains the frontend compiler and asset pipeline.
- Litestar/Granian is the only production application server.
- The native Android client remains Kotlin/Compose. It shares protocol, not UI code.

This decision replaces the previous HTMX/Alpine shell and Svelte-island refinement in this ADR.
The repository is pre-alpha; no compatibility period is promised. Existing routes remain only long
enough to serve as behavioral evidence during the rewrite and must not become a permanent second
Altar.

### 0. Instrument Map

| Instrument | Owning subsystem | Browser responsibility |
| :--- | :--- | :--- |
| **Bridge** | [Agents (20)](20-agents.md) | Conversation, input, stream projection, consent, and contextual artifact references |
| **Orb** | [Observability (29)](29-observability.md) / [Graph (24)](24-graph.md) | Bounded selected-Run structural evidence with explicit correlation and gaps |
| **Nexus** | [Orchestrator (23)](23-orchestrator.md) | Current capability observations, retained transition observations, non-binding preview, and explicit transition request |
| **Loom** | [Weaver (28)](28-workflow.md) / [Graph (24)](24-graph.md) | Immutable Pattern-revision browsing and an optional diagram lens |

The top-level application shell owns navigation and shared caller/session presentation. Each
instrument owns its route subtree and local layout. An instrument never owns the subsystem truth it
projects.

Bridge, Orb, Nexus, and Loom form the current conversation–evidence–body–design review loop.
**Scrying** is the act of inspecting evidence through the Orb, not a fifth instrument.
Artifact references stay attached to the conversation, event, or Pattern records that cite them
until LychD owns custody, retention, and retrieval semantics substantial enough to justify a
Reliquary instrument. Nexus may project the declarations that explain physical orchestration, but
Configuration remains their authority; it is not absorbed by the Orchestrator. A future dedicated
artifact or configuration instrument requires its own proved lifecycle and a deliberate revision
of this Covenant.

### 1. The Projection Law

> The Vessel emits validated semantic state and permitted intents. The Svelte Altar projects them
> through a closed local registry. The browser may cache, select, speculate, and animate; it never
> becomes authority.

State ownership is closed:

1. **Vessel and Phylactery:** canonical durable and policy truth.
2. **Replaceable snapshot cache:** the last validated API projection.
3. **Run/event projection:** transient ordered deltas applied to a snapshot.
4. **URL and component state:** navigation, selection, layout, drafts, and other ephemeral
   presentation.

No fifth state authority may emerge. A client cache is disposable. Refresh or reconnect must be
able to reconstruct the visible state from a server snapshot and event cursor.

Svelte state follows these constraints:

- `$state` holds local or transient projection state.
- `$derived` expresses values determined by other state.
- `$effect` is an escape hatch for external synchronization, not a general derivation mechanism.
- Large immutable snapshots may use raw state and replacement rather than deep mutation.
- Runes are compiler directives, not ordinary JavaScript functions. They may appear only in
  components and explicitly presentation-owned `.svelte.ts` modules.
- Generated OpenAPI code, the Fetch SDK, runtime schemas, protocol types, pure event reducers, and
  domain rules remain framework-neutral `.ts`.
- A Svelte proxy never crosses Fetch, SSE, IndexedDB, structured-clone, or extension boundaries.
  External admission receives a plain validated value; use a deliberate snapshot at the
  presentation boundary when reactive state must leave it.
- Shared reactive modules may coordinate views but may not become a browser domain layer.

Svelte is therefore a replaceable compiled view language, not the language of the application.
The compiler's concise reactivity is admitted precisely where the browser projects state; it does
not acquire authority over the protocol or the Work.

### 2. API and Type Generation

The stable browser boundary lives beneath `/api/v1`. Litestar route annotations, DTOs, Pydantic
models, msgspec structures, and dataclasses feed OpenAPI 3.1.

The audited OpenAPI generation path exports the real Litestar controller schema and uses
`openapi-typescript` plus `openapi-fetch`. It provides:

- TypeScript request and response types;
- a typed Fetch SDK;
- stable path and operation identifiers; and
- named schemas for event payloads and client contracts.

Hostile stream input is parsed by Zod schemas statically constrained to those generated event
types. The runtime validator may not invent a broader or incompatible parallel contract.

Generated code is committed or deterministically reproduced in CI. A schema-drift gate exports the
OpenAPI document from the real application factory, regenerates the client, and fails if tracked
output differs.

Operation identifiers are part of the public client contract. The generator translates a designed
API; it never names or designs the API on LychD's behalf.

### 3. Event and Voice Transport

Commands enter as complete requests:

- text as JSON;
- short recorded voice input as a complete authenticated upload;
- files and other media as bounded multipart or artifact admissions.

Live output uses semantic JSON SSE. Every event envelope carries at least:

```json
{
  "schema_version": 1,
  "run_id": "run-id",
  "event_id": "producer-stable-event-id",
  "seq": 42,
  "kind": "token|status|node|dispatch|transition|fragment|consent|log|done|resync",
  "occurred_at": "2026-01-01T00:00:00Z",
  "payload": {}
}
```

The browser loads a snapshot, opens the event stream after its cursor, ignores duplicate sequence
numbers, detects gaps, and refetches on an explicit reset/resync event. The server owns
`Last-Event-ID`, retention, keepalive, terminal synthesis, and close behavior. High-frequency token
or trace deltas may be batched once per animation frame before visual publication; batching never
changes ledger order.

The Bridge snapshot includes the selected session's active run identities and exact process-local
projections. A route remount or browser reload rebuilds each missing live turn, including the
latest retained occurrence, dispatch grant, and transition correlation, seeds its reducer from
the supplied cursor, and reattaches its stream. This reconstructs only the content and descriptors
still owned by the current process's event channels plus best-effort retained structural evidence;
it does not make token deltas durable or promise cross-process token recovery.

Audio output may arrive as a completed authenticated artifact or a later proved streaming
transport. The browser's transport convenience does not dictate the Animator contract.

### 4. Generative UI and Consent

An Agent may select a known GenUI descriptor:

```json
{
  "kind": "genui.plan_checklist",
  "schema_version": 1,
  "props": {},
  "actions": []
}
```

The Vessel validates the descriptor and allowed actions. Svelte renders it through a compile-time
closed registry. Unknown kinds fail visibly and safely.

Forbidden:

- model-generated HTML interpreted as markup;
- model-generated JavaScript or Svelte;
- runtime imports named by model output;
- `{@html}` for agent or extension content;
- browser-only authorization or consent;
- arbitrary extension bundles executing with Altar origin authority.

A pending `DeferredToolRequests` decision appears inline in the Bridge session that raised it and
through a global pending-consent indicator. The client submits one typed decision intent. The
Vessel rechecks identity, scope, state, idempotency, and policy before resuming anything.

### 5. Extensions and Graph Lenses

Extensions may contribute typed backend routes, schemas, and data descriptors through a shaped
Vessel store. They do not inject Jinja template roots or arbitrary Svelte source at runtime.

Ordinary extension UI uses the closed generic GenUI registry. A trusted first-party visual
extension may be compiled into the Altar behind an explicit registration adapter. Untrusted
third-party UI requires a separately designed sandbox boundary; a Svelte component or Web
Component is not a security sandbox.

Loom and future graph-shaped Orb views may use Svelte Flow behind one LychD-owned adapter.
Graph-shaped Nexus details may use the same presentation mechanics when a graph answers a concrete
operator question better than its primary table, list, or form. Acceptance of this seam does not
claim that `@xyflow/svelte` is installed.

The adapter contract is strict:

- each mode consumes a closed, mode-specific DTO; no universal browser graph model erases the
  difference between Pattern permission, execution evidence, physical state, lineage, and declared
  configuration;
- stable domain identity remains separate from renderer identity and coordinates;
- pan, geometric zoom, selection, expansion, layout, and inert gestures are disposable
  presentation state;
- read-only modes structurally disable graph mutation while retaining selection, focus, and
  meaningful keyboard operation;
- scope changes through explicit selection, URLs, breadcrumbs, and drill-down controls; wheel zoom
  never silently changes the domain query;
- every edge names its epistemic relation, including containment, permission, correlation,
  explicit causality, lineage, or declaration; shared time or trace identity never creates a
  causal edge;
- every canvas has a semantically equivalent keyboard-operable outline, list, table, or timeline
  and inspector;
- motion is a pausable, reduced-motion-safe acknowledgement of a typed event, never proof of state;
  and
- realistic node, edge, update, layout-time, and memory budgets are measured before a large graph
  becomes a required operator surface.

Weaver and the Vessel own validation, publication, execution, persistence, authorization, and
consent. Oculus and each acting office own evidence semantics. The adapter owns none of them.

### 6. Styling Boundary

The Altar uses native CSS custom properties, cascade layers, media queries, and semantic component
classes. Component state is expressed through meaningful classes, attributes, and `data-state`
values rather than generated utility strings.

Tailwind is rejected because the Altar already owns a small semantic design vocabulary. A utility
compiler would duplicate that vocabulary, expand the dependency and generated-code surface, and
force agents to translate between component meaning and styling tokens. Sass is rejected because
the current design needs no compile-time mixins, functions, or inheritance beyond capabilities
provided by modern CSS. A project-owned PostCSS configuration is rejected because no required
project transform remains.

Vite and its dependencies may internally process CSS as an implementation detail. That does not
authorize a LychD PostCSS configuration, Tailwind plugin, Sass compiler, or styling DSL. A new
transform requires a concrete browser requirement that native CSS cannot satisfy and a deliberate
revision of this Covenant.

### 7. Development, Build, and Production

The frontend source lives in one bounded monorepo client root. Python and frontend sources share
one repository and one release, but not one runtime authority.

Development:

```text
Browser
  → SvelteKit/Vite development server
      → /api and /schema proxy to Litestar
      → HMR remains loopback-only development tooling
```

Production:

```text
npm ci
  → SvelteKit adapter-static build
      → hashed assets + fallback document
          → packaged with LychD
              → Litestar/Granian serves UI, API, and SSE on one origin
```

Node/npm law:

- pin the Node.js 24 LTS build line in repository tooling;
- record the canonical npm 11 release in `packageManager`;
- commit `frontend/package-lock.json` and use `npm ci` for reproducible installs;
- keep Vite as the compiler;
- do not use Node-specific server APIs in browser application code;
- do not place Node.js or a SvelteKit server in the production runtime image.

Static UI fallback routes must never swallow `/api`, `/schema`, `/static`, health, A2A, or other
non-Altar namespaces. Hashed immutable assets and the fallback document use distinct cache policy.

### 8. Quality Gates

The canonical client must pass:

- TypeScript strict checking and `svelte-check`;
- deterministic OpenAPI/client drift verification;
- focused Vitest component and projection tests;
- Playwright tests against the real Litestar-served production build;
- keyboard navigation and automated accessibility checks;
- direct deep-link refresh for every instrument;
- snapshot, SSE disconnect, resume, duplicate, gap, reset, consent, and terminal-flow scenarios;
- a production-image assertion that no Node.js/SvelteKit server is present;
- a static guard against Tailwind, Sass, project-owned PostCSS, and Svelte runes outside the
  presentation boundary;
- hermetic build and local-asset checks; and
- measured bundle and high-frequency event budgets.

Semantic roles, instrument identifiers, visible states, and explicit `PASS`, `FAIL`, `BLOCKED`, or
`SKIP` verdicts remain machine-readable runtime evidence. The DOM is evidence, not authority.

### 9. Migration Law

The rewrite was a replacement, not a permanent hybrid:

1. Update the Logos and delivery boundary before claiming the new client.
2. Separate OpenAPI generation and static serving, then retire Litestar-Vite with the legacy shell.
3. Establish `/api/v1`, generated contracts, semantic JSON SSE, and the shared error law.
4. Build Bridge as the first complete vertical slice: send, stream, reconnect, consent, settle,
   refresh.
5. Port Orb, Nexus, and Loom by route.
6. Use the former HTMX behavior only as a temporary parity oracle.
7. Remove Jinja Altar templates, HTMX, Alpine, HTML SSE projection, polling fragments, and their
   obsolete tests once the corresponding Svelte behavior is proved.

This migration boundary has now been crossed for the existing Altar: steps 1–7 are represented in
source, generated assets, focused tests, and State of the Work. The Orb now has a bounded
selected-run projection while the durable Oculus, live trace tail, run index, and graph-shaped
evidence field remain later work. New Altar work must extend the Svelte contract and must not
reintroduce the retired HTMX/Jinja surface.

### 10. Decision Reopening Criteria

This decision is not reopened by:

- framework popularity, hiring pools, download counts, or social-media sentiment;
- the number of third-party component packages;
- familiarity with another framework; or
- a hypothetical future Composition without a concrete blocked requirement.

Reopening requires repository evidence that at least one of these is true:

- the static SvelteKit/Litestar production topology cannot meet a required security, packaging, or
  deep-link contract;
- a required accessible interaction cannot be implemented without an unsafe or unmaintainable
  boundary;
- measured event or memory behavior fails its budget after correct fine-grained implementation;
- a critical upstream is abandoned or carries an unresolved security defect with no bounded
  replacement seam; or
- maintaining Svelte-specific code demonstrably costs more than replacing the renderer against the
  framework-neutral protocol.

Any replacement must preserve the API, event, GenUI, authority, and production-runtime laws above.

## Primary References

- [Svelte runes](https://svelte.dev/docs/svelte/what-are-runes) and
  [`$effect`](https://svelte.dev/docs/svelte/$effect)
- [SvelteKit SPA mode](https://svelte.dev/docs/kit/single-page-apps) and
  [`adapter-static`](https://svelte.dev/docs/kit/adapter-static)
- [Svelte Flow concepts](https://svelteflow.dev/learn) and
  [accessibility configuration](https://svelteflow.dev/api-reference/types/aria-label-config)
- [Litestar-Vite type generation](https://litestar-org.github.io/litestar-vite/usage/types.html)
- [React external-store integration](https://react.dev/reference/react/useSyncExternalStore) and
  [React Compiler](https://react.dev/learn/react-compiler/introduction)
- [Node.js release lines](https://nodejs.org/en/about/previous-releases) and
  [`npm ci`](https://docs.npmjs.com/cli/v11/commands/npm-ci)

## Consequences

!!! success "Positive"
    - One typed browser component model replaces the Jinja/HTMX/Alpine/island split.
    - Fine-grained reactivity matches live agent and orchestration projections directly.
    - The operator audits less framework machinery per interaction.
    - Android and the Altar share one semantic protocol without sharing UI code.
    - Static output preserves a one-server, offline-capable production body.
    - Framework-neutral contracts keep the renderer replaceable.

!!! failure "Negative"
    - The useful existing hypermedia surface must be rewritten rather than incrementally extended.
    - Svelte 5 and SvelteKit require exact-version and runes discipline; stale Svelte 3/4 patterns
      are invalid guidance.
    - Runes are compiler-transformed semantics, so proxy admission, serialization, and debugger
      behavior require an explicit boundary rather than assumptions based on ordinary JavaScript.
    - Static SPA startup depends on JavaScript and needs explicit loading, failure, and recovery UI.
    - The team must prevent accidental use of SvelteKit server features.
    - Some specialized JavaScript libraries will require a small owned adapter.
