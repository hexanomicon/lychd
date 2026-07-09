---
title: Soulstone
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Soulstone: The Forged Local Engine

> _"A Portal is a whisper from the remote sky, but a Soulstone is a daemon in a bottle. It lives on local iron. It burns local electricity. It answers only the Magus."_

A **Soulstone** is the local runtime Animator: a Quadlet/systemd-backed service that lives on local iron. A **Soulstone Rune** is the Codex TOML declaration that describes it. When inscribed in the Codex, the system transmutes the Soulstone Rune into physical Podman Quadlet manifests and services (see **[Containers (08)](../../adr/08-containers.md)**).

Unlike a remote API, a Soulstone requires the Magus to understand the physics of local hardware. For model-backed Soulstones, the **Discipline of Animation** must align with the model's mass and the silicon's capacity. For non-model Soulstones, the same principle applies to CPU, RAM, disk, sockets, credentials, and any other local substrate the service consumes.

## 💎 The Infrastructure Mapping

Every Soulstone Rune in the Codex is a concrete leaf config under the abstract `SoulstoneConfig` branch, such as `LlamaCppSoulstoneConfig`, `VllmSoulstoneConfig`, or `SglangSoulstoneConfig`. The fields defined in the scroll shape the local runtime and the generated container manifest.

| TOML Field | Runtime Mapping | Purpose |
| :--- | :--- | :--- |
| `image` | `QuadletContainer.image` | The OCI image (e.g., llama.cpp, vLLM, SGLang, Phoenix, Playwright, or another service image). |
| `runtime` | runtime adapter selection | Selects the local runtime family (`llamacpp`, `vllm`, `sglang`, etc.). |
| `groups` | coven target membership | Operator/systemd grouping only; v1 eviction policy is independent of group labels. |
| `port` | runtime `--port` + pod publish mapping | Host-visible endpoint identity for the Soulstone. |
| `base_url` | runtime connector endpoint | Optional override; defaults to `http://localhost:{port}/v1`. |
| `exec` | `RuntimePlan.exec_args` override | Explicit command override that bypasses adapter synthesis. |
| `extra_args` (runtime-specific) | adapter flag synthesis tail | Runtime-specific override/extension flags (for example llama.cpp, vLLM, SGLang). |
| `volumes` / `env_vars` | `QuadletContainer` mounts/env | Extra local runtime mounts and environment variables. |
| `secret_env_files` | `QuadletContainer.secrets` + env hydration | Map env var names to Podman secret names; transmuter mounts each secret and sets env var to `/run/secrets/<secret>`. |
| `models` / `model_path` | connector/runtime offer surface | Optional local model catalog or single-model artifact path for model-backed binding later. |

!!! note "Binding Identity vs. Container Shape"
    Older docs described Soulstones as carrying `model_provider` / `tool_provider` directly.
    In the current codebase, Soulstones primarily define local runtime shape and local model artifacts. Dispatcher/Binder policy can still resolve provider routes, but the runtime binding path is connector-based.

---

## :material-school: Model-Backed Disciplines of Animation

A Soulstone is inert until it is bound to an **Animator adapter**: the connector that turns a local service into routable capabilities. The current model-backed core ships with built-in Soulstone profiles for **vLLM**, **SGLang**, and **llama.cpp**. Additional disciplines can be introduced through extensions, including non-model services whose adapters expose observation, browsing, execution, or peer-network capabilities.

### I. The Kinetic (vLLM)

#### "The Workhorse of the Iron."

