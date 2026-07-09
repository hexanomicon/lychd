---
title: Capabilities
icon: material/lightning-bolt-circle
---

# :material-lightning-bolt-circle: Capabilities

Every [Animator](index.md) advertises what it can do as a set of **capabilities**. A
capability is a typed contract — "this service can do `chat`", "this one can do
`embedding`" — that the [Dispatcher](../../adr/22-dispatcher.md) resolves a request
against. This page explains, for a Magus, how a capability comes to be ready and what the
states on the [Nexus](../../divination/altar/nexus.md) mean. The canonical definitions live
in the [Dispatcher (22)](../../adr/22-dispatcher.md).

## The two axes: family and modalities

A capability is described along two orthogonal axes, and LychD never conflates them:

- **Family** — the *kind of service*: `chat`, `vision`, `embedding`, `stt`, `tts`,
  `tool_execution`, `rerank`.
- **Modalities** — what a request *admits and emits*: `text`, `image`, `audio`.

There is deliberately **no audio family**. A chat model that can hear is `chat` with
`audio` in its input modalities; a chat model that can see is `chat` with `image` in its
input modalities. The dedicated `vision` family (the Eye) is reserved for a purpose-built
vision-analysis provider that you declare explicitly — a multimodal chat model that happens
to accept images is still `chat`. This keeps routing honest: a request matches on
`(family, required modalities)`, and image-in never silently promotes a chat model into the
Eye.

## `is_dynamic` vs phase

Each capability carries an **`is_dynamic` flag** (a fixed property of how it becomes ready)
and projects a **phase** (its live readiness right now). These are independent.

### `is_dynamic` — how it becomes ready

- **`is_dynamic=False`** — the runtime is ready as soon as its endpoint is reachable. The
  server binds its port only after the model is loaded, so a reachable endpoint *is* a warm
  capability. Remote [Portals](portal.md) and single-model local servers (for example a
  vLLM server pinned to one model) have `is_dynamic=False`.
- **`is_dynamic=True`** — the container is up, but the specific model needs an in-runtime
  activation step before it can serve (for example a `llama.cpp` router that loads a model
  on demand). A capability with `is_dynamic=True` can be *awaited* and then activated
  without restarting the container.

!!! note "The old names are gone"
    An earlier draft used `FIXED`/`AWAITED` for this property, then a `STATIC`/`DYNAMIC`
    enum. The shipped representation is a plain `is_dynamic: bool`; the legacy
    `dynamic_soft` string normalizes to `is_dynamic=True`.

### Phase — whether it is ready now

The live readiness ladder, in order:

| Phase | Meaning |
| :--- | :--- |
| `COLD` | Unit down or endpoint unreachable. |
| `ACTIVATABLE` | Unit up; a model with `is_dynamic=True` is not yet loaded. |
| `WARMING` | Activation in flight. |
| `WARM` | Requests accepted now. |
| `ERROR` | The capability is faulted. |
| `UNKNOWN` | State not yet observed. |

The [Nexus](../../divination/altar/nexus.md) renders these as operator words: `WARM`
shows as **active**, `WARMING` as **warming**, an `ACTIVATABLE` capability with
`is_dynamic=True` as **awaited**, `COLD`/(`ACTIVATABLE`-with-`is_dynamic=False`) as **cold**,
and `ERROR` as **fault**.

Two derived questions intentionally differ. `is_active` means this model capability is loaded or
loading (`WARM`/`WARMING`). `runtime_started` means the owning local service is physically up and
also includes `ACTIVATABLE`. Host-transition stale-state checks use `runtime_started`, so an idle
dynamic router and `systemctl is-active` describe the same physical world even before a model is
loaded.

## How a request drives readiness

When a run requests a family, the Dispatcher reads the resolved capability's phase and acts:

- **WARM** — grant it immediately.
- **ACTIVATABLE** — raise the typed readiness signal; the Orchestrator closes admission for the
  whole Animator, drains all same-Animator leases, then soft-activates the model without restarting
  the container. It waits for warm before retry; failure stays closed because v1 has no honest
  model-level inverse.
- **WARMING** — raise the same readiness signal so the Orchestrator owns the bounded wait; retry
  dispatch only after convergence.
- **COLD** (and LychD owns the lifecycle) — raise a hardware transition, so the Orchestrator
  performs a coven swap; the run parks until the substrate is ready, then resumes.
- **COLD** (not owned) or **ERROR** — the capability is unavailable, and the run settles
honestly rather than hanging.

The bounded wait has one absolute `warmup_timeout_s` deadline. `estimated_ready_ms` may delay the
first probe adaptively, but it and every later poll sleep are capped to remaining time; an estimate
never adds a second timeout budget.

For the operator's view of these transitions, see
[Coven](./coven.md) and the [Nexus](../../divination/altar/nexus.md).

## Declaring capabilities

A capability's identity is the key `{animator}:{family}:{model_id}`. Capabilities are
synthesized from your rune declarations (the `[[models]]` blocks of a
[Soulstone Rune](./soulstone.md#soulstone-rune-reference) or [Portal Rune](./portal.md#portal-rune-reference))
and, for local runtimes, enriched by a live probe of what the server reports.

Declaration is authoritative for *routing*: a rune hint always wins. A live probe may only
*downgrade* — mark a declared capability temporarily unavailable — never invent one a rune
did not declare. Verification tightens; it never loosens.

**For the builder:** the capability ontology, the two-axis law, the declare-then-verify
doctrine, and the grant/lease model are specified in the
[Dispatcher (22)](../../adr/22-dispatcher.md) and
[Orchestrator (23)](../../adr/23-orchestrator.md).
