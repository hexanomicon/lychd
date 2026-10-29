---
title: Riffmaw
icon: material/music-circle
---

# :material-music-circle: Riffmaw

Riffmaw is the music-making application being developed for LychD. Its intended experience is
to describe an idea, bring a reference or performance, hear alternatives, and shape the music
with AI assistance and approachable controls. The interface should offer detailed production
controls when needed, while keeping small changes accessible without DAW expertise.

An assistant can help develop a brief, propose material or edits, and compare candidates within
the requested scope. The Magus chooses what to keep. A remembered drop, a guitar take, a sung
line, or an empty session can all begin the craft; their contributions remain attributable.

## Start with a musical idea

The intended interaction begins with a musical request, for example:

- “Make a short psytrance sketch, with a quieter opening and a stronger bass entrance.”
- “Turn this part down; let me compare it with the previous version.”
- “Use this reference moment to explore a similar texture with different notes.”

[Workbench](workbench.md#approachable-interaction) develops that edit-and-listen experience.
Its [development operations](workbench.md#development-operations) describe the finite engineering
tools available to exercise today; they do not yet supply the native application or an AI
listening assistant. [State of Work](../../state-of-the-work.md#music-comfy-engineering-probes)
keeps that implementation boundary.

## Ways of making

| Road | Pattern | What can finish here |
| --- | --- | --- |
| **Forge** | `riffmaw.forge_track@2` | Offline composition/generation from a brief, references, lyrics, or empty session: `MusicCandidateSet@1` or `MusicFindingSet@1`. |
| **Perform** | `riffmaw.capture_take@2` | Explicitly armed audio/MIDI from played, sung, rapped, musical-spoken-word, or programmed performance: `PerformanceTake@1` and observations/findings. |
| **Jam** | `riffmaw.open_jam@2` | Performers and admitted machine players answering against mapped clocks: recoverable `MusicalPerformanceSession@1` or findings. |
| **Produce** | `riffmaw.forge_music_bundle@2` | Bounded arrangement, mix, master, probes and listening review: `MusicAssetBundle@1`, candidates, findings, or refusal. |

Each road ends by settling its own Invocation. Carry exact artifacts into later forward work without nesting or silently resuming another Pattern. A future Scroll may combine separately named capture/generation/render/review placements, but must do so under its own revision, Resolution Lock, and authority ceiling.

The passage between roads preserves their separate decisions: file access does not arm an input, a take does not admit training, a candidate mix is not master approval, and export does not publish.

## The work

Find the material in [Sources](sources.md), down to the exact musical moment. When people or
machines perform, [Sessions](sessions.md) preserves their takes and shared time;
[Hardware](hardware.md) admits the capture routes they use. [Music](music.md) develops that
material into an arrangement and master candidate.

Choose machinery through [Studio](studio.md), which keeps tool roles and dated candidates
separate from the craft. For uncertain roles, [Voice](voice.md) distinguishes musical performance
from speech, and [Sound](sound.md) follows what belongs to music. [Sync](sync.md) offers cues for
another work; [Package](package.md) seals the musical handoff.

## Reference contract

`riffmaw.music` revision `2` accepts a music brief plus explicitly admitted references, lyrics, takes, MIDI, scores, samples, or live inputs. Alongside the road-specific returns, it can issue `MusicCueMap@1`. It stops before ordinary dialogue, spoken replacement/localization, picture sound, visuals, final audiovisual assembly, impersonation, and publication. Language Edition, Broadcast, Atelier, and their technical providers retain those offices.

Prompt, lyric, requested sung language, and interface locale remain separate. Exact model profiles must prove their musical/language behavior; a local ComfyUI or other Soulstone binding and a Portal API are independently evidenced implementations. [Music](music.md#language-belongs-to-the-musical-request) owns the request; [Studio](studio.md#current-candidate-map) records candidates.

## Revision continuity

??? info "Earlier designs and their exact successors"

    `riffmaw.audio` revision `1`, its `Sonic*` family, and former `riffmaw.forge_track@1`, `riffmaw.capture_take@1`, `riffmaw.open_jam@1`, `riffmaw.index_sources@1`, and `riffmaw.mark_moment@1` are retired without reinterpretation. New identity `riffmaw.music` revision `1` used the five Pattern names at `@2`. Revision `2` advances principal `riffmaw.forge_music_bundle` to `@2` for model-native pre-execution music authority and semantic admission. `MusicAssetBundle@1` already accommodates those exact provenance receipts; other music Patterns remain unchanged. No registry, Run, or stored application record used the retired designs, so no executable migration exists.

[Audio](../../adr/37-audio.md) · [Workflow](../../adr/28-workflow.md) · [Composition Portfolio](../index.md)
