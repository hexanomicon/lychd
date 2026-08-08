---
title: Soulstone Rune
icon: material/script-text
---

# :material-script-text: Soulstone Rune

A **Soulstone Rune** is compiler input: one validated TOML document describing a local service.
It is neither live state nor a generated Quadlet. Concrete instances live beneath a registered
leaf runtime schema:

```text
~/.config/lychd/runes/animator/soulstones/<runtime>/<instance>.toml
```

The abstract Animator and Soulstone branches cannot own TOML files. Folder ancestry selects the
Rune type; no `type=` field may switch it after discovery.

In code, the Rune combines Animator-owned identity and capability intent with an embedded
`quadlet: QuadletConfig` value. That nested value owns the common image invariant only. Soulstone
keeps its own runtime, endpoint, resource, secret, and lifecycle policy, and the generated
`QuadletContainer` remains a separate Bind/Scribe artifact.

## The Runtime Shape

| Field | Default | Office |
| :--- | :--- | :--- |
| `name` | required | Animator identity; first segment of every capability key. |
| `description` | `""` | Operator note. |
| `quadlet.image` | runtime default | OCI image inside the embedded `QuadletConfig`; required by the generic runtime. |
| `runtime` | `"generic"` | Selects the local runtime adapter. |
| `model_path` | `null` | Single-model artifact path or runtime-specific identity input. |
| `served_model_id` | `null` | Exact provider-facing id returned by live model inventory; required when it differs from the path basename or Soulstone name. |
| `base_url` | derived | Connector endpoint override. |
| `port` | assigned | Unique host port; derives `http://localhost:{port}/v1`. |
| `groups` | `[]` | Compatible [Coven](../coven.md) target membership. |
| `devices` | `[]` | Explicit device passthrough. |
| `volumes` | `[]` | Explicit host-to-container mounts. |
| `env_vars` | `{}` | Non-secret environment values. |
| `secret_env_files` | `{}` | Environment names mapped to Podman secret names. |
| `exec` | `[]` | Complete command override; bypasses adapter synthesis. |
| `models` | `[]` | Declared model catalogue. |
| `generation` | `null` | Service-wide generation overlay. |

Runtime leaves may add typed fields such as `extra_args` or llama.cpp `startup_mode`. Adapter
defaults are followed by typed overrides; explicit `exec` replaces synthesized arguments rather
than extending them.

## Capability declarations

The accepted general-service shape adds first-class `[[capabilities]]` entries. A declaration
references one registered `interface_id` and immutable `profile_ref` (stable id plus revision or digest), selects its permitted
operations, and pins the driver/dialect, evidence, resource envelope, and containment profile for
this instance. A Rune may supply endpoint, secret reference, lifecycle, and explicit admitted
overlays; it cannot rewrite the referenced profile's request/result schemas, licenses, formats,
languages, or proved limits.

The following model catalogue is the currently delivered v1 compatibility path, not the universal
service schema.

### Declared models become v1 capabilities

Each `[[models]]` block names a stable `id`, an explicit container-side `path`, an optional
description and format, capability hints, and a per-model generation overlay. It yields capability
identity `{animator}:{family}:{model_id}`.

`[models.capabilities]` may declare:

- `families`: `chat`, `vision`, `embedding`, `stt`, `tts`, `tool_execution`, or `rerank`;
- `modalities_in` and `modalities_out`: `text`, `image`, or `audio`; and
- `supports_tools` and `supports_streaming`.

These hints are authoritative for routing. A live probe may downgrade availability or fill an
explicitly open runtime fact; it may not invent an undeclared model or family. Image input enriches
a `chat` capability and does not create the dedicated `vision` family. The full two-axis law lives
in [Capabilities](../capabilities.md).

Every Soulstone must synthesize at least one capability through its adapter. An unrecognised
generic runtime remains passive. It becomes routable only through a registered adapter or an
explicit OpenAI-compatible alias with defined binding semantics. In the general-service shape,
non-model services use `[[capabilities]]`; they do not fake a model declaration. Compatibility is
claimed separately for each named [Connector dialect](../connectors.md#openai-compatibility-is-per-dialect).

## Generation Overlays

Generation fields are optional: `max_context`, `max_tokens`, `temperature`, `top_p`, `top_k`,
`repetition_penalty`, and `reasoning_format`. Effective values overlay in this order:

```text
runtime defaults → Soulstone [generation] → [models.generation]
```

The accepted ranges are `max_context`/`max_tokens ≥ 1`, `temperature` 0–2, `top_p` 0–1,
`top_k ≥ 0`, and `repetition_penalty ≥ 0`.

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
promise that the complete union may coexist. `alliances` is accepted shape without enforcement
authority. Neither changes the conflict graph, reserves hardware, or asks for semantic dispatch.

## Refusal and Handoff

The complete Rune generation validates before any unit is written. Duplicate identity, invalid
ports, missing named secrets, unsafe mounts, an internally conflicting Coven, or an unauthorized
conflict declaration fails closed. [Configuration](../../../adr/12-configuration.md) owns Rune
discovery and validation; [Containers](../../../adr/08-containers.md) owns projection;
[Orchestrator](../../../adr/23-orchestrator.md) owns transitions.
