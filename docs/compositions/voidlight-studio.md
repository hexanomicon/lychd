---
title: Voidlight
icon: material/camera-timer
---

# :material-camera-timer: Voidlight

A commission arrives as references, constraints, questions, and taste. Voidlight turns that
material into a creative package whose assets can be inspected, revised, and handed to another
craft without losing their origin. The Magus remains the creative director throughout.

!!! note "Current material"
    Voidlight is a Native Reference Composition, not an executable application today. No
    Voidlight Pattern, Studio record, or `CreativeAssetBundle@1` production path is registered;
    Vision and Audio admission are Partial, and durable artifact custody remains Designed.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `voidlight.studio` revision `2` |
| **Principal Pattern** | `voidlight.build_asset_package@1` |
| **Application begins with** | an admitted commission, frozen reference dossier, rights posture, and target profile |
| **Application can return** | one approved, immutable, rights-aware `CreativeAssetBundle@1`, or an exact non-completion |
| **Application stops before** | engine-native import, editorial assembly, public release, or rights certification |

Voidlight owns the commission, creative brief, reference dossier, style and asset specifications,
candidates, accepted assets, provenance, and package. Providers and tools supply capabilities;
they do not become the application's identity or acquire creative authority.

## Commission to package

1. **Freeze the dossier.** Admit only named references, record their digests, classification,
   permitted purpose, and unresolved rights or consent questions.
2. **Set the brief.** Pin the commission, target profile, style revision, budget, and acceptance
   criteria before production starts.
3. **Specify the work.** Give every requested image, model, texture, dialogue, audio, or cutscene
   source a semantic role and concrete spatial, temporal, and format constraints.
4. **Produce and normalize.** Acquire or create candidates, then probe and transform them with
   pinned tools, configurations, input digests, and output digests.
5. **Review once.** Findings identify the smallest supported correction. One bounded repair may
   create a new candidate; exhausted repair, denied rights, or an unmet profile ends honestly.
6. **Accept and hand off.** Seal the manifest, approvals, lineage, validators, and checksums in a
   `CreativeAssetBundle@1`; the consumer performs its own admission against the exact digest.

The narrower scores remain available for work that should not pretend to be the whole package:
`voidlight.establish_style_bible@1`, `voidlight.forge_concept_set@1`,
`voidlight.forge_sprite_set@1`, `voidlight.forge_texture_set@1`,
`voidlight.forge_model_asset@1`, `voidlight.forge_dialogue_pack@1`,
`voidlight.forge_audio_pack@1`, and `voidlight.forge_cutscene_sources@1`.
`voidlight.export_asset_package@1` assembles the handoff;
`voidlight.review_asset_package@1`, `voidlight.revise_from_correction@1`, and
`voidlight.presenter_calibration@1` keep review, forward repair, and calibration distinct.

## Lineage and consumer handoff

| Record | What it preserves |
| --- | --- |
| Commission and dossier | admitted purpose, references, classifications, rights claims, and retention |
| Asset revision | immutable id, role, source and derivative digests, creator/tool receipt, transforms, review, and approval |
| Production receipt | provider or tool revision, prompt/control material, seed when available, cost, probes, and result |
| `CreativeAssetBundle@1` | bundle revision and digest, target profile, asset manifest, constraints, provenance, validators, findings, and approval |

[Foundry](game-foundry.md) owns engine imports, playability, builds, and release effects.
[Broadcast](broadcast-studio.md) owns claims, scripts, timelines, renders, accessibility, and
publication. Neither consumer may rewrite Voidlight's lineage, and a Studio handoff carries no
Sigil, secret, provider session, or downstream effect authority.

## Rights, effects, and return

Reference rights are checked before use. Likeness or voice consent is scoped to identity, purpose,
territory, duration, and revocation; approval for one asset does not authorize another use. Portal
egress, paid generation, replacement of accepted material, and final handoff each require their
own exact gate.

Paid generation and external handoff are effects bound to an idempotency key and request digest.
If acknowledgement is lost, the outcome is **unknown** until the provider or consumer result is
reconciled against that digest. Retrying blindly could buy or send the work twice and is refused.

A later bad reference, revoked consent, or failed finding marks dependent material stale without
editing accepted history. Restart resumes only with the pinned Pattern, schema, provider, tool,
receipt, and artifact revisions. Incompatible parked work drains, migrates explicitly, or ends
non-complete. Deletion inventories derivatives and consumer handoffs; it can request downstream
removal, but cannot promise that an exported copy vanished.

## Proving package

Build one local, style-led 2D package from a licensed reference dossier: a style bible, concept and
sprite or texture assets, deterministic probe and normalization, one bounded repair, and one
accepted `CreativeAssetBundle@1`. The proof uses no engine import, channel render, Portal call,
paid generation, or public release.

Related: [Workflow](../adr/28-workflow.md) · [Vision](../adr/36-vision.md) ·
[Audio](../adr/37-audio.md) · [Composition portfolio](index.md)
