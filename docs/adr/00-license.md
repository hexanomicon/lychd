---

title: 0. License
icon: material/link-variant
---

# :material-link-variant: 0. The Iron Pact: MPL 2.0 and Implicit DCA

!!! abstract "Context and Problem Statement"
    The choice of a software license defines the **Soul** of the project. It is a declaration of intent—a pact defining the relationship between the creator, the community, and the forces that would seek to chain the work.

    For [LychD](https://github.com/hexanomicon/lychd), an autonomous daemon destined for [Autopoiesis](../divination/transcendence/immortality.md), the license serves as the primary ward protecting its spirit from enslavement and privatization, while maintaining the flexibility required for sovereign local execution.

## Requirements

- **Sovereignty:** We are defending against Cloud overlords by architecture. LychD is a local-first daemon. If they want to change the core engine, they must redo it and share it.
- **Shared Ascent:** All **public** evolutions of the Lich's core engine must be returned to the collective gene pool, ensuring the shared ascent of the project.
- **Freedom for the Practitioner:** The pact must not hinder the individual. Internal use, static linking, and modification must remain free of tribute or obligation.
- **The Unbreakable Vow:** Absolute commitment to software freedom. There can be no ambiguity, no backdoors for dual-licensing, and an **Implicit Developer Certificate of Origin (DCA)** that covers contributions without requiring individual contributors to sign git commits.

## Considered Options

!!! failure "Option 1: Permissive Licenses (MIT, Apache 2.0)"
    **The path of surrender.** These licenses allow unrestricted use of code.

    - **Pros:** Maximum corporate adoption. Good for libraries.
    - **Cons:** This is a pact of enslavement for a networked application. It invites the seizure of work by proprietary entities to create closed forks, effectively extinguishing the open flame.
    - **Motto:** Software should be free as in: **"free labor for the corporate masters."**

!!! failure "Option 2: GNU AGPLv3"
    **A strong shield with a fatal crack.**

    - **Pros:** Strong protection for network-distributed software logic.
    - **Cons:** It strictly forbids static linking with proprietary code. The Lich's architecture relies heavily on **[Extensions](05-extensions.md)** and local **[Animators](../sepulcher/animator/index.md)**. If practitioners are legally blocked from grafting their own private "Secret Sauce" extensions without copyleft infection, their local sovereignty is crippled.

!!! failure "Option 3: Source-Available Licenses (BSL, SSPL, FSL)"
    **The gilded cage.** These include the Business Source License (BSL), Server Side Public License (SSPL), and Functional Source License (FSL).

    - **Pros:** They aggressively stop Cloud overlords from monetizing the code.
    - **Cons:** They are not true open source. While they protect against the cloud giants, they do so by establishing a single central authority that restricts commercial freedom. The Lich belongs to the practitioners, not a central entity hoarding intellectual property. This contradicts the fundamental ethos of a truly free, decentralized network.
    - **Motto:** Software should be free as in: **"free to study the grimoire, but bound by the master's toll."**

!!! failure "Option 4: Nihilistic Licenses (WTFPL, Unlicense)"
    **The path of chaos.** These include the "Do What The Fuck You Want To Public License" (WTFPL) and the Unlicense.

    - **Pros:** Undeniable coolness and the raw appeal of mindless anarchy.
    - **Cons:** They hold no legal ground and are practically pointless. They offer no structure, protection, or defense against capture. We forge pacts with intent; we do not simply abandon our creations to the void.
    - **Motto:** Software should be free as in: **"free to do whatever you want, until someone with a lawyer stops you."**

!!! success "Option 5: Mozilla Public License 2.0 (MPL 2.0)"
    **The Iron Pact.** The MPL 2.0 is forged to balance collective progress with individual sovereignty.

    - **Pros:**
        - **Shared Evolution:** If a modified version of the *core files* is made available, the source code *must* be shared.
        - **Freedom for the Coven:** Right to private, internal use and modification is explicitly protected.
        - **Static Linking Enabled:** It allows for static linking and private extensions without infecting the entire codebase. This saves the **[A2A Necropolis](26-a2a.md)** network by ensuring that nodes can maintain their local advantage while still participating in the Swarm.
    - **Motto:** Software should be **free as in freedom!**

## Decision Outcome

LychD is hereby bound with **The Iron Pact: the Mozilla Public License 2.0 (MPL-2.0)**.

This Covenant is absolute and eternal.

- **Dual-licensing is explicitly rejected.** LychD is not a commodity for sale.
- **Implicit DCA:** We reject the corporate rights-grab. There is **no CLA to sign**. We rely on an Implicit DCA. By reading the contributing guide, you are aware of the policy. Everything you commit is covered—you do not need to manually sign git commits. Combined with MPL 2.0, this makes LychD an absolute sanctuary for builders to protect both their open-source contributions and their proprietary extensions.

## The Boundary of the Pact: Soul vs. Mind

To prevent "Licensing Fright" among practitioners and to ensure the Necropolis (A2A network) remains a space of trust, the following boundaries are explicitly defined:

!!! tip "Hostile Architecture and the Gift"
    The MPL 2.0 is **hostile architecture against the corporate overlords** who would seek to strip-mine the project for proprietary gain. For the **common practitioner**, it is a gift—a guarantee that the engine they rely on will never be taken from them, while empowering them to build private, sovereign extensions.

### 1. The Program vs. The Data (Mind vs. Soul)

- **The Mind (MPL 2.0):** The core logic of the Vessel, the Ghouls, and the Animators. If you modify these files, you must share the source.
- **The Soul (Private):** The contents of your **Phylactery** (Postgres data, RAG documents, memories), your **LoRA weights**, your **Secrets** (API keys), and your **System Prompts** (when stored as data) are NOT "derivative works" of the program. They are your sovereign property.

### 2. Interface vs. Modification (Protocol Sovereignty)

The **A2A Intercom** is a protocol boundary.

- **Private Extensions:** Because MPL 2.0 allows static linking with other code under different licenses, you can build proprietary "Secret Sauce" agents and graft them directly into your local LychD instance as extensions without being forced to open-source them.
- **The Covenant:** Interacting with a LychD node via A2A or its REST API does not trigger the copyleft requirement for the caller.

### 3. Network Safety

The "Iron Pact" is the **Institutional Trust** of the Necropolis. By requiring that all modified core files share their source, we ensure that no peer can silently fork the foundation of the intelligence. Yet, by allowing private extensions, we ensure that the network remains a decentralized gathering of unique, sovereign actors.

### Consequences

!!! success "Positive"
    - **Outlook:** The core lineage is legally protected from capture.
    - **Symbiosis:** A collaborative ecosystem is compelled where public use of the core engine requires public contribution, strengthening all practitioners.
    - **Sovereignty:** Private extensions enable true local-first capabilities, saving the A2A network.

!!! failure "Negative"
    - **File-Level Copyleft:** Copyleft is restricted to the file level rather than the entire project, which means completely separate files are not subject to the license's share-alike provisions.

***
