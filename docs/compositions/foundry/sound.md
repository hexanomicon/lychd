---
title: World Sound
icon: material/volume-high
---

# :material-volume-high: World Sound

A machine starts, loops while running, and stops when its game state changes. An ambience zone answers the listener's position. Foundry owns these **world sound** relations because their acceptance depends on exact interactive events, states, places, listeners, and runtime behavior.

## One bounded Pattern

`game.design_world_sound@1` begins with `WorldSoundBrief@1`, exact project source, `WorldAssemblyPlan@1`, event schema, `EngineProfile@1`, source/rights references, channel/spatial profile, resources, and acceptance. It returns `WorldSoundBundle@1`, `WorldSoundFindingSet@1`, or exact refusal, preserving the project derivative and bindings it made. A later build pins that source revision in a new Invocation; the Patterns never nest or silently resume one another.

Recording, synthesis, procedures, licensed samples, processing, and models can propose layers. Each retains source/derivative digests, author/performer, tool/provider, transforms, rights/consent, role, and loss. Codec or waveform resemblance cannot establish role.

## From cue to audible behavior

The cue map describes how the world should respond. A door can choose admitted variants; a machine has start/loop/stop; a zone crossfades by listener position. These relations still need to be installed and tried in the engine; the map itself is no rendered soundtrack.

`game.import_world_sound@1`, `game.bind_world_sound@1`, and `game.validate_world_sound@1` keep sound-specific records of import, binding, and observation. They do not widen generic asset, bake, or playtest schemas. Import success answers only the import question. Event, zone, loop, listener, priority, and failure behavior require their own evidence.

| Record | Required meaning |
| --- | --- |
| `WorldSoundBrief@1` | exact project/world/event frame, requested roles, listener and spatial policy, target engine/profile, source constraints, rights, budget, and acceptance line |
| `WorldSoundRevision@1` | immutable selected layers and edits with source lineage, variants, loop and transition facts, loudness and channel facts, and approval |
| `WorldSoundCueMap@1` | event and state ids, world regions, listener perspective, conditions, priorities, concurrency, randomization, start/stop/loop/crossfade, attenuation, occlusion, reverb-send, and timing relations |
| `WorldSoundBindingPlan@1` | exact world-plan digest plus proposed event, state, zone, listener, bus, and runtime mappings; inert data rather than engine code or mutation authority |
| `WorldSoundBundle@1` | accepted revisions, cue map, manifests, probes, findings, admission receipts, and exact target constraints |
| `WorldSoundImportReceipt@1` | source-to-engine asset conversion, importer/profile revision, bus and resource facts, outputs, checks, warnings, and declared loss |
| `WorldSoundBindingReceipt@1` | exact event, state, zone, listener, mixer-bus, and runtime binding installed into one world derivative |
| `WorldSoundObservationSet@1` | exact scenario tick/time, emitted cue and engine-event ids, listener zone, mixer state, gaps, and assertions |
| `WorldSoundFindingSet@1` | attributable unsupported role, stale source, rights, timing, spatial, import, binding, resource, or playtest evidence |

## Model-native sound fails closed

Pre-execution `MediaFacetAuthoritySet@1` must declare `world_sound`, `game.foundry` revision `4`, and exact `WorldSoundBrief@1` digest. After [Prism technical settlement](../../sepulcher/extensions/prism/video.md#admit-every-compound-facet), Foundry issues its independent `SemanticFacetAdmissionReceipt@1` over child/compound digests, use, rights, findings, and disposition. Other owners, demux, and provider labels cannot do this for it. Undeclared sound is quarantined/deleted, with no guessed event or library admission. Inseparable compounds need every required owner to accept the exact digest/use.

## Neighboring offices

[Riffmaw](../riffmaw/) owns music even when a game plays it. [Language Edition](../language-edition/) owns timed dialogue/narration/captions and Echo supplies speech operations. [Broadcast](../broadcast/sound.md) owns picture-bound sound; [Atelier](../atelier/) visual direction. Foundry binds admitted material to its game without rewriting it. External packs retain producer lineage; exporting a folder cannot create a universal sound-library Composition.

## Recovery and proof

A sound result depends on the world it was judged against. Changes to project source, world plan, event schema, listener/coordinates, target engine, timebase, rights, or brief make dependent cues/imports/bindings/builds/playtests stale. Preserve those dependencies so review can identify which work must return.

If a recorder, generator, importer, or engine loses an acknowledgement, keep the result `unknown` until the exact job, derivative, destination, and digest reconcile. A fallback requires a declared branch or forward Invocation. Cancellation alone cannot prove that capture, output, or mutation stopped; partial/mismatched material stays quarantined. On deletion, inventory derivatives/imports/bindings/builds/exports and retain an honest account of other custodians' copies.

The first network-disabled synthetic world has deterministic interaction sound, a start/loop/stop machine, ambience zone, listener transition, and bounded failure. Prove cue/event order, loop/crossfade bounds, buses/resources, rebuild/restart, `WorldSoundBindingReceipt@1`, and `WorldSoundObservationSet@1`. This is no proof of universal sound libraries, photoreal acoustics, public release, or another engine profile.
