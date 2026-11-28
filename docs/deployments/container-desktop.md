---
title: Portable container Vessel
icon: material/docker
---

# Run Vessel in containers on a personal computer

Choose this profile when you want the caged Vessel image on macOS, Windows or Linux. The
desktop supplies a local Linux container engine. Compose starts PostgreSQL 18 with pgvector,
runs LychD's schema and role migration, and opens the compiled Altar on desktop loopback.
The chat overlay adds one fixed CPU model. To switch Animators on the desktop, use the
[Reactor project](#desktop-reactor) with a resident host owner. For an entirely native
Vessel, use the [personal profile](desktop.md). Managed Linux has its own
[systemd/Quadlet deployment](../summoning.md).

## Prepare the local engine and images

Use Docker Desktop in Linux-container mode on macOS or Windows, or a local Linux Docker
Engine with Compose. Use Engine 28 or newer for loopback-only publishing and Compose v2 or
newer with support for completion and health dependencies. Run the following in a dedicated,
clean checkout of the source revision you intend to install, as your ordinary desktop user.
Inspect the active context and its endpoint before building. It must refer to the local
engine you control. The `OSType` result must be `linux`. Keep port 7134 available and choose
a fresh Compose project named `lychd-portable` for the first installation. A running native
Vessel on the same port needs its own planned shutdown. [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/) · [Compose startup dependencies](https://docs.docker.com/compose/how-tos/startup-order/)

```console
docker context show
docker context inspect
docker version
docker info --format "{{.OSType}}"
docker compose version
docker compose ls --all
git rev-parse HEAD
docker build -f Containerfile -t localhost/lychd:portable-base .
cd deployments/portable-container
docker compose -f compose.yaml build vessel
```

The second build layers the portable configuration and credential provisioning program on
the selected production image. Build both images on the same engine and keep the exact
revision and image IDs. Give the engine sufficient guest memory, CPU and disk for PostgreSQL,
the images and your chosen model. The full GGUF stays on your disk.

## Start Core or add one CPU model

For Core and Altar alone, inspect the resolved deployment and start it from that directory.

```console
docker compose -f compose.yaml config
docker compose -f compose.yaml up -d
```

For local chat, select one local GGUF compatible with llama.cpp's chat template and the
guest CPU. On macOS or Linux, pass the absolute path to the file and verify it is a readable
regular file before starting Compose.

```bash
export LYCHD_GGUF='/absolute/path/to/personal-model.gguf'
test -f "$LYCHD_GGUF" && test -r "$LYCHD_GGUF"
```

In Windows PowerShell use the path available to the same desktop account running Docker.

```powershell
$env:LYCHD_GGUF = 'C:\Models\personal-model.gguf'
Get-Item -LiteralPath $env:LYCHD_GGUF -ErrorAction Stop | Select-Object FullName, PSIsContainer, Length
```

Require a non-empty file (`PSIsContainer = False` on Windows). The overlay mounts that exact
file read-only in the model service. Its container user must be able to read it. Choose the
same pair of Compose files for every command on a chat installation.

```console
docker compose -f compose.yaml -f compose.chat.yaml config
docker compose -f compose.yaml -f compose.chat.yaml up -d
docker compose -f compose.yaml -f compose.chat.yaml ps -a
docker compose -f compose.yaml -f compose.chat.yaml port database 8000
```

### Use the installed desktop CLI

After building both images, the installed macOS or Windows CLI can operate this same
project. From the `deployments/portable-container` directory, set the following in your
terminal. Include the single-file `LYCHD_GGUF` setting above for chat. Use the same model
selection and project directory whenever you return to this installation.

```bash
export LYCHD_VESSEL_MODE=container
export LYCHD_CONTAINER_DIR="$PWD"
```

```powershell
$env:LYCHD_VESSEL_MODE = 'container'
$env:LYCHD_CONTAINER_DIR = (Get-Location).Path
```

```console
lychd platform
lychd start
lychd status
lychd access
lychd logs
```

Expect `provision` and `migrate` to have exited with code 0, PostgreSQL and the selected model
to be healthy, and `vessel` to be running. The port command must report `127.0.0.1:7134`.
The service named `database` owns the shared container network namespace. Inside it,
PostgreSQL listens on loopback at 5432 and the optional model at 8080. Only the Vessel's
internal port 8000 has a desktop mapping. Check the actual mappings and listeners on the
desktop provider before admitting a browser. The model's health endpoint must report ready
before Compose starts the chat Vessel. A cold or failed model needs repair in that service.
The Core and CPU chat profiles have a read-only inbox. Host switching requires the separate
Reactor project below.
[Compose networking](https://docs.docker.com/compose/how-tos/networking/) · [llama.cpp server images](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md)

## Switch desktop-owned models from a caged Vessel {#desktop-reactor}

Use the separate Compose project `lychd-portable-reactor`. It has its own database and
credential volumes. Settle and stop any installation using port 7134 or the same native
Animator state before starting. Existing data and lifecycle journals stay with their original
installations.

1. **Configure the host.** Use the same LychD revision for the host CLI and container images.
   In a host terminal, select `LYCHD_VESSEL_MODE=native`. Use the native installation's
   `lychd.toml`, existing owner-only `native_state_dir` and dedicated Soulstone Runes. Enable
   each Rune's runtime in `[extensions].builtins`, for example `animator/llamacpp`. Follow
   [Connect a real model](desktop.md#connect-a-real-model) for a host-native GGUF, or
   [Animator ownership](desktop.md#animator-ownership) for a pre-created TLS container. Set the
   Bridge capability or route preference in that host configuration. Leave the native Vessel
   stopped so the Reactor can hold its lifecycle lock.
2. **Prepare the guest.** Run `lychd desktop reactor-prepare` in that host terminal. It prints
   a JSON object with `LYCHD_REACTOR_BUNDLE`, `LYCHD_REACTOR_INBOX`, `LYCHD_REACTOR_JOURNAL`
   and `LYCHD_REACTOR_UID`. Set all four environment variables to those exact values in a
   separate Compose terminal. Leave `LYCHD_GGUF` unset. The UID selects the guest image user
   for the private mounts. The directories and generated identities belong to the installation
   account.
3. **Start the owner.** In the host terminal run `lychd desktop reactor-serve` and leave it
   running. Its default listener is `127.0.0.1:17134`. If the provider cannot forward to host
   loopback, pass `--listen` with a specific private host IP reachable from its guest. The
   Compose default is `host.docker.internal`. The guest also accepts
   `LYCHD_DESKTOP_REACTOR_HOST=host.containers.internal` where the provider supplies that
   alias. This overlay requires a provider that supplies a reachable alias inside Vessel's
   shared database network namespace. Check this on Linux Docker Engine as well as Docker
   Desktop. If neither alias works there, the independent native Vessel and managed Linux
   installations remain available. Port 17134 carries mutually authenticated inference and
   startup verification. The host reads switch requests from the mounted inbox.
4. **Start the guest.** Build `localhost/lychd:portable-base` from the repository's
   [production Containerfile](#prepare-the-local-engine-and-images). From
   `deployments/portable-container`, build the Reactor Vessel for the returned UID if its tagged
   image is absent or needs rebuilding. The provisioner and migrator use the same image.
   Inspect the resolved configuration, then start the project.

```console
docker compose -p lychd-portable-reactor -f compose.yaml -f compose.reactor.yaml build vessel
docker compose -p lychd-portable-reactor -f compose.yaml -f compose.reactor.yaml config
docker compose -p lychd-portable-reactor -f compose.yaml -f compose.reactor.yaml up -d --wait
```

On macOS and Windows the [installed portable CLI](#use-the-installed-desktop-cli) selects this
same project when its environment contains the prepared paths. Keep the host terminal in native
mode. The guest verifies three separate mounts, the read-only bundle and host journal, and the
writable inbox. It checks the host's live session and configuration before opening the projected
loopback model routes. Engine sockets, native executable access and the host's private TLS key
stay with the desktop owner.

Select a model in Nexus, request the transition and wait for readiness. Send a Bridge turn and
check its model grant in Orb. Repeat with a conflicting target. For a coordinated shutdown,
settle work, then use the same project and both Compose files with `down` (retain the volumes)
before stopping the resident owner. If the state is ambiguous, preserve the inbox, host journal
and native state, including `native.sqlite3`, for reconciliation.

The generated host and guest certificates are valid for 365 days. To rotate them, settle and
stop the guest and host owner. Move the `identities` directory beside the inbox into private
host-only archival storage. Preserve the inbox, journal and native state. Run `lychd desktop reactor-prepare`
again, set the returned bundle and other environment values, then restart the host and guest.
For changed Runes or bindings, retain the identities and repeat preparation and startup after
settling and stopping both processes.
The base portable chat receipt below covers its own profile. Desktop-provider networking, file
sharing, lifecycle and recovery for this overlay need a trial on the selected platform.
[Deployment evidence](../state-of-the-work.md#current-evidence-envelope)

## Which files does each container receive?

| Service | Reads | Writes |
| --- | --- | --- |
| Vessel | Its image, runtime database password, application signing key and browser credential | Its guard journal, lab and temporary storage |
| PostgreSQL | Its image and bootstrap database password | Its dedicated database volume and runtime filesystem |
| Migration | Administrative, runtime and Phoenix database credentials | Schema and roles through the database connection, plus temporary storage |
| Optional CPU model | Its image and the single GGUF mounted read-only | Temporary storage |

The one-shot provisioner creates the credentials before these services start. Vessel receives
no desktop home, database data directory, administrative password, model shelf or engine socket.
Its image filesystem is read-only. Vessel and the model each have a 128 MiB temporary filesystem
with `nosuid,nodev,noexec`. The profile limits Vessel and the database to 512 tasks each and
the optional model to 1,024. Threads count towards these limits. These services share a network
namespace, so reachable services still need their own access controls.
[Compose service settings](https://docs.docker.com/reference/compose-file/services/#pids_limit)

## Open Altar and check a retained turn

Retrieve the password in a private terminal using the Compose file selection for this
installation. For the Reactor project use the CLI's `lychd access` or substitute its project
name and files below. In the example the chat overlay is active. Use the username `magus`.

```console
docker compose -f compose.yaml -f compose.chat.yaml exec -T vessel cat /run/lychd/access/value
```

Open `http://127.0.0.1:7134/` in a dedicated local browser profile. A fresh unauthenticated
request to `/api/v1/altar/status` must receive HTTP 401. Authenticate in the browser. For
chat, choose **New Séance** in Bridge, send one distinctive message and check the retained
reply and its Orb Run. For the CPU chat overlay, the dispatch must name `personal:chat:personal-model`. Record the
session and Run IDs. Reopen those same records after an authorized restart using the same
project, files, model and volumes. Include the host/engine versions, image IDs, GGUF hash
and listener observations in the receipt. [Operator receipt requirements](../state-of-the-work.md#operator-receipt-requirements)

The [Linux Compose browser receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/runtime/bridge-portable-linux-2026-11-18.json)
records a real CPU model answer and the same Run and model grant after recreating all containers
and reopening Chrome. The [Docker CI trial](https://github.com/hexanomicon/lychd/actions/runs/44311383918)
verified credentials and committed PostgreSQL data across recreation. Test port publication,
restart and the browser on the actual macOS or Windows Desktop provider during host qualification.

## Logs, shutdown and recovery

Use `docker compose -f compose.yaml -f compose.chat.yaml logs --tail 100 migrate vessel model`
on the chat profile or `docker compose -f compose.yaml logs --tail 100 migrate vessel` on
Core. A failed migration blocks Vessel startup. A missing runtime credential can be recovered
from the project's original seed. If projected credentials disagree with that seed, provisioning
stops before changing them.

Compose stores the database, runtime guard, lab and separate credentials in project-scoped
named volumes in the selected engine. The provisioning container alone sees the seed. Vessel
receives the application secret, browser password and runtime database credential. The model
receives its GGUF. Protect the engine account and backups. A provider reset, changing Docker
contexts or deleting volumes can strand or destroy the installation. Native desktop archives
and macOS Keychain or Windows DPAPI CurrentUser credentials belong to the native installation.

Plan retirement before startup. The caged application has the [managed stop limitation](../summoning.md#close-the-rite).
For an independently authorized cold shutdown after admission has closed and all work has
settled, use `docker compose -f compose.yaml -f compose.chat.yaml down` for the chat profile
or `docker compose -f compose.yaml down` for Core. These commands retire project containers
and the network while retaining named volumes. Preserve those volumes together with a
matching database backup, revision and model identity. Re-run the original `up -d` command
for that installation. A clean stop, restore to a fresh destination, device sleep/resume and
browser recovery each need their own observation on the selected desktop provider.
[Compose shutdown and volumes](https://docs.docker.com/reference/cli/docker/compose/down/) · [Deployment evidence](../state-of-the-work.md#current-evidence-envelope)
