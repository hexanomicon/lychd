---
title: Summoning
icon: material/fire
---

# :material-fire: Summoning

This pre-alpha acceptance rite binds one LychD source revision, one Linux host, one local llama.cpp
model, and one **Bridge** reply. Run it top to bottom in one shell. It is not a beginner install:
configuration, systemd, model readiness, and reply must agree.

LychD calls its recurrent whole **the Lich**. The model you bind here is one organ of that whole,
not its memory, policy, authority, or identity.

Its five movements are:

1. [The Grounds](#the-grounds) — verify the Linux host, NVIDIA device, and model file.
2. [The Desecration](#the-desecration) — install this source revision and build its Vessel image.
3. [The Inscription](#the-inscription) — create configuration and data homes, then activate the
   llama.cpp extension.
4. [The First Soulstone](#the-first-soulstone) — declare and bind one local model service.
5. [The Awakening](#the-awakening) — draw the Summoning Circle, start, diagnose, and make the
   First Invocation.

Together these movements **draw the Summoning Circle**. Code builds the Bridge, but the Magus
chooses this Lich's actual boundary: source revision, host, Codex, Crypt, model, mounts, secrets,
capabilities, and reach. The phrase is not ceremonial substitution; every line of the Circle must
compile into inspectable configuration, containment, identity, or policy.

!!! warning "Current pre-alpha install path"
    No published CLI/image pair matches this source revision. Use its checkout and build
    `localhost/lychd:dev`; do not substitute a package or remote `latest` image.

!!! warning "Foundation boundary"
    Repository tests do not prove your rootless Podman, systemd, NVIDIA, llama.cpp, and model
    conjunction. This rite observes it once; [State of Work](state-of-the-work.md) remains the
    delivery authority.

## The Grounds — verify the Linux host {#the-grounds}

The daemon needs Linux, rootless Podman 5.4 or newer, a systemd user manager, NVIDIA CDI, and one
tool-capable GGUF model.

Run the rite as your ordinary user. Do not prefix LychD, Podman, or `systemctl --user` commands
with `sudo`.

**Goal:** prove every prerequisite before changing LychD configuration.

Run:

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

Require `Linux`, a responding user manager, Podman **5.4 or newer** reporting `true`, Git, uv, a
visible NVIDIA device, and `nvidia.com/gpu=all`. If `Linger=no`:

```bash
loginctl enable-linger "$USER"
loginctl show-user "$USER" --property=Linger
```

Derive the paths LychD will use. Keep these shell variables for the rest of the continuous rite:

```bash
CODEX_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/lychd"
CRYPT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lychd"
QUADLET_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd"
USER_UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
printf '%s\n' "$CODEX_DIR" "$CRYPT_DIR" "$QUADLET_DIR" "$USER_UNIT_DIR"
```

Bring a GGUF whose model card documents llama.cpp compatibility, a chat template, and tool calling.
It must fit VRAM; LychD does not calculate that fit. Place it at this exact path:

```bash
mkdir -p "$HOME/models"
realpath "$HOME/models"
test -r "$HOME/models/first-model.gguf" \
  && test -s "$HOME/models/first-model.gguf" \
  && echo "model readable and non-empty"
ls -lh "$HOME/models/first-model.gguf"
sha256sum "$HOME/models/first-model.gguf"
```

**Proof:** every command succeeds; lingering is `yes`; CDI contains the selector; the model is
readable, non-empty, and has a recorded digest.

**If it fails:** stop. Repair that host component through distribution or NVIDIA documentation, then
repeat this movement. Do not continue with an invisible GPU, Podman below 5.4, or unreadable model.

## The Desecration — install LychD {#the-desecration}

Build the host command and containerized application from the same checkout so their configuration
and generated-unit contracts cannot drift.

**Goal:** create the locked host environment and locally tagged Vessel image from one checkout.

From an existing checkout, stay at its root and skip only `git clone` and `cd lychd`. Otherwise
start in a parent directory.

Run:

```bash
git clone https://github.com/hexanomicon/lychd.git
cd lychd
uv sync --frozen
podman build --file Containerfile --tag localhost/lychd:dev .
```

Keep the checkout at a stable absolute path; the generated Host Reactor unit points into its
`.venv`.

**Proof:** record the revision and inspect both interfaces:

```bash
git rev-parse HEAD
uv run --extra postgres-binary lychd --help
podman image inspect localhost/lychd:dev --format '{{.Id}}'
```

Help must show only `init`, `bind`, `start`, `stop`, `status` (`st`), `logs`, `run`, and `del`.
Image inspection must print an ID.

**If it fails:** use Python `>=3.12,<3.15` and read the first failed build step. Do not work around
it with the old PyPI placeholder or by assuming remote `latest` matches the checkout.

## The Inscription — create configuration and data homes {#the-inscription}

`init` creates the editable **Codex** and LychD-managed persistent **Crypt**. The model shelf
remains external.

**Goal.** Create both homes, select the local Vessel image, and activate exactly the extension this
rite uses.

This is a fresh-host path, not a migration guide. Existing active Runes or custom extensions
invalidate its one-Soulstone proof.

Preview and then perform the first inscription:

```bash
uv run --extra postgres-binary lychd init --dry-run
uv run --extra postgres-binary lychd init
vi "$CODEX_DIR/lychd.toml"
```

The dry run uses the real planner without LychD-managed mutation. Continue only when it ends with
`Initialization plan is safe`; a blocker is a stop condition.

In the existing `[server.web]` table, change its existing `image` value to:

```toml
image = "localhost/lychd:dev"
```

In the existing `[extensions]` table, change its existing `builtins` value to:

```toml
builtins = ["animator/llamacpp"]
```

Leave `crypt = []` unchanged. Run `init` again so the selected extension can contribute its Rune
anchor and inactive sample:

```bash
uv run --extra postgres-binary lychd init --dry-run
uv run --extra postgres-binary lychd init
```

`init` preserves the edited settings file and creates
`runes/animator/soulstones/llamacpp/` when needed.

**Proof.** Inspect the homes and their owner-only boundaries:

```bash
stat -c '%a %n' "$CODEX_DIR/lychd.toml"
stat -c '%a %n' \
  "$CRYPT_DIR/triggers/inbox" \
  "$CRYPT_DIR/triggers/journal"
ls -la "$CODEX_DIR/runes/animator/soulstones/llamacpp"
```

Require mode `600` on settings, `700` on both Reactor directories, and the llama.cpp anchor.

**If it fails.** Correct malformed TOML or an unknown extension ID, then rerun `init`. If you want a
fresh generated settings file, first preserve your existing one yourself; `init` refuses to
overwrite it.

## The First Soulstone — bind one local model service {#the-first-soulstone}

A **Soulstone** is a local service whose lifecycle LychD coordinates. This llama.cpp router can
load its model without restarting the Vessel.

### Secret references {#the-secret-covenant}

The Rune below names no non-core secret, so there is no action at this compatibility anchor.
`bind` creates `lychd_app_secret_key` and `lychd_db_password` when absent and preserves existing
values. A later Rune that names an external secret must bring that exact Podman-secret reference
before binding.

**Goal.** Declare one tool-capable chat model, expose only its model shelf and NVIDIA device, then
transmute that declaration into generated units.

Print the exact host path you will paste into the Rune:

```bash
MODEL_DIR=$(realpath "$HOME/models")
printf '%s\n' "$MODEL_DIR"
```

Create the active Rune:

```bash
vi "$CODEX_DIR/runes/animator/soulstones/llamacpp/atelier.toml"
```

Paste the following TOML, but replace `/home/YOU/models` with the exact `MODEL_DIR` output. Keep the
container path `/models` unchanged. TOML does not expand `$HOME`.

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
description = "First local tool-capable chat model."

[models.capabilities]
families = ["chat"]
supports_tools = true

[quadlet]
image = "ghcr.io/ggml-org/llama.cpp:server-cuda"
```

Keep top-level `model_path`: the router connector probes the same `first-model` identity it loads.
`conflict_domains = ["gpu-main"]` declares incompatibility on that device domain; do not use `[]`
without measured coexistence.

Confirm that the saved Rune contains the real mount, pre-pull the runtime image, record its resolved
identity, then bind:

```bash
grep -F "$MODEL_DIR:/models:ro,Z" \
  "$CODEX_DIR/runes/animator/soulstones/llamacpp/atelier.toml"
podman pull ghcr.io/ggml-org/llama.cpp:server-cuda
podman image inspect ghcr.io/ggml-org/llama.cpp:server-cuda \
  --format '{{.Id}} {{json .RepoDigests}}'
uv run --extra postgres-binary lychd bind --dry-run
uv run --extra postgres-binary lychd bind
```

Dry bind validates settings, Rune, host, ports, mounts, and secrets without LychD-managed mutation.
Real bind creates missing core secrets, writes the owned unit generation, and reloads systemd. It
does not start services.

**Proof.** The dry run reports no blockers and real binding completes. Confirm the two generated
boundaries and the core secret references:

```bash
podman secret exists lychd_app_secret_key && echo "application secret present"
podman secret exists lychd_db_password && echo "database secret present"
test -f "$QUADLET_DIR/lychd-vessel.container" \
  && echo "Vessel Quadlet present"
test -f "$USER_UNIT_DIR/lychd-animator-atelier.target" \
  && echo "Animator target present"
test -f "$USER_UNIT_DIR/lychd-reactor.path" \
  && echo "Host Reactor path present"
```

**If it fails.** Read the first named violation, correct the Rune or settings, and run `bind` again.
If the active Rune is not loaded, confirm `builtins = ["animator/llamacpp"]` and the exact Rune
directory. If the mount is rejected, use an absolute host path outside the Codex, Crypt,
systemd-unit, and Reactor control roots. If an external secret is missing, create the exact reported
name. Do not hand-edit generated units.

## The Awakening — draw the Circle and make the First Invocation {#the-awakening}

The body is bound but still. Caged startup brings up the pod, PostgreSQL **Phylactery**, migration
gate, Host Reactor, and Vessel web process.

**Goal.** Obtain four agreeing first-life observations through the capability **Dispatcher** and
runtime **Orchestrator** path.

Start the normal caged installation:

```bash
uv run --extra postgres-binary lychd start
```

Do not manually enable generated units. Ask the Pulse for inventory:

```bash
uv run --extra postgres-binary lychd status
```

`status` does not prove migration or model warmth, so observe both explicitly:

```bash
systemctl --user is-active \
  lychd-pod.service \
  lychd-phylactery.service \
  lychd-reactor.path \
  lychd-vessel.service
systemctl --user show lychd-migrate.service \
  --property=Result --property=ExecMainStatus
```

Require four `active` results plus migration `Result=success` and `ExecMainStatus=0`. If startup is
still converging:

```bash
uv run --extra postgres-binary lychd logs --lines 120
```

!!! danger "Temporary local-browser boundary"
    Use a dedicated browser profile on this host. Keep the listener on `127.0.0.1`; do not publish,
    proxy, tunnel, or forward it. Keep the optional SAQ diagnostic UI disabled, do not expose
    `/schema/scalar`, and do not mix this profile with hostile sites. The two internal SAQ workers
    are required for normal Run execution.

    The fixed `magus:*` Sigil is not authentication. The Vessel constrains Host authority and CORS
    to explicit loopback values and uses CSRF, but those controls do not make an untrusted browser
    profile or remote exposure safe. Stop the Vessel after the rite.

Open the loopback Altar:

```text
http://127.0.0.1:7134/
```

The root opens the **Bridge**, the Altar's place of communion. The installed code supplies that
place; your admitted configuration and host choices define the greater Summoning Circle around it.
On a fresh Phylactery, click **New Séance** to create the first session. Then send one simple
message, such as:

```text
Reply with one sentence confirming first light.
```

That Intent makes the **First Invocation** and opens a smaller living
[Circle](divination/altar/circle.md) inside Bridge. Its casting follows the exact admitted Pattern.
The first request starts the Soulstone through the Host Reactor, loads `first-model`, waits for
readiness, and retries dispatch. Once admitted, that model-backed capability is the first local
Animus available to the casting; it remains one organ, not the Lich's Spirit or identity.
`supports_tools = true` is an admission declaration; this reply does not prove arbitrary tool use.

When a non-empty response settles in the Bridge, ask the Pulse for the joined live truth again:

```bash
uv run --extra postgres-binary lychd status
```

Open `http://127.0.0.1:7134/nexus`. After the turn,
`atelier:chat:first-model` must show `warm` and `warm: true`.

**Proof.** First life exists only when all four observations agree:

1. `status` reports a coherent bound installation rather than an unknown or drifted one;
2. its exact owned inventory plus the migration observation above report the expected pod,
   Phylactery, Reactor path, Vessel, Soulstone activity, and successful migration;
3. the Nexus projection reports `atelier` / `chat` / `first-model` as warm after the turn;
4. the Bridge contains a non-empty settled reply.

This is one bounded host-acceptance result, not a general runtime or hostile-browser claim.

**If it fails.** Start with the joined report, then narrow the log target shown by that report:

```bash
uv run --extra postgres-binary lychd status
uv run --extra postgres-binary lychd logs services --lines 120
```

If the core is healthy but inference fails, recheck the exact model filename, the CDI selector,
VRAM fit, and the model's real tool/chat-template support. Correct the owning Rune and run `bind`
again. `status --help` and `logs --help` expose the target identities implemented by this revision;
do not start the Soulstone by hand as a second activation path.

**Shutdown.** The public `stop` verb refuses a live Vessel until its authenticated lifecycle port
exists. Use the explicit host fallback:

```bash
systemctl --user stop \
  lychd-atelier.service \
  lychd-vessel.service \
  lychd-phylactery.service \
  lychd-reactor.path \
  lychd-pod.service
```

**Cleanup and recovery.** Stopping is not deletion. Inspect the destructive plan without applying
it:

```bash
uv run --extra postgres-binary lychd del --dry-run
```

It must name the edited Codex and durable Phylactery. Do not delete them or generated units by hand;
retain any blocked recovery handoff and resolve its named condition before replanning.

You have drawn one bounded Summoning Circle, awakened its body, crossed its Bridge, and heard one
Invocation answer. If any observation is absent, remain in [The Awakening](#the-awakening) until
the evidence agrees.
