---
title: Personal macOS and Windows hosts
icon: material/laptop
---

# Personal macOS and Windows hosts

Run one trusted Vessel, a dedicated PostgreSQL cluster and a local model under your desktop
account. The bundled Altar opens in your browser. Linux operators can follow the primary
[Summoning guide](../summoning.md). The [platform campaign](https://github.com/hexanomicon/lychd/issues/176)
tracks hardware qualification. Native trials recovered the same conversation after restarting
PostgreSQL and Vessel on macOS 15 Apple Silicon with Chrome and Windows Server 2025 x64
with Edge. See the [dated receipts in State of Work](../state-of-the-work.md#current-evidence-envelope).
The Windows 11 workstation and cold-login trials are tracked in the platform issues below.

## Choose the installation

For a packaged Python runtime and bundled web client, follow [Desktop editions](desktop-packages.md).
The source installation below uses uv.

Start with a clean personal account or a dedicated test account. Have a checked-out LychD
revision, Git, uv, PostgreSQL **18** and the matching **server-side pgvector extension**.
For chat, supply a trusted native `llama-server` executable built for your OS and one local GGUF
in a private model directory. Choose an instruction-tuned chat model with a working template.
Bridge validates structured replies. For the small CPU trial, use the
[Qwen2.5-0.5B-Instruct Q4_K_M fixture](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/blob/9217f5db79a29953eb74d5343926648285ec7e67/qwen2.5-0.5b-instruct-q4_k_m.gguf).
Its SHA-256 is `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`.
A model can answer a raw API request and still fail Bridge's reply validation.

The Python `postgres-binary` extra supplies a database *client*. The installer provisions its
own cluster and role credentials using your installed server tools. A separate PostgreSQL
system service or an existing application database can keep its own port and data.

| Target | Prepare this machine |
| --- | --- |
| macOS · Apple Silicon | Install the matching tools, for example `brew install postgresql@18 pgvector llama.cpp`. In the terminal for this setup run `export LYCHD_PG_BIN="$(brew --prefix postgresql@18)/bin"`. Check `"$LYCHD_PG_BIN/initdb" --version` and `command -v llama-server`. |
| Windows · x64 | Install the PostgreSQL 18 server tools and [pgvector for that PostgreSQL installation](https://github.com/pgvector/pgvector#windows). Install the matching [llama.cpp Windows release](https://github.com/ggml-org/llama.cpp/releases) and keep its DLLs beside the executable. In PowerShell set `$env:LYCHD_PG_BIN = 'C:\Program Files\PostgreSQL\18\bin'` and run `& "$env:LYCHD_PG_BIN\initdb.exe" --version`. Administrator access, if required by the dependency installer, ends before running LychD. |

From the repository directory, use the same revision and environment for the following commands.
The desktop paths below target the locked Python 3.14.8 environment.

```shell
uv sync --locked --no-default-groups --extra postgres-binary --no-editable --python 3.14.8
uv run --no-sync lychd platform
uv run --no-sync lychd desktop install
```

`platform` reports the detected OS, profile and absolute settings, configuration, data and cache
paths. The installer starts a dedicated loopback PostgreSQL on port 55432 by default, installs
`vector` in the application and Phoenix databases, applies migrations and verifies restricted
runtime access. Another service holding that port must be reconciled. Existing user-authored
settings remain authoritative. Re-running install checks the dedicated cluster and applies the
current revision's migrations.

## Connect a real model

Substitute actual existing paths, including the full executable filename. The following command
declares the `personal:chat:personal-model` capability, enables the built-in llama.cpp extension
and selects it for Bridge. The generated Rune enables llama.cpp's JSON-schema output for
structured replies without active function tools. Tool-enabled requests retain the separate
tool protocol. The personal Rune also uses `f16` for both key and value caches. Lower cache
precision saves memory and can change model answers. Recheck Bridge after tuning it. Run
this command before starting Vessel. Use a separate free port for each engine.

```bash title="macOS"
uv run --no-sync lychd desktop configure-model \
  --engine "$(command -v llama-server)" --model "$HOME/Models/chat.gguf"
```

```powershell title="Windows PowerShell"
uv run --no-sync lychd desktop configure-model --engine 'C:\Models\llama.cpp\llama-server.exe' --model 'C:\Models\chat.gguf'
```

Keep the resulting settings and Rune with this installation. Installed extensions continue to
load through the [extension registry](../sepulcher/extensions/index.md). The native actuator
accepts trusted, fixed-model llama.cpp processes on IPv4 loopback. A router, an arbitrary
program or an untrusted extension requires its own execution contract. An unresolved prior
transition blocks startup until the operator verifies the recorded process and port.

### Choose between two local models in Nexus

Start with the working `personal` model above. Stop the foreground Vessel with
`uv run --no-sync lychd stop` before editing. Keep the second GGUF under the same
`native_model_root` and check that port 8082 is free. In the configuration directory reported
by `lychd platform`, create a new `runes/animator/soulstones/llamacpp/alternate.toml`.
Use the actual absolute model path. TOML single quotes also accept literal Windows paths
such as `'C:\Models\alternate.gguf'`.

```toml title="alternate.toml"
name = "alternate"
startup_mode = "single"
structured_output = "json-schema"
cache_type_k = "f16"
cache_type_v = "f16"
model_path = '/absolute/path/to/Models/alternate.gguf'
served_model_id = "alternate-model"
port = 8082
base_url = "http://127.0.0.1:8082/v1"
```

Both Runes use the default exclusive conflict declaration. Starting one evicts the other.
Each needs its own name, model identity and loopback port. Keep the existing engine and
extension settings. In the existing `[weaver.bridge]` table of `lychd.toml`, replace the
generated `capability_key` selection with this two-route preference. Save any previous
custom Bridge selection you intend to restore.

```toml title="lychd.toml"
[weaver.bridge]
revision = "2"

[weaver.bridge.preference]
schema_version = 1
routes = [
  { capability_key = "personal:chat:personal-model", weight = 1 },
  { capability_key = "alternate:chat:alternate-model", weight = 1 },
]
```

Start `uv run --no-sync lychd desktop session`. In **Nexus**, choose the desired capability,
open **Preview**, check the launch and eviction names, and choose **Request transition**.
Wait for the selected capability to show **active**, then send a fresh Bridge turn. With
this preference Bridge requires a warm, eligible route, including for the first turn after
startup. To change models while Vessel is running, repeat the Nexus transition for the other
capability. Open **Orb** for each Run and compare the recorded Animator and model identities.
[Using Nexus](../divination/altar/nexus.md) · [Bridge preference at admission](../adr/22-dispatcher.md#bridge-preference-at-admission).

## Open Altar and talk in Bridge

1. Start the database and Vessel from this account in a foreground terminal with
   `uv run --no-sync lychd desktop session`. Leave that terminal open.
2. In a second private terminal run `uv run --no-sync lychd access`. Open
   `http://127.0.0.1:7134/` in a dedicated browser profile and enter the displayed credentials
   when prompted. Keep the credentials out of screenshots, URLs and shell history.
3. Open **Bridge** beside Orb or navigate to `/bridge`. Choose **New Séance** and send a
   distinctive short message. Wait for a nonempty settled reply. In Nexus verify the selected
   `personal:chat:personal-model` capability. Record the exact revision, engine, model, OS and
   CPU/GPU. Opening the shell alone proves only the web assets and local login.
4. Run `uv run --no-sync lychd stop` in the second terminal and wait for the foreground process
   to exit. Start `desktop session` again, sign in and reopen the same conversation. Verify the
   distinctive message and reply survived. For the platform issue, attach redacted screenshots
   of the settled turn and the reopened conversation.

To stop the database too, run `uv run --no-sync lychd desktop stop` after the Vessel exits.
`lychd start` runs only the foreground Vessel when its database is already running.
`lychd desktop status` queries the dedicated PostgreSQL cluster. A second Vessel targeting the
same database must refuse before startup recovery can affect the first one's work.

The automated qualification uses a disposable OS account, the same CLI and a real browser.
For reproducible short replies it sets `temperature = 0.0` and `max_tokens = 128` in the
personal Rune’s `[generation]` table. Operators can choose a larger output budget. The trial
saves the opened Bridge, the completed reply, the same reply after restarting PostgreSQL and
Vessel, and a JSON receipt with the Run ID and the model and engine hashes. Maintainers can run
the **Desktop host CI** workflow with the browser-chat input selected. Retrieve its
`desktop-bridge-macOS` and `desktop-bridge-Windows` artifacts from that run. Use the platform
issues below for hardware, GPU and cold-login trials.

## Login, update and removal

For automatic startup use `uv run --no-sync lychd desktop enable-login` under the intended
account once foreground startup works. macOS registers a user LaunchAgent and Windows registers
a current-user `Run` registry value with the installation identifier and quoted interpreter path.
Existing Windows scheduled tasks retain their original enrollment until disabled. Windows caps
a Run command at 260 UTF-16 code units. If the edition path exceeds this bound, start
`lychd desktop session` after sign-in. [Windows Run keys](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys).
New registrations launch the installed interpreter in isolated
mode, so Python ignores user-site packages and inherited Python environment settings. Existing
registrations keep their original invocation until disabled and re-enabled. Keep the registered
environment at its original path. Disable login with the original interpreter before moving it
or changing credential file references, then register the new environment. These profiles begin at login. They use the rights of
that account, including access to its files. For a shared or hostile workload use a separately
qualified isolation boundary.

- **Paths and credentials.** macOS stores configuration and data under
  `~/Library/Application Support/LychD` and cache under `~/Library/Caches/LychD`. Windows uses
  `%LOCALAPPDATA%\LychD`. Run `lychd platform` for exact subdirectories. The installer stores
  generated credentials in the dedicated data area with per-user filesystem permissions or
  ACLs. Keep the application signing key and browser credential private. The runtime receives
  its restricted DB role. Administrative access belongs to provisioning.
- **Credential recovery.** Back up the entire generated `desktop-credentials` directory
  separately from the PostgreSQL cluster, using encrypted storage. Before relying on the
  backup, recover the directory into a fresh owner-only location and run
  `lychd desktop verify-credential-backup "<recovered-directory>"` under the installation
  account. The command compares all five recovered values against the active generated set without
  displaying their contents. Keep externally supplied credentials and their file references
  recoverable through their own provider. When restoring a cluster, recover the matching
  credentials under the destination account before starting the Vessel or running install.
  An existing cluster requires the original credentials or explicit overrides.
- **Opt-in OS credential custody.** After verifying that independent backup, run
  `lychd desktop enable-vault "<recovered-directory>"` under the installation account.
  Each generated file is atomically replaced after a successful OS readback. macOS stores
  the value in the login Keychain. Windows stores a DPAPI CurrentUser envelope at the
  original private path. Runtime and administrative processes retain their existing sets
  of file references. A locked Keychain or unavailable Windows profile stops the read.
  An interrupted migration can be rerun with the same backup. A copy of the vault references
  alone cannot recover access under a fresh user profile.
  [Apple Keychain items](https://developer.apple.com/documentation/security/keychain-items) ·
  [Windows DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)
- **Recovery into a fresh account.** Recover the original five portable files into a private
  directory under that account. Run `lychd desktop recover-credentials "<recovered-directory>"`
  before installing against the restored dedicated cluster. This verifies every input before
  filling missing credentials and stops on disagreement with an existing value. If restored
  files reference a former account's vault, add `--rebind-vault` to seal matching portable values
  under this account. This requires a record carrying a portable verifier. Keep unreadable
  older records in an encrypted archive and use a fresh credential directory for recovery.
  Then run
  `desktop install`, sign in, check a known persisted conversation and re-enable the OS
  vault with that account if desired.
- **Runtime database password.** Stop Vessel and keep its dedicated PostgreSQL running.
  Use `lychd desktop rotate-runtime-password --recovery-directory "<empty-private-directory>"`.
  It verifies the cluster and managed runtime role, stages a new recovery set, changes the
  SCRAM password, disconnects existing sessions for that role, and verifies a fresh
  login before reopening desktop operations. Repeat the same command and destination after
  interruption. A pending rotation can restart its own database after a reboot while Vessel
  admission stays closed. Store the updated five-file recovery copy encrypted. The administrative,
  Phoenix and browser credentials keep their independent lifecycles.
- **Update.** Obtain a verified backup before changing a populated installation. Stop Vessel,
  disable login for the update, and keep the current revision and configuration. Install the new
  revision into the intended environment and run `desktop install`, then repeat the persisted
  Bridge check before enabling login. PostgreSQL major-version migration needs its own upgrade.
  Once a newer generation accepts writes, restoring an old database discards those writes.
- **Uninstall.** Stop Vessel, then run `uv run --no-sync lychd desktop uninstall`. It removes the
  owned login registration and stops the dedicated database. Settings, credentials, model files
  and database contents are preserved. Verify which data and recovery credentials you need
  before disposing of your package environment. Shared PostgreSQL and llama.cpp installations
  retain their own uninstall procedures.

## Storage, networking and recovery

With the desktop database running, select an existing owner-only backup directory. Use a separate
volume for disk-loss protection. The desktop command reads the installed administrative
credential, checks the running server against the registered cluster and uses its PostgreSQL 18
tools. The destination on Windows must grant access only to the current user.

```text
uv run --no-sync lychd desktop backup --destination "<private-backup-parent>"
```

The command prints its fresh output directory, streams a physical backup and WAL, verifies both
and writes `verified.json` on success. Protect every physical copy like the active cluster.
For a restore trial, copy its `cluster` directory into a fresh private recovery location, verify
it with the matching `pg_verifybackup`, then start the copy with `pg_ctl` on a separate unused
loopback port and verify a known committed row. Keep the source and restored copies separate.
Leave LychD admission closed during database-only recovery. Application-wide recovery additionally
needs other stores and current revocation history. [Snapshot contract](../adr/07-snapshots.md)

On macOS, a second option makes a copy-on-write clone of the dedicated database on the same
APFS volume. Stop Vessel, leave its database running, and create a private destination
outside the cluster. Run `lychd desktop backup --method apfs-clone --destination "<directory>"`.
This pauses PostgreSQL, clones each file, restarts the original and hashes the inactive copy.
The receipt records pause time, total time, free space and per-file hashes. A matching-volume
clone shares disk failure risk with the source. Use the streamed backup for independent media.
An actual volume snapshot uses the [dedicated storage procedure](volume-snapshots.md).
[Apple clonefile semantics](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/bsd/man/man2/clonefile.2)

| Capability | Linux | Personal macOS / Windows |
| --- | --- | --- |
| Supervision and isolation | Rootless Podman, systemd/Quadlet, cgroup v2 and reviewed SELinux policy where enabled. | User-owned native services and a trusted engine. A same-user process has access to that user's files. |
| Fast filesystem capture | Btrfs storage preparation is implemented. Whole-installation restore has independent criteria. | [Dedicated volume setup and recovery](volume-snapshots.md) bind the volume and PostgreSQL identity to a cold cut. APFS requires an authorized producer. Windows VSS creation belongs to the storage operator. |
| VPN and routes | Native Tether has its own [delivery record](../state-of-the-work.md#vpn-tether). | Local chat uses IPv4 loopback. The [desktop Tether helper](desktop-tether.md) offers one certificate-pinned service over a private userspace WireGuard connection for each admitted peer. A remote browser must use an explicitly admitted access profile. |
| Credentials and lifecycle | Managed secrets and owned systemd resources have Linux-specific policies. | Private per-user files, opt-in Keychain/DPAPI custody and explicit recovery of the original generated set. System-wide unattended services have separate qualification requirements. |

[Apple snapshot API](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/fs_snapshot_create.2#L86) ·
[Windows VSS security](https://learn.microsoft.com/en-us/windows/win32/vss/security-considerations-for-requestors) ·
[PostgreSQL physical backup](https://www.postgresql.org/docs/18/app-pgbasebackup.html).

### Connect a desktop browser to a Linux host

When the same owner runs Core on Linux, a desktop browser can use that deployment's admitted
same-owner SSH loopback binding. Follow the [Tether operator guide](../sepulcher/aspects/tether.md)
for the binding, browser origin and independent revocation check. The Linux host retains
responsibility for tunnel and service configuration.

## Animator ownership

On Linux the Reactor applies the declared conflicts through systemd and generated Quadlets.
In the personal profile the same orchestration contract selects the native process actuator.
Vessel starts a configured executable using fixed arguments, verifies ownership of its loopback
listener, and waits for the conflicting foreground process to exit before launching its replacement. Login registration starts
Vessel under the desktop account. A request to Bridge grants no general host command execution.

We considered llama-swap for its model routing and swap matrix. Adding it as another lifecycle
owner would require coordinating its independent unload decisions with LychD's grants and
observations. The personal profile uses the existing llama.cpp extension and the native process actuator. A future
adapter for an externally managed server needs its own authority and readiness contract.
[Upstream swap matrix](https://github.com/mostlygeek/llama-swap/blob/a109800cc5340e7722895b7baf78b3d16ef19311/docs/kb/guides/routing/groups-and-matrix.md)
· [Containers and switching](../adr/08-containers.md).

## Virtual machines

A separately selected Linux guest can bring its own Linux services and storage. A future LychD
VM profile must prove guest lifecycle, private networking and access to the specific host engine.
The guest sees its own loopback interface. Test any provider-supplied host address from the actual
Vessel container. Outbound inference and inbound VPN traffic have different firewall and routing
requirements. Guest root grants no authority on the outer host. Managing a host process would
require an authenticated, narrowly scoped host helper, an allowlist of targets and recovery after
lost acknowledgement. Keep unrestricted host commands, the container-engine socket and host
credentials outside the guest. [Privilege](../adr/10-privilege.md) · [VPN](../adr/39-vpn.md).

Follow implementation of [volume snapshots](https://github.com/hexanomicon/lychd/issues/182),
[desktop Tether](https://github.com/hexanomicon/lychd/issues/183) and
[signed OS packages and credential recovery](https://github.com/hexanomicon/lychd/issues/184).

Track hands-on qualification in [macOS #177](https://github.com/hexanomicon/lychd/issues/177),
[Windows #178](https://github.com/hexanomicon/lychd/issues/178) and
[Linux #179](https://github.com/hexanomicon/lychd/issues/179).
