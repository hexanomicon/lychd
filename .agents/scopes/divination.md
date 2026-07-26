# Divination Scope

## Trigger

Load this scope for Divination, the Altar, Transcendence, the public reader journey, or Zensical
navigation touching `docs/divination/**`.

## Authorities

- [ADR 02](../../docs/adr/02-documentation.md) owns documentation topology and register boundaries.
- The [Prophecy](../../docs/index.md) owns the published reader entry and route choice.
- The [Lexicon](../../docs/lexicon.md) owns canonical project vocabulary.
- The nearest tracked Divination or Transcendence page owns its reader-facing subject.
- Technical behavior remains owned by the matching ADR, source, tests, and delivery evidence.
  Scope cards and ignored work shelves do not establish product truth.

## Probes

- Reader entry: `docs/index.md`, `README.md`, `docs/summoning.md`
- Divination map: `docs/divination/index.md`
- Altar surface: `docs/divination/altar/index.md`
- Transcendence: `docs/divination/transcendence/index.md` and its immediate children
- System bridges: `docs/sepulcher/lich/index.md`, `docs/sepulcher/vessel/index.md`,
  `docs/sepulcher/phylactery/index.md`, `docs/sepulcher/extensions/`
- Navigation and presentation: `zensical.toml`, `docs/overrides/`, `docs/assets/`

## Typical Change Surface

This is routing guidance, not authorization. Work commonly touches `docs/divination/**`, its
cross-links in `README.md`, `docs/index.md`, `docs/lexicon.md`, nearby `docs/sepulcher/**` pages,
and `zensical.toml` when public navigation changes.

## Verification

- Preserve a usable plain-language foothold while allowing the mythic register to deepen by stage.
- Verify first-use terms against the Lexicon and technical claims against their owning ADR/source.
- Check every added, moved, or removed page against Zensical navigation and inbound links.
- Run `git diff --check -- docs/divination docs/sepulcher README.md docs/index.md docs/lexicon.md zensical.toml .agents/scopes`.
- Run the documentation build for navigation, rendering, or link changes.

## Escalate

Escalate when prose would flatten the constitutional myth, use mythology as implementation proof,
present a designed feature as delivered, redefine a canonical term, or create a second navigation
or status authority.
