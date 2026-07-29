---
title: Covenants
icon: material/pillar
---

# :material-pillar: Architecture Decision Records (Covenants)

!!! abstract "Context and Problem Statement"
    The LychD project is an opinionated, complex system with a unique philosophy ("summoning" over "building"). As the system evolves, the reasoning behind key architectural decisions—such as choosing one system over another—can become lost.

    This lack of historical context can lead to inconsistent design choices, repeated debates, and difficulty in maintaining the project's core architectural principles.

!!! info "Decision is not delivery"
    An accepted Covenant records current architectural law; it does not prove that the capability is
    implemented or validated on a real host. [State of the Work](../state-of-the-work.md) owns the
    public delivery boundary. Source, focused tests, lockfiles, and maintained operator receipts own
    executable evidence. ADR pages do not carry copied status chips.

## Requirements

- **Methodology:** A lightweight, effective method is required to document critical decisions in a way that is version-controlled and accessible alongside the source code.
- **Clarity:** The reasoning for architectural choices must be clear and explicit.
- **Longevity:** Decisions must be recorded in a format that survives team changes and the passage of time.
- **Asynchronicity:** The process must support asynchronous review and contribution, fitting a distributed or solo development model.
- **Discoverability:** The records must be easy for developers to find and consult within the repository.
- **Governance Stability:** Once a decision is recorded, it becomes the current architectural contract and must not drift casually. Changes must be deliberate, traceable, and justified in the record itself or by a later ADR when the decision is truly reversed.

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

These ADRs function as "Covenants of Architecture" (living technical contracts) rather than sealed time capsules. The current text describes the current law. Git history preserves the evolution of that law, while later ADRs remain the mechanism for genuine reversals, competing patterns, or major architectural branch points.

### ADR Template

- **Format:** Each ADR is a Markdown file named `NN-kebab-case-title.md`.
- **Content Structure:**
    - **Docs Metadata:** Must include a one word `title` (with the number, e.g., "10. Extensions") and a thematic `icon`.
    - **Heading:** The H1 must include the corresponding icon and the full descriptive title.
    - **Context:** Must use `!!! abstract "Context and Problem Statement"`.
        - *Why:* This provides a visual "Flavor Text" box that separates the problem definition from the analysis.
    - **Requirements:** Standard bullet points.
    - **Considered Options:** Must use `!!! failure "Option X"` and `!!! success "Option Y"`.
        - *Why:* This allows readers to instantly scan the document and see which option was chosen without reading the text.
    - **Outcome/Implementation:** Text detailing how the decision is applied.

    - **Consequences:** (Optional) Use only if there are significant side effects not covered in the Pros/Cons. Use `!!! failure "Negative"` and `!!! success "Positive"` when more than one consequence is present; otherwise explain the consequence in the considered options section. Each pro and con starts with a bolded label and a short explanation. Use a `###` header.

### ADR Authoring Patterns (Zensical / Material)

The documentation stack already enables these authoring features in `zensical.toml`:

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
;--8<-- "src/lychd/config/runes/base.py:14:71"
```
````

Named section includes are optional and should be used only when source files carry explicit snippet markers. Otherwise, prefer exact line slices.

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
;--8<-- "src/lychd/config/runes/base.py:14:71"
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

#### 6. Cross-Cutting Ownership

An architectural feature that crosses existing offices does not earn a new Covenant merely by
being large. It extends the smallest current owners unless it establishes a genuinely new
authority. Delegated-agent execution follows this rule:

- [Graph (24)](24-graph.md#3-delegated-agent-macro-nodes) owns the macro-node and durable
  `AgentJob` handshake;
- [Security (09)](09-security.md#the-coffin-delegated-agent-profile) owns Coffin containment and
  the Provider Gate;
- [Extensions (05)](05-extensions.md#delegated-agent-runtime-adapters) owns foreign runtime
  adapters;
- [Dispatcher (22)](22-dispatcher.md#delegated-agent-capability-grants) and
  [Orchestrator (23)](23-orchestrator.md#3-delegated-provider-capacity) own selection and capacity
  admission; and
- [Oculus (29)](29-observability.md#4-delegated-agent-evidence) owns evidence projection.

This routing intentionally leaves the Forty-Third Covenant unwritten.
