---
title: Runtime Plan
icon: material/map-outline
---

# :material-map-outline: llama.cpp + vLLM Runtime Plan

This blueprint locks one rule:
- `exec` is explicit passthrough authority.
- typed fields are managed authority.
- the two modes must never be mixed in one Soulstone.

## Current Contract

- `LlamaCppSoulstone` validates:
  - passthrough mode rejects managed runtime fields.
  - single mode requires `model_path`.
  - router mode requires `models_dir`/`models_preset` (or equivalent router flags/env).
- `VllmSoulstone` validates:
  - passthrough mode rejects managed runtime fields.
  - managed mode requires `model_path` or explicit `models`.
- `RuntimePlan` now carries:
  - `exec_args`
  - `env_overrides`
  - `volumes`
  - `podman_args`
- `Transmuter` applies adapter `podman_args` and merges them with base `--replace`.
- Soulstones can declare `secret_env_files` for bind-time Podman secret checks and env hydration (`ENV=/run/secrets/<name>`).

## Deployment Shape

One runtime instance per Soulstone. Many servers means many Soulstones:
- `animator/soulstones/llamacpp/*.toml`
- `animator/soulstones/vllm/*.toml`
- `animator/soulstones/sglang/*.toml`

Use `groups` to express coexistence and exclusivity policy.

## Phase Plan

1. Contract Freeze
- Keep passthrough vs managed validation strict.
- Add tests for every conflict path and required-field path.
- Reject silent inference when a required startup source is missing.

2. llama.cpp Server Mode
- Keep dual-mode startup (`single`/`router`) behind `startup_mode`.
- In managed mode, synthesize deterministic flags from typed fields first.
- Append `extra_args` last for explicit user override.
- Keep runtime metadata inference (`mode`, `provider`, defaults) for control-plane introspection.

3. vLLM Mode
- Keep managed mode centered on `serve <model_ref>`.
- Keep container-level toggles as `podman_args` (`--ipc=host`, optional `--network=host`).
- Keep runtime args deterministic, append `extra_args` last.
- Add tests for mixed passthrough/managed, missing model source, and podman arg propagation.

4. Binder/Registry Expansion
- Treat llama.cpp/vLLM/SGLang as OpenAI-compatible connector surfaces by default.
- Keep runtime-specific connectors optional and additive.
- For vision/STT, introduce runtime-specific Soulstone subclasses only when flags diverge materially from text serving.

## Manual Operator Steps

1. Inscribe one TOML per runtime instance.
2. Create Podman secrets for any `api_key_secret` / `secret_env_files` references.
3. Run `make bind`.
4. Start selected services/targets.
5. Verify local health (`/v1/models`, `/health`) per runtime.
6. Bind dispatcher routes to active animator connectors.

## Implementation Reference

- `src/lychd/domain/animation/schemas/runes/animators.py`: rune contract for `api_key_secret` and `secret_env_files`.
- `src/lychd/cli/commands.py`: bind-time secret reconciliation and fail-closed behavior.
- `src/lychd/domain/animation/transmute.py`: Quadlet env + `Secret=` hydration.
- `src/lychd/system/templates/container.jinja`: final `Secret=` directive rendering.
- `src/lychd/config/settings.py`: startup fallback generation for internal app/db secrets.

## Non-Goals

- No hidden command mutation after validation.
- No adapter magic that overrides explicit `exec`.
- No provider-specific hard-coding in domain orchestration logic.
