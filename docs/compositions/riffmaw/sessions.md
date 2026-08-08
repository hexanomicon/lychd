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

## Jam in shared time

Live Jam is **Designed** beyond Audio's first record-and-send slice; no current Portfolio runtime
or candidate stack proves it. `riffmaw.open_jam@1` describes one bounded performance Pattern.
Spellweaver separately admits its Invocation and exact Scroll; the Pattern cannot admit a Circle or
nested production by itself.

A jam may contain microphones, guitars, keyboards, drum pads, controllers, MIDI, previously
admitted clips, remote performers, and one or more machine players. Every route independently
declares monitoring, recording, retention, analysis, transformation, remote transmission, and
machine-response scopes. If preservation of a route is required but recording or retention is not
admitted, Riffmaw refuses that route or the jam. Network presence is never recording permission,
and the Magus cannot alter another performer's monitor or participation scope unilaterally.

`PerformanceSession@1` binds the jam revision, participants and roles, assistance policy, model and
tool allowlist, and these timing and capture records:

| Record | Binds |
| --- | --- |
| `ClockDomainMap@1` | Audio sample frames, monotonic time, beat and bar position, clock epoch, external, leader or distributed mode, peer mappings, drift, resampling, and uncertainty. A remote peer never implies sample lock. |
| `LiveAudioGraphProfile@1` | Driver, sample rate, quantum and periods, ports and links, channel map, declared direct-monitor route, measured capture, playback and round-trip latency, xruns, hot-plug events, and graph revisions. |
| `MidiEventStream@1` | Device and port, MIDI 1 or UMP profile, channel and sample offset, notes, CC and sustain, bend, pressure or MPE, transport events, event loss, and admitted SysEx policy. |
| `CaptureManifest@1` | Immutable pre-fader sources, optional processed prints, MIDI, hardware returns, local and remote stems, exact frame boundaries, discontinuities, and checksums. A guitar DI remains separate from its amp or cabinet monitor path. |
| `RemoteJamLeg@1` | Peer identity, topology, codec, channels, encryption, jitter buffer, loss concealment, latency estimate, drift, resampling, reconnect epoch, local-monitor policy, and recording consent. |

The shared jam mix, individual sources, MIDI and control events, model responses, and clock or route
changes remain separately attributable. No PCM, MIDI stream, device handle, or plug-in state enters
Graph state; checkpoints retain typed references, bounded sequence state, and receipts.

The admitted participation level for every affected route is one of:

- **observe** records and derives correctable musical observations but produces no audible reply;
- **accompany** may add a bounded rhythmic, harmonic, melodic, or textural answer;
- **transform** may process an explicitly selected live route while preserving its dry source; and
- **conduct** may propose section, tempo, cue, or arrangement changes, but cannot silently impose
  them on human performers.

Escalating the participation level requires a new visible admission by every affected Principal.
A model may not turn observation into accompaniment, accompaniment into transformation, or a jam
into autonomous publication by inference.

## Performance as a correctable language

A `MusicalGestureObservation@1` may interpret notes, chords, key or tuning, beat and pocket,
accents, articulation, dynamics, timbre, phrase boundaries, repetition, tension, release, and the
relation between players. It retains the exact source regions, feature and model revisions,
latency, confidence, and competing interpretations. It is an observation about performed sound,
not access to the performer's emotions or unspoken intent.

A `JamResponse@1` binds the context available through an exact source time, its lookahead, jam and
route epochs, turn sequence, the observation or explicit cue it answered, generation controls,
ready-by deadline, scheduled window, planned and actual first audible sample, measured path
latency, output acknowledgement, omission reason, and resulting audio or MIDI artifact. Performer
corrections create a new immutable `FeelProfile@1` instance linked to its predecessor: “follow behind my attack,” “answer
only at phrase endings,” or “that distortion is energy, not a key change.” A correction links but
never rewrites the performance, observation, or earlier profile.

This is the long route toward performance-native direction: a player can steer Riffmaw through
timing, touch, phrasing, dynamics, repetition, and contrast rather than translating every musical
decision into prose. Persistent personalization or training from those performances is a separate
corpus-admission and model-promotion act; a jam alone authorizes neither.

## The realtime stopping line

Generic callback, clock-epoch, output-fence, direct-monitoring, reconnect, and uncertain-playback
law lives in [Audio](../../adr/37-audio.md#application-owned-live-audio). Riffmaw adds musical beat
and bar mapping, `JamResponse@1` ready-by and scheduled windows, and a safe omission when a machine
entrance is late. The human monitor route remains available without model cooperation. A partial
`PerformanceSession@1` preserves acknowledged takes and events; continuation is a newly armed
forward Invocation with a new musical clock and route epoch.

## Proving the jam

Use a focused fixture with an explicitly armed dry guitar DI, keyboard MIDI, two local performer
roles, and one synthetic remote leg with controlled jitter, loss, and clock drift. Capture a
`ClockDomainMap@1`, `LiveAudioGraphProfile@1`, `MidiEventStream@1`, `CaptureManifest@1`, and one
scheduled `JamResponse@1`. Exercise xrun, device removal, clock-epoch loss, plug-in crash or latency
change, late model output, and uncertain remote acknowledgement. Prove that direct monitoring
continues, stale frames cannot enter the output route, raw audio and MIDI reconcile, and
continuation requires a new Invocation. Export the attributable session, source artifacts, stems,
raw MIDI, and neutral tempo and marker maps. This deterministic fixture proves state, fencing, and
recovery; a later hardware bake must separately prove measured audio-device latency and musical
usefulness.
