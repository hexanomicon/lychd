---
title: Playtest
icon: material/controller-classic-outline
---

# :material-controller-classic-outline: Playtest

`game.playtest_candidate@1` runs one declared scenario against an exact candidate. A constrained
controller acts within time, action, observation, and cost budgets; structured engine observations
take precedence over screenshots.

An `EngineAdapter` exposes project, import, test, build, and observation operations. A separate
`ControllerAdapter` exposes bounded game inputs only. Neither supplies a generic shell, debug
console, anti-cheat bypass, public-server access, or authority to deceive players.

Scenario author, automated controller, evaluator, and human player are distinct roles. Evidence
may show that a level loads, an interaction completes, a frame-time bound holds, or a regression
appears. It cannot establish that the game is fun or that a release should occur.

`game.balance_from_evidence@1` may propose a bounded revision from attributed observations. The
change returns through ordinary project, build, and playtest gates; old evidence is never rewritten
to fit the new candidate.

Continue with [Build](build.md) when the declared scenario and checks have produced enough evidence
for review.
