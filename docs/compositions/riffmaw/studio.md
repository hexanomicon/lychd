---
title: Studio
icon: material/tune-vertical
---

# :material-tune-vertical: Studio

Riffmaw is the producer and application contract; no inference runtime, plug-in host, DAW, or
workflow UI becomes its identity. The Studio admits replaceable tools behind typed jobs so the same
production can return assets for manual work, an editable handoff, or an autonomously produced
master candidate for the Magus to accept.

## Production roles

| Role | Owes Riffmaw | Does not own |
| --- | --- | --- |
| **Planner** | A versioned `SonicProductionPlan@1` containing creative form, track roles, desired source placements, prompts, edits, and acceptance criteria. | Executable topology, implementation choice, budgets, grants, checkpoints, retry, cancellation, or stopping law; the exact Scroll and Resolution Lock own those. |
| **Generative processor** | Music, continuation, variation, cover, repaint, conversion, effect, or separated-source artifacts from an exact engine and model profile with controls and receipts. | Arrangement acceptance, authorship judgment, native-stem claims, or the production session. Speech synthesis enters through Echo's admitted `tts` contract. |
| **Analysis worker** | Attributed tempo, beat, onset, pitch, chord, section, similarity, loudness, clipping, and quality observations with uncertainty. | Creative approval or permission to transform its source. |
| **Offline studio renderer** | A pinned timeline and processing graph with tracks, clips, MIDI, routing, automation, processors, intermediate renders, node captures, and master buses. | Capture, live monitoring, creative mix decisions, the brief, source rights, performer consent, or publication. |
| **Live graph and monitor host** | A realtime-safe audio graph, device and route lifecycle, direct monitoring, latency and xrun evidence, output fence, and emergency bypass. | Model planning, recording permission, or a promise that remote peers are sample-locked. |
| **Timebase coordinator** | Explicit mappings among sample frame, monotonic time, musical beat and bar, MIDI or network tempo, epochs, drift, and uncertainty. | Authority to retime an accepted performance or treat tempo phase as audio transport. |
| **MIDI connector and machine-player scheduler** | Attributed MIDI/UMP events and deadline-fenced future audio or MIDI entrances against one clock epoch. | Permission to read arbitrary devices, admit SysEx, or emit stale responses. |
| **Capture writer** | Immutable pre-fader audio, MIDI and discontinuity manifests without blocking the realtime callback. | Analysis, transformation, retention beyond the admitted policy, or the canonical session record. |
| **Remote-jam transport** | Authenticated audio/MIDI carriage, codec and jitter state, latency, loss, drift, reconnect epochs, acknowledgements, and local-monitor policy. | Recording consent, a shared sample clock, or Composition authority. |
| **DSP and instrument host** | Allowlisted processor binaries, instruments, presets, ports, automation, latency compensation, tails, crash isolation, safe bypass, state, and rendered output. | Ambient plug-in discovery or silent substitution of a missing processor. |
| **Mastering worker** | A target-bound final processing revision and measurable loudness, peak, dynamics, stereo, sample-rate, and format facts. | Musical acceptance merely because numerical targets passed. |
| **Media utility** | Bounded decode, encode, resample, trim, join, metadata, waveform, and conformance operations. | Semantic interpretation or application finish. |
| **Human DAW projection** | Portable assets, tempo and marker maps, automation or mix notes, and enough lineage to continue manually. | The canonical Riffmaw record or authority to mutate it behind the handoff. |

`SonicProductionPlan@1` is a neutral creative Riffmaw record rather than a Python script, Scroll,
DAW session file, or provider request. A Spell implementation compiles only the creative fields
admitted for its exact pinned placement into one tool dialect. A failed implementation settles;
another exact predeclared branch or a new forward Invocation may try different admitted craft, but
the casting never rewrites its Resolution Lock. A human can continue in another workstation
without pretending that every plug-in and automation lane round-trips losslessly.

## Current candidate map

This design study was reviewed on **2026-08-07**. It is not delivery evidence or final engine
promotion. Each candidate still owes license admission, an exact engine and model profile where
applicable, a pinned Rune, hardware and latency measurements, hostile-input limits, deterministic
fixtures, restart behavior, and a bake against the Riffmaw contract.

