---
title: Video
icon: material/movie-open-play-outline
---

# :material-movie-open-play-outline: Video

Prism's **Maker/editor** office covers generation and generative transformation of visual material
through time. A video model may create a shot, animate a still, continue a clip, transfer motion,
or condition performance on audio. It does not thereby own visual direction, sound production, the
final audiovisual timeline, structured animation curves, or publication.

This candidate study was reviewed on **2026-08-08**. It records a proposed contract, runtime
shortlist, model register, and proving bake—not delivery, automatic fallback, or permission to
generate, transform, export, or publish video.

## One temporal job, several proved operations

The inner surface should remain stable while engines and models evolve. A candidate `VideoJob@1`
names one explicit operation:

| Operation | Inputs | Required meaning |
| --- | --- | --- |
| `t2v` | prompt | Create one or more new moving-image candidates from text. |
| `i2v` | prompt plus one or more source or reference images | Animate or derive a clip while declaring what continuity the selected profile can preserve. |
| `v2v` | prompt plus source video and optional controls | Restyle, edit, condition, or transform a clip without calling the result a deterministic edit. |
| `first_last` | prompt plus first and last frame | Generate the temporal path between exact boundary images. |
| `continue` | prompt plus source clip or boundary frames | Extend motion forward or backward under a separately proved continuity profile. |
| `motion_transfer` | character or subject reference plus driving video | Transfer motion or replace a subject while retaining both sources in lineage. |
| `audio_driven` | character or scene reference plus admitted audio | Produce synchronized visible performance from speech, song, music, or another exact audio source. |

Optional material never invents support. Each model profile declares the operations, source kinds,
reference counts, controls, output limits, and cancellation behavior that its exact bake proved.
First/last-frame control, masks, camera paths, poses, depth, edges, generated sound, interpolation,
and upscaling are independent claims rather than implications of generic video support.

[Sight](sight.md) may supply source-grounded masks, regions, pose, depth, flow, or tracks as exact
controls. Video owns the generative temporal effect; a track remains a bounded estimate with gaps,
not subject identity or proof of what happened.

[Kinesis](kinesis.md) owns reusable skeletal, root, hand, face, contact, and transform motion
facets. A motion-transfer or audio-driven video may visibly perform while returning pixels only;
it does not imply a rig-compatible clip. If one worker returns both pixels and structured motion,
the compound result retains separate Video and Kinesis facets, validation, and provenance.

The job carries immutable source and control `ArtifactRef` values; original and derived prompts;
negative prompt; seed policy; width, height, frames, frame rate, duration, and timebase; an
immutable preset; deadline and budget; output profile; and a closed engine-extension object. A
prompt translator may derive the model-facing prompt from the operator's preferred language, but
the receipt preserves both texts, translator revision, and declared loss. Translation never
silently replaces visual direction.

