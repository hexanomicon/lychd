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

Keep the identity used by LychD separate from the directory TabbyAPI loads. A stable
`[[models]].id` names the LychD model; its `path` must name a validated direct child of the mounted
model directory. The Connector takes that path's basename as Tabby's runtime name and translates
between them for both lifecycle control and data calls.

The current LychD TabbyAPI adapter executes the Chat Completions surface. A model declaration
with `capabilities.surface = "responses"` is rejected at Rune validation because that surface is
outside this adapter's admitted contract.

Authentication is mandatory even inside the unpublished private pod. The two distinct API and
admin keys remain Podman-secret material and are never placed in browser code or ordinary Rune
fields. Core binds only the managed container Vessel; the former `bind --uncaged` option is retired.

Follow model loading through the whole `POST /v1/model/load` server-sent-event stream, then
verify the active model with `GET /v1/model`. LychD performs both steps because a disconnected
client cannot establish that a detached load failed. An indeterminate stream keeps the result
contained for reconciliation or reset through the owning Vessel boundary.

Focused contracts cover the runtime, control plane, connector, registration, authentication, and
containment behavior. The named GPU/model/runtime receipt remains
[operator validation](../../../../state-of-the-work.md#exllamav3-tabbyapi).

See [ExLlamaV3](https://github.com/turboderp-org/exllamav3),
[TabbyAPI](https://github.com/theroyallab/tabbyAPI), and
[Soulstone Disciplines](../disciplines.md).
