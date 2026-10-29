---
title: Sessions
icon: material/record-circle-outline
---

# :material-record-circle-outline: Sessions

Keep what was actually played before editing makes it seem inevitable. A take preserves one armed performance; a jam adds participants, mapped clocks, and the conditions under which their responses could be heard.

## Arm and capture

Arm the exact performance route before `riffmaw.capture_take@2` begins. Admission pins its device, clocks, sample rate, latency, monitoring, channels, plug-in state, session revision, and consent. Preserve immutable raw audio/MIDI first, so later transcription, timing correction, comping, cleanup, or transformation can always identify the performance it changed.

`PerformanceTake@1` separates performance from attributed tempo, pitch, timing, score/lyric transcription, and other observations. Their source regions and uncertainty remain visible. [Audio](../../adr/37-audio.md) governs visible, bounded, revocable capture, custody, and hostile input. A later `MusicalPerformanceSession@1` may reference settled takes; shared file formats do not create a jam.

## Choose without erasing

When choosing the best passages, record each source take and selected region in the comp. Acceptance does not rewrite rejected takes or their retention rules. Changes to device, clock, plug-in, or session likewise create explicit revisions.

If a failure leaves capture uncertain, first stop the device. Reconcile the artifacts and session state before retrying; silence cannot prove that nothing was recorded.

[Music](music.md) receives artifacts and observations without an open DAW, microphone authority, or credentials. Ordinary spoken replacement/localization remains Language Edition work.

## Jam in shared time

`riffmaw.open_jam@2` brings participants into one bounded musical session. Spellweaver admits its Invocation/Scroll; the Pattern cannot admit its own Circle or nested production.

Microphones, instruments, MIDI/controllers, clips, remote performers, and machine players each declare monitor, recording, retention, analysis, transformation, remote transmission, and response scope. Required preservation without admitted recording/retention refuses the route or jam. Network presence does not grant recording consent; one performer cannot change another's participation or monitor scope.

“follow behind my attack,” “answer only at phrase endings,” and “that distortion is energy, not a key change” can create successor `FeelProfile@1` revisions. They correct interpretation without rewriting performance or earlier observations. This is the long road toward performance-native direction through timing, touch, phrasing, dynamics, repetition, and contrast. Persistent personalization/training still requires separate corpus admission and model promotion.

`MusicalPerformanceSession@1` binds revision, participants/roles, assistance policy, model/tool allowlist, and these exact records:

| Record | Binds |
| --- | --- |
| `ClockDomainMap@1` | Audio sample frames, monotonic time, beat and bar position, clock epoch, external, leader or distributed mode, peer mappings, clock-rate divergence, resampling, and uncertainty. A remote peer never implies sample lock. |
| `LiveAudioGraphProfile@1` | Driver, sample rate, quantum and periods, ports and links, channel map, declared direct-monitor route, measured capture, playback and round-trip latency, xruns, hot-plug events, and graph revisions. |
| `MidiEventStream@1` | Device and port, MIDI 1 or UMP profile, channel and sample offset, notes, CC and sustain, bend, pressure or MPE, transport events, event loss, and admitted SysEx policy. |
| `CaptureManifest@1` | Immutable pre-fader sources, optional processed prints, MIDI, hardware returns, local and remote stems, exact frame boundaries, discontinuities, and checksums. A guitar DI remains separate from its amp or cabinet monitor path. |
| `RemoteJamLeg@1` | Peer identity, topology, codec, channels, encryption, jitter buffer, loss concealment, latency estimate, clock-rate divergence, resampling, reconnect epoch, local-monitor policy, and recording consent. |

Together, these records keep the mix, individual sources, MIDI/control events, responses, and route/clock changes attributable. Graph checkpoints refer to that work through typed references, bounded sequence state, and receipts. The PCM/MIDI streams, device handles, and plug-in state remain outside those checkpoints.

A route's participation is **observe** (correctable observations, no audible reply), **accompany** (bounded musical answer), **transform** (process the selected live route while preserving dry source), or **conduct** (propose structural/tempo/cue changes). Escalation needs new visible admission by every affected Principal; proposals cannot silently become changes to a human performance.

## Performance as a correctable language

`MusicalGestureObservation@1` may interpret notes/chords, key/tuning, beat/pocket, accents, articulation, dynamics, timbre, phrases, repetition, tension/release, and player relations. Preserve source regions, feature/model revisions, latency, confidence, and competing readings. It grants no access to emotion or unspoken intent.

A musical answer must also explain when it was prepared and when it actually entered. `JamResponse@1` binds source-time cutoff and lookahead, jam/route epochs, turn sequence, answered observation/cue, controls, ready-by deadline, scheduled window, planned/actual first audible sample, measured latency, output acknowledgement, omission reason, and audio/MIDI artifact. This preserves the difference between an intended entrance and its observed result.

## The realtime stopping line

[Audio](../../adr/37-audio.md#application-owned-live-audio) owns callback, clock-epoch, output-fence, monitoring, reconnect, and uncertain-playback law. Riffmaw adds musical beat/bar mapping and deadline windows. A late machine entrance may be safely omitted; the human monitor remains available without a model. Partial sessions retain acknowledged takes/events. Continuation is a newly armed Invocation with new musical clock and route epoch.

## Proving the jam

Use armed dry guitar DI, keyboard MIDI, two local performer roles, and a synthetic remote leg with controlled jitter, loss, and clock-rate divergence. Capture every named clock/graph/MIDI/manifest record and a scheduled response. Exercise xrun, removal, epoch loss, plug-in crash/latency change, late output, and uncertain remote acknowledgement. Prove continued direct monitoring, stale-output fencing, raw audio/MIDI reconciliation, and newly admitted continuation. Export session, sources, stems, MIDI, tempo, and marker maps. This fixture proves state and recovery; measured device latency and musical usefulness need a separate hardware bake.
