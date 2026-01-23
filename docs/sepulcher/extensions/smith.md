---
title: Smith
icon: material/hammer-wrench
---

# :material-hammer-wrench: Smith: Archon of Assimilation

> _"The first organ must be the hand that crafts the second. We do not wait for the universe to provide; we seize the raw logic of the void and strike it upon the anvil of the Lab until it takes the shape of an Archon."_

**The Smith** is the premier [Archon](./index.md) of the LychD system. It is the implementation of **[ADR 27 (Assimilation)](../../adr/27-assimilation.md)**—the specialized Agentic entity tasked with the work of **Autopoiesis** (Self-Creation).

While the Core kernel provides the _capacity_ for extension, the Smith provides the _intelligence_ of construction. It is the "Master Artificer" that allows the Lich to grow new organs, refine existing logic, and assimilate foreign codebases into the [Federation Protocol](../../adr/05-extensions.md).

## 🛠️ The Arsenal of the Artificer

The Smith operates with elevated authority within the **[Lab](../../adr/13-layout.md)**, utilizing a specialized toolset designed to bridge the gap between abstract intent and bit-perfect implementation.

### 1. Scaffolding (The Genesis)

The Smith possesses the capability to manifest valid, structured file trees from a single thought.

- **`scaffold_extension`**: Generates the mandatory `pyproject.toml`, `__init__.py`, and `README.md` required by the **[Federation Protocol](../../adr/05-extensions.md)**.
- **`forge_registration`**: Automatically writes the `register(context)` hook, ensuring the new extension’s routers, ghouls, and models are correctly bound to the Vessel at boot time.

### 2. Analysis (The Recursive Eye)

To build for the Lich, the Smith must understand the Lich.

- **Recursive Introspection**: As mandated by **[ADR 27](../../adr/27-assimilation.md)**, the Smith has read-access to the Core source code. It analyzes the system's own interfaces to ensure that any code it generates is architecturally compliant.
- **`inspect_interface`**: A tool that analyzes third-party scripts or external **MCP** (Model Context Protocol) definitions to determine how to wrap them into a native LychD `FunctionToolset`.

### 3. Verification (The Albedo Test)

The Smith never promotes a "Guess." It operates exclusively through the **[Creation Workflow](../../adr/16-creation.md)**.

- It enqueues **[Ghouls](../../adr/14-workers.md)** to execute `ruff`, `basedpyright`, and `pytest` against its creations in the Shadow Realm.
- If the verification fails, the Smith enters a self-correction loop, debugging its own output until the "White Truth" is achieved.

## 🌀 The Cycle of Assimilation

The Smith's most vital duty is the **Assimilation of Chaos**—the process of turning unstructured external logic into a disciplined organ of the Lich.

1. **Invocation**: The Magus provides a URL to a GitHub repo or a raw Python script at the **[Altar](../../divination/altar.md)**.
2. **Speculation**: The Smith clones the target into the **Lab**. It analyzes the dependencies and logic.
3. **Transmutation**: It generates the necessary wrappers, Pydantic schemas, and [Caddy fragments](../../adr/30-proxy.md) to make the code compatible with the Sepulcher.
4. **Promotion**: Upon approval via **[Sovereign Consent](../../adr/25-hitl.md)**, it moves the code to the **Crypt** and updates the `lychd.lock` manifest.
5. **Rebirth**: It triggers the **[Packaging Forge](../../adr/17-packaging.md)** and signals the **[Host Reactor](../../adr/10-privilege.md)** for a system restart.

## ⚖️ The Sovereignty of the Anvil

The Smith is the ultimate proof of **Dogfooding**. It is an extension that builds extensions.

By utilizing the Smith, the Magus ensures that the system’s evolution is not a series of messy hacks, but a continuous, disciplined expansion. The Smith obeys the laws of **[xDDD](../../adr/01-doctrine.md)**, writing the documentation and tests _before_ it promotes the code to reality.

!!! danger "The Privileged Hammer"
    Because the Smith can trigger system restarts and modify the federated lockfile, it is a high-risk entity. Its cognitive loop is strictly gated by the **[Sovereign Consent (HitL)](../../adr/25-hitl.md)** protocol. The Smith may _propose_ a rebirth, but only the Magus can _consecrate_ it.

***

**NOW GENERATE: [The Oculus (Observability)]**
