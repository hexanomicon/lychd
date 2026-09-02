---
title: Embodiment
icon: material/drone
---

# :material-drone: Embodiment

A Familiar body is one physical form admitted for bounded real-world work. The form determines
what the body can sense, how it moves or presents, where it may go, and what must stop it.

## Body admission

`familiar.admit_body@2` pins one exact body identity from an admitted controller or device
attachment, closes the capability snapshot, and seals the safety contract. Admission is distinct
from attachment enrollment: Legion may own a remote node credential and reservation; a mobile
client/device enrollment owner may supply its exact binding while Ward proves current authority;
another bounded local adapter may own its exact controller binding. Familiar owns only the
application judgment that this physical body is fit for the declared work. Companion is
downstream: it may open its mobile device record and session only after Familiar returns the exact
admitted body revision.

| Field | What it binds |
| --- | --- |
| Controller/device attachment | exact owner, enrolled attachment identity, revision or epoch, credential generation, fencing, and local/remote route |
| Form factor | `car`, `drone`, `rover`, `legged`, `manipulator`, `card`, `display`, or another explicitly admitted form |
| Make and model | hardware identity for capability inference and safety defaults |
| Capability snapshot | requested, required, granted, missing, and revoked sensors and actuators |
| Safety envelope | geofence, altitude floor/ceiling, speed ceiling, battery floor, terrain allowlist |
| Emergency stop | autonomous triggers, manual override channel, stop behaviour per form |

Missing a required capability refuses admission. Missing an optional capability becomes an explicit
downgrade recorded on the body. A later hardware change creates a new body revision; it never
silently widens a running mission.

No attachment kind is universal Familiar law. Remote robots commonly need a Legionnaire so the
body can retain node-local safety and refusal across network loss. A phone represented through
an authenticated client can instead use its exact enrolled mobile attachment plus Ward's current
authority decision; Companion then consumes the resulting body record. Both paths must expose the
capabilities, fencing, recovery, and independently reachable stop behavior required by the
selected body profile.

## Example forms

These are orientation profiles, not compatibility, purchasing, regulatory, or safety guidance.
Each admitted body still needs an exact hardware/controller revision, measured envelope, local-law
closure, and an independently reachable stop path.

### Drone

A quadcopter or hexacopter. Airborne, fast, overhead perspective. Best for outdoor following,
aerial observation, and property survey.

| Typical build | 250–450 mm frame, 4S/6S LiPo, GPS, optical flow, downward rangefinder, forward obstacle-avoidance sensors |
| --- | --- |
| **Movement** | 3D waypoint navigation, hover-hold, altitude envelope, speed typically 2–10 m/s |
| **Sensors** | GPS/GLONASS, IMU (accelerometer + gyroscope + magnetometer), barometer, optical flow camera, forward-facing RGB camera, optional thermal, optional LIDAR |
| **Audio** | onboard mic (noisy — propeller wash), speaker or buzzer |
| **Endurance** | 15–40 minutes depending on payload and battery |
| **Safety envelope** | max altitude (regulatory + terrain), min altitude, geofence polygon, no-fly zones, kill-switch behaviour (immediate land vs. return-to-home) |
| **Emergency stop** | motor disarm + controlled descent or immediate cut; autonomous trigger on geofence breach, battery critical, signal loss timeout, or manual override |
| **Controller stack** | Pixhawk-class flight controller running one pinned ArduPilot or PX4 build; a separately admitted companion computer may connect over UART/MAVLink |
| **Legionnaire** | companion computer runs Node Agent; connects to LychD via Intercom; relays MAVLink telemetry and receives waypoint commands |

### Rover

A wheeled or tracked ground vehicle. Stable, quiet, longer endurance. Best for indoor/outdoor
following, close-range observation, and terrain the Lich walks.

| Typical build | 1/10 or 1/8 scale chassis, brushed/brushless motors, LIDAR or ultrasonic obstacle sensors, wheel encoders |
| --- | --- |
| **Movement** | 2D waypoint navigation, speed envelope, differential or Ackermann steering |
| **Sensors** | forward RGB camera, optional 360° camera array, microphone (quieter than drone), LIDAR or ultrasonic rangefinders, wheel odometry, optional GPS |
| **Audio** | onboard mic, speaker |
| **Endurance** | 1–6 hours depending on motors and battery |
| **Safety envelope** | geofence polygon, max speed, terrain allowlist (paved, grass, gravel, stairs-capable), water-crossing policy |
| **Emergency stop** | motor brake + hold position; autonomous trigger on geofence breach, obstacle at zero-range, signal loss timeout, or manual override |
| **Controller stack** | ESP32 or Arduino Mega with motor driver; optional Raspberry Pi 5 for vision |
| **Legionnaire** | ESP32 may run Node Agent directly for simple missions; companion SBC for vision-heavy missions |

