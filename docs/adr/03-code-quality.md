---
title: 3. Code Quality
icon: material/check-all
---

# :material-check-all: 3. Strict Code Quality and Linting Standards

!!! abstract "Context and Problem Statement"
    A project of this complexity and ambition requires an unwavering commitment to code quality. Inconsistent formatting, unclear style, and weak type safety can quickly accumulate as technical debt, leading to a codebase that is difficult to read, maintain, and safely modify. Allowing stylistic debates in code reviews is a waste of cognitive resources that should be focused on architectural and logical correctness.

    We need to establish a single, non-negotiable, and automatically enforceable standard for code quality. This standard must cover static analysis, linting, formatting, and type checking, ensuring that all contributions adhere to the same high bar of engineering excellence.

## Decision Drivers

- **Consistency:** All code in the repository must look and feel as if it were written by a single, disciplined author.
- **Automated Enforcement:** Quality standards must be enforced by tools, not by human reviewers during pull requests.
- **Early Bug Detection:** The toolchain must be able to catch entire classes of potential runtime bugs (especially type-related errors) during development.
- **Holistic Quality:** The commitment to quality should extend beyond Python to all project artifacts, including documentation, configuration files, and frontend assets.

## Considered Options

!!! failure "Option 1: Manual Enforcement / Loose Guidelines"
    Rely on human reviewers to enforce a set of informal style guides.

    - **Pros:** Low initial setup cost.
    - **Cons:** A recipe for inconsistency, endless debates, and low-quality code. It is fundamentally unprofessional.

!!! success "Option 2: Automated, Strict, and Opinionated Tooling"
    Adopt a best-in-class, modern toolchain and configure it for maximum strictness. Mandate that all code must pass these checks to be considered for inclusion.

    - **Pros:** Creates a "quality floor" that eliminates stylistic debates and catches bugs early. Radically improves maintainability and developer velocity.
    - **Cons:** Can have a slight learning curve for new contributors; requires discipline.

## Decision Outcome

We will enforce a strict set of code quality standards through a mandatory, automated toolchain. Adherence to these standards is not optional. The `pyproject.toml` file serves as the canonical configuration for this toolchain.

### The Python Pillars

1. **`Ruff` as the Linter and Formatter:**
    - We will use Ruff to enforce a superset of community standards (flake8, isort, pep8-naming, etc.).
    - Ruff will also be used as the definitive code formatter, ensuring a consistent style across the entire codebase.
    - The configuration will be tuned to be strict, with specific, deliberate rule ignores documented in the `pyproject.toml`.

2. **`Pyright` as the Type Checker (in `strict` mode):**
    - We will use Pyright for static type analysis, configured to its strictest possible setting (`typeCheckingMode = "strict"`).
    - This decision means that all code must be explicitly and correctly typed. The use of `Any` is strongly discouraged, and all function signatures and variable assignments must be type-complete.

### The Holistic Commitment

Our dedication to quality is not limited to Python. The project's recommended VS Code extensions (`extensions.json`) and configuration files formalize a commitment to quality across the entire stack:

- **Markdown:** All documentation will be linted via `markdownlint` to ensure consistency and readability.
- **Configuration Files:** Linters and formatters for TOML, YAML, and JSON (`prettier`) will be used.
- **Frontend Assets:** Tooling for TailwindCSS, PostCSS, and Jinja templates will ensure the quality of the UI layer.
- **Systemd Units:** Tooling will be used to provide syntax highlighting and support for `.quadlet` and `.service` files.

This holistic approach ensures that every artifact in the repository, not just the Python code, is treated as a first-class citizen with a high standard of quality.

### Consequences

!!! success "Positive"
    - **Maintainability:** The codebase will be exceptionally clean, consistent, and maintainable.
    - **Safety:** A significant number of potential bugs, especially type-related errors, will be caught before the code is ever run.
    - **Focus:** Code reviews can focus on architectural and logical substance, as stylistic concerns are handled automatically.

!!! failure "Negative"
    - **Learning Curve:** The strictness, particularly of the type checker, imposes a high degree of discipline on developers. This is a deliberate and accepted trade-off.
