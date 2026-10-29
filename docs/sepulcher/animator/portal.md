---
title: Portal
icon: material/weather-hurricane
---

# :material-weather-hurricane: Portal: The Rift to the Remote Sky

> _Beyond the rift, another sky keeps its own thunder._

A **Portal** is a remote, API-backed [Animator](./index.md) declared by a provider-specific Rune.
It has no container and consumes no local VRAM. Its connector runs inside the trusted Vessel, where
it may read the one Podman secret explicitly mounted for it.

The credential shares that trust boundary: file permissions do not hide it from code already
executing inside the Vessel.

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

With probing off, the registry reports the route as `UNKNOWN`; a declaration alone cannot
establish `WARM`. Enabling it permits the current
two-second unauthenticated `GET <base_url>/models` probe and validation of the returned
`data[*].id` inventory. Malformed inventory or the absence of the declared model id produces
`ERROR`. A credentialed provider can reject this probe even if its ordinary authenticated model
call would work.

Read the result as a readiness observation only. It cannot bypass the current all-Portal
dispatch quarantine.

[State of Work](../../state-of-the-work.md#context-privatization-and-portal-egress) owns the absent
egress gate. The documented anonymization Pattern does not authorize transmission.

### Qualify disclosure accounting locally

The opt-in `closed-diagnostic-recording@1` profile exercises durable decisions and consumed
capacity using only the existing closed diagnostic fixture and a concrete local recorder.
Its host pins a synthetic export consumer and expected binding independently of the Cut.
The acceptance witness must retain consumed host/purpose/Cut limits across new identifiers and
service reconstruction, refuse old seals and copied claims, and record exactly the verified bytes.
The database retains restricted custody rather than source or candidate bodies.

Run its disposable-PostgreSQL receipts with:

```bash
make test-containers CONTAINER_TEST_TARGETS="tests/integration/test_privacy_disclosure_pg.py tests/integration/test_privacy_disclosure_migrations_pg.py"
```

The command requires the container-test environment described in
[Contributing](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#quality-checks). An explicit
`LYCHD_PRIVACY_TEST_DATABASE_URL` selects a disposable database supplied by the operator instead;
the profile never selects an application database automatically.

This profile opens no network road and changes no Portal grant. Actual peer enrollment, full
envelope verification, transport and native wait/adoption remain separate work. Its law is in
[Security](../../adr/09-security.md#offline-disclosure-accounting-qualification) and
[Persistence](../../adr/06-persistence.md#closed-disclosure-accounting-custody);
[State of Work](../../state-of-the-work.md#context-privatization-and-portal-egress) owns delivery.

<span id="open-one-intentionally"></span>

## Declare and inspect one Portal

This rite assumes a summoned host. Run its commands from the stable
[Summoning checkout](../../summoning.md#the-desecration), under the same operator user and XDG
environment. For a first installation, begin with [Summoning](../../summoning.md).

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

The built-in `animator` extension registers `runes/animator/portals/openai/` and
`runes/animator/portals/google-gemini/`. Both use an OpenAI-shaped HTTP interface, while the
Connector selects the declared provider's model-profile resolver. Selecting an `animator/*`
runtime also registers the shared Portal base.

For another interface, an extension must supply its Rune schema and Connector factory. The schema
alone admits declarations, without constructing a runtime or capability. That construction needs
one exact `PortalDefinition` for the concrete schema; there is no anonymous OpenAI-compatible
fallback.

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

[models.capabilities]
families = ["chat"]
modalities_in = ["text"]
supports_tools = true

[models.generation]
max_tokens = 4096
```

The `openai` leaf supplies provider identity and its default URL. Override `base_url` only for an
OpenAI-compatible endpoint. A Portal with no `[[models]]` blocks contributes no capability; LychD
does not infer or download a provider catalogue. The endpoint is a root: an existing path prefix is
kept when `/models` is appended, while embedded credentials, query or fragment state, port zero,
and out-of-range ports fail validation. Model ids are unique; duplicates fail before registry
construction.

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

The direct Systemd restart below is a separately chosen operator action under
[Reanimation’s limits](../phylactery/reanimation.md#perform-one-bounded-reanimation) and the
separately authorized [recovery plan](../../summoning.md#close-the-rite). It bypasses Orchestrator
admission and lease drain. It is not a delivered CLI fallback: [public stop still refuses an
active Vessel](../../state-of-the-work.md#core-cli-rites).

```bash
uv run --extra postgres-binary lychd bind --dry-run
uv run --extra postgres-binary lychd bind
systemctl --user restart lychd-vessel.service
uv run --extra postgres-binary lychd status
```

After binding, distinguish the three observations. Bind verifies the Rune, named secret, and
atomic reconciliation of units. CLI `status` inspects the installation. Neither establishes a
provider call or lists its model capabilities.

To inspect registration, open `http://127.0.0.1:7134/orchestrator/status` in the same-host browser.
Under `all_capabilities`, find the row whose `capability_key` is `openai-main:chat:gpt-5.2`.
This row establishes that the declared
capability was synthesized and registered. Because the example sets `probe = false`, its `phase`
remains `unknown`.

A later `warm` observation would establish readiness of that exact declared binding, without
establishing egress eligibility or credentialed invocation. Current Dispatcher policy quarantines
every Portal grant.

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

## Credential custody in Reach

Reach needs a stronger credential boundary than the current Vessel-local Connector supplies.
Its [deployment profiles](../../compositions/reach/deployments/index.md) must keep the provider
secret out of both Reach core and the Discord edge, even when they share a host. The Designed
profiles place that one exact provider or peer credential in a separate Provider Gate/egress
adapter service, which accepts only typed, egress-admitted attempts.

Until that service boundary and its deployment receipt are delivered, the current Connector
cannot serve as a Reach provider path, including in the public VPS profile.

## Portal Rune Reference

| Field | Default | Meaning |
| :--- | :--- | :--- |
| `name` | required | Animator identity and capability-key prefix. |
| `description` | `""` | Operator note. |
| `provider_name` | provider leaf | Connector identity. |
| `base_url` | provider leaf | HTTP(S) endpoint root without credentials, query, fragment, or invalid port. |
| `api_key_secret_name` | `null` | One option-free Podman secret name, never its value. |
| `models` | `[]` | Explicit declarations; empty means zero capabilities. |
| `generation` | `null` | Portal-wide generation overlay. |
| `probe` | `false` | Opt in to the unauthenticated `/models` probe. |

Each model requires provider-facing `id`; it may add capability hints and a per-model
generation overlay. Operator description belongs to the Portal, not each model block. Capability hints default to chat with text admission. Verification
may downgrade a declaration, never invent one.
