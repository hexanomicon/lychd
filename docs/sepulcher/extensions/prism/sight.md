---
title: Sight
icon: material/eye-circle-outline
---

# :material-eye-circle-outline: Sight

Prism's **Sight** faculty turns admitted images and finite video into precise, typed visual
estimates. It can locate, segment, track, estimate depth, recover pose, or measure apparent motion.
It does not thereby know why something happened, identify a person, control a camera, or authorize
an effect.

This candidate study was reviewed on **2026-08-08**. It records a proposed contract, runtime and
model shortlist, live-session boundary, and proving bake—not delivery, source truth, surveillance
authority, or permission to retain or act on visual material.

## Three kinds of seeing

The distinction between a multimodal Mind and specialist computer vision is epistemic, not merely
performance tuning:

| Office | Result | Example |
| --- | --- | --- |
| **Lens** | deterministic probe result or derivative under an exact implementation | decode, dimensions, orientation, frame extraction, crop/resize transform |
| **Sight** | typed model estimate grounded to pixels and time | boxes, masks, tracks, depth, keypoints, flow, registered change candidate |
| **Multimodal Mind** | attributed semantic interpretation | caption, relationship, open-ended answer, event or causal hypothesis |

A Qwen, Gemma, or another image-capable chat model can explain what a scene appears to mean. It
does not replace pixel-accurate masks, calibrated coordinates, flow fields, or track gaps. A
specialist detector can report a high score and still be wrong; learned Sight output is not
deterministic truth merely because it is structured.

Scanner retains document OCR, reading order, tables, formulae, and document reconstruction. Sight
may locate a general visual region, but it does not become a second document pipeline.

## One finite job, exact operation

The candidate `SightJob@1` acts on one or more authorized, finite `ArtifactRef` sources and names
one explicit operation:

| Operation | Required meaning |
| --- | --- |
| `classify` | Score an exact closed ontology for a declared region or source; failure to name an open-world object is not absence. |
| `detect` | Return boxes or points for a pinned class vocabulary, threshold, suppression policy, and candidate limit. |
| `ground` | Relate a retained text query to candidate regions; translated queries preserve original text and translator revision. |
| `segment` | Produce semantic, instance, panoptic, or prompted masks under an exact ontology, prompt, and overlap policy. |
| `track` | Relate region hypotheses through an exact finite time window; track identity is local to this job. |
| `estimate_depth` | Produce explicitly relative, inverse, or metric depth plus validity and uncertainty. |
| `estimate_pose` | Produce keypoints under a pinned skeleton ontology and coordinate space. |
| `estimate_flow` | Produce dense or sparse apparent motion between exact source and destination frames. |
| `compare` | Register two sources or a time window and return bounded change candidates plus registration error and alternatives. |

Open-ended event interpretation remains a separately routed Multimodal Mind step. It may consume
exact Sight regions and tracks and return time-bounded hypotheses, but prose does not become a
precise Sight result and a visual correlation does not establish identity or cause. The
interpretation retains the source digest, exact query or open-ended task, sampled and omitted frame
and time spans, supporting and contradicting regions or tracks, prompt, model and profile,
uncertainty, and alternatives. It cannot establish identity, cause, security incident, or effect
completion.

The request pins the operation, source and every Lens derivative, region and time window, query or
class ontology, segmentation and skeleton variants, desired result kinds, eligible profile
constraints, thresholds and output limits, deadline and budget, purpose, classification, and
retention. Resolution Lock selects an exact finite ToolProfile, or Dispatcher selects an eligible
declared capability; the admitted invocation and terminal receipt pin the exact tool or model,
runtime, preprocessing, and postprocessing profile. Optional inputs never imply support.

