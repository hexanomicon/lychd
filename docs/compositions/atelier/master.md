---
title: Video master
icon: material/movie-cog-outline
---

# Video master

A door closes exactly as the latch clicks. The caption stays on screen long enough to read. The
music falls away before the next line. These decisions belong to the same cut. In
`atelier.studio` revision `6`, `atelier.finish_video_master@1` takes a video commission through
its storyboard, audiovisual timeline, render and final review. The accepted local result is
`VideoMaster@1`. This is the application design. The [local cut](short-video.md#try-a-local-cut)
exercises one technical render, and the [Portfolio delivery record](../../state-of-the-work.md#composition-portfolio-delivery)
tracks native delivery.

## Edit the timeline

Start with the [brief](brief.md), the approved words or other source material, and an explicit
target. Pin the timebase, aspect, frame and duration limits, sound and caption requirements, and
the tests the director will use. Show the storyboard in sequence with actual selected references,
shot lengths, camera and action, spoken words, captions, and sound cues. Record the director's
decision against that exact revision. A request for changes creates a successor for review.
A render that requires storyboard approval waits for it.

In the [proposed Atelier cut workspace](../../divination/altar/applications.md#cut-a-video-in-atelier),
follow one caption from its timeline cue to the frame where the observatory dome opens.

Each timeline entry names its source revision and digest, permitted role, in and out points,
placement, transforms, and relation to any script span or claim. Retain use limits, provenance,
validator findings and approval. The cut can combine several roles.

- Visuals from [Assets](assets.md) or [Motion](motion.md), including an admitted
  `VisualAssetBundle@1`.
- An exact `MusicAssetBundle@1` and optional `MusicCueMap@1` from [Riffmaw](../riffmaw/sync.md).
  Moving a musical entrance changes the cut. Moving an accent *within* the music requires a
  successor from its producer.
- A `TimedLanguageAssetBundle@2` from [Language Edition](../language-edition/index.md), with its
  approved performance or captions, source script, locked picture and timing anchors. A changed
  cut may need a new alignment.
- The picture-bound sound prepared for this cut, including any `PictureSoundCueMap@1`.

An asset request names the role, timing, constraints, and source or likeness conditions.
`VisualAssetRequest@1`, `MusicAssetRequest@1`, and `LanguageVersionRequest@2` keep their request
digests and producer boundaries. Each declared model-generated facet also brings its own
`SemanticFacetAdmissionReceipt@1`, linked to the shared compound parent when present. Atelier
records how the admitted contributions work together. A request for a new generated shot opens a
new visual attempt. Trims, transitions, title overlays and the final mix are operations on the
versioned timeline.

## Picture-bound sound

For the latch, pin the locked picture digest, frame rate, scene and event in the
`PictureSoundBrief@1`. Specify the room, listening distance, source and rights references,
target channels, loudness and acceptance criteria. Recordings, licensed layers, synthesis,
processing and audio from generated video can supply candidates for foley, room tone, effects,
environmental beds or ambience.

Before a model runs, `MediaFacetAuthoritySet@1` must name the `picture_sound` role,
`atelier.studio` revision `6` and the exact picture-sound brief digest. A joint video request
also names its visual role and commission digest. Music and timed-language facets require
separate declarations for their owners. Core keeps the technical attempt and Prism retains the
compound digest, child digests, timebase and production lineage.

Audition the candidate against the locked shot. `PictureSoundRevision@1` and the optional cue
map record event, material, distance, perspective, duration, continuity and uncertainty. Check
channels, boundaries, clipping and loudness, then judge the impact against the visible latch.
Atelier issues a distinct semantic admission receipt for each of its accepted roles and seals the
accepted sound revisions as `PictureSoundBundle@1`. Quarantine or delete undeclared sound. When
streams cannot be separated, each required owner must accept that exact compound use. Trimming
the reverberation or changing the picture, brief, claim or timebase reopens the affected review.
Interactive world sound has its own event and runtime judgment in [Foundry](../foundry/sound.md).

## Render and review

Pin the timeline, renderer and project revision, input digests, fonts, filters, color settings,
codec, channel layout, loudness target and caption format. A pinned FFmpeg or equivalent renderer
can trim, concatenate, retime, overlay, mix, mux and encode the approved timeline. Retain the
output digest and probes for duration, dimensions, frame rate, color, stream layout, caption
presence and tolerances. Measure the end of picture and audio against the duration limit.

Play the actual export from beginning to end. Review pacing, continuity, the relation of picture
to words, caption timing and legibility, contrast, motion and flashing hazards, intelligibility,
music and effects balance, language and channel alternatives. Record the final verdict against
the **rendered bytes** and target. A technical pass can still leave a cut that needs revision.
A missing font, failed probe, wrong aspect, unsupported input or new claim returns a specific
finding to the responsible owner. Retain the original and recheck the affected parts of a
successor before asking for final approval.

## Return the master

`VideoMaster@1` binds the accepted render digest, timeline and target revisions, source and
asset manifests, facet receipts, technical probes, use boundaries and final review. The local
commission can finish here. An authorized private commission may return the master to its named
requester through [Intercom](../../sepulcher/intercom.md) under a separate transfer decision.
[A short video for a colleague](short-video.md) follows both reviews and collection after reconnect.
For channel distribution, [Broadcast](../broadcast/distribution.md) admits the exact settled
master and evidence.

On restart, recover the pinned commission, storyboard decision, timeline, render occurrence and
candidate digest before advancing. A completed write can outlive its acknowledgement. Reconcile
the destination and checksum against that occurrence, keeping the outcome unknown while evidence
is missing. A changed input stales its dependent approvals. Render success, master acceptance,
private transfer and public release each have distinct receipts.
