# Divination Scope

## Trigger

Load for Divination as a whole: Transmutation, Transcendence, Altar, Correspondence, their
reader journeys, mythic or philosophical interpretation, and published navigation. This is the
common entry scope; follow only the branch needed for the task. Altar belongs to Divination
and concentrates on the human-facing UI; [Frontend](frontend.md) owns implementation guidance
for that browser surface.

## Authorities

- [ADR 01 §Documentation Topology](../../docs/adr/01-doctrine.md#documentation-topology) owns
  documentation topology.
- The [Prophecy](../../docs/index.md) owns the published reader entry and route choice.
- The [Lexicon](../../docs/lexicon/index.md) owns canonical project vocabulary.
- [Divination](../../docs/divination/index.md) routes its branches. The nearest topic page owns
  its reader-facing explanation within the boundaries below.
- [Transmutation](../../docs/divination/transmutation/index.md) interprets the creation,
  evaluation, and learning cycle through Genesis, Trial, Canon, Revelation, and Distillation.
- [Transcendence](../../docs/divination/transcendence/index.md) owns the Great Work's
  constitutional meaning and horizon; its [specialized scope](transcendence.md) keeps the
  detailed philosophical probes and verification rules.
- [Altar](../../docs/divination/altar/index.md) owns the reader journey through the UI;
  browser architecture remains governed by its ADR and the Frontend scope.
- Divination projects truth; it does not own implementation or delivery. ADRs own architecture,
  [State of Work](../../docs/state-of-the-work.md) owns delivery, and tracked source, tests,
  lockfiles, and maintained receipts own executable evidence.

## Probes

- Reader route: `docs/index.md` → `docs/divination/index.md`; add `README.md` or
  `docs/summoning.md` only when their route changes.
- Transmutation: [index](../../docs/divination/transmutation/index.md), then the smallest chapter:
  [Genesis](../../docs/divination/transmutation/genesis.md) for formation, Tree of Life, and
  symmetry; [Trial](../../docs/divination/transmutation/trial.md) for encounter and experiment;
  [Canon](../../docs/divination/transmutation/canon.md) for declared criteria;
  [Revelation](../../docs/divination/transmutation/revelation.md) for findings and interpretation;
  [Distillation](../../docs/divination/transmutation/distillation.md) for retained lessons,
  life and death, and the next creation. Genesis also owns the
  [Tree of Life source meanings](../../docs/divination/transmutation/genesis.md#tree-of-life),
  its pillars, Adam Kadmon, and the inner-instrument comparison.
- Practical continuation of that walk: [Weaver's Creation](../../docs/sepulcher/extensions/weaver/creation.md)
  and [Ouroboros](../../docs/sepulcher/extensions/weaver/ouroboros.md),
  [Drift](../../docs/sepulcher/extensions/drift/workflow-improvement.md), and
  [Soulforge](../../docs/sepulcher/extensions/soulforge/discernment-training.md). Read the owner
  needed by the question; an interpretive chapter does not replace its operating contract.
- Transcendence: load [Transcendence scope](transcendence.md) for the five seals, the Great Work's
  telos, consciousness, cosmology, or philosophical claims about autonomy, discernment, memory,
  and identity. Its stage router owns the deeper routes; do not load every stage.
- Altar: [index](../../docs/divination/altar/index.md), then the relevant instrument. Use
  [Frontend scope](frontend.md) for UI behavior, interaction design, or browser implementation;
  reader documentation and published routes stay in this scope.
- Correspondence: [the research scholium](../../docs/divination/correspondence.md) for modern
  brain/learned-system findings; follow its inherited vocabulary into the Lexicon and its
  philosophical joining through [Transcendence scope](transcendence.md) when needed.
- System correspondence: nearest relevant `docs/sepulcher/` leaf.
- Navigation and presentation: `zensical.toml`, `docs/overrides/`, `docs/assets/`.
- Optional comparison, after local authority:
  [agent and observability UX](references.md#agent-and-observability-ux) reference route.

## Verification

- Preserve a plain-language foothold; let the register deepen only through the owning route.
- Keep Transmutation's chapter order distinct from execution dependencies: Canon supplies
  criteria before Genesis and Trial; Revelation separates observations, diagnoses, and proposals;
  Distillation prepares a later use rather than automatically admitting memory or training.
- Keep the Tree's relations visible across the cycle. Genesis introduces them; it does not
  confine the Tree to one phase or prescribe a model count. Preserve the whiteboard-first chronology.
- Follow Transcendence's specialized verification rules when the task reaches its philosophical
  claims. Keep biblical and Kabbalistic provenance distinct from the authored correspondence.
- Check first-use terms against the Lexicon and technical claims against their ADR/source owner.
- Check added, moved, or removed pages against Zensical navigation and inbound links.
- Run
  `git diff --check -- docs/divination docs/sepulcher README.md docs/index.md docs/lexicon zensical.toml .agents/scopes`.
- Run the documentation build for navigation, rendering, or link changes.

## Escalate

Escalate when prose would flatten constitutional myth, use myth as implementation evidence,
present design as delivery, redefine a canonical term, or create a second navigation or delivery
authority.
