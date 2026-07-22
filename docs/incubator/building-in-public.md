---
title: Building in Public
icon: material/hammer-wrench
---

# :material-hammer-wrench: Building in Public: The Tutorial Forge

!!! warning "Publication program — not an implementation claim"
    This page proposes how future LychD work can become articles and videos. It does not promise a
    release sequence or make any Reference Composition available. Follow [State of the
    Work](../state-of-the-work.md) for the real software boundary.

The strongest Hexanomicon tutorial is not a polished reconstruction performed after the struggle.
It follows one real form from uncertainty into evidence. The audience sees why a boundary exists,
which first design failed, how the database changed, what the Agent was allowed to do, and what
observation finally justified the delivery claim.

## One season, one vertical slice

A substantial seed can become a tutorial season with this recurring path:

1. **Intent:** state the human problem, non-goals, and smallest proving scenario.
2. **Logos:** identify the owning domain and write or amend the ADR before declaring an API.
3. **Extension shape:** decide whether the slice is actually an extension, Pattern, Agent,
   managed workload, Animator, or external project.
4. **Rune and configuration:** introduce the smallest typed operator intent without embedding
   credentials or ambient defaults.
5. **Data and migration:** add owned tables only when persistence is required; demonstrate
   upgrade, downgrade or forward-only policy, fixtures, export, deletion, and failure recovery.
6. **Provider boundary:** implement the connector, toolset, or service adapter and prove its
   declared capabilities against the real provider.
7. **Agent and Pattern:** bind typed inputs, outputs, budgets, tools, checkpoints, and truthful
   non-completion into the workflow.
8. **Authority and interface:** expose the narrow Altar surface, consent gate, and evidence needed
   for a human decision.
9. **Adversarial proof:** run deterministic tests, Riddle evaluation, interruption and replay
   checks, and one bounded real-host receipt.
10. **Promotion:** update the owning topic and State from evidence, publish the exact limits, and
    preserve the failures that shaped the result.

The order may bend during prototyping. The published account must still distinguish what was
believed, what was attempted, and what was observed.

## Episode contract

Every episode or article should provide:

- the exact repository revision or release it demonstrates;
- a short claim ledger separating observation, inference, design, and myth;
- source and asset provenance;
- commands only after they have been executed in the named boundary;
- the most instructive failure, not only the final success;
- privacy, authority, and external-effect decisions;
- links to the canonical docs and focused tests; and
- corrections when later evidence changes the account.

AI-assisted research, scripting, narration, visual generation, and editing should be disclosed in
plain language. The Magus remains responsible for source selection, final claims, publication,
and correction. A generated explanation that no one is willing to defend does not become true
because the render is beautiful.

## Candidate tutorial seasons

### [Voidlight Studio](../compositions/voidlight-studio.md)

Follow one multimodal Pattern through source acquisition, claim checking, script and storyboard,
local model swaps, voice and image providers, artifact custody, reproducible rendering,
multimodal review, final consent, and an idempotent publication receipt.

### [Minecraft Agent Server](../compositions/minecraft-agent-server.md)

Build a private server and one bounded bot from the container and Rune through typed observation
and action tools, world snapshots, an `observe → plan → act → verify` Pattern, player consent,
restart recovery, and proof that no block changed outside the declared plot.

### [Health, Food & Movement](../compositions/health-food-and-movement.md)

Build a privacy-sensitive vertical slice through the extension decision, profile and log
migrations, deterministic allergen and unit checks, Agent/Pattern composition, local-first model
routing, plan approval, scheduled review, and complete export/deletion.

## What not to manufacture

- Do not split one shallow implementation into dozens of nearly identical videos.
- Do not publish generated commands before executing them.
- Do not disguise remote providers as local sovereignty.
- Do not convert an architectural Composition diagram into a feature announcement.
- Do not omit failed tests, manual edits, synthetic voices, or externally sourced assets when
  those facts materially change how the artifact should be judged.
- Do not expose a public server, health-adjacent recommendation, or publication credential merely
  to make a tutorial more dramatic.

The tutorial is itself a receipt: not proof that every future host will behave identically, but a
faithful account of one bounded transition from word into matter.

## Continue

- Return to the [Incubator](index.md).
- Review the accepted [Reference Compositions](../compositions/index.md).
- Read [State of the Work](../state-of-the-work.md) before presenting any current capability.
- Use the [contributor forge](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md) and the
  [Covenants](../adr/index.md) when a seed becomes selected work.
