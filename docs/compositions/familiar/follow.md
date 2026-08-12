---
title: Follow
icon: material/directions
---

# :material-directions: Follow

`familiar.follow@1` is the Pattern that wakes the body, locks a subject, traces a path through
physical space, and settles what happened. It may transition into speaking mode — mic and camera
activate, the Lich speaks through the body — and return to following when the conversation ends.

## Admission

Admission pins one exact `FamiliarBody@1` revision, subject designation, path constraints, and
stop conditions. A missing required body capability (camera for visual lock, GPS for outdoor
navigation) refuses the mission before the body moves.

| Field | What it binds |
| --- | --- |
| Body reference | exact immutable `FamiliarBody@1` revision with confirmed capability snapshot |
| Subject designation | one explicit lock method with fallback chain |
| Follow envelope | target distance (min/max), altitude floor/ceiling (drones), speed ceiling, terrain mode |
| Obstacle avoidance | stop, reroute, climb, or refuse per obstacle class |
| Signal-loss policy | hover-and-wait duration, land-in-place, return-to-home waypoint, or freeze |
| Speaking mode | activation trigger, mic gain, camera resolution, speaker volume, deactivation trigger |
| Budgets | max duration, max distance, battery floor for continuation vs. settlement |
| Stop conditions | subject lost beyond policy, geofence breach, battery critical, manual override, emergency stop |
| Optional Avatar binding | exact `ProjectionBinding@1` for Lich presentation through body speaker and display |

## Subject designation

The body must know _what_ to follow. The designation is explicit, attributable, and pinned at
admission. "Follow whoever is nearby" is not an admissible designation.

| Method | How it works | Failure mode |
| --- | --- | --- |
| **BLE / UWB beacon** | body locks signal strength + angle-of-arrival; subject carries a tag | signal lost in RF-noisy environments; tag battery death |
| **Visual signature** | AprilTag, ArUco marker, or known face embedding; body tracks with RGB camera | occlusion, lighting change, subject leaves frame |
| **GPS tag** | subject carries GPS broadcaster; body navigates to reported coordinates | GPS drift, urban canyon, indoor loss |
| **Thermal profile** | body locks heat signature with thermal camera | ambient temperature crossover, multi-person scenes |
| **Visual fallback** | color-blob tracker on a bright vest, or ML person-follower | false positives on similar colors/shapes |

A fallback chain is admissible: "lock BLE beacon, fall back to visual signature on AprilTag, fall
back to color-blob on orange vest." Each fallback transition records a `subject_lock_degraded`
event. When the chain is exhausted, the mission records `subject_lost` and executes signal-loss
policy.

Subject designation never proves identity, consent, attention, or relationship. A visual lock on
a face does not mean the person agreed to be followed.

## Path-tracing loop

The body runs one closed loop for the mission duration:

1. **Acquire** — read sensor inputs, compute subject position relative to body, record lock quality
2. **Plan** — compute path to maintain target distance envelope, avoid known obstacles, respect
   terrain constraints and geofence
3. **Move** — issue waypoint to controller; controller handles motor actuation and local obstacle
   avoidance; Familiar records waypoint receipt
4. **Observe** — re-acquire subject, validate lock quality, record any obstacle or deviation event
5. **Adjust** — correct path if subject moved, lock degraded, or obstacle appeared
6. **Check** — evaluate stop conditions, budgets, speaking-mode triggers

```
acquire → plan → move → observe → adjust → check → acquire …
```

The loop runs at the body's control rate (typically 5–20 Hz for drones, 1–10 Hz for rovers).
Between loop iterations the controller maintains the last commanded waypoint and enforces local
obstacle avoidance autonomously.

## Distance, altitude, and speed envelopes

The follow envelope keeps the body near enough to observe without crowding or endangering the
subject.

