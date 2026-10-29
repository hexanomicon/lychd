---
title: Summoning
icon: material/fire
---

# :material-fire: Summoning

!!! warning "The Circle is not yet whole"
    **Summoning does not work end to end yet.** This page describes how the rite is intended to
    work, not a supported installation path. Individual steps have repository evidence, but no
    maintained real-host receipt proves the complete sequence. Consult the
    **[State of Work](state-of-the-work.md#inscription-and-embodiment)** before attempting it.

A model replying to a prompt is only part of bringing LychD to life. The application must start
from the source you built, load the model you declared, retain its committed history, and return
the answer through the intended workflow. This rite shows how to check those parts together on
one Linux host.

Bring a source checkout, NVIDIA hardware, and a tool-capable GGUF model. You will work as your
ordinary user in one shell; later commands reuse the paths and identities established earlier.
This is a pre-alpha host acceptance procedure for someone familiar with Linux, TOML, systemd,
and containers.

Before starting services, read [Close the rite](#close-the-rite). The public stop command currently
refuses an active Vessel. An acceptance attempt needs a separately authorized recovery plan;
this guide does not supply a working end-to-end start/stop procedure.

## Draw the Summoning Circle

The five movements establish which source, host, model, configuration, mounts, secrets, and
capabilities the trial uses, and where the resulting services can be reached:

1. [The Grounds](#the-grounds) — establish the host and model.
2. [The Desecration](#the-desecration) — build the command and Vessel from one source.
3. [The Inscription](#the-inscription) — give configuration and durable state their homes.
4. [The First Soulstone](#the-first-soulstone) — declare and bind the local model service.
5. [The Awakening](#the-awakening) — start the body and witness its First Invocation.

LychD calls the recurrent whole **the Lich**. The model is one of its organs. These commands set
up that organ and the services around it; the [anatomy](sepulcher/index.md) explains how memory,
policy, authority, and identity contribute to the whole.

!!! warning "Use this revision's body"
    No published CLI/image pair matches this source revision. Build `localhost/lychd:dev` from
    the checkout used for the host command. A package or remote `latest` image is not a substitute.
    [State of Work](state-of-the-work.md) records repository evidence. You must still observe
    whether this combination works on your host.

## Stage the acceptance campaign

Choose the question your trial will answer. If you only need to test an already running model,
begin with the [standalone vLLM probe](sepulcher/animator/soulstone/engines/vllm.md#bring-one-service-to-a-first-reply).
That probe does not qualify the complete LychD installation. The worked rite here uses
llama.cpp. Using vLLM in its place needs a specific engine recipe and separate observations of
its namespace, devices, cache, shared memory, and lifecycle.

Keep one trial record. Identify the source, configuration, images, and model; write down the
permitted effects, case counts, deadlines, expected outcomes, receipt destination, stop conditions,
and person responsible for recovery. Keep private host material and raw receipts outside the
checkout. The gates below separate a model response from a composed installation, browser
acceptance, and later use. Complete each gate before claiming the next:

| Gate | Required observation before continuing |
| --- | --- |
| Source and configuration | Host command and Vessel image share a recorded source and lock; selected extensions and Runes agree; dry-run binding validates paths, ports and separate secret references. |
| Warm model path | Exact inventory and response identities, useful text, an actually executed harmless tool, finite request limits and released grants. This proves neither managed activation nor a persisted Run. |
| Composed body | Owned startup, migration and restricted runtime role, queue processing, actual dispatch and a settled reply agree; settled session/Run evidence remains inspectable after restart. |
| Browser operation | Dedicated local login and wrong-credential/foreign-Origin refusal, keyboard submission and cancellation, then exact Run → Orb → Loom → return. Qualify the synthetic development fixture separately. |
| Daily pilot | Predeclared repeated turns, startup/stop/restart, timeout/failure/cancellation and longer-session cases retain useful work and explain uncertain outcomes; measure latency, queues and resources. Complete authenticated lifecycle control before treating public CLI stop as supported. |
| Growth | Add one measured application or resource demand at a time, preserve an exact baseline and regressions, verify extension-generation compatibility and recovery, and separately admit memory or code-change effects. |

Begin the pilot with one fixed text model and sequential requests. Record those operating
conditions: the lease ledger does not limit capacity for you. Set measurable latency and resource
limits before the trial, then judge useful completed work on that profile. Arbitrary throughput,
synthetic GPU arithmetic, or a large test count cannot establish that result.

For each case, record pass, failed, blocked, or unknown. If an acknowledgment is lost or a request
times out, the external effect may still be running. Test interruption separately from retaining
a settled reply through restart; they establish different behavior. Use the
[receipt requirements](state-of-the-work.md#operator-receipt-requirements) and the relevant
[delivery boundary](state-of-the-work.md) to interpret what the observation supports.

Keep the first text pilot small. It needs no Phoenix, embedding model, Archive, Scout, Tomb,
foreign coding runtime, training, federation, or public extension SDK. When adding one later,
repeat the authority, custody, persistence, resource, and recovery checks affected by that addition.

## The Grounds — verify the Linux host {#the-grounds}

The [supported host policy](adr/08-containers.md#supported-host-policy) requires a free and
open-source Linux host stack under operator control. macOS and Windows are unsupported hosting
platforms, including deployments in Linux guests on those hosts.

Before writing configuration, establish Linux with cgroup v2, rootless Podman **5.4 or newer**,
an effective Quadlet user generator **5.4 or newer**, a responding systemd user manager, NVIDIA
CDI, Git, and uv. Do not prefix LychD, Podman, or `systemctl --user` commands with `sudo`.

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

Require `Linger=yes` before proceeding. The initialization report below also checks cgroup v2
and the effective Quadlet user generator; the Podman CLI version alone cannot establish those
requirements. An absent device, older Podman or Quadlet, or failed required host probe needs repair
through the distribution or NVIDIA documentation before this rite can continue.

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

Keep the digest so the trial identifies the file it used. Readability and size establish that
the file is present; loading it and running inference will test whether it works.

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
with the first failed step and the supported Python range `>=3.12,<3.16`; a different package or
image would abandon the source agreement this movement establishes.

## The Inscription — create configuration and data homes {#the-inscription}

`init` gives editable intent a **Codex** and managed persistent material a **Crypt**. This is a
fresh-host procedure. Existing active Runes or custom extensions change the installation being tested and need
their own acceptance plan.

Preview the inscription. Resolve required `HOST` failures in its readiness report before
continuing. The plan must also end with `Initialization plan is safe`; that message establishes
layout safety and does not establish host readiness:

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

The **Soulstone** is the local model service. This one uses llama.cpp's router mode so its model
can load without restarting the Vessel. Its Rune specifies which model shelf and NVIDIA device
the service can use.

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

A failed bind reports the first boundary it could not satisfy. Correct the cause and preview again.
An absent Rune usually means the wrong extension selection or directory. A rejected mount must be
an absolute host path outside Codex, Crypt, systemd-unit, and Reactor control roots. Supply an
external secret only under its exact reported name. Edit the Rune or settings that produced the
generated units; LychD will regenerate the files from those declarations.

### Retired host-native bindings

Core binds one managed container Vessel. The former `--native-only` and `--uncaged` options
refuse before host inspection or effects. Existing native bindings remain preserved and block
mutation; removal of support grants no conversion, stop or deletion authority. Reconcile such
an installation separately under its actual ownership.

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
    Sigil. This does not establish hostile-browser or remote safety. Close the trial under the
    recovery plan established before startup; the public stop limitation is explained below.

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
Dispatcher again. The loaded
model can then answer through the selected capability: the local Animus available to this
casting. Declaring `supports_tools = true` permits admission, but a text reply does not demonstrate
arbitrary tool use.

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
| Binding | `status` reports a coherent installation, with no unknown or changed ownership. |
| Body | Exact owned inventory and migration observations agree on pod, Phylactery, Reactor, Vessel, Soulstone activity, and successful migration. |
| Faculty | Nexus shows the exact `atelier` / `chat` / `first-model` capability as `active` after the turn. |
| Answer | Bridge contains a non-empty settled reply. |

Record all four observations with the source, configuration, image, model, host, and device
identities. Together they document this installation and its first reply. They do not qualify
another runtime combination or remove the local-browser restrictions above.

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

`lychd stop` currently refuses to stop an active Vessel. The authenticated container admission
and exact settlement needed to complete that lifecycle are not yet implemented and qualified.
The historical native signed-stop receipts describe a different deployment and do not establish
that this container can be stopped through the public command.

There is no automatic direct-manager fallback. A separately authorized operator recovery must
identify the owned units and containers, close admission, establish their terminal state, and
preserve dependencies while any outcome remains unknown. Follow the recovery plan agreed before
startup. [State of Work](state-of-the-work.md#core-cli-rites) records what remains unqualified;
completing the observations above does not certify a production lifecycle.

Stopping leaves configuration and history in place. You can inspect the destructive plan without
applying it:

```bash
uv run --extra postgres-binary lychd del --dry-run
```

The plan must account for the edited Codex and durable Phylactery. Retain any blocked recovery
handoff and resolve its named condition before replanning. Do not remove those homes or generated
units by hand.

The first answer is now tied to the machine and model that produced it, its committed Run, and
the limits of the trial. If an observation is missing, return to [The Awakening](#the-awakening).
When the observations agree and the trial has been closed, continue into
[Divination](divination/index.md) to follow what happens when the Lich's answer begins a
conversation.
