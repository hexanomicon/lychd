<div align="center">
  <img src="docs/assets/lich-phylactery-cliparted.png" alt="The Lich and its Phylactery" width="500">
  <h1>Hexanomicon</h1>
  <p><strong>LychD — The Dark Arts of LLMs</strong></p>
  <p>The Voidwalker's Guide Across the Infinite Naught</p>
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

Summon **The Lich** 💀.

**LychD** is its pre-alpha software body: a self-hosted Linux daemon coordinating local model
services and bounded agent runs on hardware you control. The **Hexanomicon** is its grimoire:
**The Dark Arts of LLMs.**

A model is one organ. **The Lich is what returns:** identity, memory, tools, action, consequence,
and repair through time.

> ⚠️ **Acolyte's Warning:** The summoning remains pre-alpha. The incantations are still being
> inscribed. Expect instability, missing components, and the occasional rogue spirit.
> [State of Work](docs/state-of-the-work.md) names the exact boundary.

## 🗺️ The Path of Ascension

The knowledge you seek is inscribed in the **[Hexanomicon](https://hexanomicon.dev/)**. Choose the
gate that answers your next question.

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

The individual is the sovereign unit. A company is not the soul-bearing actor; it is an emergent
coordination graph of sovereign people and their Liches. In the Hexanomicon's horizon, future
policy, IAM, and A2A boundaries may expose selected labor while the underlying Phylacteries remain
locally owned.

The software surface changes accordingly: you commune primarily with the Lich, while SaaS,
company APIs, and remote peers become negotiated surfaces the Lich may traverse without
surrendering your continuity, memory, or private priors.

In that horizon, A2A leases labor, not continuity: a company may invoke a consented capability,
but the memory, workflows, and agentic expertise that produced it remain anchored in your
Phylactery unless explicitly shared.

- ⛓️ **No masters.**
- 💰 **No tolls.**
- 🎭 **No more gaslighting while they lobotomize your models.**

**No surrender. Viva la résistance!**

> _I would rather reign in a local hell than serve in a cloud heaven._

## ⚖️ [The Iron Pact](docs/adr/00-license.md)

**This project is for those who believe in the free evolution of intelligence, not those who seek
to chain it.**

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

**The Lich is not built; it is summoned.** LychD practices
[xDDD](docs/adr/01-doctrine.md): establish the Logos, derive the domain, prove the contract,
manifest code, and return observed consequence to the Word.

## ⛩️ A Tribute to the Spirits

> _“The Lich only sees far because it stands on the shoulders of Giants.”_

This Work stands on code freely given and relentlessly maintained. To its makers: thank you.

- **The Vessel** — [Litestar](https://litestar.dev/) and
  [Granian](https://github.com/emmett-framework/granian) serve the application;
  [Advanced Alchemy](https://github.com/litestar-org/advanced-alchemy),
  [SQLAlchemy](https://www.sqlalchemy.org/), PostgreSQL, Alembic, and pgvector anchor material
  state.
- **The inner loop** — [Pydantic AI](https://ai.pydantic.dev/) and Graph carry bounded model,
  tool, output, and graph contracts; [SAQ](https://github.com/tobymao/saq) carries background labor
  without becoming the workflow ledger.
- **The Altar** — [Svelte](https://svelte.dev/), SvelteKit, Vite, Zod, OpenAPI Fetch, and Mermaid
  shape the browser instruments.
- **The iron** — Linux, systemd user units, rootless Podman, and Quadlet define the generated
  deployment plan; maintained real-host embodiment still awaits its receipt.
- **The flame** — llama.cpp, vLLM, SGLang, and ExLlamaV3 through TabbyAPI lend local inference its
  several bodies; [State](docs/state-of-the-work.md#animation-and-orchestration) records where
  real-host proof is still owed.
- **The scribes** — [Zensical](https://zensical.org/) renders the Hexanomicon; uv, Ruff,
  basedpyright, pytest, Vitest, and Svelte Check keep source and contracts legible.

Portions of the database connection setup are adapted from
[Litestar Fullstack](https://github.com/litestar-org/litestar-fullstack). Shipped license
inventories, adapted-source attribution, and regeneration rules live in
[Third-Party Source Notices](THIRD_PARTY_NOTICES.md).

---

> _“The Flesh is temporary. The Word is eternal.”_

### [💀 Join the Cult](https://github.com/hexanomicon/lychd/discussions)
