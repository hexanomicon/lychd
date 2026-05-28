# Divination Scope

## Trigger

Load this scope when changing Divination, Altar, Transcendence, public reader paths, or Zensical navigation that touches `docs/divination/**`.

## Purpose

Route work on the reader-facing interaction path without turning agent routing into published docs. Divination explains how the Magus meets the Lich; this scope only tells agents where to look and how to verify changes.

## Agent Posture

Reader journey first, doctrine second, prose last. Keep interaction concepts legible for newcomers, and keep deeper metaphysics in the Transcendence layer where ADR 02 places it.

## Probes

- Documentation doctrine: `docs/adr/02-documentation.md`
- Divination landing: `docs/divination/index.md`
- Altar surface: `docs/divination/altar/index.md`
- Transcendence map: `docs/divination/transcendence/index.md`
- Transcendence seals: `docs/divination/transcendence/incantation.md`, `docs/divination/transcendence/invocation.md`, `docs/divination/transcendence/illumination.md`, `docs/divination/transcendence/immortality.md`, `docs/divination/transcendence/infinity.md`
- Public entrypoints: `README.md`, `docs/index.md`, `docs/lexicon.md`
- Zensical navigation: `zensical.toml`
- Cross-links only when touched: `docs/sepulcher/lich.md`, `docs/sepulcher/vessel/index.md`, `docs/sepulcher/extensions/shadow.md`, `docs/sepulcher/extensions/mirror.md`, `docs/sepulcher/phylactery/index.md`

## Write Bounds

- `docs/divination/**`
- `zensical.toml` when adding, removing, or reordering Divination pages.
- `README.md`, `docs/index.md`, and `docs/lexicon.md` when public entrypoints or terms change.
- `docs/adr/02-documentation.md` only when changing documentation-layer doctrine.
- `docs/sepulcher/**` only for cross-link or terminology sync caused by Divination edits.
- Frontend/source files only when the task changes the actual Altar implementation, not merely its documentation.

## Verification

- Check Zensical nav entries when files under `docs/divination/**` are added, removed, renamed, or reordered.
- Check relative links with targeted `rg` around changed terms and paths.
- Run `git diff --check -- docs/divination zensical.toml README.md docs/index.md docs/lexicon.md .agents/scopes` for Markdown/navigation changes.
- For documentation build confidence, run `uv run zensical build` when the task changes navigation, admonition-heavy pages, or link structure.
- For source-backed Altar changes, add targeted frontend or backend checks from `CONTRIBUTING.md`.
