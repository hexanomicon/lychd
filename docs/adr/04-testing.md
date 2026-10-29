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

All Core test, lint, format-check, type and coverage processes run in the explicit OCI image
built from `Containerfile.tests`, selected through the Makefile and `scripts/container_checks.sh`.
The host harness may build and launch that image; it does not execute a host Vessel or fall back
to host pytest when the engine is unavailable. Application construction and ASGI/domain helpers
inside the image are test techniques, not another deployment profile. Installed-runtime
qualification instead needs the actual rebuilt production Vessel image and declared boundary.

Some probes share host-resource boundaries, so tests run serially by default. Callers may select
bounded `pytest-xdist` parallelism. An ordinary invocation gets unique scratch under the
disposable container's `.cache/pytest`, captured logs, and pytest's native compact report without
an output wrapper. Caller-owned scratch and verbose diagnostics require explicit choices;
[CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#test-selection)
owns the exact switches.

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

By default, `make test` and `make check` exclude `container`. An explicit marker expression
replaces that exclusion. `make test-containers` admits that profile with its separate dependencies
and an explicitly admitted Docker daemon socket through the Docker-only PostgreSQL harness. Ordinary checks receive no daemon
socket or network; this separate PostgreSQL harness has its own declared socket/network authority. Host and external
systems stay opt-in and need named receipts. Network and provider dependence enter a deterministic
test only when its declared integration boundary requires them.

### 3. The Fabricator (Polyfactory)

Generated fixture data must remain valid under the actual schema; a factory helps construct it.
The test still needs to show which property matters and satisfy any validator prerequisites.
Keeping those responsibilities visible lets a contributor distinguish a failed fabrication from
failed system behavior.

### 4. The Quality Gate (Coverage)

`pytest-cov` measures branch coverage against the `pyproject.toml` **80%** floor and deliberate
structural exclusions. `make coverage` enforces it serially with the ordinary `not container`
selection. Default tests, the Python umbrella, pull-request checks, and release-candidate CI do
not pass `--cov`. Coverage is an opt-in gate, not an implicitly passed release condition.

Pull-request, `dev` and `main` Core Python CI runs the explicit `make test-ci` selection, using
in-process substitutes inside that OCI image, without a model or daemon socket in the test
process. The outer build/launch still requires a working OCI engine. Full ordinary tests and
disposable PostgreSQL receipts remain separate jobs in the manually dispatched Repository Checks
workflow. A core-CI pass does not establish those broader results or waive affected-boundary
verification. The normal `make test` and `make check` selections remain unchanged.

### 5. Runtime Surface Probes

A repository test establishes its recorded conjunction. Real systemd, Podman, PostgreSQL, GPU,
model, and browser behavior requires the corresponding maintained operator receipt; mocks do not
inherit the authority of the systems they replace. [State of Work](../state-of-the-work.md)
records that distinction. Host-native Core deployments and their test fixtures are retired;
frozen native-profile receipts retain only their dated historical scope and cannot qualify the
current test image or a rebuilt production image.

Altar and GenUI probes may inspect rendered semantic contracts and preserve DOM or screenshot
evidence. A missing prerequisite is `BLOCKED`, not a fabricated behavioral `FAIL`. Server state
remains authoritative, and a rendered success message must not substitute for the effect record.

## Consequences

Keep a failure together with the test that reproduces it. Select directories, marks, and opt-in
boundaries to match the claim, widening the checks when a change crosses those boundaries. An
exception needs its own stated scope and receipt. This gives contributors both a suite they can
reason about and an exact account of what still needs to be witnessed on real iron.