- **Best For:** High-throughput chat, serving multiple agents simultaneously, and models that fit strictly within VRAM (e.g., Llama-3-70B AWQ on 2x3090).
- **The Mechanic (Continuous Batching):** The Kinetic engine creates a "fluid" memory space. If two Agents query the Soulstone simultaneously, vLLM splits the GPU's attention cycle, serving both in parallel slots. It is the only way to run a "Hive Mind" on limited silicon without queuing latency.
- **The Constraint:** It demands purity. The model **must** fit entirely in VRAM. If it overflows, it crashes.
- **The Configuration:**
    - **Memory Greed:** By default, vLLM consumes 90% of VRAM instantly for the KV Cache. During testing, curb its appetite or an OOM occurs before a single token is generated. Use `--gpu-memory-utilization 0.9` to tune this.
    - **The Batching Trap:** For a single user, vLLM's aggressive batching can sometimes increase latency. During debugging, use `--max-num-seqs 1` to force serial processing, though this defeats the engine's primary purpose.
    - **Quantization:** Excellent support for **AWQ**. Define `--quantization awq` explicitly.

### II. The Radix (SGLang)

#### "The Specialist of Loops."

_(This discipline was formerly called "the Weaver"; it was renamed to free that name for the [Workflow extension](../extensions/weaver.md).)_

- **Best For:** Agentic Orchestrators, complex tool-use loops, and structured data extraction.
- **The Mechanic (Radix Attention):** Unlike the Kinetic engine which sees memory as isolated blocks, The Radix sees memory as a **Tree**.
    - _The Loop:_ When an Agent tries a plan, fails, and backtracks to the system prompt to try again, The Radix does not re-compute the prompt. It simply "branches" the tree from the existing memory node.
    - _The Result:_ Massive efficiency gains for Agents that "think" in loops or multi-turn reasoning steps.
- **The Hardware Reality (Ampere):** SGLang utilizes the **Marlin Kernel** (`--enable-marlin`) for AWQ models. This is highly optimized for RTX 3090 architectures, often outperforming standard GEMM kernels.
- **The Nuance:** SGLang is strictly for NVIDIA. While vLLM attempts to support AMD/ROCm, SGLang focuses on CUDA purity.

!!! tip "The Pydantic Synergy (No DSL Required)"
    The complex SGLang DSL (`sgl.gen`) is not required to unlock this speed. SGLang is natively compatible with OpenAI-style chat completions, which the binder can expose through the same `OpenAIChatModel` path used by other OpenAI-compatible runtimes.

    1. **Automatic FSM:** When PydanticAI sends a standard `json_schema` in the API request, SGLang automatically detects it and engages its **Compressed Finite State Machine**. This forces the GPU to generate valid JSON at hardware speed, bypassing the need for Python-based regex parsing.
    2. **The Multitasking Tree:** Context switching is safe when the buffer has room. The Radix Attention engine is a **Tree**, not a single block. A "Coder Agent" and a "Vision Agent" can run with completely different System Prompts simultaneously. As long as the VRAM context buffer (the ~13GB margin) is not 100% full, SGLang keeps *both* conversation branches "hot" in memory, switching between them instantly without reloading.
    3. **The Iterative Ingestion Pattern (Attention Exactness):** Avoid dumping 100K+ context files (like full framework repos) into a single prompt. LLM attention mechanisms degrade and lose precision in massive contexts. Instead, establish a Base Prompt and loop over the document chapter-by-chapter (`Base Prompt + Snippet 1`, `Base Prompt + Snippet 2`). SGLang's Radix Attention instantly prefills the Base Prompt for every iteration, allowing fast, aggregated results with pinpoint attention accuracy across massive codebases.

### III. The Titan (llama.cpp)

#### "The Burden of Atlas."

- **Best For:** Massive Models (MoE, 405B) that exceed a 48GB VRAM envelope, and Orchestration tasks where raw intelligence outweighs speed.
- **The Mechanic (The Offload):** The Titan accepts that the GPU is finite. It splits the model layer-by-layer. Layers 1-40 might live on the GPU (Fast), while layers 41-80 live in System RAM (Slow).
- **The Flags of Power:**
    - `--n-gpu-layers`: The slider of speed. Raise it until VRAM is nearly full.
    - `--n-cpu-moe`: A critical flag for Mixture-of-Experts (like Mixtral or DeepSeek). It allows the "Expert" layers to live in RAM while the attention heads stay on GPU.
