---
title: Personal macOS and Windows hosts
icon: material/laptop
---

# Personal macOS and Windows hosts

Run one trusted Vessel, a dedicated PostgreSQL cluster and a local model under your desktop
account. The bundled Altar opens in your browser. Linux operators can follow the primary
[Summoning guide](../summoning.md). The [platform campaign](https://github.com/hexanomicon/lychd/issues/176)
tracks actual installation and Bridge receipts.

## Choose the installation

Start with a clean personal account or a dedicated test account. Have a checked-out LychD
revision, Git, uv, PostgreSQL **18** and the matching **server-side pgvector extension**.
For chat, supply a trusted native `llama-server` executable built for your OS and one local GGUF
in a private model directory. Choose an instruction-tuned chat model with a working template.
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
and selects it for Bridge. Run it before starting Vessel. Use a separate free port for each engine.

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

## Login, update and removal

For automatic startup use `uv run --no-sync lychd desktop enable-login` under the intended
account once foreground startup works. macOS registers a user LaunchAgent and Windows registers
an interactive, unelevated scheduled task. Both use the installed interpreter. Keep that
environment at its registered path. Disable login with the original interpreter before moving it
or changing credential file references, then register the new environment. These profiles begin at login. They use the rights of
that account, including access to its files. For a shared or hostile workload use a separately
qualified isolation boundary.

- **Paths and credentials.** macOS stores configuration and data under
  `~/Library/Application Support/LychD` and cache under `~/Library/Caches/LychD`. Windows uses
  `%LOCALAPPDATA%\LychD`. Run `lychd platform` for exact subdirectories. The installer stores
  generated credentials in the dedicated data area with per-user filesystem permissions or
  ACLs. Keep the application signing key and browser credential private. The runtime receives
  its restricted DB role. Administrative access belongs to provisioning.
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

For PostgreSQL 18 on one dedicated volume, the source includes a physical backup command. Set up a
private [libpq password file](https://www.postgresql.org/docs/18/libpq-pgpass.html) for the
selected local replication/administrative role and loopback port. Give the file owner-only
access. Use an existing private destination on a separate volume for disk-loss protection.
Find the running cluster's data directory in `desktop status`. Supply the matching PostgreSQL
18 bin directory.

```text
uv run --no-sync python -m lychd.system.pg_backup --pg-bin "<absolute-bin>" --source "<absolute-PGDATA>" --destination "<private-backup-parent>" --port 55432 --user lich --passfile "<absolute-password-file>"
```

The command prints its fresh output directory, streams a physical backup and WAL, verifies both
and writes `verified.json` on success. Protect every physical copy like the active cluster.
For a restore trial, copy its `cluster` directory into a fresh private recovery location, verify
it with the matching `pg_verifybackup`, then start the copy with `pg_ctl` on a separate unused
loopback port and verify a known committed row. Keep the source and restored copies separate.
Leave LychD admission closed during database-only recovery. Application-wide recovery additionally
needs other stores and current revocation history. [Snapshot contract](../adr/07-snapshots.md)

| Capability | Linux | Personal macOS / Windows |
| --- | --- | --- |
| Supervision and isolation | Rootless Podman, systemd/Quadlet, cgroup v2 and reviewed SELinux policy where enabled. | User-owned native services and a trusted engine. A same-user process has access to that user's files. |
| Fast filesystem capture | Btrfs storage preparation is implemented. Whole-installation restore has independent criteria. | APFS and VSS are candidates for volume-level capture. Apple's direct snapshot API needs additional entitlement and superuser authority. VSS requires appropriate backup authority. Qualify creation and recovery before selecting either. |
| VPN and routes | Native Tether has its own [delivery record](../state-of-the-work.md#vpn-tether). | Local chat uses IPv4 loopback. Managing native host VPNs, route overlaps and live revocation requires separate platform evidence. A remote browser must use an explicitly admitted access profile. |
| Credentials and lifecycle | Managed secrets and owned systemd resources have Linux-specific policies. | The personal profile uses private per-user files and OS access controls. Keychain/DPAPI custody, automatic multi-consumer credential rotation and system-wide unattended services need separate qualification. |

[Apple snapshot API](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/fs_snapshot_create.2#L86) ·
[Windows VSS security](https://learn.microsoft.com/en-us/windows/win32/vss/security-considerations-for-requestors) ·
[PostgreSQL physical backup](https://www.postgresql.org/docs/18/app-pgbasebackup.html).

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
