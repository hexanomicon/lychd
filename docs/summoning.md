---
icon: material/fire
---

# :material-fire: Summoning Ritual

To bind the Daemon to the Host, you must complete the four stages of the Rite.

### I. The Desecration

Prepare the **Unholy Grounds** by installing the summoning tool. Choose your path:

- **📦 PyPI (The Acolyte)**
  _Standard / uv installation_

  ```bash
  pip install lychd
  # uv tool install lychd
  ```

- **&lt;/&gt; Source (The Necromancer)**
  _For Magi seeking to modify the core._

  ```bash
  git clone https://github.com/hexanomicon/lychd.git
  cd lychd
  pip install -e .
  ```

### II. The Inscription

Before the Lich can rise, you must tell it where the bodies are buried.
Initialize the **Codex** to spawn the configuration templates.

```bash
lychd init
```

This establishes the **Sacred Grounds**:

- 📜 **The Codex** (`~/.config/lychd`): The book of **Runes** (Quadlets & Blueprints).
- 🪦 **The Crypt** (`~/.local/share/lychd`): The **Phylactery** mount (Postgres & PgVector).

_> **Action Required:** Enter the Codex and configure your power sources._

- _Set your `model_root` in `lychd.toml`._
- _Define your **Soulstones** (Local LLMs) or **Portals** (Cloud APIs) in `conf.d/`._

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

# Use this command to hear the live, unending thoughts of the Vessel
journalctl --user -fu lychd
```

\*\*"The summoning is complete."\*\*
