---
title: World
icon: material/earth
---

# :material-earth: World

World turns admitted design, source, assets, and motion into an engine-native place that can be
loaded, traversed, observed, and tested. Foundry owns level and gameplay meaning: scene hierarchy,
placements, collision, navigation, physics policy, animation controllers, interactions, actors,
streaming, and the exact engine derivatives that bind them. It does not regenerate source art,
declare a model's pixels to be physics, or acquire authority over a persistent external world.

This candidate study was reviewed on **2026-08-08**. It records a designed contract and first
engine profile—not a delivered Foundry Pattern, Godot adapter, Tomb, project store, or permission
to execute an untrusted game project.

## One inert assembly plan

`WorldAssemblyPlan@1` is the canonical, engine-neutral plan for one bounded playable world or
slice. It may be authored directly, compiled from a closed procedural recipe, or proposed by a
Mind; it is data rather than GDScript, Python, a Godot scene, shell, or authority to mutate a live
world.

| Facet | Required facts |
| --- | --- |
| **source frame** | exact design, project, asset-catalogue, Form assembly, Kinesis motion, and parent-world revisions |
| **space** | 2D or 3D coordinates, units, axes, origin, bounds, zones, layers, chunks, and streaming roles |
| **placements** | stable node or entity ids, exact artifact facets, transforms, variants, parentage, and instance bounds |
| **anchors** | player and actor spawns, cameras, entrances, exits, interactions, checkpoints, targets, and authored landmarks |
| **collision and physics** | body role, shapes, materials, layers, masks, joints, gravity zones, backend profile, and declared tolerances |
| **navigation** | agent profiles, walkable regions, links, avoidance policy, bake parameters, unreachable policy, and expected routes |
| **presentation** | lights, probes, audio zones, occlusion, ambience, level of detail, visibility, and performance budgets |
| **motion use** | exact clips, target rigs, controller states, transitions, blending, root-motion policy, and event bindings |
| **gameplay** | actors, components, interactions, triggers, state, win or stop predicates, and separately referenced source behavior |
| **procedure** | seed, closed generator revision, opened parameters, maximum counts, spatial envelope, and termination rule |
| **target** | `EngineProfile@1`, platform, quality profile, scenario set, and build acceptance criteria |

`game.assemble_world@1`, `game.bake_world@1`, and `game.validate_world@1` are proposed semantic
Spell contracts placed inside Foundry's principal Pattern. They are not independent Patterns,
Dispatcher capability families, or proof that an adapter exists.

The first compiler validates ids, references, bounds, cardinality, units, axes, placements,
collision and navigation declarations, resource ceilings, and target support before producing an
engine-native scene. Unsupported facets return `WorldFindingSet@1`; they are not silently omitted
or approximated. Successful compilation returns `WorldBakeReceipt@1` with source and result
digests, exact compiler and engine profile, coordinate transforms, generated collision,
navigation, lighting and LOD artifacts, warnings, validation, and declared loss.

An engine-native `.tscn`, `.scn`, resource database, imported cache, navmesh, lightmap, or shader
cache is a Foundry derivative. It never replaces the portable plan, source asset, Form assembly,
Kinesis clip, or producer lineage from which it was made.

## Godot is the first engine profile

