---
title: Riffmaw
icon: material/music-circle
---

# :material-music-circle: Riffmaw

Riffmaw turns remembered moments, recordings, words, and musical intent into attributable music.
AI generation, instrumental or vocal performance, editing, and signal processing can all
contribute; the Magus remains the producer and no model or DAW owns the craft.

| Field | Reference contract |
| --- | --- |
| **Identity** | `riffmaw.music` revision `1` |
| **Principal Pattern** | `riffmaw.forge_music_bundle@1` |
| **Begins with** | a music brief plus any explicitly admitted references, lyrics, takes, MIDI, scores, samples, or live inputs |
| **Can return** | `PerformanceTake@1`, `MusicalPerformanceSession@1`, `MusicAssetBundle@1`, `MusicCandidateSet@1`, `MusicFindingSet@1`, optional `MusicCueMap@1`, or an exact refusal |
| **Stops before** | ordinary dialogue, spoken dialogue replacement or spoken-media localization, picture-bound sound design, visual generation, final audiovisual assembly, performer impersonation, or publication |

The earlier Designed-only `riffmaw.audio` revision `1`, its `Sonic*` contract family, and the former
`riffmaw.forge_track@1`, `riffmaw.capture_take@1`, `riffmaw.open_jam@1`,
`riffmaw.index_sources@1`, and `riffmaw.mark_moment@1` meanings are retired, not reinterpreted.
`riffmaw.music` revision `1` is a new, narrower identity and uses those five Pattern names only as
`@2` revisions. No Portfolio registry, Run, or stored application record uses the retired design, so
there is no executable migration; historical references retain their old meaning.

Prompt language, lyric language, requested sung language, and interface locale remain separate.
The exact Riffmaw model profile owns proved musical and language behavior; Soulstone may bind it to
a local ComfyUI or another admitted runtime, while Portal may bind a separately evidenced hosted
API. Similar product names never make those implementations equivalent. [Music](music.md#language-belongs-to-the-musical-request)
owns the request boundary and [Studio](studio.md#current-candidate-map) keeps the candidate routes.

## Ways of making

Riffmaw can complete the same application purpose through different production modes:

| Mode | Representative Pattern | Human and machine relation | Typed finish |
| --- | --- | --- | --- |
| **Forge** | `riffmaw.forge_track@2` | A brief, references, lyrics, or an empty session drive offline composition and generation. | `MusicCandidateSet@1` or `MusicFindingSet@1`. |
| **Perform** | `riffmaw.capture_take@2` | Explicitly armed audio or MIDI preserves what one or more people play, sing, rap, perform as musical spoken word, or program. | One attributable `PerformanceTake@1` plus exact observations or findings. |
| **Jam** | `riffmaw.open_jam@2` | Performers and admitted machine players share mapped clocks and answer one another live or ahead of a declared musical boundary. | Recoverable `MusicalPerformanceSession@1` or `MusicFindingSet@1`. |
| **Produce** | `riffmaw.forge_music_bundle@1` | Riffmaw iterates arrangement, mix, mastering, deterministic probes, and attributable listening review. | `MusicAssetBundle@1`, `MusicCandidateSet@1`, `MusicFindingSet@1`, or refusal. |

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
- [Voice](voice.md) keeps musical vocals here while routing ordinary dialogue, spoken dialogue replacement, captions,
  and spoken timed-language editions to [Language Edition](../language-edition/).
- [Sound](sound.md) distinguishes musical production effects from Broadcast's picture-bound sound
  and the unresolved reusable-sound office.
- [Music hardware boundary](hardware.md) admits exact instrument and musical-vocal capture routes
  while the shared Animator page keeps generic Linux, speech, mobile, and body mechanics.
- [Sync](sync.md) exposes musical timing without directing the image.
- [Package](package.md) seals lineage, effects, recovery, and the consumer handoff.

[Voidlight](../voidlight/) owns visual assets. [Broadcast](../broadcast/) owns picture-bound sound,
editorial assembly, the final timeline, and publication effects. Language Edition owns ordinary dialogue,
spoken dialogue replacement, captions, and spoken timed-language editions. Reusable standalone
sound remains an unresolved future standalone-sound Composition boundary rather than hidden
Riffmaw scope.

Related: [Audio](../../adr/37-audio.md) · [Workflow](../../adr/28-workflow.md) ·
[Composition portfolio](../index.md)
