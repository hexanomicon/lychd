---
title: 3. Code Quality
icon: material/check-all
---

# :material-check-all: 3. Strict Toolchain & Code Quality Standards

!!! abstract "Context and Problem Statement"
    A project of this complexity requires an unwavering commitment to quality and determinism. Inconsistent formatting, weak type safety, and slow, fragile dependency management accumulate as technical debt. We require a system that is instantaneous, strict, and reproducible.

## Decision Drivers

- **Determinism:** The development environment must be bit-for-bit identical across all machines (Local and CI).
- **Velocity:** Tooling must be instant. Waiting for environments to solve or linters to run breaks the "Flow."
- **Automated Enforcement:** Quality standards must be enforced by the machine, not by human debate.
- **Early Bug Detection:** The toolchain must catch entire classes of bugs (typing, dependencies) before runtime.

## Considered Options

!!! failure "Option 1: The Legacy Stack (Poetry, Mypy, Flake8)"
    The traditional assembly of Python tooling.

    - **Poetry:** While correct, its dependency solver is slow, and environment management is heavy.
    - **Mypy:** Suffers from performance bottlenecks in large codebases.
    - **Flake8/Black:** Requires managing disparate configuration files and slow CI pipelines.

!!! success "Option 2: The Modern Iron Stack (uv, Ruff, BasedPyright)"
    Adopting the next-generation, high-performance toolchain.

    - **uv:** A Rust-based package manager that replaces pip, poetry, and virtualenv. It provides instant dependency resolution and strict lockfile compliance.
    - **Ruff:** A Rust-based linter/formatter that is orders of magnitude faster than the legacy stack.
    - **BasedPyright:** An enhanced fork of Pyright that fixes type-inference gaps and enforces stricter standards than the mainline release.

## Decision Outcome

**Modern Iron Stack** (`uv`, `ruff`, `basedpyright`) is adopted. This toolchain prioritizes speed, strictness, and Rust-based reliability.

### The Python Pillars

1. **`uv` as the Foundation (Manager):**
    - **Determinism:** `uv.lock` is the single source of truth. We do not use `pip` directly.
    - **Speed:** Environment creation and dependency syncing are effectively instant, removing friction from the "Switching Spheres" context switch.
    - **Workflow:** All commands are executed via `uv run`, ensuring the correct environment is always used.

2. **`Ruff` as the Enforcer (Linter & Formatter):**
    - Acts as the definitive source of truth for code style.
    - Configured to be strict, replacing Flake8, Black, and isort.
    - Rule ignores are documented and deliberate in `pyproject.toml`.

3. **`BasedPyright` as the Judge (Type Checker):**
    - Configured to `typeCheckingMode = "strict"`.
    - We prefer BasedPyright over standard Pyright for its superior handling of complex type interactions and fixes for common inference annoyances.
    - Code must be explicitly and correctly typed. Implicit `Any` is forbidden.

### The Holistic Commitment

Quality controls extend beyond the Python backend. The project's recommended VS Codium extensions (`extensions.json`) and configuration files mandate linting across the entire stack:

- **Markdown:** Linted via `markdownlint` for documentation consistency.
- **Configuration:** Formatted via `prettier` (TOML, YAML, JSON).
- **Frontend:** TailwindCSS and PostCSS tooling ensures UI layer quality.
- **Jinja:** Syntax highlighting and validation for `.jinja` templates.

### Consequences

!!! success "Positive"
    - **Reproducibility:** `uv` guarantees that "it works on my machine" means it works on *every* machine.
    - **Velocity:** The feedback loop (install -> lint -> test) is reduced from minutes to seconds.
    - **Safety:** Type-related bugs are eliminated before runtime.

!!! failure "Negative"
    - **Discipline:** The `strict` BasedPyright setting and `uv`'s strict locking impose a steep learning curve. This is an accepted trade-off for long-term stability.
