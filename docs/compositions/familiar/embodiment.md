---
title: Embodiment
icon: material/drone
---

# :material-drone: Embodiment

A phone, a wheeled body, and an airborne body cannot share one emergency action. Embodiment admits the exact capabilities and commissioned local behavior that make a particular body eligible for a bounded task. A form-factor name is only orientation.

## Body admission

`familiar.admit_body@3` returns immutable `FamiliarBody@3` after checking an already admitted controller/device attachment. Legion may own remote enrollment/reservation; a bounded local adapter may own another controller binding. For a phone, Ward first supplies the device/application `Principal`, revocable `Credential` and generation, current object-scoped `Authority Grant`, and policy generation. Companion needs no prior record: it opens its device/session only after Familiar supplies the body.

The body record pins:

- attachment owner, typed identity, revision/epoch, credential generation, fencing, and local/remote road;
- admitted form factor and exact make/model, hardware and controller revisions;
- requested, required, granted, missing, and revoked sensor/actuator capabilities;
- commissioned operating limits, relevant geofence, altitude/speed/battery/terrain limits where applicable;
- autonomous stop triggers, independently reachable manual override, form-specific stopped/contained state, and recovery policy.

Missing required capability refuses admission. Optional absence is a recorded downgrade. A changed hardware, firmware, attachment, or safety envelope creates a new body revision; no running mission wakes to a silently widened body.

## Example forms

These comparisons name the contracts a future profile must close, not tested builds, shopping recommendations, operating limits, or safety certification.

### Drone

An airborne profile must prove its exact flight-controller/companion-computer road, positioning, motion and altitude envelope, obstacle policy, battery/signal behavior, permitted geography, and locally executable recovery. Pixhawk-class, ArduPilot, PX4, and MAVLink are possible controller/mechanism references, not interchangeable or admitted implementations. The controller must distinguish actions that maintain controlled flight from disarm and other terminal actions; a generic immediate motor stop is no universal emergency policy.

### Rover

A wheeled/tracked profile must prove steering, braking/holding, slope/terrain, obstacle and water-crossing policy, local positioning, power, override, and loss recovery. ESP32, Arduino, or SBC examples grant no compatibility or Node Agent capability without an exact profile. The body's stop state must account for its actual mechanics and environment.

### Legged

A legged profile must close gait/posture, joint/load limits, falls, terrain/stairs, self-righting, local sensing, and recoverable stop behavior. Neither a ROS2 route nor a marketed robot name proves stair capability or that freezing its motors is safe.

### Manipulator, phone, card, and display

Locomotion is optional. A manipulator or personal presentation device still needs an exact capability snapshot, bounded effect vocabulary, local safety envelope, and reachable stop. A phone may host [Companion](../companion/index.md), while Familiar keeps its physical capability and stop truth. These forms inherit no vehicle or flight authority.

### Car and other vehicles

The vehicle profile retains occupants, route/motion envelope, controller, local override, and emergency policy. Familiar receives semantic tasks and attributed receipts without raw steering, throttle, brake, or actuator authority.

## Capability admission is honest

Capabilities must be proved by the attachment/profile rather than inferred from make or form. Positioning may use `gps`, `optical_flow`, `wheel_odometry`, or another admitted local reference. `obstacle_avoidance` and `lidar` require exact detection/control and failure evidence. `rgb_camera` or `thermal_camera` can support declared observation or subject designation, without proving identity or consent.

`microphone` permits only separately admitted Echo capture/transcription and authorized activation. `speaker` permits admitted playback, alerts, or Avatar voice presentation. Missing capabilities narrow eligible missions or produce the required refusal; another sensor is not a silent equivalent.

## One body, many missions

Every `FamiliarMission@3` pins the body revision. Broken or withdrawn capabilities remain visible; required ones block new missions and affect live work according to its stop/downgrade policy. An eligible body may host many finite missions without becoming an endless control session.

## The body decides what fits

The exact controller owns fast motion loops, actuation, and local safety interrupts. Familiar issues admitted semantic waypoint/task intents and receives receipts, never prompt-produced `motor_pwm=1400` or generic actuator commands.

Stop behavior must remain enforceable locally without a LychD round trip. On a Legion route the admitted node carries that responsibility; local/mobile attachments prove their equivalent. Link loss invokes the commissioned body-specific policy, not a universal hover, land, brake, disarm, or freeze instruction. Re-entry requires observed controller state and the profile's recovery admission.

Continue with [Follow](follow.md), or return to [Familiar](index.md).
