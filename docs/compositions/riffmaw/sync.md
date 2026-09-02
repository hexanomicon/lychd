---
title: Sync
icon: material/timeline-clock-outline
---

# :material-timeline-clock-outline: Sync

Sync translates an accepted music revision into cues another craft can answer without letting
Riffmaw direct the picture.

`riffmaw.prepare_music_cue_map@1` emits `MusicCueMap@1`: a neutral map of musical events, ranges,
intensity, continuity, entrances, exits, accents, transitions, and uncertainty under one declared
timebase. Every cue points to the exact `MusicAssetBundle@1` revision and source region that
supports it.

The map may carry beat grids, section boundaries, vocal or instrumental entrances, musical
transitions, or synchronization anchors. Dialogue-replacement regions belong to [Language Edition](../language-edition/), while
picture-bound effect and ambience cues belong to Broadcast. The music map does not prescribe a
camera, image, cut, animation, or editorial claim.
[Voidlight](../voidlight/motion.md) decides how visual motion responds. [Broadcast](../broadcast/edit.md)
owns placement in the final audiovisual timeline and may request a forward correction rather than
editing Riffmaw's map.

Prism [Kinesis](../../sepulcher/extensions/prism/kinesis.md) may consume the exact map in a
declared `synchronize` or constrained-generation job. The resulting motion is a new derivative
that retains the music digest, clock relation, anchors, and uncertainty. Kinesis neither rewrites
the map nor decides which visible response Voidlight accepts.

A frame-rate conversion, retime, shortened master, or changed mix can stale the map. The consumer
must reject a mismatched music digest or timebase. Riffmaw can issue a new map revision; it never
rewrites the accepted history or claims that two independently changed timelines still align.

An audiovisual Suite may coordinate the same brief, exact music and visual bundles, and cue map.
It pins revisions and typed handoffs but owns no files, provider sessions, creative approvals,
budgets, Sigils, or publication authority.
