# Contributing to LychD

Begin with one concrete change: a reader who cannot find the right page, a failing contract, or a
new capability with a named owner. Establish what the owning documentation promises, make the
change at that boundary, and leave enough evidence for the next contributor to understand it.

This guide takes you from a checkout to a reviewable contribution. [State of
Work](docs/state-of-the-work.md) tells you what current evidence supports; the
[Covenants](docs/adr/index.md) explain accepted decisions. Coding agents first load the routes in
[AGENTS.md](AGENTS.md).

## Find the part you want to change

If you are new to the codebase, follow one request through the [Map](docs/map.md). Then choose
the boundary your change crosses:

| Your change concerns… | Read first |
| --- | --- |
| Application startup, domain logic, or persistence | [Backend](docs/adr/11-backend.md), then its linked source and tests. |
| Run admission, execution, or recovery | [Workers](docs/adr/14-workers.md) and the relevant [Graph](docs/adr/24-graph.md) section. |
| Browser behavior or API projection | [Frontend](docs/adr/15-frontend.md), then the affected instrument in the [Altar source map](clients/web/src/README.md). |
| Documentation, vocabulary, or lore | [Documentation topology](docs/adr/01-doctrine.md#documentation-topology), then the owning page and its neighbors. |

You can start with that one boundary. Use the Covenant index for adjacent decisions as the change
reaches them; the full grimoire is not a prerequisite to a first contribution.

## Supported Environment

- Python is `>=3.12,<3.15`; `.python-version` pins 3.13 for repository and release checks. Use
  `uv` for dependencies and commands.
- Host operation targets a free and open-source Linux stack with systemd, cgroup v2, and rootless
  Podman/Quadlet. Most repository tests use isolated substitutes and do not prove that a real host
  works; [Summoning](docs/summoning.md) owns the live-host prerequisites and rite.
- Frontend work uses Node.js 24.20.0 (`.nvmrc`) and npm 12.0.2
  (`clients/web/package.json`): supported ranges are 24.20.x-or-newer within Node 24 and
  12.0.x-or-newer within npm 12, starting at 12.0.2. npm 12 keeps dependency lifecycle
  scripts blocked unless explicitly approved; the Linux Altar build requires no such approvals.

## Setup and Commands

Install only what the change needs:

```bash
make install
make frontend-install    # Frontend changes only
make help
```

`make install` creates or updates `.venv` from `uv.lock`, including the local
`postgres-binary` convenience extra. `make frontend-install` runs `npm ci` from the web-client lock.

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

Tests run serially by default so shared host-resource probes remain deterministic. Set an explicit
worker count such as `N=8` to opt into bounded parallelism, use `K="expression"` for pytest name
selection, and use `VERBOSE=1` for raw output, long tracebacks, and live DEBUG logs. Ordinary runs use
pytest's native compact report, capture logs, and allocate a unique scratch directory beneath
`.cache/pytest`; set `PYTEST_BASETEMP` to an explicit current-user-owned path only when a caller
must own that location.

Pull requests run four independent repository checks: the Python umbrella, the disposable
PostgreSQL receipts, the Altar check/build plus generated-diff guard, and a clean documentation
build. Pushes to `main` repeat the first three while the deployment workflow's clean documentation
build supplies the fourth gate and its Pages artifact. The tag/manual release-candidate workflow
remains a separate non-publishing artifact receipt.

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
make test PYTEST_TARGETS="tests/architecture" N=0
uv run --locked --only-group docs zensical build --clean
```

Check local file links and fragments, including links into a renamed heading. A moved page needs
its incoming links, parent index, compatibility anchors, and `zensical.toml` navigation updated
together. The architecture suite checks the delivery ledger and its evidence routes; the clean
build checks the published tree. `make docs` serves the Hexanomicon at `http://localhost:7778` for
local reading and layout inspection.

### Browser development and its backend

Frontend checks and the static build need the Python and Node dependencies above, but no running
Vessel, database, GPU, or model. Start there for a first frontend contribution.

`make frontend-dev` serves the source client at `http://127.0.0.1:5173`. It starts only Vite;
its `/api` and `/schema` requests currently proxy to `http://127.0.0.1:8000`. A separately prepared,
isolated backend or fixture must supply that address. Without it, the shell can load while API
reads fail. The repository does not currently supply a standalone hostless backend launcher for
this target.

An isolated backend using the application middleware must retain its local login and CSRF checks
and explicitly admit `http://127.0.0.1:5173` through `server.web.allowed_cors_origins`. A proxy does
not grant access or authorize effects. Do not put credentials in Vite configuration, rewrite the
browser's Origin, or point this preview at the installation used for Summoning. Browser acceptance
against a real host uses the compiled Altar at Litestar's own origin and follows
[Summoning](docs/summoning.md). Fixture previews and component tests remain separate evidence.

### Test Selection

Start with the closest test that can fail, then widen by boundary. For example:

```bash
make test PYTEST_TARGETS="tests/unit" K="expression"
make test PYTEST_TARGETS="tests/integration" M="integration"
make coverage
```

`K` selects test names; `M` selects registered markers. Most tests are classified by directory,
and the registered `unit` and `slow` markers are currently unapplied. `M=unit` therefore collects
nothing: use `PYTEST_TARGETS="tests/unit"`. `make coverage` is a separate serial branch-coverage
gate with the configured 80% floor; ordinary tests and CI do not enable coverage implicitly.

Choose the evidence boundary that matches the change:

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
  update both `clients/web/package.json` and `clients/web/package-lock.json`.
- **Frontend:** Follow **[ADR 15](docs/adr/15-frontend.md)**. The Altar is a Svelte 5/SvelteKit
  static SPA served by Litestar; do not add SvelteKit server routes, a JavaScript production
  server, or handwritten mirrors of generated OpenAPI transport contracts. Coding agents must
  also follow the [frontend scope](.agents/scopes/frontend.md) before touching `clients/web/**`.
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

## License

Contributions are accepted and distributed under **MPL-2.0**. There is no CLA or private
relicensing grant, and no `Signed-off-by` trailer is required. See [ADR 00](docs/adr/00-license.md)
for the contribution policy and [LICENSE](LICENSE) for the binding terms.
