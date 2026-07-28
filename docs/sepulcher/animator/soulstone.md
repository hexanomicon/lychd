---
title: Soulstone
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Soulstone: The Forged Local Engine

> _"A Portal is a whisper from the remote sky, but a Soulstone is a daemon in a bottle. It lives on local iron. It burns local electricity. It answers only the Magus."_

A **Soulstone** is the local runtime Animator: a Quadlet/systemd-backed service that lives on local iron. A **Soulstone Rune** is the Codex TOML declaration that describes it. When inscribed in the Codex, the system transmutes the Soulstone Rune into physical Podman Quadlet manifests and services (see **[Containers (08)](../../adr/08-containers.md)**).

Unlike a remote API, a Soulstone requires the Magus to understand the physics of local hardware. For model-backed Soulstones, the **Discipline of Animation** must align with the model's mass and the silicon's capacity. For non-model Soulstones, the same principle applies to CPU, RAM, disk, sockets, credentials, and any other local substrate the service consumes.

## The Infrastructure Mapping

Every Soulstone Rune in the Codex is a concrete leaf config under the abstract `SoulstoneConfig` branch, such as `LlamaCppSoulstoneConfig`, `ExLlamaV3SoulstoneConfig`, `VllmSoulstoneConfig`, or `SglangSoulstoneConfig`. The fields defined in the scroll shape the local runtime and the generated container manifest.

| TOML Field | Runtime Mapping | Purpose |
| :--- | :--- | :--- |
| `image` | `QuadletContainer.image` | The OCI image (e.g., llama.cpp, TabbyAPI, vLLM, SGLang, or another service image). |
| `runtime` | runtime adapter selection | Selects the local runtime family (`llamacpp`, `exllamav3`, `vllm`, `sglang`, etc.). |
| `groups` | Coven target membership | Compatible operator/systemd aggregation; never a conflict declaration. |
| `[concurrency].conflict_domains` | Animator-target conflict graph | Finite hardware domains this managed Soulstone cannot share. Omission preserves conservative switching; explicit `[]` declares coexistence. |
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

A Soulstone is inert until it is bound to an **Animator adapter**: the connector that turns a local service into routable capabilities. The current model-backed core ships with built-in Soulstone profiles for **vLLM**, **SGLang**, **llama.cpp**, and **ExLlamaV3 through TabbyAPI**. Additional disciplines can be introduced through extensions, including non-model services whose adapters expose observation, browsing, execution, or peer-network capabilities.

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

### IV. ExLlamaV3 through TabbyAPI

**ExLlamaV3 is the inference library; TabbyAPI is its official OpenAI-compatible server.** LychD
keeps that server outside the daemon dependency graph and registers it as the dynamic
`animator/exllamav3` Soulstone runtime.

- The official TabbyAPI image is pinned by digest in the generated sample. TabbyAPI is a rolling,
  separately versioned boundary; changing the image requires contract tests and a local NVIDIA
  hardware receipt.
- The container starts healthy without a model. That is `ACTIVATABLE`, not `WARM`.
- `POST /v1/model/load` reports several stages over SSE. LychD consumes the whole stream and then
  verifies `GET /v1/model`; a disconnect is ambiguous because TabbyAPI continues the detached load.
  A valid terminal stream followed by no active model releases the fence as a completed-but-lost
  runtime epoch. A mid-stream transport loss cannot prove that, so it becomes a contained `ERROR`;
  restart the caged Vessel to reset Tabby and the in-memory epoch together before another load.
- Stable LychD `[[models]].id` values are distinct from Tabby's directory basenames. LychD derives
  the runtime name from each validated direct-child `path` basename. The connector translates it
  on both the lifecycle API and OpenAI data plane; agent bindings continue to request the stable
  LychD id.
- Authentication is mandatory even inside the un-published private pod. `auth_secret_name`
  references one Podman secret containing strict JSON with distinct `api_key` and `admin_key`
  values of at least 32 printable ASCII characters. The secret is mounted only into TabbyAPI and
  the trusted Vessel: inference uses the data-plane key and lifecycle calls use the admin key.
  Rune files, environment values, and generated manifests contain only the secret name.
  This contract is deliberately unavailable to the uncaged Vessel until a host credential and
  network boundary exists; `bind --uncaged` rejects such a Soulstone.
