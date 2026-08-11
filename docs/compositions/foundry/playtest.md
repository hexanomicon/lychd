---
title: Playtest
icon: material/controller-classic-outline
---

# :material-controller-classic-outline: Playtest

The proposed Spell `game.playtest_candidate@1` runs one declared scenario against an exact candidate. A constrained
controller acts within time, action, observation, and cost budgets; structured engine observations
take precedence over screenshots.

`PlaytestSession@1` is the Foundry-owned bounded live-process contract. A direct trusted/Tomb
process driver may implement it without becoming an Animator; an independently resident, queued,
or remote harness may instead expose an exact `SessionGrant`. World owns finite
`EngineToolJob@1`. A separate `ControllerAdapter` exposes only the input schema admitted by the
scenario. None supplies a generic shell, engine editor, debug console, arbitrary RPC, anti-cheat
bypass, public-server access, or authority to deceive players.

`GameplayScenario@1` pins the build and world epoch, initial state, spawn, reset, random streams,
ordered steps, permitted inputs, structured observations, tick and clock policy, time and action
budgets, assertions, tolerances, and terminal outcomes. Every session receives a new epoch unless
the exact engine process, world state, cursor, and clock continuity are proved. Late observations
are fenced by session epoch and scenario cursor.

`EngineObservationSet@1` records exact tick and time, entity ids, transforms and velocities,
collisions and triggers, navigation, controller and animation state, selected gameplay state,
logs, performance, gaps, and assertion results. A screenshot or fluent controller report cannot
replace those facts. If acknowledgement disappears after an input, the harness reconciles the
same session epoch, scenario cursor, and resulting state, then settles recovered, failed,
cancelled, or indeterminate/contained. An unproved effect is not repeated.

Scenario author, automated controller, evaluator, and human player are distinct roles. Evidence
may show that a level loads, an interaction completes, a frame-time bound holds, or a regression
appears. It cannot establish that the game is fun or that a release should occur.

A [Spectre](../spectre/index.md) Encounter is not a longer PlaytestSession. Foundry uses declared
scenarios to judge a candidate build; Spectre uses an admitted VR Habitat to keep participant,
comfort, interruption, and safe-exit truth for one bounded meeting or experience.

The proposed Spell `game.balance_from_evidence@1` may propose a bounded revision from attributed observations. The
change returns through ordinary project, build, and playtest gates; old evidence is never rewritten
to fit the new candidate.

Continue with [Build](build.md) when the declared scenario and checks have produced enough evidence
for review.
