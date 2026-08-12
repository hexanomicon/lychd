---
title: Portal
icon: material/weather-hurricane
---

# :material-weather-hurricane: Portal: The Rift to the Remote Sky

> _"A rift is not a rescue that opens itself. It is named, sealed, and entered under the Magus's
> authority."_

A **Portal** is a remote, API-backed [Animator](./index.md) declared by a provider-specific Rune.
It has no container and consumes no local VRAM. Its connector runs inside the trusted Vessel, where
it may read the one Podman secret explicitly mounted for it.

The credential shares that trust boundary: file permissions do not hide it from code already
executing inside the Vessel.

That delivered v1 placement is insufficient for every [Reach deployment
profile](../../compositions/reach/deployments/index.md). Reach core and the Discord edge must never
inherit the provider secret merely because services run on one host. Its Designed profiles require
a separate Provider Gate/egress-adapter service that alone holds one exact provider or peer
credential and accepts only typed, egress-admitted attempts. Until that service boundary and its
deployment receipt ship, a current Vessel-local Portal connector cannot activate as a Reach
provider path, including on the public VPS profile.

LychD does not own the remote service's lifecycle. Portal capabilities are
`dedicated=False` and `is_dynamic=False`: the Orchestrator cannot start, stop, load, or repair the
provider.

[Portal Roads](portal-roads.md) owns the choice between direct server APIs, BYOK gateways,
aggregators, human coding subscriptions, subscription bridges, and local inference. A provider or
dashboard appearing there is a candidate classification, not a delivered connector or endorsement.

## Egress Is a Deliberate Boundary

!!! warning "Declaring a Portal names a possible egress path; it does not authorize one"
    A matching Portal may enter the registry, but Dispatcher currently refuses every Portal grant
    because the typed egress-admission path is absent. Payload privatization, secure-mode,
    local-before-paid, and x402 gates are not current enforcement. Declare only a credential, data
    boundary, and spend profile that could become eligible after those gates are delivered.

Three limits matter:

1. **No automatic cloud replay.** A failed local call is not replayed through a Portal; no current
   `FallbackModel` path exists.
2. **No probe egress by default.** `probe = false` prevents the registry's optional `/models`
   request. The resulting route remains unverified `UNKNOWN` and cannot receive a grant; the
   separate Portal quarantine also refuses it before transmission.
3. **No hidden remote lifecycle.** Binding writes no Portal Quadlet and contacts no provider. It
   validates intent, proves named-secret presence, and mounts the reference into the Vessel.

With probing off, a declared route is projected as `UNKNOWN`, not fabricated as `WARM`. With
probing on, current source performs a two-second, unauthenticated `GET <base_url>/models` and
validates the returned `data[*].id` inventory. A live link with malformed inventory or without the
declared model id becomes `ERROR`, while a credentialed provider may reject the probe even when its
ordinary authenticated model path works. Successful readiness observation still does not bypass
the current all-Portal dispatch quarantine.

