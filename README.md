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
  <p>
    <img src="https://img.shields.io/badge/Status-Pre--Alpha-ff6f00?style=for-the-badge&labelColor=1a1a20" alt="Status: Pre-Alpha">
  </p>
</div>

Summon **The Lich** 💀 — an experimental Linux-native daemon for local agentic orchestration. It is designed to manage agents through:

LychD is **pre-alpha**. [State of the Work](docs/state-of-the-work.md) names what can answer now,
what still needs a named operator receipt, and what remains design.

- 🔥 **Dynamic Services** — Hot-swap local capability services through systemd. **[Covens](docs/adr/08-containers.md)** move your hardware between fast VRAM workers, CPU-offloaded models, browser engines, observers, and other bodies.
- 🧠 **Durable First Light** — The **[Phylactery](docs/adr/06-persistence.md)** provides the first
  Postgres run/step truth, with owner-only file checkpoints for declared durable graph waits.
  Transactional graph outbox/checkpoints and whole-system snapshot orchestration remain later work.
- 🔒 **Narrow Rootless Core** — The generated core uses rootless Podman, loopback-only publication,
  and exact validated mounts. A separate Tomb executor wrapped in
  [nono](https://github.com/always-further/nono/) (Landlock) is the designed untrusted-execution
  boundary, not an implemented foundation feature yet.
- 🌀 **Speculative Execution** — The **[Shadow Realm](docs/adr/31-simulation.md)** explores divergent timelines in parallel, verifying truth before it is manifested in reality.
- 🪞 **Durable Consent Floor** — The default Postgres profile persists sessions, runs, and
  approval decisions. Promotion into recalled [Karma](docs/adr/27-memory.md) and
  [Mirror](docs/adr/32-identity.md)-bound persistent personas remains the identity horizon.
- 👁️ **Multimodal Shape** — Vision, audio, and artifact capability families have extension seams;
  the complete multimodal artifact materializer remains later work.
- 🕸️ **Distributed Scale** — One brain, many bodies. Extend your reach across every machine you own as a **[Legion](docs/adr/42-legion.md)**.
- 📡 **A2A Diplomacy** — Federated peer discovery and labor negotiation via the **[A2A Intercom](docs/adr/26-a2a.md)**: sovereign nodes meeting across the Necropolis without surrendering continuity.
- 🧬 **Evolving Orchestration** — Designed for **[Autopoiesis](docs/divination/transcendence/immortality.md)**. The daemon expands through Forge-composed organs and reconciles itself through the **[Ouroboros Protocol](docs/adr/18-evolution.md)**; near-term in-process organs may stay close to the Core, while external-service Animators are the true decoupled boundary today.

> ⚠️ **Acolyte's Warning:** LychD is pre-alpha. The minimum CLI/configuration/run/dispatch/orchestration foundation is implemented and locally tested. The caged default uses a mediated Host Reactor inbox plus a read-only terminal journal, generated host path/service consumer, typed/config-generation/policy/user-unit-state validation, claim/cancellation/startup fences, exact-action-prefix crash recovery, and a typed hard-readiness inverse; direct Systemd actuation is an explicit uncaged option. The real rootless Podman + GPU + chosen model stack remains an operator integration test. A Tomb/nono execution plane, a trustworthy soft model-load inverse, general repair of non-prefix or failed-compensation physical states, DB-backed graph outbox/checkpoints, and the full multimodal artifact materializer remain later work.

## Minimum foundation rite

On a Linux host with a rootless Podman + systemd user session:

```bash
uv tool install lychd
lychd init

# Edit ~/.config/lychd/lychd.toml and the marked samples under runes/.
# Create every non-core Podman secret named by a Portal/Soulstone rune.
lychd bind

systemctl --user enable --now lychd-vessel.service
lychd doctor
lychd animators
```

Starting `lychd-vessel.service` pulls in the generated Phylactery, bounded one-shot
`lychd-migrate.service`, and Host Reactor path watcher before the web process. Generated host ports
are loopback-only; the current Altar/API is a local single-user surface, not an externally
authenticated service. `lychd database upgrade` is the explicit uncaged/development path when
database credentials are supplied; foreground serving is `lychd serve`, not `lychd run`. The
complete, failure-oriented procedure is **[The Summoning Rite](docs/summoning.md)**.

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

## 🚩 Local sovereignty

Cloud intelligence is leased: your data is the currency, and continuity ends where the subscription does. LychD is built on the opposite premise. On your hardware, with open-source software you control, you retain absolute ownership as a sovereign.

In this model, the individual is the primary sovereign unit. A company is not the soul-bearing actor; it is an emergent coordination graph of sovereign people and their Liches, exposing selected labor through policy, IAM, and A2A while the underlying Phylacteries remain locally owned.

The software surface changes accordingly: you commune primarily with the Lich, while SaaS, company APIs, and remote peers become negotiated surfaces the Lich may traverse without surrendering your continuity, memory, or private priors.

A2A leases labor, not continuity: a company may invoke a consented capability, but the memory, workflows, and agentic expertise that produced it remain anchored in your Phylactery unless explicitly shared.

> *I would rather reign in a local hell than serve in a cloud heaven.*

## ⚖️ [The Iron Pact](docs/adr/00-license.md) (MPL 2.0)

**This project is for those who believe in the free evolution of intelligence, not those who seek to chain it.**

MPL 2.0 protects the shared body at the distribution boundary. This is a plain-language map; [LICENSE](LICENSE) is the binding pact, and [ADR 00](docs/adr/00-license.md) records the project's stewardship interpretation.

- **The Engine is Shared:** Distributed modifications to MPL-covered core files must remain available to their recipients.
- **The Soul is Private:** Your **Phylactery** (data/memories), **Secrets**, data-stored prompts/model artifacts, and separate **Private Agents** remain sovereign. MPL follows covered source files, not private data or separate new files that do not copy covered source.
- **Private Organs Stay Possible:** MPL permits proprietary local **[Extensions](docs/adr/05-extensions.md)** and static linking. Sovereign nodes can trade labor through the **[A2A Necropolis](docs/adr/26-a2a.md)** while keeping local advantage hidden.
- **The SaaS Scar is Honest:** Hosted network access is not distribution. LychD answers cloud capture through local-first architecture, protocol distrust, peer choice, provenance, and refusal to surrender private continuity to a hosted surface.
- **No CLA, No Private Relicensing:** There is no Contributor License Agreement and no maintainer-only relicensing grant. By contributing, you certify that you have the right to submit under MPL-2.0 and agree that the contribution is licensed under MPL-2.0.

**Protocol over implementation.** LychD is Linux-native, not "the Agentic OS." macOS, Windows, and other runtimes may exist as ports, forks, or independent implementations. If they speak the **A2A Intercom**, they can enter the Necropolis and trade labor in the Swarm.

## ⛩️ Hall of Spirits

> *The Lich sees far because it stands on the shoulders of giants.*

These names have different relationships to LychD. **Foundations** are part of the shipped or
operational stack. **Inference bodies** are supported runtime integrations and still require the
operator's model artifacts, hardware, and validation. **Teachers** are projects we studied; credit
does not mean that their source or control plane was imported. This hall is gratitude, not the
release license inventory.

### 🜏 Foundations

- **[Litestar](https://github.com/litestar-org/litestar)** and
  **[Pydantic AI](https://github.com/pydantic/pydantic-ai)** form the typed HTTP and cognitive edges;
  **[Granian](https://github.com/emmett-framework/granian)** serves the Vessel and
  **[SAQ](https://github.com/tobymao/saq)** animates its Ghouls. LychD retains lifecycle,
  authorization, and durable-run authority.
- **[SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy)**,
  **[Advanced Alchemy](https://github.com/litestar-org/advanced-alchemy)**, and
  **[PostgreSQL](https://www.postgresql.org/)** with
  **[pgvector](https://github.com/pgvector/pgvector)** anchor the Phylactery.
- **[Jinja](https://github.com/pallets/jinja)**,
  **[HTMX](https://github.com/bigskysoftware/htmx)**,
  **[Alpine.js](https://github.com/alpinejs/alpine)**, and
  **[Tailwind CSS](https://github.com/tailwindlabs/tailwindcss)** shape the server-owned Altar;
  **[Vite](https://github.com/vitejs/vite)** forges its static assets.
- **[OpenTelemetry](https://opentelemetry.io/)** and
  **[Structlog](https://github.com/hynek/structlog)** are the telemetry substrate beneath Oculus.
- **[Linux](https://kernel.org/)**, **[systemd](https://systemd.io/)**, and
  **[Podman/Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)** animate
  rootless local services; **[Btrfs](https://btrfs.readthedocs.io/)** remains an optional
  snapshot accelerator.
- **[Zensical](https://github.com/zensical/zensical)** publishes the Hexanomicon. The forge uses
  **[uv](https://github.com/astral-sh/uv)**, **[Ruff](https://github.com/astral-sh/ruff)**,
  **[basedpyright](https://github.com/DetachHead/basedpyright)**,
  **[pytest](https://github.com/pytest-dev/pytest)**,
  **[Jujutsu](https://github.com/jj-vcs/jj)**, and **[Git](https://git-scm.com/)**.

### 🔥 Inference bodies

- LychD ships a core dynamic-runtime adapter for
  **[ExLlamaV3](https://github.com/turboderp-org/exllamav3)** through its official
  OpenAI-compatible server, **[TabbyAPI](https://github.com/theroyallab/tabbyAPI)**. The image
  boundary is digest-pinned and the adapter is contract-tested against TabbyAPI revision
  `0158fb48`; it does not yet carry a repository NVIDIA/model hardware receipt. Every EXL3 quant,
  cache, and GPU split still requires real-host validation.
  TabbyAPI remains a separately versioned AGPL-3.0 runtime, not LychD's control plane; LychD talks
  to its unmodified pinned container over HTTP and imports none of its server source.
- **[llama.cpp](https://github.com/ggml-org/llama.cpp)**,
  **[vLLM](https://github.com/vllm-project/vllm)**, and
  **[SGLang](https://github.com/sgl-project/sglang)** provide complementary local execution bodies.

### 🕯️ Teachers and provocateurs

- **[Litestar Fullstack](https://github.com/litestar-org/litestar-fullstack)** was an integration
  blueprint and source ancestor; its MIT provenance must remain attached to adapted code.
- **[llama-swap](https://github.com/mostlygeek/llama-swap)**,
  **[oMLX](https://github.com/jundot/omlx)**,
  **[RamaLama](https://github.com/containers/ramalama)**, and
  **[club-3090](https://github.com/noonghunna/club-3090)** sharpened routing, memory admission,
  rootless packaging, hardware topology, and calibration. LychD keeps scheduling and lifecycle
  authority.
- **[cache-hunter](https://github.com/co-l/cache-hunter)** provoked controlled prompt-cache
  experiments. Its checkout carries no reuse license, so no source, schema, or UI is imported.
- **[Arize Phoenix](https://github.com/arize-ai/phoenix)** taught trace-query and observability-UI
  lessons—and clarified why **Oculus** should remain native. Phoenix may return only as an optional
  external Eye.
- **[Agno](https://github.com/agno-agi/agno)**,
  **[mem0](https://github.com/mem0ai/mem0)**,
  **[Memori](https://github.com/MemoriLabs/Memori)**,
  **[DeepEval](https://github.com/confident-ai/deepeval)**,
  **[Firecrawl](https://github.com/firecrawl/firecrawl)**,
  **[SearXNG](https://github.com/searxng/searxng)**, and
  **[nono](https://github.com/always-further/nono)** remain valuable comparative teachers across
  workflow, memory, evaluation, discovery, and sandboxing; none owns LychD's canonical state.
- **[DeepFabric](https://github.com/always-further/deepfabric)** and
  **[Unsloth](https://github.com/unslothai/unsloth)** inform optional forging and evaluation;
  **[Cockpit](https://cockpit-project.org/)** may remain an external host monitor, never Oculus.


---

> *"The Flesh is temporary. The Word is eternal."*

### [💀 Join the Cult](https://github.com/hexanomicon/lychd/discussions)