- **The Cost:** Speed bleeds away the deeper the model reaches into System RAM. The PCIe bus becomes the bottleneck.
- **The Solitude:** The Titan is solitary. It generally processes one request at a time (Serial).

#### Router Specialization (llama.cpp)

llama.cpp is treated as a special runtime with two startup modes:

- **Single Mode:** starts with `-m <model_path>` and serves one model alias.
- **Router Mode:** starts without `-m` and uses `--models-dir` or `--models-preset` to load/unload models dynamically.

When `startup_mode = "auto"`:

- if `model_path` is set -> single mode
- otherwise -> router mode

This allows a single Soulstone to expose a model catalog while still presenting one runtime endpoint to the dispatcher/binder at any given moment.

Mode/argument precedence is deterministic:

1. `exec` set explicitly in TOML → runtime adapter does not synthesize flags.
2. `startup_mode` set to `single`/`router` → forced mode.
3. `startup_mode = "auto"` → infer from `model_path` (`single` if set, else `router`).
4. `extra_args` → appended last, so users can override defaults without forking schema.

#### Capability State During Model Swaps

In router mode, a single llama.cpp Soulstone can serve different models over its lifetime without the container restarting. Each model load/unload transitions the Animator's capability state:

- Container boots → the router is up, so its `is_dynamic=True` capabilities sit at phase `ACTIVATABLE` until a model is loaded.
- Model swap triggered (via llama.cpp API) → the old model's capabilities fall back toward `ACTIVATABLE`/`COLD`.
- New model loads and warms → its capabilities pass through `WARMING` and reach `WARM`.
- The **[Orchestrator](../../adr/23-orchestrator.md)** manages these transitions; no coven swap (Systemd restart) is required.

This means a single llama.cpp Soulstone can dynamically expose `chat`, `vision`, or `embedding` capability families as different models are loaded. The **[Dispatcher](../../adr/22-dispatcher.md)** tracks each capability's `CapabilityPhase` (its position on the `COLD → ACTIVATABLE → WARMING → WARM` ladder) and routes accordingly.

## :material-scale-balance: The Ritual of Compression (Quantization)

Models should not run in FP16 (Raw weight) unless H100-class hardware is available. The degradation in intelligence from **4-bit quantization** is negligible compared to the massive gains in VRAM efficiency (allowing for larger context windows).

| Discipline | Format | Recommended Quant | Notes |
| :--- | :--- | :--- | :--- |
| **Kinetic / Radix** | **AWQ** | 4-bit | The gold standard for vLLM/SGLang. Faster decoding than GPTQ on Ampere. Compatible with the **Marlin** kernel for extreme speed. |
| **Titan** | **GGUF** | **Q4_K_M** | The "Balanced" quant. Offers the best ratio of perplexity (intelligence) to size. Avoid Q2/Q3 unless strictly necessary for 405B models. |

---

## 🤝 Coven Management (The Group Rule)

Soulstones declare operator/systemd **Coven target membership** with the `groups` field.

- **Shared Label:** If two Soulstones share a group (for example `groups = ["vision-state"]`), both
  are addressable through that multi-member target.
- **No Hidden Policy:** Group labels do not prove safe coexistence, and different labels do not make
  services mutually exclusive. Generated units contain no `Conflicts=`. The v1 Orchestrator policy
  independently plans active, dedicated, non-resident Animators and drains its exact set.
- **Operator Break-Glass:** A host operator may explicitly start or stop a Coven target as an
  aggregate action. That bypasses Orchestrator admission, lease drain, and readiness convergence;
  runtime and agent code must never use the target as an orchestration API.
- **Reserved Alliances:** Global `alliances` are accepted configuration shape for a future
  group-aware policy. They have no enforcement effect in v1.

### Example: A Vision Coven

