---
title: Music
icon: material/music-note-outline
---

# :material-music-note-outline: Music

Music owns the route from sonic intent to an accepted musical work. It can begin with a generated
sketch, a played take, MIDI, a score, a remembered moment, or an empty session. None of those
methods receives privileged authorship.

## Compose and arrange

`riffmaw.forge_track@1` pins the sonic brief, admitted sources, `FeelProfile@1`, target form,
budget, and acceptance criteria. AI music generation may propose motifs, harmony, rhythm, timbre,
sections, or complete candidates. Human performance, manual composition, procedural systems,
sampling, and DAW editing may answer or replace those proposals. Every generated or transformed
artifact keeps its provider or tool revision, control material, seed when available, input and
output digests, cost, and source influence.

A `FeelProfile@1` may begin as explicit direction or be revised from admitted, correctable
observations of a take or [jam](sessions.md#jam-in-shared-time). It can describe pocket, density,
attack, space, motion, instrumental relation, tension and release, and when the machine should
listen rather than answer. Each correction creates a linked immutable revision. It never converts
a model's guess about a performance into a fact about the performer.

The Magus selects and arranges the musical matter. Structure, tempo map, meter, key or tuning,
instrumental roles, transitions, repetition, and controlled variation remain editable decisions.
Generated output is a candidate, not a finished track and not evidence that reuse is safe.

## Answer and develop

During an admitted jam, Riffmaw may generate or schedule accompaniment, counterpoint, percussion,
harmony, texture, effects, or transitions against the shared clock. A reply may use an exact recent
performance window, an accumulated submix, MIDI, an explicit cue, or the current `FeelProfile@1`.
The scheduled and actual entrance are both recorded so a musically useful late answer is not
misreported as realtime success.

The request declares one latency class rather than calling every machine reply realtime:

| Class | Contract |
| --- | --- |
| **Inline DSP** | Bounded processing inside a proved realtime-safe host; no model or control-plane wait enters the audio callback. |
| **Streaming player** | A model emits playable increments under a measured buffering and deadline contract. |
| **Scheduled player** | Riffmaw prepares a phrase, bar, or section ahead and fences its future entrance against the mapped musical clock. |
| **Offline producer** | No live deadline; generation and revision occur only after the captured session is frozen. |

Scheduled phrase- or bar-ahead accompaniment is **near-live**, not proof of sample-continuous
realtime generation. The first credible Linux path may schedule symbolic MIDI into a deterministic
synth before attempting generated audio inside the live deadline.

After capture closes, Riffmaw can develop the session without pretending the live moment remains
open: select or comp takes, infer an editable tempo map, repair a bounded passage, extend an idea,
generate supporting layers, arrange sections, and propose or execute a mix. Every step works from
frozen artifact and session revisions. Returning to live performance requires a newly armed jam.

## Production autonomy

The production request declares how far Riffmaw may finish on its own:

| Finish policy | Riffmaw may do | Required return |
| --- | --- | --- |
| **`assets_only`** | Generate, capture, separate, clean, align, label, and package reusable material. | Dry and processed assets, stems where available, observations, and lineage; no implied mix approval. |
| **`assisted_session`** | Also arrange, route, automate, process, and render one or more proposed mixes. | Editable production plan and session state, stems, candidate mixes, findings, and unresolved choices. |
| **`autonomous_master_candidate`** | Also select bounded candidates, repair failed regions, mix, master, run deterministic gates, and repeat within budget. | A master candidate satisfying its automated gates, stems and receipts, or the exact criteria and budget that prevented completion; Magus acceptance remains separate. |

Autonomy means Riffmaw can close the production loop, not that one model emits a finished song in
one shot. A planner can direct replaceable generators, analyzers, editors, renderers, effects, and
mastering tools; deterministic probes and bounded listening judgments feed the next revision.
Candidate count, wall time, compute, paid cost, similarity risk, loudness target, repair attempts,
and stopping policy are declared before the loop begins. Exhaustion returns the best attributable
candidates and findings when policy permits, never a quietly relabelled failure.

Each finish policy is a scope ceiling, not an authority grant. It never by itself arms capture,
authorizes payment or Portal egress, admits a plug-in, permits export, accepts a master, or publishes
the result. A failed bound implementation is replaced only by an exact predeclared branch in the
pinned Scroll or by a new forward Invocation after settlement; a casting never silently changes
its Resolution Lock.

## Edit, mix, master

Editing preserves its parents: comping, timing changes, tuning, cleanup, resampling, and destructive
processing each create an attributable revision. The mix owns routing, gain, pan, automation,
effects, spatial relation, and the balance between music, voice, and sound elements. A stem is an
export of those relationships, not an independent master.

Mastering targets declared loudness, peak, dynamic, sample-rate, format, and sequencing profiles.
The accepted output can include score or MIDI where present, session and edit lineage, stems, mix,
and master. Deterministic probes establish the measurable facts; listening review still decides
whether the work fits.

Paid generation, DAW export, and plug-in render are separate effects. Lost acknowledgement leaves
the result **unknown** until the provider, session, or destination is inspected. A failed profile,
unresolved similarity, stale source, or exhausted repair returns findings or refusal instead of a
quietly degraded master.

Music passes accepted assets and mix relationships to [Package](package.md), and exposes temporal
events through [Sync](sync.md) when another craft needs them.
