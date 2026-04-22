---
title: Soulstone
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Soulstone: The Forged Local Engine

> _"A Portal is a whisper from the void, but a Soulstone is a god trapped in a bottle. It lives on your iron. It burns your electricity. It obeys only you."_

A **Soulstone** is a **rune config** for a local, containerized inference engine. When inscribed in the Codex, the system transmutes this TOML into physical Podman Quadlet manifests and services (see **[Containers (08)](../../adr/08-containers.md)**).

Unlike a remote API, a Soulstone requires the Magus to understand the physics of their own hardware. You must choose the **Discipline of Animation** that aligns with the model's mass and your silicon's capacity.

## 💎 The Infrastructure Mapping

Every Soulstone in the Codex is a manifestation of the `SoulstoneConfig` rune schema (and possibly a runtime-specific subclass such as `LlamaCppSoulstone`, `VllmSoulstone`, or `SglangSoulstone`). The fields you define in the scroll shape the local runtime and the generated container manifest.

| TOML Field | Runtime Mapping | Purpose |
| :--- | :--- | :--- |
| `image` | `QuadletContainer.image` | The OCI image (e.g., llama.cpp, vLLM, SGLang). |
| `runtime` | runtime adapter selection | Selects the local runtime family (`llamacpp`, `vllm`, `sglang`, etc.). |
| `groups` | coven targets + `Conflicts=` synthesis | Coven/state membership for orchestration. |
| `port` | runtime `--port` + pod publish mapping | Host-visible endpoint identity for the Soulstone. |
| `base_url` | runtime connector endpoint | Optional override; defaults to `http://localhost:{port}/v1`. |
| `exec` | `RuntimePlan.exec_args` override | Explicit command override that bypasses adapter synthesis. |
| `extra_args` (runtime-specific) | adapter flag synthesis tail | Runtime-specific override/extension flags (for example llama.cpp, vLLM, SGLang). |
| `volumes` / `env_vars` | `QuadletContainer` mounts/env | Extra local runtime mounts and environment variables. |
| `secret_env_files` | `QuadletContainer.secrets` + env hydration | Map env var names to Podman secret names; transmuter mounts each secret and sets env var to `/run/secrets/<secret>`. |
| `models` / `model_path` | connector/runtime offer surface | Local model catalog or single-model artifact path for binding later. |

!!! note "Binding Identity vs. Container Shape"
    Older docs described Soulstones as carrying `model_provider` / `tool_provider` directly.
    In the current codebase, Soulstones primarily define local runtime shape and local model artifacts. Dispatcher/Binder policy can still resolve provider routes, but the runtime binding path is connector-based.

---

## :material-school: The Four Disciplines of Animation

A Soulstone is inert until it is bound to an **Animator**—the engine that pumps electricity into the weights. The current core ships with built-in Soulstone profiles for **vLLM**, **SGLang**, and **llama.cpp**. Additional disciplines can be introduced through extensions.

### I. The Kinetic (vLLM)

#### "The Workhorse of the Void."

* **Best For:** High-throughput chat, serving multiple agents simultaneously, and models that fit strictly within VRAM (e.g., Llama-3-70B AWQ on 2x3090).
* **The Mechanic (Continuous Batching):** The Kinetic engine creates a "fluid" memory space. If two Agents query the Soulstone simultaneously, vLLM splits the GPU's attention cycle, serving both in parallel slots. It is the only way to run a "Hive Mind" on limited silicon without queuing latency.
* **The Constraint:** It demands purity. The model **must** fit entirely in VRAM. If it overflows, it crashes.
* **The Configuration:**
    * **Memory Greed:** By default, vLLM consumes 90% of VRAM instantly for the KV Cache. When testing, curb its appetite or an OOM occurs before a single token is generated. Use `--gpu-memory-utilization 0.9` to tune this.
    * **The Batching Trap:** For a single user, vLLM's aggressive batching can sometimes increase latency. If you are debugging, use `--max-num-seqs 1` to force serial processing, though this defeats the engine's primary purpose.
    * **Quantization:** Excellent support for **AWQ**. Ensure you strictly define `--quantization awq`.

### II. The Weaver (SGLang)

#### "The Specialist of Loops."

* **Best For:** Agentic Orchestrators, complex tool-use loops, and structured data extraction.
* **The Mechanic (Radix Attention):** Unlike the Kinetic engine which sees memory as isolated blocks, The Weaver sees memory as a **Tree**.
    * _The Loop:_ When an Agent tries a plan, fails, and backtracks to the system prompt to try again, The Weaver does not re-compute the prompt. It simply "branches" the tree from the existing memory node.
    * _The Result:_ Massive efficiency gains for Agents that "think" in loops or multi-turn reasoning steps.
* **The Hardware Reality (Ampere):** SGLang utilizes the **Marlin Kernel** (`--enable-marlin`) for AWQ models. This is highly optimized for RTX 3090 architectures, often outperforming standard GEMM kernels.
* **The Nuance:** SGLang is strictly for NVIDIA. While vLLM attempts to support AMD/ROCm, SGLang focuses on CUDA purity.

!!! tip "The Pydantic Synergy (No DSL Required)"
    You do not need to learn the complex SGLang DSL (`sgl.gen`) to unlock this speed. SGLANG is natively compatible with **OpenAIChatCompletions**.

    1.  **Automatic FSM:** When PydanticAI sends a standard `json_schema` in the API request, SGLang automatically detects it and engages its **Compressed Finite State Machine**. This forces the GPU to generate valid JSON at hardware speed, bypassing the need for Python-based regex parsing.
    2.  **The Multitasking Tree:** Do not fear context switching. The Radix Attention engine is a **Tree**, not a single block. You can run a "Coder Agent" and a "Vision Agent" with completely different System Prompts simultaneously. As long as your VRAM context buffer (the ~13GB margin) is not 100% full, SGLang keeps *both* conversation branches "hot" in memory, switching between them instantly without reloading.