```toml
# ~/.config/lychd/runes/animator/soulstones/sglang/vision_eye.toml
name = "eye"
description = "Reasoning and Vision engine."
image = "lmsysorg/sglang:latest"
runtime = "sglang"
groups = ["vision-ritual"]
port = 8780
model_path = "/models/qwen3-next-80b-awq"
tensor_parallel_size = 2
enable_marlin = true
# extra_args are appended after adapter defaults
extra_args = ["--reasoning-parser", "deepseek-r1"]

# ~/.config/lychd/runes/animator/soulstones/llamacpp/vision_scribe.toml
name = "scribe"
description = "Specialized OCR tool (Titan)."
image = "ghcr.io/ggerganov/llama.cpp:server"
runtime = "llamacpp"
groups = ["vision-ritual"] # Shares the operator target; not a coexistence guarantee.
port = 8781
model_path = "/models/moondream.gguf"
startup_mode = "single"
n_gpu_layers = 99
```

The Dispatcher later binds capability surfaces from the runtime connector exposed by these Soulstones. In this example those surfaces are model and tool capabilities, but the same placement law applies to non-model local services.

## :material-shield-key: Podman Secret Hydration

Soulstones can reference Podman secrets directly with `secret_env_files`.

```toml
name = "private-runtime"
runtime = "vllm"
image = "vllm/vllm-openai:latest"
model_path = "/models/qwen-awq"

# ENV var -> Podman secret name
[secret_env_files]
HF_TOKEN_FILE = "hf_runtime_token"
```

At bind time:

1. LychD checks that each referenced secret exists in Podman.
2. Generated Quadlets emit `Secret=hf_runtime_token`.
3. The container env contains `HF_TOKEN_FILE=/run/secrets/hf_runtime_token`.

This keeps rune files reference-only while allowing runtime code to read credential files.

## ⚔️ The Law of Exclusivity

The **[Orchestrator](../../adr/23-orchestrator.md)**, not the group target, owns the machine's state.

1. **The Intent:** An Agent needs one declared capability on a target Animator.
2. **The Plan:** `evict-idle` selects every other active, dedicated, non-resident Animator,
   regardless of group label.
3. **The Drain:** Admission closes and existing leases on that exact set finish.
4. **The Manifestation:** The actuator performs only the planned stops and target start. Systemd
   target membership adds no automatic stop or extra launch.

For a dynamic router, an in-process model load is also a mutation even though no service restarts.
The Orchestrator closes admission for that entire Animator and drains its leases before loading;
this prevents an existing grant for model A from being invalidated when a bounded router loads
model B. A failed soft activation remains fail-closed because v1 cannot reconstruct the prior
loaded-model set well enough to promise an inverse.

!!! warning "The Port Singularity"
    **Every Soulstone must listen on a unique host port.**
    Even if they are in different Covens and never run together, the host OS requires a "cool down" period for the TCP socket. Reusing a port across different Soulstones causes state transitions to fail with `Address already in use`.

!!! tip "Self-Aware Connectivity"
    A Soulstone may omit `port` and `base_url`; the loader assigns a unique local port and calculates `base_url` as `http://localhost:{port}/v1` before runtime binding. Explicit values still win.

    The Lich handles the internal networking within the Pod. The rune defines the local runtime shape (`runtime`, ports, groups, models, flags), and the Dispatcher/Binder hydrate callable capability surfaces from the connector exposed by that runtime.

---

## Soulstone Rune reference

The precise schema of a Soulstone Rune (`~/.config/lychd/runes/animator/soulstones/<group>/<name>.toml`). The mappings above explain what each field *does*; this is the full field list with types and defaults.

