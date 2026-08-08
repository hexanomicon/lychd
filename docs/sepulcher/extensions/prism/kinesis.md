---
title: Kinesis
icon: material/run-fast
---

# :material-run-fast: Kinesis

Prism's **Kinesis** faculty turns admitted performance, prompts, constraints, audio cues, and
existing clips into bounded, reusable motion. It may recover motion from finite video, generate or
complete curves, retarget them to an exact rig, clean technical faults, align them to exact cues,
or convert them into a declared portable projection. It does not thereby choreograph a scene,
approve a performance, alter sound, import an engine controller, drive an avatar or robot, or
publish anything.

This candidate study was reviewed on **2026-08-08**. It records a proposed contract, FOSS tool
base, license-gated model register, live-session boundary, and proving bake—not delivery,
automatic fallback, or permission to capture, generate, retarget, play, or publish motion.

## A pose is not an animation

The same visible movement crosses several owners without becoming one indistinct "motion" system:

```text
Sight pose observations
→ Kinesis motion recovery or generation
→ Kinesis retargeted technical clip
→ Voidlight creative review and accepted animation set
→ Foundry engine import, controller, compression, and playtest
```

[Sight](sight.md) owns estimates grounded to exact pixels and times. [Form](form.md) owns geometry,
skeleton hierarchy, rest and bind pose, skin weights, morph targets, and rig revision. Kinesis owns
structured change through time and its technical derivatives. [Voidlight
Motion](../../../compositions/voidlight/motion.md) owns choreography, direction, sequencing, and
acceptance. [Foundry](../../../compositions/foundry/assets.md) owns target-engine behavior.

A direct video-to-motion worker may perform detection and pose estimation internally; it need not
expose that private pipeline as separate Sight jobs. Its internal points become canonical
`VisualObservationSet@1` output only if the exact worker also satisfies Sight's provenance,
coordinates, uncertainty, and validation contract. Likewise, a video model may return convincing
moving pixels without returning one reusable joint, contact, or facial curve.

## One finite job, exact operation

There is no useful OpenAI-compatible protocol for skeletons, clocks, constraints, retarget maps,
contacts, or animation curves. The candidate `KinesisJob@1` therefore names one explicit
operation while its selected profile declares the source kinds, facets, controls, and limits it
has proved:

| Operation | Inputs | Required meaning |
| --- | --- | --- |
| `recover` | finite video, calibrated views, Sight observations, or admitted mocap | Infer declared body, hand, face, prop, root, or camera-relative motion while retaining coverage and uncertainty. |
| `generate` | text plus optional reference motion, constraints, paths, keyframes, or admitted audio cues | Produce new structured motion under an exact generation profile. |
| `retarget` | source motion and skeleton plus one exact target Form rig and `RigMap@1` | Create a target-rig derivative without pretending bone-name similarity is compatibility. |
| `clean` | admitted motion plus exact limits, gap, filter, IK, and contact policies | Repair declared technical defects while retaining before/after metrics and corrected regions. |
| `synchronize` | motion plus exact anchors, `ClockDomainMap@1`, or `SyncCueMap@1` | Create a retimed derivative; never edit or approve the source sound. |
| `convert` | admitted motion facets plus one output profile | Resample, transform coordinates, or create a portable projection with declared loss. |
| `validate` | motion, skeleton, target rig, or projection | Return attributable technical findings without creative acceptance or engine-playability claims. |

`compose`, `choreograph`, `direct`, `play`, `drive_avatar`, and `publish` are deliberately absent.
Those acts belong to a Composition or a separately authorized world effect, not a motion worker.

The request pins exact sources and temporal regions; operation and requested facets; source
skeleton and target Form rig digests; calibration; units, axes, coordinate spaces, and time
policies; constraints and anchors; purpose, classification, consent, retention, and likeness-use
boundary; immutable model or tool preset; seed policy; deadline; compute or Portal budget; and
idempotency key. Optional material never invents profile support.

