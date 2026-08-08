---
title: Sync
icon: material/timeline-clock-outline
---

# :material-timeline-clock-outline: Sync

Sync translates an accepted sonic revision into cues another craft can answer without letting
Riffmaw direct the picture.

`riffmaw.prepare_sync_map@1` emits `SyncCueMap@1`: a neutral map of audible events, ranges,
intensity, continuity, entrances, exits, accents, transitions, and uncertainty under one declared
timebase. Every cue points to the exact `SonicAssetBundle@1` revision and source region that
supports it.

The map may carry beat grids, section boundaries, dialogue regions, effect events, or synchronization
anchors. It does not prescribe a camera, image, cut, animation, or editorial claim.
[Voidlight](../voidlight/motion.md) decides how visual motion responds. [Broadcast](../broadcast/edit.md)
owns placement in the final audiovisual timeline and may request a forward correction rather than
editing Riffmaw's map.

Prism [Kinesis](../../sepulcher/extensions/prism/kinesis.md) may consume the exact map in a
declared `synchronize` or constrained-generation job. The resulting motion is a new derivative
that retains the sonic digest, clock relation, anchors, and uncertainty. Kinesis neither rewrites
the map nor decides which visible response Voidlight accepts.

A frame-rate conversion, retime, shortened master, or changed mix can stale the map. The consumer
must reject a mismatched sonic digest or timebase. Riffmaw can issue a new map revision; it never
rewrites the accepted history or claims that two independently changed timelines still align.

An audiovisual Suite may coordinate the same brief, exact sonic and visual bundles, and sync map.
It pins revisions and typed handoffs but owns no files, provider sessions, creative approvals,
budgets, Sigils, or publication authority.
