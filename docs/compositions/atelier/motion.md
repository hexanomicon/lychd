---
title: Motion
icon: material/movie-open-outline
---

# :material-movie-open-outline: Motion

The first frame has been chosen. Motion asks what should change, over which timebase, and how the director will recognize a finished sequence. Its material includes animation, transitions, camera movement, loops, and generated or authored visual sequences.

Prism's [Video](../../sepulcher/aspects/prism/video.md) supplies pixel effects; [Kinesis](../../sepulcher/aspects/prism/kinesis.md) supplies structured motion recovery, generation, retargeting, cleanup, synchronization, and conversion. Atelier keeps choreography, visual direction, review, and acceptance across those replaceable tools. The [video master](master.md) owns the full audiovisual edit and picture-bound sound.
Riffmaw retains musical judgment, Language Edition retains timed-language judgment, and
Broadcast decides channel distribution and release.

## Progressive visual depth

The commission declares an accepted still, accepted motion, or sealed package as the requested finish. `atelier.build_visual_package@3` may contain exact image, review, motion, probe, and package placements branching on that typed policy. Alternatively, a completed image becomes immutable input to a new `atelier.forge_visual_sequence@3` Invocation.

A path through motion to a sealed package is:

```text
brief + target profiles + language policy
→ ImageJob@2 generate or edit
→ review and select exact first frame
→ optional second boundary image
→ VideoJob@2 i2v or first_last
→ temporal probe and visual review
→ VisualAssetBundle@1
```

At a requested still boundary, success is terminal. A declared review Gate or hardware transition may enter Stasis while something remains outstanding; future animation alone is no reason to keep the completed Run open.

The Scroll names Image and Video Spell contracts. Its exact Resolution Lock may bind Qwen Image and an LTX-2.5 Comfy preset, other local profiles, or separately admitted Portal implementations. This is an illustrative binding, not a delivery claim. Prism's prompt-translation record preserves original/model-facing texts, translator revision, and loss; an imported Comfy graph is no portable Scroll or global Translation service.

## Clips and cues

`atelier.forge_animation_set@1` binds clips to exact assets and Form rigs, plus Kinesis motion revisions when used. `atelier.forge_visual_sequence@3` binds frame rate, duration, aspect, continuity, and transitions. Exports retain source revisions, tools, transforms, timeline, probes, and checksum.

A [Riffmaw](../riffmaw/sync.md) `MusicCueMap@1` offers musical events, windows, intensity, and transitions. The director chooses their visual answer without editing the musical map. Audio conditioning likewise requires an exact admitted reference.

A video attempt may also produce sound, so its owners must be known before execution. For a `VideoJob@2` in the visual-only `@3` score,
`MediaFacetAuthoritySet@1` must declare the visual role, `atelier.studio` revision `5`, and
the exact commission request digest. The new master score binds revision `6` and its own request. Any sound role needs separate authority.

After production, Atelier issues its own `SemanticFacetAdmissionReceipt@1` for the visual facet, keeping the compound Prism parent attached. Riffmaw, Language Edition and Foundry separately admit declared music, timed-language or
world-sound facets. For new video masters, Atelier admits [picture-bound sound](master.md#picture-bound-sound)
against its own picture-sound brief. A facet produced for an earlier owner retains its original receipt. Undeclared sound is quarantined/deleted. When streams are inseparable, refusal by any required owner prevents use of the compound.

Those judgments may concern one joint model attempt with a shared timebase. They require neither
duplicate generation nor a separate screen for each role; [Vision](../../adr/36-vision.md#compound-media-and-application-acceptance)
keeps the single technical parent and each facet's admission explicit.

## Review the movement

Check the sequence duration against the target, then review across that full duration: seams, ordering, camera continuity, clipping, flicker/accessibility hazards, and export stability can fail between otherwise acceptable frames. A bounded correction makes a successor revision. A wrong timebase, stale assets, unsupported profile, or ambiguous synchronization returns findings or refusal.

[Package](package.md) receives accepted motion as visual material. In a [finished video](master.md),
Atelier owns placement, trim, retiming, transitions, caption integration and the mix. Broadcast
owns editorial claims about what the sequence depicts and its use in a channel publication.
Foundry owns engine import and runtime behavior. Each owner judges its own use of the same input.

## Procedural rendering study

[RAEA at `7caf1bb`](https://github.com/shinyobjectz/raea/tree/7caf1bb5966dd536d007eb531dfe1c54f387fe69)
renders scenes authored in React and TypeScript to individual frames or video on a local GPU.
Its [technical checks](https://github.com/shinyobjectz/raea/blob/7caf1bb5966dd536d007eb531dfe1c54f387fe69/apps/check/src/lib.rs)
can use a render manifest to report findings such as clipped text with a location on the timeline.

The candidate idea is an independent Atelier and Prism workflow for short motion graphics.
Pin the scene, assets, renderer and timebase, render a preview or export, and bind each finding to
the exact output and affected time. A correction produces a successor candidate. Prism can
supply rendering and technical findings. Atelier judges the result against the visual brief.

RAEA is an inspiration for a bounded [Assimilation study](../../sepulcher/aspects/weaver/assimilation.md#upstream-reuse-and-notices).
Start from the behavior and author the local implementation independently. The upstream
[FSL-1.1-ALv2 license](https://github.com/shinyobjectz/raea/blob/7caf1bb5966dd536d007eb531dfe1c54f387fe69/LICENSE)
restricts competing commercial use. Any proposal to integrate RAEA or incorporate upstream
material needs its own review of the exact material and intended use.

A first experiment could render one short scene with text deliberately clipped at a known time,
then correct it in a new revision. The check must identify the first export and affected time,
and a repeat check must establish that the successor fixes the defect. Atelier reviews the
corrected sequence against the original visual criteria before accepting it.
