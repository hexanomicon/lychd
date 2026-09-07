---
title: Follow
icon: material/directions
---

# :material-directions: Follow

A finite follow mission begins with an explicitly designated, consenting subject and a body proved fit for the task. It can track a path, pause for speaking presence, and report exactly where work stopped. `familiar.follow@3` owns that semantic journey while the local controller keeps the fast motion and safety loop.

## Admission

Pin `FamiliarBody@3`, its confirmed capability epoch, designation/fallback chain, path constraints, and stop conditions. The envelope includes target-distance limits, relevant altitude/speed/terrain limits, obstacle policy by class, signal-loss behavior, speaking triggers and media settings, duration/distance/battery budgets, and optional Avatar `ProjectionBinding@2`. Every physical value comes from the exact commissioned body/profile and applicable authority; this contract sets no universal safety distances or operating defaults.

Required capabilities—such as the admitted camera for visual lock or positioning method for a particular route—must be available before movement. Safety, geography, authority, or designation failure refuses admission.

## Representative journey

The synthetic fixture admits a mock body with simulated positioning, camera, microphone, speaker, battery, and locally proved stop behavior. A beacon and declared visual fallback identify the subject. Following a recorded outdoor path produces waypoint receipts; an obstacle and occlusion produce deviation/degraded-lock evidence.

At a workbench, the subject stops beside a tray of seedlings: “Hey Lich, what do you notice about these leaves?” The admitted activation requests a speaking window. Disclosure precedes separate Sight and Echo capture; their observations and transcript enter Context with uncertainty. An admitted response returns through Avatar/Echo/device receipts. The resume request closes capture before the follow loop continues. A simulated battery floor then triggers the declared local policy and settles the exact completed subset, with battery-depleted reason rather than invented destination success.

This proves workflow and receipt behavior, not drone dynamics, obstacle avoidance, hardware compatibility, plant diagnosis, or physical safety.
## Subject designation

The subject is explicit, attributable, and pinned. “Follow whoever is nearby” is inadmissible. A profile may use an admitted BLE/UWB beacon, GPS tag, AprilTag/ArUco marker, visual signature, thermal cue, or other bounded visual tracker. Each needs exact sensor, tracking, confidence, ambiguity, and loss behavior. A face embedding or similar cue proves no identity, attention, relationship, or consent.

A declared fallback chain can move from beacon to marker to a selected visual cue. Each transition records `subject_lock_degraded`; it cannot select an arbitrary nearby replacement. Occlusion, lighting, RF loss, tag battery, positioning drift, thermal ambiguity, and lookalike cues must remain visible. Exhausting the chain returns `subject_lost` and invokes the admitted containment/stop policy.

## Path-tracing loop

```text
acquire → plan → move → observe → adjust → check → acquire …
```

Acquire the designated subject and lock-quality evidence. Plan a bounded waypoint intent against distance, terrain, obstacles, and geofence. The controller admits and executes motion locally; Familiar records its receipt. Observe again, account for movement/obstacle/lock changes, and check budget, stops, and speaking triggers before the next intent.

The controller runs at its pinned measured rate. LychD declares no universal frequency and does not micromanage avoidance. Between semantic updates, the controller maintains or rejects the last admitted command under its local envelope.

## Distance, altitude, and speed envelopes

Admission must supply the exact body-specific limits and required sensing. A deviation records what crossed the envelope and how the controller responded. Sustained inability to maintain the target relation invokes the pinned stop policy; an appealing follow path cannot widen speed, clearance, geography, or authority.

## Obstacle avoidance

Static objects, moving people/animals/vehicles, narrow passages, water, and stairs require separately admitted responses. The profile may permit bounded stopping, rerouting, or another controller-proved maneuver; unsupported passages and terrain refuse. Controller observations and response receipts establish what happened. No general table can make an airborne climb, vehicle brake, or legged freeze safe for every body or situation.

## Signal loss

The attachment's bounded control link may disappear—Intercom for a Legion-backed route or the exact local/mobile equivalent. A body-specific policy defines the autonomous transition, deadline, contained/stopped state, and evidence/recovery path without waiting for LychD.

Candidate policy names such as hover-and-wait, land-in-place, return-to-home, brake-and-wait, or freeze are meaningful only inside a commissioned profile that proves their applicability. A label itself promises no physical safety. Reconnect reads the body journal, epoch, pending intent, and actual state before any continuation. Once the loss policy has executed, a late signal cannot silently resume the old mission: settle `signal_lost` and use explicit recovery admission.

## Speaking mode

A speaking window is a transition within the mission, not a second speech ledger. The trigger is declared at admission: an Echo Listener's exact activation phrase, authorized operator/application request, or an admitted proximity/gesture request. Proximity or visual resemblance cannot authorize capture, identity, or consent.

### Activation

First obtain the body's admitted stationary/contained presentation posture. Activate visible camera/microphone disclosure and any required audible announcement before separately admitted capture. Exact body policy determines whether this transition is possible; it never assumes a drone, rover, or legged body can use the same stabilization action.

### Active session

Open a separately admitted camera epoch for Prism/Sight source-bound observations and an Echo capture window whose transcript retains source, timing, provider, language assumptions, and uncertainty. Avatar may select an eligible presentation; Echo owns synthesis and playback chronology, while the device supplies physical delivery evidence.

Familiar records the bounded window's exact Companion controls when present, Prism/Echo epochs, transcript, disclosures, and receipts. It creates no duplicate `FamiliarSpeakingSession` chronology.

### Deactivation

An admitted goodbye/resume request, subject departure beyond grace, authorized instruction, exhausted speaking/mission budget, or mission stop closes the window. Stop camera/mic and settle their owner records before withdrawing indicators. Resume following only if the original mission's current admission and body policy permit it; otherwise settle the mission. A spoken request never acquires consequential effect authority by itself.

## Terminal settlement

| Result | Required account |
| --- | --- |
| `completed` | Declared destination reached, or the admitted duration finish reached with subject locked, and every completed segment has waypoint receipts. |
| `partial` | Policy permits the exact completed subset; refused, absent, or interrupted segments are named. |
| `subject_lost` | Designation chain exhausted; last position/quality, loss event, and admitted policy execution retained. |
| `emergency_stopped` | Autonomous/manual trigger, source, stopped body state, and post-stop telemetry retained. |
| `signal_lost` | Control-loss policy executed; journal remains available for reconciliation. |
| `battery_depleted` | Declared floor reached and body-specific low-battery behavior executed before power loss, with final position/charge evidence. |
| `refused` | Admission failed before movement: capability, route, geofence, designation, or other required condition. |
| `unresolved` | Required effect/result evidence remains unknown or unreconcilable. |

Return to [Familiar](index.md).
