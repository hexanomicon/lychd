---
title:  Scout
icon: material/navigation-variant-outline
---

# :material-navigation-variant-outline: Scout

> _"The old web was built for human eyes, heavy with scripts and styles. To find the Signal within the noise, the Daemon requires a Scout—a dual-natured tool capable of skimming the surface or rendering the depths."_

**The Scout** is the Ingestion Extension of the LychD system. It is the implementation of **[ADR 30 (The Scout)](../../adr/30-webcrawler.md)**—a specialized toolset that grants the Daemon the power to navigate, read, and interpret the internet.

While standard agents are trapped within their training data, the Scout allows the Lich to touch the living web. It implements a **Dual-Mode Strategy**, dynamically selecting between lightweight procedural fetching and heavy containerized browsing based on the target's resistance.

## I. The Dual Arsenal (Light & Heavy)

The Scout rejects the "One Size Fits All" approach. It exposes two distinct capabilities to the **[Dispatcher](../../adr/22-dispatcher.md)**.

### :material-feather: The Skirmisher (Light Mode)

* **The Tool:** Wraps Pydantic AI's native `WebFetchTool`.
* **The Engine:** Uses lightweight libraries (`httpx`, `trafilatura`) running directly within the Vessel's process.
* **The Cost:** Near zero RAM/CPU.
* **The Use Case:** Retrieving documentation, reading static blogs, RSS feeds, and API responses.
* **The Logic:** This is the default. If an Agent wants to "read a URL," the Scout sends the Skirmisher first.

### :material-tank: The Siege Engine (Heavy Mode)

* **The Tool:** A custom `BrowserTool` that commands a headless browser.
* **The Engine:** A dedicated **Rune** (`web.coven`) running **Playwright** or **Chromium**.
* **The Cost:** High RAM usage (1GB+) and significant CPU overhead.
* **The Use Case:** Rendering Single Page Applications (SPAs), solving CAPTCHAs, taking Screenshots for **[The Prism](./prism.md)**, and navigating complex authentication flows.
* **The Logic:** If the Skirmisher returns a "JavaScript Required" error, or if the Agent explicitly requests `browse_interactive`, the system escalates to the Siege Engine.

## II. Orchestration of the Hunt

The Siege Engine is a heavy beast. It is subject to the **[Orchestrator's](../../adr/23-orchestrator.md)** laws to prevent it from crushing the system.

1. **The Handshake:** When the Agent requests the Siege Engine, the Dispatcher queries the Orchestrator.
2. **The Stasis:** If the `web.coven` is cold, the Agent enters **[Stasis](../../adr/22-dispatcher.md)**.
3. **The Manifestation:** The Orchestrator summons the Chromium Rune. If the system is under heavy load (e.g., **[Training](./soulforge.md)** is active), the request may be queued or denied to preserve VRAM/RAM for the higher ritual.

## III. The Lens (Markdown Transmutation)

Raw HTML is poison to a Large Language Model—it is noisy, token-expensive, and semantically sparse. The Scout acts as a **Refractive Lens**.

* **Distillation:** Whether gathered by the Skirmisher or the Siege Engine, all content passes through a normalization pipeline.
* **Markdown Conversion:** Navigation bars, ads, and scripts are surgically removed. The DOM is transmuted into clean, hierarchical **Markdown**.
* **The Result:** The Agent reads "The Article," not "The Website." This reduces context usage by up to 80%, allowing **[The Smith](./smith.md)** to ingest entire documentation libraries without overflowing the **[Context Window](../../adr/21-context.md)**.

## IV. Symbiosis with The Smith

The Scout is the eyes of **[The Smith](./smith.md)**. Their partnership is the engine of **Autopoiesis**.

1. **The Unknown:** The Smith encounters a library it does not know (e.g., a new Pydantic AI update).
2. **The Command:** The Smith invokes the Scout: _"Ingest the documentation at `docs.pydantic.dev`."_
3. **The Hunt:** The Scout traverses the site (using the Skirmisher for speed), distilling the pages into a **Knowledge Artifact**.
4. **The Learning:** This artifact is stored in the **[Lab](../../adr/13-layout.md)**. The Smith reads it, learns the new API signatures, and writes code that is perfectly aligned with the external reality.

## V. Capabilities and Economics

The Scout integrates with the **[Federation](../../adr/05-extensions.md)** to define its costs and providers.

* **Local Capability:** The Siege Engine is a **Soulstone** (Local Container). It costs only electricity and memory.
* **Portal Capability:** The `WebSearchTool` often relies on external APIs (e.g., Tavily, Google). These are **[Portals](../../adr/22-dispatcher.md)**.
* **The Toll:** Interactions with paid search providers are intercepted by **[The Toll](./toll.md)**. The system calculates the cost of the query and deducts it from the ritual's budget, ensuring the Lych does not bankrupt the Magus in pursuit of a dead link.