### III. The Titan (llama.cpp)

#### "The Burden of Atlas."

* **Best For:** Massive Models (MoE, 405B) that exceed your 48GB VRAM capacity, and Orchestration tasks where raw intelligence outweighs speed.
* **The Mechanic (The Offload):** The Titan accepts that the GPU is finite. It splits the model layer-by-layer. Layers 1-40 might live on the GPU (Fast), while layers 41-80 live in System RAM (Slow).
* **The Flags of Power:**
    * `--n-gpu-layers`: The slider of speed. You push this until your VRAM is 99% full.
    * `--n-cpu-moe`: A critical flag for Mixture-of-Experts (like Mixtral or DeepSeek). It allows the "Expert" layers to live in RAM while the attention heads stay on GPU.
* **The Cost:** Speed bleeds away the deeper you tap into System RAM. The PCIe bus becomes the bottleneck.
* **The Solitude:** The Titan is solitary. It generally processes one request at a time (Serial).

#### Router Specialization (llama.cpp)

llama.cpp is treated as a special runtime with two startup modes:

- **Single Mode:** starts with `-m <model_path>` and serves one model alias.
- **Router Mode:** starts without `-m` and uses `--models-dir` or `--models-preset` to load/unload models dynamically.

When `startup_mode = "auto"`:

- if `model_path` is set -> single mode
- otherwise -> router mode

This allows a single Soulstone to expose a model catalog while still presenting one runtime endpoint to the dispatcher/binder at any given moment.

Mode/argument precedence is deterministic:

1. `exec` set explicitly in TOML -> runtime adapter does not synthesize flags.
2. `startup_mode` set to `single`/`router` -> forced mode.
3. `startup_mode = "auto"` -> infer from `model_path` (`single` if set, else `router`).
4. `extra_args` -> appended last, so users can override defaults without forking schema.

### IV. The Flash (ExLlamaV2)

#### "The Speed of Light."

!!! note "Extension-Owned Discipline (Current Phase)"
    ExLlamaV2 is described here as a valid discipline pattern, but it is not a built-in core Soulstone profile in the current codebase. Treat it as an extension-owned runtime family unless/until a builtin rune schema and runtime adapter are added.

* **Best For:** Single-user throughput and "Fractional" Quantization (e.g., 4.65bpw) to squeeze the absolute maximum model size into VRAM.
* **The Architecture:** This engine uses the **ExLlamaV2** kernel.
    * _Warning:_ There is a "V3" kernel designed for Hopper (H100) architecture. For your RTX 3090s (Ampere), **ExLlamaV2** is still the superior choice. Do not be seduced by the higher number; architecture compatibility matters more.
* **The Format:** Requires models converted to `.exl2`. This format allows for "measurement files" that calibrate the quantization specifically to minimize perplexity loss on critical layers.

---

## :material-scale-balance: The Ritual of Compression (Quantization)

Do not run models in FP16 (Raw weight) unless you possess H100s. The degradation in intelligence from **4-bit quantization** is negligible compared to the massive gains in VRAM efficiency (allowing for larger context windows).

| Discipline | Format | Recommended Quant | Notes |
| :--- | :--- | :--- | :--- |
| **Kinetic / Weaver** | **AWQ** | 4-bit | The gold standard for vLLM/SGLang. Faster decoding than GPTQ on Ampere. Compatible with the **Marlin** kernel for extreme speed. |
| **Titan** | **GGUF** | **Q4_K_M** | The "Balanced" quant. Offers the best ratio of perplexity (intelligence) to size. Avoid Q2/Q3 unless strictly necessary for 405B models. |
| **Flash** | **EXL2** | **4.0 - 6.0 bpw** | Fractional bit-per-weight. Allows you to fill your VRAM to the exact megabyte. |

---

## 🤝 Coven Management (The Group Rule)

To manage finite VRAM, Soulstones declare their membership in **Covens** using the `groups` field.

* **Inclusive Coexistence:** If two Soulstones share at least one common group (e.g., `groups = ["vision-state"]`), they belong to the same Coven. Systemd allows them to run simultaneously.
* **Exclusive Banishment:** If two Soulstones share **no** common groups, they are mutually exclusive. The system generates a `Conflicts=` directive between them.

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
groups = ["vision-ritual"] # Shares the group; will NOT be killed by 'eye'
port = 8781
model_path = "/models/moondream.gguf"
startup_mode = "single"
n_gpu_layers = 99
```

The Dispatcher later binds model/tool surfaces from the runtime connector exposed by these Soulstones.

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

The **[Orchestrator](../../adr/23-orchestrator.md)** uses these group definitions to manifest the machine's state.

1. **The Intent:** An Agent needs `vision`. The Orchestrator identifies the `vision-ritual` coven.
2. **The Cleansing:** Systemd automatically stops any active Soulstone services/Quadlet units that do not belong to `vision-ritual` (e.g., your heavy `deep-think` coven).
3. **The Manifestation:** All services tagged with `vision-ritual` are started in concert.

!!! warning "The Port Singularity"
    **Every Soulstone must listen on a unique host port.**
    Even if they are in different Covens and never run together, the host OS requires a "cool down" period for the TCP socket. Reusing a port across different Soulstones causes state transitions to fail with `Address already in use`.

!!! tip "Self-Aware Connectivity"
    The system automatically calculates the `base_url` for every Soulstone as `http://localhost:{port}/v1` unless you override it.

    The Lich handles the internal networking within the Pod. You define the local runtime shape (`runtime`, ports, groups, models, flags), and the Dispatcher/Binder hydrate the callable model/tool surfaces from the connector exposed by that runtime.
