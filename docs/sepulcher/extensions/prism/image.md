---
title: Image
icon: material/image-auto-adjust
---

# :material-image-auto-adjust: Image

An image request owes more than new pixels. **Image** records which operation was requested,
which sources and controls it may use, what changed, and which exact profile produced the
candidate. An image-capable chat model can interpret the picture; this Maker/editor passage
produces or transforms it.

Begin with the operation and expected return, then select a simple serving or full workflow
route. The study was reviewed on **2026-08-26**. These are Designed contracts and candidate
bakes, with delivery owned by [State](../../../state-of-the-work.md#vision-admission). Technical
settlement leaves creative adoption, export, and publication with their named owners.

## One job, explicit operation

The image-producing surface should accept the whole useful input family without pretending that
every admitted model implements every form:

| Operation | Inputs | Required meaning |
| --- | --- | --- |
| `generate` | prompt | Create one or more new candidates from text. |
| `edit` | prompt plus one or more source or reference images | Mutate, restyle, compose, or preserve identity according to the selected profile. |
| `inpaint` | prompt, source image, and mask | Replace only the declared region; outpainting is an expanded canvas plus an explicit mask. |
| `control` | prompt plus pose, depth, edge, sketch, layout, or other control artifact | Preserve the declared structure according to a separately baked control profile. |
| `enhance` | source image and exact enhancement profile | Restore, remove a background, or upscale while declaring whether the operation can hallucinate detail. |

### Request and provenance

A candidate `ImageJob@2` therefore carries an explicit operation, prompt and negative prompt,
authorized source, reference, mask, and control `ArtifactRef` values, requested dimensions and
candidate count, seed policy, immutable preset, deadline, budget, and output policy. Optional
inputs do not grant an engine capabilities it has not declared and proved.

The job also retains the operator-facing prompt, its declared or detected source language when
known, the requested model-facing language, and translation policy. A translator may derive a
model-facing prompt only through an admitted transformation that preserves both texts, translator
revision, and declared loss. Interface locale, model convenience, or prompt enhancement never
silently replaces visual direction.

Source-grounded masks, regions, pose, depth, and other controls may come from
[Sight](sight.md). Image retains the generative effect; the control's source coordinates,
transform lineage, uncertainty, and exact artifact digest remain visible rather than becoming
anonymous workflow tensors.

### Technical settlement

`ImageJob@2` owns the requested operation, candidate set, technical validation, and result
settlement. Creative adoption belongs to Voidlight or another consuming Composition; successful
custody and probes never accept the image on that owner's behalf. Each concrete execution uses Core's Designed
[`ServiceJobAttempt@1`](../../../adr/14-workers.md#service-job-attempts-designed) mechanics;
`INDETERMINATE` remains contained and nonterminal rather than a successful or failed image result.
Numeric progress, previews, cancellation acceptance and settlement, multiple references, hard
masks, deterministic seeds, and partial streaming are independent capability facts. A Connector
must not synthesize support from a broadly compatible endpoint.

Each result receipt retains source and output digests, original and derived prompt language and
texts, translator revision and declared loss, engine and container revision, model and component
digests, exact preset or graph digest, LoRA and control adapters, scheduler, steps, guidance, seed,
dtype and quantization, dimensions, timing, warnings, and cancellation settlement.
Provider filenames, image IDs, and embedded PNG metadata are evidence inputs, not canonical
provenance.

## Serving route and workflow route

The first implementation study keeps two complementary routes rather than forcing a workflow
graph through a lowest-common-denominator API.

| Candidate | Office | Present judgment |
| --- | --- | --- |
| [vLLM-Omni](https://github.com/vllm-project/vllm-omni) | Apache-2.0 omni and diffusion serving through OpenAI-compatible `/v1/images/generations` and `/v1/images/edits`, including multiple images and masks where the model supports them. | Primary simple serving candidate. It is a separate runtime project from ordinary vLLM even though it shares the ecosystem and command shape. Bake generation, editing, cancellation, quantization, output limits, and lifecycle independently. |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | GPL-3.0 graph inference server with image and mask upload, queued workflows, WebSocket progress, history, interruption, and model-memory release. | Full-power workflow connector for control maps, LoRA stacks, multiple samplers, inpaint, upscale, detail passes, and future image/video/3D nodes. Only allowlisted built-in or exactly pinned custom nodes and immutable workflow presets may run. |
| [SGLang-Diffusion](https://github.com/sgl-project/sglang) | Apache-2.0 performance-oriented diffusion server with OpenAI Images serving and native or Diffusers-backed pipelines. | Challenger behind the same basic Images profile. Promote only where a model or measured throughput, batching, placement, or sharding advantage beats the first route. |

OpenAI Images is a useful transport dialect, not the inner contract. Generation and edit support
must be profiled separately, along with mask, multi-reference, partial-stream, and cancellation
behavior. The API does not provide a universal durable image-job resource; LychD retains job
identity, state, authority, retry law, and artifact custody.

For a Comfy route, select only the immutable preset and parameter openings admitted under the
[engine contract](../../animator/soulstone/engines/comfyui.md#keep-model-engine-and-road-apart).
Arbitrary graphs, runtime checkpoint downloads, partner API nodes, and ambient custom-node
installation are forbidden. The engine graph supplies no Spellweaver or effect authority.

[Diffusers](https://github.com/huggingface/diffusers) remains the reference implementation and
model-compatibility path. It is a Python library rather than a complete multi-user job service, so
LychD should not build another general Diffusers server before a supported serving engine proves
insufficient. Stable Diffusion is one model family runnable through these engines, not an
automation runtime; every chosen checkpoint, encoder, VAE, adapter, and dependency retains its own
license and bake.

One runtime adapter and endpoint may later expose separate admitted Image and Video dialect drivers
for pinned graphs. Their operations, job profiles, and editorial boundaries remain separate; a
generic Connector label cannot merge them.

## First permissive model profiles

The initial model bake remains deliberately small:

| Profile | Intended office | License and iron |
| --- | --- | --- |
| [FLUX.2 klein 4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) | Fast interactive text-to-image, single-reference edit, and multi-reference edit in one checkpoint. | Apache-2.0 and approximately 13 GB VRAM by its official card. The FLUX.2 klein 9B, 9B-KV, and FLUX.2 dev models use non-commercial terms and are not substitutes for this profile. |
| [Qwen-Image-2512](https://huggingface.co/Qwen/Qwen-Image-2512) plus [Edit-2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) and a pinned control profile | High-quality generation and typography; identity-sensitive single/multi-image editing; masked and structural work across the family. | Apache-2.0 but heavy: the official BF16 packages include roughly 57.7 GB of components. Treat as a stasis/offload or explicitly sharded quality route, not a permanent companion to a large Mind. |

FLUX.2 klein 4B is the first resident-friendly default. The Qwen family is the first heavy quality
and control route. Neither project logo proves every operation: FLUX generic reference editing is
not a hard preservation mask, and separate Qwen checkpoints remain separate Rune profiles.

## Coven, stasis, and the proving bake

One possible Coven keeps a compact Multimodal Mind on one 24 GB GPU and FLUX.2 klein on the other.
A large Qwen-Image profile may instead need affected work to release its leases through
[Prism's Stasis and readiness passage](index.md#sight-on-finite-iron).
Two 24 GB devices are not implicitly one 48 GB device: the exact runtime must prove sharding,
offload, warm-up, cancellation, and complete release. Neither Comfy nor a serving engine may choose
placement or evict another Animator.

The first corpus should cover natural scenes, illustration, UI and poster text, Slovak diacritics,
single- and multi-reference identity, preservation edits, masks and expanded canvases, pose/depth/
edge controls, transparent output, adversarial dimensions and metadata, cancellation, OOM,
restart, and deterministic-seed replay. Measure prompt alignment, text accuracy, source and region
preservation, identity drift, control adherence, diversity, latency, peak VRAM, output validity,
artifact lineage, and license closure.

Promote exact profiles: the first bake compares FLUX.2 klein through vLLM-Omni with the same basic
profile where SGLang-Diffusion supports it, then proves one allowlisted Comfy workflow for the
advanced path. Qwen-Image enters as the heavy quality/control route only after its exact
quantization or offload topology passes on operator iron.
