---
title: 4. Testing
icon: material/shield-check-outline
---

# :material-shield-check-outline: 4. Testing

A test is useful when it can fail for a reason the contributor understands. Its setup, assertion,
and execution boundary should make that reason recoverable. LychD chooses ordinary typed fixtures
and explicit evidence classes over a second language for describing behavior.

## Decision Outcome

**pytest** is the primary engine. Its fixtures and parametrization fit the repository more directly
than verbose `unittest` scaffolding or keyword-heavy BDD. **Polyfactory** builds valid Pydantic
models and plain types where fabrication helps; an explicit local factory remains appropriate
when the fixture's meaning is part of the assertion.

### 1. The Engine (Pytest + Xdist)

Tests run serially by default because some probes share host-resource boundaries. A caller may
select bounded `pytest-xdist` parallelism. Each ordinary invocation receives unique scratch under
`.cache/pytest`, captured logs, and pytest's native compact report without an output wrapper.
Caller-owned scratch and verbose diagnostics remain explicit choices. The exact switches belong
in [CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#test-selection).

Start with the smallest relevant source boundary. The directory layout makes that selection
visible:

| Directory | Evidence sought |
| --- | --- |
| `tests/unit` | Isolated domain, utility, and adapter contracts. |
| `tests/integration` | The named cross-layer, filesystem, database, or substitute conjunction. |
| `tests/architecture` | Package boundaries, release declarations, public contracts, and documentation topology. |
| `tests/web` | HTTP and browser-projection contracts at their declared server boundary. |

### 2. The Taxonomy (Markers)

Markers use strict `pytest.mark` semantics: `unit` names isolated contracts, `integration` names
joined layers, `container` selects explicit disposable-container receipts, and `slow` marks
expensive work such as heavy model loading. Strictness catches misspelled markers; it does not
populate them. Most present selection follows directories: `unit` and `slow` are unapplied, and
only a few integration tests carry `integration`. Consequently `M=unit` collects nothing today;
select the directory instead.

Ordinary `make test` and `make check` exclude `container`. `make test-containers` admits that
profile with its separate dependencies and a working Docker-compatible daemon. Host and external
systems stay opt-in and need named receipts. Network and provider dependence enter a deterministic
test only when its declared integration boundary requires them.

### 3. The Fabricator (Polyfactory)

Generated fixture data must remain valid under the actual schema. Factories help construct it;
they do not explain which property matters or conceal a validator prerequisite. A failing
fabrication and a failing system behavior are distinct diagnoses.

### 4. The Quality Gate (Coverage)

`pytest-cov` measures branch coverage against the `pyproject.toml` **80%** floor and deliberate
structural exclusions. `make coverage` enforces it serially with the ordinary `not container`
selection. Default tests, the Python umbrella, pull-request checks, and release-candidate CI do
not pass `--cov`. Coverage is an opt-in gate, not an implicitly passed release condition.

Pull-request and `main` workflows run ordinary tests and disposable PostgreSQL receipts in
separate jobs. Their results remain separate even when both are green.

### 5. Runtime Surface Probes

A repository test establishes its recorded conjunction. Real systemd, Podman, PostgreSQL, GPU,
model, and browser behavior requires the corresponding maintained operator receipt; mocks do not
inherit the authority of the systems they replace. [State of Work](../state-of-the-work.md)
records that distinction.

Altar and GenUI probes may inspect rendered semantic contracts and preserve DOM or screenshot
evidence. A missing prerequisite is `BLOCKED`, not a fabricated behavioral `FAIL`. Server state
remains authoritative, and a rendered success message must not substitute for the effect record.

## Consequences

Retain failures with their reproducing tests. Choose directories, marks, and opt-in boundaries for
the claim being made, then widen when a change crosses those boundaries. Any exception needs its
own stated scope and receipt. The result is a suite a contributor can reason about, and a clear
account of what still needs to be witnessed on real iron.
