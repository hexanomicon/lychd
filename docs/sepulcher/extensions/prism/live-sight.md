---
title: Live Sight
icon: material/video-wireless-outline
---

# :material-video-wireless-outline: Live Sight

A finite observation has a last frame. An armed camera route needs an explicit way to end,
account for missing frames, and keep old observations from acting as current sight. This designed
passage defines that session around [Sight's](sight.md) typed visual estimates.

`LiveSightSession@1` is not delivered. [Vision](../../../adr/36-vision.md) owns its contract;
[State of Work](../../../state-of-the-work.md#vision-admission) owns delivery. The controlling
Composition admits capture and every world effect; Sight returns observations under that scope.

## Arm one bounded session

A camera or RTSP feed is not an infinite `SightJob`. The later `LiveSightSession@1` pins camera and
controller identity, named purpose, retained admitted authority or policy receipt, viewers, zones
and privacy masks, active window, resolution and rate, separately admitted raw-frame access,
recording, analysis, retention and egress scopes, stream epoch, queue, cardinality, latency and
resource budgets, sampling and drop policy, and downstream consumers. The receipt records the
basis LychD admitted; it is not a claim of legal certification.

## Keep frame and clock truth

Frame identity is stream epoch plus sequence. Reported RTP, device, or PTS clocks may be absent,
synthesized, or reset, so their provenance and mapping to monotonic and wall clocks retain explicit
synchronization uncertainty. Queues are bounded. When upstream cannot pause, the admitted profile
samples or drops under an explicit policy and emits exact gaps and watermarks. A proved contiguous
transport reconnect may continue the same epoch; otherwise it closes. Every new epoch receives a
new local track namespace. Cross-epoch association is a separately attributed inference, never a
reused track identity. Checkpoints retain references, cursors, prompts, and gaps—not raw frames,
framework objects, device handles, or unbounded history.

## Contain transport and control

[GStreamer](https://gstreamer.freedesktop.org/documentation/frequently-asked-questions/general.html)
is the first later live transport candidate for RTSP jitter, timestamps, hardware decode, and
bounded [`appsink`](https://gstreamer.freedesktop.org/documentation/app/appsink.html) delivery.
Pipeline strings and network routes are immutable allowlisted Rune profiles, never operator or
model-authored code. Only the contained transport worker receives the exact admitted RTSP route;
inference workers remain networkless. Starting capture, PTZ, recording, camera configuration,
robot motion, or another world effect remains with the controlling Composition. Sight only observes.