- TabbyAPI is bound to `lychd-vessel.service`; loss or restart of the Vessel also stops Tabby so a
  detached model load cannot outlive LychD's mutation fence. ExLlamaV3, vLLM, and SGLang runtime
  plans request shared memory explicitly. Because every container in the pod shares one tmpfs,
  the pod sums the configured per-runtime requirements; the size remains a lazy ceiling rather
  than preallocated RAM, and no shared-memory size is imposed when no runtime requests one.
- The current phase-one adapter sends only the declared model directory and backend. Effective
  context, cache quantization/size, tensor or autosplit placement, and per-GPU reserve therefore
  remain TabbyAPI defaults and are opaque to LychD's scheduler. A model-local `tabby_config.yml`
  overrides even API load parameters. Resource-aware support must add a typed per-model load
  profile plus requested-versus-effective verification and an explicit managed-mode policy for
  that hidden override; raw option dictionaries are not an acceptable Rune surface.
- TabbyAPI writes a rotating file log under `/app/logs` even though LychD captures stdout through
  journald. The rootless Quadlet therefore mounts that directory as an ephemeral mode-1777 tmpfs;
  no writable host or control-plane directory is exposed to the inference container. LychD also
  pins TabbyAPI's log level above INFO because that upstream level prints raw authentication keys.
- The adapter does not copy rootful Docker Compose `memlock` or `nofile` raises into rootless
  Quadlet: ordinary user-manager hard limits cannot honor them. Any future limit change needs a
  measured Tabby requirement, host preflight, and rootless Podman receipt.

```toml
name = "exl3"
volumes = ["/data/models:/app/models:ro"]
auth_secret_name = "tabby_exl3_auth"

# podman secret create tabby_exl3_auth ./tabby-exl3-auth.json
# JSON: {"api_key":"<32+-char-data-key>","admin_key":"<different-32+-char-admin-key>"}

[[models]]
id = "daily-driver"
path = "/app/models/qwen-exl3"
format = "EXL3"
```

The adapter and mocked server-contract tests are part of core support. A real Podman + NVIDIA +
model run remains an operator/hardware acceptance receipt, as it does for the other GPU engines.
Replacing a Podman secret does not update existing containers; rotate both keys by recreating the
Vessel and this TabbyAPI Soulstone together.

## :material-scale-balance: The Ritual of Compression (Quantization)

Models should not run in FP16 (Raw weight) unless H100-class hardware is available. The degradation in intelligence from **4-bit quantization** is negligible compared to the massive gains in VRAM efficiency (allowing for larger context windows).

| Discipline | Format | Recommended Quant | Notes |
| :--- | :--- | :--- | :--- |
| **Kinetic / Radix** | **AWQ** | 4-bit | The gold standard for vLLM/SGLang. Faster decoding than GPTQ on Ampere. Compatible with the **Marlin** kernel for extreme speed. |
| **ExLlamaV3** | **EXL3** | Hardware/model-specific | Native ExLlamaV3 format. Validate the chosen quant, cache, and split against the actual GPU topology. |
| **Titan** | **GGUF** | **Q4_K_M** | The "Balanced" quant. Offers the best ratio of perplexity (intelligence) to size. Avoid Q2/Q3 unless strictly necessary for 405B models. |

---

## Coven Management (The Group Rule)

Soulstones declare compatible operator/systemd **Coven target membership** with `groups` and
physical incompatibility separately with `[concurrency].conflict_domains`.

- **Shared Coven Label:** If two Soulstones share `groups = ["vision-ritual"]`, both are addressed
  through that generated aggregate only when their conflict-domain sets are compatible.
- **Shared Conflict Domain:** If two lifecycle-managed Soulstones both declare
  `conflict_domains = ["gpu-main"]`, binding compiles a conflict edge between their individual
  Animator targets. They may not share a Coven.
- **Conservative Omission:** Omitting `conflict_domains` on a dedicated non-resident assigns the
  compiler-owned `default-exclusive` unknown wildcard. It conflicts with every managed
  non-resident whose effective domain set is non-empty, so partial migration cannot silently make
  a legacy Rune coexist.
- **Explicit Coexistence:** `conflict_domains = []` declares that the Soulstone has no
  systemd-enforced conflict. Make that assertion only when the combined hardware profile is known
  to fit.