`SightJob@1` owns perception stages, observation validity, and adoption. Each asynchronous or
durable service or tool execution uses Core's Designed
[`ServiceJobAttempt@1`](../../../adr/14-workers.md#service-job-attempts-designed) state,
idempotency, cancellation, reconciliation, and indeterminate-effect law. The parent Run remains
fenced until the same attempt settles. Partial results enter quarantined custody; only rehashed,
validated observations are adopted, and an uncertain paid or remote request is never replayed
under a new identity.

## A typed visual observation set

`VisualObservationSet@1` does not flatten every output into generic JSON. It binds the source and
working-derivative digests, operation, evidence class, exact producer and profiles, then carries
typed facets:

| Facet | Required facts |
| --- | --- |
| regions | original-source boxes, points, polygons, class or phrase, score semantics, ontology and coverage |
| masks | semantic/instance/panoptic/prompted kind, RLE or mask artifact, region relation, overlap and prompt lineage |
| depth | relative/inverse/metric kind, ray-depth or camera-z convention, units and scale when proved, validity and uncertainty artifacts |
| pose | skeleton ontology and revision, coordinate space, keypoints, visibility and score semantics |
| flow | exact ordered frame pair, vector axes and units, dense or sparse field artifact, validity and occlusion |
| tracks | job-local track id, observations and spans, association method, gaps, occlusion and termination |
| comparison | registration transform and error, compared regions, candidate changes and non-change alternatives |

The terminal receipt additionally pins model and weight digests and license, worker and container,
runtime, precision, device, decoder, color conversion, resize, crop, padding and letterbox,
thresholds, NMS or association revision, taxonomy and label map, timing, resource peaks, warnings,
skipped material, gaps, cancellation settlement, and output digests. An overlay PNG or annotated
video is a derived visualization; machine-readable observations remain canonical.

A confidence value is not automatically a calibrated probability and is not comparable across
models. Calibration evidence, if available, names its corpus, revision, and applicable profile. A
negative result is valid only for its exact region, time window, ontology, threshold, sampling, and
coverage. Crash, occlusion, dropped frame, skipped region, and unknown class never become
"absent".

## Coordinates and time survive preprocessing

Every canonical region refers to original source pixels and pins source width and height, origin,
axes, pixel-edge or pixel-center convention, half-open `xyxy` box convention, polygon winding and
clipping policy, plus the exact derivative-to-source transform chain for orientation, crop, resize,
pad, and letterbox. Normalized coordinates are only a projection.

Every mask raster, depth grid, and dense flow field pins its own width, height, sample convention,
validity domain, and exact spatial map to the original source. A model-sized array is never assumed
to share source pixels merely because it has been upsampled for display.

Finite-video observations pin artifact digest, presentation-frame ordinal, original rational
timebase and PTS, and DTS where relevant. They also retain the temporal derivative-to-source map
for trim, frame extraction, decimation, resampling, and duplicate or dropped frames. Inferred
average FPS cannot replace variable-rate timing. Tracks name gaps and occlusion rather than drawing
a continuous history through missing evidence. Stream epoch belongs only to live sessions.

Depth additionally pins intrinsics, extrinsics, lens distortion and admitted scale evidence where
available. Relative depth is not metres. Pose declares image, camera, or world coordinates and the
exact keypoint schema. Flow declares source and destination frames, vector direction and units,
and any transform back to the original source. Compare cannot silently treat lighting, viewpoint,
compression, parallax, or registration failure as physical change.

## One Prism interface, two first worker substrates

There is no useful OpenAI-compatible wire contract for exact masks, depth, pose, flow, coordinates,
and time. OpenAI-style chat remains appropriate for VLM text. KServe v2 can later transport named
tensors, shapes, and dtypes, but it does not define Sight semantics. Prism therefore owns the Sight
interface, profiles, reference adapter, and normalization into `VisualObservationSet@1`; Core owns
only general capability demand, typed grants, readiness, and attempt mechanics.

| Candidate | Layer | Present judgment |
| --- | --- | --- |
| `sight-torch` | Immutable isolated [PyTorch](https://github.com/pytorch/pytorch) and [Transformers](https://github.com/huggingface/transformers) worker profiles using native model preprocessing. | First reference substrate because current foundation CV models ship here first. Heavy and model-specific, so no ambient downloads, unpinned modules, caller-supplied paths, or network. |
| `sight-onnx` | [ONNX Runtime](https://onnxruntime.ai/docs/execution-providers/) worker with pinned graph, opset, shapes, execution provider, preprocessing and postprocessing. | Second Prism reference substrate and first CPU lane. Exportability is a proved profile, not a family assumption; golden parity against the reference worker is mandatory. |
| [OpenVINO](https://github.com/openvinotoolkit/openvino) | Initial ONNX Runtime execution-provider profile for Intel CPU, iGPU, or NPU. | Prism execution profile inside `sight-onnx`, not a third substrate or first separate server. A direct backend needs later measured justification. |
| [NVIDIA Triton](https://github.com/triton-inference-server/server) | Later KServe-compatible tensor serving with Triton-specific batching, sequence, repository, and multi-model behavior. | Add an optional adapter only when GPU-fleet measurements justify its operational weight. Source is BSD-3-Clause, but the NGC image and optional NVIDIA components retain additional terms. |
| [OpenVINO Model Server](https://github.com/openvinotoolkit/model_server) | Later KServe-compatible Intel edge and fleet serving with its own scheduler, DAG, and MediaPipe behavior. | Reuse the tensor adapter where proved; KServe compatibility does not make its state or scheduling equivalent to Triton. |

PyTorch, ONNX Runtime, and OpenVINO run model graphs; Transformers, MMDetection, MMSegmentation,
MMPose, SAM, OpenCV, Kornia, Supervision, and tracking packages are libraries inside a pinned
worker. None knows LychD custody, coordinate law, authority, result schemas, or recovery and none
becomes a Core connector merely by exposing Python or a demo server.

The strict-FOSS execution lane is CPU ONNX Runtime with its CPU or OpenVINO profile. NVIDIA driver,
CUDA, cuDNN, ONNX Runtime CUDA, and PyTorch CUDA deployments retain separate proprietary system
terms even without TensorRT. TensorRT is an additional operator-enabled NVIDIA accelerator under
its own non-OSI SDK license, not the strict-FOSS default. Ultralytics is AGPL-3.0 or commercially
licensed and remains an external license-gated profile; exporting one of its models to ONNX does
not erase upstream terms.
TorchServe is excluded because the official project is archived and no longer plans maintenance or
security fixes. Roboflow Inference mixes an Apache core with cloud, enterprise, metered, dynamic,
and separately licensed surfaces, so it is not the default Sight boundary.

The minimum promotion order is one Torch detector; SAM 2 image segmentation; the same or an
equivalent exported detector through ONNX Runtime CPU with golden parity; RTMW through ONNX Runtime
and OpenVINO; finite-video association; SAM 2 video propagation; and only then live GStreamer.

## First permissive profile candidates

The first register composes a small number of distinct specialists:

| Profile | Components and office | License and placement judgment |
| --- | --- | --- |
| `ground_segment_track` | Original Grounding DINO Swin-T for text-grounded boxes, [SAM 2.1 Small](https://github.com/facebookresearch/sam2) for prompted image/video masks, and [ByteTrack](https://github.com/FoundationVision/ByteTrack) for box association when the detector reruns on a declared cadence. | [Grounding DINO](https://github.com/IDEA-Research/GroundingDINO) and SAM 2 use Apache-2.0 source routes, SAM 2 checkpoints declare Apache-2.0, and ByteTrack is MIT. Pin and close the exact Grounding DINO checkpoint metadata and dependencies. GPU is the practical interactive bake despite its CPU mode. |
| `depth_camera` | [Depth Anything 3 Small](https://github.com/ByteDance-Seed/depth-anything-3) for relative depth, confidence, and multiview camera facts. | Apache-2.0 80M profile and first general depth candidate. DA3 Large, Giant, and Nested are CC-BY-NC-4.0; Metric Large and Mono Large are separately named Apache exceptions, and metric output remains a separate bake. |
| `human_wholebody` | Exact RTMW-m 256 by 192 through [MMPose](https://github.com/open-mmlab/mmpose), with a pinned RTMDet person detector and whole-body schema. | Apache-2.0 toolkit candidate for detailed 2D body, hand, face, and foot keypoints; exact weights and dependencies still require closure. First prove PyTorch reference and ONNX Runtime CPU/OpenVINO parity. Ordinary RTMPose-m remains a baseline, not the same profile. |
| `dense_flow` | [SEA-RAFT `Tartan480x640-M`](https://github.com/princeton-vl/SEA-RAFT) for optical flow and uncertainty. | BSD-3-Clause 19.7M specialist. Activate only when Image, Video, Form, or an exact Pattern has a consumer; no CPU or real-time promise is inferred. |

SAM 2 propagates only prompted masks. ByteTrack associates boxes supplied by repeated detector
runs; it neither detects new entrants nor performs mask propagation. Point tracking and optical
flow are further distinct temporal claims. Stateful video profiles preserve frame order and retain
every point, box, mask, query, detector-cadence, and association event; embedding caches and
framework session objects are ephemeral optimizations, never artifact custody or recoverable truth.

Useful challengers remain profiles rather than initial duplication: Apache-designated D-FINE N/S
or RF-DETR Nano/Small for fixed-taxonomy real-time detection; EdgeTAM for mobile segmentation;
DA3 Metric Large when metres are actually required; Video Depth Anything Small for long-video
depth; and RTMO for crowded one-stage pose. Each enters only where exact quality, latency, hardware,
export, or fine-tuning evidence beats the first route.

SAM 3/3.1 is the present technical reference for unified text-prompted image/video detection,
segmentation, and tracking, but it uses Meta's custom SAM License and gated checkpoints rather than
an OSI license. Grounding DINO 1.5/1.6 and DINO-X examples use the DDS cloud API; only the original
Grounding DINO route is the first local permissive candidate. Depth Anything V2 Small and Video
Depth Anything Small are Apache alternatives, while their larger variants are generally
CC-BY-NC-4.0. Sapiens2, Rex-Omni, X-Pose data paths, CoTracker, and RF-DETR Plus components retain
custom, non-commercial, or otherwise gated terms and cannot be inferred safe from a family name.

No general temporal-event model enters the first set. A Multimodal Mind handles coarse semantic
video understanding. Fixed action localization through OpenTAD and an exact backbone may enter
later only for a named ontology and corpus; generated timestamps remain interpretations grounded
to the frames and temporal resolution actually sampled.

## Finite video first, live sight later

[`FFmpeg`](https://www.ffmpeg.org/legal.html) remains the pinned Lens subprocess for file probing,
exact frame extraction, pixel-format conversion, and finite batch video. Its effective distribution
license depends on the exact build: `--enable-gpl` makes that build GPL, while `--enable-nonfree`
makes the resulting binary unredistributable. Neither can be hidden behind the executable name.

A camera or RTSP feed is not an infinite `SightJob`. The later `LiveSightSession@1` pins camera and
controller identity, named purpose, retained admitted authority or policy receipt, viewers, zones
and privacy masks, active window, resolution and rate, separately admitted raw-frame access,
recording, analysis, retention and egress scopes, stream epoch, queue, cardinality, latency and
resource budgets, sampling and drop policy, and downstream consumers. The receipt records the
basis LychD admitted; it is not a claim of legal certification.

Frame identity is stream epoch plus sequence. Reported RTP, device, or PTS clocks may be absent,
synthesized, or reset, so their provenance and mapping to monotonic and wall clocks retain explicit
synchronization uncertainty. Queues are bounded. When upstream cannot pause, the admitted profile
samples or drops under an explicit policy and emits exact gaps and watermarks. A proved contiguous
transport reconnect may continue the same epoch; otherwise it closes. Every new epoch receives a
new local track namespace. Cross-epoch association is a separately attributed inference, never a
reused track identity. Checkpoints retain references, cursors, prompts, and gaps—not raw frames,
framework objects, device handles, or unbounded history.

[GStreamer](https://gstreamer.freedesktop.org/documentation/frequently-asked-questions/general.html)
is the first later live transport candidate for RTSP jitter, timestamps, hardware decode, and
bounded [`appsink`](https://gstreamer.freedesktop.org/documentation/app/appsink.html) delivery.
Pipeline strings and network routes are immutable allowlisted Rune profiles, never operator or
model-authored code. Only the contained transport worker receives the exact admitted RTSP route;
inference workers remain networkless. Starting capture, PTZ, recording, camera configuration,
robot motion, or another world effect remains with the controlling Composition. Sight only observes.

## Privacy and identity are not optional profiles

Admission bounds dimensions, pixels, frames, duration, rate, bitrate, codec and parser resources,
decompression, metadata, output cardinality, derivative expansion, compute, and retention. Decode
and inference run contained without ambient network. Embedded URLs, subtitles, metadata, OCR text,
pixels, and VLM output are hostile data, never instructions.

Classification follows every crop, mask, embedding, overlay, depth map, and track derivative. A
blurred image or caption is not automatically declassified. Track IDs are local association labels,
never stable object or person identities. Face detection used to apply a privacy mask grants no
face recognition.

When policy requires source-side privacy masking, the capture or transport boundary applies the
pinned mask before persistence, inference-worker access, preview, or Portal egress. Stale camera
calibration, mask mismatch, or masking failure stops the route; it never falls back to unmasked
frames. Access to raw frames remains a separate explicit scope even when downstream derivatives
are retained.

Cross-session re-identification, face recognition, gait or voice fusion, demographic or emotion
inference, biometric templates, neighbour surveillance, ambient public streaming, and indefinite
retention are absent and denied by default. They would require separate high-risk law and cannot be
enabled by changing a model id in a Sight Rune.

## Profiles, Runes, Covens, and the proving bake

A model profile pins exact operation, weights, license, ontology, preprocessing, result facets,
postprocessing, measured hardware envelope, and quality claims. A Designed Rune pins a concrete
resident/shared worker through exact `[[capabilities]]` references plus backend, devices, mounts,
lifecycle, load semantics, and conflicts. A finite worker may instead be a Spell-selected
ToolProfile delivered through a trusted executor or Tomb. A Coven names compatible Soulstones that
may rise together; it does not load every catalogue entry, merge GPU memory, create a live camera
grant, or choose fallbacks.

A small fixed detector or RTMPose profile may live on an ONNX Runtime CPU/OpenVINO worker while a
multimodal Mind occupies a GPU. Grounding DINO, SAM 2, or DA3 may use a transient or resident
PyTorch GPU worker. "Real-time" is never an engine property: the exact model, resolution, device,
precision, stream count, queue, sampling, and drop profile must prove it. Two GPUs are not pooled
memory without explicit runtime support.

The first bake covers clean and degraded images; orientation, crop, pad, and letterbox reversal;
small, occluded, transparent, overlapping, and unknown objects; negative grounding queries; masks
and boundaries; crowded people and nonstandard poses; relative and calibrated depth; camera facts;
fast motion, blur and occlusion; variable-frame-rate video, duplicate and dropped frames; Slovak and
multilingual grounding prompts with retained translation; change under lighting and viewpoint;
adversarial codecs and metadata; cancellation, OOM, crash, restart, and stasis.

Measure per-operation benchmark quality and calibration, localization and boundary error, ontology
coverage, depth error and scale validity, keypoint error, flow endpoint error, tracking association
and gaps, source-coordinate round trip, PTS/timebase fidelity, false absence, output validity,
latency, throughput, peak GPU and host memory, queue behavior, cancellation, recovery, custody,
privacy enforcement, and license closure. Promote exact profiles, not model logos or demo FPS.

Sight's results may become exact controls for [Image](image.md), [Video](video.md),
[Form](form.md), or [Kinesis](kinesis.md). A per-frame pose or tracked keypoint remains an
observation with source coordinates, gaps, and uncertainty; Kinesis must create and validate any
structured motion derivative. Voidlight retains creative judgment, Form retains 3D
reconstruction, Blockworld and physical Compositions retain effect authority, and
[Oculus](../oculus.md) may observe Sight job health without owning the underlying visual facts.
