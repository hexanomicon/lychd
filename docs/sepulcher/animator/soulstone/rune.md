---
title: Soulstone Rune
icon: material/script-text
---

# :material-script-text: Soulstone Rune

A **Soulstone Rune** is compiler input: one validated TOML document describing a local service.
It is neither live state nor a generated Quadlet. Concrete instances live beneath a registered
leaf runtime schema, relative to the active [Codex](../../codex.md) root:

```text
runes/animator/soulstones/<runtime>/<instance>.toml
```

Codex defaults to `~/.config/lychd/`; `XDG_CONFIG_HOME` changes that prefix.

The abstract Animator and Soulstone branches cannot own TOML files. Folder ancestry selects the
Rune type; no `type=` field may switch it after discovery.

## The Runtime Shape

| Field | Default | Office |
| :--- | :--- | :--- |
| `name` | required | Animator identity; first segment of every capability key. |
| `description` | `""` | Operator note. |
| `quadlet.image` | runtime default | OCI image inside the embedded `QuadletConfig`; required by the generic runtime. |
| `runtime` | `"generic"` | Selects the local runtime adapter. |
| `model_path` | `null` | Single-model artifact path or runtime-specific identity input. |
| `served_model_id` | `null` | For an inferred single model, set the exact provider-facing id when it differs from the path stem (basename without its final suffix), or the Soulstone name if no path is set. |
| `base_url` | derived | Connector endpoint root; credentials, query, fragment, and invalid ports are refused. |
| `port` | assigned | Unique host port; derives `http://localhost:{port}/v1`. |
| `groups` | `[]` | Compatible [Coven](../coven.md) target membership. |
| `devices` | `[]` | Explicit device passthrough. |
| `volumes` | `[]` | Explicit host-to-container mounts. |
| `env_vars` | `{}` | Non-secret environment values. |
| `secret_env_files` | `{}` | Environment names mapped to Podman secret names. |
| `exec` | `[]` | Complete command override; bypasses adapter synthesis. |
| `models` | `[]` | Declared model catalogue; a non-empty table is the exact admitted id allowlist. |
| `generation` | `null` | Service-wide generation overlay. |

Runtime leaves may add typed fields such as `extra_args` or llama.cpp `startup_mode`. Adapter
defaults are followed by typed overrides; explicit `exec` replaces synthesized arguments rather
than extending them.

Choose the Rune directory for the adapter you intend to use. Each built-in runtime leaf pins
its `runtime` literal, so a llama.cpp, vLLM, SGLang, or ExLlamaV3 file cannot select a different
adapter merely by changing that field.

Then check the endpoint. `base_url` preserves a path prefix such as `/v1`, but rejects embedded
credentials, query or fragment state, port zero, and out-of-range ports during validation.
Hydration also requires an approved loopback host and an explicit port. If `port` is declared
separately, it must match the URL. Remote endpoints belong at the Portal boundary.

## Capability declarations

