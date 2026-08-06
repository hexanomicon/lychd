---
title: Riffmaw
icon: material/music-circle
---

# :material-music-circle: Riffmaw

A sound often arrives sideways: a timestamp, a mouth-made rhythm, a remembered drop, a spoken
line, or a guitar take worth keeping. Riffmaw turns those moments into attributable music, voice,
effects, and ambience while leaving the Magus in charge of what the work becomes.

> “At `01:32` it drops: _tz, tz, u-do_. Keep the pressure and spacing, change the musical matter,
> and mark the transitions another craft can answer.”

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `riffmaw.audio` revision `2` |
| **Principal Pattern** | `riffmaw.forge_sonic_bundle@1` |
| **Application begins with** | operator-admitted sources, remembered moments, optional live takes or approved words, and a sonic brief |
| **Application can return** | `SonicAssetBundle@1`, an optional `SyncCueMap@1`, or an exact refusal |
| **Application stops before** | visual generation, audiovisual assembly, rights certification, performer impersonation, or publication |

Riffmaw owns reference moments, sessions, takes, musical structure, arrangements, performances,
sound effects, ambience, stems, mixes, masters, and synchronization markers. A DAW, plug-in,
model, decoder, or media index remains replaceable machinery. [Voidlight](voidlight-studio.md) owns
visual assets; [Broadcast](broadcast-studio.md) owns editorial assembly, the final timeline, and
publication effects.

## Mark, play, and forge

1. **Admit the sources.** The Magus names exact files, recordings, or attributed source artifacts;
   recursion, symlinks, bytes, duration, decoding work, and retention are bounded before indexing.
2. **Mark the moment.** A timestamp, beat range, tapped rhythm, or phrase such as _tz, tz, u-do_
   yields ranked source spans under a pinned feature set. The Magus chooses the useful span.
3. **Capture a take.** An explicitly armed interface records its device profile, clocks, latency,
   monitoring route, plug-in state, and immutable raw audio or MIDI before proposing transcription.
4. **Describe the feel.** Pocket, density, accents, space, motion, and energy become an editable
   `FeelProfile`; the performer may correct it, play the answer, or reject it.
5. **Forge the work.** Accepted moments, takes, and words guide original music, performances,
   effects, ambience, stems, mix, and master. Every generated or transformed artifact keeps its
   tool, provider, control material, cost, and digest.
6. **Prepare synchronization.** Audible events become time windows, intensity, continuity, and
   transition markers in a `SyncCueMap@1` fitted to the exact sonic revision. The map describes
   sound and time; it does not prescribe images.

## Session records and sonic handoff

| Pattern | Return |
| --- | --- |
| `riffmaw.index_sources@1` | a bounded, attributable index of approved media |
| `riffmaw.mark_moment@1` | a human-selected `ReferenceMoment@1` with source, timebase, features, uncertainty, and rights posture |
| `riffmaw.capture_take@1` | a `PerformanceTake@1` preserving raw performance and attributed observations |
| `riffmaw.forge_track@1` | original musical work, score or MIDI when present, stems, and master |
| `riffmaw.forge_voice_pack@1` | approved performances tied to exact words, performer authority, and takes |
| `riffmaw.forge_sound_pack@1` | attributable effects and ambience for declared semantic roles |
| `riffmaw.forge_sonic_bundle@1` | `SonicAssetBundle@1` with assets, mix relationships, credits, provenance, findings, and checksums |
| `riffmaw.prepare_sync_map@1` | neutral `SyncCueMap@1` tied to the accepted sonic revision |

An audiovisual Suite may give the same brief and `SyncCueMap@1` to Voidlight, then hand the
resulting `SonicAssetBundle@1` and `VisualAssetBundle@1` to Broadcast. The Suite coordinates exact
revisions and typed artifacts; it does not merge files, records, secrets, Sigils, budgets,
approvals, or provider authority.

## Rights, effects, and return

Riffmaw never crawls an ambient home directory. Having a file is not evidence of permission, and
feature similarity is not proof of authorship or safe reuse. Requests “in the style of” are reduced
to reviewable musical properties; unresolved rights or similarity, performer impersonation, voice
cloning, or lifted melody leads to quarantine, replacement, review, or refusal.

Capture, paid generation, DAW export, and application handoff are separate effects with exact
payload digests and receipts. If a DAW or plug-in may have written a file before acknowledgement
was lost, the result stays **unknown** until the destination is inspected; Riffmaw never repeats
the effect merely to obtain a cleaner answer.

Restart pins source, feature, Pattern, model, plug-in, session, and export revisions. Raw takes,
rejected candidates, accepted works, indexes, stems, masters, and handoffs have separate retention
rules. Deletion stops capture and indexing, removes permitted derivatives, inventories exported
copies, and retains only required content-free receipts.

## Proving session

Use two local synthetic two-minute references with known events, one thirty-second guitar or MIDI
take, one approved spoken fixture, and a marker at `01:32`. Produce deterministic onset and tempo
observations, an editable `FeelProfile`, an original four-section arrangement, one voice or effect
asset, stems, a local mix, three synchronization markers, restart-safe indexing, and a
lineage-complete `SonicAssetBundle@1`. No arbitrary folder, ambient microphone, copyrighted
catalogue, Portal, visual generation, paid effect, or platform call enters the proof.

Related: [Voidlight](voidlight-studio.md) · [Broadcast](broadcast-studio.md) ·
[Audio](../adr/37-audio.md) · [Composition portfolio](index.md)
