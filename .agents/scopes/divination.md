# Divination Scope

## Trigger

Load for published Divination pages, the Altar reader journey, routes into `docs/divination/**`,
or Zensical navigation. For Transcendence meaning, mythic voice, formation, consciousness,
cosmology, or eschatology, load [Transcendence scope](transcendence.md); add this scope only for
route or presentation changes.

## Authorities

- [ADR 01 §Documentation Topology](../../docs/adr/01-doctrine.md#documentation-topology) owns
  documentation topology.
- The [Prophecy](../../docs/index.md) owns the published reader entry and route choice.
- The [Lexicon](../../docs/lexicon/index.md) owns canonical project vocabulary.
- The nearest tracked Divination page owns its reader-facing projection.
- Divination projects truth; it does not own implementation or delivery. ADRs own architecture,
  [State of Work](../../docs/state-of-the-work.md) owns delivery, and tracked source, tests,
  lockfiles, and maintained receipts own executable evidence.

## Probes

- Reader route: `docs/index.md` → `docs/divination/index.md`; add `README.md` or
  `docs/summoning.md` only when their route changes.
- Altar: `docs/divination/altar/index.md`; use [frontend scope](frontend.md) for experience or
  frontend behavior.
- System correspondence: nearest relevant `docs/sepulcher/` leaf.
- Navigation and presentation: `zensical.toml`, `docs/overrides/`, `docs/assets/`.
- Optional comparison, after local authority:
  [agent and observability UX](references.md#agent-and-observability-ux) reference route.

## Verification

- Preserve a plain-language foothold; let the register deepen only through the owning route.
- Check first-use terms against the Lexicon and technical claims against their ADR/source owner.
- Check added, moved, or removed pages against Zensical navigation and inbound links.
- Run
  `git diff --check -- docs/divination docs/sepulcher README.md docs/index.md docs/lexicon zensical.toml .agents/scopes`.
- Run the documentation build for navigation, rendering, or link changes.

## Escalate

Escalate when prose would flatten constitutional myth, use myth as implementation evidence,
present design as delivery, redefine a canonical term, or create a second navigation or delivery
authority.
