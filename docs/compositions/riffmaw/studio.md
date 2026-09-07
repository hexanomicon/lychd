---
title: Studio
icon: material/tune-vertical
---

# :material-tune-vertical: Studio

A production plan might call for a new bass layer, a dry guitar print, a changed transition, and a candidate master. Each need belongs to a different tool role. Studio keeps those roles replaceable while Riffmaw retains the music, its acceptance, and its recoverable history.

## Closed-loop production

```text
brief + admitted sources + takes or jam
→ MusicProductionPlan@1
→ generate, capture, or separate candidates
→ analyze musical and measurable facts
→ arrange and render a multitrack revision
→ mix and master under declared targets
→ listen, measure, accept, repair, or stop
→ assets, editable session handoff, or MusicAssetBundle@1
```

Every iteration names parents and consumes a bounded attempt while accepted sources/takes remain unchanged. Model ranking, measured facts, and Magus acceptance stay distinguishable. [Music](music.md#production-autonomy) follows permitted finishes and bounded repair.

[Sessions](sessions.md#the-realtime-stopping-line) follows live deadlines and epoch recovery against `ClockDomainMap@1`. The Scroll owns execution and termination; the plan owns musical direction. Once Jam closes, its accepted captured material can enter a slower offline Invocation.

## Production roles

| Role | Owes Riffmaw | Does not own |
| --- | --- | --- |
| **Planner** | A versioned `MusicProductionPlan@1` containing creative form, track roles, desired source placements, prompts, edits, and acceptance criteria. | Executable topology, implementation choice, budgets, grants, checkpoints, retry, cancellation, or stopping law; the exact Scroll and Resolution Lock own those. |
| **Generative processor** | Music, continuation, variation, cover, repaint, conversion, production-effect, or separated-source artifacts from an exact engine and model profile with controls and receipts. | Arrangement acceptance, authorship judgment, native-stem claims, or the production session. Speech synthesis enters through Echo's admitted `tts` contract; ordinary dialogue remains [Language Edition](../language-edition/) work. |
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

`MusicProductionPlan@1` is a neutral creative record. The exact Spell implementation compiles only the creative fields admitted at its pinned placement into a tool dialect. The plan cannot be executable Python, a Scroll, a DAW session, or a provider request by implication. Failure settles the implementation; another declared exact branch or forward Invocation may try different craft without changing the current Resolution Lock.

A human handoff must name what can be continued: portable assets, MIDI, maps, processing receipts, and notes. It must not promise lossless plug-in/automation round trips merely because two programs can open a project format.

## Current candidate map

The following ledger retains the study reviewed **2026-08-26**. Its dated observations are selection inputs, not delivery or promotion receipts. Before a trial, each candidate still needs licence admission, exact engine/model profile where applicable, pinned Rune, hardware/latency measurements, hostile-input bounds, fixtures, restart behavior, and a bake against the role above. Fast-changing availability and APIs must be checked again at selection time.

| Candidate | Candidate office | Present reading |
| --- | --- | --- |
| [audio.cpp](https://github.com/0xShug0/audio.cpp), evaluated at `0.5` | Inference engine for music-generation and separation profiles | Local route for explicitly supported ACE-Step, Stable Audio, Demucs and RoFormer families. A Riffmaw profile admits only proved musical operations; server API and pipelines remain experimental, loaded sessions live until process exit, and Apache-2.0 runtime terms do not admit a model's weights. Keep exact families in isolated, lifecycle-reclaimable workers. |
| [MiniMax Music 3](https://huggingface.co/MiniMaxAI/MiniMax-Music3) | Offline generative-processor model profile | Direct long-form song candidate conditioned on lyrics plus a detailed music description. The upstream card exposes SGLang-Omni and Diffusers routes; the [Comfy-Org pack](https://huggingface.co/Comfy-Org/MiniMax-Music-3) supplies a ComfyUI-shaped route. Each pack, component, structured-caption transform, language, duration, precision, offload plan, cancellation behavior, and licence closure needs an exact bake; no route becomes Riffmaw truth or speech TTS. |
| [MiniMax hosted Music Generation](https://platform.minimax.io/docs/api-reference/music-generation) | Portal generative-processor candidate | A separate provider API currently names `music-3.0` and accepts prompt plus lyrics. It is not presumed byte-, model-, output-, or policy-equivalent to the open-weight Music 3 profile. The provider announced August 2026 access changes, so availability and terms must be rechecked before every trial; no local failure may replay here automatically. |
| [DawDreamer](https://github.com/DBraun/DawDreamer) | Isolated offline renderer and DSP/instrument host | First candidate for processor DAGs, audio and MIDI, timing, automation, VST and FAUST, and simultaneous graph-node captures. It is GPLv3 and Alpha, has no capture or live-jam contract, and emits no persistent human-editable DAW session; its “stems” are selected graph outputs. |
| [FFmpeg](https://ffmpeg.org/) | Media utility and conformance probe | Conversion, resampling, channel, packaging, and two-pass loudness-normalization route when the exact binary, build flags and sample format are pinned. Target compliance is not mastering judgment. |
| [librosa](https://github.com/librosa/librosa) | Initial analysis library | ISC-licensed first route for a bounded tempo and onset proving fixture. It is an analysis implementation, not a realtime clock or production decision-maker. |
| [PortAudio](https://www.portaudio.com/) with [python-sounddevice](https://github.com/spatialaudio/python-sounddevice) | First bounded capture worker | Small first route for one explicitly armed audio take. It does not supply the multiclient graph, musical clock, remote jam, or full studio session. |
| [PipeWire](https://pipewire.org/) with [JACK](https://jackaudio.org/) compatibility | Live graph, MIDI and monitor host candidate | Linux route for low-latency ports, links, MIDI, transport, latency and xrun evidence. It is host infrastructure rather than another inference engine and still needs a Riffmaw capture, epoch and output-fence adapter. |
| [Ableton Link](https://github.com/Ableton/link) | Optional LAN tempo and phase bridge | Provides musical tempo, beat and phase agreement. It is not audio transport, recording consent, or sample-clock authority. |
| [JackTrip](https://jacktrip.github.io/jacktrip/) | Remote-jam transport candidate | First research-bake candidate for low-latency network audio. Authentication, encryption, jitter, recording consent, drift, failure and local monitoring remain Riffmaw admissions rather than consequences of connection. |
| [DAWproject](https://github.com/bitwig/dawproject) | Neutral human-handoff candidate | MIT interchange schema for project structure and device state where a target DAW supports it. Canonical handoff remains raw and rendered assets, MIDI, tempo and markers because not every workstation round-trips the format. |
| [Essentia](https://github.com/MTG/essentia) | Optional broad analysis worker | Broad MIR coverage, but the open path is AGPLv3, commercial alternatives exist, and upstream learned-model terms can be non-commercial or no-derivatives. Do not make it the default first dependency. |
| [Matchering](https://github.com/sergree/matchering) | Watched reference-guided final processor | GPLv3 optional reference treatment whose latest packaged release is old. It matches one target's measurable spectrum, level, peak and stereo properties to a reference; it neither mixes stems nor proves musical mastering quality. |
| [Ardour](https://ardour.org/) | Human DAW and watched mature renderer | FOSS workstation for capture, sessions and stem export. Lua, OSC and `libardour` utilities deserve a later bake, but headless/API parity with complex GUI editing is not promised and arbitrary plug-ins are not sandboxed. |
| [Diff-MST](https://github.com/sai-soum/Diff-MST) | Ineligible research reference for automatic mixing | Predicts interpretable reference-conditioned gain, pan, EQ and compression, but has no stable package or API and its code is CC-BY-NC-SA. It cannot enter the FOSS Core path under the present policy. |
| [ACE-Step DAW](https://github.com/ace-step/ACE-Step-DAW) | Design reference | Its sequential “LEGO” generation and scriptable browser state resemble Riffmaw's desired loop, but it is an AGPL WIP browser/Tone.js application with IndexedDB state, no releases, and no versioned remote agent contract. |

## Minimum first proofs

The proposed offline proof chooses one baked music profile. The dated study selects MiniMax Music 3 through an immutable allowlisted ComfyUI preset as the first long-form candidate, with `audio.cpp` as the alternative family road. It also calls for a separated-source profile, isolated DawDreamer with allowlisted processors, pinned FFmpeg, librosa tempo/onset probes, and a LychD sample-accurate compiler from creative plan placements into the exact render graph.

That proof may establish `assets_only` and bounded `assisted_session`. Its human return is stems, MIDI, tempo/markers, processor receipts, and mix notes—not a native DawDreamer project. Add PortAudio only for the separate armed-take proof.

The live proof starts again from its own contract: PipeWire/JACK graph and clock evidence, MIDI scheduling, capture writer, output-deadline fence, then a machine player. Scheduled symbolic MIDI precedes any realtime ACE-Step audio claim. Remote Jam and automatic mix control remain later bakes. New tools enter only when they close a missing musical role.
