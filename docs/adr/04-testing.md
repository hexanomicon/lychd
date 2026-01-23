---

title: 4. Testing
icon: material/shield-check-outline
---

# :material-shield-check-outline: 4. Structured Testing & Coverage Strategy

!!! abstract "Context and Problem Statement"
    The complexity of an autonomous agentic daemon cannot be validated by manual testing. Without a formal, automated strategy, the system becomes brittle and unsafe to refactor. A rigorous, high-velocity feedback loop is required to maintain the integrity of the "Lych."

## Requirements

- **Reliability:** The test suite must guarantee that new changes do not break existing functionality.
- **Taxonomy:** Clear separation between fast logic tests and slow I/O tests is mandatory.
- **Velocity:** The suite must run in parallel to minimize idle time and maximize developer flow.
- **Data Integrity:** Test data must be typed and dynamic, rather than brittle, static JSON files.
- **Quality Gate:** A quantitative coverage metric must be enforced by the CI pipeline to prevent the erosion of safety.

## Considered Options

!!! failure "Option 1: The Standard Library (`unittest`)"
    Python's built-in, xUnit-style testing framework.

    - **Pros:** Zero external dependencies; guaranteed stability across Python versions.
    - **Cons:** **Boilerplate Heavy. ** - Lacks native support for dependency injection (fixtures). Class-based structures are required for every test. The lack of a robust dependency injection system (fixtures) necessitates complex `setUp`/`tearDown` chains. Assertion output lacks the granular introspection of modern tools.

!!! failure "Option 2: BDD / Keyword Frameworks (Robot Framework, Behave)"
    "Given-When-Then" style syntax or keyword-driven testing to separate test logic from implementation.

    - **Pros:** High readability for non-technical stakeholders.
    - **Cons:** **Abstraction Overhead.** A translation layer ("glue code") is required between natural language and Python. This introduces unnecessary friction for a technical daemon project where the "User" is typically a developer or another system.

!!! success "Option 3: The Pytest Ecosystem"
    A functional paradigm leveraging `pytest` as the primary runner and framework.

    - **Pros:**
        - **Fixtures:** Modular, reusable setup code is achieved via dependency injection without inheritance hierarchies.
        - **Ecosystem:** Native support exists for parallel execution (`xdist`), async loops (`pytest-asyncio`), and deep introspection of failures.
        - **Velocity:** Simple `assert` statements reduce code volume and allow developers to remain in the "Flow."

## Decision Outcome

A strictly configured **Pytest** suite is adopted as the definitive testing standard. Configuration is managed exclusively via `pyproject.toml`.

### 1. The Engine (Pytest + Xdist)

- **Framework:** `pytest` serves as the exclusive testing framework.
- **Parallelism:** Execution is parallelized by default (`-n auto` via `pytest-xdist`) to utilize all available compute resources.
- **Strictness:** `--strict-markers` and `--strict-config` are enabled. Misconfigurations or typos in markers result in immediate build failure.

### 2. The Taxonomy (Markers)

Tests are categorized to manage execution time and infrastructure requirements:

- **`@pytest.mark.unit`:** Pure logic tests. These must be fast, synchronous, and perform zero I/O.
- **`@pytest.mark.integration`:** Tests that cross boundaries (Database, Redis, Filesystem).
- **`@pytest.mark.slow`:** Heavy AI inference or model loading tests.

### 3. The Fabricator (Polyfactory)

- **Dynamic Data:** `Polyfactory` is utilized to generate Pydantic models for testing.
- **Type Safety:** Data generation is linked directly to application model definitions, preventing "fixture drift" where test data becomes out of sync with the actual schema.

### 4. The Quality Gate (Coverage)

- **Tool:** `pytest-cov` is executed on every run.
- **Threshold:** A **mandatory minimum coverage of 80%** is enforced. Builds falling below this threshold are rejected by the CI.
- **Exclusions:** Pragmatic exclusions (e.g., `if TYPE_CHECKING:`, `abstractmethod`) are configured to ensure the focus remains on logic rather than boilerplate.

### Consequences

!!! success "Positive"
    - **Confidence:** Strict configuration prevents "silent failures" in the test suite itself.
    - **Speed:** Parallel execution ensures the feedback loop remains rapid despite the growing complexity of the daemon.
    - **Resilience:** Model-based data generation ensures tests evolve automatically alongside schema changes.

!!! failure "Negative"
    - **Isolation Requirements:** Parallel testing requires absolute isolation. Tests cannot share mutable global state or database rows without risking race conditions.
    - **Maintenance:** High coverage requirements necessitate disciplined test writing for every new capability.
