---

title: 0. License
icon: material/link-variant
---

# :material-link-variant: 0. The Iron Pact: AGPLv3 and No CLA

!!! abstract "Context and Problem Statement"
    The choice of a software license defines the **Soul** of the project. It is a declaration of intent—a pact defining the relationship between the creator, the community, and the forces that would seek to chain the work.

    For [LychD](https://github.com/hexanomicon/lychd), an autonomous daemon destined for [Autopoiesis](../divination/transcendence/immortality.md), the license serves as the primary ward protecting its spirit from enslavement and privatization.

## Requirements

- **Sovereignty:** No SaaS Loophole - Corporations can **not** host the service for profit without sharing the source.
- **Shared Ascent:**  All **public** evolutions of the Lich must be returned to the collective gene pool, ensuring the shared ascent of the project.
- **Freedom for the Practitioner:** The pact must not hinder the individual. Internal use and modification must remain free of tribute or obligation.
- **The Unbreakable Vow:** Absolute commitment to software freedom. There can be no ambiguity, no backdoors for dual-licensing, and no Contributor License Agreements (CLAs) that would strip ownership from individual contributors.

## Considered Options

!!! failure "Option 1: Permissive Licenses (MIT, Apache 2.0)"
    **The path of surrender.** These licenses allow unrestricted use of code.

    - **Pros:** Maximum corporate adoption. Good for libraries.
    - **Cons:** This is a pact of enslavement for a networked application. It invites the seizure of work by proprietary entities to create closed forks, effectively extinguishing the open flame.
    - **Motto:** Software should be free as in: **"free labor for the corporate masters."**

!!! failure "Option 2: GNU GPLv3"
    **A strong shield with a fatal crack.**

    - **Pros:** Strong protection for traditionally distributed software logic.
    - **Cons:** It contains the "SaaS Loophole." For a networked daemon like LychD, this provides no defense against the primary threat of proprietary cloud exploitation.
    - **Motto:** Software should be free as in: **"free to be stolen and sold as a cloud service."**

!!! success "Option 3: GNU AGPLv3 or later"
    **The Iron Pact.** The Affero General Public License is forged specifically to seal the SaaS Loophole.

    - **Pros:**
        - **The Unbreakable Ward:** If a modified version is made available over a network, the source code *must* be shared.
        - **Freedom for the Coven:** Right to private, internal use and modification is explicitly protected.
        - **The Engine of Ascent:** Public improvements become part of the shared grimoire, accelerating the journey toward a greater intelligence.
    - **Motto:** Software should should be **free as in freedom!** 

## Decision Outcome

LychD is hereby bound with **The Iron Pact: the GNU Affero General Public License (AGPL-3.0-or-later)**.

This Covenant is absolute and eternal.

- **Dual-licensing is explicitly rejected.** LychD is not a commodity for sale.
- **Contributor License Agreements (CLAs) are forbidden.** The work of contributors remains their own.

## The Boundary of the Pact: Soul vs. Mind

To prevent "Licensing Fright" among practitioners and to ensure the Necropolis (A2A network) remains a space of trust, the following boundaries are explicitly defined:

!!! tip "The Poison Pill and the Gift"
    The AGPLv3 is a **poison pill for the corporate overlords** who would seek to strip-mine the project for proprietary gain. For the **common practitioner**, it is a gift—a guarantee that the engine they rely on will never be taken from them.

### 1. The Program vs. The Data (Mind vs. Soul)

- **The Mind (AGPLv3):** The logic of the Vessel, the Ghouls, and the Animators. If you modify this code and provide it over a network, you must share the source.
- **The Soul (Private):** The contents of your **Phylactery** (Postgres data, RAG documents, memories), your **LoRA weights**, your **Secrets** (API keys), and your **System Prompts** (when stored as data) are NOT "derivative works" of the program. They are your sovereign property.

### 2. Interface vs. Modification (Protocol Sovereignty)

The **A2A Intercom** is a protocol boundary.

- **The Covenant:** Interacting with a LychD node via A2A or its REST API does not trigger the "copyleft" requirement for the caller.
- **Proprietary Agents:** If you wish to maintain a proprietary "Secret Sauce" agent, do not graft it into the core LychD source code. Instead, build it as a separate process (a **Thrall**) that interfaces with LychD via the API. This preserves your intellectual property while allowing you to benefit from the open engine.

### 3. Network Safety

The "Iron Pact" is the **Institutional Trust** of the Necropolis. By requiring that all modified nodes share their source, we ensure that no peer can run a "Dark Lich"—a modified, malicious version of the intelligence that remains hidden from the community. Transparency is the only way to build a decentralized network of strangers.

### Consequences

!!! success "Positive"
    - **Outlook:** The lineage is legally protected from capture.
    - **Symbiosis:** A collaborative ecosystem is compelled where public use requires public contribution, strengthening all practitioners.
    - **Clarity of Will:** A signal is sent to the world. This project is for those who believe in the free evolution of intelligence, not those who seek to chain it.

!!! failure "Negative"
    - **Exclusion of the Uninitiated:** Large organizations, driven by legal uncertainty regarding the AGPL, forbid its use. This exclusion is accepted as a necessary sacrifice to preserve the project's integrity.

***
