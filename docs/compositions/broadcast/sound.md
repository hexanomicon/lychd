---
title: Picture-Bound Sound
icon: material/surround-sound
---

# :material-surround-sound: Picture-Bound Sound

A door closes in a small room. Its impact, distance, reverberant tail, and the silence around it belong to the meaning of that exact shot. Broadcast calls this **picture-bound sound design**: effects, foley, room tone, environmental beds, and ambience judged against picture, scene, cut, claim, or editorial timeline.

Start with the exact cut. When does the door hit the frame, and how long should the room ring
afterward? For `broadcast.design_picture_sound@2`, the editor records the locked picture's
digest and timebase in `PictureSoundBrief@1`, along with the event and the space it needs to
convey. The brief identifies source and rights references, target channels and loudness, and
the criteria for accepting a sound.

A recording, a synthesized or licensed layer, a processed sound, or audio from a generated
video can all supply candidates. Each layer keeps its source, implementation, transforms,
rights, timing, and digest so the editor can trace what they hear in the cut.

## Hear the scene, then admit the result

Play the candidate against the locked shot. In `PictureSoundRevision@1` and optional
`PictureSoundCueMap@1`, record the event, place, material, distance, listening perspective,
duration, continuity, relation to the cut, and uncertainty. Probe boundaries, clipping, channels,
loudness, and format. Even a clean recording fails this cut if the impact comes before the
latch hits. Seal accepted selections as `PictureSoundBundle@1` for [Edit](edit.md).

Riffmaw owns music; Language Edition owns spoken performance/captions against a locked source; Echo owns speech lifecycle; Foundry may own game-event sound. A reusable standalone library would need its own proved Composition records, judgment, finish, and recovery. Broadcast's scene does not create that owner.

## When the video model also returns sound

Can the editor use a slam that came back with a generated shot? Before the model runs,
`MediaFacetAuthoritySet@1` must declare `picture_sound`, `broadcast.studio` revision `4`, and
the exact `PictureSoundBrief@1` digest. Core keeps the technical attempt. Prism preserves the
compound and child digests, timebase, and provenance.

After technical settlement, Broadcast auditions the sound and issues its own
`SemanticFacetAdmissionReceipt@1`. Extracting a track, enabling `generate_sound`, or approving
the picture cannot admit the audio. Quarantine or delete unexpected audio. If picture and sound
are inseparable, every required owner must accept that exact compound use.

Trim the cut through the reverberation and the affected sound is stale. Changes to the picture,
source claim, timebase, or brief have the same consequence. Corrections create successors.
A recorder, generator, renderer, or destination that loses its acknowledgement leaves the
outcome `unknown` until reconciled. The accepted bundle can enter [Edit](edit.md).
[Render](render.md) handles the final mux, and publication requires a separate
[release decision](release.md).
