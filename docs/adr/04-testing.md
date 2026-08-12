---
title: 4. Testing
icon: material/shield-check-outline
---

# :material-shield-check-outline: 4. Testing

!!! abstract "Context and Problem Statement"
    Tests make behavioral claims inspectable when they are fast enough to run, explicit about
    their boundary, and unwilling to impersonate a live host. LychD needs fixtures and
    parametrization without BDD ceremony, parallel execution without shared scratch ambiguity,
    and data that follows its schemas.

## Decision Outcome

`pytest` is LychD's primary test engine. Its fixtures, parametrization, and plugin ecosystem fit
the repository more directly than verbose `unittest` scaffolding or keyword-heavy BDD. Tests are
classified by the boundary they exercise; selection begins with the closest class and widens only
when the change crosses it.

### 1. The Engine (Pytest + Xdist)

The default suite is serial because some tests exercise shared host-resource boundaries; a caller
may opt into bounded `pytest-xdist` parallelism with an explicit worker count such as `N=8`.
`K="expression"` selects a pytest keyword expression, and `M="expression"` selects registered
markers. Ordinary runs capture logs and allocate a unique invocation directory beneath
`.cache/pytest` and use pytest's native compact report without an intervening output wrapper; an
explicit `PYTEST_BASETEMP` instead names a caller-owned path. `VERBOSE=1` streams stdout, long
tracebacks, and live DEBUG logs for diagnosis.

The layout is `tests/unit`, `tests/integration`, `tests/architecture`, and `tests/web`. Start at
the smallest relevant directory, then widen deliberately rather than turning each edit into an
unexplained whole-suite ritual.

### 2. The Taxonomy (Markers)

Registered markers use `pytest.mark` semantics:

- **unit**: isolated contracts.
- **integration**: layers, filesystems, databases, or substitutes; never an opaque live-host claim.
- **container**: explicit disposable-container receipts. The ordinary `make test`/`make check`
  gate excludes them; `make test-containers` selects them with the separate dependency group and
  requires a Docker-compatible daemon.
- **slow**: deliberately expensive work, such as heavy model loading.

Strict markers reject typos, but the repository currently selects most cost classes by directory:
`unit` and `slow` are not applied, and only a few integration tests carry `integration`. Therefore
`M=unit` collects nothing today; use `PYTEST_TARGETS` for reliable selection. Host or
external-system tests are opt-in and require a named receipt.

### 3. The Fabricator (Polyfactory)

Polyfactory constructs valid Pydantic models and plain types. A test may define an explicit local
factory when the fixture's meaning matters; fabrication is not test magic and does not hide the
contract being asserted.

### 4. The Quality Gate (Coverage)

`pytest-cov` measures branch coverage with the `pyproject.toml` 80% floor and deliberate
structural exclusions. `make coverage` enforces that floor, but default `make test`, `make check`,
pull-request checks, and release-candidate CI do not pass `--cov`; it is an opt-in gate, not a
release receipt. Coverage remains serial and preserves the ordinary suite's `not container`
selection. Pull-request and `main` checks run the ordinary suite and disposable PostgreSQL profile
in separate jobs, preserving their distinct evidence boundaries.

### 5. Runtime Surface Probes

Repository tests are evidence about the repository. A real systemd, Podman, PostgreSQL, GPU, or
model surface needs maintenance-operator receipts; State of Work owns the delivery interpretation.
Network and provider dependence stay out of deterministic tests unless a specifically classified
integration boundary needs them. Altar and GenUI probes may inspect rendered semantic contracts,
but distinguish `BLOCKED` from `FAIL`, preserve DOM or screenshot evidence where useful, and leave
server state authoritative.

## Consequences

A green suite does not prove a live host. Keep failures and their reproducing tests, choose marks
and reasons intentionally, and preserve deterministic seams rather than accidental provider or
network coupling. Exceptions to that discipline must state their boundary and receipt.
