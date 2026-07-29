---
title: 0. License
icon: material/link-variant
---

# :material-link-variant: 0. License

!!! abstract "Context and Problem Statement"
    The choice of a software license defines the **Soul** of the project. It is a declaration of intent—a pact defining the relationship between the creator, the community, and the forces that would seek to chain the work.

    For [LychD](https://github.com/hexanomicon/lychd), an autonomous daemon destined for [Autopoiesis](../divination/transcendence/immortality.md), the license serves as the primary ward protecting its spirit from enslavement and privatization, while maintaining the flexibility required for sovereign local execution.

## Requirements

- **Sovereignty:** LychD defends against Cloud capture primarily by architecture. It is a local-first daemon whose durable continuity belongs on the Magus's own iron. MPL-2.0 protects distributed covered files; it does not treat hosted network access as distribution.
- **Shared Ascent:** Distributed modifications to MPL-covered core files must remain source-available to their recipients, ensuring the shared ascent of the project where the body is actually passed onward.
- **Convergent Forking:** Forks and independent implementations must remain possible, especially across the A2A boundary, but distributed modifications to the canonical core should not disappear into closed lineages. The license should keep the roads open while preserving file-level reciprocity for the shared body.
- **Freedom for the Practitioner:** The pact must not hinder the individual. Internal use, static linking, and modification must remain free of tribute or obligation.
- **The Unbreakable Vow:** Absolute commitment to software freedom. There can be no CLA, no private relicensing backdoor, and no ambiguity about the contribution grant. Plain MPL-2.0 Secondary License compatibility remains intact unless a future ADR intentionally changes that posture.

## Considered Options

!!! failure "Option 1: Permissive Core Licenses (MIT, Apache 2.0)"
    **The path of fragmentation for the daemon core.** These licenses allow unrestricted use of code.

    - **Pros:** Maximum corporate adoption. Good for libraries, protocol examples, SDKs, conformance fixtures, and other surfaces where frictionless interoperability matters more than shared core evolution.
    - **Cons:** For the canonical daemon core, permissive licensing invites closed modified distributions that fragment away from the shared body without returning foundation changes. This optimizes divergence over convergence: forks remain legal, but their improvements can disappear into private lineages instead of strengthening the inspectable commons.
    - **Motto:** Software should be free as in: **"free labor for the corporate masters."**

!!! failure "Option 2: GNU AGPLv3"
    **A strong shield with a fatal crack.**

    - **Pros:** Strong protection for network-distributed software logic.
    - **Cons:** It would make proprietary in-process extensions legally burdensome. The Lich's architecture relies heavily on **[Extensions](05-extensions.md)** and local **[Animators](../sepulcher/animator/index.md)**. If practitioners must isolate private "Secret Sauce" behind external service boundaries to avoid broader copyleft obligations, local sovereignty and low-latency grafting are crippled.

!!! failure "Option 3: GNU LGPLv3"
    **A library covenant for the wrong body.**

    - **Pros:** Allows proprietary applications to link against a free library while keeping modifications to that library open.
    - **Cons:** LGPL is framed around a Library, an Application, and a Combined Work. LychD is a daemon and composed runtime, not primarily a linkable library. LGPL's replacement/relinking obligations add operational complexity without solving the SaaS boundary or improving private extension sovereignty.
    - **Motto:** Software should be free as in: **"replaceable library component."**

!!! failure "Option 4: Source-Available Licenses (BSL, SSPL, FSL)"
    **The gilded cage.** These include the Business Source License (BSL), Server Side Public License (SSPL), and Functional Source License (FSL).

    - **Pros:** They aggressively stop Cloud overlords from monetizing the code.
    - **Cons:** They are not true open source. While they protect against the cloud giants, they do so by establishing a single central authority that restricts commercial freedom. The Lich belongs to the practitioners, not a central entity hoarding intellectual property. This contradicts the fundamental ethos of a truly free, decentralized network.
    - **Motto:** Software should be free as in: **"the grimoire opens, but the tollgate remains."**

!!! failure "Option 5: Nihilistic Licenses (WTFPL, Unlicense)"
    **The path of chaos.** These include the WTFPL and the Unlicense.

    - **Pros:** Undeniable coolness and the raw appeal of mindless anarchy.
    - **Cons:** They hold no legal ground and are practically pointless. They offer no structure, protection, or defense against capture. LychD forges pacts with intent; it does not abandon its creations to the dark.
    - **Motto:** Software should be free as in: **"free until the first lawyer arrives."**

!!! success "Option 6: Mozilla Public License 2.0 (MPL 2.0)"
    **The Iron Pact.** The MPL 2.0 is forged to balance collective progress with individual sovereignty.

    - **Pros:**
        - **Shared Evolution:** If modified *core files* are distributed outside an organization, those files must remain source-available under MPL.
        - **Freedom for the Coven:** Right to private, internal use and modification is explicitly protected.
        - **Static Linking Enabled:** It allows for static linking and private extensions without requiring the entire Larger Work to use MPL terms. This saves the **[A2A Necropolis](26-a2a.md)** network by ensuring that nodes can maintain their local advantage while still participating in the Swarm.
        - **Honest SaaS Boundary:** It does not provide an AGPL-style network-use trigger. LychD accepts this in exchange for private-extension sovereignty and relies on local-first architecture, reproducible provenance, peer selection, and protocol boundaries for cloud resistance.
    - **Motto:** Software should be **free as in freedom!**

## Decision Outcome

LychD is hereby bound with **The Iron Pact: the Mozilla Public License 2.0 (MPL-2.0)**.

This Covenant is absolute and eternal.

- **Private relicensing is explicitly rejected.** LychD is not a commodity for sale. There is no CLA and no side grant that lets a central owner sell proprietary terms to the core.
- **Plain MPL compatibility is preserved.** LychD currently uses plain MPL-2.0 and does not attach the Exhibit B "Incompatible With Secondary Licenses" notice. Eligible Larger Works may therefore use the MPL-2.0 Secondary License path under the license's own terms. That compatibility is not a private dual-license sales path.
- **Inbound equals outbound:** The corporate rights-grab is rejected. Contributions are accepted
  under the same MPL-2.0 terms under which LychD distributes them. There is no CLA, private
  relicensing grant, or claim that an unaudited “implicit DCA” substitutes for the standard DCO.
  A future DCO policy would require the exact certification, contributor instructions, and
  enforcement in one reviewed change.

## The Boundary of the Pact: Soul vs. Mind

To prevent "Licensing Fright" among practitioners and to ensure the Necropolis (A2A network) remains a space of trust, the following boundaries are explicitly defined:

!!! tip "Local-First Architecture and the Gift"
    MPL 2.0 is one part of LychD's resistance to capture. It protects the files that are distributed, while the broader system protects sovereignty through local execution, protocol boundaries, reproducible composition, and the refusal to make hosted continuity the source of truth. For the **common practitioner**, it is a gift: the shared body remains open where it is passed onward, while private sovereign extensions remain possible.

!!! warning "License Precision"
    MPL-2.0 is file-level copyleft triggered by distribution, not by mere hosted use. A cloud operator that modifies server-side LychD code and only offers access over a network may not be required by MPL alone to publish those changes. This is the deliberate trade: AGPL gives stronger network copyleft, while MPL preserves private in-process extension sovereignty. For the steward's practical interpretation, see Mozilla's [MPL 2.0 FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/).

!!! note "Ideas, Source, and Reimplementation"
    The license governs covered source code, not abstract ideas, architecture, protocols, or doctrine. The ADRs intentionally make LychD's ideas legible; independent implementations may study those ideas and build their own bodies, especially across the A2A boundary. Copying or modifying covered LychD source remains governed by MPL-2.0. Clean-room claims are fact-specific and are not a project promise. This is aligned with **[Assimilation (35)](35-assimilation.md)**: patterns may be studied and re-expressed without pretending every implementation must share one body.

### 1. The Program vs. The Data (Mind vs. Soul)

- **The Mind (MPL 2.0):** The core logic of the Vessel, the Ghouls, and the Animators. Modified core files must remain source-available to recipients when distributed.
- **The Soul (Private):** The contents of the Magus's **Phylactery** (Postgres data, RAG documents, memories), **LoRA weights**, **Secrets** (API keys), and **System Prompts** (when stored as data) are NOT "derivative works" of the program. They remain sovereign property.

### 2. Interface vs. Modification (Protocol Sovereignty)

The **A2A Intercom** is a protocol boundary.

- **Private Extensions:** Because MPL 2.0 allows static linking with other code under different licenses, proprietary "Secret Sauce" agents can be grafted directly into a local LychD instance as extensions without being forced open.
- **The Covenant:** Interacting with a LychD node via A2A or its REST API does not trigger the copyleft requirement for the caller.

### 3. Network Safety

The "Iron Pact" is the **Institutional Trust** of the Necropolis. By requiring distributed modifications to covered core files to share their source with recipients, the pact prevents distributed packages and peer-deployed copies from hiding changes to the foundation of the intelligence. It does not police private hosted operations by itself. By allowing private extensions, it keeps the network a decentralized gathering of unique, sovereign actors.

### Consequences

!!! success "Positive"
    - **Outlook:** The distributed core daemon is legally protected from closed redistribution.
    - **Symbiosis:** A collaborative ecosystem is compelled where distribution of modified covered files requires source availability to recipients, strengthening all practitioners who receive the body.
    - **Sovereignty:** Private extensions enable true local-first capabilities, saving the A2A network.

!!! failure "Negative"
    - **File-Level Copyleft:** Copyleft is restricted to the file level rather than the entire project, which means completely separate files are not subject to the license's share-alike provisions.
    - **No SaaS Trigger:** Hosted network use alone does not force publication of server-side modifications. Cloud resistance must come from architecture, trust policy, provenance, and local ownership.

***
