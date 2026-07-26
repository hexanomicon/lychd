---
title: Summoning
icon: material/fire
---

# :material-fire: The Summoning Rite

This rite brings one LychD source revision to first life on one Linux host and receives one reply
in its **Bridge chat instrument**. Follow it top to bottom in one shell. At the end, configuration
preflight, systemd state, model readiness, and that Bridge reply must agree.

LychD calls its recurrent whole **the Lich**. The model you bind here is one organ of that whole,
not its memory, policy, authority, or identity.

The path has six movements:

1. [The Grounds](#the-grounds) — verify the Linux host, NVIDIA device, and model file.
2. [The Desecration](#the-desecration) — install this source revision and build its Vessel image.
3. [The Inscription](#the-inscription) — create configuration and data homes, then activate the
   llama.cpp extension.
4. [The Secret Covenant](#the-secret-covenant) — keep secret values outside configuration.
5. [The First Soulstone](#the-first-soulstone) — declare and bind one local model service.
6. [The Awakening](#the-awakening) — start, diagnose, and send one message.

!!! warning "Current pre-alpha install path"
    This repository revision does not have a published command-line package and Vessel image pair
    that matches its source. The rite therefore uses a source checkout and builds
    `localhost/lychd:dev`. Do not substitute `uv tool install lychd`, `pip install lychd`, or
    `ghcr.io/hexanomicon/lychd:latest` unless a later release records matching public artifacts.

!!! warning "Foundation boundary"
    Repository tests exercise the local software foundation. Rootless Podman, systemd, NVIDIA,
    llama.cpp, and your selected weights meet only on your host; their conjunction must be observed
    there and is not something documentation can pre-claim. [State of the
    Work](state-of-the-work.md) owns every other delivery boundary and the metadata required for a
    maintained operator receipt.

!!! note "Time"
    The commands are short. Building and pulling images, acquiring a suitable model, and loading it
    on your hardware dominate the duration, so there is no honest fixed estimate.

## The Grounds — verify the Linux host {#the-grounds}

The daemon needs ground that can carry its body. This candidate path is deliberately narrow: a
Linux host, rootless Podman 5.4 or newer, a working systemd user manager, NVIDIA CDI, and one
tool-capable GGUF model.

Run the rite as your ordinary user. Do not prefix LychD, Podman, or `systemctl --user` commands
with `sudo`.

**Goal.** Prove every prerequisite before changing LychD configuration.

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

You need `Linux`, a responding user manager, Podman **5.4 or newer** reporting `true` for rootless
operation, Git, uv, a visible NVIDIA device, and an NVIDIA CDI entry such as
`nvidia.com/gpu=all`. If `Linger=no`, make the user service survive logout:

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

This rite does not acquire weights for you. Arrive with a GGUF whose model card explicitly
documents llama.cpp compatibility, a chat template, and tool calling; the filename and later Rune
hint alone prove none of those properties. The model must also fit your VRAM because LychD does not
yet calculate that fit for you. Place the file at this exact path:

```bash
mkdir -p "$HOME/models"
realpath "$HOME/models"
test -r "$HOME/models/first-model.gguf" \
  && test -s "$HOME/models/first-model.gguf" \
  && echo "model readable and non-empty"
ls -lh "$HOME/models/first-model.gguf"
sha256sum "$HOME/models/first-model.gguf"
```

**Proof.** Every command above succeeds; lingering reads `yes`; the CDI list contains the selector;
and the final commands show a readable, non-empty `first-model.gguf` and its digest. Preserve that
digest if you later assemble a maintained receipt. Model licensing and the source from which you
obtain the weights remain your responsibility.

**If it fails.** Stop at the failed prerequisite. Install or repair that host component with your
distribution or NVIDIA documentation, then repeat this movement. Do not continue with an invisible
GPU, Podman older than 5.4, or an unreadable model.

??? info "No NVIDIA device?"
    A remote [Portal](sepulcher/animator/portal.md) avoids local VRAM, and other Soulstone runtimes
    have their own device contracts. They are different **Runes—TOML configuration
    declarations**—not drop-in substitutions for the CUDA Rune below. Complete their owning guide
    instead of mixing paths in this rite.

## The Desecration — install LychD {#the-desecration}

Build the host command and containerized application from the same checkout so their configuration
and generated-unit contracts cannot drift.

**Goal.** Create the locked host environment and a locally tagged Vessel image from one checkout.

If you already completed the README bootstrap or opened this page from an existing checkout, do
not clone another copy inside it. Stay at that checkout's root, skip only the `git clone` and
`cd lychd` lines below, and rerun the common `uv sync`, build, and proof commands. Otherwise, start
in a parent directory that does not already contain `lychd`.

Run:

```bash
git clone https://github.com/hexanomicon/lychd.git
cd lychd
uv sync --frozen
podman build --file Containerfile --tag localhost/lychd:dev .
```

Keep this checkout at a stable absolute path. The Host Reactor unit generated later points to the
`lychd` executable inside this checkout's `.venv`; moving or deleting the checkout breaks that
host-side consumer.

**Proof.** Record the revision and inspect both interfaces:

```bash
git rev-parse HEAD
uv run lychd --help
podman image inspect localhost/lychd:dev --format '{{.Id}}'
```

The public help output must contain only the compact Pulse grammar—`init`, `bind`, `start`, `stop`,
`status` (with `st` as its alias), `logs`, `run`, and `del`—while the image inspection must print
an image ID. Server, migration, consent, and Reactor process entrypoints are internal machinery,
not operator roots.

**If it fails.** Use Python `>=3.12,<3.15` for the locked environment and read the first failing
build step. Do not work around a failure by installing the old PyPI placeholder or by assuming a
remote `latest` image matches the checkout.

For development conventions and the full quality gate, enter the [contributor
forge](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md).

## The Inscription — create configuration and data homes {#the-inscription}

The source now exists, but it has no host inscription. `init` creates the editable configuration
home—the **Codex**—and LychD-managed persistent data—the **Crypt**. Your model shelf remains the
separate directory you made in the first movement.

**Goal.** Create both homes, select the local Vessel image, and activate exactly the extension this
rite uses.

This is a fresh-install or README-bootstrap path, not a migration guide for an existing LychD
configuration. If this Codex already contains custom extensions or active Runes, stop and reconcile
them through their owning guides; additional active declarations invalidate this rite's
one-Soulstone proof.

Preview and then perform the first inscription:

```bash
uv run lychd init --dry-run
uv run lychd init
vi "$CODEX_DIR/lychd.toml"
```

The preview uses the same planner as the real command and renders three concise XDG tiers:
**Codex** beneath `~/.config` (including host Binding), **Crypt** beneath `~/.local/share`
(including the Phylactery), and **Forge** beneath `~/.cache`. It makes no LychD-managed change to
files, modes, mounts, services, or secrets; bounded external probes may let Podman or another host
tool maintain its own runtime metadata. A preceding host-foundation panel concurrently verifies the systemd
user manager, Podman/Quadlet versions, cgroup v2, Binding sites, SELinux mode, Btrfs substrate, and
the observed PostgreSQL No-COW directory policy. Systemd, Podman/Quadlet, cgroup v2, and prepared
Binding sites govern the aggregate `BIND` verdict; SELinux and Btrfs remain optional hardening and
storage optimization.

Blockers and external mounts remain explicit. Cyan paths will be created by LychD; green LychD
paths already exist. Shared XDG, Podman, and systemd anchors are blue with a separate `will create`
or `present` suffix because LychD may create a missing directory but never owns its namespace. `present` does
not mean `ready`: the Binding panel says `prepared` only after proving shape, current-user
ownership, and write/search access. Yellow means removal and red means blocked. The default tree
keeps only paths, states, and safety-relevant qualifiers; add `--verbose` when you also want the
source-owned description of each path and every inspected intermediate host anchor. Continue only when it ends with
`Initialization plan is safe`. Read the
lifecycle-receipt node carefully: a successful
non-dry initialization first proves full convergence, then explicitly adopts the exact Codex,
Crypt, and Forge root identities as the recursive authority for a later confirmed `del`. Each root
must share its parent's mount ID. Shared XDG parents, external shelves, foreign mounts, and the
mounted Phylactery remain outside that grant.

??? danger "Optional destructive developer round trip before editing"
    A pristine first inscription can be deleted and repeated before you place any intent or useful
    data in the Codex and Phylactery:

    ```bash
    uv run lychd del --dry-run
    uv run lychd del
    uv run lychd init --dry-run
    uv run lychd init
    ```

    `del` asks for confirmation because its intended scope is the whole LychD installation,
    including exact-owned services and bindings plus verified Codex, Crypt, cache, snapshots, and
    Phylactery data. Read every group in the preview. Unreceipted Podman objects and secrets, the
    package, and the source checkout are preserved explicitly. `del` must not follow symlinks,
    cross an unknown mount, or delete an external model shelf. If an attested mount or subvolume
    requires root, LychD retires its exact-owned units, retains a mode-`0600` continuation
    checkpoint bound to the filesystem UUID and subvolume UUID/ID, and pauses with an
    absolute-tool privileged operator handoff rather than invoking `sudo`; run `del` again after
    completing that handoff. If any plan group is `BLOCKED`, no deletion effect runs and no
    copyable root command is offered; clear the blocker and preview again.

In the existing `[server.web]` table, change its existing `image` value to:

```toml
image = "localhost/lychd:dev"
```

In the existing `[extensions]` table, change its existing `builtins` value to:

```toml
builtins = ["animator/llamacpp"]
```

Leave `crypt = []` unchanged. Do not add a `[lychd]` table or global model-mount setting; neither
exists. Run `init` a second time so the now-active extension can contribute its Rune anchor and
marked, inactive sample:

```bash
uv run lychd init --dry-run
uv run lychd init
```

`init` does not overwrite the existing `lychd.toml`. The second pass reads your extension selection
and creates `runes/animator/soulstones/llamacpp/` if needed.

When PostgreSQL data is absent on a Btrfs substrate and the trusted tools are available,
initialization attempts a subvolume plus a No-COW directory policy. It verifies the result after
apply. Existing storage—including an external mount—is preserved and only observed; `init` never
retrofits `+C` onto existing data. The directory flag governs newly created extents and does not
rewrite existing PostgreSQL files. On another filesystem LychD uses an ordinary directory and does
not claim snapshot rollback.

**Proof.** Inspect the homes and their owner-only boundaries:

```bash
stat -c '%a %n' "$CODEX_DIR/lychd.toml"
stat -c '%a %n' \
  "$CRYPT_DIR/triggers/inbox" \
  "$CRYPT_DIR/triggers/journal"
ls -la "$CODEX_DIR/runes/animator/soulstones/llamacpp"
```

The settings file must report mode `600`; both Reactor directories must report `700`; and the
llama.cpp anchor must exist. Its generated sample begins with `# lychd: sample-rune` and remains
inactive. The next movement creates a separate active Rune.

**If it fails.** Correct malformed TOML or an unknown extension ID, then rerun `init`. If you want a
fresh generated settings file, first preserve your existing one yourself; `init` refuses to
overwrite it.

Read [The Codex](sepulcher/codex.md) when you need precedence, layout, or additional Rune families.

## The Secret Covenant — account for referenced secrets {#the-secret-covenant}

Configuration may name a secret, but it may never contain the value. Rootless Podman's secret
store holds values; Codex and Rune TOML hold references.

**Goal.** Account for every non-core secret name before binding without inventing one the current
Rune does not need.

The llama.cpp Rune in the next movement references **no non-core secret**, so the candidate path has
nothing to create here. Inspect the store:

```bash
podman secret ls
```

`lychd bind` will generate strong values for the two core references—`lychd_app_secret_key` and
`lychd_db_password`—only when they are absent. It preserves existing values.

??? info "Later Runes with non-core secrets"
    If you later add a Portal or Soulstone Rune that names a non-core secret, create that exact
    name before binding. For example, only if a Rune names `portal_openai_main`:

    ```bash
    SECRET_NAME=portal_openai_main
    read -rsp "Value for $SECRET_NAME: " LYCHD_SECRET
    printf '%s' "$LYCHD_SECRET" | podman secret create "$SECRET_NAME" -
    podman secret exists "$SECRET_NAME"
    unset LYCHD_SECRET SECRET_NAME
    ```

**Proof.** Every non-core name referenced by `api_key_secret_name`, `secret_env_files`, or a runtime
control-plane field exists in `podman secret ls`. For the exact Rune below, that set is empty.

**If it fails.** Create the missing name and rerun `bind`. Missing references fail closed before the
generated unit set is rewritten. Use `podman secret create --replace` only for a deliberate
rotation, then recreate affected containers so they receive the new value.

## The First Soulstone — bind one local model service {#the-first-soulstone}

A **Soulstone** is a local model service whose lifecycle LychD can coordinate. This one is a
llama.cpp router: LychD's runtime **Orchestrator** starts the service, and its model can move from
available to warming to warm without restarting the Vessel.

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
image = "ghcr.io/ggml-org/llama.cpp:server-cuda"
startup_mode = "router"
model_path = "/models/first-model.gguf"
models_dir = "/models"
models_autoload = false
volumes = ["/home/YOU/models:/models:ro,Z"]
devices = ["nvidia.com/gpu=all"]

[concurrency]
dedicated = true
persistent_resident = false

[[models]]
id = "first-model"
path = "/models/first-model.gguf"
description = "First local tool-capable chat model."

[models.capabilities]
families = ["chat"]
supports_tools = true
```

The top-level `model_path` is a current router-identity compatibility field: it makes the connector
probe `first-model`, matching the explicit model ID it asks the router to load.

Confirm that the saved Rune contains the real mount, pre-pull the runtime image, record its resolved
identity, then bind:

```bash
grep -F "$MODEL_DIR:/models:ro,Z" \
  "$CODEX_DIR/runes/animator/soulstones/llamacpp/atelier.toml"
podman pull ghcr.io/ggml-org/llama.cpp:server-cuda
podman image inspect ghcr.io/ggml-org/llama.cpp:server-cuda \
  --format '{{.Id}} {{json .RepoDigests}}'
uv run lychd bind --dry-run
uv run lychd bind
```

The dry run validates the active settings and Rune, host prerequisites, ports, mount boundaries,
and secret references, then renders the owned unit generation without LychD-managed mutation.
External probes such as Podman may maintain their own rootless runtime metadata. Real `bind`
creates missing core secrets, writes that complete Quadlet/plain-unit generation, and reloads the
user manager. It does **not** start the services. Live state belongs to `status`, not binding.

**Proof.** The dry run reports no blockers and real binding completes. Confirm the two generated
boundaries and the core secret references:

```bash
podman secret exists lychd_app_secret_key && echo "application secret present"
podman secret exists lychd_db_password && echo "database secret present"
test -f "$QUADLET_DIR/lychd-vessel.container" \
  && echo "Vessel Quadlet present"
test -f "$USER_UNIT_DIR/lychd-reactor.path" \
  && echo "Host Reactor path present"
```

**If it fails.** Read the first named violation, correct the Rune or settings, and run `bind` again.
If the active Rune is not loaded, confirm `builtins = ["animator/llamacpp"]` and the exact Rune
directory. If the mount is rejected, use an absolute host path outside the Codex, Crypt,
systemd-unit, and Reactor control roots. If an external secret is missing, create the exact reported
name. Do not hand-edit generated units.

The [Soulstone guide](sepulcher/animator/soulstone.md) owns additional runtimes, concurrency, and
mount configuration.

## The Awakening — start, diagnose, and send one message {#the-awakening}

The body is bound but still. Starting the containerized (or **caged**) Vessel pulls its dependency
chain into motion: the pod and its PostgreSQL **Phylactery** durable-data service start, the
migration gate waits up to 60 seconds and upgrades the schema, the **Host Reactor** host-side
transition actuator watches for typed intents, and only then does the web process rise.

**Goal.** Obtain four agreeing first-life observations through the capability **Dispatcher** and
runtime **Orchestrator** path.

Start the normal caged installation:

```bash
uv run lychd start
```

Do not manually enable the generated caged Quadlet. Ask the Pulse for live inventory and
readiness:

```bash
uv run lychd status
```

The Phase-1 report distinguishes initialization, binding ownership, exact unit activity, and the
Phylactery mount. It does **not** yet prove the migration result, database or HTTP readiness, queue
health, or model warmth. Preserve the two missing raw observations for this candidate rite:

```bash
systemctl --user is-active \
  lychd-pod.service \
  lychd-phylactery.service \
  lychd-reactor.path \
  lychd-vessel.service
systemctl --user show lychd-migrate.service \
  --property=Result --property=ExecMainStatus
```

The four units must each print `active`; migration must show `Result=success` and
`ExecMainStatus=0`. If startup is still in progress, inspect the bounded operational tail and rerun
it as needed:

```bash
uv run lychd logs --lines 120
```

The Phase-1 log projection is a bounded read, not a live follow.

!!! danger "Temporary local-browser boundary"
    **Before opening the Altar:** use a dedicated browser profile on this same host. Keep the HTTP
    listener on `127.0.0.1`; do not publish, reverse-proxy, tunnel, or port-forward its port. Do not
    enable the SAQ UI or open `/schema/scalar`. Stop the Vessel when the rite is finished if hostile
    webpages are in your threat model.

    **Why:** the fixed `magus:*` identity label (a **Sigil**) is not a login. The production app
    still accepts arbitrary Host values and wildcard CORS, so loopback alone does not isolate
    Bridge, Nexus, or run streams from every hostile webpage. CSRF blocks ordinary unsafe
    cross-origin requests, but it does not protect GET/SSE confidentiality or DNS rebinding. Do
    not use the Altar from a browser profile that also visits untrusted sites.

    Until the S0 ingress gate lands, use exactly the documented generated deployment. The internal
    ASGI process entrypoint is not a public Pulse command and is not permission to expose the port
    remotely.

Open the loopback Altar:

```text
http://127.0.0.1:7134/
```

The root opens the **Bridge**, the Altar's chat instrument. On a fresh Phylactery, click **New
Séance** to create the first session. Then send one simple message, such as:

```text
Reply with one sentence confirming first light.
```

The first request may take time: it requests the declared tool-capable chat service, starts the
dedicated Soulstone through the Host Reactor, asks the router to load `first-model`, waits for
readiness, and then retries dispatch. The Rune's `supports_tools = true` is an operator assertion
used for admission; the settled reply does not prove arbitrary tool calling.

When a non-empty response settles in the Bridge, ask the Pulse for the joined live truth again:

```bash
uv run lychd status
```

You can witness the same cached capability through the **Nexus transition board** at
`http://127.0.0.1:7134/nexus`; `http://127.0.0.1:7134/orchestrator/status` exposes the local JSON
projection. The `atelier:chat:first-model` row should have phase `warm` and `warm: true` after the
settled turn.

**Proof.** First life exists only when all four observations agree:

1. `status` reports a coherent bound installation rather than an unknown or drifted one;
2. its exact owned inventory plus the migration observation above report the expected pod,
   Phylactery, Reactor path, Vessel, Soulstone activity, and successful migration;
3. the Nexus projection reports `atelier` / `chat` / `first-model` as warm after the turn;
4. the Bridge contains a non-empty settled reply.

!!! success "The foundation has answered"
    These four observations form a bounded first-life result for this host, model, driver, and
    image combination. Preserve them with State's required environment, command, timing, log,
    identity, shutdown, and recovery metadata before calling the result a maintained operator
    receipt. They do not prove every accelerator, model, engine, later organ, or hostile-browser
    boundary.

**If it fails.** Start with the joined report, then narrow the log target shown by that report:

```bash
uv run lychd status
uv run lychd logs services --lines 120
```

If the core is healthy but inference fails, recheck the exact model filename, the CDI selector,
VRAM fit, and the model's real tool/chat-template support. Correct the owning Rune and run `bind`
again. `status --help` and `logs --help` expose the target identities implemented by this revision;
do not start the Soulstone by hand as a second activation path.

The canonical `stop` verb already exists, but this revision deliberately refuses to actuate while
the Vessel is alive because its authenticated lifecycle port is not wired. Until that port can
perform a real drain, stop this bounded candidate stack through the explicit host fallback:

```bash
systemctl --user stop \
  lychd-atelier.service \
  lychd-vessel.service \
  lychd-phylactery.service \
  lychd-reactor.path \
  lychd-pod.service
```

Stopping and deleting are separate acts. After this rite, `lychd del --dry-run` must show the
edited Codex and durable Phylactery explicitly because real `del` is intended to erase them. Review
that plan; do not delete the Codex or Phylactery by hand merely to force a clean result.

??? info "Development alternative: uncaged execution"
    Uncaged execution is a distinct developer profile, not a fallback for a broken caged rite. Its
    server, migration, and direct-Systemd entrypoints are intentionally internal rather than public
    Pulse roots. This Summoning therefore provides no copyable uncaged recipe. Keep the caged path
    above as the operator contract until a maintained developer guide proves the complete secret,
    migration, startup, and browser boundary.

You have awakened one bounded body and heard it answer. Enter the [Sepulcher](sepulcher/index.md)
next to learn which organ owns configuration, persistence, inference, execution, and extension. If
any of the four observations is still absent, remain in [The Awakening](#the-awakening) until the
evidence agrees.