| Parameter | Drone | Rover | Legged |
| --- | --- | --- | --- |
| Min distance | 2 m (propeller safety) | 1 m | 0.5 m |
| Max distance | 15 m (visual lock range) | 10 m | 5 m |
| Altitude floor | 1.5 m above ground | — | — |
| Altitude ceiling | 15 m or regulatory limit | — | — |
| Max speed | 8 m/s | 3 m/s | 1.5 m/s |
| Terrain mode | outdoor-only (default), open-indoor (warehouse) | paved, grass, gravel, stairs-capable (rover-dependent) | indoor, stairs, uneven |

Envelope breaches record a deviation event. A sustained breach — subject sprinting beyond max
speed, drone forced below altitude floor by terrain — may trigger a stop condition.

## Obstacle avoidance

The body may encounter obstacles the subject passed but the body cannot. The avoidance mode is
declared per obstacle class at admission.

| Obstacle class | Stop | Reroute | Climb (drone) | Refuse mission |
| --- | --- | --- | --- | --- |
| Static object (tree, wall, furniture) | hover/brake, record, wait for subject to return or path to clear | plan alternate path around object, record deviation | ascend over object, record deviation | mission requires clear path; obstacle = `refused` |
| Dynamic object (person, animal, vehicle) | hover/brake, record, wait | reroute with wider margin | — | — |
| Narrow passage (doorway, gap) | stop, record width, wait for operator decision | — | — | body wider than passage = `refused` |
| Water (rover) | stop at edge, record | reroute around | — | water crossing not in terrain allowlist = `refused` |
| Stairs (rover without stairs capability) | stop at base, record | — | — | stairs in path + no stairs capability = `refused` |

The controller enforces obstacle avoidance at hardware level between waypoint updates. Familiar
records the event and the controller's response; it does not micro-manage the avoidance maneuver.

## Signal loss

The Intercom connection between the Legionnaire and LychD may drop. The body must decide what to
do without a round-trip to the Master.

| Policy | Behaviour | Recovery |
| --- | --- | --- |
| **Hover-and-wait** (drone) | hover at current position for N seconds; if signal returns, resume mission; if timeout, execute land-in-place | Master reconnects, reads body journal, resumes or settles |
| **Land-in-place** (drone) | descend vertically at current position, disarm motors, record landing receipt | body on ground, safe; manual retrieval |
| **Return-to-home** (drone) | ascend to safe altitude, navigate to pre-admitted home waypoint, land | body returns to known safe location |
| **Brake-and-wait** (rover/legged) | stop, hold position for N seconds; if signal returns, resume; if timeout, remain stopped | body stationary, safe; manual retrieval |
| **Freeze** (any) | immediate motor stop/brake, hold position indefinitely | safest option; requires manual intervention to resume |

The signal-loss policy is pinned at mission admission. The Legionnaire enforces it autonomously.
A late signal return after policy execution settles the mission with `signal_lost`; it does not
silently resume as though nothing happened.

## Speaking mode

The body transitions from following to conversational presence. The Lich speaks through the body's
speaker; the body's camera and microphone feed the Lich's senses.

### Activation

A trigger begins the speaking session. The trigger is declared at mission admission.

| Trigger | How it works |
| --- | --- |
| **Voice command** | body mic detects wake phrase ("Hey Lich"), streams to LychD, Riffmaw confirms, Familiar activates speaking mode |
| **Proximity** | subject enters close-distance threshold (≤ 1.5 m) and stops moving for N seconds |
| **Gesture** | subject faces body and raises hand (visual gesture detection via camera) |
| **Explicit instruction** | Lich decides to speak; Familiar receives command through Intercom |

### Active session

1. Body stabilizes — hover hold (drone), park (rover), stand (legged)
2. Camera activates — stream to LychD → Voidlight artifact → enters Lich Context as visual
   observation; may feed Avatar's visual grounding
3. Microphone activates — stream to LychD → Riffmaw artifact → speech transcription enters Lich
   Context
