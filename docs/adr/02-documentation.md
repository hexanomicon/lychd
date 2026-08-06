---
title: 2. Documentation
icon: material/book-cog-outline
---

# :material-book-cog-outline: 2. Documentation

## Historical record

This Covenant records the decision to select the Markdown/Zensical Hexanomicon and its register
discipline. It is not current topology law: [ADR 01](./01-doctrine.md#documentation-topology) owns
placement, while `CONTRIBUTING.md` owns authoring and verification mechanics.

## Context and requirements

The Hexanomicon must be versioned beside the body it describes, visually its own, quick to preview,
and accessible. Its plain, reviewable Markdown source must stay readable by humans and coding
agents while preserving the distinct burdens of law, operation, threshold, and myth.

## Options

| Option | Decision pressure |
| --- | --- |
| Sphinx / reStructuredText | Strong reference tooling, but heavier syntax and a poorer fit for this grimoire. |
| Hosted wiki | Convenient editing, but detached from repository history and review. |
| External documents | Useful exploration, not canonical law. |
| Zensical | Markdown-native, versioned locally, fast to preview, and visually capable. |

## Decision and invariants

Zensical renders `docs/`. `zensical.toml` owns navigation, extensions, theme, and deploy metadata;
`docs/overrides/stylesheets/hexanomicon.css` supplies the visual layer. Admonitions, details,
snippets, and Mermaid are used when they clarify. Snippets stay short and use repository-root paths.

| Register | Surface and burden |
| --- | --- |
| Law | Covenants and accepted Compositions: exact decisions, invariants, failure, recovery, compatibility, consequence. |
| Iron | Commands, config, troubleshooting, recovery: literal, copyable, observable, recoverable. |
| Threshold | README, Prophecy, Map, State, indexes: lucid enchantment followed by a next act. |
| Operated doctrine | Sepulcher and Altar: anatomy joined to concrete ownership and use. |
| Great Work | Transcendence: full mythic voltage, formative movement, correspondence, and vow. |

Placement establishes register. Myth needs no disclaimer where it belongs, but a technical page
cannot borrow scientific or mystical certainty to make an unproved mechanism sound inevitable.
Portfolio publication marks a Native Reference Composition and accepted application contract; it
does not prove executable delivery. Each leaf states its current application material, while State
of Work keeps the shared whole-system evidence envelope.

## Progressive revelation

1. Give the first viewport purpose and voice.
2. Put vocabulary beside the thing; the Lexicon is reference, not initiation.
3. Give each page one office.
4. Prefer one image to repeated representations.
5. Link rather than recap an owner's deep truth.
6. Keep useful etymology and correspondence visible.
7. Make new terms earn a stable distinction.

## ADR presentation

An ADR normally records context and pressure; requirements; alternatives; decision and invariants;
then failure, recovery, compatibility, and consequence. It does not copy live implementation.
Short source snippets name a repository-root path and link explicitly to their source. Stable named
sections are used only where the source accepts them; page view/edit actions do not imply an
included target. Where registers meet, pages link across the seam. The current
[Covenant registry](./index.md) routes architectural questions.

## Consequences

The historical decision supports a distinctive, reviewable manual without merging every register
into one voice. It does not authorize deep operational duplication: authoring remains in
[CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md), and current
topology remains ADR 01.