`KinesisJob@1` owns motion stages, candidates, validation, and adoption. Each concrete service or
tool execution uses Core's Designed
[`ServiceJobAttempt@1`](../../../adr/14-workers.md#service-job-attempts-designed) state,
idempotency, cancellation, reconciliation, and indeterminate-effect law. An attempt remains
contained until the same provider/executor job identity and working set settle; cancellation
request is never proof that capture, inference, process, or remote effect stopped.

Decode, observe, solve, fit, generate, retarget, correct contacts, bake, validate, and export are
progress stages rather than lifecycle states. Partial or uncertain output enters quarantined
Reliquary custody. Only rehashed and validated artifacts are promoted. An uncertain paid, remote,
or local tool effect is reconciled by its exact provider/executor job identity rather than blindly
replayed.

## Motion is a typed asset set

Successful producing or transforming operations return `MotionAssetSet@1`; `validate` returns an
attributable `MotionFindingSet@1` bound to the exact inputs and validation profile. A motion asset
set is not a filename enum. It groups separately typed facets whose evidence and relations remain
explicit:

| Facet | Required facts |
| --- | --- |
| **clip manifest** | stable clip id and name, exact start and end, channel references, source-to-derived region, duration, loop intent, and positional and velocity seam tolerances |
| **skeletal curves** | exact skeleton revision, stable joint ids, local or world space, channels, key times, interpolation, and missing-channel policy |
| **root trajectory** | root-versus-pelvis semantics, translation and orientation, with explicit `preserve_world`, `extract_planar`, `in_place`, `target_warp`, or `none` policy |
| **transform tracks** | exact Form assembly nodes, cameras, or props being transformed |
| **hand motion** | left and right schema, joint coverage, visibility, gaps, and uncertainty |
| **facial and morph curves** | exact joint, blendshape, expression, or viseme ontology; neutral state, ranges, and target mapping |
| **contacts and events** | effector, object or ground reference, interval, point, normal, coordinate space, and uncertainty |
| **time relation** | rational timebase, exact sample times, source PTS, original-to-derived map, anchors, drift, resampling, and gaps |
| **coverage and uncertainty** | per-source and per-interval measured, estimated, generated, repaired, interpolated, occluded, or absent regions |
| **projections** | GLB, BVH, VRMA, USD, FBX, previews, sidecars, and exact validation or round-trip findings |

Every facet declares an evidence class such as `measured`, `recovered_estimate`, `generated`,
`deterministic_transform`, or `manual`. A monocular solve is not performer ground truth, a contact
hypothesis is not physical proof, and a generated dance is not an observation. Missing hands or
face channels never silently become zero motion.

[glTF 2.0](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) is the default portable
projection and may carry node translation, rotation, scale, and morph-weight animation. A GLB
cannot by itself preserve Kinesis's contact meaning, root policy, loop intent, source-time map,
uncertainty, consent, or provenance; the canonical manifest and receipt travel with it. BVH is
legacy skeletal-motion interchange and must retain its exact hierarchy, channel order, Euler
order, axes, scale, and source. VRM is a Form-owned avatar and rig projection; VRM 1.0 does not use
embedded glTF animations. The separate
[VRM Animation](https://github.com/vrm-c/vrm-specification/tree/master/specification/VRMC_vrm_animation-1.0)
format is a later Kinesis humanoid-motion projection.
[OpenUSD/UsdSkel](https://github.com/PixarAnimationStudios/OpenUSD) is a later studio profile whose
current TOST 1.0 license is pinned explicitly; a Blender round trip cannot be presumed to preserve
every layer, reference, or variant semantic. FBX is lossy input or output compatibility only. Its
original digest survives, Blender's
[animation-import limitations](https://docs.blender.org/manual/en/latest/addons/import_export/scene_fbx.html)
are part of the profile, and the EULA-governed Autodesk SDK is neither canonical nor a dependency
of the FOSS path.

## Rig and clock law

Kinesis consumes one exact Form deformation facet. That Form-owned facet exposes stable joint ids
and hierarchy; rest, bind, and inverse-bind transforms; local frames; handedness; up and forward
axes; units and scale; root and pelvis semantics; degrees of freedom and joint limits; effectors
and contact bones; mirror pairs; skin influences; and facial, expression, or viseme ontology where
present.

`RigMap@1` binds source and target skeleton digests, calibration pose, semantic mapping,
orientation offsets, scale and translation rules, twist and helper distribution, IK chains and
goals, unmapped joints, root and contact policy, facial mapping, and declared loss. Bone-name
equality or `humanoid=true` is not compatibility. A changed target rig stales the retargeted clip;
altering that rig creates a separate Form derivative.

A rational source timebase and exact timestamps survive every stage; `30 fps` alone is
insufficient. Variable-rate video, duplicate or dropped frames, audio drift, resampling, and gaps
remain explicit. Rotations pin coordinate frame and representation plus Euler order where used;
quaternions are normalized and checked for hemisphere continuity. Root motion is never silently
stripped, baked into the pelvis, or reintroduced. Metric scale requires calibration or an admitted
scale reference. Lip or facial timing points to the exact audio, transcript, or phoneme evidence
and preserves its uncertainty.

## Runtime and toolchain decision

Kinesis owns the job and artifact contracts, not a repository's Python API. Model repositories
enter as pinned worker profiles; tools enter as finite contained tool workers. Sharing a process,
container, Blender installation, or GPU with Form does not merge their semantics.

| Candidate | Office | Present judgment |
| --- | --- | --- |
| Prism Kinesis interface and reference adapter | Validate `KinesisJob@1`, resolve an exact profile, settle domain results and custody, and normalize `MotionAssetSet@1`. | Prism owns semantics and normalization; Core supplies demand/grant/attempt mechanics. No OpenAI-compatible or repository-shaped public API. |
| [Blender](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html) headless worker | Rig mapping, FK/IK, contact-aware correction, baking, GLB/BVH conversion, and validation previews. | First general tool worker. Blender is GPL; its [license guidance](https://developer.blender.org/docs/license/) says generated output is not automatically GPL, while distributed scripts and add-ons still require license closure. Pin build, scripts and environment; admission rejects or allowlists embedded code, add-ons, drivers, linked files, and Geometry Nodes before execution. |
| [Khronos glTF Validator](https://github.com/KhronosGroup/glTF-Validator) and [glTF Transform](https://github.com/donmccurdy/glTF-Transform) | Structural validation, channel inspection, explicit resampling and pruning of portable projections. | FOSS portable substrate. Optimization creates a measured derivative and cannot replace semantic Kinesis validation. |
| [Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync) | CPU generation of simple mouth-cue timelines from speech. | MIT low-resource fallback. Slovak must use its language-independent phonetic recognizer, which Rhubarb describes as generally less precise than PocketSphinx on supported English speech; output is `VisemeCueTrack`, not full 3D facial motion. |

Blender runs as a rootless isolated subprocess with job-local scratch, fixed mounts, read-only
scripts, no ambient home, host sockets, secrets, or network. Its pinned invocation includes
`--background`, `--disable-autoexec`, `--offline-mode`, and `--python-exit-code 1` plus one admitted
read-only script. Blender's
[production guidance](https://docs.blender.org/manual/en/dev/advanced/deploying_blender.html) warns
that offline mode cannot stop a third-party add-on from networking, so an OS network namespace is
mandatory. Those flags do not disable malicious linked material, Geometry Nodes, or add-ons;
admission rejects or explicitly allowlists them. Kinesis pins the Blender build, scripts,
permitted add-ons, backend, threading, flags, and environment, then claims reproducible intent only
where semantic validation agrees—not byte identity by default.

The first proving profile would use deterministic declared mapping, rest-pose orientation
correction and FK, with an optional IK pass for named effectors. Foot lock acts only over declared
or estimated contact intervals and reports the magnitude of every correction. Validate
joint-limit violations and bone-length constancy except for declared scale channels; end-effector
error; foot skate and floor penetration; root path and yaw; angular and discontinuity error; loop
pose and velocity seam; maximum and RMS cleanup correction; output timebase; and projection
validity. Exported and re-imported or decompressed projections are sampled against canonical
curves under pinned maximum and RMS translation and angular tolerances; structural glTF validation
alone cannot prove animation fidelity. Engine-native controllers, blending, target-engine
root-motion extraction and use, and animation compression remain Foundry concerns.

## First model profiles

The strict-FOSS first profile is the tool path above: admitted or authored motion, contained
Blender transforms, portable GLB plus manifest, independent validation, and optional Rhubarb mouth
cues. The strongest current learned candidates use custom open-model weight licenses, so they are
operator-eligible profiles rather than the strict-FOSS default:

| Profile | Intended office | License and placement judgment |
| --- | --- | --- |
| [GEM-X](https://github.com/NVlabs/GEM-X) | Finite monocular video to 77-joint SOMA whole-body, hand, face, trajectory, and camera-relative or world motion. | Apache-2.0 code and NVIDIA Open Model License weights: open-weight, not OSI-FOSS. Main published path is CUDA-centric; ONNX/TensorRT and Apple Silicon routes still require exact bakes. Output is SOMA motion, not an arbitrary target-rig clip. |
| [Kimodo SOMA-RP v1.1](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1) | Text, keyframe, end-effector, waypoint, and root-path conditioned skeletal generation. | 282M profile, Apache-2.0 code and NVIDIA Open Model License weights: open-weight, not OSI-FOSS. Published clips are 30 fps and at most ten seconds; the text encoder is the main memory cost and may be placed on CPU. Do not substitute its separately licensed SMPL-X profile. |
| [Audio2Face-3D](https://github.com/NVIDIA/Audio2Face-3D) | Prerecorded or later live speech to declared facial blendshape, joint, or vertex-motion profiles. | MIT SDK and Apache-2.0 training code with NVIDIA Open Model License weights. Promote each control schema independently. Audio2Emotion has separate terms and inferred affect never becomes evidence or source truth. |

[ARDY](https://github.com/nv-tlabs/ardy) is a promising later interactive text-and-constraint
profile, but its current CUDA path and gated Llama 3 text encoder make it a poor Core v1
dependency. Its code is Apache-2.0 and weights use the NVIDIA Open Model License, so the whole
profile is not strict OSI-FOSS.
[MotionBricks](https://github.com/NVlabs/GR00T-WholeBodyControl/tree/main/motionbricks) is a later
real-time interactive motion-synthesis and smart-primitives candidate with the same Apache-2.0
code and NVIDIA Open Model weight distinction.
[FreeMoCap](https://github.com/freemocap/freemocap) is a useful AGPL specialist capture connector
rather than the default Kinesis runtime.

No current music-to-dance or speech-to-whole-body model closes a sufficiently mature,
permissive, dependency-complete default. EDGE and DiffSHEG remain research challengers. MoMask,
MDM, MotionGPT, UniTalker, AnyTop, GEM-SMPL/GENMO, GVHMR, WHAM, and similar demonstrations may have
permissive-looking repository code while depending on SMPL, SMPL-X, MANO, FLAME, AMASS,
HumanML3D, BEAT, AIST++, Mixamo, Truebones, gated weights, or non-commercial data. Code, weights,
body model, datasets, dependencies, and output-use terms all close independently before a profile
can enter. A wrapper or converted checkpoint repairs none of them.

Until a champion closes that gate, music-conditioned work composes exact Riffmaw
`SyncCueMap@1` cues, authored or generated clips, Kimodo constraints where eligible, and declared
Kinesis editing. Riffmaw still owns the sound and Voidlight still decides the visible response.

## Live motion comes later

A camera, tracking endpoint, instrument, or microphone is not an infinite `KinesisJob`. The later
`LiveKinesisSession@1` consumes exact upstream epochs from `LiveSightSession@1`, Riffmaw
`PerformanceSession@1` and `ClockDomainMap@1`, or a separately armed mocap transport. It inherits
no camera, microphone, MIDI, avatar, robot, or world-effect authority.

The session pins participants; purpose and consent scopes; exact upstream session or admitted
transport references and epochs; calibration and target-rig revisions; requested channels; clock
maps and uncertainty; armed window; latency, cardinality, compute and cost bounds; bounded queue;
sampling, resampling, reorder, and drop policy; consumers; retention; and output-segment policy.
Every output binds the motion epoch, source cursor, target-rig digest, and deadline so consumers
can reject stale results. Calibration, sender, target-rig, or unproved reconnect changes rotate
the motion epoch. When an upstream source cannot pause, sampling and drops emit exact gaps and
watermarks rather than hidden latency or invented motion. Disconnect retains acknowledged
segments; only proved transport continuity may resume the same epoch, otherwise a newly armed
forward session is required.

[VMC](https://protocol.vmc.info/english.html) over
[OSC](https://opensoundcontrol.stanford.edu/spec-1_0.html) is a later admitted motion-transport or
output-projection profile, not Core law. Its first profile allowlists motion messages and rejects
file paths, configuration, MIDI/control, and passthrough messages unless separately authorized.
Kinesis may consume an admitted source transport or create the projection artifact; it does not
open or send to a target avatar endpoint. A separately authorized Foundry or avatar adapter owns
that effect. OSC and VMC provide neither application authentication nor guaranteed reliable
delivery. A profile binds an admitted sender and network zone, allowlists message addresses,
records receive time, reorder and drop facts, and rotates the epoch whenever sender or clock
continuity cannot be proved. [GStreamer](https://gstreamer.freedesktop.org/) may preserve media
clocks, PTS, gaps, reorders, and drops; its core is LGPL-2.1-or-later while plug-in and codec
licenses remain profile-specific. It is media substrate rather than a Kinesis runtime. Checkpoints
retain configuration, cursors, exact segment references, and gaps—not sockets, device handles,
tensors, or unbounded history. Stopping Kinesis proves neither that upstream capture stopped nor
that a downstream avatar stopped moving.

## Privacy, rights, and the proving bake

Body proportions, gait, hands, face curves, voice-conditioned facial motion, and even
skeleton-only derivatives may identify or reveal a performer. Their classification and purpose
follow every derivative after pixels or sound are discarded. Admission distinguishes capture,
realtime analysis, persistence, inference, Portal egress, retargeting or likeness use,
personalization or training, and publication. Consent for one is not consent for the others.

Face or gait recognition, cross-session re-identification, demographic, emotion, health, injury,
or intention inference is outside Kinesis. Source-side privacy masking remains capture or Sight
law; Kinesis cannot request an unmasked fallback. Revocation stops future admitted processing but
cannot claim that already exported copies disappeared. A generated or recovered clip carries no
authority to move an avatar, game entity, robot, vehicle, or physical effector.

Every receipt pins request and idempotency digest; input, intermediate, output, skeleton, rig, and
retarget-map digests; model code, weights, body-model, dataset, dependency, and output-use
licenses; runtime, container, Blender build, scripts, add-ons and flags; hardware, dtype, seed, and
resource peaks; axes, units, coordinate and clock maps; root, contact, IK, gap, filter, resample,
and projection policies; before/after metrics; warnings; uncertainty; performer and content
consent and use-rights receipt digests; and cancellation or recovery settlement.

The proving corpus covers authored, generated, monocular and calibrated capture; single and
multiple people; standard, unusual and nonhuman rigs; hands, face, props and partial coverage;
Slovak and multilingual prompts and speech; variable-rate video and drifting audio; occlusion,
dropped and duplicate frames; scale and floor ambiguity; contacts, fast turns, loops, root motion,
in-place variants, retarget maps, missing and extra bones, twist helpers, morph schemas; GLB and
BVH round trips; adversarial files and Blender scenes; cancellation, OOM, crash, restart, Stasis,
Portal reconciliation, live gaps, privacy, rights, and license closure.

Measure source-time fidelity, pose and trajectory error where ground truth exists, uncertainty
coverage, retarget and end-effector error, contacts, foot skate and penetration, joint limits,
continuity and loop seams, constraint adherence, lip synchronization, maximum repair magnitude,
semantic and projection validity, target-engine findings, latency, throughput, peak GPU and host
memory, queue behavior, cancellation, recovery, and custody. A beauty preview proves none of rig
compatibility, source fidelity, contact integrity, engine behavior, or creative acceptance.

## Profiles, Runes, Covens, and authority

Each model or tool profile pins exact operation, inputs, outputs, licenses, preprocessing,
coordinate and time semantics, limits, measurements, and validation. A Designed Rune declares one
resident/shared service with exact `[[capabilities]]` references, devices, mounts, lifecycle,
conflicts, and readiness. A finite Blender, glTF, or Rhubarb ToolProfile is selected by the Spell
Resolution Lock and delivered into a trusted executor or Tomb; it is not a fake Animator. A Coven
names compatible Soulstones that may rise together; it does not schedule a job, pool GPU memory,
evict a Mind, authorize a camera, or infer Portal fallback.

Kinesis may coexist with a Mind on one GPU and a generator on another, let its requesting Run enter
Stasis while Orchestrator transitions an incompatible workload, or use an explicitly admitted
Portal. Those are operator and Orchestrator placement choices proved by exact profiles, never
consequences of the abstract job. Kinesis owns
technical motion and its provenance. Voidlight owns what the movement should mean and which take
is accepted; Foundry owns how it runs in an engine; Broadcast owns its final audiovisual
placement; physical and game Compositions own every world effect.
