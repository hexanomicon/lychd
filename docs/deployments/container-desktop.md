---
title: Portable container Vessel
icon: material/docker
---

# Run Vessel in containers on a personal computer

Choose this profile when you want the caged Vessel image on macOS, Windows or Linux. The
desktop supplies a local Linux container engine. Compose starts PostgreSQL 18 with pgvector,
runs LychD's schema and role migration, and opens the compiled Altar on desktop loopback.
An optional CPU llama.cpp service provides one already-loaded model for Bridge. If your
priority is a native GPU engine, login service or Animator switching, use the
[personal native profile](desktop.md). On Linux the [managed Quadlet profile](../summoning.md)
provides the Host Reactor and generated service graph.

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
The caged Vessel has a read-only Reactor inbox and cannot launch a host engine.
[Compose networking](https://docs.docker.com/compose/how-tos/networking/) · [llama.cpp server images](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md)

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
installation. In the example below the chat overlay is active. Use the username `magus`.

```console
docker compose -f compose.yaml -f compose.chat.yaml exec -T vessel cat /run/lychd/access/value
```

Open `http://127.0.0.1:7134/` in a dedicated local browser profile. A fresh unauthenticated
request to `/api/v1/altar/status` must receive HTTP 401. Authenticate in the browser. For
chat, choose **New Séance** in Bridge, send one distinctive message and check the retained
reply and its Orb Run. The dispatch must name `personal:chat:personal-model`. Record the
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
