---
title: 3. Quality
icon: material/check-all
---

# :material-check-all: 3. Quality

!!! abstract "Context and Problem Statement"
    Quality is legible when every contributor can run the same small, deterministic gates. LychD
    needs correctness, style, static contracts, repeatable dependencies, and release-client checks
    without accumulating overlapping toolchains or treating a passing local command as host proof.

## Decision Outcome

LychD uses `uv` to resolve, lock, and run Python tooling; Ruff for linting and formatting; and
BasedPyright in strict mode for `src/lychd`. `pytest` is the test engine specified by
[ADR 04](04-testing.md). The repository's `Makefile` is the shared command grammar.

The older Poetry + mypy + Flake8 + Black/isort stack remains a credible mature alternative, but it
duplicates installation, configuration, and lint/format responsibility. The selected stack keeps
those responsibilities explicit with fewer moving parts.

### The Python Pillars

- `uv` owns resolution, the committed lockfile, and tool execution.
- Ruff owns linting and formatting, configured in `pyproject.toml`.
- BasedPyright checks `src/lychd` under its strict configuration.
- `pytest` supplies regression evidence; its taxonomy and runtime limits belong to ADR 04.

`uv.lock` is the repository-managed environment's source of truth; project dependencies are not
managed with direct `pip` use. Ruff exceptions are deliberate, documented configuration rather
than reviewer folklore, and the same configured BasedPyright implementation serves local and CI
checks.

### Cross-stack gates

The normal Python gates are non-mutating except the deliberate formatter command:

```sh
make lint RUFF_TARGETS="src/lychd tests"
make format-check FORMAT_TARGETS="src/lychd tests"
make type-check TYPECHECK_TARGETS="src/lychd"
make test PYTEST_TARGETS="tests/unit"
make check
```

`make check` is the non-mutating Python umbrella; it does not silently run frontend work. The
frontend has its own Node/npm boundary:

```sh
make frontend-check
make frontend-build
```

Both frontend gates regenerate OpenAPI and build the client. Resulting updates beneath
`src/lychd/public/` are tracked so review can see the generated projection. Published
documentation is checked separately with `uv run zensical build --clean`; this ADR does not claim
that command runs automatically.

The editor configuration also routes Markdown through `markdownlint` and TOML, YAML, and JSON
through Prettier. The client uses strict TypeScript, `svelte-check`, and Vitest/jsdom; native CSS
is inspected directly. A production-factory browser receipt remains outside these gates and is
owned by ADR 15 and State of Work.

## Consequences

Tool or configuration changes carry their lockfile and documentation consequences. Gates fail
early and reproducibly, but a green gate is repository evidence, not evidence that a deployed host
is healthy. Source, tests, locks, generated projections, and operational receipts retain their
separate owners; delivery status belongs to State of Work.