### Top-level fields

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | string (required) | — | Animator name; first segment of every capability key. |
| `description` | string | `""` | Human note. |
| `image` | string | — | Container image (required by the generic runtime; runtime subclasses default it). |
| `runtime` | string | `"generic"` | Runtime family; selects the adapter. |
| `model_path` | string | `null` | Single-model path (single-model servers). |
| `base_url` | URL | `null` | Explicit endpoint, if not derived from the port. |
| `port` | int (1–65535) | `null` | Host port to publish. |
| `groups` | list[string] | `[]` | Coven groups this stone joins. |
| `devices` | list[string] | `[]` | Device passthrough (e.g. GPUs). |
| `volumes` | list[string] | `[]` | Volume mounts. |
| `env_vars` | dict | `{}` | Environment variables. |
| `secret_env_files` | dict | `{}` | Secret-file env mappings (names, not values). |
| `exec` | list[string] | `[]` | Container command/args (bypasses adapter synthesis). |
| `models` | list of `[[models]]` | `[]` | Declared models (below). |
| `generation` | `[generation]` table | `null` | Default generation profile. |

The `[concurrency]` table governs lifecycle:

| Field | Type | Description |
| :--- | :--- | :--- |
| `dedicated` | bool | LychD owns this runtime's lifecycle (may start/stop/swap it). Only `dedicated` animators can be evicted for a swap. |
| `persistent_resident` | bool | Pin the runtime resident — keep it out of the default eviction set and survive swaps. |

### The `[[models]]` blocks

One entry per model served; each yields a capability spec.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | string (required) | — | Model id; last segment of the capability key. |
| `path` | path (required) | — | Container-side model artifact path, made reachable by an explicit global, rune, or adapter volume; there is no implicit host `model_root`. |
| `description` | string | `null` | Human note. |
| `format` | enum | `null` | Weight format override. |
| `[models.capabilities]` | table | `null` | Capability hints (below). |
| `[models.generation]` | table | `null` | Per-model generation overrides. |

All Soulstone volumes—global defaults, rune `volumes`, and adapter-contributed mounts—share one
fail-closed control-root gate. Both endpoints must be absolute. A host symlink is resolved before
comparison, and neither endpoint may equal, contain, or sit beneath the Codex, Crypt, stasis,
Reactor, or user-systemd binding roots. Percent signs, backslashes, and non-printable characters are
also rejected before a value reaches a systemd unit. A safe existing host alias is emitted as its
resolved canonical target, so the checked source cannot later be retargeted through that symlink.

#### `[models.capabilities]` — capability hints

Hints are **authoritative for routing**: a live probe may downgrade a declared capability but can never invent one (the declare-then-verify doctrine, [Dispatcher (22)](../../adr/22-dispatcher.md)).

| Field | Type | Description |
| :--- | :--- | :--- |
| `families` | list | Explicit families; overrides synthesis. Values: `chat`, `vision`, `embedding`, `stt`, `tts`, `tool_execution`, `rerank`. |
| `modalities_in` | list[string] | Admitted inputs: `text`, `image`, `audio`. |
| `modalities_out` | list[string] | Emitted outputs. |
| `supports_tools` | bool | Whether the model can call tools. |
| `supports_streaming` | bool | Whether the model streams. |

!!! warning "image-in is not the Eye"
    Declaring `modalities_in = ["text", "image"]` enriches a `chat` model's admission — it does **not** make it the `vision` family. The dedicated `vision` family is reserved for a purpose-built vision-analysis provider and must be declared with `families = ["vision"]`. This is the [two-axis law](./capabilities.md).

### The `[generation]` table

Default generation parameters. Overlays in order: runtime defaults → the stone's `[generation]` → a model's `[models.generation]`. Every field is optional.

| Field | Type | Range |
| :--- | :--- | :--- |
| `max_context` | int | ≥ 1 |
| `max_tokens` | int | ≥ 1 |
| `temperature` | float | 0.0–2.0 |
| `top_p` | float | 0.0–1.0 |
| `top_k` | int | ≥ 0 |
| `repetition_penalty` | float | ≥ 0.0 |
| `reasoning_format` | string | — |

!!! note "`is_dynamic` follows the server shape"
    A **router** (llama.cpp loading models on demand — `startup_mode = "router"`, `models_dir` set) yields `is_dynamic=True` capabilities (reachable but awaited until a model loads). A server **pinned to one model** (a single `model_path`, e.g. a vLLM server) yields `is_dynamic=False` — reachable means warm, no activation step.