| Candidate | Candidate office | Present reading |
| --- | --- | --- |
| [audio.cpp](https://github.com/0xShug0/audio.cpp) `0.5` | Inference engine for generative and separation model profiles | Promising, rapidly moving local route for explicitly supported ACE-Step, Stable Audio, Demucs and RoFormer families. Server API and pipelines remain experimental; loaded sessions live until process exit, and Apache-2.0 runtime terms do not admit a model's weights. Keep exact families in isolated, lifecycle-reclaimable workers. |
| [DawDreamer](https://github.com/DBraun/DawDreamer) | Isolated offline renderer and DSP/instrument host | Strong first candidate for processor DAGs, audio and MIDI, timing, automation, VST and FAUST, and simultaneous graph-node captures. It is GPLv3 and Alpha, has no capture or live-jam contract, and emits no persistent human-editable DAW session; its “stems” are selected graph outputs. |
| [FFmpeg](https://ffmpeg.org/) | Media utility and conformance probe | Mature conversion, resampling, channel, packaging, and two-pass loudness-normalization route when the exact binary, build flags and sample format are pinned. Target compliance is not mastering judgment. |
| [librosa](https://github.com/librosa/librosa) | Initial analysis library | Active ISC-licensed first route for a bounded tempo and onset proving fixture. It is an analysis implementation, not a realtime clock or production decision-maker. |
| [PortAudio](https://www.portaudio.com/) with [python-sounddevice](https://github.com/spatialaudio/python-sounddevice) | First bounded capture worker | Small first route for one explicitly armed audio take. It does not supply the multiclient graph, musical clock, remote jam, or full studio session. |
| [PipeWire](https://pipewire.org/) with [JACK](https://jackaudio.org/) compatibility | Live graph, MIDI and monitor host candidate | Strong Linux route for low-latency ports, links, MIDI, transport, latency and xrun evidence. It is host infrastructure rather than another inference engine and still needs a Riffmaw capture, epoch and output-fence adapter. |
| [Ableton Link](https://github.com/Ableton/link) | Optional LAN tempo and phase bridge | Useful for musical tempo, beat and phase agreement. It is not audio transport, recording consent, or sample-clock authority. |
| [JackTrip](https://jacktrip.github.io/jacktrip/) | Remote-jam transport candidate | Credible first research bake for low-latency network audio. Authentication, encryption, jitter, recording consent, drift, failure and local monitoring remain Riffmaw admissions rather than consequences of connection. |
| [DAWproject](https://github.com/bitwig/dawproject) | Neutral human-handoff candidate | MIT interchange schema for project structure and device state where a target DAW supports it. Canonical handoff remains raw and rendered assets, MIDI, tempo and markers because not every workstation round-trips the format. |
| [Essentia](https://github.com/MTG/essentia) | Optional broad analysis worker | Credible MIR coverage, but the open path is AGPLv3, commercial alternatives exist, and upstream learned-model terms can be non-commercial or no-derivatives. Do not make it the default first dependency. |
| [Matchering](https://github.com/sergree/matchering) | Watched reference-guided final processor | GPLv3 optional reference treatment whose latest packaged release is old. It matches one target's measurable spectrum, level, peak and stereo properties to a reference; it neither mixes stems nor proves musical mastering quality. |
| [Ardour](https://ardour.org/) | Human DAW and watched mature renderer | Strong FOSS workstation for capture, sessions and stem export. Lua, OSC and `libardour` utilities deserve a later bake, but headless/API parity with complex GUI editing is not promised and arbitrary plug-ins are not sandboxed. |
| [Diff-MST](https://github.com/sai-soum/Diff-MST) | Ineligible research reference for automatic mixing | Predicts interpretable reference-conditioned gain, pan, EQ and compression, but has no stable package or API and its code is CC-BY-NC-SA. It cannot enter the FOSS Core path under the present policy. |
| [ACE-Step DAW](https://github.com/ace-step/ACE-Step-DAW) | Design reference | Its sequential “LEGO” generation and scriptable browser state resemble Riffmaw's desired loop, but it is an AGPL WIP browser/Tone.js application with IndexedDB state, no releases, and no versioned remote agent contract. |

## Minimum first proofs

The first offline proof needs one baked `audio.cpp` music profile and one separated-source profile,
an isolated DawDreamer renderer with allowlisted processors, a pinned FFmpeg worker, librosa tempo
and onset probes, and a LychD-owned sample-accurate compiler from `SonicProductionPlan@1` creative
placements to one pinned render graph. It can prove `assets_only` and a bounded
`assisted_session`; the human handoff is stems, MIDI, tempo, markers, processor receipts, and mix
notes rather than a native DawDreamer project.

The first input proof adds one PortAudio capture worker for a bounded armed take. The first live
proof is separate: PipeWire/JACK graph and timebase evidence, MIDI scheduling, capture writer,
output deadline fence, and only then a machine player. Symbolic MIDI scheduled ahead into a pinned
synth is a more credible first jam response than claiming ACE-Step audio is realtime before Linux
hardware measurements exist. Remote Jam and an automatic mix controller remain later bakes.

Additional tools earn admission by closing a missing Riffmaw role, not by offering another UI over
the same models.

## Closed-loop production

```text
brief + admitted sources + takes or jam
→ SonicProductionPlan@1
→ generate, capture, or separate candidates
→ analyze musical and measurable facts
→ arrange and render a multitrack revision
→ mix and master under declared targets
→ listen, measure, accept, repair, or stop
→ assets, editable session handoff, or SonicAssetBundle
```

Every loop iteration names its parents and consumes a bounded attempt. A quality gate can request a
forward repair such as repainting one region, regenerating one layer, changing an effect chain, or
rebalancing the mix. It cannot silently mutate an accepted take or source. A model judgment may
rank candidates, but deterministic facts and the Magus's acceptance remain distinguishable.

For live work, admitted creative intent is scheduled against a `ClockDomainMap@1` in deadline-fenced
turns; the Scroll, not the plan, owns executable topology and termination. The realtime path favors
a safe omission over a late or uncertain machine entrance. Accepted captured material can enter a
new, slower offline Invocation only after the jam closes.