- **Resident Law:** A `persistent_resident` Soulstone may not participate in a conflict domain.
  Binding rejects a configuration that could let another target evict it.
- **Advertised Life:** Every Soulstone must synthesize at least one capability through its
  registered runtime adapter. Phase one derives Orchestrator activity truth from capabilities, so
  bind/load rejects an unadvertised local service instead of allowing its systemd state to diverge
  from the planner. A container that is intentionally only infrastructure belongs in a core or
  extension unit until an Animator runtime-state port exists independently of capabilities.
- **Operator Break-Glass:** A host operator may explicitly start or stop an Animator or Coven
  target. That bypasses Orchestrator admission, lease drain, stale-world validation, readiness, and
  compensation; runtime and agent code must never use those targets as an orchestration API.
- **Reserved Alliances:** Global `alliances` remain accepted shape for later policy. They are not
  an enforcement boundary.

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
exec = [
  "-m", "sglang.launch_server",
  "--host", "0.0.0.0", "--port", "8780",
  "--model-path", "/models/qwen3-next-80b-awq",
  "--tp", "2",
]

[concurrency]
dedicated = true
conflict_domains = ["gpu-pair"]

# ~/.config/lychd/runes/animator/soulstones/llamacpp/vision_scribe.toml
name = "scribe"
description = "Specialized CPU OCR tool (Titan)."
image = "ghcr.io/ggml-org/llama.cpp:server-cuda"
runtime = "llamacpp"
groups = ["vision-ritual"]
port = 8781
model_path = "/models/moondream.gguf"
startup_mode = "single"
n_gpu_layers = 0

[concurrency]
dedicated = true
conflict_domains = ["cpu-ocr"]
```

The domains do not overlap, so binding may place both Animator targets in `vision-ritual`. The
domain names are declarations of incompatibility, not measured capacity: the Magus must still know
that the GPU-backed engine and CPU-backed OCR service fit together. The Dispatcher later binds
capability surfaces from their runtime connectors; the same placement law applies to non-model
local services.

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

## The Law of Exclusivity

The **[Orchestrator](../../adr/23-orchestrator.md)** owns temporal authority; systemd owns the
physical transaction. Coven grouping owns neither.

1. **The Intent:** An Agent needs one declared capability on a target Animator.
2. **The Plan:** `declared-conflicts` recomputes the Rune-declared graph and selects the target's exact
   active conflict neighborhood, independent of group labels.
3. **The Drain:** Admission closes and existing leases on that exact affected set finish.
4. **The Seal:** The current active world and loaded Animator-target graph must match the plan.
5. **The Manifestation:** The actuator asks systemd to start the target Animator target once;
   systemd stops its compiled conflicts before starting it as one transaction.
6. **The Proof:** The Orchestrator awaits WARM and owns exact compensation toward the captured
   prior compatible target set if readiness fails.

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
| `groups` | list[string] | `[]` | Compatible Coven aggregates this stone joins; not a conflict declaration. |
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
| `persistent_resident` | bool | Pin the runtime resident. A resident cannot participate in a conflict domain. |
| `conflict_domains` | list[string], optional | Finite hardware domains the runtime cannot share. Omitted on a dedicated non-resident means the conservative `default-exclusive` wildcard; explicit `[]` alone declares coexistence. |

Conflict domains apply only to lifecycle-managed Soulstones. A shared (`dedicated = false`) Rune
or a persistent resident may omit the field or declare `[]`; a non-empty set fails bind because
LychD may neither evict a shared runtime nor let a compiled edge evict a resident.
Labels are unique lowercase identifiers of at most 50 characters, beginning and ending with an
ASCII letter or digit and using only letters, digits, `_`, or `-` inside. Treat
`default-exclusive` as compiler-owned: omit the field to request that conservative wildcard.

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
comparison, and neither endpoint may equal, contain, or sit beneath the Codex, Crypt,
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
    A **dynamic server** (the llama.cpp router or ExLlamaV3 through TabbyAPI) yields `is_dynamic=True` capabilities: the endpoint may be reachable while the requested model is only `ACTIVATABLE`. A server **pinned to one model** (a single `model_path`, e.g. a vLLM server) yields `is_dynamic=False` — reachable means warm, no activation step.
