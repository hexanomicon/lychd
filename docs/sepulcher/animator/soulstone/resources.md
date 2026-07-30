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
container paths. Model artifacts must be reachable through a declared global, Rune, or
adapter-contributed mount; there is no implicit host `model_root`.

Every contributed mount passes one protected-root gate. Both endpoints must be absolute. Host
symlinks resolve before comparison, and a safe alias is emitted as its canonical target. Neither
endpoint may equal, contain, or sit beneath the Codex, Crypt, Reactor, or user-systemd binding
roots. Percent signs, backslashes, and non-printable characters are rejected.

## Secret Hydration

`secret_env_files` maps an environment-variable name to a Podman secret name:

```toml
name = "private-runtime"
runtime = "vllm"
image = "vllm/vllm-openai:latest"
model_path = "/models/qwen-awq"

[secret_env_files]
HF_TOKEN_FILE = "hf_runtime_token"
```

Binding first proves that `hf_runtime_token` exists. The generated Quadlet emits
`Secret=hf_runtime_token`, and the container receives
`HF_TOKEN_FILE=/run/secrets/hf_runtime_token`. The Codex stores only the name; the value remains
in rootless Podman's secret store. Binding verifies only that the named Podman secret exists; it
does not inspect its contents. A missing name or failed existence probe refuses binding. Replacing
a secret requires recreation of the consuming container.

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