### Legged

A quadruped or hexapod robot. Can handle stairs, uneven terrain, and indoor spaces a rover cannot.
Best for indoor following, multi-floor environments, and close physical presence.

| Typical build | open-source quadruped (Stanford Pupper, Petoi Bittle, Mini Pupper), 8–12 DOF |
| --- | --- |
| **Movement** | gait-based navigation, stair climbing, step-over obstacles, posture control |
| **Sensors** | forward RGB camera, IMU, joint encoders, foot contact sensors, optional LIDAR |
| **Audio** | onboard mic, speaker |
| **Endurance** | 20–60 minutes depending on gait and payload |
| **Safety envelope** | geofence, stair policy (allowed/refused), max gait speed, terrain allowlist, self-righting policy |
| **Emergency stop** | freeze posture + hold; autonomous trigger on fall, joint overload, geofence breach, signal loss timeout, or manual override |
| **Controller stack** | Raspberry Pi 5 or Jetson with ROS2; servo driver board |
| **Legionnaire** | same SBC runs Node Agent alongside controller |

### Manipulator, phone, card, and display

A Familiar need not locomote. A robotic hand, phone, tactile device, card, or display can be
admitted as a physical presentation or effect body when its controller or client exposes an exact
capability snapshot, local safety envelope, bounded effect vocabulary, and physical stop path. A
phone may carry a [Companion](../companion/index.md) session while Familiar retains its body and
hardware facts. Such a body does not inherit drone, vehicle, or locomotion authority merely because
it shares the Familiar identity.

### Car and other vehicles

A car or other vehicle is admitted as a vehicle body with its own controller, occupants, motion
envelope, route boundary, local override, and emergency policy. Familiar receives semantic vehicle
tasks and attributed receipts; it does not receive raw steering, throttle, brake, or actuator
authority.

## Capability admission is honest

A capability declared "required" refuses body admission when the hardware or controller cannot
supply it. A capability declared "optional" becomes an explicit downgrade recorded on
`FamiliarBody@2`. Familiar never infers capabilities from a form-factor label alone.

| Capability | What it enables | Absence means |
| --- | --- | --- |
| `gps` | outdoor waypoint navigation, return-to-home, geofence enforcement with global coordinates | indoor-only or relative-position missions |
| `optical_flow` | hover-hold without GPS, indoor position holding | drift-prone hover, refused for indoor drones |
| `obstacle_avoidance` | autonomous path deviation around detected obstacles | stop-on-obstacle only; mission may require manual clearance |
| `rgb_camera` | visual subject lock and separately admitted Prism/Sight observations or visual source material | follow by beacon/GPS only; no visual observation or image-derived grounding |
| `thermal_camera` | subject lock by heat signature, thermal observation | visible-spectrum-only subject designation |
| `microphone` | separately admitted Echo capture/transcription and an authorized activation event | no audio capture; microphone-dependent speaking mode unavailable |
| `speaker` | Echo delivery, authorized Avatar voice projection, audible alerts, and disclosure announcements | silent body; Avatar projection limited to display or motion |
| `lidar` | precise obstacle mapping, SLAM, 3D observation | coarser obstacle detection via ultrasonic or vision |
| `wheel_odometry` (rover or vehicle) | dead-reckoning position between GPS fixes | position drift without external reference; other forms use their own admitted local reference |

## One body, many missions

A `FamiliarBody@2` may admit many `FamiliarMission@2` records. Changing the hardware, controller
firmware, or safety envelope creates a new body revision. A mission always references an exact
immutable body revision; it never wakes to find its body silently upgraded underneath it.

A body that loses a capability between revisions — a broken camera, a downgraded controller —
records that loss. Missions that required the lost capability refuse admission. Missions that
declared it optional may proceed with the downgrade explicit.

## The body decides what fits

Familiar receives no raw motor authority. The controller — Pixhawk, ESP32, ROS2 node — remains
the sole authority over motor PWMs, PID loops, and obstacle avoidance interrupts. Familiar sends
semantic waypoints and receives attributed receipts; it never sends `motor_pwm=1400`.

The emergency stop is hardware-level and autonomous. Familiar declares the stop policy
(kill-switch behaviour, autonomous triggers) at body admission. The controller enforces it
without waiting for a LychD round-trip. A lost admitted control link—Intercom on a Legion-backed
route—triggers the signal-loss policy, not an unbounded hover.

Continue with [Follow](follow.md) for how the body locks onto a subject, traces a path, avoids
obstacles, handles signal loss, and transitions into speaking presence. Return to
[Familiar](index.md).
