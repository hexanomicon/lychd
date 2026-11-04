# OpenAPI generation

This private workspace runs the existing OpenAPI TypeScript generator with its supported
TypeScript 5 compiler. SvelteKit 3 requires TypeScript 6, while openapi-typescript 7.13 declares
TypeScript 5 as a peer dependency. The checked-in npm nested install strategy keeps that
compiler beside the generator instead of hoisting the generator into the application compiler
scope. npm installs both from the single Altar lockfile; Node 24.20
and npm 12 remain the shared build tools. Run generation through `npm run generate:api` in
`clients/web`, after the canonical Litestar schema export.

The workspace contributes no browser code or production server. Its own local link is excluded
from third-party notices; its external dependencies remain in the generated notice inventory.
