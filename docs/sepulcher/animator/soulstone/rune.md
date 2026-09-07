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
| `served_model_id` | `null` | Exact provider-facing id returned by live model inventory; required when it differs from the path basename or Soulstone name. |
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

A concrete built-in runtime leaf pins its own `runtime` literal. A llama.cpp, vLLM, SGLang, or
ExLlamaV3 file cannot claim another adapter merely by changing that field; use the matching Rune
directory and schema. `base_url` is a composable endpoint root, so a path prefix such as `/v1` is
preserved, while embedded credentials, query or fragment state, port zero, and out-of-range ports
fail during Rune validation. Hydration additionally requires a Soulstone URL to use an approved
loopback host and an explicit port; when `port` is also declared, the two values must agree. A
non-loopback endpoint belongs at the Portal boundary.

## Capability declarations

The model catalogue below is the current v1 compatibility path. General service declarations remain
[Designed](#general-service-declarations-designed).

### Declared models become v1 capabilities

Each `[[models]]` block names a stable `id`, an explicit container-side `path`, an optional
format, capability hints, and a per-model generation overlay. It yields capability
identity `{animator}:{family}:{model_id}`. Duplicate ids fail validation. When at least one block is
present, those ids are the complete admitted catalogue in declaration order: live discovery for an
undeclared id is ignored, while a declared id absent from discovery keeps its declaration but may
be downgraded by readiness evidence.

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

These fields describe model admission, not a complete application. The current Bridge accepts
text and requires tool support for its structured reply. It has no image/audio upload or materializer,
and the `vision`, `embedding`, `rerank`, `stt`, and `tts` families have no executable v1 grant.
Selecting a model that can accept images does not add image input to Bridge. Output modalities,
streaming hints, and model descriptions are not current Rune fields and fail validation.

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

The current optional generation fields are `max_context`, `max_tokens`, `temperature`, and
`top_p`. Effective values overlay in this order:

```text
runtime defaults → Soulstone [generation] → [models.generation]
```

The accepted ranges are `max_context`/`max_tokens ≥ 1`, finite `temperature` 0–2, and finite
`top_p` 0–1. Other generation keys fail validation. The overlay bounds request settings; it does
not resize a running engine. llama.cpp's managed `n_ctx` is reflected from its actual generated
command before the explicit generation overlays apply.

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

In code, the Rune combines Animator-owned identity and capability intent with an embedded
`quadlet: QuadletConfig` value. That nested value owns the common image invariant only. Soulstone
and Phoenix embed it under `quadlet` without sharing Domain or Rune ancestry; future Tether or Veil
Runes may compose it on the same terms. Soulstone keeps its own runtime, endpoint, resource, secret,
and lifecycle policy, and the generated `QuadletContainer` remains a separate Bind/Scribe artifact.

Loaded Rune values are immutable through their nested models, sequences, and string maps. Change
the TOML and construct a new process generation; do not mutate an admitted object in place. Rune
writing uses the same exact schema generation admitted by loading, rather than every imported
Python subclass, so an unregistered branch cannot leak into generated configuration.

## General-service declarations (Designed)

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
