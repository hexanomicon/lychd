---
title: Summoning
icon: material/fire
---

# :material-fire: Summoning Ritual

To bind the Daemon to the Host, complete the four stages of the Rite.

### I. The Desecration

Prepare the **Unholy Grounds**. The Order of the Iron Covenant mandates the use of **uv** for its speed and hermetic isolation, though legacy `pip` installation remains available for end-user package installation when `uv` is unavailable. Repository and contributor workflows remain `uv`-governed.

- **The Iron Path (Recommended)**
  _Clean, isolated, and instant._

  ```bash
  uv tool install lychd
  ```

- **The Acolyte's Path (Legacy)**
  _Standard pip installation._

  ```bash
  pip install lychd
  ```

- **The Necromancer's Path (Source)**
  _For Magi seeking to modify the core._

  ```bash
  git clone https://github.com/hexanomicon/lychd.git
  cd lychd
  uv sync
  ```

### II. The Inscription

Before the Lich can rise, the Codex must learn where the bodies are buried.
Initialize the **Codex** to spawn the configuration templates and forge the Crypt.

```bash
lychd init
```

This establishes the **Sacred Grounds**:

- 📜 **[The Codex](sepulcher/codex.md)** (`~/.config/lychd`): The book of **Runes** (validated TOML intent).
- 🪦 **[The Crypt](sepulcher/crypt.md)** (`~/.local/share/lychd`): The persistent storage.

The Scribe inspects the filesystem. If **Btrfs** is not detected, it automatically forges a **Loopback Mirror** to support [Autopoiesis](./divination/transcendence/immortality.md).

> **Action Required:** Enter the Codex and configure your power sources.

- _Set your `model_root` in `lychd.toml`._
- _Define **Soulstones** (local services) or **Portals** (remote services) under `runes/animator/soulstones/` and `runes/animator/portals/`._

### III. The Transmutation

Once the Runes are set, transmute the configuration into Systemd units.
This command reads your Codex, generates the native Quadlet files, and reloads the daemon.

```bash
lychd bind
```

> **"The circle is bound."** The Codex Runes have been transmuted into native Quadlet manifests.

### IV. The Summoning

Invoke the **Vessel**.
The **Sepulcher** manages the start of required services.

```bash
systemctl --user start lychd

# Use this command to hear the internal monologue of the Scribe
journalctl --user -fu lychd
```

> **"The summoning is complete."**
