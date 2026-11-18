---
title: Platform differences
icon: material/compare-horizontal
---

# Platform differences across Linux, macOS and Windows

**Where does Vessel run?** Linux is the primary managed host. Its Vessel (the LychD application server) defaults to a rootless Podman container. Set `LYCHD_VESSEL_MODE=native` to run it directly on Linux too. On macOS and Windows, a personal installation runs Vessel, PostgreSQL and the selected inference engine as native processes under one ordinary account. All three serve the compiled Altar in a browser and can retain a Bridge conversation across restart. Set `LYCHD_VESSEL_MODE` to `native` or `container` to choose explicitly. On macOS and Windows the container choice uses a separate Docker Desktop Compose installation. Run `lychd platform` to see the selected profile and its paths or Compose project. [Choose and install a profile](index.md) · [Supported host policy](../adr/08-containers.md#supported-host-policy)

| If you're deciding… | Jump to |
| --- | --- |
| What to install, where the files go, or how to run Vessel from source | [Installation](#installation), [layout](#layout), [native Vessel and development](#vessel) |
| Who starts a service, who can stop it, or how A yields the GPU to B | [Lifecycle](#lifecycle), [Animator switching](#animators), [host authority](#authority) |
| How the browser, model or another machine reaches a service | [Local networking](#network), [Tether and routing](#tether), [virtual machines](#vm) |
| Where the database and secrets live, or what a snapshot restores | [PostgreSQL](#database), [credentials](#credentials), [snapshots and recovery](#snapshots) |
| How to upgrade safely or reproduce a result on your machine | [Upgrade and removal](#upgrade), [diagnostics and qualification](#qualification) |

## Installation and runtime dependencies {#installation}

### Linux {#installation-linux}

Start with the systemd user manager, lingering for the runtime user, cgroup v2, rootless Podman and its effective Quadlet user generator. Both Podman and the generator must meet the 5.4 minimum. The worked GPU installation additionally uses NVIDIA CDI and an operator-supplied GGUF. Build the host CLI and Vessel image from the same revision, keep the checkout at a stable path, then run `lychd init --dry-run` and inspect both host readiness and the filesystem plan. Initialize, configure the model, preview the binding and bind. Binding writes the owned units and reloads the user manager. Agree an operator recovery plan before first startup. The public stop command currently refuses an active managed Vessel. [Linux prerequisites and install](../summoning.md#the-grounds) · [Tumbleweed provisioning](tumbleweed/index.md)

### macOS {#installation-macos}

The Apple Silicon edition is a per-user `.pkg`. Its revision directory contains Python, the locked application, compiled Altar and the desktop Tether helper. Bring PostgreSQL 18 with its matching **server-side pgvector** and, for local chat, a trusted macOS `llama-server` and GGUF. Set `LYCHD_PG_BIN` to the PostgreSQL 18 bin directory and use the edition's interpreter to run `lychd desktop install`. The source guide gives the equivalent uv command and Homebrew paths. If you want whole-volume captures, select the dedicated storage *before* first installation. [macOS prerequisites](desktop.md#choose-the-installation) · [Install an edition](desktop-packages.md#verify-and-install-an-edition)

### Windows {#installation-windows}

The x64 desktop edition is a per-user `.exe`. Install matching native PostgreSQL 18 server tools and pgvector, and keep the Windows llama.cpp DLLs with `llama-server.exe`. In PowerShell set `$env:LYCHD_PG_BIN` to the actual PostgreSQL bin directory and run `lychd desktop install` from the chosen edition as the desktop user. Any administrator action required by an external dependency installer ends before provisioning the LychD database. A source checkout can use the locked uv environment. This procedure runs entirely in Windows. [Windows prerequisites](desktop.md#choose-the-installation) · [Edition commands for PowerShell](desktop-packages.md#verify-and-install-an-edition)

## Files, configuration and persistent data {#layout}

### Linux {#layout-linux}

The **Codex** holds editable settings and Runes (TOML declarations), by default in `~/.config/lychd`. The **Crypt** holds persistent state under `~/.local/share/lychd`, and cache defaults to `~/.cache/lychd`. XDG overrides relocate these roots. Quadlets go under `$XDG_CONFIG_HOME/containers/systemd`, plain user units under `$XDG_CONFIG_HOME/systemd/user`, with `~/.config` as the default base. Native mode instead uses sibling `lychd-native` directories under each XDG root for its settings, private credentials, database and cache. Changing modes never adopts or migrates the other installation. The model shelf stays outside the managed roots. Vessel mounts the Codex read-only and receives only the particular state directories it needs. PostgreSQL owns its data mount. [Layout and mount ownership](../adr/13-layout.md#host-and-container-geography)

### macOS {#layout-macos}

Settings and Runes live in `~/Library/Application Support/LychD/config`, persistent state in the neighboring `data` directory and cache in `~/Library/Caches/LychD`. A packaged interpreter lives separately in `~/Applications/LychD Editions/<revision>`. Point the model Rune at a real file under the configured model root. Changing the edition directory does not move the database, model or credentials. Use the `settings` field printed by `lychd platform` to find the file this account will read. [Personal desktop paths and credentials](desktop.md#login-update-and-removal)

### Windows {#layout-windows}

The account's `%LOCALAPPDATA%\LychD` contains `config`, `data` and `cache`. Program files live under `%LOCALAPPDATA%\Programs\LychD Editions\<revision>`. In a Rune use an absolute Windows path, for example a TOML literal string such as `'C:\Models\chat.gguf'`. A dedicated database volume relocates the cluster while its storage binding, grants and revocation records stay on the account disk. Use `lychd platform` from the intended account before editing or copying files. [Desktop layout](desktop.md#login-update-and-removal) · [Volume selection](volume-snapshots.md#select-storage-and-grant-capture)

## Vessel placement and local development {#vessel}

### Linux {#vessel-linux}

Choose either placement before installation. The default `LYCHD_VESSEL_MODE=auto` and explicit `container` both select the **managed container Vessel** on Linux. PostgreSQL, migrations and admitted local model services also have their own units. The old `--native-only` and `--uncaged` flags refuse before changing the host. For a **native Linux Vessel**, set `export LYCHD_VESSEL_MODE=native` in both terminals, prepare PostgreSQL 18 and pgvector, and run `lychd desktop install`. Configure your local model and run `lychd desktop session`. Use `lychd access` in the second terminal. `lychd stop` gracefully retires this native Vessel, and `lychd desktop stop` then stops its dedicated database. [Native setup and commands](desktop.md#choose-the-installation)

For frontend work alone, `make frontend-dev` runs Vite and `make developer-fixture` supplies a disposable API with synthetic data. For a real persisted conversation use the compiled Altar served by either installed Vessel. [Linux binding](../summoning.md#retired-host-native-bindings) · [Browser development](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#browser-development-and-its-backend)

### macOS {#vessel-macos}

**A developer can run Vessel directly from source.** After installation and model configuration, run `uv run --no-sync lychd desktop session` in the prepared checkout. It starts the dedicated PostgreSQL and serves the compiled Altar in the foreground. Use a second terminal in the same environment for `lychd access` (with the same uv prefix). A working Bridge turn uses the actual database and model. A packaged edition runs the same `desktop session` through its bundled interpreter. For a containerized Vessel, set up the [portable Compose project](container-desktop.md), select `LYCHD_VESSEL_MODE=container` and point `LYCHD_CONTAINER_DIR` at its reviewed directory. `lychd start` then starts the prepared stack in the local Linux engine. Its database and optional CPU model live inside that deployment. [Start a session and verify a turn](desktop.md#open-altar-and-talk-in-bridge)

### Windows {#vessel-windows}

Run `uv run --no-sync lychd desktop session` from the prepared checkout in PowerShell, or `lychd desktop session` through the packaged edition function. Vessel and PostgreSQL run under the Windows account and the engine runs as a native Windows child process when selected. The native path needs no container engine. To run the container build instead, prepare [Docker Desktop with its Linux engine and Compose project](container-desktop.md), set `$env:LYCHD_VESSEL_MODE = 'container'` and `$env:LYCHD_CONTAINER_DIR` to that absolute directory. `lychd start`, `status`, `logs` and `access` then address the portable deployment. A second Vessel pointed at the same database must refuse startup. [Source setup and foreground session](desktop.md#open-altar-and-talk-in-bridge)

## Startup, shutdown and login supervision {#lifecycle}

### Linux {#lifecycle-linux}

`lychd start` brings up the pod, PostgreSQL, the migration gate, Host Reactor and Vessel through systemd user units. Lingering lets this user manager outlive an interactive login. Use `lychd status` for inventory, then check that `lychd-migrate.service` finished successfully. Plan shutdown before first startup. At this revision the public `lychd stop` refuses an active managed Vessel. Handling that case requires the separately authorized operator recovery procedure and evidence that the owned units settled. [Startup](../summoning.md#the-awakening) · [Active-Vessel stop boundary](../summoning.md#close-the-rite)

### macOS {#lifecycle-macos}

`desktop session` starts both database and Vessel. With PostgreSQL already running, `lychd start` starts Vessel alone. `lychd stop` retires Vessel, then `lychd desktop stop` can stop its database. To start at sign-in, use `lychd desktop enable-login` after the foreground path works. It installs the account's `org.lychd.vessel` LaunchAgent bound to that installation's interpreter. Disable that registration from the original edition before changing editions. An unattended system daemon would have a different identity and key access. [Login and shutdown](desktop.md#login-update-and-removal)

### Windows {#lifecycle-windows}

The same foreground and graceful stop commands apply. New `desktop enable-login` registrations use the current user's Registry `Run` key to start the exact installed interpreter in isolated mode at sign-in. Existing scheduled-task registrations keep their original provider until disabled. LychD installs no machine-wide Windows service. If the quoted command exceeds the 260 UTF-16 code-unit limit, use foreground `desktop session` after sign-in. `desktop status` reports the dedicated database's state. Confirm Vessel separately in the browser. [Windows login and registration limits](desktop.md#login-update-and-removal)

## Animator switching, conflicts and hardware {#animators}

### Linux {#animators-linux}

A native Linux Vessel uses the personal fixed-model process actuator under the ordinary user and checks its child’s TCP listener through `/proc`. On managed Linux, to switch from A to B, Nexus previews which declared Animators will stop and start. Vessel submits a typed transition to the **Host Reactor**. The compiler translates hardware conflict domains into generated systemd targets with ordered `Conflicts=` and `After=` edges. The host validates the pre-transition state, actuates the owned targets and observes their terminal state before model readiness is assessed. For the worked llama.cpp GPU Rune, the model shelf is mounted read-only and the device is selected through NVIDIA CDI. Model fit and actual GPU inference require observation on that host. [Unit graph and conflicts](../adr/08-containers.md#current-unit-graph) · [Example model Rune](../summoning.md#inscribe-the-rune)

### macOS {#animators-macos}

Configure a trusted native `llama-server` executable and a fixed GGUF with `lychd desktop configure-model --engine … --model …`. For two exclusive engines, give A and B distinct Rune names, served model IDs and free loopback ports, and configure the Bridge preference. In Nexus preview and request B. Vessel's native actuator stops its owned A process, waits for exit, launches B and uses `lsof` to confirm the child owns its private upstream listener. With the two-route preference, activate one eligible engine in Nexus before the first Bridge turn after startup. If enabled, the LaunchAgent starts the session at login. The actuator owns the model switch. The native path allows a hardware-capable engine build, while the browser trial establishes no Metal throughput figure. [Two-engine example](desktop.md#choose-between-two-local-models-in-nexus)

### Windows {#animators-windows}

The same fixed-model Runes and Nexus request select a managed `llama-server.exe`. Vessel starts the configured executable with fixed arguments, waits for the conflicting owned process to exit and matches the new child's private loopback listener to its PID using the system `netstat.exe`. A process already holding the port or a transition with unresolved ownership blocks admission. Verify the served identity and Orb grant after switching. Both desktop browser trials switched A → B → A using distinct processes and served names with the same pinned weights. Arbitrary native services, external inference daemons and non-inference Animators need their own actuator contract. Neither desktop profile requires llama-swap. [Animator ownership](desktop.md#animator-ownership) · [Switching receipts](../state-of-the-work.md#current-evidence-envelope)

## Host authority, isolation and extensions {#authority}

### Linux {#authority-linux}

In native mode the installer protects the config, data and cache roots with mode `0700`.
It gives each model launch a private working directory. For native GPU use with a separate
user, install the engine and weights on a user- or root-owned path and keep personal data private to
your own login. For per-container mount enforcement, use the managed profile.
[Native filesystem access](desktop.md#which-host-files-can-a-native-vessel-read)

In managed container mode, Vessel can write a bounded transition request to its mounted inbox and read the Host Reactor's transition journal at `triggers/journal`. A systemd path unit wakes the host consumer. Authority comes from validating the typed request, configuration, ownership and observed state. A changed file alone authorizes nothing. The container receives neither a Podman socket nor a systemd bus. The Host Reactor exposes only its declared operations. Trusted code, selected mounts, rootless isolation and the applicable host SELinux policy each constrain a different part of the deployment. Some storage operations require an independently authorized administrator acting on an exact identity. [Host Reactor and privilege](../adr/10-privilege.md) · [Container mount boundaries](../adr/13-layout.md#host-and-container-geography)

### macOS {#authority-macos}

For native development with personal documents kept private, use a separate standard macOS
login and keep those documents inaccessible to that login. The model gets private temporary
storage for each launch and can use Metal with the account's normal permissions. For a mount
boundary around Vessel itself, the portable container attaches its runtime secrets read-only
and keeps the chosen GGUF in the model container. [Native filesystem access](desktop.md#which-host-files-can-a-native-vessel-read) · [Portable mounts](container-desktop.md#which-files-does-each-container-receive)

The personal account already has permission to launch its own trusted engine. Vessel invokes its scoped actuator directly. Normal chat and switching need no root daemon, watched command file or password prompt. The same-user engine can access files available to that account, so install only trusted engines and extensions. An approved OS utility and its operator own privileged whole-volume snapshot creation separately. Adding an extension to the registry does not authorize host operations. [Host policy](../adr/08-containers.md#supported-host-policy) · [Extension contract](../adr/05-extensions.md)

### Windows {#authority-windows}

Native startup and credential retrieval inspect the process token and refuse elevation. A
dedicated standard Windows account can read the GGUF you grant it while an NTFS access
control list excludes it from your private documents. Its fresh working directory also serves
as the model's temporary and AppData directories. For mount-level restrictions choose the
portable container. [Native filesystem access](desktop.md#which-host-files-can-a-native-vessel-read) · [Portable mounts](container-desktop.md#which-files-does-each-container-receive)

Vessel and its engine run with the ordinary user's token. Private file ACLs protect against other ordinary accounts. Code running as the installation user can exercise that user's access. Keep elevated dependency setup and the one-shot VSS producer outside the running Vessel. Neither Nexus nor Bridge provides generic PowerShell execution, service control or elevation. Untrusted workloads require a separately qualified isolation boundary on either desktop. [Privilege boundaries](../adr/10-privilege.md) · [Desktop storage authority](volume-snapshots.md#capture)

## Browser and inference networking {#network}

### Linux {#network-linux}

Open the compiled Altar at `http://127.0.0.1:7134/` with the local credential from `lychd access`. The managed topology places core services and ordinary local Soulstones in the generated pod. The host browser reaches the published loopback web listener. Vessel reaches the engine at the address declared for its pod topology. Verify engine readiness separately from HTTP availability of Altar. A broad host port publication would change the access boundary. [Generated topology](../adr/08-containers.md#current-unit-graph) · [Authenticated browser access](../summoning.md#the-awakening)

### macOS {#network-macos}

Native Vessel and the native engine share the Mac's IPv4 loopback. For example, the browser reaches Vessel on `127.0.0.1:7134` and the documented B Rune publishes its model API at `http://127.0.0.1:8082/v1`. Vessel reserves that stable port and relays requests to the active child's verified private loopback port. No host alias, container port forward or LAN listener is needed. Authenticate in the browser, send a message and check the settled Run in Orb to exercise both links. [Local model routes](desktop.md#choose-between-two-local-models-in-nexus) · [Local browser access](desktop.md#open-altar-and-talk-in-bridge)

### Windows {#network-windows}

Native Windows Vessel, database, model and browser use the same Windows loopback. A port in use must be reconciled or the affected service configured on a free port. The Rune names a stable loopback endpoint owned by Vessel. Its relay connects to the child's separately allocated port and verifies socket ownership before forwarding request bytes. `host.containers.internal` is not part of this setup and the LychD installer creates no such entry. For a client connecting to a separate Linux installation, use the access arrangement admitted by that installation's owner. [Local session](desktop.md#open-altar-and-talk-in-bridge) · [Desktop browser with a Linux host](desktop.md#connect-a-desktop-browser-to-a-linux-host)

## PostgreSQL provisioning and ownership {#database}

### Linux {#database-linux}

The Phylactery is the managed PostgreSQL service with pgvector. Its unit owns the database mount under the Crypt at `postgres/data`. Migration is a separate unit ordered before Vessel. Administrative and runtime credentials are scoped to their consumers. On an existing deployment, preserve the dedicated data and verify the migration result and committed Run after restart. An active unit alone cannot establish either. [Managed startup](../summoning.md#the-awakening) · [Persistence](../adr/06-persistence.md)

### macOS {#database-macos}

`desktop install` uses the selected PostgreSQL 18 tools to provision a dedicated cluster on IPv4 loopback, port 55432 by default. It sets up roles, enables pgvector in the application and Phoenix databases, runs migrations and verifies restricted runtime access. A separate Homebrew server can retain its own port and data. Rerunning install checks the registered cluster and respects existing user-authored settings. The default cluster directory is `data/postgres/native-data` under Application Support/LychD. [PostgreSQL preparation](desktop.md#choose-the-installation)

### Windows {#database-windows}

The account owns a dedicated cluster through the native PostgreSQL tools. An existing system PostgreSQL service can coexist on a different port. Verify `initdb.exe` and that pgvector belongs to this server installation. The Python binary extra bundles the client. For dedicated-volume operation, select the fixed NTFS drive before provisioning. Startup verifies the selected storage binding, and maintenance checks the configured endpoint owns the expected data directory. [Windows PostgreSQL setup](desktop.md#choose-the-installation) · [Storage registration](volume-snapshots.md#select-storage-and-grant-capture)

## Credential custody and recovery {#credentials}

### Linux {#credentials-linux}

Native Linux uses separate ordinary-user credential files and a portable recovery set. The managed binding provisions missing core Podman secrets and assigns individual read-only secret mounts to the consumers that need them. The web process uses the restricted database role. The migration service has separate provisioning authority. `lychd access` displays the local browser credential in a private terminal. Preserve the secrets and configuration for recovery independently of the data snapshot. [Secret references](../summoning.md#the-secret-covenant) · [Container secret mounts](../adr/08-containers.md)

### macOS {#credentials-macos}

The installation generates five private values covering the runtime, administrative and Phoenix database passwords, application signing key and local browser credential. Back up their portable files separately and run `desktop verify-credential-backup` against a recovered copy. Opt-in `desktop enable-vault` uses the login Keychain. A locked Keychain can stop reads. For a new account, recover the matching portable values and use explicit vault rebinding when applicable. After managed runtime password rotation, store the new recovery set. [Credential backup, rebinding and rotation](desktop.md#login-update-and-removal)

### Windows {#credentials-windows}

Private per-user files are the default. Optional vault enrollment uses Windows DPAPI CurrentUser, with an encrypted envelope at the original private path. A copy of the envelope alone cannot recover the values under a fresh profile. Retain an independent encrypted backup of the five portable values. Restore them before installing against a restored database, then rebind former vault records where supported. A pending runtime password rotation blocks normal admission until resumed with its original recovery directory. [Windows credential lifecycle](desktop.md#login-update-and-removal)

## Database snapshots, backups and restore {#snapshots}

### Linux {#snapshots-linux}

Native Linux provides the streaming PostgreSQL physical backup documented in [desktop recovery](desktop.md#storage-networking-and-recovery). In managed mode, a fresh, absent PostgreSQL data target on trusted Btrfs can be created as its own subvolume with its filesystem UUID, subvolume UUID and subvolume ID recorded. Initialization attempts and checks the No-COW inheritance flag on this new directory. A failed flag check yields a warning. Existing data stays in place. The Linux layout code also recognizes ext4 identities for lifecycle purposes. Btrfs preparation establishes storage identity. The coordinated checkpoint that freezes writes, captures the stores, verifies current consent and reopens LychD remains **Designed**. A Tumbleweed OS snapshot protects a different scope. No ZFS capture workflow is qualified here. [PostgreSQL substrate](../adr/13-layout.md#postgresql-substrate) · [Whole-body recovery status](../state-of-the-work.md#whole-body-snapshot-restore)

### macOS {#snapshots-macos}

Choose by recovery objective. For disk loss, `lychd desktop backup --destination …` streams a PostgreSQL physical backup with WAL to independent storage and verifies it. The hosted Mac trial restored a committed row from this backup. For a quick copy on the same APFS volume, stop Vessel, leave its dedicated database running and select a private destination outside the cluster. Then `desktop backup --method apfs-clone --destination …` stops PostgreSQL, clones each file, restarts the original and hashes the copy. A second PostgreSQL instance recovered the captured row and excluded a later write. The measured database pause was 1.068 seconds for that fixture. Both source and clone depend on the same disk. This procedure applies to a natively provisioned database. A portable Compose installation keeps its PostgreSQL data in the engine’s volume. [Backup and clone procedure](desktop.md#storage-networking-and-recovery)

For a **whole-volume APFS snapshot**, select a dedicated volume before install, register it against the running cluster, stop Vessel and begin `desktop volume capture`. An authorized snapshot producer creates and mounts the snapshot while PostgreSQL is cold. LychD checks the native identity, read-only mount and database cut, then records the seal off-volume. The hosted whole-volume trial covers registration and missing-snapshot refusal. A positive capture and restored row using the authorized producer still need a target receipt. [Dedicated volume procedure and restore drill](volume-snapshots.md)

### Windows {#snapshots-windows}

The same running PostgreSQL backup with WAL is available for independent media. The hosted Windows trial restored a committed row from that backup as well. For VSS, reserve a **dedicated fixed NTFS drive** and select it before installation. `desktop volume register` binds the volume and live database identities. Stop Vessel and begin capture as the desktop owner. A storage operator runs the reviewed one-shot DiskShadow producer from an elevated console. The standard account verifies the protected receipt, kernel mapping and read-only exposure, then records the off-volume seal. Keep the snapshot, exposure, receipt and grant together for restoration. [VSS capture and retention](volume-snapshots.md#capture)

Windows Server 2025 recovered a captured row in a separate PostgreSQL 18 instance, excluded a later write and refused a revoked capture. The fixture paused PostgreSQL for 11.721 seconds, including the producer step. The Mac and Windows timings cover different operations and do not predict downtime for your database. Windows 11 still needs a provider check and restore drill. On both desktops, restoring database files yields an inactive copy. Opening LychD also requires matching credentials, configuration and current revocations. [Recovery drill](volume-snapshots.md#recover-a-committed-row-on-a-disposable-installation) · [Checkpoint contract](../adr/07-snapshots.md)

## Private networking, VPN and Tether {#tether}

### Linux {#tether-linux}

Select the managed `tether-container-v1` profile during original initialization for native Tether protocol 2. A rootless pod serves the offered peer network. Independent imported attachments get separate pods and generation-specific consumer sockets, so the same private IP on two attachments can name two different peers. Selection binds the attachment, peer, generation and authorized service. A transport failure closes that route. The optional same-owner SSH browser binding has its own admission. An administrator-managed WireGuard network and restricted SSH forward are a separate deployment choice. [Protocol 2 setup](tumbleweed/index.md#native-tether-profile-protocol-2) · [Tether delivery and remaining host checks](../state-of-the-work.md#vpn-tether)

### macOS {#tether-macos}

Run the separate `desktop-tether` helper under the desktop account to offer **one TCP service**. Each admitted WireGuard peer gets a userspace network stack, its own encrypted UDP listener and one exact private destination. The helper forwards to a loopback TLS service after checking its certificate and name. The service must authenticate remote callers. macOS routes, interfaces and DNS stay under the operator's control. The owner Bridge stays on loopback and is excluded from this offered-service profile. [Start the helper and admit a peer](desktop-tether.md#start-and-admit)

### Windows {#tether-windows}

`desktop-tether.exe` offers the same scoped service under an ordinary token. The owner arranges a reachable UDP endpoint and any needed firewall permission or NAT mapping. The peer uses an exact service route and checks for local routing conflicts. Revoking one grant closes its live streams while the other peer can continue. A fresh helper starts with zero grants and requires explicit enrollment again. End the helper before sleep or hibernation pending qualification of resumed in-memory authority. [Peer revocation and restart](desktop-tether.md#revoke-stop-and-recover)

## Editions, upgrades and removal {#upgrade}

### Linux {#upgrade-linux}

Keep the source revision, built image and generated configuration together. Tumbleweed host provisioning, OS snapshot upgrades and application upgrades have different owners. For LychD removal start with `lychd del --dry-run` after settling the running installation. The lifecycle receipt bounds the objects eligible for retirement. An eligible Btrfs subvolume that needs root yields an exact handoff for the administrator. Retain unresolved storage or service identities for reconciliation. [Linux retirement](../summoning.md#close-the-rite) · [OS snapshot upgrade qualification](tumbleweed/qualification.md)

### macOS {#upgrade-macos}

Keep the prior edition, matching pre-upgrade database backup and portable credentials. Stop Vessel, retire login and the database through the old edition, install the new edition alongside it and run `desktop install`. Reopen a known conversation before enabling login again. Removing one revision's program directory leaves account data intact. Test candidates have revision and digest provenance. Signed public distribution also requires Developer ID identities, notarization and Gatekeeper verification. [Edition repair, upgrade and removal](desktop-packages.md#repair-upgrade-recover-or-remove)

### Windows {#upgrade-windows}

Use the old edition to retire its login registration before selecting a new interpreter. Reinstalling the same edition can repair program files. **Installed apps** removes the matching program revision while the account retains its data. To recover an earlier database after a migration, restore the matching pre-upgrade backup into a fresh destination and verify a committed row. A signed public installer requires the expected Authenticode signer and timestamp. CI exercises unsigned candidates and specific tested upgrade pairs. [Windows edition verification and recovery](desktop-packages.md)

## Diagnostics and hands-on qualification {#qualification}

### Linux {#qualification-linux}

Use `lychd logs --lines 120` and the user journal to distinguish Vessel, migration and model failures. Check unit state, migration result, an authenticated Bridge reply, the selected model in Orb and that same Run after restart. The recorded Chrome trial used a production image and a manually assembled rootless pod. The [native Linux receipt](../state-of-the-work.md#current-evidence-envelope) separately covers an installed foreground Vessel, two exclusive model switches and a retained Bridge answer on openSUSE Tumbleweed. A separate generated-target test covered managed conflict handling. End-to-end deployment and switching on the generated Quadlet/GPU host remain assigned to Linux qualification. [Evidence and receipts](../state-of-the-work.md#current-evidence-envelope) · [Linux host trial #179](https://github.com/hexanomicon/lychd/issues/179)

### macOS {#qualification-macos}

Start in the foreground to see startup errors, check the dedicated database with `lychd desktop status`, then use `lychd access` and send a distinctive Bridge message. Compare the Run ID, model grant and reply before and after restarting PostgreSQL, Vessel and Chrome. The hosted trial did this on macOS 15 Apple Silicon. Physical cold sign-in, hardware acceleration, whole-volume snapshot recovery and signed installer acceptance each require their own observation. [Hosted evidence](../state-of-the-work.md#current-evidence-envelope) · [macOS host trial #177](https://github.com/hexanomicon/lychd/issues/177)

### Windows {#qualification-windows}

Perform the same restart and retained-Run check from a standard account. Record the Windows build, engine and model, browser, chosen accelerator and any separate elevated storage step. Edge on Windows Server 2025 x64 exercised real chat, native switching and persistence. Windows 11 hardware, cold sign-in, GPU behavior, SmartScreen acceptance and the local VSS provider remain separate target checks. [Hosted evidence](../state-of-the-work.md#current-evidence-envelope) · [Windows host trial #178](https://github.com/hexanomicon/lychd/issues/178)

## Virtual machines and outer-host access {#vm}

### Linux {#vm-linux}

A Linux guest can be the machine on which you qualify the managed Linux profile. Its systemd instances, storage identities, loopback interfaces and permissions belong to the guest. A disposable QEMU test of a Tumbleweed OS upgrade qualifies that upgrade scenario. Managing an outer-host engine or restoring the whole LychD installation requires separate evidence and authority. [OS upgrade trial](tumbleweed/qualification.md) · [Future VM profile](desktop.md#virtual-machines)

### macOS {#vm-macos}

The personal profile already reaches a native Mac engine over loopback. The portable Compose option keeps PostgreSQL and the optional engine inside the Linux provider. A future container-in-VM Vessel would need a verified private route to that engine and an authenticated host-side operation to switch it. Reaching an inference endpoint gives the guest only the API exposed there. Guest root does not grant Mac process-control rights. Incoming Tether connections would need a separately tested route. [VM boundaries](desktop.md#virtual-machines)

### Windows {#vm-windows}

WSL or a Podman machine introduces a Linux guest with its own loopback. For any future guest profile, test the provider's host address from the actual Vessel container, the Windows listener and firewall scope, and return traffic. A name such as `host.containers.internal` alone proves neither reachability nor permission to restart an engine. Native Windows operation bypasses that boundary. The portable Compose installation publishes Altar to Windows loopback and keeps the database and optional model in the provider. [VM networking and host authority](desktop.md#virtual-machines)
