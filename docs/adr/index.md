---
title:  Covenants
icon: material/pillar
---

# :material-pillar: Architecture Decision Records (Covenants)

!!! abstract "Context and Problem Statement"
    The LychD project is an opinionated, complex system with a unique philosophy ("summoning" over "building"). As the system evolves, the reasoning behind key architectural decisions—such as choosing one system over another—can become lost.

    This lack of historical context can lead to inconsistent design choices, repeated debates, and difficulty in maintaining the project's core architectural principles.

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

**Architecture Decision Records (ADRs)**, as popularized by Michael Nygard, are adopted as the primary mechanism of architectural rigour. All significant decisions for the LychD project are documented in Markdown files within the `docs/adr/` directory.

The right is explicitly reserved to **retrospectively adjust** these ADRs as the architecture evolves. These documents function as "Covenants of Architecture" (living technical contracts) rather than immutable point-in-time records. The Git history serves as the immutable time record of how the system evolved.

### ADR Template

- **Format:** Each ADR is a Markdown file named `XXXX-kebab-case-title.md`.
- **Content Structure:**
    - **Mkdocs Metadata:** Must include a one word `title` (with the number, e.g., "10. Extensions") and a thematic `icon`.
    - **Heading:** The H1 must include the corresponding icon and the full descriptive title.
    - **Context:** Must use `!!! abstract "Context and Problem Statement"`.
        - *Why:* This provides a visual "Flavor Text" box that separates the problem definition from the analysis.
    - **Requirements:** Standard bullet points.
    - **Considered Options:** Must use `!!! failure "Option X"` and `!!! success "Option Y"`.
        - *Why:* This allows readers to instantly scan the document and see which option was chosen without reading the text.
    - **Outcome/Implementation:** Text detailing how the decision is applied.

    - **Consequences:** (Optional) Use only if there are significant side effects not covered in the Pros/Cons. Use `!!! failure "Negative"` and `!!! success "Positive"` when more than one consequence is present; otherwise explain the consequence in the considered options section. Each pro and con starts with a bolded label and a short explanation. Use a `###` header.

### ADR Authoring Patterns (MkDocs / Material)

The documentation stack already enables these authoring features in `mkdocs.yaml`:

- `admonition`
- `pymdownx.details`
- `pymdownx.snippets`
- `pymdownx.superfences`

Use them deliberately. ADRs are technical source, not prose dumps.

#### 1. Admonitions (Decision Scanning)

Use admonitions to make the decision shape legible at a glance:

- `!!! abstract "Context and Problem Statement"` for the problem statement
- `!!! failure "Option X"` for rejected alternatives
- `!!! success "Option Y"` for the selected option
- `!!! success "Positive"` / `!!! failure "Negative"` for consequences when needed

This keeps long ADRs skimmable without removing rigor.

#### 2. Live Snippets (No Duplicated Code Blocks)

Prefer live includes from source files over hand-copied code blocks.

Whole-file include (rare; use only for short files):

````md
```python
;--8<-- "src/lychd/config/runes/protocols.py"
```
````

Exact line-slice include (preferred):

````md
```python
;--8<-- "src/lychd/config/runes/base.py:14:86"
```
````

Named section include (optional, when source files carry snippet markers):

````md
```python
;--8<-- "src/lychd/system/services/scribe.py:sample_section"
```
````

Guidelines:

- Use repo-root paths only.
- Prefer exact slices for implementation proof.
- Keep snippets short and local to the claim they support.
- Keep conceptual explanation in ADR prose; snippets provide evidence, not substitute architecture reasoning.

#### 3. Collapsed Snippet Blocks (Default)

Wrap snippet-backed proofs in collapsed details blocks so the ADR remains readable by default:

````md
??? example "Live snippet: `src/lychd/config/runes/base.py:14`"
    ```python
    ;--8<-- "src/lychd/config/runes/base.py:14:86"
    ```
````

Behavior:

- `???` = collapsed by default
- `???+` = expanded by default

Use collapsed blocks for most implementation references. Expand by default only when the snippet is central to understanding the ADR.

#### 4. Wording Discipline (Technical Source Style)

ADR prose should be direct and durable:

- Prefer present-tense descriptions of current architecture and contracts.
- Use future tense only for explicit follow-on work or deferred ADRs.
- **Indirect Third Person:** First-person pronouns (we, our, us) are forbidden. All prose must be in the indirect third person (e.g., "The system provides..." instead of "We provide...").
- Prefer direct claims over contrast formulas where possible.
- Preserve lore vocabulary when it improves precision, but keep ADRs developer-heavy and operationally explicit.

#### 5. Inter-ADR Referencing (Covenant Overlap)

- Earlier ADRs may foreshadow or subtly reference later concepts to establish the shape of the architecture.
- Later ADRs should expand upon and specify the details foreshadowed by earlier ADRs (e.g., the Extensions ADR provides the summary of what is being extended, while specific extension ADRs detail the "how").
- Explicit linking is permitted and encouraged to bind the covenants together.
