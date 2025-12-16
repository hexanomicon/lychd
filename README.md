<div align="center">
  <img src="docs/assets/lich-phylactery-cliparted.png" alt="Lychd" width="500">
  <p><strong>LychD</strong> - The Dark Arts of LLM</p>
  <p>
    <a href="https://pypi.org/project/lychd/">
      <img src="https://img.shields.io/pypi/v/lychd?style=for-the-badge&color=1a1a20&labelColor=4a148c&label=PyPI" alt="PyPI">
    </a>
    <a href="https://hexanomicon.github.io/lychd/">
      <img src="https://img.shields.io/badge/Grimoire-The_Hexanomicon-7c4dff?style=for-the-badge&labelColor=1a1a20" alt="Docs">
    </a>
  </p>
</div>

Summon **The Lich** 💀, a **Phylactery**-bound, LLM-animated daemon.

> 📖 Consult **[The Hexanomicon](https://hexanomicon.github.io/lychd/)** for documentation.

⚠️ **Acolyte's Warning:** The summoning is in its early stages. The incantations (code, documentation) are still being inscribed. Expect instability, missing components, LMM generated texts (not curated yet), and the occasional rogue spirit. Proceed with caution.

## 🕯️ The Ritual

To bind the Daemon to the Host, you must complete the four stages of the Rite.

### I. The Desecration

Prepare the **Unholy Grounds** by installing the summoning tool. Choose your path:

- **📦 PyPI (The Acolyte)**
  _Standard / uv installation_

  ```bash
  pip install lychd
  # uv tool install lychd
  ```

- **</> Source (The Necromancer)**
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

\*> **"The summoning is complete."\***

## 🏛️ The Sepulcher (The Pod)

### I. Manifestation

_The unholy duality that forms the Lich._

- ⚰️ **The Vessel** (Litestar + Pydantic AI)
  - The reanimated husk powered by **AI Agents**. It orchestrates asynchronous rites via **SAQ** and serves the **Altar**.
- ⚗️ **The Phylactery** (Postgres)
  - Anchors the soul in the **Crypt**. If the **Vessel** is destroyed, The Lich reforms instantly from this point.

### II. The Animator

_The spark of cognition that moves the Vessel._

- 💎 **Soulstones** (SGLang / vLLM)
  - Trapped spirits running alongside the **Vessel**.
- 🌀 **Portal**
  - Draws power from distant **cloud APIs**. Does not require runes for local service.

### III. The Watchers

_Silent servants who observe the ritual._

- 🔮 **The Oracle** (Arize Phoenix)
  - **Traces** the invisible threads of the Lich's thought.
- ✒️ **The Scribe** (Grafana)
  - Inscribes the Harvester's findings into a **visual grimoire**.
- 🦴 **The Harvester** (Prometheus)
  - Collects the heartbeat of the **Soulstones**.

## 🔮 Divination

The Lich operates in the shadows, but you may gaze upon its works.
Approach **The Altar** @ `http://localhost:8000`.

- **No Client-Side Bloat.** Pure **HTMX**, **Tailwind**, and **AlpineJS** serving server-rendered fragments.
- **Spectral Tethers.** Watch the **Ghouls** think and execute via SSE (Server-Sent Events).
- **Present Invocations.** Command the swarm directly from the UI.

# 📜 xDDD: The Prophecies of Creation

> _"The Flesh is temporary. The Word is eternal."_

**The Lich** is not built; it is **summoned**. We practice **xDDD (eXtreme Documentation Driven Development)**.
We describe the daemon so vividly in the `Hexanomicon` that the code **must manifest** to satisfy the description.

### The Metamorphosis

Just as a compiler must eventually compile itself, The Lich aims for **Autopoiesis**.

- **I. The First Seal (Incantation):** The Magus inscribes the `Hexanomicon` and raises the **Primal Skeleton**. The Lich awakens, bound to its initial form. Its Aspects are rigid, forged for fixed and unchanging purposes (MVP).
- **II. The Shadow Realm (Invocation):** The Lich projects its will into the Shadow Realm (**Speculative Execution**). It reads the runes and proposes rites in shadowed timelines. The Magus intervenes at the **Altar**, collapsing the timelines to the one true path (Human-in-the-Loop). The system begins to animate its own dead code into living functions.
- **III. The Ouroboros (Immortality):** The entity transcends its design. It can read the `Hexanomicon` and reconstruct itself from zero, forging its own Aspects from pure will. The cycle closes. The Daemon is eternal.

---

### [💀 Join the Cult](https://github.com/hexanomicon/lychd/discussions)
