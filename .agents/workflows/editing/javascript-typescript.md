# JavaScript and TypeScript Editing

Load this card immediately before changing `.js`, `.jsx`, `.ts`, or `.tsx` files. For
`frontend/**`, load the Frontend scope first. Svelte-family files additionally follow the Svelte
scope instead of treating this card as framework guidance.

## Inspect before patching

Read:

- the target module, exports, direct consumers, and closest tests;
- the nearest `package.json`, lockfile, TypeScript configuration, lint configuration, and build
  boundary;
- generated transport types and their backend/OpenAPI owner when data crosses the browser seam;
- runtime target: browser, build tool, worker, Node-only tooling, or shared code;
- state ownership, event ordering, cancellation, reconnect, and error behavior; and
- accessibility and no-JavaScript/static fallbacks when the changed code affects presentation.

Comments and JSDoc may reveal intent but do not override types, generated contracts, tests, or
accepted browser law. Update them when they own changed semantics; remove narration that only
repeats the code.

## Change discipline

- Preserve ESM/export shape and strict type information at boundaries.
- Do not handwrite a mirror of a generated API contract.
- Keep durable domain truth, authorization, secrets, persistence, and server effects outside the
  browser.
- Distinguish absent, loading, stale, failed, cancelled, and terminal data when the owner does.
- Use stable semantic identities; array position and renderer coordinates are not identity.
- Avoid broad dependency, formatter, or generated-file churn in a behavioral patch.
- Do not introduce a Node production server or server-only framework surface where the accepted
  topology is static.

## Verify

Run the closest test first, then the package's type/lint gate. For `frontend/**`, use the exact
frontend checks routed by the Frontend scope and run the production build when routes,
configuration, CSS, dependencies, or packaged assets change.

Inspect the final diff for export drift, generated-contract edits, browser/server boundary
changes, dependency/lock mismatch, unhandled rejection or cancellation, and stale documentation.
When an export, transport shape, or executable example changes, run affected consumer tests and
the owning generation/parity command; visual inspection of generated types is not sufficient.
