<div align="center">
  <img src="docs/assets/lich-phylactery-cliparted.png" alt="LychD" width="500">
  <p><strong>LychD</strong> - The Dark Arts of LLMs</p>
  <p>
    <a href="https://github.com/hexanomicon/lychd">
      <img src="https://img.shields.io/badge/Source-GitHub-1a1a20?style=for-the-badge&labelColor=4a148c" alt="Source on GitHub">
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

**LychD is a pre-alpha Linux daemon for local model services and agent workflows on hardware you
control.** Its current software contract plans and mediates rootless services through systemd,
defines PostgreSQL as the durable home for committed run truth, and exposes a loopback web surface
for one operator.

In the project's language, that recurrent whole is **the Lich**. A model is one organ—not its
identity, memory, orchestration, or authority.

Repository evidence covers the local, loopback, single-operator software foundation. An actual
Linux host, accelerator, model, and inference-engine combination must be validated by its operator;
anything beyond the proved envelope remains a horizon until [State of the
Work](docs/state-of-the-work.md) records otherwise.

**Choose your next act:**

- 🕯️ **[Inspect the source foundation](#minimum-source-bootstrap)** — build one checkout and verify
  the current CLI and generated configuration.
- 🔍 **[Judge the current envelope](docs/state-of-the-work.md)** — inspect proved behavior, limits,
  and evidence.
- 📜 **[Read the Prophecy](https://hexanomicon.github.io/lychd/)** — enter the Hexanomicon and see
  the Great Work this foundation serves.

## Minimum source bootstrap

This pre-alpha revision does not yet have a public `lychd` package and Vessel image built from the
same release. On Linux with Git, uv, and Podman, create a local CLI environment and Vessel image
from one source checkout:

```bash
git clone https://github.com/hexanomicon/lychd.git
cd lychd
git rev-parse --verify HEAD
uv sync --frozen
podman build --file Containerfile --tag localhost/lychd:dev .
uv run lychd --help
uv run lychd init
```

That receipt proves only that the selected source resolves, builds, exposes the real command tree,
and generates its initial configuration. It does **not** prove caged startup, accelerator access,
a warm model, or a Bridge reply.

The complete operator path is still being revalidated and is deliberately not linked from this
threshold. Do not continue from this bootstrap to `lychd bind` or service startup yet. The
corrected rite must first point the `image` key under `[server.web]` to
`"localhost/lychd:dev"`, select an Animator extension and rerun `uv run lychd init`, then declare
the hardware-specific model mounts and devices and state the temporary local-browser safety
boundary. Until that rite and a named-host receipt land, consult **[State of the
Work](docs/state-of-the-work.md)** for the proved envelope. Do not substitute `uv tool install
lychd`, `pip install lychd`, or `ghcr.io/hexanomicon/lychd:latest` for this checkout yet.

## 🗺️ Choose Your Path

The Hexanomicon is one body with several entrances. Choose the question you need answered:

- 🕯️ **Operator — inspect the source bootstrap above.** The complete first-life proof ladder will
  return here when its candidate rite and named-host boundary agree.
- 🔍 **Evaluator — [inspect State of the Work](docs/state-of-the-work.md).** Judge current behavior,
  boundaries, and evidence before trusting a claim.
- ⚒️ **Developer — [enter the contributor forge](CONTRIBUTING.md).** Learn the repository contract,
  then use the [Covenants](docs/adr/index.md) to find the decision that owns a change.
- ⭕ **Seeker — [read the Prophecy](https://hexanomicon.github.io/lychd/).** Begin with the public
  initiation, then enter [Philosophy](docs/philosophy/index.md) when you want the Logos beneath the
  system.

The [Lexicon](docs/lexicon.md) is a reference when an unfamiliar term blocks you; it is not
required pre-reading.

Every path rests on the same premise: continuity, memory, and authority should remain anchored on
hardware the operator controls.

## 🚩 Local sovereignty

Cloud intelligence is leased: your data is the currency, and continuity ends where the subscription
does. LychD is built on the opposite premise. On hardware you control, with open-source software
you can inspect and alter, you retain local custody of the system and its continuity as a sovereign
operator.

In the federation this Work intends, the individual remains the primary sovereign unit. A company
is not the soul-bearing actor; it is an emergent coordination graph of sovereign people and their
Liches. Future policy, IAM, and A2A boundaries could expose selected labor while the underlying
Phylacteries remain locally owned.

As that horizon is embodied, SaaS, company APIs, and remote peers would become negotiated surfaces
the Lich may traverse without surrendering your continuity, memory, or private priors.

The planned A2A boundary would lease labor, not continuity: a company could invoke a consented
capability, while the memory, workflows, and agentic expertise that produced it would remain
anchored in your Phylactery unless explicitly shared.

> *I would rather reign in a local hell than serve in a cloud heaven.*

## ⚖️ [The Iron Pact](docs/adr/00-license.md) (MPL 2.0)

**This project is for those who believe in the free evolution of intelligence, not those who seek to chain it.**

MPL 2.0 protects the shared body at the distribution boundary. This is a plain-language map; [LICENSE](LICENSE) is the binding pact, and [ADR 00](docs/adr/00-license.md) records the project's stewardship interpretation.

- **The Engine is Shared:** Distributed modifications to MPL-covered core files must remain available to their recipients.
- **The Soul is Private:** Your **Phylactery** (data/memories), **Secrets**, data-stored prompts/model artifacts, and separate **Private Agents** remain sovereign. MPL follows covered source files, not private data or separate new files that do not copy covered source.
- **Private Organs Stay Possible:** MPL permits proprietary local
  **[Extensions](docs/adr/05-extensions.md)** and static linking. ADR 26 reserves a future
  **[A2A Necropolis](docs/adr/26-a2a.md)** in which sovereign nodes could trade selected labor while
  keeping local advantage hidden.
- **The SaaS Scar is Honest:** Hosted network access is not distribution. LychD answers cloud capture through local-first architecture, protocol distrust, peer choice, provenance, and refusal to surrender private continuity to a hosted surface.
- **No CLA, No Private Relicensing:** There is no Contributor License Agreement and no maintainer-only relicensing grant. By contributing, you certify that you have the right to submit under MPL-2.0 and agree that the contribution is licensed under MPL-2.0.

**Protocol over implementation.** LychD is Linux-native, not "the Agentic OS." macOS, Windows, and
other runtimes may exist as ports, forks, or independent implementations. ADR 26 reserves a future
**A2A Intercom** for compatible ports and independent implementations; once that protocol is
specified and implemented, they could enter the Necropolis and trade labor in the Swarm.

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
  **[Structlog](https://github.com/hynek/structlog)** are the chosen telemetry substrate for the
  designed native Oculus.
- **[Linux](https://kernel.org/)**, **[systemd](https://systemd.io/)**, and
  **[Podman/Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)** animate
  rootless local services; **[Btrfs](https://btrfs.readthedocs.io/)** supplies optional groundwork
  for the designed snapshot ritual.
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
