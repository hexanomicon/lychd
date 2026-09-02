---
title: Voidlight
icon: material/camera-iris
---

# :material-camera-iris: Voidlight

Voidlight turns a visual commission into an attributable package of images, models, textures,
visual effects, and motion. The Magus remains the visual director; generators, editors, renderers,
and deterministic tools remain replaceable machinery. Here **VFX means visual effects**, never
sound effects.

| Field | Reference contract |
| --- | --- |
| **Identity** | `voidlight.studio` revision `4` |
| **Principal Pattern** | `voidlight.build_visual_package@2` |
| **Begins with** | an admitted commission, frozen references, a target profile, and acceptance criteria |
| **Can return** | one approved, immutable `VisualAssetBundle@1`, or an exact non-completion |
| **Stops before** | sound production, engine import, final audiovisual assembly, publication, or rights certification |

Revision `4` supersedes the Designed-only revision `3` because its audiovisual handoff consumes a
`MusicCueMap@1` and routes model-returned sound by role instead of reinterpreting the former
`SyncCueMap@1` sequence contract. The former `voidlight.build_visual_package@1` and
`voidlight.forge_visual_sequence@1` meanings remain historical; revision `4` uses `@2`. No
Portfolio registry or Run used revision `3`, so no executable migration exists.

The commission also declares its finish boundary. It may complete honestly with an accepted still,
continue through an admitted image-to-video or first/last-frame path, or seal a larger visual
package. A later continuation starts from the immutable earlier artifact; it does not keep a
finished image Run artificially paused. [Motion](motion.md#progressive-visual-depth) follows the
reference journey.

## The work

- [Brief](brief.md) freezes the commission, references, constraints, source influence, and
  acceptance line.
- [Direction](direction.md) turns taste into a reviewable visual system without making a model the
  author.
- [Assets](assets.md) creates, transforms, reviews, and traces still images, models, textures, and
  other visual material.
- [Motion](motion.md) owns generated or authored animation and visual sequence timing, but not
  sound or the final edit.
- [Package](package.md) seals the approved revisions, effects, recovery rules, and consumer
  handoff.

Voidlight owns its commission, visual judgment, candidates, accepted revisions, provenance, and
package. [Riffmaw](../riffmaw/) owns music; [Language Edition](../language-edition/) owns timed-language editions;
[Foundry](../foundry/) owns engine integration; and [Broadcast](../broadcast/) owns picture-bound
sound, editorial assembly, the final timeline, and publication.

Related: [Workflow](../../adr/28-workflow.md) · [Vision](../../adr/36-vision.md) ·
[Composition portfolio](../index.md)
