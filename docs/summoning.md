---
icon: material/fire
---

# :material-fire: Summoning Ritual

To bind the Daemon to the Host, you must complete the four stages of the Rite.

### I. The Desecration

Prepare the **Unholy Grounds**. The Order of the Iron Covenant mandates the use of **uv** for its speed and hermetic isolation, though legacy pip invocations are tolerated.

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

Before the Lich can rise, you must tell it where the bodies are buried.
Initialize the **Codex** to spawn the configuration templates and forge the Crypt.

```bash
lychd init
```

This establishes the **Sacred Grounds**:

- 📜 **[The Codex](sepulcher/codex.md)** (`~/.config/lychd`): The book of **Runes** (Quadlets & Blueprints).
- 🪦 **[The Crypt](sepulcher/crypt.md)** (`~/.local/share/lychd`): The persistent storage.
    - **Note:** The Scribe will inspect your filesystem. If **Btrfs** is not detected, it will automatically forge a **Loopback Mirror** to support [Autopoiesis](./divination/transcendence/immortality.md).

_> **Action Required:** Enter the Codex and configure your power sources._

- _Set your `model_root` in `lychd.toml`._
- _Define your **Soulstones** (Local LLMs) or **Portals** (Cloud APIs) in `soulstones/` and `portals/`._

### III. The Transmutation

Once the runes are set, transmute the configuration into Systemd units.
This command reads your Codex, generates the native Quadlet files, and reloads the daemon.

```bash
lychd bind
```

_> **"The circle is bound."** The abstract configs have been transmuted into native `.service` units._

### IV. The Summoning

Invoke the **Vessel**.
The **Sepulcher** manages the start of required services.

```bash
systemctl --user start lychd

# Use this command to hear the internal monologue of the Scribe
journalctl --user -fu lychd
```

\*> **"The summoning is complete."\***
