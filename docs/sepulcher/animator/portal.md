---
title: Portal
icon: material/weather-hurricane
---

# :material-weather-hurricane: Portal: The Rift to the Remote Sky

> _"A rift is not a rescue that opens itself. It is named, sealed, and entered under the Magus's
> authority."_

A **Portal** is a remote, API-backed [Animator](./index.md) declared by a provider-specific Rune in
the Codex. It gives the Dispatcher a typed capability backed by another service rather than local
iron. The Portal has no container of its own and consumes no local VRAM; its connector runs inside
the trusted Vessel, where it may read the one Podman secret explicitly mounted for it.

LychD does not own the remote service's lifecycle. A Portal capability is therefore
`dedicated=False` and `is_dynamic=False`: the Orchestrator cannot start, stop, load, or repair it.
Current delivery is bounded by the [Animator dispatch
spine](../../state-of-the-work.md#animator-dispatch-spine) and [extension contribution
path](../../state-of-the-work.md#extension-activation-contributions).

## The law of the rift

!!! danger "Declaring a Portal grants a path to egress and cost"
    A matching Portal joins the Dispatcher's ordinary candidate set. The current foundation does
    **not** yet enforce the designed payload-privatization, secure-mode, local-before-paid, or x402
    gates. Do not declare a routable model unless its credential, data boundary, and spend are
    acceptable for every matching run.

Three limits are easy to confuse:

1. **No automatic cloud replay.** If a local provider call fails, LychD does not replay that
   request through a Portal. There is no current `FallbackModel` recovery path.
2. **No probe egress by default.** `probe = false` prevents the registry's optional `/models`
   request. It does not prevent a later model call after the Dispatcher selects this Portal.
3. **No hidden remote lifecycle.** Binding a Portal writes no Portal Quadlet and performs no
   provider request. It validates intent, verifies named secrets, and mounts the reference into the
   Vessel; runtime selection and the provider call happen later.

With probing off, a non-empty `base_url` is projected as passively `WARM`. That word means
**declared and eligible**, not “the provider answered.” With probing on, current source performs a
two-second, unauthenticated `GET <base_url>/models`; a credentialed provider may reject that probe
even when its ordinary authenticated model path would work.

## The connector boundary

The built-in `animator` extension currently contributes two concrete Portal Rune leaves:

- `runes/animator/portals/openai/` uses OpenAI's default API URL; and
- `runes/animator/portals/google-gemini/` uses Google's OpenAI-compatible endpoint.

Both hydrate through the OpenAI-compatible Pydantic AI connector. Other provider names require an
extension-owned Rune schema and connector factory. An unknown provider may be represented by a
passive Portal, but a model-bearing grant cannot become callable merely because a URL exists.

Each `[[models]]` block creates one or more declared capability keys. A Portal with no model blocks
is safely unadvertised: it contributes zero routable capabilities. LychD never downloads or guesses
a provider catalog.

## Open one intentionally

This is an **already-summoned-host** operation. If LychD's preflight, units, local runtime
readiness, and Bridge reply have not already agreed, begin with [The Summoning
Rite](../../summoning.md) instead of extracting commands from this page.

### 1. Activate the Portal schema

Resolve the Codex without hardcoding one home:

```bash
CODEX_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/lychd"
vi "$CODEX_DIR/lychd.toml"
```

Add `animator` to the existing `[extensions].builtins` list without removing active extensions. A
Portal-only list is:

```toml
[extensions]
builtins = ["animator"]
crypt = []
```

Then let the active extension inscribe its provider anchors and inactive samples:

```bash
uv run lychd init
```

Selecting any built-in `animator/*` runtime also registers the shared Portal base, so an existing
Soulstone installation need not add a duplicate entry merely for inheritance.

### 2. Seal the credential

Create exactly the name the Rune will reference. Do not put the value in TOML:

```bash
SECRET_NAME=portal_openai_main
read -rsp "Value for $SECRET_NAME: " LYCHD_SECRET
printf '%s' "$LYCHD_SECRET" | podman secret create "$SECRET_NAME" -
podman secret exists "$SECRET_NAME"
unset LYCHD_SECRET SECRET_NAME
```

Use `podman secret create --replace` only for a deliberate rotation, then recreate the Vessel so it
receives the new value. Portal credentials share the trusted Vessel process boundary with its
connector; file permissions do not hide a secret from code executing inside that same unit.

### 3. Inscribe one explicit model

Create `"$CODEX_DIR/runes/animator/portals/openai/main.toml"`:

```toml title="main.toml"
name = "openai-main"
description = "Explicit remote chat capability."
api_key_secret_name = "portal_openai_main"
probe = false

[generation]
temperature = 0.5

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

The provider name and default URL come from the `openai` leaf schema. Override `base_url` only when
the intended endpoint is genuinely OpenAI-compatible.

### 4. Bind, restart, and distinguish the observations

!!! danger "Restart only a quiescent Vessel"
    The current CLI has no complete active-run census or graceful drain command. Restarting the
    Vessel fails work in `RUNNING` or `AWAITING_HARDWARE`; it is not a transparent configuration
    reload. For this bounded local operation, stop new submissions and wait for every run visible
    in the Bridge to settle before continuing. That visual check is not a system-wide proof. If
    work may still be active or its continuity matters, stop here and do not restart.

```bash
uv run lychd bind --dry-run
uv run lychd bind
systemctl --user restart lychd-vessel.service
uv run lychd status
```

Read the results narrowly:

- successful `bind` proves Rune validation, secret presence, and atomic unit reconciliation; it
  does not contact the provider;
- the `openai-main:chat:gpt-5.2` row proves capability synthesis and registration;
- `warm` with `probe = false` is passive declaration, not live reachability; and
- only a successful model invocation proves the credentialed request path.

The current Bridge has no provider picker. To attribute an end-to-end test to this Portal, make it
the only eligible `chat` + tools candidate for that bounded test, open the [Bridge under the Altar's
browser boundary](../../divination/altar/index.md), and send only a benign, public-safe prompt. Do
not infer Portal use from an unattributed reply when another candidate was eligible.

If the row is missing, confirm the active extension, the exact provider anchor, at least one
`[[models]]` block, and the Vessel restart. If a real request fails, inspect the Vessel journal and
the provider account separately; an unauthenticated `probe = true` failure does not validate or
invalidate the mounted key.

## Portal Rune reference

A concrete Portal Rune lives below
`runes/animator/portals/<provider>/<instance>.toml` in the Codex. It declares remote intent; it is
not the connector object and not a generated unit.

### Top-level fields

| Field | Default | Office |
| --- | --- | --- |
| `name` | required | Animator name; first segment of each capability key. |
| `description` | `""` | Operator note. |
| `provider_name` | provider leaf | Connector identity; normally supplied by the concrete Rune schema. |
| `base_url` | provider leaf | HTTP(S) endpoint root. |
| `api_key_secret_name` | `null` | One option-free Podman secret name, never the value. |
| `models` | `[]` | Explicit remote model declarations; empty means zero capabilities. |
| `generation` | `null` | Portal-wide generation overlay. |
| `probe` | `false` | Opt in to the current unauthenticated `/models` reachability request. |

### `[[models]]` fields

| Field | Default | Office |
| --- | --- | --- |
| `id` | required | Provider-facing model id and final capability-key segment. |
| `description` | `null` | Operator note. |
| `[models.capabilities]` | chat/text defaults | Declared families, modalities, surface, tools, and streaming hints. |
| `[models.generation]` | `null` | Per-model overlay above the Portal generation profile. |

Declared capability hints may narrow or describe a model; verification may downgrade them. It may
not invent a model or a power absent from the Rune.

> _Close the sky by removing its routable model declarations, binding the new intent, and
> restarting the Vessel. A rift is safest when its opening and closing are equally explicit._
