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

Before arming, pin participants, purpose and consent scopes, exact upstream session or admitted
transport references and epochs, calibration and target-rig revisions, requested channels, and
clock maps with their uncertainty. Define the armed window, latency, cardinality, compute and
cost bounds, bounded queue, sampling, resampling, reorder and drop policy, consumers, retention,
and output-segment policy.

Each output then binds its motion epoch, source cursor, target-rig digest, and deadline, allowing
the consumer to reject stale motion. A calibration, sender, target-rig, or unproved reconnect
change rotates the motion epoch. If upstream cannot pause, sampling and drops must expose exact
gaps and watermarks rather than hide latency or invent motion. Disconnect preserves acknowledged
segments; resuming the same epoch requires proved transport continuity. Otherwise, admit a newly
armed forward session.

## Deliver through an admitted transport

[VMC](https://protocol.vmc.info/english.html) over
[OSC](https://opensoundcontrol.stanford.edu/spec-1_0.html) is a candidate for a later admitted
motion-transport or output-projection profile. Its first profile allowlists motion messages;
file paths, configuration, MIDI/control, and passthrough messages require separate authorization.
Kinesis may consume an admitted transport or create the projection artifact, but sending to or
opening a target avatar endpoint belongs to a separately authorized Foundry or avatar adapter.

Neither OSC nor VMC supplies application authentication or guaranteed reliable delivery. The
profile must bind an admitted sender and network zone, allowlist message addresses, and retain
receive time, reorder, and drop facts. If sender or clock continuity cannot be proved, rotate
the epoch. [GStreamer](https://gstreamer.freedesktop.org/) may preserve media clocks, PTS, gaps,
reorders, and drops as media substrate, not as a Kinesis runtime. Its core is LGPL-2.1-or-later;
plug-in and codec licenses remain profile-specific.

Checkpoints retain configuration, cursors, exact segment references, and gaps, excluding sockets,
device handles, tensors, and unbounded history. Stopping Kinesis establishes neither that upstream
capture stopped nor that a downstream avatar stopped moving.

## Earlier Designed revisions

`KinesisJob@2` supersedes the Designed-only `KinesisJob@1`: its `synchronize` input names
`MusicCueMap@1` rather than reinterpreting `SyncCueMap@1`, and its result settles technical motion
without adopting it for an application. `LiveKinesisSession@2` likewise supersedes the Designed-only
`LiveKinesisSession@1` because it consumes Riffmaw's narrower `MusicalPerformanceSession@1` rather
than reinterpreting `PerformanceSession@1`. Neither older contract was registered or run, so there
is no executable migration.
