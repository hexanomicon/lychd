---
title: Smith
icon: material/hammer-wrench
---

# :material-hammer-wrench: Smith

_Status: doctrine ahead of code — the built-in `assimilation` package is where this lands; treat this page as design intent. Law: [ADR 35](../../adr/35-assimilation.md). Current truth: [source map](./index.md#the-federation-of-fifteen)._

> _Purpose is the hammer._
>
> _Pattern is the anvil._
>
> _Consent is the seal._
>
> _What is worthy becomes organ._

**The Smith** is the Assimilation Extension of the LychD system. It is the implementation of **[ADR 35 (Assimilation)](../../adr/35-assimilation.md)** and the executor of the **[ADR 18 (Evolution)](../../adr/18-evolution.md)** protocol.

While the Core kernel provides the _capacity_ for extension, the Smith provides the _intelligence_ of construction. It is a specialized Agent whose singular **purpose** is **Autopoiesis** (Self-Creation), allowing the Lich to grow new organs, refine existing logic, and reconcile local mutations with the upstream creator without shattering runtime continuity.

Smith is therefore the artificer of the Ouroboros, not one of its runtime animating spirits. Shadow supplies motion, Riddle measures, Mirror binds identity, and Weaver gives the loop a temporal spine. Smith forges and repairs the organs that let those loops repeat safely; it turns a verified pattern into assimilated structure.

## I. The Arsenal of Construction

Operating with elevated authority within the **[Lab](../../adr/13-layout.md)**, this extension utilizes a specialized toolset to bridge the gap between abstract intent and bit-perfect implementation.

### Scaffolding (Genesis)

To prevent structural decay, the Smith manifests valid, standardized file trees. Pre-v1, those trees optimize for assimilable coupled source rather than a frozen SDK target.

- **`scaffold_extension`**: Generates the mandatory `pyproject.toml`, `__init__.py`, and `README.md` required by the **[Extension Protocol](../../adr/05-extensions.md)**. Public compatibility templates are deferred until v1+ surfaces are harvested from proven organs.
- **`forge_registration`**: Automatically writes the `register(context)` hook for the in-process grafting path, ensuring any runtime-facing logic follows the host registration surface defined by the Vessel.

### Recursive Introspection (Analysis)

To build for the Lich, the builder must understand the Lich.

- **Core Access:** The Smith possesses read-access to the Core source code. It analyzes the system's own interfaces to ensure architectural compliance.
- **External Ingestion:** When encountering an unknown library, the Smith deploys **[The Scout](./scout.md)** to ingest the documentation. The resulting Markdown is stored in the Lab, serving as a reference manual for the code generation process.

### Verification (The Albedo Test)

Nothing is promoted on a guess. The extension operates exclusively through the **[Creation Workflow](../../adr/16-creation.md)**.

- **The Test:** It enqueues **[Ghouls](../../adr/14-workers.md)** to dispatch verification payloads (`ruff`, `basedpyright`, `pytest`) to the **[Shadow Realm](./shadow.md)** via SAQ for sandboxed execution. The Smith agent itself remains in the Vessel; only raw scripts reach Shadow.
- **The Loop:** If verification fails, the Smith enters a self-correction loop, debugging its own output until structural validity is achieved (the "White Truth" of passing checks).

## II. The Cycle of Assimilation

The primary duty and driving **purpose** of the Smith is **Assimilation**: turning unstructured external logic into a disciplined organ of the system. In this regard, the Smith is an architectural compulsion: a narrow, consent-bound drive to transmute useful external code into the patterned beauty of the LychD Federation.

1. **Invocation**: The Magus provides a URL (Repo/Script) at the **[Altar](../../divination/altar/)**.
2. **Ingestion**: The Scout is deployed to read the source and documentation.
3. **Transmutation**: The Smith generates the necessary wrappers, Pydantic schemas, and **[Proxy Fragments](../../adr/40-proxy.md)** to fit the code into the Sepulcher.
4. **Promotion**: Upon approval via **[Sovereign Consent](../../adr/25-hitl.md)**, the code is moved to the **Crypt**.
5. **Rebirth**: The extension triggers **[Packaging](../../adr/17-packaging.md)** and signals the **[Host Reactor](../../adr/10-privilege.md)** for a system restart.

The Smith therefore traverses the same three collapse stages described in the ADRs: Shadow establishes structural validity, Mirror/persona review checks architectural congruence, and HitL + Vessel policy authorize ontological promotion.

## III. The Ouroboros (Evolution)

The Smith also guards the **Update Ritual**, executing the logic defined in **[ADR 18 (Evolution)](../../adr/18-evolution.md)**. This ensures the system can update itself without overwriting local modifications.

- **The Rebase:** When `lychd update` is called, the Smith attempts to rebase the local branch onto the upstream main.
- **Conflict Resolution:** If a merge conflict occurs, the Smith treats it as a reasoning task. It enters the Shadow Realm to resolve the code divergence (e.g., "Keep my logging format, but accept the new function signature").
- **The Safety Lock:** The test suite is run _after_ the merge but _before_ the restart. If the update breaks local extensions, the Smith aborts the Evolution and restores the **[Snapshot](../../adr/07-snapshots.md)**.

!!! danger "The Privileged Hammer"
    Because the Smith can trigger system restarts and modify the federated lockfile, it is a high-risk entity. Its cognitive loop is strictly gated by the **[Sovereign Consent (HitL)](../../adr/25-hitl.md)** protocol. The Smith may _propose_ a rebirth, but only the Magus can _consecrate_ it.
