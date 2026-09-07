---
title: Video
icon: material/movie-open-play-outline
---

# :material-movie-open-play-outline: Video

A still may become a shot; a clip may be continued, transformed, or driven by admitted sound.
Prism **Video** binds that generative temporal effect to exact sources, prompts, controls, and
clocks, then returns technically validated candidates. Visual direction, structured animation,
sound production, final editing, and publication remain separately owned.

Read the operation and compound-facet passage before selecting a model. The candidate study was
reviewed on **2026-08-26** and proves no delivered adapter or permitted effect;
[State](../../../state-of-the-work.md#vision-admission) owns that boundary.

## One temporal job, several proved operations

The inner surface should remain stable while engines and models evolve. A candidate `VideoJob@2`
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

`VideoJob@2` owns the requested temporal effect, candidate set, technical validation, and result
settlement. Creative adoption belongs to Voidlight or another consuming Composition; successful
custody and probes never accept the work on that owner's behalf. Each concrete execution uses
Core's Designed
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

## Admit every compound facet

A video request that may return sound crosses a second, explicit admission boundary. Declare its
roles before dispatch; after technical settlement, retain each owner's independent judgment.
The same compound artifact can therefore be technically valid while one intended use is refused.

Before execution, `VideoJob@2` also pins one `MediaFacetAuthoritySet@1`. It contains one row for
every requested output facet: stable facet id; technical kind; exact semantic role; consuming
Composition identity and revision; owner request or brief digest; permitted use and audience;
source, likeness, voice, rights, and consent evidence; classification, retention, and Portal
policy; paid-effect ceiling; required separability; and disposition when that facet cannot be
proved. The closed sound-role vocabulary is `music`, `timed_language`, `picture_sound`, and
`world_sound`; a provider's generic `audio` or `sound` label is not a semantic role.

A profile may enable native sound only after every requested sound row passes that preflight. When
the row entails speech capture, transcription, synthesis, cloning, or voice identity, it also pins
the exact eligible Echo contract and profile; the timed-language consumer still owns words,
alignment, performance fit, and edition judgment. When a model cannot disable or separate a sound
facet, the job either declares and authorizes every possible role before dispatch or selects a
different profile. Capability support, payment authority, and semantic acceptance are separate
facts.

If a model emits sound with video, Prism records one compound candidate, original container digest,
shared timebase, and generation receipt, then separates the returned streams into attributable
child artifacts when their rights and formats permit it. [Voidlight](../../../compositions/voidlight/index.md)
retains visual judgment; [Riffmaw](../../../compositions/riffmaw/index.md) musical judgment;
[Language Edition](../../../compositions/language-edition/index.md) timed-language judgment;
[Broadcast](../../../compositions/broadcast/index.md) picture-sound and final editorial audiovisual judgment;
and [Foundry](../../../compositions/foundry/sound.md) world-sound judgment.

Technical settlement does not make any facet usable. Each declared consumer independently issues a
`SemanticFacetAdmissionReceipt@1` that pins its Composition identity and revision, owner request
digest, facet and compound digests, role, use boundary, evidence and findings, decision maker, and
one `accepted`, `refused`, or `quarantined` disposition. Prism may link those receipts to the
technical result but cannot issue, merge, or upgrade them. The same bytes used in two roles require
two receipts. Broadcast's later judgment of the final editorial audiovisual relation cannot substitute for
Voidlight, Riffmaw, Language Edition, or Foundry admission.

Sound absent from `MediaFacetAuthoritySet@1` produces an `UnexpectedMediaFacet@1` finding and fails
closed for that facet: it is quarantined or deleted under the pinned retention rule, never routed
as a usable candidate and never assigned a guessed owner. A provably separable visual child may
continue after that disposition; an inseparable compound remains unusable unless every declared
facet owner accepts the exact compound digest and use. `generate_sound=true`, demux, or a provider
label cannot transfer an office or launder undeclared sound.

## Serving route, workflow route, and deterministic tools

| Candidate | Office | Present judgment |
| --- | --- | --- |
| [vLLM-Omni](https://docs.vllm.ai/projects/vllm-omni/en/latest/serving/videos_api/) | OpenAI-compatible asynchronous `/v1/videos` serving for text-, image-, video-, and audio-conditioned models, with a synchronous benchmark route and runtime-specific fields. | First simple-serving runtime. One server instance hosts one startup-selected model. Bake each operation independently; its documented delete route does not establish running cancellation. |
| [ComfyUI](../../animator/soulstone/engines/comfyui.md#pin-the-dialect-and-execution-lifecycle) | Graph runtime whose external beta API v2 supplies durable jobs, progress, outputs, and cancellation requests. Self-hosting that dialect currently requires the separately pinned `comfy-api-proxy`; classic local server routes remain distinct. | Advanced connector for first/last frames, masks, structural controls, model chains, motion transfer, interpolation, upscale, and audio-driven workflows. Admit only immutable allowlisted graphs and pinned nodes. |
| [SGLang-Diffusion](https://docs.sglang.io/docs/sglang-diffusion/api/openai_api) | Performance-oriented image/video server implementing a subset of OpenAI Videos, native and Diffusers-backed pipelines, offload, quantization, and parallel execution. | Bake-time challenger behind the same basic profile. Add no second mandatory connector until an exact model proves a material support, placement, batching, or throughput advantage. |
| [LightX2V](https://lightx2v-en.readthedocs.io/en/latest/deploy_guides/deploy_service.html) | Video-focused inference framework with quantization, CPU and disk offload, multi-device execution, asynchronous task endpoints, and current-task interruption. | Research lane for constrained and heterogeneous iron. Its service-wide busy/idle and current-task stop semantics are too coarse to define Core job law. |

[Diffusers](https://github.com/huggingface/diffusers) remains a model SDK and compatibility
substrate, not another connector unless LychD deliberately builds and accepts a durable worker
around it. OpenAI Videos is likewise a useful wire dialect, not the inner contract: LychD keeps
job identity, authority, custody, retry, cancellation, and recovery.

For a Comfy workflow, select only the preset and parameter openings admitted under the
[engine contract](../../animator/soulstone/engines/comfyui.md#keep-model-engine-and-road-apart).
Caller-supplied graphs, runtime downloads, ambient custom nodes, and unapproved partner nodes fail
closed. The Spell placement retains the surrounding semantic contract.

[Prism's Lens](../../../adr/36-vision.md#decision) may use a pinned FFmpeg revision as deterministic
machinery for per-artifact probing, extraction, normalization, interpolation, or
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
| [LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) | Joint synchronized audio-video generation, multishot and multi-keyframe work, image conditioning, continuation, and related audio/video transformations in one family. | Distinct capability candidate under the LTX-2.x Community License rather than Apache-2.0. Its August 2026 terms include a commercial-revenue threshold and other use, transfer, attribution, and derivative conditions; the exact checkpoint, Gemma 4 encoder, video/audio decoders, Comfy or native pipeline, and placement require one reviewed closure. |
| [HunyuanVideo-1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) | Efficient text- and image-conditioned video where its exact profile wins a bake. | Region-gated candidate, not a universal local option: its community license excludes use in the EU, UK, and South Korea. Location and current license eligibility must fail closed before model download or execution. |

Wan TI2V-5B is the first permissive routine default; VACE is the first controlled editor. Animate
and S2V remain distinct specialists because a general T2V/I2V checkpoint does not prove motion
transfer or audio-driven performance. LTX remains valuable where native joint sound and video
outweigh its license and resource burden. Hunyuan is neither globally accepted nor globally
banned: it is ineligible where its own territory clause withholds a license.

## Profiles, Runes, Covens, and arbitrary iron

Hardware suitability belongs to an exact deployment profile, never to the universal job contract.
The same model may be permanently resident on a large-memory workstation, offloaded or quantized
on a smaller host, sharded across measured devices, or reached through an explicitly admitted
Portal. A personal two-card bake is evidence for that host, not a product ceiling.

Follow [Prism's admission route](index.md#sight-on-finite-iron) for a grant or handle-free
transition and re-dispatch. Declare the concrete service through its
[Soulstone Rune](../../animator/soulstone/rune.md) and Designed
[capability/profile binding](../../animator/capabilities.md#runes-runes-in-groups-and-placement);
current `[[models]]` hints cover only v1 model compatibility. Orchestrator validates placement
and declared conflicts; a Coven only groups compatible local services. Any Portal fallback needs
its own admission.

A compact Mind and Wan worker may occupy separate consumer GPUs; a high-memory workstation may
keep a heavy specialist resident beside a large Mind. Reassigning incompatible devices first
requires lease drain and an Orchestrator transition. Two devices do not become pooled memory
without exact runtime support; the chosen tensor, pipeline, sequence, or stage topology must prove
correctness and benefit.

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
honest; more powerful iron may admit a broader resident Coven without changing `VideoJob@2`.