4. Lich voice projects through body speaker — audio out from LychD → Familiar → speaker
5. Body records a `FamiliarSpeakingSession` sub-record within the mission observation chronology — start time, audio artifact ref (Riffmaw), video artifact ref (Voidlight), transcript ref
6. Body indicators activate — camera LED, speaker announcement ("Lich is listening") for
   disclosure

### Deactivation

| Trigger | Behaviour |
| --- | --- |
| **Voice command** | "Goodbye" / "Resume follow" — Lich or subject ends session |
| **Subject departure** | subject leaves proximity threshold beyond grace period |
| **Explicit instruction** | Lich ends session through Intercom |
| **Budget exhaustion** | mission duration or speaking duration budget reached |
| **Stop condition** | any mission stop condition also ends speaking mode; session closes before mission settlement |

Deactivation closes the speaking session record, stops camera and mic streams, deactivates
disclosure indicators, and returns the body to the follow loop. If the follow mission itself is
complete, deactivation settles the mission.

## Terminal settlement

Every follow mission ends with one attributed judgment. A partial mission names exactly what was
completed and what stopped it.

| Settlement | Meaning |
| --- | --- |
| `completed` | subject reached declared destination, or mission duration budget expired with subject still locked; all segments have waypoint receipts |
| `partial` | some segments completed, some refused or interrupted; policy permits the exact settled subset; every absent or interrupted segment is named |
| `subject_lost` | subject designation chain exhausted and signal-loss policy executed; last known position, last lock quality, and loss event recorded |
| `emergency_stopped` | autonomous or manual emergency stop triggered; trigger source, body state at stop, and post-stop telemetry recorded |
| `signal_lost` | Intercom connection lost and signal-loss policy executed to completion; body journal available for later reconciliation |
| `battery_depleted` | battery reached declared floor; body executed low-battery behaviour (land/stop) before power loss; final position and remaining charge recorded |
| `refused` | mission admission failed (missing capability, infeasible path, geofence conflict, subject designation invalid) before movement began |
| `unresolved` | a required outcome remains unknown or cannot be reconciled without guessing; mission evidence is incomplete but honestly recorded |

## Representative journey

1. Magus admits one `FamiliarBody@1` — a 350 mm quadcopter with GPS, optical flow, forward RGB
   camera, downward rangefinder, mic, speaker. Safety envelope: max altitude 15 m, min altitude
   1.5 m, geofence = property boundary, emergency stop = kill switch + autonomous low-battery land.
2. Magus designates subject: BLE beacon in pocket, visual fallback to color-blob on bright vest.
   Signal-loss policy: hover 10 s, then land-in-place.
3. Magus opens `familiar.follow@1` mission: follow at 3 m distance, 3 m altitude, outdoor terrain,
   speaking mode on voice command "Hey Lich."
4. Drone lifts off, locks BLE beacon, begins path-tracing loop.
5. Drone follows Magus through garden — records waypoints, avoids tree branch (reroute event),
   re-acquires subject after brief visual occlusion (lock-degraded-then-reacquired event).
6. Magus stops at workbench, faces drone, says "Hey Lich, what do you think of these seedlings?"
7. Voice command triggers speaking mode. Drone stabilizes at hover, LED activates, speaker
   announces presence. Camera streams to Voidlight, mic streams to Riffmaw. Lich sees seedlings,
   hears question.
8. Lich responds through drone speaker: "The tomatoes are crowded — give them each a bigger pot.
   The basil is ready to harvest." Speaking session recorded with audio/video/transcript refs.
9. Magus says "Thanks, resume follow." Speaking mode deactivates. Drone re-acquires beacon,
   resumes follow loop.
10. Battery reaches 25% floor. Drone records `battery_low` event, descends to land at current
    position, settles mission as `partial` with battery-depleted reason. Magus retrieves drone.

Return to [Familiar](index.md) for the full contract and boundaries.
