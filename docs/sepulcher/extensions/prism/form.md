---
title: Form
icon: material/cube-outline
---

# :material-cube-outline: Form

A photograph may suggest geometry, a capture set may support reconstruction, and an existing mesh
may need a new material, rig, or block projection. **Form** carries each requested operation to a
validated spatial result with its sources, representation, scale, and loss still visible.

Choose the operation first, then inspect the facets it must return. A useful preview cannot settle
those technical questions. Creative adoption, engine import, animation, and live-world placement
remain with the consuming owner.

This candidate study was reviewed on **2026-08-08**. The contracts and bakes below are Designed;
[State](../../../state-of-the-work.md#vision-admission) records the present visual boundary.

## One form job, explicit operation

There is no mature universal OpenAI-compatible 3D serving protocol to make the inner contract.
The candidate `FormJob@2` names one explicit operation while its selected profile declares the
inputs, output facets, controls, and limits it has actually proved:

| Operation | Inputs | Required meaning |
| --- | --- | --- |
| `generate` | prompt and optional image, multiview, depth, or layout references | Produce new spatial facets proved by the exact model profile. |
| `reconstruct` | admitted images, calibrated views, video frames, or point observations | Recover spatial facets while retaining cameras, source coverage, and uncertainty. |
| `texture` | geometry plus images, prompt, or material controls | Produce new appearance facets without claiming the geometry was regenerated. |
| `segment_parts` | image or geometry | Propose a structural part graph and separately addressable geometry. |
| `rig` | compatible geometry and optional skeleton or semantic controls | Produce deformation facets; no animation is implied. |
| `voxelize` | mesh, point cloud, volume, or scene | Apply an exact occupancy, sampling, scale, and optional palette policy to a bounded grid. |
| `block_generate` | biome, seed, mask, or admitted block context | Produce a block-native candidate without pretending it came from mesh voxelization. |
| `convert` | one admitted facet set | Create explicit derivative facets with declared loss and validation. |
| `render` | admitted form facets, camera, and render profile | Produce attributable image or video previews; a beauty render does not validate the source asset. |

The request must identify both the material and the spatial meaning to preserve. It carries
immutable input and control `ArtifactRef` values, original and derived prompts, the requested
operation and output facets, and units, axes, origin, scale, bounds, and coordinate transforms.
Seed policy, immutable preset, deadline, budget, and a closed engine-extension object bound the
execution. Optional material cannot invent support in the selected profile.

A text-to-image-to-form route is valid when both effects remain explicit. The generated image
is an attributable intermediate artifact, so the spatial result can still be traced through it;
it cannot disappear into hidden prompt machinery.

[Sight](sight.md) may supply masks, regions, pose, depth, flow, and camera estimates as exact input
facets. Form owns reconstruction and form generation; monocular relative depth is neither metric
geometry nor a reconstructed mesh.

`FormJob@2` owns spatial stages, candidate facets, technical validation, and result settlement.
Creative adoption and engine use belong to their consuming Compositions. Each concrete service or
tool execution uses Core's Designed
[`ServiceJobAttempt@1`](../../../adr/14-workers.md#service-job-attempts) state,
idempotency, cancellation, reconciliation, and indeterminate-effect law. The parent Run remains
nonterminal and fenced while the same attempt is indeterminate; neither job nor effect is replayed
under a new identity.

### Progress, cancellation, and return

Stages such as camera solve, generating or reconstructing, extracting, texturing, rigging, baking,
validating, and exporting are reported separately from numeric progress. Cancellation before GPU
admission, cooperative model cancellation, bounded worker termination, and tool-process
termination are different proved capabilities. A vanished worker does not prove that its effect
stopped or failed.

Keep unfinished material available for diagnosis without treating it as a result. Partial,
temporary, failed, or uncertain output enters quarantined Reliquary custody with its own digest
and working-set relation. Restart and reconciliation can inspect that material, but only validated
output enters the settled Prism Form result.

On reconnect, reconcile the exact provider job, request digest, working-set receipt, and returned
artifacts. Repeating an uncertain paid or remote effect would create a new event without settling
the old one, so no blind retry is permitted.

Every canonical receipt retains request digest and idempotency key; input, intermediate, and output
digests; model weights, runtime, container, graph, tool, add-on, and dependency revisions and
licenses; seed and exact configuration; dtype, quantization, offload and device topology; units,
axes, scale, transforms, camera uncertainty, and representation facts; timing, peak resources,
warnings, validation, cancellation settlement, and declared conversion loss. Provider paths,
Python objects, and embedded file metadata are evidence inputs, not canonical provenance.

## One asset set, typed facets

"3D" is not one flat output enum. `FormAssetSet@1` groups separately typed facets whose relations
remain explicit:

| Facet | Candidate forms | What it does not prove |
| --- | --- | --- |
| **geometry** | mesh, point cloud, voxel grid, or block grid | appearance, clean topology, physics, or portability to another renderer |
| **appearance** | PBR materials and texture artifacts with UV, color-space, channel, and sampler facts | geometry, source truth, or engine compatibility |
| **field/render representation** | 3D Gaussian splats or neural radiance field with cameras, bounds, renderer, and configuration | a clean mesh, separately editable appearance, physics, or renderer-independent portability |
| **structure** | semantic part graph with member geometry and transforms | joints, assembly constraints, or a usable rig |
| **deformation** | skeleton, skin weights, bind transforms, and rig profile | useful motion, retargeting quality, or animation rights; those technical derivatives belong to [Kinesis](kinesis.md) |
| **assembly** | `PortableSceneAssembly@1` with artifact references, transforms, hierarchy, cameras, lights, and declared constraints | an engine-native scene, collision, gameplay, or playability |
| **procedure** | inert `ProceduralFormRecipe@1` in a closed allowlisted grammar | executable Python, drivers, Geometry Nodes, shell, game commands, or authority to run an effect |

Canonical handoff normally uses a GLB/glTF container that may combine mesh, PBR appearance,
deformation, and animation facets when each is present. A Gaussian PLY or exact renderer package,
a NeRF checkpoint and configuration, and their camera sets remain field/render facets. They do not
impersonate point clouds or meshes merely because a viewer can render each of them.

A conversion creates another artifact whose losses must be named. Meshing a radiance field,
baking a Gaussian scene, reducing a textured mesh to blocks, retopologizing geometry, or converting
a rig can each discard different information. The receipt records that loss rather than allowing
the converted file to stand in for everything its source contained.

Reconstruction remains an inference from admitted captures. It can claim metric scale only with
supporting camera calibration or an admitted scale reference. Likewise, TRELLIS.2's internal
sparse voxels are not a Minecraft block grid; reaching that grid still requires an explicit
conversion.

## Hostile form custody

The Reliquary owns every source before Form materializes it. Admission bounds external URIs,
archive expansion, vertices, faces, nodes, scene depth, materials, texture pixels and channels,
animation channels, bones and influences, points, splats, voxels, training frames, parser memory,
GPU time, disk, and output expansion. Importers verify claimed media types and reject recursive or
unsupported content.

Scripts, drivers, expressions, add-ons, custom nodes, linked libraries, remote references, and
generated procedures remain inert unless a separate contained tool effect explicitly admits them.
Blender and ComfyUI workers run rootlessly without ambient home access, network access, auto-run
scripts, arbitrary plug-ins or nodes, and runtime downloads. A capture set additionally retains
consent, camera facts, and every source frame; rendering another view cannot launder the people,
places, or restricted material it depicts.

<span id="composition-boundaries-and-the-proving-bake"></span>

## Composition boundaries

Prism owns hostile-form handling, technical dispatch, transforms, facet semantics, conformance to
the declared Form profile, and effect provenance. An independent validator checks tool output
where the transforming tool cannot establish its own result.
[Atelier](../../../compositions/atelier/assets.md) owns creative acceptance, the brief,
candidate review, accepted form asset, and visual package. Foundry owns target-engine import and
validation, coordinate and material adaptation, collision, LOD, performance, engine-native scene
assembly, and playability. Blockworld owns live-world effect validation and bounded missions. A
Form output crossing any boundary is an exact artifact handoff, never shared authority.

An [Avatar](../../../compositions/avatar/index.md) profile may reference an exact Form asset, rig,
and morph ontology. Form still owns only that spatial material and its provenance; it does not
bind Persona, open an Avatar presence, admit a Spectre VR Habitat or Encounter, drive the
projection, or acquire world or body authority.

## Model workers, graph serving, and tool workers

Keep one Prism-owned Form interface while qualifying several immutable implementations behind
it. A research repository can supply a model without defining Core's protocol. If its worker
has resident, queued, or remote service behavior, it is an Animator reached through a `JobGrant`.
If execution is a finite model or tool operation, the Spell Resolution Lock selects it for a
trusted executor or Tomb. A pinned contained process needs no invented Soulstone, and two paths
that both emit GLB are not thereby interchangeable.

| Candidate | Office | Present judgment |
| --- | --- | --- |
| pinned Form model workers | Run one admitted generation, decomposition, rigging, reconstruction, or block-model profile behind `FormJob@2`. | Primary route. Each worker exposes only proved operations, accepts no ambient code or download, and settles output through custody. |
| [ComfyUI](../../animator/soulstone/engines/comfyui.md#pin-the-dialect-and-execution-lifecycle) | Graph route for multi-stage image-to-form, texture, preview, and future 3D nodes. | Advanced connector only. Admit immutable allowlisted graphs and pinned nodes; partner or cloud nodes are not proof of a local runtime. |
| [Blender](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html) | Headless UV, bake, material normalization, decimation or retopology, armature work, animation bake, GLB export, and validation renders. | Separate sandboxed tool process, never authority or deterministic truth. Pin build, add-ons, scene digest, command, environment, seeds where available, and output validation; prove semantic equivalence unless byte identity is explicitly claimed. |
| [trimesh](https://github.com/mikedh/trimesh), [Open3D](https://github.com/isl-org/Open3D), and [OpenVDB](https://www.openvdb.org/) | Geometry probing, bounds, topology checks, repair, registration, ray or signed-distance queries, voxelization, and sparse volumes. | Deterministic substrate only where the exact operation proves reproducible. NumPy or a bitset is enough for the 32-cubed fixture; OpenVDB is reserved for sparse volumes that justify it. |
| [COLMAP](https://colmap.github.io/), [Nerfstudio](https://docs.nerf.studio/), and [gsplat](https://github.com/nerfstudio-project/gsplat) | COLMAP supplies SfM/MVS and camera solving; Nerfstudio supplies reconstruction and training pipelines; gsplat supplies Gaussian rasterization and training machinery. | First composable reconstruction stack, not three equivalent video-to-3D engines. Retain camera calibration and pose uncertainty; the result stays a radiance or Gaussian form until a separately proved conversion creates another facet. |

OpenAI Images, OpenAI Videos, ordinary vLLM, and vLLM-Omni are not silently extended into 3D.
They may produce conditioning images or video through their own contracts, but Form owns the job,
facet semantics, custody, and recovery. Diffusers or a repository's Python demo is a model
integration substrate, not a durable multi-user job service by itself.

A Form graph must use only the preset and parameter openings admitted under the
[ComfyUI engine contract](../../animator/soulstone/engines/comfyui.md#keep-model-engine-and-road-apart).
Unapproved runtime downloads or remote nodes cannot fill gaps in a local profile.

## First model profiles

No current open stack reliably turns an arbitrary prompt or video into a finished, rigged, PBR,
engine-ready scene. The initial register deliberately composes narrower champions:

| Profile | Intended office | License and placement judgment |
| --- | --- | --- |
| [TRELLIS.2](https://github.com/microsoft/TRELLIS.2) | High-quality image-to-form mesh and GLB with PBR material channels. | MIT code and model candidate; Linux and NVIDIA GPU with at least 24 GB are the published floor. Close separately licensed dependencies such as `nvdiffrast` and `nvdiffrec`; published H100 speed is not a consumer-GPU promise. |
| [TRELLIS](https://github.com/microsoft/TRELLIS) | Direct text or image experiments and multiple spatial representations. | Models and most code are MIT candidates, while `diffoctreerast` and modified FlexiCubes retain separate licenses. Retain only an exact dependency-closed profile; family relation does not make it equivalent to TRELLIS.2. |
| [TripoSR](https://github.com/VAST-AI-Research/TripoSR) | Fast low-memory single-image reconstruction to mesh. | MIT code and weights and roughly 6 GB in its published path. First latency baseline, not a universal generator or PBR quality default. |
| [Step1X-3D Geometry](https://github.com/stepfun-ai/Step1X-3D) | Alternative 1.3B geometry profile. | Apache-2.0 candidate. Prove geometry alone and its handoff separately from the full published pipeline. |
| [Step1X-3D Texture](https://github.com/stepfun-ai/Step1X-3D) | Separate 3.5B geometry-to-appearance profile. | Apache-2.0 candidate with a published combined path around 27–29 GB. Texture presence is not automatically a common PBR contract. |
| [TripoSG](https://github.com/VAST-AI-Research/TripoSG) | High-fidelity shape-only geometry. | MIT candidate. It deliberately requires a separate appearance path. |
| [PartCrafter](https://github.com/wgsxm/PartCrafter) | Image-to-semantic, separately editable parts. | MIT core candidate. Its automatic BRIA background-removal path and optional Gemini route retain separate license and Portal gates; disable them unless independently admitted. |
| [SkinTokens](https://github.com/VAST-AI-Research/SkinTokens) | Unified compatible-mesh-to-skeleton-and-skin profile. | MIT research candidate with a published path at 14 GB or more. Promote only with topology-diverse deformation and export validation. |
| [UniRig](https://github.com/VAST-AI-Research/UniRig) | Separate two-stage skeleton and skinning predecessor. | MIT research candidate. Code and weight licenses do not settle training-source or produced-character rights. |
| [AniGen](https://github.com/VAST-AI-Research/AniGen) | Experimental image-to-rigged asset. | MIT core, but bundled `extensions/CUBVH` derives from `instant-ngp` under non-commercial/research-only terms. A commercial profile must prove that component is neither imported, built, nor executed and close every remaining dependency. |
| [MIDI-3D](https://github.com/VAST-AI-Research/MIDI-3D) | Experimental single-image-to-compositional multi-instance scene and GLB candidate. | Apache-2.0 code and weights candidate; textured generation needs instance segmentation and roughly 30 GB in its published path. It is not an engine-ready world. |

[Stable Fast 3D](https://github.com/Stability-AI/stable-fast-3d) remains a useful fast challenger,
but its Community License, registration, attribution, and revenue conditions keep it outside the
permissive default. [Hunyuan3D 2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) remains a
technical reference, not an eligible Bratislava deployment: its published community license does
not grant use in the European Union, United Kingdom, or South Korea. Eligibility is re-evaluated
from the pinned license before download and execution; neither a model wrapper nor a community
quantization repairs a withheld grant.

[DreamCubed](https://github.com/SakanaAI/DreamCubed) is an interesting Minecraft-native research
candidate for chunk generation, biome conditioning, inpainting, supersampling, and stitching. The
official DP4 and DP2 Hugging Face cards label those exact weights Apache-2.0, while CP2 currently
surfaces neither model-card text nor a license file. The two-commit code repository likewise
exposes no license file, and the dataset, block mappings, textures, dependencies, and resulting-use
terms are not closed. The whole route therefore remains license-blocked research rather than a
Core profile. Even after closure, model tokens must map to the canonical block palette and pass the
same validation and consumer admission as any other block source.

The first text-to-form quality route begins with [Image](image.md), then passes its admitted
image to the image-to-PBR TRELLIS.2 profile. Keep both effects, both prompts, and that intermediate
image in the lineage.

For an editable character, a candidate chain may retain the original unified shape, derive
optional semantic parts, choose compatible geometry for rigging, and run contained Blender
validation. Every handoff needs its own compatibility bake: disconnected parts or seams may
invalidate skinning, so their
outputs cannot be assumed compatible with SkinTokens or UniRig. Form then hands the exact
skeleton, hierarchy, rest and bind transforms, local frames, axes, units, limits, skinning, and
morph ontology to [Kinesis](kinesis.md). Kinesis supplies motion clips and technical retargeting;
Atelier supplies animated storytelling. The `rig` operation implies neither.

## Profiles, Runes, Covens, and arbitrary iron

Use [Prism's admission route](index.md#sight-on-finite-iron) to obtain the exact model and
deployment binding. Separate consumer-GPU workers, a resident workstation profile, an Orchestrator
transition after affected leases drain, or an explicitly admitted Portal each needs its own
measured evidence. Two GPUs do not automatically pool VRAM; a published minimum does not prove an
unmeasured driver, precision, resolution, or offload topology.

## The proving bake

The proving corpus covers single images, multiview references, transparent and ambiguous objects,
thin structures, open and non-manifold meshes, hard-surface and organic forms, PBR channels,
semantic parts, humanoid and non-humanoid rigs, camera reconstruction with missing coverage,
Gaussian and radiance portability, Slovak and multilingual briefs, adversarial files, cancellation,
OOM, restart, stasis, and deterministic replay where claimed. Voxel fixtures cover exact 32-cubed
bounds, `solid`, `shell`, and `surface` policies, palette collisions, clipping, empty and full
volumes, block inpainting, closed procedural recipes, `.schem` round trip, and prohibited stateful
blocks.

Measure conditioning adherence, multiview consistency, geometry completeness, topology and
manifoldness where required, normals, UV and PBR validity, texture seams and projection error,
scale and axis correctness, part usefulness, skeleton hierarchy, skin-weight normalization and
deformation clips, held-out reconstruction views, representation portability, voxel occupancy and
silhouette error, palette validity, output validity, latency, peak VRAM and host RAM, disk use,
cancellation settlement, recovery, lineage, and license closure. Promotion is per exact model,
worker, dependency, tool, preset, precision, device topology, input class, and facet set. A prettier
turntable cannot conceal an invalid asset or authority gap.

<span id="voxels-and-the-32-cubed-proving-fixture"></span>

For the complete bounded grid, palette, schematic, and read-back workflow, follow
[Voxel and block export](voxel-and-block-export.md). Form retains the spatial request and result;
the consuming application admits the exported artifact and any later world effect.
