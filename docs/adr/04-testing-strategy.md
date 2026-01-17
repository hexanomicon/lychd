---
title: 4. Testing Strategy
icon: material/flask-outline
---

# :material-flask-outline: 4. Structured Testing and Coverage Strategy

!!! abstract "Context and Problem Statement"
    A system with the complexity and autonomous ambitions of LychD cannot be validated by manual testing alone. Without a formal, automated, and comprehensive testing strategy, the project would be brittle, difficult to refactor, and fundamentally unreliable. The cost of a single regression in the autopoiesis engine is too high to leave to chance.

    We need a structured approach to testing that provides a rapid feedback loop for developers, clearly separates different types of tests, and enforces a quantitative measure of quality through code coverage.

## Decision Drivers

- **Reliability:** The test suite must provide high confidence that the application works as intended and that new changes do not break existing functionality.
- **Clarity:** The distinction between fast, self-contained unit tests and slower, resource-dependent integration tests must be clear and explicit.
- **Developer Velocity:** The test suite must run quickly, enabling developers to iterate rapidly. Parallel execution is a key requirement.
- **Data Quality:** Test data, especially for complex Pydantic models, should be generated automatically and be type-safe to avoid brittle, hardcoded fixtures.
- **Enforceable Quality Gate:** We need a concrete, non-negotiable metric for test coverage to ensure a consistent quality floor.

## Considered Options

!!! failure "Option 1: Unstructured Testing"
    Allow developers to write tests in an ad-hoc manner without clear categorization or quality metrics.

    - **Pros:** Low barrier to entry.
    - **Cons:** Leads to an inconsistent, slow, and unreliable test suite that provides a false sense of security.

!!! success "Option 2: A Formal, Multi-Layered Testing Strategy"
    Adopt a standard set of best-in-class tools and establish clear conventions for how tests are written, categorized, and measured.

    - **Pros:** Creates a robust, reliable, and maintainable test suite. Fosters developer confidence and accelerates safe refactoring.
    - **Cons:** Requires initial setup and ongoing discipline.

## Decision Outcome

We will adopt a professional and highly structured testing strategy, with the configuration defined canonically in `pyproject.toml`.

1. **Framework: Pytest**
    - We will use `pytest` as the exclusive framework for all tests, leveraging its powerful fixture system, plugin architecture, and concise syntax.

2. **Test Categorization and Structure:**
    - The test suite will be physically divided into `tests/unit/` and `tests/integration/`.
    - `pytest` markers will be used to logically tag tests, primarily `@pytest.mark.unit` for fast, I/O-free tests and `@pytest.mark.integration` for tests that interact with the database or other external services.

3. **Performance: Parallel Execution**
    - To ensure a rapid feedback loop, tests will be executed in parallel by default using `pytest-xdist` (`-n auto`).

4. **Test Data Generation: Polyfactory**
    - We will use `Polyfactory` as the standard for generating test data, particularly for our Pydantic models. This avoids brittle, manually-defined fixtures and ensures that our test data is always in sync with our type-safe data models.

5. **Quality Gate: Mandatory Code Coverage**
    - We will use `pytest-cov` to measure code coverage on every test run.
    - We will enforce a **mandatory minimum coverage threshold of 80%**. A test run that falls below this threshold will be considered a failure.

### Consequences

!!! success "Positive"
    - **Confidence:** The project will have a robust safety net, enabling developers to refactor and add features with a high degree of confidence.
    - **Speed:** The clear separation of test types and parallel execution ensures that the development feedback loop remains fast and efficient.
    - **Quality:** The mandatory coverage threshold provides an objective, enforceable quality standard for all contributions.

!!! failure "Negative"
    - **Overhead:** This strategy requires discipline. Writing high-quality tests and maintaining the coverage target requires a consistent investment of developer time.