`VideoJob@1` owns the requested temporal effect, candidates, validation, and adoption. Each
concrete execution uses Core's Designed
[`ServiceJobAttempt@1`](../../../adr/14-workers.md#service-job-attempts-designed) mechanics.
Numeric progress, step progress, previews, cancellation before start, cancellation while running,
and cancellation granularity are separate Connector facts. Deleting a provider record is not
evidence that a running generation was cancelled; an indeterminate attempt remains contained and
is reconciled by the same provider identity.

Every returned file is immediately ingested into Reliquary custody and rehashed. A canonical
receipt retains input and output digests; engine, container, model, encoder, decoder, VAE, LoRA,
and control revisions and licenses; graph or preset digest; sampler, steps, guidance, seed, dtype,
quantization, offload and parallelism; dimensions, frames, rate, timebase, codec, timing, warnings,
cost, progress, and cancellation settlement. Provider IDs, filenames, and embedded metadata are
evidence inputs, not canonical provenance.

## Serving route, workflow route, and deterministic tools

| Candidate | Office | Present judgment |
| --- | --- | --- |
| [vLLM-Omni](https://docs.vllm.ai/projects/vllm-omni/en/latest/serving/videos_api/) | OpenAI-compatible asynchronous `/v1/videos` serving for text-, image-, video-, and audio-conditioned models, with a synchronous benchmark route and runtime-specific fields. | First simple-serving runtime. One server instance hosts one startup-selected model. Bake each operation independently; its documented delete route does not establish running cancellation. |
| [ComfyUI](https://docs.comfy.org/api-reference/v2/jobs/submit-a-workflow-for-execution) | Self-hosted graph runtime with durable API v2 jobs, polling, event progress, outputs, and a cancellation request; legacy local server routes remain a different dialect. | Advanced connector for first/last frames, masks, structural controls, model chains, motion transfer, interpolation, upscale, and audio-driven workflows. Admit only immutable allowlisted graphs and pinned nodes. |
| [SGLang-Diffusion](https://docs.sglang.io/docs/sglang-diffusion/api/openai_api) | Performance-oriented image/video server implementing a subset of OpenAI Videos, native and Diffusers-backed pipelines, offload, quantization, and parallel execution. | Bake-time challenger behind the same basic profile. Add no second mandatory connector until an exact model proves a material support, placement, batching, or throughput advantage. |
| [LightX2V](https://lightx2v-en.readthedocs.io/en/latest/deploy_guides/deploy_service.html) | Video-focused inference framework with quantization, CPU and disk offload, multi-device execution, asynchronous task endpoints, and current-task interruption. | Research lane for constrained and heterogeneous iron. Its service-wide busy/idle and current-task stop semantics are too coarse to define Core job law. |

[Diffusers](https://github.com/huggingface/diffusers) remains a model SDK and compatibility
substrate, not another connector unless LychD deliberately builds and accepts a durable worker
around it. OpenAI Videos is likewise a useful wire dialect, not the inner contract: LychD keeps
job identity, authority, custody, retry, cancellation, and recovery.

A Comfy graph is an engine program, not a Spellweaver Pattern or another workflow jurisdiction.
Its Rune selects an immutable LychD preset whose graph, nodes, model dependencies, parameter
openings, network behavior, and output paths passed Assimilation. Runtime downloads, arbitrary
imported workflows, ambient custom-node installation, and unapproved partner nodes fail closed.

FFmpeg is deterministic machinery, not a generative model or application. Prism's Lens may use a
pinned FFmpeg revision for per-artifact probing, extraction, normalization, interpolation, or
encoding with declared loss. [Voidlight](../../../compositions/voidlight/motion.md) owns creative
motion and accepted visual sequences; [Broadcast](../../../compositions/broadcast/edit.md) owns the
final audiovisual timeline, trim, placement, captions, mix, mux, and editorial render. A
generative `v2v` operation never becomes the final cut merely because its input was already video.

## First model profiles

The initial register keeps one permissive routine family and a few materially distinct
specialists. These are exact profile candidates, not claims that one family name grants every
operation.

| Profile | Intended office | License and placement judgment |
| --- | --- | --- |
| [Wan2.2 TI2V-5B](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B) | Routine text-to-video and image-to-video through one 5B model, including 720p at 24 fps. | Apache-2.0. Its official single-consumer-GPU path makes it the first default bake, but one named card does not prove every 24 GB device, driver, precision, duration, or resolution. |
| [Wan2.1 VACE-1.3B](https://github.com/ali-vilab/VACE) | Reference-to-video, controlled video-to-video, masked changes, motion, swap, expansion, and other structural editing. | Small first control/editor candidate. Pin exact VACE and Wan dependencies and close their licenses; do not infer that a later VACE profile is equivalent. |
| [Wan2.2 Animate-14B](https://huggingface.co/Wan-AI/Wan2.2-Animate-14B) | Character animation and subject replacement driven by reference motion. | Apache-2.0 specialist. Its optional dependencies retain separate terms; no community quantization or wrapper changes those terms. |
| [Wan2.2 S2V-14B](https://huggingface.co/Wan-AI/Wan2.2-S2V-14B) | Image-plus-audio performance for speech, song, and other synchronized visible motion. | Apache-2.0 specialist with a substantially heavier official placement than TI2V-5B. Supplying audio is conditioning, not proof that the model created or owns that audio. |
| [LTX-2.3](https://github.com/Lightricks/LTX-2) | Joint synchronized audio-video generation, retake, extension, dubbing, and multi-keyframe work in one family. | Distinct capability candidate under the LTX-2 Community License rather than Apache-2.0; revenue threshold, attribution/disclosure, derivative terms, compatible Gemma encoder terms, and larger-memory placement require separate admission. |
| [HunyuanVideo-1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) | Efficient text- and image-conditioned video where its exact profile wins a bake. | Region-gated candidate, not a universal local option: its community license excludes use in the EU, UK, and South Korea. Location and current license eligibility must fail closed before model download or execution. |

Wan TI2V-5B is the first permissive routine default; VACE is the first controlled editor. Animate
and S2V remain distinct specialists because a general T2V/I2V checkpoint does not prove motion
transfer or audio-driven performance. LTX remains valuable where native joint sound and video
outweigh its license and resource burden. Hunyuan is neither globally accepted nor globally
banned: it is ineligible where its own territory clause withholds a license.

If a model emits sound with video, Prism records a compound candidate and separates the returned
streams into attributable artifacts. [Riffmaw](../../../compositions/riffmaw/index.md) retains sonic
judgment, Voidlight retains visual judgment, and Broadcast alone accepts their final relation.
`generate_sound=true` cannot silently transfer those offices to a video connector.

## Profiles, Runes, Covens, and arbitrary iron

Hardware suitability belongs to an exact deployment profile, never to the universal job contract.
The same model may be permanently resident on a large-memory workstation, offloaded or quantized
on a smaller host, sharded across measured devices, or reached through an explicitly admitted
Portal. A personal two-card bake is evidence for that host, not a product ceiling.

The service path remains distinct:

```text
VideoJob@1
→ CapabilityDemand(interface, operation, typed facets, eligible profile refs)
→ Dispatcher issues JobGrant or HardwareTransitionRequired
→ Orchestrator converges scarce local iron when required
→ re-dispatch and invoke the exact granted driver
```

A Designed Soulstone Rune declares the concrete service instance and exact `[[capabilities]]`
references to immutable interface/profile/driver/dialect/evidence/resource definitions, plus
devices, mounts, lifecycle, group membership, and conflicts. Current `[[models]]` capability hints
belong only to v1 model compatibility. A Coven only names compatible Soulstones that may rise
together. It does not choose placement, merge GPU memory, schedule jobs, relax conflicts, put
another service to sleep, or authorize Portal fallback.

One deployment may keep a compact Mind and routine Wan worker on separate consumer GPUs. Another
may keep a large Mind and a heavy video specialist together on one high-memory workstation. A
third may drain incompatible leases, invoke runtime-native sleep through Orchestrator, and assign
several measured devices to one worker. Two devices do not become pooled memory without exact
runtime support, and multi-device execution is admitted only when its chosen tensor, pipeline,
sequence, or stage topology proves correctness and benefit.

[vLLM-Omni Sleep Mode](https://docs.vllm.ai/projects/vllm-omni/en/latest/features/sleep_mode/)
can release most stage VRAM while retaining process state, making it a strong future runtime
transition mechanism. The Run—not the engine—enters Stasis; Orchestrator owns lease drain,
transition admission, readiness, restoration, and uncertainty containment.

## The proving bake

Promotion is per exact engine, model, dependency, preset, precision, quantization, offload,
parallel topology, device class, resolution, frame count, and rate. The matrix includes a bounded
24 GB consumer profile, a single large-memory workstation profile, an explicit multi-device
profile, and a Portal profile where policy permits. No universal VRAM formula substitutes for
receipts on operator iron.

The corpus covers multilingual and Slovak briefs with preserved prompt derivation; text-to-video;
single- and multi-image conditioning; first/last frames; continuation; controlled and masked V2V;
identity and character motion; speech, song, and music-driven performance; camera and temporal
continuity; subtitles and visible text; adversarial dimensions, codecs, metadata, and durations;
cancel before start and during generation; OOM; restart; stasis/wake; and deterministic-seed
replay where claimed.

Measure prompt and control adherence, source and identity preservation, temporal coherence,
motion quality, lip and audio synchronization, flicker, visible text, accessibility hazards,
duration and timebase correctness, output validity, latency, peak VRAM, host RAM, disk traffic,
warm-up and wake time, throughput, cancellation settlement, recovery, artifact lineage, and
license closure. Promote only the exact profiles whose measured costs and failure behavior remain
honest; more powerful iron may admit a broader resident Coven without changing `VideoJob@1`.
