---
title: Live Kinesis
icon: material/motion-play-outline
---

# :material-motion-play-outline: Live Kinesis

Live motion joins an admitted source epoch to one exact target rig and a bounded consumer.
The session must expose latency, gaps, recalibration, stopping, and stale output rather than
stretch a finite clip into an endless job. [Kinesis](kinesis.md) retains the technical motion
facets and validation used by each admitted segment.

`LiveKinesisSession@2` is Designed. [Vision](../../../adr/36-vision.md) owns the accepted contract;
[State of Work](../../../state-of-the-work.md#vision-admission) records the absent implementation.
Upstream capture and downstream avatar, engine, or physical control remain separately owned.

## Live motion comes later

A camera, tracking endpoint, instrument, or microphone is not an infinite `KinesisJob`. The later
`LiveKinesisSession@2` consumes exact upstream epochs from `LiveSightSession@1`, Riffmaw
`MusicalPerformanceSession@1` and `ClockDomainMap@1`, or a separately armed mocap transport. It inherits
no camera, microphone, MIDI, avatar, robot, or world-effect authority.

## Pin the session and preserve its epoch

The session pins participants; purpose and consent scopes; exact upstream session or admitted
transport references and epochs; calibration and target-rig revisions; requested channels; clock
maps and uncertainty; armed window; latency, cardinality, compute and cost bounds; bounded queue;
sampling, resampling, reorder, and drop policy; consumers; retention; and output-segment policy.
Every output binds the motion epoch, source cursor, target-rig digest, and deadline so consumers
can reject stale results. Calibration, sender, target-rig, or unproved reconnect changes rotate
the motion epoch. When an upstream source cannot pause, sampling and drops emit exact gaps and
watermarks rather than hidden latency or invented motion. Disconnect retains acknowledged
segments; only proved transport continuity may resume the same epoch, otherwise a newly armed
forward session is required.

## Deliver through an admitted transport

[VMC](https://protocol.vmc.info/english.html) over
[OSC](https://opensoundcontrol.stanford.edu/spec-1_0.html) is a later admitted motion-transport or
output-projection profile, not Core law. Its first profile allowlists motion messages and rejects
file paths, configuration, MIDI/control, and passthrough messages unless separately authorized.
Kinesis may consume an admitted source transport or create the projection artifact; it does not
open or send to a target avatar endpoint. A separately authorized Foundry or avatar adapter owns
that effect. OSC and VMC provide neither application authentication nor guaranteed reliable
delivery. A profile binds an admitted sender and network zone, allowlists message addresses,
records receive time, reorder and drop facts, and rotates the epoch whenever sender or clock
continuity cannot be proved. [GStreamer](https://gstreamer.freedesktop.org/) may preserve media
clocks, PTS, gaps, reorders, and drops; its core is LGPL-2.1-or-later while plug-in and codec
licenses remain profile-specific. It is media substrate rather than a Kinesis runtime. Checkpoints
retain configuration, cursors, exact segment references, and gaps—not sockets, device handles,
tensors, or unbounded history. Stopping Kinesis proves neither that upstream capture stopped nor
that a downstream avatar stopped moving.

## Earlier Designed revisions

`KinesisJob@2` supersedes the Designed-only `KinesisJob@1`: its `synchronize` input names
`MusicCueMap@1` rather than reinterpreting `SyncCueMap@1`, and its result settles technical motion
without adopting it for an application. `LiveKinesisSession@2` likewise supersedes the Designed-only
`LiveKinesisSession@1` because it consumes Riffmaw's narrower `MusicalPerformanceSession@1` rather
than reinterpreting `PerformanceSession@1`. Neither older contract was registered or run, so there
is no executable migration.
