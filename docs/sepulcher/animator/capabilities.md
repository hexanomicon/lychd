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

## Lifecycle vs phase

Each capability carries a **lifecycle** (a fixed property of how it becomes ready) and
projects a **phase** (its live readiness right now). These are independent.

### Lifecycle — how it becomes ready

- **`STATIC`** — the runtime is ready as soon as its endpoint is reachable. The server
  binds its port only after the model is loaded, so a reachable endpoint *is* a warm
  capability. Remote [Portals](portal.md) and single-model local servers (for example a
  vLLM server pinned to one model) are `STATIC`.
- **`DYNAMIC`** — the container is up, but the specific model needs an in-runtime
  activation step before it can serve (for example a `llama.cpp` router that loads a model
  on demand). A `DYNAMIC` capability can be *awaited* and then activated without restarting
  the container.

!!! note "The old names are gone"
    An earlier draft used `FIXED`/`AWAITED` for the lifecycle. The shipped vocabulary is
    `STATIC`/`DYNAMIC`; the legacy `dynamic_soft` string normalizes to `DYNAMIC`.

### Phase — whether it is ready now

The live readiness ladder, in order:

| Phase | Meaning |
| :--- | :--- |
| `COLD` | Unit down or endpoint unreachable. |
| `ACTIVATABLE` | Unit up; a `DYNAMIC` model is not yet loaded. |
| `WARMING` | Activation in flight. |
| `WARM` | Requests accepted now. |
| `ERROR` | The capability is faulted. |
| `UNKNOWN` | State not yet observed. |

The [Nexus](../../divination/altar/nexus.md) renders these as operator words: `WARM`
shows as **active**, `WARMING` as **warming**, an `ACTIVATABLE` `DYNAMIC` capability as
**awaited**, `COLD`/`ACTIVATABLE`-on-`STATIC` as **cold**, and `ERROR` as **fault**.

## How a request drives readiness

When a run requests a family, the Dispatcher reads the resolved capability's phase and acts:

- **WARM** — grant it immediately.
- **ACTIVATABLE** — soft-activate the model (no container restart), wait for warm, then
  grant. This path never involves the Orchestrator.
- **WARMING** — wait for warm, then grant.
- **COLD** (and LychD owns the lifecycle) — raise a hardware transition, so the Orchestrator
  performs a coven swap; the run parks until the substrate is ready, then resumes.
- **COLD** (not owned) or **ERROR** — the capability is unavailable, and the run settles
  honestly rather than hanging.

For the operator's view of these transitions, see the
[Manage Covens](../../praxis/rites/manage-covens.md) rite and the
[Nexus](../../divination/altar/nexus.md).

## Declaring capabilities

A capability's identity is the key `{animator}:{family}:{model_id}`. Capabilities are
synthesized from your rune declarations (the `[[models]]` blocks of a
[Soulstone Rune](../../praxis/runes/soulstones.md) or [Portal Rune](../../praxis/runes/portals.md))
and, for local runtimes, enriched by a live probe of what the server reports.

Declaration is authoritative for *routing*: a rune hint always wins. A live probe may only
*downgrade* — mark a declared capability temporarily unavailable — never invent one a rune
did not declare. Verification tightens; it never loosens.

**For the builder:** the capability ontology, the two-axis law, the declare-then-verify
doctrine, and the grant/lease model are specified in the
[Dispatcher (22)](../../adr/22-dispatcher.md) and
[Orchestrator (23)](../../adr/23-orchestrator.md).