[State of Work](../../state-of-the-work.md#context-privatization-and-portal-egress) owns the absent
egress gate. The documented anonymization Pattern does not authorize transmission.

## Open One Intentionally

This rite assumes a summoned host. Otherwise begin with [Summoning](../../summoning.md).

### 1. Admit the provider schema

Resolve the Codex without assuming its home, then add `animator` to the existing
`[extensions].builtins` list:

```bash
CODEX_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/lychd"
vi "$CODEX_DIR/lychd.toml"
```

Inscribe the provider anchors and inactive samples:

```bash
uv run --extra postgres-binary lychd init
```

The built-in `animator` extension contributes `runes/animator/portals/openai/` and
`runes/animator/portals/google-gemini/`. Both speak an OpenAI-shaped HTTP interface, while the
connector selects the declared provider's model-profile resolver. Selecting an `animator/*`
runtime also registers the shared Portal base. Another interface needs an extension-owned Rune
schema and connector factory.

### 2. Seal one credential

Create exactly the name the Rune will reference; never put the value in TOML:

```bash
SECRET_NAME=portal_openai_main
read -rsp "Value for $SECRET_NAME: " LYCHD_SECRET
printf '%s' "$LYCHD_SECRET" | podman secret create "$SECRET_NAME" -
podman secret exists "$SECRET_NAME"
unset LYCHD_SECRET SECRET_NAME
```

For deliberate rotation, use `podman secret create --replace`, then recreate the Vessel.

### 3. Declare one model

Create `"$CODEX_DIR/runes/animator/portals/openai/main.toml"`:

```toml title="main.toml"
name = "openai-main"
description = "Explicit remote chat capability."
api_key_secret_name = "portal_openai_main"
probe = false

[[models]]
id = "gpt-5.2"
description = "Remote tool-capable chat model."

[models.capabilities]
families = ["chat"]
modalities_in = ["text"]
supports_tools = true

[models.generation]
max_tokens = 4096
```

The `openai` leaf supplies provider identity and its default URL. Override `base_url` only for an
OpenAI-compatible endpoint. A Portal with no `[[models]]` blocks contributes no capability; LychD
does not infer or download a provider catalogue.

Portal models use the Pydantic AI profile selected by provider alias and model id, so settings
known to be unsupported are omitted rather than forced onto the request. OpenRouter, LiteLLM, and
Ollama retain their provider resolvers; Gemini's OpenAI-compatible leaf uses Google's model
profile. Generic compatible endpoints and local Soulstones use a conservative compatibility
profile. OpenRouter model ids keep their `provider/model` prefix. The current Google, LiteLLM, and
Ollama aliases reject the Responses surface; OpenAI, OpenRouter, and explicitly compatible generic
endpoints may select it. This is not evidence of a native Gemini transport.

### 4. Bind, restart, and observe

!!! danger "Restart only a quiescent Vessel"
    There is no complete active-run census or graceful drain command. Restarting fails work in
    `RUNNING` or `AWAITING_HARDWARE`. Stop submissions and let visible runs settle; if continuity
    is uncertain, do not restart.

```bash
uv run --extra postgres-binary lychd bind --dry-run
uv run --extra postgres-binary lychd bind
systemctl --user restart lychd-vessel.service
uv run --extra postgres-binary lychd status
```

Successful bind proves Rune validation, secret presence, and atomic unit reconciliation—not
provider reachability. The `openai-main:chat:gpt-5.2` row proves synthesis and registration. A
`WARM` observation proves only readiness of that exact declared binding; it proves neither egress
eligibility nor credentialed invocation. Current Dispatcher policy quarantines every Portal grant.

The Bridge has no provider picker. Once the general Egress Gate is delivered, a future attributable
end-to-end proof may make this Portal the only eligible `chat` plus tools candidate and send one
benign public-safe fixture through a fresh payload-bound decision. Today, do not send that prompt:
the current executable proof ends at declaration, bind, and readiness observation because
Dispatcher refuses the grant.

## Failure and Closure

If the row is absent, check extension activation, the provider anchor, at least one model block,
and the Vessel restart. If a request fails, inspect the Vessel journal and provider account
separately; do not reinterpret passive warmth as a provider response.

Close the sky by removing its routable model declarations, binding the new intent, and restarting
the quiescent Vessel. The named secret may then be rotated or retired under the operator's own
secret policy.

## Portal Rune Reference

| Field | Default | Meaning |
| :--- | :--- | :--- |
| `name` | required | Animator identity and capability-key prefix. |
| `description` | `""` | Operator note. |
| `provider_name` | provider leaf | Connector identity. |
| `base_url` | provider leaf | HTTP(S) endpoint root. |
| `api_key_secret_name` | `null` | One option-free Podman secret name, never its value. |
| `models` | `[]` | Explicit declarations; empty means zero capabilities. |
| `generation` | `null` | Portal-wide generation overlay. |
| `probe` | `false` | Opt in to the unauthenticated `/models` probe. |

Each model requires provider-facing `id`; it may add description, capability hints, and a
per-model generation overlay. Capability hints default to chat with text admission. Verification
may downgrade a declaration, never invent one.
