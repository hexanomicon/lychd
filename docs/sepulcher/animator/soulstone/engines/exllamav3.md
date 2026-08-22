---
title: ExLlamaV3 through TabbyAPI
icon: material/memory
---

# :material-memory: ExLlamaV3 through TabbyAPI

**ExLlamaV3 is the inference library; TabbyAPI is its official OpenAI-compatible server.** LychD
keeps that server outside the daemon dependency graph and registers it as the dynamic
`animator/exllamav3` Soulstone runtime.

The generated sample pins the TabbyAPI image by digest. The container starts without a model, so
its declared capabilities become `ACTIVATABLE`, not `WARM`. LychD sends the declared model
directory and backend through Tabby's lifecycle API; context, cache, split, and reserve remain
TabbyAPI defaults unless a model-local `tabby_config.yml` overrides them.

Stable LychD `[[models]].id` values are not Tabby directory names. Each model `path` must identify a
validated direct child of the mounted model directory. The connector derives the runtime name from
that path's basename and translates it on both lifecycle and data planes.

Authentication is mandatory even inside the unpublished private pod. The two distinct API and
admin keys remain Podman-secret material and are never placed in browser code or ordinary Rune
fields. `bind --uncaged` rejects this Soulstone.

`POST /v1/model/load` reports stages over server-sent events. LychD consumes the complete stream
and verifies the active model with `GET /v1/model`; a disconnected client alone is not proof that a
detached load failed. An indeterminate stream remains contained and is reconciled or reset through
the owning Vessel boundary.

Focused contracts cover the runtime, control plane, connector, registration, authentication, and
containment behavior. The named GPU/model/runtime receipt remains
[operator validation](../../../../state-of-the-work.md#exllamav3-tabbyapi).

See [ExLlamaV3](https://github.com/turboderp-org/exllamav3),
[TabbyAPI](https://github.com/theroyallab/tabbyAPI), and
[Soulstone Disciplines](../disciplines.md).
