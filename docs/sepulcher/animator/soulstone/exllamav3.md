---
title: ExLlamaV3 through TabbyAPI
icon: material/flash
---

# :material-flash: ExLlamaV3 through TabbyAPI

**ExLlamaV3 is the inference library; TabbyAPI is its official OpenAI-compatible server.** LychD
keeps that server outside the daemon dependency graph and registers it as the dynamic
`animator/exllamav3` Soulstone runtime.

## The Dynamic Local Contract

The generated sample pins the TabbyAPI image by digest. The container starts without a model, so
its declared capabilities become `ACTIVATABLE`, not `WARM`. LychD sends the declared model
directory and backend through Tabby's lifecycle API; context, cache, split, and reserve remain
TabbyAPI defaults unless a model-local `tabby_config.yml` overrides them.

Stable LychD `[[models]].id` values are not Tabby directory names. Each model `path` must identify a
validated direct child of the mounted model directory. The connector derives the runtime name from
that path's basename and translates it on both lifecycle and data planes.

## Seal the Two Keys

Authentication is mandatory even inside the unpublished private pod. `auth_secret_name` names one
Podman secret containing strict JSON with distinct `api_key` and `admin_key` values, each at least
32 printable ASCII characters:

```toml
name = "exl3"
volumes = ["/data/models:/app/models:ro"]
auth_secret_name = "tabby_exl3_auth"

[[models]]
id = "daily-driver"
path = "/app/models/qwen-exl3"
format = "EXL3"
```

Create the referenced secret from a protected JSON document:

```text
{"api_key":"<32+-char-data-key>","admin_key":"<different-32+-char-admin-key>"}
```

The secret is mounted only into TabbyAPI and the trusted Vessel. `bind --uncaged` rejects this
Soulstone. Replacing the Podman secret does not update an existing container; rotate both keys by
recreating the Vessel and this Soulstone together.

## Observe the Whole Activation

`POST /v1/model/load` reports several stages over server-sent events. LychD consumes the complete
stream and then verifies the active model with `GET /v1/model`; a disconnected client alone is not
proof of failure because TabbyAPI continues a detached load.

The outcomes differ deliberately:

- a valid terminal stream followed by no active model is a completed-but-lost runtime epoch, so
  LychD releases the mutation fence;
- a mid-stream transport loss cannot prove settlement and becomes a contained `ERROR`.

After the second outcome, restart the caged Vessel. TabbyAPI is bound to
`lychd-vessel.service`, so that restart stops Tabby and resets the detached load and LychD's
in-memory epoch together before another attempt.

## Keep the Cage Honest

TabbyAPI writes a rotating log beneath `/app/logs` while LychD also captures stdout through
journald. Its Quadlet mounts that path as ephemeral mode-1777 tmpfs. Logging is pinned above INFO
because Tabby's upstream INFO level prints raw authentication keys.

ExLlamaV3, vLLM, and SGLang request shared memory explicitly; the pod sums their requirements as a
lazy tmpfs ceiling. None of those declarations proves VRAM fit.

Focused contracts cover the runtime, control plane, connector, registration, authentication, and
containment behavior. The named GPU/model/runtime receipt remains
[operator validation](../../../state-of-the-work.md#exllamav3-tabbyapi); transition authority and
containment belong to the [Orchestrator](../../../adr/23-orchestrator.md).
