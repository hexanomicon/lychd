---
title: Riffmaw
icon: material/music-circle
---

# :material-music-circle: Riffmaw

Riffmaw turns remembered moments, recordings, words, and sonic intent into attributable music,
voice, effects, and ambience. AI generation, live performance, editing, and signal processing can
all contribute; the Magus remains the producer and no model or DAW owns the craft.

| Field | Reference contract |
| --- | --- |
| **Identity** | `riffmaw.audio` revision `1` |
| **Principal Pattern** | `riffmaw.forge_sonic_bundle@1` |
| **Begins with** | a sonic brief plus any explicitly admitted references, words, takes, MIDI, scores, samples, or live inputs |
| **Can return** | `SonicAssetBundle@1`, `PerformanceSession@1`, `SonicCandidateSet@1`, `RiffmawFindingSet@1`, optional `SyncCueMap@1`, or an exact refusal |
| **Stops before** | visual generation, final audiovisual assembly, performer impersonation, or publication |

## Ways of making

Riffmaw can complete the same application purpose through different production modes:

| Mode | Representative Pattern | Human and machine relation | Typed finish |
| --- | --- | --- | --- |
| **Forge** | `riffmaw.forge_track@1` | A brief, references, words, or an empty session drive offline composition and generation. | `SonicCandidateSet@1` or `RiffmawFindingSet@1`. |
| **Perform** | `riffmaw.capture_take@1` | Explicitly armed audio or MIDI preserves what one or more people play, sing, speak, or program. | `PerformanceSession@1` containing attributed takes and observations. |
| **Jam** | `riffmaw.open_jam@1` | Performers and admitted machine players share mapped clocks and answer one another live or ahead of a declared musical boundary. | Recoverable `PerformanceSession@1` or `RiffmawFindingSet@1`. |
| **Produce** | `riffmaw.forge_sonic_bundle@1` | Riffmaw iterates arrangement, mix, mastering, deterministic probes, and attributable listening review. | `SonicAssetBundle@1`, `SonicCandidateSet@1`, `RiffmawFindingSet@1`, or refusal. |

The Patterns connect through typed artifacts and new forward Invocations; one Pattern never nests
or silently resumes another. A later Scroll may publish exact capture, generation, render, and
review Spell placements inside one casting, but only with its own revision, Resolution Lock, and
authority ceilings. Opening a file does not arm an input; arming a guitar does not authorize
synthesis or model training; accepting a machine accompaniment does not approve the mix; exporting
a master does not authorize publication.

## The work

- [Sources](sources.md) finds exact moments without turning an ambient media library into authority.
- [Sessions](sessions.md) preserves armed inputs, human recordings, takes, MIDI, live jams, and performance conditions.
- [Music](music.md) covers composition, AI generation, arrangement, editing, mixing, and mastering.
- [Studio](studio.md) defines the replaceable production-tool roles and the current candidate stack.
- [Voice](voice.md) binds spoken or sung performance to approved words and performer authority.
- [Sound](sound.md) creates and edits effects, foley, textures, and ambience.
- [Sync](sync.md) exposes sonic timing without directing the image.
- [Package](package.md) seals lineage, effects, recovery, and the consumer handoff.

[Voidlight](../voidlight/) owns visual assets. [Broadcast](../broadcast/) owns editorial assembly,
the final timeline, and publication effects.

Related: [Audio](../../adr/37-audio.md) · [Workflow](../../adr/28-workflow.md) ·
[Composition portfolio](../index.md)