The model catalogue below is the current v1 compatibility path. General service declarations remain
[Designed](#general-service-declarations).

### Declared models become v1 capabilities

Give each `[[models]]` block a stable `id`, an explicit container-side `path`, and, as needed,
a format, capability hints, and a per-model generation overlay. The resulting capability is
identified as `{animator}:{family}:{model_id}`. Duplicate ids refuse validation.

Once any model blocks exist, their ids form the entire admitted catalogue in declaration order.
Discovery cannot add an undeclared id. A declared id missing from discovery stays declared but
may be downgraded by readiness evidence. This lets you distinguish what was authorized from what
the service currently reports.

`[models.capabilities]` may declare:

- `families`: `chat`, `vision`, `embedding`, `stt`, `tts`, `tool_execution`, or `rerank`;
- `surface`: `chat` or `responses`, selecting the connector's admitted API surface;
- `modalities_in`, such as `text`, `image`, or `audio`; and
- `supports_tools`.

These hints are authoritative for routing. A live probe may downgrade availability or fill an
explicitly open runtime fact; it may not invent an undeclared model. An explicit `families` list is
closed. When that field is omitted, the current catalogue synthesizes `chat`; other families
require an explicit declaration. Image input enriches a `chat` capability and does not create the dedicated
`vision` family. The full two-axis law lives in [Capabilities](../capabilities.md).

The declared model is only one part of an application path. Bridge currently accepts text and
needs tool support for its structured reply. It supplies no image/audio upload or materializer,
and the v1 grant cannot execute the `vision`, `embedding`, `rerank`, `stt`, or `tts` families.
An image-capable model therefore cannot by itself add image input to Bridge. Output modalities,
streaming hints, and model descriptions are also absent from the current Rune schema and fail
validation.

An empty `models` list is not the Portal zero-capability rule. A Soulstone adapter may instead use
its runtime/discovery model catalogue or derive one model id from `served_model_id`, `model_path`,
or the Soulstone name. A non-empty list remains the exact allowlist.

Every admitted Soulstone must synthesize at least one capability through its adapter. An
unrecognised generic runtime remains passive at the adapter boundary, but registry generation
refuses that Soulstone until a registered adapter or explicit OpenAI-compatible alias with defined
binding semantics yields a capability. In the general-service shape, non-model services use
`[[capabilities]]`; they do not fake a model declaration. Compatibility is claimed separately for
each named [Connector dialect](../connectors.md#openai-compatibility-is-per-dialect).

## Generation Overlays

The common optional generation fields are `max_context`, `max_tokens`, `temperature`, and
`top_p`. Effective values overlay in this order:

```text
runtime defaults → Soulstone [generation] → [models.generation]
```

The accepted ranges are `max_context`/`max_tokens ≥ 1`, finite `temperature` 0–2, and finite
`top_p` 0–1. Other generation keys fail validation apart from the model-local policy below.
The overlay bounds request settings; it does
not resize a running engine. llama.cpp's managed `n_ctx` is reflected from its actual generated
command before the explicit generation overlays apply.

For an explicit local vLLM `Qwen3.8-27B` model using Chat, the model's generation block may also
select the closed policy `thinking = "qwen3.8-non-thinking"`. It sends the supported template
argument `enable_thinking = false` through that model's grant; it changes neither the running
server's launch defaults nor sibling models. Omit it to retain ordinary behavior. It is refused in
runtime or Soulstone-wide defaults, Portals, other models/runtimes and Responses. Arbitrary
`extra_body`, a generic boolean and unknown policy tags are not accepted Rune inputs. This mode
selection does not guarantee useful output or increase the existing output/call budget. Follow
[vLLM](./engines/vllm.md) for the engine boundary and
[State of Work](../../../state-of-the-work.md#vllm-integration) for delivery evidence.

Bridge normally requests a tool-capable chat grant from Dispatcher's eligible pool. To pin one
exact current v1 capability for new turns, follow the
[`[weaver.bridge]` selector](../../extensions/weaver/index.md#choose-a-bridge-capability).
Dispatcher still checks compatibility, readiness, and policy; a refused target never falls back.
`[orchestration.routing]` selects only physical queue and priority.

## Concurrency Intent

The `[concurrency]` table separates lifecycle authority from coexistence:

| Field | Meaning |
| :--- | :--- |
| `dedicated` | LychD owns lifecycle and may start, stop, or evict the runtime. |
| `persistent_resident` | Keep the runtime resident and outside every eviction set. |
| `conflict_domains` | Finite hardware domains this managed runtime cannot share. |

Omitting `conflict_domains` on a dedicated non-resident requests the compiler-owned
`default-exclusive` wildcard. Explicit `[]` alone asserts coexistence. A shared
(`dedicated = false`) or persistent-resident Soulstone may omit the field or declare `[]`; a
non-empty set fails binding because LychD may neither evict the shared runtime nor compile an edge
that could evict a resident. Labels are lowercase identifiers of at most 50 characters; operators
must not spell `default-exclusive` directly.

`groups` requests compatible aggregation, and one Rune may name several groups. That means the
same service participates in several operator formations; it does not duplicate the instance or
promise that the complete union may coexist. `alliances` is not an accepted Rune field. Groups
do not change the conflict graph, reserve hardware, or ask for semantic dispatch.

## Schema and process generation

The Rune brings together Animator identity and capability intent with an embedded
`quadlet: QuadletConfig`. The nested value supplies only the common image invariant. Soulstone
and Phoenix can both embed it under `quadlet` without sharing a Domain or Rune ancestry; future
Tether or Veil Runes may do the same.

Soulstone still owns runtime, endpoint, resource, secret, and lifecycle policy. Binding and Scribe
produce the separate `QuadletContainer` artifact. Sharing a configuration value cannot transfer
those responsibilities.

Loaded Rune values are immutable through their nested models, sequences, and string maps. Change
the TOML and construct a new process generation; do not mutate an admitted object in place. Rune
writing uses the same exact schema generation admitted by loading, rather than every imported
Python subclass, so an unregistered branch cannot leak into generated configuration.

## General-service declarations

The accepted general-service shape adds first-class `[[capabilities]]` entries. A declaration
references one registered `interface_id` and immutable `profile_ref` (stable id plus revision or digest), selects its permitted
operations, and pins the driver/dialect, evidence, resource envelope, and containment profile for
this instance. A Rune may supply endpoint, secret reference, lifecycle, and explicit admitted
overlays; it cannot rewrite the referenced profile's request/result schemas, licenses, formats,
languages, or proved limits.

## Refusal and Handoff

The complete Rune generation validates before any unit is written. Duplicate identity, invalid
ports, missing named secrets, unsafe mounts, an internally conflicting Coven, or an unauthorized
conflict declaration fails closed. [Configuration](../../../adr/12-configuration.md) owns Rune
discovery and validation; [Containers](../../../adr/08-containers.md) owns projection;
[Orchestrator](../../../adr/23-orchestrator.md) owns transitions.
