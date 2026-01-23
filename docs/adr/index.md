---
title: The Covenants
icon: material/pillar
---

# :material-pillar: Architecture Decisions Records (Covenants)

!!! abstract "Context and Problem Statement"
    The LychD project is an opinionated, complex system with a unique philosophy ("summoning" over "building"). As the system evolves, the reasoning behind key architectural decisions—such as choosing Litestar over FastAPI, or Quadlets over Docker Compose—can become lost.

    New contributors (or even the original author) may struggle to understand why certain paths were taken and others were explicitly rejected. This lack of historical context can lead to inconsistent design choices, repeated debates, and difficulty in maintaining the project's core architectural principles.

## Requirements

- **Methodology:** A lightweight, effective method is required to document critical decisions in a way that is version-controlled and accessible alongside the source code.
- **Clarity:** The reasoning for architectural choices must be clear and explicit.
- **Longevity:** Decisions must be recorded in a format that survives team changes and the passage of time.
- **Asynchronicity:** The process must support asynchronous review and contribution, fitting a distributed or solo development model.
- **Discoverability:** The records must be easy for developers to find and consult within the repository.
- **Immutability:** Once a decision is recorded, it must be considered a settled matter unless formally superseded.

## Considered Options

!!! failure "Option 1: Wiki Pages"
    Store architectural decisions in a project wiki (e.g., GitHub Wiki).

    - **Pros:** Easy to edit, good for collaborative brainstorming.
    - **Cons:** Not directly version-controlled with the source code, can become outdated or fragmented, lacks a formal status tracking process.

!!! failure "Option 2: Long-Form Design Documents"
    Write detailed design documents in a format like Google Docs or Confluence.

    - **Pros:** Can be extremely detailed and comprehensive.
    - **Cons:** Heavyweight, lives outside the repository, often becomes "write-once, never-read," poor for capturing specific, atomic decisions.

!!! success "Option 3: Architecture Decision Records (ADRs)"
    Use lightweight Markdown files stored in the project repository (`docs/adr/`) to document individual architectural decisions.

    - **Pros:** Version-controlled with the code, follows a simple template, encourages atomic and focused decisions, supports asynchronous review via pull requests.
    - **Cons:** Can proliferate if not managed; requires discipline to maintain.

## Decision Outcome

**Architecture Decision Records (ADRs)**, as popularized by Michael Nygard are adopted as primary mechanism of architectural rigour. All significant decisions for the LychD project will be documented in Markdown files within the `docs/adr/` directory.

### ADR Template and Process

- **Format:** Each ADR will be a Markdown file named `XXXX-kebab-case-title.md`.
- **Content Structure:**
    - **Mkdocs Metadata:** Must include a one word `title` (with the number, e.g., "10. Extensions") and a thematic `icon`.
    - **Heading:** The H1 must include the corresponding icon and the full descriptive title.
    - **Context:** Must use `!!! abstract "Context and Problem Statement"`.
        - *Why:* This provides a visual "Flavor Text" box that separates the problem definition from the analysis.
    - **Requirements:** Standard bullet points.
    - **Considered Options:** Must use `!!! failure "Option X"` and `!!! success "Option Y"`.
        - *Why:* This allows readers to instantly scan the document and see which option was chosen without reading the text.
    - **Outcome/Implementation:** Text detailing how the decision is applied.
    - **Consequences:** (Optional) Use only if there are significant side effects not covered in the Pros/Cons. Must use `!!! failure "Negative"` and `!!! success "Positive"` if its is not a single consequence and otherwise they are explained in considered options. Each pro and con must start with a bolded benefit, which is explained. use ### header.

- **Process:**
    1. New ADRs are created with the status "Proposed" via Pull Request.
    2. After discussion, the status becomes "Accepted" or "Rejected".
    3. Future ADRs can mark older ones as "Superseded".
