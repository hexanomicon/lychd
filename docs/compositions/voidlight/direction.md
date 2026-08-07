---
title: Voidlight Direction
icon: material/palette-outline
---

# :material-palette-outline: Direction

Direction turns the Magus's taste into a visual system that can guide several assets without
flattening them into one prompt. It owns the answer to “what should this work feel and look like?”

## A reviewable visual system

`voidlight.establish_style_bible@1` can return a versioned style bible containing composition,
shape, proportion, palette, material, lighting, camera, typography, motion, and exclusion rules
where those dimensions apply. References support those decisions, but do not become instructions
to imitate a named living artist or copy protected expression.

Direction separates four things that are easy to blur:

1. **intent** — the response the commission seeks;
2. **observations** — attributable properties seen in admitted references;
3. **decisions** — the Magus's chosen rules and controlled exceptions; and
4. **tests** — concrete checks that a candidate can pass or fail.

Provider wording, seeds, control settings, and exploratory candidates may help discover the system.
They do not own it. A style revision changes only through an explicit forward decision, and
accepted assets keep the exact direction revision under which they were reviewed.

## Review and correction

A direction review returns findings against named rules rather than a vague request to “make it
better.” One bounded repair may revise the direction or candidate through
`voidlight.revise_from_correction@1`; the finding states which layer was wrong. Conflicting rules,
an impossible target profile, or exhausted repair ends with an exact non-completion.

Calibration through `voidlight.presenter_calibration@1` may compare how a presentation or viewer
changes perception. Calibration evidence can adjust the direction; it never silently edits an
accepted asset or proves that a display matches every consumer.

The result guides [Assets](assets.md) and [Motion](motion.md). It carries creative constraints, not
authority to generate, spend, export, publish, or change the brief.
