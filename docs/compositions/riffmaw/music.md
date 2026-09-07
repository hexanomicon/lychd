---
title: Music
icon: material/music-note-outline
---

# :material-music-note-outline: Music

A guitar phrase can become the center of an arrangement, a reference for an accompaniment, or material the producer decides to leave alone. Music keeps that choice editable through generation, performance, composition, sampling, signal processing, and DAW work.

## Compose and arrange

`riffmaw.forge_track@2` pins brief, sources, `FeelProfile@1`, target form, budget, and acceptance. A model may propose motifs, harmony, rhythm, timbre, sections, or complete sketches; a human performance or another method can answer or replace them. Each artifact retains tool/provider revision, controls, seed where available, source influence, input/output digests, and cost.

`FeelProfile@1` can begin as direction or derive from correctable take/[jam](sessions.md#jam-in-shared-time) observations: pocket, density, attack, space, motion, instrumental relation, tension/release, and when the machine should listen. Corrections create linked immutable revisions, never facts about the performer's unspoken intent. The Magus selects structure, tempo map, meter, key/tuning, roles, transitions, repetition, and variation. A generated sketch remains a candidate.

## Language belongs to the musical request

Brief language, structured-description language, lyrics, requested sung language, and phonetic/transliteration aids are separate typed inputs. Preserve original words. An exact Translation Spell can propose a lexical derivative; Riffmaw owns lyric adaptation and musical fit, keeping author, implementation, rhyme, metre, pronunciation, and meaning-loss findings. A generator's favored prompt language cannot replace approved lyrics.

Each exact music profile separately proves description understanding, lyric rendering, pronunciation, structure tags, mixed-language behavior, and instrumental mode. Neither Altar locale nor Persona language selects these fields. Optimized lyrics are another authored candidate.

Singing, rap, and musical spoken word remain here. [Language Edition](../language-edition/) owns ordinary dialogue, narration, spoken replacement, captions, and timed editions. A translated song keeps Riffmaw's lyric/performance revisions while the edition keeps source alignment, captions, fit, and packaging; exact words, timing, performance, and findings cross the seam.

## Answer and develop

An admitted jam may request accompaniment, counterpoint, percussion, harmony, texture, effects, or transitions from a recent performance window, submix, MIDI, cue, or FeelProfile. Preserve both scheduled and actual entrances. The request chooses an honest latency class:

| Class | Contract |
| --- | --- |
| **Inline DSP** | Bounded processing inside a proved realtime-safe host; no model or control-plane wait enters the audio callback. |
| **Streaming player** | A model emits playable increments under a measured buffering and deadline contract. |
| **Scheduled player** | Riffmaw prepares a phrase, bar, or section ahead and fences its future entrance against the mapped musical clock. |
| **Offline producer** | No live deadline; generation and revision occur only after the captured session is frozen. |

Phrase- or bar-ahead scheduling is **near-live**. Symbolic MIDI into a deterministic synth is the first proposed Linux road before any claim of sample-continuous generated audio. After capture closes, frozen artifacts may enter slower comping, tempo-map editing, bounded repair, extension, supporting layers, arrangement, or mix. Returning to performance requires a newly armed jam.

## Production autonomy

The request pins its permitted finish:

| Finish policy | Riffmaw may do | Required return |
| --- | --- | --- |
| **`assets_only`** | Generate, capture, separate, clean, align, label, and package reusable musical material. | Dry and processed assets, stems where available, observations, and lineage; no implied mix approval. |
| **`assisted_session`** | Also arrange, route, automate, process, and render one or more proposed mixes. | Editable production plan and session state, stems, candidate mixes, findings, and unresolved choices. |
| **`autonomous_master_candidate`** | Also select bounded candidates, repair failed regions, mix, master, run deterministic gates, and repeat within budget. | A master candidate satisfying its automated gates, stems and receipts, or the exact criteria and budget that prevented completion; Magus acceptance remains separate. |

Before the loop, declare candidate count, wall time, compute, paid cost, similarity risk, loudness, repair attempts, and stopping policy. A planner can direct admitted generators, analyzers, editors, renderers, effects, and mastering tools, using deterministic probes and bounded listening judgments for the next revision. Budget exhaustion returns permitted attributable candidates/findings, never a relabeled master.

These policies cannot arm capture, authorize payment/Portal egress, admit a plug-in, export, accept, or publish. A failed binding settles before an exact predeclared branch or new Invocation tries another road; the Resolution Lock never changes mid-casting.

## Edit, mix, master

Comping, timing, tuning, cleanup, resampling, and destructive processing retain parent revisions. The mix records routing, gain, pan, automation, effects, spatial relation, and balance among instrumental, vocal, sampled, and processed elements. Stems export those relationships rather than become independent masters.

Mastering binds loudness, peak, dynamics, sample rate, format, and sequencing targets. Score/MIDI where present, edits/session lineage, stems, mix, and master stay attributable. Probes establish measurable fit; listening review decides musical fit. Generation, DAW export, and plug-in renders have separate effects; lost acknowledgement remains **unknown** until provider/session/destination reconciliation. Failed profiles, similarity uncertainty, stale inputs, or exhausted repair return findings/refusal.

Compound-model music must have originated under a `VideoJob@2` whose `MediaFacetAuthoritySet@1` predeclared `music`, `riffmaw.music` revision `2`, and exact request digest. After Prism technical settlement, Riffmaw issues `SemanticFacetAdmissionReceipt@1` over music/compound digests, use, rights, evidence, findings, and disposition. Labels, demux, and undeclared sound cannot supply musical acceptance.

[Package](package.md) seals accepted work. [Sync](sync.md) exposes exact musical events to another craft.
