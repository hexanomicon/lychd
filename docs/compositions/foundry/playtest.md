---
title: Playtest
icon: material/controller-classic-outline
---

# :material-controller-classic-outline: Playtest

The candidate loads. Now make the player perform the declared interaction and inspect what the engine reports. `game.playtest_candidate@1` runs that bounded scenario against the exact build; screenshots support, but never replace, structured observations.

`PlaytestSession@1` owns the bounded live process. A trusted/Tomb driver may implement it directly; an independently resident, queued, or remote harness may expose `SessionGrant`. World keeps finite `EngineToolJob@1`. The scenario's `ControllerAdapter` exposes only admitted inputs, without shell, editor, debug console, arbitrary RPC, anti-cheat bypass, public-server access, or deceptive player authority.

## Pin the attempt

`GameplayScenario@1` binds build/world epoch, initial state, spawn/reset, random streams, ordered steps, inputs, structured observations, tick/clock policy, time/action budgets, assertions, tolerances, and terminal outcomes. A fresh session gets a new epoch unless process, world, cursor, and clock continuity are all proved. Epoch and cursor fence late observations.

`EngineObservationSet@1` retains exact tick/time, entity identities, transforms/velocities, collisions/triggers, navigation, controller/animation state, selected gameplay state, logs, performance, gaps, and assertions. Missing acknowledgement after an input requires reconciliation of the same epoch, cursor, and resulting state. Settle recovered, failed, cancelled, or indeterminate/contained; do not repeat an unproved effect.

## What the evidence can judge

Scenario author, controller, evaluator, and human player remain separate roles. Their evidence may establish loading, completed interaction, frame-time bounds, or regression. It cannot decide fun or release. `game.balance_from_evidence@1` proposes a bounded successor through ordinary project/build/playtest gates without revising old evidence.

A [Spectre](../spectre/index.md) Encounter is separately admitted participant, comfort, interruption, and exit work in a VR Habitat. It cannot substitute for candidate-build judgment.

Continue to [Build](build.md) when the scenario and checks support review.
