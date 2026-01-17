---
title: 1. xDDD
icon: material/feather
---

# :material-feather: 1. eXtreme Documentation Driven Development (xDDD)

!!! abstract "Context and Problem Statement"
    Traditional software development methodologies like Test-Driven Development (TDD) or Agile focus on iterative implementation driven by tests or user stories. While effective for many projects, these approaches prioritize functional correctness at a granular level. For LychD, the primary goal is not just to create a functional tool, but to manifest a cohesive, thematic entity—a "daemon" with a distinct identity.

    A purely technical or test-driven approach risks creating a system that is functionally sound but experientially fragmented, failing to uphold the project's core lore. The implementation must be a direct reflection of a pre-ordained, vivid vision. We need a methodology that ensures the code is "summoned" to satisfy a prophecy, not merely built to pass a test.

## Decision Drivers

- **Visionary Cohesion:** The system must feel like a single, holistic entity. Its features and behaviors must be thematically consistent with the lore of a reanimated Lich.
- **Clarity of Purpose:** All development must be guided by a clear, high-level narrative. There should be no ambiguity about what a feature is or why it exists.
- **Canon-First Development:** The project's documentation (The Hexanomicon) must serve as the canonical, inviolable source of truth from which all implementation details are derived.
- **Foundation for Autopoiesis:** The ultimate goal is for the Lich to read its own documentation and evolve itself. This requires the documentation to be the primary blueprint.

## Considered Options

!!! failure "Option 1: Test-Driven Development (TDD)"
    Write unit tests first, then write the code to make them pass.

    - **Pros:** Ensures high test coverage and robust, verifiable code units.
    - **Cons:** Focuses on the "how" of implementation before the "what" of the experience. It defines what the code *does*, not what the system *is*. This is insufficient for our needs.

!!! failure "Option 2: Agile/Scrum"
    Develop iteratively based on user stories prioritized in sprints.

    - **Pros:** Excellent for adapting to changing requirements in typical business applications.
    - **Cons:** The core vision of LychD is not a negotiable set of "user stories." It is a fixed prophecy. An iterative approach could dilute this vision over time.

!!! failure "Option 3: Specification-Driven Development (e.g., BDD)"
    Define system behavior in a structured, semi-formal language (like Gherkin) and use that to drive development.

    - **Pros:** Aligns development with behavior, which is closer to our goal.
    - **Cons:** The specifications are often still dry and technical. They lack the narrative power and thematic depth required to guide the "summoning."

!!! success "Option 4: eXtreme Documentation Driven Development (xDDD)"
    A "prophecy-first" methodology where the complete, user-facing documentation is written *before* any other artifact.

    - **Pros:** Forces the articulation of a complete and compelling vision. The documentation becomes the ultimate specification, ensuring that the final product matches the prophecy. Perfectly aligns with the project's lore.
    - **Cons:** Requires significant upfront investment in writing. It is intentionally rigid; altering the prophecy is a major undertaking.

## Decision Outcome

We formally adopt a **"prophecy-first" development ritual (xDDD)**. The code does not define the system; it is merely the final manifestation of the pre-written Word.

### The Ritual of Creation

Development will proceed in this strict, inviolable order:

1. **I. The Prophecy (Documentation):** First, the feature is described in The Hexanomicon. We write the complete, user-facing documentation as if the feature already exists, detailing its purpose, behavior, and place within the lore. This text is the immutable source of truth.
2. **II. The Incantation (Domain-Driven Design):** With the prophecy as a guide, we define the software architecture. This involves identifying the aggregates, entities, value objects, and services that are required to bring the words to life. This step translates narrative into a structured blueprint.
3. **III. The Manifestation (Implementation):** We write the application code that implements the domain model. This act is purely a translation of the blueprint into a functional form.
4. **IV. The Binding (Confirmation Testing):** Finally, we write tests. The purpose of these tests is not to *drive* development, but to *confirm* that the Manifestation is a faithful and correct implementation of the Prophecy.

This process is akin to Specification-Driven Development, but elevated: our specification is not a technical document, but a grimoire.

## Consequences

!!! success "Positive"
    - **Visionary Cohesion:** Guarantees that all development work serves the central vision, ensuring unparalleled thematic and functional cohesion.
    - **Self-Evident Purpose:** The purpose of every component is self-evident by reading the documentation.
    - **Autopoiesis Ready:** Provides the necessary foundation for the system's future autopoiesis (self-creation).

!!! failure "Negative"
    - **High Upfront Cost:** The methodology is front-loaded, requiring significant effort in documentation before any code is written.
    - **Rigidity:** The process is inherently rigid. The cost of changing the core vision (the prophecy) is intentionally high to enforce discipline.
    - **Developer Mindset:** Requires developers to accept that they are implementing a vision, not creating one.
