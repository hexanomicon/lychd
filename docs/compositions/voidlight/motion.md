---
title: Motion
icon: material/movie-open-outline
---

# :material-movie-open-outline: Motion

Motion owns visual change through time: animation sets, transitions, camera movement, loops, and
visual sequences. It does not own music, sound effects, the final audiovisual timeline, or public
rendering.

`voidlight.forge_animation_set@1` produces animation clips tied to exact asset and rig revisions.
`voidlight.forge_visual_sequence@1` arranges visual events under a declared frame rate, duration,
aspect profile, continuity rules, and transition constraints. Every exported clip retains the
source asset revisions, tools, transforms, timeline, probes, and checksum that made it.

A `SyncCueMap@1` from [Riffmaw](../riffmaw/sync.md) may describe audible events, time windows,
intensity, and transitions. Voidlight decides how—or whether—those cues receive a visual answer.
The map does not prescribe images, and Voidlight does not alter its sonic revision.

Review checks declared motion rather than only the last frame: duration, loop seams, temporal
ordering, camera continuity, clipping, flicker or accessibility hazards, and export stability.
One bounded correction may create a new revision. A mismatched timebase, stale input asset,
unsupported profile, or ambiguous synchronization ends with a finding or refusal instead of a
best-effort clip.

The accepted motion remains a visual artifact inside the [package](package.md). Broadcast owns its
placement beside sound, captions, and editorial claims; Foundry owns engine-native import and
runtime behavior.
