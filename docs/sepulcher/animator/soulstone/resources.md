---
title: Soulstone Resources and Secrets
icon: material/shield-key
---

# :material-shield-key: Soulstone Resources and Secrets

A Soulstone receives an explicit slice of local substrate. Its Rune may name devices, ports,
volumes, non-secret environment, and Podman secret references. It gains no blanket Crypt, model
shelf, host socket, or credential authority from being local.

## Explicit Local Substrate

`devices` passes named hardware into the container. `volumes` maps exact host paths to exact
container paths. Model artifacts must be reachable through a declared Rune or
adapter-contributed mount; there is no implicit host `model_root`.

Before admitting a mount, the protected-root gate checks both ends. Each must be absolute.
It resolves host symlinks before comparison and emits a safe alias as its canonical target.
Neither end may equal, contain, or sit beneath the Codex, Crypt, Reactor, or user-systemd binding
roots. Percent signs, backslashes, and non-printable characters also cause rejection.

## Secret Hydration

`secret_env_files` maps an environment-variable name to a Podman secret name. This schematic
example demonstrates that mapping; an admitted engine profile must separately pin its image:

```toml
name = "private-runtime"
runtime = "vllm"
model_path = "/models/qwen-awq"

[quadlet]
image = "vllm/vllm-openai:latest"

[secret_env_files]
HF_TOKEN_FILE = "hf_runtime_token"
```

Binding first checks that `hf_runtime_token` exists, without reading its contents. Missing secrets
or failed existence probes refuse the bind. A successful bind emits `Secret=hf_runtime_token`
in the Quadlet, making `HF_TOKEN_FILE=/run/secrets/hf_runtime_token` available inside the container.
The Codex retains the name; rootless Podman's secret store retains the value. Recreate the
consuming container after replacing that value.

## The Port Singularity

!!! warning "Every Soulstone must listen on a unique host port"
    Reusing a port can fail a transition with `Address already in use`.

A Soulstone may omit both `port` and `base_url`; loading assigns a unique local port and derives
`http://localhost:{port}/v1`. Explicit values win, and host publication remains loopback-bound.

## Owners and Refusal

[Configuration](../../../adr/12-configuration.md) owns secret references and Rune validation;
[Layout](../../../adr/13-layout.md) owns protected geography; and
[Containers](../../../adr/08-containers.md) owns unit-scoped mounts, devices, and secrets.
[Security](../../../adr/09-security.md) owns the trust boundary they defend. Repair the rejected
declaration and bind again. Do not edit generated units to bypass a refusal.
