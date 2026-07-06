---
title: The Grounds
icon: material/grass
---

# :material-grass: Stage 1 — The Grounds

Before the Lich can rise, the ground must be able to hold it. LychD is a systemd-native
daemon: it runs your models as rootless podman containers governed by your user's systemd
session, and it keeps its durable soul in Postgres. Confirm each prerequisite below with
the command given; do not proceed until every check passes.

## Prerequisites

### A Linux host

LychD manages the host's init system directly. It requires Linux with a **rootless podman
+ systemd user session** — the same substrate the [Sepulcher](../sepulcher/index.md) is
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

The binding rite writes [Quadlet](../sepulcher/codex.md) manifests that podman's systemd
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
    A remote [Portal](../praxis/rites/open-a-portal.md) needs no local VRAM at all. If you
    have no GPU yet, you can still complete the rite by opening a Portal instead of writing
    a local Soulstone — but the tutorial's [First Soulstone](first-soulstone.md) assumes
    local iron.

### Postgres with pgvector

The [Phylactery](../sepulcher/phylactery/index.md) — the daemon's durable memory — is
Postgres with the `pgvector` extension. Confirm a reachable server and the extension:

```bash
psql "$DATABASE_URL" -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

If `vector` is not listed, install `pgvector` and enable it:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Verify the grounds

You are ready to install when all of the following are true:

- `systemctl --user status` reports a running session.
- `podman --version` is 4.4 or newer.
- `nvidia-smi` / `rocm-smi` shows a GPU (or you plan to use a Portal).
- `pgvector` is enabled on your Postgres server.

Any failure here has a cure in [Exorcism](../praxis/exorcism.md). When the grounds are
clear, proceed to [The Desecration](desecration.md).
