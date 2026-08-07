---
title: Sessions
icon: material/record-circle-outline
---

# :material-record-circle-outline: Sessions

Sessions preserves what a person actually played, sang, spoke, or programmed before editing makes
the result look inevitable.

## Arm and capture

`riffmaw.capture_take@1` starts only through an explicitly armed interface. It records the device
profile, clocks, sample rate, latency, monitoring route, channel layout, plug-in state, session
revision, and consent boundary. The immutable raw audio or MIDI is retained before transcription,
timing correction, comping, cleanup, or transformation.

A `PerformanceTake@1` distinguishes raw performance from observations about it. Tempo, pitch,
timing, transcription, and performance notes remain attributed interpretations with their source
regions and uncertainty. They do not replace the recording. Capture authority is visible,
time-bounded, revocable, and governed by the custody and hostile-audio rules in
[Audio](../../adr/37-audio.md).

## Choose without erasing

Comping and editing create new revisions that name every source take and selected region. Rejected
takes remain subject to their own retention rule; an accepted comp never rewrites them. A changed
device, clock, session state, or plug-in chain is explicit rather than smuggled into a continuation.

If capture state is uncertain after failure, Riffmaw stops the device and reconciles the artifact
and session records before retry. It never assumes that silence means nothing was recorded.

Accepted takes may anchor [Music](music.md), [Voice](voice.md), or [Sound](sound.md). The handoff
shares exact artifact references and observations, not microphone authority, credentials, or an
open DAW session.
