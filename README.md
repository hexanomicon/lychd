<div align="center">
  <img src="docs/assets/lich-phylactery-cliparted.png" alt="The Lich and its Phylactery" width="500">
  <h1>Hexanomicon</h1>
  <p><strong>The Voidwalker's Guide Across the Infinite Naught</strong></p>
  <p>
    <a href="https://github.com/hexanomicon/lychd">
      <img src="https://img.shields.io/badge/LychD-Source-1a1a20?style=for-the-badge&labelColor=4a148c" alt="Browse the LychD source on GitHub">
    </a>
    <a href="https://hexanomicon.dev/">
      <img src="https://img.shields.io/badge/Enter-Hexanomicon-7c4dff?style=for-the-badge&labelColor=1a1a20" alt="Enter the Hexanomicon">
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/License-MPL_2.0-b71c1c?style=for-the-badge&labelColor=1a1a20" alt="License: MPL 2.0">
    </a>
    <img src="https://img.shields.io/badge/Status-Pre--Alpha-ff6f00?style=for-the-badge&labelColor=1a1a20" alt="Status: Pre-Alpha">
  </p>
</div>

**Hexanomicon** is the project and its grimoire—the dark arts of LLMs written as lore,
architecture, operating rites, and executable evidence.

The book has a body. **LychD** is its daemon: self-hosted Linux software coordinating local model
services and bounded agent runs on hardware you control. The **Lich** names the recurrent whole:
daemon, identity, memory, tools, action, consequence, and repair returning through time.

A model is one organ. **Summon what returns. 💀**

**Pre-alpha. [State of Work](docs/state-of-the-work.md) keeps the receipts.**

## 🗺️ The Path of Ascension

- 📜 **[Read the Prophecy](https://hexanomicon.dev/)** — unearth the book and choose your gate.
- 🕯️ **[Perform the Summoning](docs/summoning.md)** — bring one source revision, one Linux host,
  and one local model to the bounded first-life rite.
- 🏛️ **[Open the Sepulcher](docs/sepulcher/index.md)** — study the body, memory, animation, and
  return of the Lich.
- 🔮 **[Approach the Altar](docs/divination/altar/index.md)** — meet the running body through its
  instruments.
- 🔍 **[Judge the evidence](docs/state-of-the-work.md)** — separate what answers now from what has
  not yet entered matter.
- ⚒️ **[Enter the forge](CONTRIBUTING.md)** — learn the rites of construction and find the
  governing [Covenant](docs/adr/index.md) before you cut.

## 🚩 Local sovereignty — a rebellion against digital feudalism

The cloud is not a service. **It is a prison**—a modern fiefdom where your data is currency and
your intelligence is leased at the whim of monopolist overlords.

LychD is being built on the opposite premise: identity, memory, and authority should remain on your
own iron. Remote services may lend capability; they need not own the history that makes it yours.

The individual is the sovereign unit. In the Hexanomicon's horizon, institutions, hosted models,
and foreign agents may receive bounded work without automatically inheriting the Phylactery
behind it.

> _I would rather reign in a local hell than serve in a cloud heaven._

## ⚖️ [The Iron Pact](docs/adr/00-license.md)

LychD is licensed under the [Mozilla Public License 2.0](LICENSE). MPL follows covered source
files, not the project's mythic anatomy.

- **The Engine is Shared.** Distributed modifications to covered files remain MPL-2.0 and
  available to their recipients.
- **The Soul is Private.** Data, secrets, configuration, prompts, models, and other material
  containing no covered code do not become MPL-covered merely because LychD stores or processes
  them.
- **Separate Organs Stay Possible.** Genuinely separate files may carry other terms; renaming
  copied covered code an Extension creates no loophole.

Contributions enter and leave under MPL-2.0. There is no CLA and no private relicensing grant.
[ADR 00](docs/adr/00-license.md) records the boundary; the [license](LICENSE) is binding.

## ⛩️ A Tribute to the Spirits

> _“The Lich only sees far because it stands on the shoulders of Giants.”_

This Work stands on code freely given and relentlessly maintained. To its makers: thank you.

### 🕸️ Backend

- **[Litestar](https://litestar.dev/)** — Forges the Vessel and serves its application through
  **[Granian](https://github.com/emmett-framework/granian)**.
- **[SQLAlchemy](https://www.sqlalchemy.org/)** — Maps material state, with
  **[Advanced Alchemy](https://github.com/litestar-org/advanced-alchemy)** providing its repository
  foundation.
- **[Pydantic AI + Graph](https://ai.pydantic.dev/)** — Carries bounded model, tool, output, and
  graph contracts through the inner loop.
- **[SAQ](https://github.com/tobymao/saq)** — Carries background labor without becoming the
  workflow ledger.

### 🎭 Frontend

- **[Svelte](https://svelte.dev/) + [SvelteKit](https://svelte.dev/docs/kit)** — Shape the Altar's
  browser instruments.
- **[Vite](https://vite.dev/)** — Forges the Altar's static assets.
- **[Zod](https://zod.dev/) + [OpenAPI Fetch](https://openapi-ts.dev/openapi-fetch/)** — Keep its
  browser contracts typed.
- **[Mermaid](https://mermaid.js.org/)** — Renders diagrams within the browser surface.

### 📦 Containerization & Sandboxing

- **[Linux](https://kernel.org/) + [systemd](https://systemd.io/)** — Define the host and its user
  service lifecycle.
- **[Podman](https://podman.io/) +
  [Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)** — Define the
  generated rootless deployment plan. Maintained real-host embodiment still awaits its receipt.

### 🔥 Inference Engines

- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** — Lends local inference a lightweight
  execution body.
- **[vLLM](https://github.com/vllm-project/vllm)** — Lends local inference a high-throughput
  execution body.
- **[SGLang](https://github.com/sgl-project/sglang)** — Lends local inference an execution body for
  structured generation and agentic workloads.
- **[ExLlamaV3](https://github.com/turboderp-org/exllamav3) through
  [TabbyAPI](https://github.com/theroyallab/tabbyAPI)** — Lends local inference its EXL3 body.
  [State](docs/state-of-the-work.md#animation-and-orchestration) records where real-host proof is
  still owed.

### 👁️ Database

- **[PostgreSQL](https://www.postgresql.org/)** — Anchors material state.
- **[Alembic](https://alembic.sqlalchemy.org/) + [pgvector](https://github.com/pgvector/pgvector)**
  — Evolve its schema and extend it with vector search.

### 🛠️ Code Control

- **[Zensical](https://zensical.org/)** — Renders the Hexanomicon.
- **[uv](https://github.com/astral-sh/uv)** — Manages the Python environment and dependencies.
- **[Ruff](https://github.com/astral-sh/ruff) +
  [basedpyright](https://github.com/DetachHead/basedpyright)** — Keep Python source formatted,
  linted, and typed.
- **[pytest](https://pytest.org/) + [Vitest](https://vitest.dev/) +
  [Svelte Check](https://www.npmjs.com/package/svelte-check)** — Keep source and contracts
  verified.

Portions of the database connection setup are adapted from
[Litestar Fullstack](https://github.com/litestar-org/litestar-fullstack). Shipped license
inventories, adapted-source attribution, and regeneration rules live in
[Third-Party Source Notices](THIRD_PARTY_NOTICES.md).

---

> _“The Flesh is temporary. The Word is eternal.”_

### [💀 Join the Cult](https://github.com/hexanomicon/lychd/discussions)
