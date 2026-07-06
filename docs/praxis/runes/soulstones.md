---
title: Soulstone Runes
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Soulstone Rune reference

A **Soulstone Rune** declares one local model service. It lives under
`~/.config/lychd/runes/animator/soulstones/<group>/<name>.toml` and `lychd bind` transmutes
it into a podman/systemd service. This is the full schema. For the concept, see
[Soulstone](../../sepulcher/animator/soulstone.md); for how it becomes a routable
capability, see [Capabilities](../../sepulcher/animator/capabilities.md).

## Top-level fields

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | string (required) | — | Animator name; first segment of every capability key (`<name>:<family>:<model_id>`). |
| `description` | string | `""` | Human note. |
| `image` | string | — | Container image (required by the generic runtime; runtime-specific subclasses default it). |
| `runtime` | string | `"generic"` | Runtime family; selects the adapter. |
| `model_path` | string | `null` | Single-model path (for single-model servers). |
| `model_format` | enum | `null` | Weight format. |
| `base_url` | URL | `null` | Explicit endpoint, if not derived from the port. |
| `port` | int (1–65535) | `null` | Host port to publish. |
| `groups` | list[string] | `[]` | Coven groups this stone joins. |
| `devices` | list[string] | `[]` | Device passthrough (e.g. GPUs). |
| `security_label_disable` | bool | `false` | Disable SELinux labeling for mounts. |
| `volumes` | list[string] | `[]` | Volume mounts. |
| `env_vars` | dict | `{}` | Environment variables. |
| `secret_env_files` | dict | `{}` | Secret-file environment mappings (names, not values). |
| `exec` | list[string] | `[]` | Container command/args. |
| `models` | list of `[[models]]` | `[]` | Declared models (below). |
| `generation` | `[generation]` table | `null` | Default generation profile for this stone. |

The `[concurrency]` table (`ConcurrencyIntent`) governs lifecycle:

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `dedicated` | bool | — | LychD owns this runtime's lifecycle (may start/stop/swap it). Only `dedicated` animators can be evicted for a swap. |
| `persistent_resident` | bool | — | Pin the runtime resident — keep it out of the default eviction set and survive swaps. |

## The `[[models]]` blocks

One array-of-tables entry per model the service serves. Each yields a capability spec.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | string (required) | — | Model id; last segment of the capability key. |
| `path` | path (required) | — | Model path, resolved against `model_root`. |
| `description` | string | `null` | Human note. |
| `format` | enum | `null` | Weight format override. |
| `tags` | list[string] | `[]` | Freeform tags. |
| `[models.capabilities]` | table | `null` | Capability hints (below). |
| `[models.generation]` | table | `null` | Per-model generation overrides. |

### `[models.capabilities]` — capability hints

Hints are **authoritative for routing**: a live probe may downgrade a declared capability
but can never invent one. See the declare-then-verify doctrine in the
[Dispatcher (22)](../../adr/22-dispatcher.md).

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `families` | list of families | `null` | Explicit family list; overrides synthesis. Values: `chat`, `vision`, `embedding`, `stt`, `tts`, `tool_execution`, `rerank`. |
| `surface` | enum | `null` | Model surface kind. |
| `modalities_in` | list[string] | `null` | Admitted inputs: `text`, `image`, `audio`. |
| `modalities_out` | list[string] | `null` | Emitted outputs. |
| `supports_tools` | bool | `null` | Whether the model can call tools. |
| `supports_streaming` | bool | `null` | Whether the model streams. |

!!! warning "image-in is not the Eye"
    Declaring `modalities_in = ["text", "image"]` enriches a `chat` model's admission — it
    does **not** make it the `vision` family. The dedicated `vision` family is reserved for
    a purpose-built vision-analysis provider and must be declared explicitly with
    `families = ["vision"]`. This is the [two-axis law](../../sepulcher/animator/capabilities.md).

## The `[generation]` table

Default generation parameters. Applies at three levels, each overlaying the last: runtime
defaults, then the stone's `[generation]`, then a model's `[models.generation]`. Every field
is optional; only what you set overrides.

| Field | Type | Range | Description |
| :--- | :--- | :--- | :--- |
| `max_context` | int | ≥ 1 | Total context window. |
| `max_tokens` | int | ≥ 1 | Maximum tokens generated per response. |
| `temperature` | float | 0.0–2.0 | Sampling temperature. |
| `top_p` | float | 0.0–1.0 | Nucleus sampling threshold. |
| `top_k` | int | ≥ 0 | Top-k sampling. |
| `repetition_penalty` | float | ≥ 0.0 | Repetition penalty. |
| `reasoning_format` | string | — | Reasoning-output format hint. |

## Examples

### A `llama.cpp` router (DYNAMIC, multi-model)

The router loads models on demand, so its capabilities are `DYNAMIC`:

```toml
name = "atelier"
description = "Reference multi-model atelier soulstone (llama.cpp router ⇒ DYNAMIC)."
groups = ["atelier"]
startup_mode = "router"
models_dir = "/models"

[concurrency]
dedicated = true
persistent_resident = false

[generation]
max_tokens = 2048
temperature = 0.7

[[models]]
id = "qwen3-vl-8b"
path = "/models/qwen3-vl-8b"
description = "Multimodal chat model (image-in enriches the CHAT admission filter)."

[models.capabilities]
modalities_in = ["text", "image"]
supports_tools = true

[[models]]
id = "bge-m3"
path = "/models/bge-m3"
description = "Embedding model (explicit family)."

[models.capabilities]
families = ["embedding"]

[[models]]
id = "the-eye"
path = "/models/the-eye"
description = "Explicit VISION capability (the Eye)."

[models.capabilities]
families = ["vision"]
modalities_in = ["text", "image"]

[models.generation]
max_tokens = 512
```

This yields exactly three capabilities: `atelier:chat:qwen3-vl-8b` (image admitted, tools),
`atelier:embedding:bge-m3`, and `atelier:vision:the-eye` — all `DYNAMIC`.

### A single-model vLLM server (STATIC)

A server pinned to one model is `STATIC` — reachable means warm, no activation step:

```toml
name = "glm"
description = "Reference static vLLM soulstone (reachable ⇒ WARM)."
image = "vllm/vllm-openai:latest"
model_path = "/models/GLM-4.6.gguf"
port = 8000
groups = ["glm"]

exec = [
  "serve", "/models/GLM-4.6.gguf",
  "--served-model-name", "GLM-4.6",
  "--host", "0.0.0.0", "--port", "8000",
]
```

This yields `glm:chat:GLM-4.6` (`STATIC`).
