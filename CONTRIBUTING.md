# Contributing to LychD

Coding agents begin at **[AGENTS.md](AGENTS.md)**. This page owns the maintained development
environment, commands, and contribution conventions; [State of Work](docs/state-of-the-work.md)
owns claims about present delivery.

## License

Contributions are accepted and distributed under **MPL-2.0**. There is no CLA or private
relicensing grant, and no `Signed-off-by` trailer is required. See
**[ADR 00](docs/adr/00-license.md)** for the contribution policy and [LICENSE](LICENSE) for the
binding terms.

## Supported Environment

- Python is `>=3.12,<3.15`; `.python-version` pins 3.13 for repository and release checks. Use
  `uv` for dependencies and commands.
- Host operation targets a free and open-source Linux stack with systemd, cgroup v2, and rootless
  Podman/Quadlet. Most repository tests use isolated substitutes and do not prove that a real host
  works; [Summoning](docs/summoning.md) owns the live-host prerequisites and rite.
- Frontend work uses Node.js 24.18.0 (`.nvmrc`) and npm 11.16.0
  (`frontend/package.json`): supported ranges are 24.18.x-or-newer within Node 24 and
  11.16.x-or-newer within npm 11.

## Setup and Commands

Install only what the change needs:

```bash
make install
make frontend-install    # Frontend changes only
make help
```

`make install` creates or updates `.venv` from `uv.lock`, including the local
`postgres-binary` convenience extra. `make frontend-install` runs `npm ci` from the frontend lock.

`make init` materializes local host layout; it is not a development bootstrap. Use it only for
[Summoning](docs/summoning.md) or deliberate host-initialization testing.

### Quality Checks

```bash
make lint RUFF_TARGETS="src/lychd tests"
make format-check FORMAT_TARGETS="src/lychd tests"
make type-check TYPECHECK_TARGETS="src/lychd"
make test PYTEST_TARGETS="tests/unit"
make check
```

Omit a target variable for the repository-wide default. `make check` runs the complete
non-mutating Python lint, format, type, and test suite—not frontend checks. Use `make format` only
when you intend to change files.

Tests run in parallel by default. Use `N=0` for serial execution, `K="expression"` for pytest
name selection, and `VERBOSE=1` for raw output and long tracebacks. Pytest scratch data defaults to
`.cache/pytest`; set `PYTEST_BASETEMP` to another current-user-owned directory when isolation
requires it.

Disposable PostgreSQL receipts are an explicit host-integration profile, not part of ordinary
`make check`:

```bash
make test-containers
```

That target installs the separate `container-test` dependency group, requires a working
Docker-compatible daemon, and may pull the pinned `pgvector` image. Ryuk remains unprivileged by
default. A rootless compatibility environment may deliberately opt in with
`TESTCONTAINERS_RYUK_PRIVILEGED=true make test-containers`; do not export that setting as a normal
repository default.

For frontend changes, run:

```bash
make frontend-check
make frontend-build
```

Both regenerate the Litestar OpenAPI contract. The build updates the tracked static Altar in
`src/lychd/public/`; review and commit it with its source change.

For documentation changes, run:

```bash
uv run zensical build --clean
```

`make docs` serves the Hexanomicon at `http://localhost:7778` for local inspection.

### Test Selection

Start with the closest test that can fail, then widen by boundary:

- Pure domain or utility changes: the matching `tests/unit/` subtree.
- Database, filesystem, service wiring, or cross-layer changes: matching `tests/integration/`
  tests plus affected unit tests.
- Architecture, packaging, public contracts, or documentation topology: `tests/architecture/`.
- Web contracts or projections: matching `tests/web/` tests; add `make frontend-check` when the
  OpenAPI contract or client changes.
- Frontend source: `make frontend-check` and `make frontend-build`.

Run `make check` before review when practical. Report skipped host checks: tests, generated plans,
and mocks are not live systemd, Podman, PostgreSQL, GPU, or model-engine receipts.

## Implementation Conventions

- **Python:** Support the declared range, use PEP 695 generics, and keep boot-hook imports lazy
  where startup order requires it.
- **Paths:** Do not hardcode user paths such as `~/.config/...`. Use the `PATH_*` authorities in
  `src/lychd/system/constants.py`.
- **Boundaries:** Domain computes intent without host mutation; system services own filesystem,
  process, systemd, and other effects. Backend route/repository law is in
  **[ADR 11](docs/adr/11-backend.md)**.
- **Dependencies:** Use `uv add` or `uv remove` with the correct dependency group and commit the
  resulting `pyproject.toml` and `uv.lock` changes together. Frontend dependencies must likewise
  update both `frontend/package.json` and `frontend/package-lock.json`.
- **Frontend:** Follow **[ADR 15](docs/adr/15-frontend.md)**. The Altar is a Svelte 5/SvelteKit
  static SPA served by Litestar; do not add SvelteKit server routes, a JavaScript production
  server, or handwritten mirrors of generated OpenAPI transport contracts. Coding agents must
  also follow the [frontend scope](.agents/scopes/frontend.md) before touching `frontend/**`.
- **Logging:** Use `structlog` with stable semantic event names. Make fatal initialization errors
  useful; shared configuration captures exceptions and tracebacks.
- **Documentation:** Follow
  **[ADR 01 §Documentation Topology](docs/adr/01-doctrine.md#documentation-topology)**. Root files
  are thin entry doors; ADRs own accepted decisions, the lexicon owns canonical terms,
  compositions own native reference application contracts, worked examples, and their local
  current-material statement, while State of Work owns the shared whole-system evidence envelope.
  xDDD establishes vocabulary and boundaries in the owning documentation before
  implementation. Myth is constitutional telos, not evidence that a feature ships. If code changes
  system truth, update its owning documentation and routing links in the same change.

## Change and Review Discipline

Keep each contribution cohesive: one reviewable intent, its tests, generated artifacts, and
documentation made necessary by changed truth. Do not mix unrelated cleanup into behavior work.
Inspect the complete diff and retain third-party notices when dependencies or adapted source change.

A review description should state:

1. what behavior or boundary changed;
2. which checks ran and their results;
3. which live-host or external checks did not run;
4. which documentation, generated contracts, or delivery claims changed.

Review against the owning source, test, ADR, and State of Work entry rather than against prose
elsewhere that merely repeats them.
