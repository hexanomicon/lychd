---
title: Robotic Dance
icon: material/human-handsup
---

# :material-human-handsup: Robotic Dance

Put on motion trackers, step into the admitted dance space, and lead a group of physical
familiars with your own body. Each robot adapts the movement to its proportions and capabilities.
Candidate modes are **Mirror** (follow together), **Echo** (a deliberate time offset), and
**Ensemble** (declared variations for different bodies).

This is a **candidate Familiar use case**, with research checked on **2026-09-17**. It suggests a
dance Pattern and exact body/controller profiles; it adds no published Pattern or supported
hardware to the [Familiar contract](index.md#contract). [State of Work](../../state-of-the-work.md#composition-portfolio-delivery)
keeps the shared delivery boundary.

## How it could fit

```text
armed wearable / optical mocap source
→ calibrated human motion with timestamps
→ Live Kinesis retargeting for each exact robot rig
→ separately admitted local tracking controller
→ Familiar mission observations, effects, and settlement
```

[Live Kinesis](../../sepulcher/extensions/prism/live-kinesis.md) is the proposed seam for source
epochs, clocks, retargeting, gaps, and expiring motion segments. A pinned GMR adapter is one
candidate for its technical mapping. Familiar would bind each `FamiliarBody@3` to a finite dance
mission, the designated consenting performer, dance mode, space, duration, and stop policy.
The [body's controller](embodiment.md#the-body-decides-what-fits) retains balance, contacts, joint
limits, collision response, and fast actuation; an LLM can select an admitted mode or request a
stop while this local loop runs independently.

Each robot needs its own mapping and physical admission. Shared source timing would support
group synchronization, with an explicit policy for one member dropping out. Intentional Echo
delay must remain distinguishable from stale tracking. Lost tracking, changed calibration, or
an expired segment invokes the commissioned local response; reconnect requires fresh admission.
The result records the performed intervals, deviations, stopped members, and any unknown effects.
Capture, recording, and reuse of the performer's motion remain separate consent choices.

## Research and existing demonstrations

These are integration leads, with different evidence boundaries:

| Reference | What it contributes |
| --- | --- |
| [TWIST](https://arxiv.org/abs/2505.02833) and [TWIST2](https://yanjieze.com/projects/TWIST2/) | Whole-body human-to-humanoid teleoperation. TWIST2 uses a PICO 4 Ultra and two PICO Motion Trackers, making it a concrete wearable-input reference for a Unitree G1 profile. |
| [GMR — General Motion Retargeting](https://github.com/YanjieZe/GMR) | Maps human motion onto different humanoid bodies and supports live teleoperation. A candidate retargeting component; mapping a pose does not establish balance or successful physical execution. |
| [ASAP](https://agile.human2humanoid.com/) | Demonstrates learned agile skills, including APT Dance, on a real G1. Useful for controller training and a rehearsed-clip route; it does not establish live imitation of an arbitrary dancer. |
| [CHINGMU × Unitree, WRC 2026](https://en.chingmu.com/case/10801.html) | The vendor's September 3 report describes a dancer's captured movement driving a humanoid synchronously. A direct demonstration of the intended experience, without an independently verified latency or general compatibility claim. |

Selecting a profile would still require its exact capture interface, robot/controller revision,
measured timing, and code, weights, body-model, and data-use terms. None of these references is
an installed LychD dependency.

## First bounded probe

Start with one recorded performer trace and two simulated bodies with different mappings.
Exercise Mirror and Echo, then inject stale frames, calibration changes, one-body refusal, and
an operator stop. Check timing and per-body partial settlement before attempting a separately
commissioned single-robot live trial. Ensemble variations can follow; the fixture establishes
no physical safety or hardware compatibility.

Return to [Familiar](index.md) or [Embodiment](embodiment.md).
