---
title: Platform differences
icon: material/compare-horizontal
---

# LychD on Linux, macOS and Windows

On all three systems you open **Bridge** in a browser to chat. **Vessel** is the server
that connects that chat to your model and database. Linux normally runs Vessel in a rootless Podman container.
Mac and Windows normally run it directly under your login. You can choose either placement
on all three.

**Installation guides**
[Managed Linux](../summoning.md#the-grounds) · [Native on any OS](desktop.md#choose-the-installation) · [Desktop containers](container-desktop.md)

| What do you want to know? | The short answer |
| --- | --- |
| [Where should Vessel run?](#vessel) | Native runs under your OS account. A container limits which host files Vessel sees. |
| [What do I install?](#installation) | Managed Linux needs Podman and systemd. Native installs need PostgreSQL 18, pgvector and a local engine for chat. |
| [Where are my files?](#layout) | Look in your Linux user directories, macOS Library or Windows LocalAppData. Compose owns separate volumes. |
| [What starts and stops it?](#lifecycle) | systemd manages Linux containers. Native runs in a terminal, with optional sign-in startup on Mac and Windows. |
| [How does model A give way to B?](#animators) | Choose native or container per Soulstone. Managed Linux uses systemd. On a desktop, native Vessel or a resident host Reactor owns the switch. |
| [What can a process read?](#authority) | A native engine can read your account’s files. The Compose model receives one read-only model file. |
| [How do the browser and model connect?](#network) | The browser opens a local port. A caged desktop Vessel reaches host-managed models over a mutually authenticated relay. |
| [Who owns PostgreSQL?](#database) | Containers have dedicated database storage. A native install creates a separate cluster for LychD. |
| [Which credentials do I keep?](#credentials) | Keep a separate copy of the credentials. You need them to reopen a restored database. |
| [What can I snapshot or restore?](#snapshots) | Native PostgreSQL supports an independent backup on every OS. Quick local copies depend on Btrfs, APFS or Windows VSS and the chosen setup. |
| [Can I share a service over a VPN?](#tether) | Linux can isolate overlapping peer addresses. Desktop Tether can offer one authenticated service to selected peers. |
| [What survives an upgrade?](#upgrade) | Program files and data have separate lifecycles. Keep a matching database backup and credentials before upgrading. |
| [How do I know chat works?](#qualification) | Send a message, restart, then reopen the same conversation and check the saved reply. |
| [Do I need to set up a VM?](#vm) | Native installs run directly on the host. Controlling a model outside a separate LychD guest is future work. |

## Where should Vessel run? {#vessel}

Choose a placement before installing. Run `lychd platform` to see which installation the
current terminal addresses. Switching the setting selects a different installation with its own data.

### Linux {#vessel-linux}

The default is managed Podman. For native development, set `export LYCHD_VESSEL_MODE=native`
in both terminals. For frontend work with synthetic data, use `make frontend-dev` and
`make developer-fixture`. [Frontend development](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#browser-development-and-its-backend)

### macOS {#vessel-macos}

Native is the default and lets a compatible engine use the Mac GPU. For containers, set
`LYCHD_VESSEL_MODE=container` and point `LYCHD_CONTAINER_DIR` at the prepared Compose project.
[Desktop container setup](container-desktop.md#use-the-installed-desktop-cli)

### Windows {#vessel-windows}

Native runs directly in Windows without WSL. For Docker Desktop, select its Linux engine,
set `$env:LYCHD_VESSEL_MODE = 'container'`, and set `$env:LYCHD_CONTAINER_DIR` to the
prepared project directory. [PowerShell setup](container-desktop.md#use-the-installed-desktop-cli)

## What do I install? {#installation}

Native chat needs PostgreSQL 18, its **server-side pgvector** extension, a trusted
`llama-server` executable and a model file in GGUF format. Run `lychd desktop install` as
your ordinary user. For dedicated-volume snapshots, select the volume **before** installing.
[Native prerequisites](desktop.md#choose-the-installation) · [Choose storage](volume-snapshots.md#select-storage-and-grant-capture)

### Linux {#installation-linux}

Managed Linux needs systemd user services with lingering, cgroup v2, and rootless Podman
and Quadlet 5.4+. Quadlet turns container definitions into systemd services. Build the CLI and
image from the same revision and run `lychd init --dry-run` first. [Linux install](../summoning.md#the-grounds)

### macOS {#installation-macos}

The Apple Silicon `.pkg` includes the app and Python. Install it under your existing login
and run LychD from a normal Terminal without `sudo`. An administrator-capable login works.
Install PostgreSQL 18, pgvector and the model engine separately.
[Verify the package](desktop-packages.md#verify-and-install-an-edition) · [Run the installed Mac edition](desktop-packages.md#run-the-macos-edition)

### Windows {#installation-windows}

Use the x64 per-user `.exe` or the source checkout. Point `LYCHD_PG_BIN` at PostgreSQL’s
`bin` directory and keep the engine DLLs beside `llama-server.exe`. [Windows prerequisites](desktop.md#choose-the-installation)

## Where are my settings and data? {#layout}

`lychd platform` prints the native settings, data and cache paths. Portable Compose keeps its
database and credentials in project volumes owned by the container engine. [Compose storage](container-desktop.md#logs-shutdown-and-recovery)

### Linux {#layout-linux}

Managed defaults are `~/.config/lychd` for settings, `~/.local/share/lychd` for data and
`~/.cache/lychd` for cache. Native uses `lychd-native` under each of the same XDG roots.
[Linux paths and mounts](../adr/13-layout.md#host-and-container-geography)

### macOS {#layout-macos}

Open `~/Library/Application Support/LychD` for native `config` and `data`. Cache lives in
`~/Library/Caches/LychD`. Installed editions live separately in `~/Applications/LychD Editions`.

### Windows {#layout-windows}

Open `%LOCALAPPDATA%\LychD` for native `config`, `data` and `cache`. Program files live in
`%LOCALAPPDATA%\Programs\LychD Editions`. A dedicated drive can hold the database.

## How do I start and stop it? {#lifecycle}

**Native on all three systems:** run `lychd desktop session` in one terminal to start PostgreSQL
and Vessel. Use `lychd access` in a second terminal under the same login for the browser
address and password.
Shut down with `lychd stop`, then `lychd desktop stop`. In a prepared source checkout,
prefix these commands with `uv run --no-sync`. [Foreground session](desktop.md#open-altar-and-talk-in-bridge)

### Linux {#lifecycle-linux}

For managed Linux, `lychd start` brings up the systemd user services. **Plan shutdown first.**
The public `lychd stop` currently refuses an active managed Vessel. [Start services](../summoning.md#the-awakening) · [Shutdown procedure](../summoning.md#close-the-rite)

### macOS {#lifecycle-macos}

`lychd desktop enable-login` registers the working native installation with launchd as a
per-user LaunchAgent. It starts that edition at sign-in. [Login setup](desktop.md#login-update-and-removal)

### Windows {#lifecycle-windows}

The same command registers the interpreter in the current user's Registry Run key. Older
scheduled-task registrations keep working until disabled. [Sign-in setup and command-length limit](desktop.md#login-update-and-removal)

## How does LychD switch from model A to model B? {#animators}

Configure A and B as conflicting models. In **Nexus**, the model-selection screen, choose B,
open **Preview** to see that A will stop, request the transition, and wait for B to become
active. With the native two-model setup, also select a model before the first chat after
startup. [Set up two models](desktop.md#choose-between-two-local-models-in-nexus)

| Vessel and lifecycle owner | Native Soulstone | Container Soulstone |
| --- | --- | --- |
| Managed Linux, host systemd | Fixed single-model llama.cpp user service with private Unix socket and a pod-loopback relay | Runtime-specific Quadlet in the same conflict graph |
| Personal native Vessel, desktop account | Owned foreground llama.cpp child on the host | Operator-provisioned fixed-model TLS container bound by exact ID |
| Portable Reactor project, resident desktop owner | The same host child, reachable from the guest through authenticated inference | The same fixed container, lifecycle managed on the host |
| Base portable Compose or its CPU chat overlay | — | The chat overlay starts one fixed CPU model with the stack |

### Linux {#animators-linux}

Managed Vessel asks the [Host Reactor](../sepulcher/reactor.md) to submit one target
transaction. A personal native Vessel can switch its own child and a container on a local
rootless engine. It uses `/proc` to verify a child's listener. [Managed Rune setup](../sepulcher/extensions/animators/soulstone/rune.md#choose-placement)

### macOS {#animators-macos}

The desktop owner checks a native child's listening port with `lsof`. Container switching
requires an account-owned local engine socket, for rootless Podman or Docker, or Docker Desktop.
launchd may start the native Vessel at sign-in. [Configure a container binding](desktop.md#animator-ownership)

### Windows {#animators-windows}

The desktop owner verifies `llama-server.exe` with `netstat.exe`. For a container, use Docker
Desktop's local Linux-engine pipe. Windows Podman is outside this binding. The
[portable Reactor setup](container-desktop.md#desktop-reactor) puts either placement behind a
caged Vessel. Check [State of Work](../state-of-the-work.md#current-evidence-envelope) for the
host combinations exercised.

## What can Vessel and the model access? {#authority}

**A native engine process can read files its OS account can read.** It gets private scratch
space and a filtered environment. To keep personal documents out of reach while using a native
GPU, install under a separate standard account and restrict your documents to your own login.
The Compose model receives one read-only GGUF file from the host. Foreign code needs its own
sandbox in either placement. [Native file access](desktop.md#which-host-files-can-a-native-vessel-read) · [Mounts by container](container-desktop.md#which-files-does-each-container-receive)

### Linux {#authority-linux}

Managed Vessel gets read-only settings and selected data and secrets. It submits model switches
through a mounted inbox. The Host Reactor validates each request. The container has no Podman
socket or systemd bus. Native installation directories use mode `0700`. [Host permissions](../adr/10-privilege.md)

### macOS {#authority-macos}

Native chat, model switching and installed extensions use the login account’s access.
Whole-volume snapshots require a separately authorized storage operator.

### Windows {#authority-windows}

Native Vessel refuses to run elevated. Use NTFS permissions to keep personal files private
from its standard account. The storage operator runs the privileged VSS step separately.

## How do the browser and engine connect? {#network}

Open `http://127.0.0.1:7134/` for the default local browser interface. Signing in checks
the connection to Vessel. A reply in Bridge also checks the model connection. [Open Bridge](desktop.md#open-altar-and-talk-in-bridge)

### Linux {#network-linux}

Managed container services communicate inside their Podman pod. The pod relay for a
native engine connects to its private host socket. The browser reaches the published loopback port. Native Vessel and its engine use the host's loopback directly.

### macOS {#network-macos}

Native Vessel forwards the model's configured endpoint, for example `127.0.0.1:8082`, to
the verified engine process on the Mac. The portable CPU model runs inside its stack.
The Reactor overlay instead reaches host-owned models through TLS on port 17134.

### Windows {#network-windows}

Native Vessel reaches a Windows-native engine over loopback. In the portable Reactor project,
Vessel connects to `host.docker.internal:17134` for authenticated inference and submits switches
through a mounted inbox. [Compose networking and mount checks](container-desktop.md#desktop-reactor)

## Who owns PostgreSQL? {#database}

A native install creates a dedicated cluster, normally at `127.0.0.1:55432`. Vessel uses a
restricted database role. Another PostgreSQL service can coexist on a different port.
[Database setup](desktop.md#choose-the-installation)

### Linux {#database-linux}

Managed PostgreSQL has its own container and data mount. A separate service applies schema
migrations before Vessel starts. [Managed startup](../summoning.md#the-awakening)

### macOS {#database-macos}

Native data defaults to `data/postgres/native-data` under LychD’s Application Support directory.
Rerunning `lychd desktop install` checks that cluster and applies migrations.

### Windows {#database-windows}

The installation account owns the native cluster. To capture snapshots on a dedicated NTFS
drive, register the live cluster against that drive. [Registration procedure](volume-snapshots.md#select-storage-and-grant-capture)

## Which credentials do I need for recovery? {#credentials}

Native installs generate five values for database access, application signing and browser
login. Keep an independent protected copy and check it with
`lychd desktop verify-credential-backup`. [Backup, rotation and recovery](desktop.md#login-update-and-removal)

### Linux {#credentials-linux}

Native uses private credential files. Managed Linux mounts each Podman secret read-only into
the service that needs it. Save the matching secrets and configuration separately from the
database snapshot. [Managed secrets](../summoning.md#the-secret-covenant)

### macOS {#credentials-macos}

Private files are the default. You can move the values into your login Keychain after
verifying the portable backup. Keep that backup for recovery under a new account.

### Windows {#credentials-windows}

Optional DPAPI encryption ties stored values to the Windows account. A fresh Windows
profile needs the portable backup to recover them.

## What do backups and snapshots restore? {#snapshots}

**For disk failure**, all three native profiles can stream a verified PostgreSQL backup to
independent storage with `lychd desktop backup --destination …`. A dedicated-volume restore
creates an inactive database copy in a new directory and leaves the original cluster in place.
Reopening LychD also requires matching configuration, credentials and current revocations.
[Database backup](desktop.md#storage-networking-and-recovery) · [Volume restore drill](volume-snapshots.md#recover-a-committed-row-on-a-disposable-installation)

### Linux {#snapshots-linux}

Managed installation can create a Btrfs subvolume for a new database. A coordinated
snapshot and restore of the whole installation is still a design. [Btrfs setup](../adr/13-layout.md#postgresql-substrate) · [Whole-installation restore status](../state-of-the-work.md#whole-body-snapshot-restore)

### macOS {#snapshots-macos}

An **APFS clone** briefly stops PostgreSQL and makes a copy on the same disk. A test recovered
a committed row from that copy. A **whole-volume APFS snapshot** uses a dedicated volume and a
separate authorized producer. A successful whole-volume restore still needs a host trial.
[Clone procedure](desktop.md#storage-networking-and-recovery) · [Volume snapshots](volume-snapshots.md)

### Windows {#snapshots-windows}

The **Volume Shadow Copy Service (VSS)** snapshots a dedicated fixed NTFS drive while PostgreSQL
is stopped. An authorized operator creates the snapshot. The standard account verifies it.
Windows Server 2025 recovered a captured row and excluded a later write. Windows 11 still
needs its own provider check and restore drill. [VSS capture](volume-snapshots.md#capture)

## Can I offer a service to a VPN peer? {#tether}

**Tether** gives an authorized peer access to a specific service. The desktop helper offers
one TCP service over WireGuard. The owner's Bridge chat stays local. [Desktop service setup](desktop-tether.md#start-and-admit)

### Linux {#tether-linux}

Choose `tether-container-v1` during managed initialization. Each imported peer attachment
gets its own pod, so a private IP can appear on two attachments and still identify the right
peer on each. [Managed Tether](tumbleweed/index.md#native-tether-profile-protocol-2)

### macOS {#tether-macos}

Run `desktop-tether` as your user. Each peer gets a separate userspace network. The helper
forwards to one local TLS service that authenticates callers and leaves Mac routes and DNS alone.

### Windows {#tether-windows}

Run `desktop-tether.exe` under a standard account. Arrange a reachable UDP port and any
required firewall or router rule. Restart clears the grants. Stop the helper before sleep
or hibernation until resume has been tested. [Revoke and reconnect](desktop-tether.md#revoke-stop-and-recover)

## How do I upgrade or remove LychD? {#upgrade}

Keep the old revision, its pre-upgrade database backup and the matching credentials. After
the upgrade, reopen a known conversation. [Desktop upgrade and recovery](desktop-packages.md#repair-upgrade-recover-or-remove)

### Linux {#upgrade-linux}

Keep the managed CLI, image and generated configuration together. Before removal, settle the
services and inspect `lychd del --dry-run` for affected files and any Btrfs operation that
needs an administrator. [Managed removal](../summoning.md#close-the-rite)

### macOS {#upgrade-macos}

Stop Vessel and disable login through the old edition before changing editions. Install the
new edition alongside it and run `lychd desktop install`. Removing an edition preserves account data.

### Windows {#upgrade-windows}

Disable the old login registration before changing interpreters. Reinstall the same edition
to repair program files. Uninstalling through **Installed apps** retains the account's data.

## How can I tell whether chat works? {#qualification}

Send a distinctive message in Bridge and note its saved Run ID. Restart Vessel and PostgreSQL,
reopen the conversation, and check the reply, model and ID. [Recorded trials](../state-of-the-work.md#current-evidence-envelope)

### Linux {#qualification-linux}

Native Linux passed the browser test. For managed Linux, check the migration service and
`lychd logs --lines 120`. Switching on the target Quadlet/GPU host still needs a hardware trial.
[Linux checks](https://github.com/hexanomicon/lychd/issues/179)

### macOS {#qualification-macos}

Chrome passed on macOS 15 Apple Silicon. Cold sign-in, GPU performance, physical Docker
Desktop, whole-volume restore and public installer acceptance have separate checks.
[Mac checks](https://github.com/hexanomicon/lychd/issues/177)

### Windows {#qualification-windows}

Edge passed on Windows Server 2025 x64 under a standard account. Windows 11 hardware,
cold sign-in, physical Docker Desktop, SmartScreen and the local VSS provider still need
workstation checks. [Windows checks](https://github.com/hexanomicon/lychd/issues/178)

## Do I need to manage a virtual machine? {#vm}

Native LychD runs directly on the OS. Docker Desktop supplies its containers’ Linux
environment. Using a separate LychD guest to control the outer host is a future deployment
option. [VM design and requirements](desktop.md#virtual-machines)

### Linux {#vm-linux}

A Linux guest can host its own managed installation. Its services, storage and loopback
belong to the guest. [Linux guest qualification](tumbleweed/qualification.md)

### macOS {#vm-macos}

Native mode reaches a Mac engine today. Switching it from a separate guest would require
a private network route and an authorized operation on the Mac.

### Windows {#vm-windows}

WSL and Podman guests have their own loopback. Connecting to a Windows engine would require
a tested listener, firewall and return route. Restarting that engine would also require
host-side authorization.
