---
title: Summoning
icon: material/fire
---

# :material-fire: The Summoning Rite

This is the minimum rite that binds and starts the daemon. Follow it top to bottom and you
will have a validated Codex, generated rootless Podman units, an upgraded Phylactery, a
running Vessel, and a foundation diagnosis. A first local model reply is the final
operator smoke test; it still depends on your chosen image, weights, driver stack, and
runtime flags.

Six movements, each ending in a command that proves it worked:

| Movement | You will |
| :--- | :--- |
| [The Grounds](#the-grounds) | Confirm the host can carry the daemon (Linux, rootless Podman, systemd; optionally a GPU). |
| [The Desecration](#the-desecration) | Install the `lychd` command-line tool. |
| [The Inscription](#the-inscription) | Run `lychd init` and meet the Codex and the Crypt. |
| [The Secret Covenant](#the-secret-covenant) | Establish referenced Podman secrets without putting values in TOML. |
| [The First Soulstone](#the-first-soulstone) | Write your first Soulstone Rune (a local model service) and bind it. |
| [The Awakening](#the-awakening) | Start the Vessel, let migrations run, diagnose the foundation, and try the first message. |

!!! note "Time estimate"
    Budget about 30 minutes if Podman and your device drivers are ready, plus however long
    it takes to download your first model weights.

!!! warning "The host is Linux"
    LychD binds to a Linux host with a rootless podman + systemd user session. macOS and
    Windows are development platforms for the code, not summoning grounds for the daemon.
    See [The Grounds](#the-grounds) for the full list.

!!! warning "Foundation boundary"
    The CLI/configuration/dispatch/orchestration foundation is covered by local tests. A real
    rootless Podman + GPU + model-image invocation is intentionally an operator integration test
    at this phase. The caged default includes mediated Host Reactor delivery, a read-only terminal
    journal, a host path/service consumer, typed validation, claim/cancellation/startup fences,
    exact-action-prefix crash recovery, and a typed hard-readiness inverse. A trustworthy soft
    model-load inverse, general repair of non-prefix or failed-compensation physical states, a
    DB-backed graph outbox, and the multimodal artifact materializer are later work. This rite does
    not imply they already exist.

When you finish, the daemon is alive on your iron. From there, the [Sepulcher](sepulcher/index.md)
documents each part you will work with — opening [Portals](sepulcher/animator/portal.md) and
driving [coven](sepulcher/animator/coven.md) swaps — while [Divination](divination/index.md) is
where you commune with the running daemon through the [Altar](divination/altar/index.md) instruments.

## The Grounds

Before the Lich can rise, the ground must be able to hold it. LychD is a systemd-native
daemon: it runs your models as rootless Podman containers governed by your user's systemd
session, and it keeps its durable soul in a generated pgvector/Postgres Phylactery unit. Confirm each prerequisite below with
the command given; do not proceed until every check passes.

### A Linux host

LychD manages the host's init system directly. It requires Linux with a **rootless podman
+ systemd user session** — the same substrate the [Sepulcher](sepulcher/index.md) is
built on. Confirm the user session is live:

```bash
systemctl --user status
loginctl show-user "$USER" --property=Linger
```

!!! tip "Enable lingering"
    If `Linger=no`, the daemon stops when you log out. Enable it so LychD survives a
    disconnected session:

    ```bash
    loginctl enable-linger "$USER"
    ```

### Podman with Quadlet support

The binding rite writes [Quadlet](sepulcher/codex.md) manifests that podman's systemd
generator turns into services. Quadlet requires podman 4.4 or newer:

```bash
podman --version
```

### A GPU with enough VRAM

Local model inference needs a GPU. The VRAM you have sets how large a model you can hold
warm and how many can share a coven. Check what the host sees:

```bash
nvidia-smi        # NVIDIA
rocm-smi          # AMD
```

!!! note "You can start without a GPU"
    A remote [Portal](sepulcher/animator/portal.md) needs no local VRAM at all. If you
    have no GPU yet, you can still complete the rite by opening a Portal instead of writing
    a local Soulstone — but the [First Soulstone](#the-first-soulstone) movement assumes
    local iron.

### The generated Phylactery

The normal caged rite does not require a separately installed Postgres. `lychd bind`
generates `lychd-phylactery.service` from the configured pgvector image and a one-shot
migration Quadlet (`lychd-migrate.container`, generated as `lychd-migrate.service`) ordered
before the Vessel. An uncaged/development invocation may instead
target an already-running Postgres and run `lychd database upgrade` explicitly.

**Verify the grounds.** You are ready to install when all of the following are true:

- `systemctl --user status` reports a running session.
- `podman --version` is 4.4 or newer.
- `nvidia-smi` / `rocm-smi` shows a GPU (or you plan to use a Portal).
- Podman can pull the configured Phylactery and model images.

## The Desecration

Install the `lychd` command-line tool — the [Pulse](lexicon.md), the rhythm by which you
drive the daemon. Pick one path. The Iron Path is recommended; it installs `lychd` into an
isolated environment so it never collides with your other Python tools.

=== "The Iron Path (recommended)"

    [`uv`](https://docs.astral.sh/uv/) installs the tool cleanly and instantly:

    ```bash
    uv tool install lychd
    ```

=== "The Acolyte's Path (pip)"

    Standard pip installation, for hosts without `uv`:

    ```bash
    pip install lychd
    ```

=== "The Necromancer's Path (source)"

    For Magi who intend to modify the core:

    ```bash
    git clone https://github.com/hexanomicon/lychd.git
    cd lychd
    uv sync
    ```

    From a source checkout the command runs as `uv run lychd`.

**Verify the install.** Confirm the Pulse answers:

```bash
lychd --help
```

You should see the command groups — `init`, `bind`, and the others. If the shell reports
`command not found`, the tool's install directory is not on your `PATH` — ensure
`~/.local/bin` is on it (`uv tool update-shell`).

## The Inscription

Before the Lich can rise, it must be told where its body will live. `init` creates the two
directories every later rite reads from and writes a starter set of configuration
templates.

```bash
lychd init
```

This establishes the two homes of the daemon:

- **The Codex** (`~/.config/lychd`) — your configuration. It holds `lychd.toml` plus the
  `runes/` tree of TOML declarations (your Soulstones, Portals, and settings). **You edit
  this.** See [The Codex](sepulcher/codex.md).
- **The Crypt** (`~/.local/share/lychd`) — persistent data: model weights, the
  Phylactery's volumes, and generated state. **LychD manages this; you back it up.** See
  [The Crypt](sepulcher/crypt.md).

During `init`, the filesystem is inspected. On **Btrfs**, the layout service may establish
native subvolume boundaries. On another filesystem it creates ordinary directories and
continues without snapshot guarantees. Automatic loopback-Btrfs fallback and complete
rollback orchestration are later work; `init` does not pretend a plain directory is a snapshot.

`init` also discovers every installed configuration schema and writes one sample TOML per
schema under the Codex `runes/` tree — including sample Soulstone and Portal declarations
you will edit in the next movement.

!!! tip "Set your model mount now"
    Open `~/.config/lychd/lychd.toml` and set `[lychd].models_dir` plus
    `[lychd].default_soulstone_mounts` for the host directory that contains your weights.
    Rune model paths name the container-side path (normally `/models/...`); they are not an
    undocumented host-relative `model_root` shortcut.

**Verify the inscription.** Confirm both homes exist:

```bash
ls ~/.config/lychd/lychd.toml ~/.local/share/lychd
```

For the full Codex layout — file precedence, the `runes/` tree, and environment
overrides — see [The Codex](sepulcher/codex.md).

## The Secret Covenant

Codex and Rune TOML contain secret **names**, never secret values. Core application and
database secret names are declared by `app.secret_key_secret` and `db.password_secret`;
`lychd bind` reconciles those core references with rootless Podman secret storage. A Portal
or Soulstone secret is operator-owned and must exist before bind.

For each non-core secret name referenced by a rune:

```bash
read -rsp "Secret value: " LYCHD_SECRET
printf '%s' "$LYCHD_SECRET" | podman secret create portal_openai_main -
unset LYCHD_SECRET
podman secret ls
```

Use `podman secret create --replace ...` only when you deliberately rotate an existing
value. Never paste a credential into `lychd.toml`, a Rune, a command history argument, or a
generated Quadlet.

**Verify the covenant.** Every name referenced by a Portal's `api_key_secret_name` or a
Soulstone's `secret_env_files` must appear in `podman secret ls`. Missing references make
`lychd bind` fail closed before any unit is rewritten.

## The First Soulstone

A [Soulstone](sepulcher/animator/soulstone.md) is a local model service running on your
own iron. You declare it as a **Soulstone Rune** — a TOML file in the Codex — and `bind`
transmutes that declaration into a systemd service. This movement writes your first
Soulstone Rune and binds it.

### Write the rune

Soulstone Runes live under `~/.config/lychd/runes/animator/soulstones/`. Create one for a
`llama.cpp` server. This example runs the server in **router** mode, which loads models on
demand (a capability with `is_dynamic=True`):

```toml title="~/.config/lychd/runes/animator/soulstones/llamacpp/atelier.toml"
name = "atelier"
description = "My first local model service."
groups = ["atelier"]
startup_mode = "router"
models_dir = "/models"

[concurrency]
dedicated = true
persistent_resident = false

[[models]]
id = "qwen3-8b"
path = "/models/qwen3-8b"
description = "A local chat model."

[models.capabilities]
supports_tools = true
```

What each part declares:

- `name` — the Animator's name. It becomes the first segment of every capability key this
  Soulstone yields: `atelier:chat:qwen3-8b`.
- `startup_mode = "router"` — the `llama.cpp` router loads models on demand, so its
  capabilities carry `is_dynamic=True` (see [Capabilities](sepulcher/animator/capabilities.md)).
  A single-model server (for example vLLM) has `is_dynamic=False` instead — reachable means warm.
- `[concurrency]` — `dedicated = true` means LychD owns this runtime's lifecycle and may
  swap it; `persistent_resident = false` means it is not pinned to survive every swap.
- `[[models]]` — one block per model. The `id` and `path` are required; `path` names the
  container-side artifact supplied by your configured model mount. The
  `[models.capabilities]` hints declare what the model can do — here, tool calling.

The full schema, including every field and how to declare vision, embeddings, and
generation defaults, is the [Soulstone Rune reference](sepulcher/animator/soulstone.md#soulstone-rune-reference).

!!! tip "A simpler non-dynamic alternative"
    If you run a single-model server such as vLLM, the capability has `is_dynamic=False` — it is
    warm the moment its endpoint is reachable, with no activation step. See the
    [reference](sepulcher/animator/soulstone.md#soulstone-rune-reference) for a vLLM example.

### Bind it

Transmute the Codex into systemd units:

```bash
lychd bind
```

This reads your runes and installed extensions, generates the Podman/systemd
[Quadlet](sepulcher/codex.md) manifests (including the Phylactery, migration, and Vessel
units), and—in the default `host-reactor` mode—inscribes the host-only
`lychd-reactor.path` and `lychd-reactor.service` units. It then reloads the user daemon. No
service is started by bind. Quadlets and plain user units are reconciled as one complete desired
fileset: a failure restores the prior owned generation, stale owned names disappear, and unrelated
operator units remain untouched. The circle is bound.

**Verify the soulstone.** Confirm LychD sees the Soulstone and can read its declared
capabilities:

```bash
lychd animators
```

You should see `atelier` listed with a `chat` capability for your model. Its **Active** and
**Warm** columns stay empty until the daemon runs and the model warms — that is expected
before the Awakening. If `bind` failed or the animator is missing, confirm the rune
parsed — `lychd bind` reports a named error on an invalid rune.

## The Awakening

Everything is in place: the grounds are clear, the tool is installed, the Codex is
inscribed, and a Soulstone is bound. This movement wakes the daemon and exchanges the first
message.

### Start the daemon

Summon the Vessel through the user's systemd session:

```bash
systemctl --user enable --now lychd-vessel.service
```

The generated dependencies start the Phylactery, wait at most 60 seconds for its TCP
readiness, run the one-shot schema migration, activate the Host Reactor path watcher, and only
then start the Vessel. A timeout or migration failure prevents the Vessel from starting. The
path watcher invokes the host-side `lychd reactor consume` oneshot when a complete typed
transition arrives. Watch the daemon's internal monologue while it comes up:

```bash
journalctl --user -fu lychd-vessel.service
```

!!! tip "Foreground alternative for development"
    Uncaged/development mode uses explicit database credentials and migration, then the
    native foreground server bridge:

    ```bash
    DB__PASSWORD_FILE=/secure/path/db-password lychd database upgrade
    DB__PASSWORD_FILE=/secure/path/db-password \
      APP__SECRET_KEY_FILE=/secure/path/app-key \
      ORCHESTRATION__SWITCHING__ACTUATOR=systemd \
      lychd serve --host 127.0.0.1 --port 7134
    ```

    `lychd database upgrade` is not an extra step in the normal caged rite; the generated
    migration unit owns it. Direct Systemd actuation is an explicit uncaged choice; the caged
    default is `host-reactor`. Use `lychd doctor --uncaged` for the matching preflight. There is
    no `lychd run` command.

    For a host-managed uncaged service instead of the foreground process, set
    `orchestration.switching.actuator = "systemd"`, run `lychd bind --uncaged`, and explicitly
    enable `lychd-uncaged-vessel.service`. Its distinct name cannot shadow the caged
    `lychd-vessel.service`. Before returning to caged mode, disable the uncaged unit, restore
    `actuator = "host-reactor"`, and run ordinary `lychd bind`; complete-fileset reconciliation
    removes the now-stale owned unit file.

### Examine the foundation

After startup, run the read-only preflight:

```bash
lychd doctor
systemctl --user --no-pager status \
  lychd-phylactery.service lychd-migrate.service lychd-reactor.path \
  lychd-vessel.service
```

`doctor` validates Codex permissions, settings, Runes, host tools, secret references, the
owner-only stasis/Reactor directories, and both generated Reactor unit files.
The systemd status is the separate live-unit check; `doctor` does not claim that a model has
completed real inference.

### Open the Altar

The [Altar](divination/altar/index.md) is the web surface for communing with the Lich.
Open it in a browser:

```
http://localhost:7134
```

The generated Pod publishes this port on host loopback only. That makes the current Altar a
single-user local surface; it is not caller authentication. Do not expose it by changing the bind
address alone. Remote access needs a separately configured authenticated, authorized, TLS front
door.

### Watch the Nexus warm

Open the [Nexus](divination/altar/nexus.md) — the capability board. When you first
arrive, your model's `chat` capability will show as **awaited** (a dynamic model —
`is_dynamic=True` — that is reachable but not yet loaded) or **cold**. This is honest:
nothing is loaded until something asks for it.

### Exchange the first message

Open the [Bridge](divination/altar/index.md) — the chat instrument — and send a message.

Behind the scenes: your Intent resolves to a `chat` capability with explicit modality and
tool requirements. The Dispatcher selects semantically but grants only `WARM`; a managed
non-WARM capability emits a transition signal. The Orchestrator alone performs the soft
activation or hard swap, waits for `WARM`, and lets the graph retry dispatch. The Nexus then
moves the capability **awaited → warming → active**, and the first tokens can stream back on
the Bridge.

!!! success "The foundation is summoned"
    When `doctor`, the core unit and Reactor-path states, `lychd animators`, and the Bridge reply all agree,
    the minimum vertical slice is alive on your iron. If the units pass but inference does
    not, the remaining fault is in the selected model image/weights/runtime boundary rather
    than a reason to bypass the Dispatcher or add a second activation path.

## Where to go next

- [Open a Portal](sepulcher/animator/portal.md) to add a remote provider alongside your
  local models.
- [Manage covens](sepulcher/animator/coven.md) to understand and drive model swaps.
- Drive and watch the daemon from the [Altar](divination/altar/index.md) — the Bridge and
  the Loom.
