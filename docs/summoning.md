---
title: Summoning
icon: material/fire
---

# :material-fire: Summoning

A first reply is a small event. To make it credible, the machine around it must agree: the right
source built the Vessel, the declared model entered memory, committed state has a home, and the
answer returned through the admitted path. This rite brings those observations together on one
Linux host.

Bring a source checkout, NVIDIA hardware, and a tool-capable GGUF model. Work as your ordinary
user, from one shell, and keep the values you establish along the way. This is a pre-alpha host
acceptance procedure; familiarity with Linux, TOML, systemd, and containers is assumed.

## Draw the Summoning Circle

The Circle begins with choices you can inspect: source revision, host, model, configuration,
mounts, secrets, capabilities, and reach. The five movements give each choice a place:

1. [The Grounds](#the-grounds) — establish the host and model.
2. [The Desecration](#the-desecration) — build the command and Vessel from one source.
3. [The Inscription](#the-inscription) — give configuration and durable state their homes.
4. [The First Soulstone](#the-first-soulstone) — declare and bind the local model service.
5. [The Awakening](#the-awakening) — start the body and witness its First Invocation.

LychD calls its recurrent whole **the Lich**. The model is one organ within it. The commands below
establish the boundaries around that organ; memory, policy, authority, and identity keep their
separate places in the [anatomy](sepulcher/index.md).

!!! warning "Use this revision's body"
    No published CLI/image pair matches this source revision. Build `localhost/lychd:dev` from
    the checkout used for the host command. A package or remote `latest` image is not a substitute.
    [State of Work](state-of-the-work.md) records repository evidence; your host conjunction still
    needs its own observation.

## The Grounds — verify the Linux host {#the-grounds}

Before writing configuration, establish Linux, rootless Podman **5.4 or newer**, a responding
systemd user manager, NVIDIA CDI, Git, and uv. Do not prefix LychD, Podman, or `systemctl --user`
commands with `sudo`.

```bash
uname -s
systemctl --user status
loginctl show-user "$USER" --property=Linger
podman --version
podman info --format '{{.Host.Security.Rootless}}'
git --version
uv --version
nvidia-smi
nvidia-ctk cdi list
```

Look for `Linux`, Podman reporting rootless `true`, a visible NVIDIA device, and the CDI selector
`nvidia.com/gpu=all`. The user manager must respond. If `Linger=no`, enable it and check again:

```bash
loginctl enable-linger "$USER"
loginctl show-user "$USER" --property=Linger
```

Require `Linger=yes` before proceeding. An absent device, older Podman, or failed host probe needs
repair through the distribution or NVIDIA documentation before this rite can continue.

Name the four paths that the remaining commands will use:

```bash
CODEX_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/lychd"
CRYPT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lychd"
QUADLET_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd"
USER_UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
printf '%s\n' "$CODEX_DIR" "$CRYPT_DIR" "$QUADLET_DIR" "$USER_UNIT_DIR"
```

The model shelf is outside those LychD-owned roots. Bring a GGUF whose model card documents
llama.cpp compatibility, a chat template, and tool calling. Establish it at the exact filename
below; creating the directory does not supply the model. Its fit in VRAM is yours to verify.
LychD has no capacity calculation that can prove it for you.

```bash
mkdir -p "$HOME/models"
realpath "$HOME/models"
test -r "$HOME/models/first-model.gguf" \
  && test -s "$HOME/models/first-model.gguf" \
  && echo "model readable and non-empty"
ls -lh "$HOME/models/first-model.gguf"
sha256sum "$HOME/models/first-model.gguf"
```

Keep the digest. A readable, non-empty file is the first material witness; actual loading and
inference will test the rest of its claim.

## The Desecration — install LychD {#the-desecration}

The host command and containerized application must speak the same configuration and unit
contracts. Build both from this checkout. If you already have it, begin at its root and skip only
`git clone` and `cd lychd`:

```bash
git clone https://github.com/hexanomicon/lychd.git
cd lychd
uv sync --frozen
podman build --file Containerfile --tag localhost/lychd:dev .
```

Keep the checkout at a stable absolute path: the generated Host Reactor unit points into its
`.venv`. Record the source and image identities, then inspect the installed grammar:

```bash
git rev-parse HEAD
uv run --extra postgres-binary lychd --help
podman image inspect localhost/lychd:dev --format '{{.Id}}'
```

Help exposes `init`, `bind`, `start`, `stop`, `status` (with exact alias `st`), `logs`, `access`, and `del`.
There is no public `run` verb. Image inspection must return an ID. If construction fails, start
with the first failed step and the supported Python range `>=3.12,<3.15`; a different package or
image would abandon the source agreement this movement establishes.

## The Inscription — create configuration and data homes {#the-inscription}

`init` gives editable intent a **Codex** and managed persistent material a **Crypt**. This is a
fresh-host procedure. Existing active Runes or custom extensions change the installation being tested and need
their own acceptance plan.

Preview the inscription. Continue to the effect only when the plan ends with
`Initialization plan is safe`:

```bash
uv run --extra postgres-binary lychd init --dry-run
uv run --extra postgres-binary lychd init
vi "$CODEX_DIR/lychd.toml"
```

In the existing `[server.web]` table, replace its `image` value with:

```toml
image = "localhost/lychd:dev"
```

In the existing `[extensions]` table, replace its `builtins` value with:

```toml
builtins = ["animator/llamacpp"]
```

Leave `crypt = []` unchanged. These are edits to existing tables, not additional tables to append.
Run `init` again so the selected extension can supply its Rune anchor and inactive sample:

```bash
uv run --extra postgres-binary lychd init --dry-run
uv run --extra postgres-binary lychd init
```

Your edited settings file survives. The extension adds `runes/animator/soulstones/llamacpp/` where
needed. Now inspect the homes:

```bash
stat -c '%a %n' "$CODEX_DIR/lychd.toml"
stat -c '%a %n' \
  "$CRYPT_DIR/triggers/inbox" \
  "$CRYPT_DIR/triggers/journal"
ls -la "$CODEX_DIR/runes/animator/soulstones/llamacpp"
```

Settings must have mode `600`; both Host Reactor directories must have mode `700`; the llama.cpp
anchor must exist. A malformed TOML value or unknown extension ID should be corrected before
repeating `init`. The command refuses to overwrite existing settings. Preserve them yourself
before deliberately replacing them with a fresh generated file.

## The First Soulstone — bind one local model service {#the-first-soulstone}

The **Soulstone** supplies a local faculty. This one uses llama.cpp's router mode so its model can
load without restarting the Vessel. Its Rune declares exactly which shelf and NVIDIA device the
service receives.

### Secret references {#the-secret-covenant}

This Rune names no non-core secret. `bind` creates absent `lychd_app_secret_key` and
`lychd_db_password`, `lychd_runtime_db_password`, `lychd_phoenix_db_password`, and
`lychd_local_access_password` secrets and preserves existing values. A later Rune naming an external secret
must have that exact Podman-secret reference available before binding.

The administrative database credential is reserved for PostgreSQL and the migration gate.
The Vessel/SAQ and optional Phoenix receive separate roles and credentials. Initialization
creates the versioned HBA file; binding mounts it read-only so TCP authentication also applies
to existing data. Restart PostgreSQL with that generated policy before the new migration gate
runs. Preserve existing database secrets and data; replacing the administrator password does
not reset an initialized PostgreSQL cluster.

### Inscribe the Rune

Print the actual model directory and open the active Rune:

```bash
MODEL_DIR=$(realpath "$HOME/models")
printf '%s\n' "$MODEL_DIR"
```

```bash
vi "$CODEX_DIR/runes/animator/soulstones/llamacpp/atelier.toml"
```

Replace `/home/YOU/models` below with that exact directory. Keep the container path `/models`;
TOML does not expand `$HOME`.

```toml title="atelier.toml"
name = "atelier"
description = "First local llama.cpp router."
startup_mode = "router"
model_path = "/models/first-model.gguf"
models_dir = "/models"
models_autoload = false
volumes = ["/home/YOU/models:/models:ro,Z"]
devices = ["nvidia.com/gpu=all"]

[concurrency]
dedicated = true
persistent_resident = false
conflict_domains = ["gpu-main"]

[[models]]
id = "first-model"
path = "/models/first-model.gguf"

[models.capabilities]
families = ["chat"]
supports_tools = true

[quadlet]
image = "ghcr.io/ggml-org/llama.cpp:server-cuda"
```

Keep top-level `model_path`: it supplies the same `first-model` query identity the router loads.
Explicit router mode determines the launch shape. The `gpu-main` conflict domain declares
incompatibility; an empty list would claim coexistence and requires measured evidence.

Verify the mount, pull the engine image, record its resolved identity, and preview the binding:

```bash
grep -F "$MODEL_DIR:/models:ro,Z" \
  "$CODEX_DIR/runes/animator/soulstones/llamacpp/atelier.toml"
podman pull ghcr.io/ggml-org/llama.cpp:server-cuda
podman image inspect ghcr.io/ggml-org/llama.cpp:server-cuda \
  --format '{{.Id}} {{json .RepoDigests}}'
uv run --extra postgres-binary lychd bind --dry-run
uv run --extra postgres-binary lychd bind
```

Dry binding validates settings, Runes, host, ports, mounts, and secret references without
LychD-managed mutation. Real binding creates missing core secrets, writes the generated unit
files, and reloads systemd once. Services are still stopped.

Check that the binding left the expected material:

```bash
podman secret exists lychd_app_secret_key && echo "application secret present"
podman secret exists lychd_db_password && echo "database secret present"
podman secret exists lychd_runtime_db_password && echo "runtime database secret present"
podman secret exists lychd_phoenix_db_password && echo "Phoenix database secret present"
podman secret exists lychd_local_access_password && echo "local access secret present"
test -f "$QUADLET_DIR/lychd-vessel.container" \
  && echo "Vessel Quadlet present"
test -f "$USER_UNIT_DIR/lychd-animator-atelier.target" \
  && echo "Animator target present"
test -f "$USER_UNIT_DIR/lychd-reactor.path" \
  && echo "Host Reactor path present"
```

A failed bind names the first violated boundary. Correct that declaration and preview again.
An absent Rune usually means the wrong extension selection or directory. A rejected mount must be
an absolute host path outside Codex, Crypt, systemd-unit, and Reactor control roots. Supply an
external secret only under its exact reported name. Edit the Rune or settings that produced the
generated units; LychD will regenerate the files from those declarations.

## The Awakening — draw the Circle and make the First Invocation {#the-awakening}

The body is bound but still. Normal caged startup brings up the pod, PostgreSQL **Phylactery**,
migration gate, Host Reactor, and Vessel web process:

```bash
uv run --extra postgres-binary lychd start
```

Do not manually enable the generated units. Ask the **Pulse** for its bounded inventory:

```bash
uv run --extra postgres-binary lychd status
```

That inventory does not establish migration success or model warmth. Inspect the core units and
migration result directly:

```bash
systemctl --user is-active \
  lychd-pod.service \
  lychd-phylactery.service \
  lychd-reactor.path \
  lychd-vessel.service
systemctl --user show lychd-migrate.service \
  --property=Result --property=ExecMainStatus
```

Require four `active` results, migration `Result=success`, and `ExecMainStatus=0`. While startup is still converging, read the last 120 log lines:

```bash
uv run --extra postgres-binary lychd logs --lines 120
```

!!! danger "Temporary local-browser boundary"
    Use a dedicated browser profile on this host. Keep the listener on `127.0.0.1`; do not publish,
    proxy, tunnel, or forward it. Keep the optional SAQ diagnostic UI disabled, do not expose
    `/schema/scalar`, and do not mix this profile with hostile sites. The two internal SAQ workers
    are required for normal Run execution.

    Protected requests require a separate local credential before receiving the fixed `magus:*`
    Sigil. This does not establish hostile-browser or remote safety. Stop the Vessel after this rite.

Retrieve the local login explicitly in a private terminal, then enter its displayed username and
password in the browser's authentication dialog. Do not put the password in a URL or command line:

```bash
uv run --extra postgres-binary lychd access
```

Open the local Altar:

```text
http://127.0.0.1:7134/
```

The root opens **Bridge**. On a fresh Phylactery, choose **New Séance**, then offer a simple Intent:

```text
Reply with one sentence confirming first light.
```

This is the **First Invocation**, a smaller living [Circle](divination/altar/circle.md) within the
boundary you have prepared. Its casting follows the exact admitted Pattern. The first request
starts the Soulstone through the Host Reactor, loads `first-model`, waits for readiness, and asks
Dispatcher again. The model-backed capability becomes a local Animus available to this casting.
A declared `supports_tools = true` allows admission; this one reply proves no arbitrary tool use.

When a non-empty reply settles, ask the Pulse again:

```bash
uv run --extra postgres-binary lychd status
```

Open `http://127.0.0.1:7134/nexus` and find `atelier:chat:first-model`. Its chip should read
**`active`**: Nexus's screen label for the backend `warm` phase. Raw `phase` and `warm: true`
observations are available through `/orchestrator/status`; they are not additional card labels.

### Four witnesses to first light

| Witness | Required observation |
| --- | --- |
| Binding | `status` reports a coherent installation, with no unknown or drifted ownership. |
| Body | Exact owned inventory and migration observations agree on pod, Phylactery, Reactor, Vessel, Soulstone activity, and successful migration. |
| Faculty | Nexus shows the exact `atelier` / `chat` / `first-model` capability as `active` after the turn. |
| Answer | Bridge contains a non-empty settled reply. |

Record all four observations alongside the source, configuration, image, model, host, and device
identities. The receipt establishes that particular installation and first reply. Other runtime
combinations still need their own evidence, and the local-browser restrictions above continue to
apply.

### When the witnesses disagree

Begin with inventory, then narrow the log target to the component it names:

```bash
uv run --extra postgres-binary lychd status
uv run --extra postgres-binary lychd logs services --lines 120
```

If the core is healthy but inference fails, inspect the exact model filename, CDI selector, VRAM
fit, and real chat-template/tool support. Correct the owning Rune and bind again. Current target
names live in `status --help` and `logs --help`; hand-starting the Soulstone would create a second
activation path and obscure the failure you are trying to observe.

## Close the rite

The public `stop` verb currently refuses a live Vessel because its authenticated lifecycle port
is absent. For this acceptance procedure, use the explicit host fallback:

```bash
systemctl --user stop \
  lychd-atelier.service \
  lychd-vessel.service \
  lychd-phylactery.service \
  lychd-reactor.path \
  lychd-pod.service
```

Stopping leaves configuration and history in place. You can inspect the destructive plan without
applying it:

```bash
uv run --extra postgres-binary lychd del --dry-run
```

The plan must account for the edited Codex and durable Phylactery. Retain any blocked recovery
handoff and resolve its named condition before replanning. Do not remove those homes or generated
units by hand.

The first answer now has a context: the machine that produced it, the declared faculty, the
committed Run, and the limits you observed. If a witness is missing, return to
[The Awakening](#the-awakening). When they agree, continue into [Divination](divination/index.md),
where the body’s answer becomes the beginning of a conversation.
