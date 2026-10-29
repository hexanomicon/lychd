---
title: Playing with a companion
icon: material/account-voice
---

# Playing with a companion

**Unofficial Minecraft integration. Neither Mojang nor Microsoft approves or is associated with this project.**

Publisher: LychD contributors · Contact: [hexanomicon@proton.me](mailto:hexanomicon@proton.me).

You start a world, ask the companion to follow, and begin a small building project together.
You should spend your attention on the world: know when the companion heard you, understand
what it can do, and interrupt it without navigating a technical console. A companion earns trust
by being useful, quiet when appropriate, and precise about work it did not finish.

These user stories and acceptance trials guide the experimental
[Horizon-assist profile](horizon-assist.md). They are targets, not a feature announcement.
[State of Work](../../state-of-the-work.md#composition-portfolio-delivery) owns delivery;
the [managed mission](mission.md) retains its separate authority and receipt contract.

## The first fifteen minutes

1. **Prepare:** inspect the selected microphone, models, disposable world and separate bot
   identity. Show what is ready and what needs attention before recording. A muted input is a
   useful diagnosis, not a reason to change the person's audio settings silently.
2. **Speak:** record one short Slovak, Czech or English utterance. A visible indicator says when
   capture is active. A text view and concise response make misunderstood words recoverable.
3. **Observe:** ask for state, then ask the companion to wait. It remains still and quiet while
   bounded observations continue. Its presence must not turn into a stream of repeated speech.
4. **Follow:** bind the exact human client, stand still, then walk a few blocks. Check personal
   distance, bounded movement, target loss and keyboard stop before attempting a longer walk.
5. **Build:** inspect one exact plank cell, supply materials, then try three cells. Compare the
   world, inventory and retained outcomes. Stop during a step and inspect any partial result.
6. **Leave:** stop the controller before leaving the world. A new session rechecks client and
   world identity and offers reconciliation; it never silently repeats an uncertain action.

The first enjoyable slice is reliable short interaction, following and a tiny shared task.
A free-form house builder, background worker and persistent personality each need additional
contracts and trials. They do not follow automatically from connecting speech to a game command.

## User stories and acceptance trials

| ID | As a player, I want… | Observable acceptance and difficult ending | Execution path |
| --- | --- | --- | --- |
| BW-01 | one clear start, so setup does not consume the play session | Preflight names the selected input, model readiness and exact bot/target bindings. Missing model, muted input, loading client and quarantined generation each produce a useful next step. No recording starts during preflight. | Local preparation and admission; launcher operation remains separate from a game Run. |
| BW-02 | to speak Slovak, Czech or English naturally | A human recording in each language reaches the intended closed command. A different accent, short word, noise and numbers are included in the trial. Unsupported wording refuses; no confidence score or detected language is invented. | Echo interpretation, then the same bounded command parser. General paraphrase understanding needs a separately evaluated resolver. |
| BW-03 | to understand what the companion accepted | Show a concise result in the selected reply language. Distinguish instruction received, behavior started, client-reported outcome, refusal and unknown effect. Starting a build must never announce that the house is finished. | Deterministic presentation of retained results; no planning model is needed. |
| BW-04 | to correct an ambiguous instruction without accidental work | “Build a house here” cannot become guessed coordinates or a control string. Explain the supported next step. A later resolver may ask one precise clarification and bind its answer to the exact draft; it still needs ordinary action admission. | Current strict refusal; a future typed intent/clarification draft precedes the action Graph. |
| BW-05 | to keep playing while the companion follows at a comfortable distance | A stationary target causes no movement. Small motion inside the deadband does not produce jitter; longer motion produces finite segments. A lost, distant or stale target stops following. Pathfinding without measured progress stops the task; missing post-observation reports movement unverified. | Separate finite follow ticks, exact-person observer and supervisor. Post-observation compares with the final pre-command pose and the original target sample; a 0.05-block progress floor excludes negligible motion. |
| BW-06 | the companion to wait quietly when I am busy | Waiting grants no wandering, mining, inventory use or unsolicited conversation. Unchanged idle observations stay in private evidence without repeated console announcements or TTS. A meaningful state change can produce one concise notice. | Idle ticks with bounded cadence; presentation suppresses unchanged notices without discarding Run evidence. |
| BW-07 | stop and new instructions to take priority | Keyboard stop works during capture, inference, action and optional playback. New capture settles the prior background task before opening the microphone. The voice target observer joins an already started finite read and discards its cancelled sample; valid completion keeps that same bound feed usable for a fresh task. Actual read failure still retires it. Repeated cancellation must join owned work. Already placed blocks remain honestly recorded. | Existing synchronous fences, native cancellation and explicit control containment; speech-server work can remain unknown. |
| BW-08 | to hear useful replies without feeding them back into the microphone | Playback is explicitly selected and occurs after capture closes. Default operation retains a private WAV. Player failure preserves the game result and never repeats the action. Player exit is distinguished from human hearing. Stop retires the owned player process group. | Optional finite local playback after synthesis, outside the game action slot; no continuous listening or full-duplex claim. |
| BW-09 | a text fallback when speech is inconvenient | A future text entry uses the same typed intent, budgets, supervisor and outcome path. It does not simulate a transcript or acquire separate authority. Supported commands are discoverable while the game is focused. | The one-action text tool exists; an integrated in-game text/activation surface remains further work. |
| BW-10 | help with a precise small building task | Review one or three exact cells and the material. Require air, stone support, reach, selected ordinary planks and expected consumption. Each known cell outcome and native completion precedes the next cell. Changed conditions or an unknown result stop the plan. | Finite build steps and shared arbiter; stock client observations retain their concurrency limits. |
| BW-11 | to build a house together without rebuilding or destroying my work | Preview a finite blueprint, material list, plot and exclusions. Agree on phases and which person owns each area. Existing blocks are classified before admission; partial work is reconciled rather than counted as new work or demolished. Missing materials produce a useful handoff. | Future blueprint/phase admission and guarded placement; no mining, item spawning or demolition is implied by a request to build. |
| BW-12 | nearby danger and interruptions to produce predictable reactions | Health loss, death, loading, menus and world changes suspend dependent activity and explain why. “Help” does not silently authorize combat, destructive digging, teleportation or emergency administrator commands. | Bounded world observations fence dependent behavior. Any rescue or combat score needs explicit capabilities and its own acceptance. |
| BW-13 | the companion to remember our project when I return | Retain the admitted project, verified progress and unresolved outcomes with provenance. On reconnect, reconcile the new client/world generation before continuing. User preferences need their own reviewed retention boundary. | Future durable project/session continuity; process-local records do not establish memory admission or automatic restart. |
| BW-14 | control over privacy, voices and cost | Local mode remains usable without a paid account. Choosing a hosted provider explicitly binds destination, purpose, language, retention and spend. No quiet fallback sends a recording elsewhere. Voice style and verbosity are explicit preferences. | Existing local profile; hosted routing and paid adapters require separate implementation and admission. |
| BW-15 | the game to remain responsive | Measure frame behavior while speech and a finite task run together. Idle makes zero planning calls; follow does not accumulate stale ticks. Speech, game and logs expose separate costs. Reducing checks cannot weaken freshness or containment. | Deterministic selection, bounded cadence, deadband and shared budgets; resource allocation is measured on the exact host/profile. |
| BW-16 | a useful explanation after something goes wrong | Retain what was requested, which Run owned it, known/unknown outcome and a concrete next action. Offer a compact playtest summary with timings and refusal reasons. Never recommend replay merely because a reply or voice response was lost. | Private native events and stage timings; a session summary may aggregate these records without reading raw audio. |
| BW-17 | to agree on a useful task for otherwise idle time | “Finish these approved floor cells, then wait” binds the exact finite plan and terminal idle state. No pending task means no work. Danger, expiry or missing material interrupts the chore and reports the handoff rather than selecting a new goal. | Future explicit finite task selection, reusing admitted scores; idle itself still grants no effects. |
| BW-18 | help bringing materials without losing my supplies | Name the permitted source, destination, item and quantity. Show missing materials and account for every transfer. Do not raid another player's inventory, open an unrelated chest or start mining when a transfer fails. | Future typed inventory/transfer capability and receipts; today's inventory port is read-only. |
| BW-19 | the companion to know what it can actually observe | Correctly describe held material, health and queried terrain. Missing cells and unseen players stay unknown; old observations trigger a fresh read. Misleading names or chat cannot authorize work. After an action, compare a new observation with the intended change. | Future attributed perception and typed model proposal passage, followed by independent action admission; structured data and pixel vision are qualified separately. |

## Feedback and sound contract

Choose feedback from the actual result using the first presentation cut's fixed Slovak, Czech
and English wording. When idle/follow/build begins, say it was **started**. Completion needs its
own evidence. An ordinary command result remains a **client report**.

Make the next step clear when work cannot proceed. Refusal means no eligible action was admitted;
an unknown effect means work stopped and must not be replayed. Keep provider-private detail and
raw exceptions out of the spoken explanation while leaving full diagnostics privately accessible.

After the game result, settle optional speech separately. If synthesis or playback fails, keep
the game result and mark the speech stage failed. The failed reply cannot make an already
attempted game action safe to retry. Cancellation still propagates and settles owned work.
Generated audio and successful local player exit remain evidence about their own stages, not
proof that the person heard the reply.

An explicit playback option uses only validated bounded PCM bytes with a fixed local player
invocation. It accepts no shell command, arbitrary player option or voice-controlled device name.
Capture and playback do not overlap in this first half-duplex profile. Keyboard stop retires the
owned process group, including cancellation during player launch. No playback is launched during
setup or automated game qualification. Music ducking, positional audio, a global push-to-talk
key, overlays, wake words and conversational barge-in remain separate design work.

## Optimizing the experience

Optimize measured pain rather than the shortest isolated inference. Keep capture time separate
from STT, Graph/game response, TTS and optional playback; a fixed recording window can dominate
the perceived delay even when warm inference is fast. Record cold/warm conditions, utterance
length, language, model/runtime pins, CPU allocation and concurrent game load.
Wall time and process CPU are independent measurements: process CPU includes all threads and
can exceed wall time. Preserve both observations rather than clamping one to resemble the other.

| Trial | Acceptance target to evaluate; not a claimed service level |
| --- | --- |
| Quiet idle | Zero game effects and planning calls; no repeated unchanged notices. Native evidence and cancellation remain available. |
| Follow stability | No command while inside the deadband; finite command rate and no catch-up queue. Measure actual displacement, stop distance and missed/stale samples. |
| Turn responsiveness | Measure median and p95 after capture closes to first useful feedback, plus each stage. A first local trial aims for feedback within two seconds on warm simple commands; report failures rather than removing them from the sample. |
| Stop | Measure key event to fenced send, owned game stop and player/recorder retirement separately. The local fence should precede the first await; observed stop latency is not inferred from socket closure. |
| Recognition | Use human SK/CZ/EN commands, accents, silence, noise and deliberately ambiguous requests. Track correct intent, safe refusal and wrong admitted action separately. The playtest accepts zero wrong admitted actions. |
| Building | Compare intended cells, observed blocks, expected inventory delta and exact non-completion. Include target/support/material changes and cancellation before/after send and report. |
| Resource contention | Compare game frame behavior and process CPU/RSS with speech cold, warm and absent. Preloading trades memory for latency; a GPU model is not automatically better for a GPU game. |
| Model perception | Compare stated facts against the exact sample and measure reasoning latency separately. Missing, unloaded, stale and misleading inputs must not become assumed terrain, player identity or action authority. Keep idle and ordinary follow independent of model latency. |
| Recoverability | No automatic effect replay after lost replies, restart or speech failure. Retained evidence must identify the first unresolved boundary. |

The current engineering profile has no confidence-bearing STT contract. Do not optimize by
inventing a confidence threshold. Prefer an exact parser, bounded clarification, reviewed plan
and human command corpus. Selection of different models or paid services follows the separate
[speech research](../../sepulcher/extensions/echo-research.md) and an explicit provider trial.

## Order of preparation

| Priority | Player value | Gate before broadening the slice |
| --- | --- | --- |
| First session | BW-01/03/06/07/08/15/16: start clearly, understand outcomes, wait quietly and stop independently | Microphone and listening bake; truthful failure feedback; cancellation tests; measured warm/cold timing. |
| Shared walk | BW-02/04/05/09 plus the safety/privacy baseline in BW-12/14 | Exact separate target; human command corpus; live stationary/walking/target-loss trials; no wrong admitted action. |
| Shared build | BW-10, then BW-11 | Live one-cell/three-cell outcomes and interruption, controlled fixture, explicit blueprint/plot/material agreement before a house. |
| Longer relationship | BW-13/17/18 and any broader rescue, hosted voice or autonomous task | Durable reconciliation and separately admitted retention, inventory, provider or task capabilities; no implicit authority from elapsed idle time. |

First make short turns legible: readiness, correct language, useful outcome wording, quiet idle,
and optional interruptible playback. Then qualify the actual microphone and two-client follow
fixture, including stop and target loss. Establish one-cell and three-cell live building before
adding house blueprints or a planner. Only after those trials should background errands,
persistent project memory and broader autonomy acquire their own bounded scores.

Each added score specifies trigger, required observations, authority, budgets, finish evidence,
interruption, partial effects and reconciliation. World events can select an admitted response;
they never grant the companion new powers.
