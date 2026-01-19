---
title: 4. Testing Strategy
icon: material/flask-outline
---

# :material-flask-outline: 4. Structured Testing & Coverage Strategy

!!! abstract "Context and Problem Statement"
    The complexity of an autonomous agentic daemon cannot be validated by manual testing. Without a formal, automated strategy, the system becomes brittle and unsafe to refactor. A rigorous, high-velocity feedback loop is required to maintain the integrity of the "Lych."

## Decision Drivers

- **Reliability:** The test suite must guarantee that new changes do not break existing functionality.
- **Taxonomy:** Clear separation between fast logic tests and slow I/O tests is mandatory.
- **Velocity:** The suite must run in parallel to minimize idle time.
- **Data Integrity:** Test data must be typed and dynamic, not brittle static JSON.
- **Quality Gate:** A quantitative coverage metric must be enforced by the CI pipeline.

## Considered Options

!!! failure "Option 1: The Standard Library (`unittest`)"
    Using Python's built-in, xUnit-style testing framework.

    - **Pros:** Zero external dependencies; guaranteed stability across Python versions.
    - **Cons:** **Boilerplate Heavy.** Requires class-based structures for every test. Lacks a robust dependency injection system (fixtures), necessitating complex `setUp`/`tearDown` chains. Assertion output is verbose and lacks the granular introspection of modern tools.

!!! failure "Option 2: BDD / Keyword Frameworks (Robot Framework, Behave)"
    Adopting "Given-When-Then" style syntax or keyword-driven testing to separate test logic from implementation.

    - **Pros:** Readable by non-technical stakeholders (Product Managers, Business Analysts).
    - **Cons:** **Abstraction Overhead.** Requires maintaining a translation layer ("glue code") between natural language and Python. This introduces unnecessary friction and cognitive load for a technical daemon project where the "User" is a developer or another system.

!!! success "Option 3: The Pytest Ecosystem"
    Adopting `pytest` as the runner and framework, leveraging its functional paradigm.

    - **Pros:** **Fixtures.** The dependency injection system allows for modular, reusable setup code without inheritance hierarchies.
    - **Ecosystem:** Native support for parallel execution (`xdist`), async loops (`pytest-asyncio`), and deep introspection of failures (`pytest-sugar`).
    - **Velocity:** Simple `assert` statements reduce code volume and allow developers to stay in the "Flow" without context-switching to a DSL (Domain Specific Language).

## Decision Outcome

Adopt a strictly configured **Pytest** suite. The `pyproject.toml` file serves as the immutable configuration source.

### 1. The Engine (Pytest + Xdist)

- **Framework:** `pytest` is the exclusive testing framework.
- **Parallelism:** Execution is parallelized by default (`-n auto` via `pytest-xdist`) to maximize resource usage.
- **Feedback:** `pytest-sugar` provides instant visual feedback; `pytest-asyncio` handles the native coroutine loop.
- **Strictness:** `--strict-markers` and `--strict-config` are enabled. Typos in markers or config keys cause immediate build failure.

### 2. The Taxonomy (Markers)

Tests are strictly categorized to manage execution time and dependencies.

- **`@pytest.mark.unit`:** Pure logic tests. Must be fast, synchronous, and zero-I/O.
- **`@pytest.mark.integration`:** Tests that cross boundaries (DB, Redis, Filesystem).
- **`@pytest.mark.slow`:** Heavy AI inference or model loading tests.

### 3. The Fabricator (Polyfactory)

- **Dynamic Data:** `Polyfactory` is used to generate Pydantic models for testing.
- **Type Safety:** Test data generation is linked to the actual model definitions, preventing "fixture drift" where test data no longer matches the application schema.

### 4. The Quality Gate (Coverage)

- **Tool:** `pytest-cov` executes on every run.
- **Threshold:** A **mandatory minimum coverage of 80%** is enforced. Builds below this threshold fail.
- **Exclusions:** Pragmatic exclusions (e.g., `if TYPE_CHECKING:`, `abstractmethod`) are configured to focus on logic, not boilerplate.

### Consequences

!!! success "Positive"
    - **Confidence:** Strict configuration prevents "silent failures" in the test suite itself.
    - **Speed:** Parallel execution ensures the feedback loop remains rapid despite growing complexity.
    - **Resilience:** Model-based data generation ensures tests evolve automatically with schema changes.

!!! failure "Negative"
    - **Complexity:** Parallel testing requires strict isolation. Tests cannot share mutable global state or database rows without causing race conditions.