[Godot](https://github.com/godotengine/godot) is the first native engine candidate: its engine is
MIT-licensed, its command line supports project import, headless execution and export, and its
scene, navigation and animation systems cover the first 2D and 3D proving slices. World owns the
finite tool boundary rather than exposing a generic engine shell:

| Contract | Office | Boundary |
| --- | --- | --- |
| `EngineToolJob@1` | finite inspect, import, assemble, bake, validate, test, or export operation | exact project root, operation, inputs, engine profile, limits, outputs, findings, cancellation, and receipt |

[Playtest](playtest.md) separately owns `PlaytestSession@1`; a finite world compile cannot be
extended indefinitely into an interactive process.

The first tool path needs no public network service. A Worker delivers one `EngineToolJob@1` into a
trusted executor or Tomb under a pinned ToolProfile. An optional wrapper becomes an Animator only
when independent residency, lifecycle, queue, or remote operation justifies a `JobGrant`; direct
Godot never becomes a fake Soulstone. A URL, editor remote-control port, debug console, generic RPC,
arbitrary CLI argument, or project script never becomes the stable LychD contract.

`EngineProfile@1` pins the engine build and binary digest; export-template digest; platform and
renderer; GPU, display and audio mode; physics backend, fixed tick, substeps and threading;
navigation bake settings per agent; importers and plug-ins with revisions and licenses; locale,
timezone and random streams; network policy; CPU, GPU, RAM, disk and wall-time bounds; and whether
the source is a trusted fixture or requires Tomb containment.

Headless means no interactive display; it does not mean sandboxed, deterministically rendered, or
audio-proved. Godot projects execute scripts and native extensions. Foreign projects, imported
plug-ins, editor scripts, shaders, resource references, archives, and generated source therefore
remain hostile. The first proof uses a trusted synthetic fixture. General project execution waits
for the [Tomb](../../adr/09-security.md#6-tomb-execution-contract) to prove filesystem,
process, device, network, secret, resource, cancellation, and residue containment.

Physics and navigation are reproducible only under the exact profile and asserted tolerances.
Foundry does not promise bit-identical simulation across engine, backend, architecture, renderer,
threading, or driver changes. A new profile creates new evidence.

## Portable sources and engine derivatives

LychD manifests retain semantics and provenance. [glTF/GLB](https://www.khronos.org/gltf/) is the
first portable 3D asset and assembly projection and passes the
[Khronos glTF Validator](https://github.com/KhronosGroup/glTF-Validator) before engine import.
Godot scene and resource forms are engine-native derivatives. OpenUSD/UsdSkel remains a later
studio-interchange profile rather than Core canonical truth. FBX remains optional lossy
compatibility and is never required for the FOSS route.

[Blender](https://www.blender.org/) remains a contained Form, Kinesis, or asset-preparation tool.
It may create or normalize a portable input and a validation preview; successfully opening a
Blender scene does not establish Godot import, collision, navigation, physics, gameplay, or
playability.

Asset-level operations such as texture import, mesh LOD, skeleton mapping, or one collider remain
in `AssetImportReceipt@1`. World-wide layer meaning, collision matrices, navigation joins, spawn,
streaming, gameplay binding, and controller use belong to `WorldBakeReceipt@1`. The compiler may
reuse an asset derivative without taking ownership of its source lineage.

## Procedural and model-assisted worlds

The first useful generator is a bounded compiler, not another large model:

```text
design and admitted catalogue
→ inert WorldAssemblyPlan@1 or closed procedural recipe
→ schema, reference, bounds, cardinality, and target validation
→ contained engine compiler
→ collision, navigation, presentation, and controller bake
→ static probes and declared gameplay scenario
→ candidate world revision
```

A Mind may propose placements, rules, constraints, a plan, or a reviewed project patch. It cannot
invent asset rights, open an unbounded catalogue, install a plug-in, execute generated source, or
claim playability from prose. Generated GDScript, C#, native code, shaders, or build configuration
is ordinary hostile project source and passes diff review, containment, engine tests, and
playtests. It is not smuggled through the closed recipe grammar.

Visual world models that emit video return pixels through Prism Video. Spatial generators return
candidate Form facets. Neither becomes an engine world merely by looking explorable. A
model-produced artifact enters Foundry only after it passes the same catalogue, compiler, bake,
scenario, license, and rights gates as authored material.

Actor behavior begins with deterministic state machines, behavior trees, navigation policies, and
fixture controllers stored in the project. A later `ActorPolicyProfile@1` may bind bounded
observations and actions to an eligible model capability, but it receives no engine console,
filesystem, scene mutation, network, or world authority. Its unavailable, late, malformed, and
unsafe-result policies are part of the build; an NPC cannot make the game irrecoverable because a
Portal or local model vanished.

## Playable evidence handoff

[Playtest](playtest.md) owns `GameplayScenario@1`, `PlaytestSession@1`, and
`EngineObservationSet@1`. [Build](build.md) owns the complete 2D and 3D proving fixtures and local
candidate bundle. World hands them one exact assembly plan, bake receipt, engine profile, and
finding set; it does not duplicate their scenario, observation, or fixture truth.

[Spectre](../spectre/index.md) may receive one exact world or scene revision, build digest, engine
profile, and relevant playtest evidence as candidate material for a `VRHabitat@1`. Spectre then
admits the runtime capabilities, reference-space policy, comfort, accessibility, retention, and
exit boundary required for VR. It does not absorb Foundry's project source, engine derivatives,
gameplay meaning, build judgment, or playtest verdict. A successful Foundry playtest does not by
itself admit a Habitat, and a Spectre Encounter does not rewrite whether the candidate build was
reproducible or playable.

## The neighboring worlds

[Shadow](../../sepulcher/extensions/shadow/) owns counterfactual branch lineage and promotion
requests; a game engine's simulated physics is not a Shadow branch. [Blockworld](../blockworld/)
owns bounded effects in an already persistent authoritative server world. Foundry owns the local
project candidate and can import a block grid or `.schem`, but a successful offline bake grants no
live placement authority. A later release or distribution application must freshly admit signing,
store credentials, upload, rollout, rollback, public players, and remote-copy receipts. Foundry
ends with the attributable local build candidate it can actually test.
