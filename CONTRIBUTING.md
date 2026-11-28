# Contributing to LychD

Start with one concrete change and its owning contract. [State of Work](docs/state-of-the-work.md)
records delivery; the [Covenants](docs/adr/index.md) own architectural decisions. Coding agents
enter through [AGENTS.md](AGENTS.md).

## Find the part you want to change

Choose work from [#52](https://github.com/hexanomicon/lychd/issues/52). New to the codebase?
Follow one request through the [Overview](docs/map.md), then enter the affected boundary:

| Your change concerns… | Read first |
| --- | --- |
| Startup, domain logic, persistence | [Backend](docs/adr/11-backend.md); trace the [runtime actuator](src/lychd/system/services/runtime.py). |
| Run admission, execution, recovery | [Workers](docs/adr/14-workers.md) and [Graph](docs/adr/24-graph.md). |
| Agent steps, consent, delegated work | [Agents](docs/adr/20-agents.md), [HitL](docs/adr/25-hitl.md), and the [Bridge workflow](src/lychd/agents/workflows/bridge_chat.py). Check [delegation delivery](docs/state-of-the-work.md#delegated-agent-execution) before adding a runtime. |
| Browser behavior, API projection | [Frontend](docs/adr/15-frontend.md) and the [Altar source map](clients/web/src/README.md). |
| Extension configuration, typed contributions | [Extensions](docs/sepulcher/extensions/index.md), then the contribution guide for the thing being added. |
| Upstream code, tests, documentation, assets | [Reuse upstream material](#reuse-upstream-material). |
| Documentation, vocabulary, lore | [Documentation topology](docs/adr/01-doctrine.md#documentation-topology), then the owning page. |

Claim one contract, reproduce a failure, and use its source and focused tests. Changes to shared
API types, checkpoint identity or effect settlement need review from the adjacent owners.
[Select checks](#test-selection) for the affected boundary; read adjacent Covenants as needed.

## Branches and everyday collaboration

### Coordinate before starting work

Before substantial work, read relevant issues, assignees, recent coordination comments and linked
PRs. Record the repository, work items, observation time and access gaps. Branches are supporting
evidence, not proof that work is claimed, active or abandoned. An operator-assigned task may
proceed within its existing authority despite a visibility gap.

Announce the intended outcome and approximate area in the existing owning issue, or create a
concrete task issue. Name the responsible contributor, add an assignee when permitted, and set
**In progress** when implementation starts. Small fixes may state scope in the PR or commit
without a separate issue or prior discussion. External contributors need no private-board access. A claim grants neither exclusive ownership
of an area nor unlimited write authority.

Publish a linked draft PR when there is useful work to inspect. Update the issue/PR when scope,
responsibility or disposition changes, including pauses and abandonment; refresh coordination
before selecting another task or accepting a handoff. Exploration can establish the exact file
list, but a delegated writer needs a bounded input/effect contract before construction.
Agents follow the same procedure under their actual communication permissions; this rule does
not authorize posting or changing GitHub state.

### Current phase: team integration through dev

Ordinary task branches start from current `dev`; fork and team PRs target `dev`. `main` remains
the default branch and the deliberately verified public snapshot.

1. Keep each PR small and cohesive; link its issue with `Refs #N`.
2. Inspect the full diff, including generated code/tests. Obtain one approving review from
   another eligible contributor, resolve conversations and pass the required checks. Changed
   diffs invalidate stale approvals; automated review does not replace human responsibility.
3. The author may merge after those gates. Small fixes follow the same PR path.
4. Verify the combined `dev` result before [promotion](#promote-a-tested-snapshot).

The four required checks are **Core Python 3.14.8 (OCI test image)**,
**Core Python 3.15.0 (OCI test image)**, **Altar contracts and build**, and **Hexanomicon build**.
They run on PRs and pushes to both long-lived branches. Add affected-boundary checks; CI does
not establish live-host acceptance.

**Temporary founder exception, 4 November 2026:** `zenithruneblade` may push to `dev` and `main`
or merge without another contributor's approval until the operator revokes this named-account
exception. All four checks still apply. Record scope, exact source and verification; promotion
uses the exact tested `dev` commit. Other contributors retain the ordinary PR/review path.

Integrate independently verified, compatible slices frequently, preferably within the working day.
Keep unfinished disruptive work on short task branches. When `dev` breaks, fix or revert before
adding more changes; when review or CI capacity is full, finish waiting work before starting more.
Branch age grants no permission to merge. Preserve shared history: no force pushes or deletion
of `dev`/`main`. Disposable task PRs may be squashed into `dev`.

`@hexanomicon/core` has repository **Write** and a shared review target. Only
`@hexanomicon/release-maintainers` and repository administrators may update `main`; required
checks also apply to administrators. `main` permits checked direct promotion without a separate
PR. Repository Write alone grants no ordinary direct-main permission. Project access is separate:
`core` has **Write** on the private [delivery board](https://github.com/orgs/hexanomicon/projects/1).
External contributors use public issues and fork PRs without team or board membership.

### Agent-assisted campaigns

Follow [Development bootstrap](docs/sepulcher/aspects/weaver/development-bootstrap.md).
Pin the actual input closure, allowed paths and effects; reserve verification/reviewer capacity
and a separate candidate surface per writer. Include admitted dirty patches and selected untracked
inputs: a commit alone does not identify a dirty checkout. Preserve unrelated work.

Review returned bytes and attributed observations against the original acceptance criteria;
record reviewer exposure and conflicts. Platform sessions retain their actual identities and
permissions. Idle work stays within standing authority and stops when useful work, review capacity
or budget runs out. The bootstrap's pilot limits do not change approval or promotion rules.

### Promote a tested snapshot

Record the exact commit, checks and untested boundaries in the issue/PR. Wait for all four
required **push-to-dev** checks on that commit, including its earlier changes. A PR merge-preview
or manual run is insufficient. A release maintainer or administrator then fast-forwards `main`
to that tested `dev` commit; keep a working backup maintainer.

In a clean checkout, replace `FULL_TESTED_COMMIT_SHA` with the recorded commit:

```bash
git fetch origin &&
git merge-base --is-ancestor origin/main FULL_TESTED_COMMIT_SHA &&
git merge-base --is-ancestor FULL_TESTED_COMMIT_SHA origin/dev &&
git push origin FULL_TESTED_COMMIT_SHA:refs/heads/main
```

Stop on any failure. If history diverged, merge current `main` into `dev`, resolve, verify the new
candidate and retry. Merge direct-main fixes back into `dev`; ordinary fast-forward promotions
need no merge back. Avoid routine cherry-pick, squash or rebase promotion between these branches:
it changes ancestry and can create an untested combination. Keep `dev` during branch cleanup.
Publishing `main` updates the documentation site; it is not a package release.

Dependabot version updates target `dev`. For security PRs targeting default `main`, carry the fix
through a reviewed `dev` PR, verify and promote, then reconcile the original PR. Bots do not bypass
these gates. An urgent exception needs recorded scope and verification, followed by synchronization
back into `dev`.

### Issues and the board

| State | Meaning |
| --- | --- |
| In progress | Implementation is underway. |
| Review | Implementation, tests and docs need human review. |
| Testing | Acceptance is needed in the relevant environment, usually after `dev` integration; tests also run earlier. |
| Done | Full issue criteria are verified, changes are on `main`, and affected documentation is current. |

Small changes may go from Review to Done after acceptance and promotion. Partial PRs do not
complete parent issues. Closing keywords on `dev` PRs do not close issues while `main` is default;
use explicit references, then close completed issues after promotion. The promoting maintainer
updates issues/board or names who will. CI and a merged PR do not perform that acceptance.

## Grow into shared stewardship

Maintainer responsibility follows demonstrated contributions, compatibility work and review,
with an explicit scope independent of employment or founding status; there is no fixed-size inner
circle. Use Discord for working conversation, [Discussions](https://github.com/hexanomicon/lychd/discussions)
for lasting proposals/questions/showcases, and issues for concrete work. Small fixes need no prior
Discussion, and contributions need no Discord account. Record accepted decisions and evidence in
the owning docs, linked to their PR or commit.

Current authority comes from repository permissions and review. The future
[source roster](docs/adr/17-packaging.md#forge-neutral-source-trust) and
[Evolution roster](docs/adr/18-evolution.md#future-quorum-roster) do not grant participation-based
credentials or release authority.

## Supported Environment

- Python range: `>=3.12,<3.16`; repository tooling pins 3.15.0, production Vessel uses
  `python:3.14.8-slim-bookworm`. Core CI and manual Python/PostgreSQL checks cover both 3.14.8
  and 3.15.0 using `uv` 0.13.0. Core tests, lint, formatting and typing run only in the explicit
  `Containerfile.tests` OCI image.
- The primary host uses Linux with systemd, cgroup v2 and rootless Podman/Quadlet.
  Personal [native deployments on Linux, macOS and Windows](docs/deployments/desktop.md) have separate host receipts.
  [Summoning](docs/summoning.md) owns host prerequisites; isolated repository checks do not
  qualify a deployment.
- Web tooling pins Node.js 24.20.0 (`.nvmrc`) and npm 12.0.2 (`clients/web/package.json`).
  Supported ranges are Node 24.20.x or newer within 24 and npm 12.0.x or newer within 12,
  starting at 12.0.2. npm lifecycle scripts stay blocked unless explicitly approved;
  the Linux Altar build needs no approvals.
- [Android client setup and checks](clients/android/README.md) use JDK 17 and the pinned Gradle
  wrapper. JVM tests need no SDK; the opt-in app build needs the Android SDK, and instrumented
  tests need a selected device/emulator. These gates are separate from Python/web checks.

## Setup and Commands

Core verification requires a working OCI engine: rootless Podman by default, or explicitly
`LYCHD_TEST_ENGINE=docker`. The wrapper builds an allowlisted source image and runs its exact ID
without mounting the checkout or HOME. Missing engines/build failures stop the check; there is
no host fallback. Docker needs Buildx with `--resource` support (checked with 0.36.1) or an
explicitly selected classic builder; Podman uses native build limits.

Install host CLI or frontend tooling only when needed:

```bash
make install
make frontend-install    # Web work only
make help
```

`make install` updates `.venv` from `uv.lock`, including the `postgres-binary` convenience extra;
that is host tooling, not a Core test environment. `make frontend-install` uses locked `npm ci`.
`make init` materializes host layout: reserve it for [Summoning](docs/summoning.md) or deliberate
host-initialization tests.

### Quality Checks

```bash
make lint RUFF_TARGETS="src/lychd tests"
make format-check FORMAT_TARGETS="src/lychd tests"
make type-check TYPECHECK_TARGETS="src/lychd"
make test PYTEST_TARGETS="tests/unit"
make check
```

Omit target variables for repository-wide defaults. `make check` runs non-mutating Python
lint/format/type/tests; frontend checks are separate. `make format` changes files.
Select an interpreter with `LYCHD_TEST_PYTHON=3.14.8` or `3.15.0`.

PR/push Core CI runs lint, formatting, strict typing and `make test-ci`; [the Makefile](Makefile)
owns `CI_PYTEST_TARGETS`. This subset uses in-process substitutes and does not replace the full
ordinary `make test`/`make check` selection. Automatic Altar CI regenerates contracts, checks,
tests and builds the client, rejecting unexpected generated changes; Hexanomicon CI builds clean.
Both jobs always report without path filters. Manual Repository Checks additionally offers full
Python and disposable PostgreSQL jobs. Host-specific Quadlet/filesystem acceptance remains separate.
The tag/manual release-candidate workflow produces a non-publishing artifact receipt.

For web changes, run `make frontend-check` and `make frontend-build`. Both regenerate OpenAPI
through offline host tooling without starting Core; Node tests keep their separate boundary.
Review the generated static Altar under `src/lychd/public/` with the source change.

For docs, run the architecture suite through the OCI wrapper, then the clean build inside an
admitted OCI documentation environment:

```bash
make test PYTEST_TARGETS="tests/architecture" N=0
uv run --locked --only-group docs zensical build --clean
```

Run them sequentially: the clean build removes `.cache`, including repository test scratch.
Keep an explicit uv cache outside it. Check local links/fragments and update inbound links,
parent indexes and the owning `.nav.yml` when routes move. Zensical's built-in Awesome Nav reads
`docs/.nav.yml` and section-local lists relative to each file; new pages need explicit entries.
`zensical.toml` owns renderer/theme configuration; no extra navigation package is needed.
`make docs` serves local documentation on port 7778.

Specialized model, database, namespace and host proofs have different prerequisites and receipt
boundaries. Follow [qualification profiles](tests/README.md) for PostgreSQL, Intercom/Atlas,
Quadlet, embedding/semantic memory, Webcrawler/Scavenger and optional music probes. Historical
host-native receipts do not qualify the current image; [State of Work](docs/state-of-the-work.md#current-evidence-envelope)
owns their status. The ordinary wrapper does not forward arbitrary proof flags, files or sockets.

### Browser development and its backend

Frontend checks/build need Python/Node dependencies, not a running Vessel, database, GPU or model.
For an interactive preview, run `make developer-fixture` and `make frontend-dev` in separate
terminals. Defaults: fixture `http://127.0.0.1:8000`, Vite `http://127.0.0.1:5173`, forwarding
`/api` and `/schema`. Vite alone loads the shell; API reads require the fixture.

Each fixture start prints user `magus` and a fresh password. Its process-local memory contains
one labelled synthetic conversation and failed Run for Bridge, Orb and the exact Loom Pattern.
It reads no operator secrets/configuration and starts no database, worker, model or Host Reactor.
The failed Run represents no execution; all mutations are refused, even with valid credentials/CSRF.

`make developer-fixture CANVAS_AUTHORING=1` admits only Canvas and existing Project authoring
in that disposable memory. Authentication, Origin, CSRF and handler scopes stay active;
conversation admission, consent and physical transitions stay refused. Stopping loses edits.

For manual browser verification, use a dedicated local browser profile, authenticate at
`http://127.0.0.1:5173/api/v1/altar/status`, then open `/bridge` and follow its synthetic Run to Orb
and its exact Pattern in Loom. Check authentication across those reads. Commands/backend tests
alone do not qualify this journey; [State](docs/state-of-the-work.md#current-evidence-envelope)
records the current and retired browser evidence, including retained-reply rendering limits.

Preserve the browser Origin and normal Host/CORS/authentication/CSRF checks. Keep credentials out
of Vite config, URLs, environment and source. Use the disposable fixture separately from the
Summoning installation; real-host acceptance uses compiled Altar at Litestar's own origin.
This preview grants neither production macOS support nor Linux host qualification.

### Test Selection

Start with the nearest failing contract, then widen across affected boundaries:

| Change | Checks |
| --- | --- |
| Domain/utilities | Matching `tests/unit/` subtree. |
| Database/filesystem/services/cross-layer | Matching `tests/integration/` and affected unit tests. |
| Architecture/packaging/public contracts/docs topology | `tests/architecture/`. |
| Web contracts/projections | `tests/web/`; add frontend checks for OpenAPI/client changes. |
| Frontend | `make frontend-check` and `make frontend-build`. |

`PYTEST_TARGETS` selects paths, `K="expression"` test names. `M` replaces the default
`not container` marker expression; preserve that exclusion explicitly when needed. Most selection
uses directories: registered `unit` and `slow` markers are unapplied, so `M=unit` collects nothing.
Runs are serial by default; `N=8` opts into bounded parallelism. `VERBOSE=1` enables raw output,
long tracebacks and DEBUG logs; otherwise pytest captures logs and uses its compact report.

Scratch is unique under the disposable container's `.cache/pytest`; `PYTEST_BASETEMP` is also a
container path. Reports do not persist without an admitted export. Use ordinary task scratch
such as fresh `/tmp` paths, outside protected authority roots such as `~/.codex`.
Ordinary checks receive no network, added capabilities, daemon socket, live database, systemd,
model or GPU. [Special profiles](tests/README.md) explicitly admit their extra prerequisites.

`make coverage` separately enforces serial branch coverage with the configured 80% floor;
ordinary tests/CI do not enable coverage implicitly. Run full `make check` before review when
practical and report skipped live checks with their limits.

## Implementation Conventions

- **Python:** support the declared range, use PEP 695 generics and keep boot-hook imports lazy
  where startup order requires it.
- **Paths:** use `PATH_*` from `src/lychd/system/constants.py`, not hardcoded user paths.
- **Boundaries:** domain computes intent; system services own filesystem/process/systemd effects.
  Follow [Backend](docs/adr/11-backend.md).
- **Dependencies:** use `uv add`/`uv remove` with the right group; commit `pyproject.toml` and
  `uv.lock` together. Web changes pair `package.json` and `package-lock.json`.
- **Frontend:** follow [ADR 15](docs/adr/15-frontend.md): static Svelte 5/SvelteKit SPA served by
  Litestar, no SvelteKit server routes or JS production server, no handwritten OpenAPI mirrors.
  Agents load the [frontend scope](.agents/scopes/frontend.md).
- **Logging:** use `structlog`, stable event names and useful fatal initialization errors.
- **Documentation:** follow [ADR 01 topology](docs/adr/01-doctrine.md#documentation-topology).
  Establish vocabulary and boundaries in owning docs before implementation (xDDD); myth is
  constitutional telos, not delivery evidence. Update owners and stale routes/status with code.

## Reuse upstream material

Before copying, adapting or deriving a local mechanism from upstream material, follow
[Assimilation's reuse procedure](docs/sepulcher/aspects/weaver/assimilation.md#upstream-reuse-and-notices).
It covers exact provenance, applicable terms, changes and shipped notices, including agent-produced
ports, tests, docs and assets. Ordinary dependencies/integrations retain license and inventory
duties without automatically requiring an Assimilation Dossier. [ADR 00](docs/adr/00-license.md#receiving-third-party-material)
owns the legal boundary; [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) records incorporations.
README Tribute remains curated gratitude.

## Change and Review Discipline

Keep one reviewable intent, its tests, generated artifacts and required docs together. Inspect the
complete diff and third-party notices; exclude unrelated cleanup. Review against owning source,
tests, ADRs and State rather than repeated summaries.

For a changed capability, contract, procedure or context route, verify discovery from a realistic
question through maintained entrypoints without supplying the destination. Record the question,
entrypoint, observed route to owner/evidence, result, repairs and gaps; test a neighboring task when
changing a shared route. Agents follow [context-loading verification](.agents/workflows/context-loading.md).
Link checks alone do not establish discoverability.

The PR description states the changed behavior/boundary, checks and results, unrun live/external
checks, and affected docs/generated contracts/delivery claims.

## License

Contributions are inbound/outbound **MPL-2.0**, preserving applicable third-party terms. There is
no CLA, private relicensing grant or required `Signed-off-by` trailer. [ADR 00](docs/adr/00-license.md)
owns the policy; [LICENSE](LICENSE) supplies the binding terms.
