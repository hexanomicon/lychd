---
title: 2. Documentation
icon: material/book-cog-outline
---

# :material-book-cog-outline: 2. Documentation

## Historical record

This Covenant records the decision to select the Markdown/Zensical Hexanomicon and its register
discipline. For current placement rules, follow
[ADR 01](./01-doctrine.md#documentation-topology); for authoring and verification, use
[CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md).

## Context and requirements

The Hexanomicon must remain versioned beside the body it describes so that readers can review
the two together. Its Markdown source must be plain enough for humans and coding agents to read,
while the rendered work stays accessible, visually its own, and quick to preview. Within that
shared medium, law, operation, threshold, and myth retain their distinct burdens.

## Options

| Option | Decision pressure |
| --- | --- |
| Sphinx / reStructuredText | Strong reference tooling, but heavier syntax and a poorer fit for this grimoire. |
| Hosted wiki | Convenient editing, but detached from repository history and review. |
| External documents | Useful exploration, not canonical law. |
| Zensical | Markdown-native, versioned locally, fast to preview, and visually capable. |

## Decision and invariants

Zensical renders `docs/`. `zensical.toml` owns extensions, theme, and deploy metadata. Native
Awesome Nav reads the top-level order from `docs/.nav.yml` and each section's navigation from
its own `.nav.yml`; navigation stays beside the content it arranges.
`docs/overrides/stylesheets/hexanomicon.css` supplies the visual layer. Admonitions, details,
snippets, and Mermaid are used when they clarify. Snippets stay short and use repository-root paths.

| Register | Surface and burden |
| --- | --- |
| Law | Covenants and accepted Compositions: exact decisions, invariants, failure, recovery, compatibility, consequence. |
| Iron | Commands, config, troubleshooting, recovery: literal, copyable, observable, recoverable. |
| Threshold | README, Prophecy, Map, State, indexes: lucid enchantment followed by a next act. |
| Operated doctrine | Sepulcher and Altar: anatomy joined to concrete ownership and use. |
| Great Work | Transcendence: full mythic voltage, formative movement, correspondence, and vow. |

A page's placement establishes its register. Myth can speak fully where it belongs; technical
pages must support their mechanisms without borrowing scientific or mystical certainty.
Likewise, publication in the Portfolio accepts a Native Reference Composition and its application
contract, but does not prove executable delivery. State of Work holds the shared whole-system
evidence envelope. A leaf needs a local delivery note only when that limit materially changes
how its contract should be read.

## Progressive revelation

1. Give the first viewport purpose and voice.
2. Put vocabulary beside the thing; the Lexicon is reference, not initiation.
3. Give each page one office.
4. Prefer one image to repeated representations.
5. Link rather than recap an owner's deep truth.
6. Keep useful etymology and correspondence visible.
7. Make new terms earn a stable distinction.

## ADR presentation

An ADR normally leads from context and pressure through requirements and alternatives to a decision and
its invariants. It then explains failure, recovery, compatibility, and consequence. Live
implementation stays in source. When a short snippet helps, name its repository-root path and
link explicitly to the source; use a stable named section only where the source accepts it.
Page view/edit actions do not establish an included target. Links carry readers across register
seams, and the current [Covenant registry](./index.md) routes architectural questions.

## Consequences

The historical decision supports a distinctive, reviewable manual without merging every register
into one voice. It does not authorize deep operational duplication: authoring remains in
[CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md), and current
topology remains ADR 01.
