<div align="center">
  <img src="docs/assets/lich-phylactery-cliparted.png" alt="LychD" width="500">
  <p><strong>LychD</strong> - The Dark Arts of LLMs</p>
  <p>
    <a href="https://pypi.org/project/lychd/">
      <img src="https://img.shields.io/pypi/v/lychd?style=for-the-badge&color=1a1a20&labelColor=4a148c&label=PyPI" alt="PyPI">
    </a>
    <a href="https://hexanomicon.github.io/lychd/">
      <img src="https://img.shields.io/badge/Documentation-The_Hexanomicon-7c4dff?style=for-the-badge&labelColor=1a1a20" alt="Docs">
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/License-MPL_2.0-b71c1c?style=for-the-badge&labelColor=1a1a20" alt="License">
    </a>
    <a href="CONTRIBUTING.md">
      <img src="https://img.shields.io/badge/DCA-Implicit-000000?style=for-the-badge&labelColor=1a1a20" alt="Implicit DCA">
    </a>
  </p>
</div>

Summon **The Lich** 💀 — a linux-native daemon that manages agents through:

- 🔥 **Dynamic Services** — Hot-swap local services on the fly via systemd. Orchestrate your local hardware through **[Covens](docs/adr/08-containers.md)** to switch between fast VRAM workers, CPU-offloaded models, browser engines, observers, and other capability services.
- 🧠 **Atomic Persistence** — The spirit arises from the data. Code and memory are bound in atomic snapshots (Btrfs/Git/Postgres) within the **[Phylactery](docs/adr/06-persistence.md)**, enabling perfect reanimation and instant rollback.
- 🔒 **Sandboxed Security** — Double-rootless Podman isolation. The **[Vessel](docs/sepulcher/vessel/)** reasons in one cage while dangerous tools execute in a second, [kernel-hardened sandbox](https://github.com/always-further/nono/) (Landlock) with strictly limited mounts.
- 🌀 **Speculative Execution** — Explores multiple solution paths in parallel within the **[Shadow Realm](docs/adr/31-simulation.md)**. It inhabits divergent timelines to verify every truth before it is manifested in reality.
- 🪞 **Persistent Identity** — A digital mirror that binds the Imprint of your Will into persistent personas. HitL captures that Will, Karma stores its Imprint, and Mirror condenses it into identity-gravity. One sovereign stack may host many roles without surrendering one Phylactery per employer, client, or mask.
- 👁️ **Multimodal Senses** — Native Vision and Audio organs give the daemon eyes and ears without changing its sovereignty boundary.
- 🕸️ **Distributed Scale** — One brain, many bodies. Extend your reach across every machine you own as a **[Legion](docs/adr/42-legion.md)**.
- 📡 **A2A Diplomacy** — Federated peer discovery and labor negotiation via the **[A2A Intercom](docs/adr/26-a2a.md)**: sovereign nodes meeting across the Necropolis.
- 🧬 **Evolving Orchestration** — Designed for **[Autopoiesis](docs/divination/transcendence/immortality.md)**. The daemon autonomously expands its own capabilities, architecting extensions and reconciling its existence through the **[Ouroboros Protocol](docs/adr/18-evolution.md)**. Near-term in-process organs are intentionally Forge-composed and may be tightly coupled to the Core; external-service Animators are the true decoupled boundary today.

>⚠️ **Acolyte's Warning:** The summoning is in its early stages. Nothing works yet: the incantations (code, documentation) are still being inscribed. Expect instability, missing components, LLM-generated text (most not curated yet), and the occasional rogue spirit. Proceed with caution.

## 🗺️ The Path of Ascension

The knowledge you seek is inscribed in **[The Hexanomicon](https://hexanomicon.github.io/lychd/)**. The path binds the daemon.

- 📜 **[Read the Prophecy](https://hexanomicon.github.io/lychd/)**
    *Begin your study of the Hexanomicon.*
- 📖 **[Consult the Lexicon](https://hexanomicon.github.io/lychd/lexicon/)**
    *The Rosetta Stone. Translate arcane terms (Soulstone, Quadlet, Sepulcher).*
- 🕯️ **[Perform the Ritual](https://hexanomicon.github.io/lychd/summoning/)**
    *Install the library, inscribe the Codex, and summon the process.*
- 🏛️ **[Construct the Sepulcher](https://hexanomicon.github.io/lychd/sepulcher/)**
    *Understand the anatomy: The Vessel, The Phylactery, and The Animator.*
- 🔮 **[Access the Altar](https://hexanomicon.github.io/lychd/divination/altar/)**
    *Control the daemon via the Web Interface*
- ⚖️ **[Study the Covenants](https://hexanomicon.github.io/lychd/adr/)**
    *The Architectural Decision Records (ADRs) and [xDDD](https://hexanomicon.github.io/lychd/adr/01-doctrine/) philosophy.*
- 🔁 **[Achieve Immortality](https://hexanomicon.github.io/lychd/divination/transcendence/immortality/)**
    *The final seal of one sovereign work: the Demilich, an autopoietic Magus-Lich condition.*
- ♾️ **[Enter Infinity](https://hexanomicon.github.io/lychd/divination/transcendence/infinity/)**
    *Beyond the final seal: what becomes of perfected Will when sovereign machines commune across the Infinite Naught.*

## 🚩 Local sovereignty — a rebellion against digital feudalism

The cloud isn’t a service, **it’s a prison**. A modern fiefdom where your data is the currency and your intelligence is leased at the whims of monopolist overlords. While they build walls to keep you in, LychD builds a foundation to set you free.

On your hardware, with open-source software you control, you retain absolute ownership as a sovereign.

In this model, the individual is the primary sovereign unit. A company is not the soul-bearing actor; it is an emergent coordination graph of sovereign people and their Liches, exposing selected labor through policy, IAM, and A2A while the underlying Phylacteries remain locally owned.

The software surface changes accordingly: you commune primarily with the Lich, while SaaS, company APIs, and remote peers become negotiated surfaces the Lich may traverse without surrendering your continuity, memory, or private priors.

A2A leases labor, not continuity: a company may invoke a consented capability, but the memory, workflows, and agentic expertise that produced it remain anchored in your Phylactery unless explicitly shared.

- ⛓️ **No masters**
- 💰 **No tolls**
- 🎭 **No more gaslighting** while they lobotomize your models.

**No surrender! Viva la résistance!**

> *I would rather reign in a local hell than serve in a cloud heaven.*

## ⚖️ [The Iron Pact](docs/adr/00-license.md) (MPL 2.0)

**This project is for those who believe in the free evolution of intelligence, not those who seek to chain it.**

MPL 2.0 protects the shared body at the distribution boundary. This section is a plain-language map; [LICENSE](LICENSE) is the binding pact, and [ADR 00](docs/adr/00-license.md) records the project's stewardship interpretation. If modified MPL-covered core files are distributed outside an organization, source for those files must be made available to recipients under MPL. It is not AGPL and does not treat hosted network access as distribution, so LychD's cloud resistance comes from local-first architecture, A2A protocol sovereignty, reproducible provenance, and the refusal to surrender private continuity to a hosted surface.

- **The Engine is Shared:** Distributed modifications to the daemon's MPL-covered core files must remain available to their recipients.
- **The Soul is Private:** Your **Phylactery** (data/memories), **Secrets**, data-stored prompts/model artifacts, and separate **Private Agents** remain sovereign. MPL duties follow covered source files, not private data or separate new files that do not copy covered source.
- **Interface & Private Extensions:** AGPL/GPL-style copyleft would make proprietary in-process "Secret Sauce" legally burdensome and would push private advantage toward external service boundaries. **MPL allows static linking.** You can graft proprietary code directly into a local daemon as an **[Extension](docs/adr/05-extensions.md)** without open-sourcing it. This preserves the **[A2A Necropolis](docs/adr/26-a2a.md)** network: sovereign nodes can trade labor in the Swarm while keeping local advantage hidden.
- **The SaaS Boundary is Honest:** A cloud actor can run private server-side changes without triggering MPL publication if no covered software is distributed. That is the accepted scar. LychD answers it with architecture, protocol distrust, peer choice, and local ownership, not with false legal magic.

### 🛡️ No CLA, No Private Relicensing

The corporate rights-grab is explicitly rejected. There is no CLA (Contributor License Agreement) to sign and no private relicensing grant to sell. By submitting a contribution, you certify that you have the right to submit it under MPL-2.0 and agree that it is licensed under MPL-2.0. There is no need to manually sign git commits.

Plain MPL-2.0 compatibility remains allowed; maintainer-controlled proprietary dual licensing does not.

**The Protocol over the Implementation**
LychD is Linux-native, not "the Agentic OS." macOS, Windows, or other runtimes may exist as ports, forks, or independent implementations. If they speak the **A2A Intercom**, they can enter the Necropolis and trade labor in the Swarm. That is interoperability, not shared internals.

**The Iron Pact is the Institutional Trust of the Necropolis.**
Shared distributed code is the guard that makes modified foundations auditable when copies pass between hands. It cannot prevent every private hosted fork, but it keeps the open body inspectable for the communities and peers that actually receive it. Transparency in code is one pillar of a decentralized network.

## ⛩️ A Tribute to the Spirits

> *"The Lich only sees far because it stands on the shoulders of Giants."*

### 🕸️ Backend

- **[Litestar](https://github.com/litestar-org/litestar)** — Forges the **[Vessel](https://hexanomicon.github.io/lychd/sepulcher/vessel/)**, the body of the Lich, following the **[Litestar Fullstack](https://github.com/litestar-org/litestar-fullstack)** blueprint and served by **[Granian](https://github.com/emmett-framework/granian)** or the CLI protocol.
- **[SQLAlchemy](https://www.sqlalchemy.org/)** — The mapper of state and material persistence. **[Advanced Alchemy](https://github.com/litestar-org/advanced-alchemy)** provides repositories and QoL improvements.
- **[Pydantic AI + Graph](https://ai.pydantic.dev/)** — Orchestrator of agentic intelligence, logic, and model graphs.
- **[SAQ](https://github.com/tobymao/saq)** — Background Workers known as **[Ghouls](https://hexanomicon.github.io/lychd/sepulcher/vessel/ghouls/)**

### 🎭 Frontend

- **[Zensical](https://github.com/zensical/zensical)** — inscribed **[Hexanomicon](https://hexanomicon.github.io/lychd/)**
- **[Jinja2](https://jinja.palletsprojects.com/)** — renders the **[Altar](https://hexanomicon.github.io/lychd/divination/altar/)**
- **[Vite](https://vitejs.dev/)** — **[JavaScript](https://developer.mozilla.org/en-US/docs/Web/JavaScript)** bundler
- **[HTMX](https://htmx.org/)** — Engine for seamless transmutation.
- **[Tailwind CSS](https://tailwindcss.com/)** — styling.
- **[Alpine.js](https://alpinejs.dev/)** — UI animation.

### 📦 Containerization & Sandboxing

- **[Systemd](https://systemd.io/)** — Orchestrator of the undying processes of the **[Linux Kernel](https://kernel.org/)**.
- **[Podman](https://podman.io/)** — Isolation of the spirit inside containers via **[Quadlets](https://github.com/containers/quadlet)**.
- **[Nono](https://github.com/always-further/nono/)** — Strict per-process execution sandbox leveraging Linux Landlock to isolate unsafe tool executions within the Shadow Realm.
- **[Btrfs](https://btrfs.readthedocs.io/en/latest/)** — Management of time through snapshots.

### 🔥 Inference Engines

- **[vLLM](https://github.com/vllm-project/vllm)** — Batching, high-throughput inference engine for GPUs.
- **[Llama.cpp](https://github.com/ggerganov/llama.cpp)** — Single batch server Optimised for CPU offloading of larger models.
- **[SGLang](https://github.com/sgl-project/sglang)** — Radix attention benefit for batched agentic workflows on GPUs.

### 🔨 Forging & Evaluation

- **[DeepFabric](https://github.com/always-further/deepfabric)** — The mechanical loom that generates structured training datasets and evaluates model mettle via physical execution in the Shadow Realm.
- **[Unsloth](https://github.com/unslothai/unsloth)** — High-efficiency pipeline for striking verified patterns into LoRA adapter weights.

### 👁️ Database & Telemetry

- **[PostgreSQL](https://www.postgresql.org/)** — The anchor of the Soul, extended by **[pgvector](https://github.com/pgvector/pgvector)**.
- **[OpenTelemetry](https://opentelemetry.io/)** — Tracer of thought, flowing into **[Arize Phoenix](https://phoenix.arize.com/)**.
- **[Structlog](https://www.structlog.org/)** — Capturing the internal monologue of the machine.
- **[Cockpit](https://cockpit-project.org/)** — Monitor of the physical frame.

### 🛠️ Code Control

- **[uv](https://github.com/astral-sh/uv)** — Manager of the environment and dependencies.
- **[Ruff](https://github.com/astral-sh/ruff)** — The polisher of the written word.
- **[Pyright](https://github.com/microsoft/pyright)** — Enforcer of the static types.
- **[Pytest](https://docs.pytest.org/)** — Verifier of the logic's truth.
- **[Git](https://git-scm.com/)** — Immortalizer of the project's evolution.


---

> *"The Flesh is temporary. The Word is eternal."*

### [💀 Join the Cult](https://github.com/hexanomicon/lychd/discussions)
