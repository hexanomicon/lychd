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
| Agent steps, consent continuation, or delegated work | [Agents](docs/adr/20-agents.md), then [HitL](docs/adr/25-hitl.md) or [Graph](docs/adr/24-graph.md). |
| Browser behavior or API projection | [Frontend](docs/adr/15-frontend.md), then the affected instrument in the [Altar source map](clients/web/src/README.md). |
| Extension configuration or typed contributions | [Extension authoring](docs/sepulcher/extensions/authoring.md), then its linked Phoenix source and isolated tests. |
| Documentation, vocabulary, or lore | [Documentation topology](docs/adr/01-doctrine.md#documentation-topology), then the owning page and its neighbors. |

You can start with that one boundary. Use the Covenant index for adjacent decisions as the change
reaches them; the full grimoire is not a prerequisite to a first contribution.

### Start with three development lanes

Use these entry points to divide work around the same system contracts:

| Lane | Trace one contract | First verification |
| --- | --- | --- |
| Agentic | [Bridge workflow](src/lychd/agents/workflows/bridge_chat.py): model result → consent → completed history. Read [delegation status](docs/state-of-the-work.md#delegated-agent-execution) before adding an external runtime. | `make test PYTEST_TARGETS="tests/agents tests/unit/domain/delegation tests/unit/domain/cortex/test_delegate_resume.py"` |
| Fullstack | [Altar source map](clients/web/src/README.md): generated API contract → retained evidence → accessible instrument. | `make frontend-check` and the affected `tests/web` slice; then `make frontend-build`. |
| Backend | [Runtime actuator](src/lychd/system/services/runtime.py): observation → effect → settlement → reopened admission or containment. | `make test PYTEST_TARGETS="tests/unit/system/services/test_runtime.py tests/unit/domain/orchestration"` |

Claim one contract in an issue before changing it. Changes to shared API types, checkpoint identity,
or effect settlement need review from the adjacent lane; keep their source, tests and generated
artifacts together. A first contribution should reproduce one failure and close it through the
existing owner. The [quality gates](#quality-checks) distinguish repository evidence from live-host
acceptance; the [delivery ledger](docs/state-of-the-work.md) keeps the remaining boundaries.

## Branches and everyday collaboration

**Send ordinary pull requests to `dev`, including contributions from forks.** `main` stays the
default branch and the source of published documentation; it records the last deliberately
verified snapshot. `dev` is the shared integration branch.

1. For substantial work, agree a small slice in an issue and claim it. For small fixes, describe
   the change in the PR or commit. Branch from current `dev`.
2. Open a draft PR to `dev` when work would benefit from visibility or discussion. Link the issue
   with `Refs #N`; describe the result and checks in the PR template.
3. Read your complete change, including AI-generated code and tests. Request another reviewer
   when the change needs their expertise. Maintainers may merge their own ready PRs; small fixes
   may go directly to `dev`. No mandatory approval count or branch protection is configured.
4. Check the combined result on `dev`. Core Python CI runs on PRs and pushes to both long-lived
   branches; run the additional checks appropriate to the feature before promotion.

Keep task branches short and leave disruptive unfinished work there. When shared `dev` breaks,
fix or revert the regression before piling on more changes. Preserve shared history: fix forward
or revert instead of resetting or force-pushing `dev` or `main`. Squashing a disposable task PR
into `dev` is fine; preserve ancestry when moving work between `dev` and `main`.

The `@hexanomicon/core` team has repository **Write** access and a shared review/mention target.
Its membership grows through agreed responsibility; paid and independent contributors can become
maintainers. Write applies to the repository, including unprotected `main`, so this branch policy
is a working agreement. Project access is granted separately; `core` has **Write** on the private
[delivery board](https://github.com/orgs/hexanomicon/projects/1). External contributors use public
issues and fork PRs without joining the team or needing board access.

### Agent-assisted campaigns

Use [Development bootstrap](docs/sepulcher/extensions/weaver/development-bootstrap.md) for a
bounded operator campaign and its later native handoffs. Claim a concrete contract, pin the
actual input closure and allowed paths, reserve verification/reviewer capacity, and give each
writer a separate candidate surface. A dirty checkout needs an explicit admitted patch and
selected untracked inputs; a commit alone does not identify it. Preserve unrelated operator work.

Agents return candidate bytes and attributed observations. Inspect the complete diff and verify
the integrated object against the original acceptance criteria; independent review records its
exposure and conflicts. Platform sessions use their actual identities and permissions, without
claiming LychD containment. Idle work selects only eligible tasks under current standing authority
and stops when review capacity, useful work or its budget is exhausted. The guide's pilot limits
do not impose a new approval count or change the branch/promotion policy below.

### Promote a tested snapshot

Record the exact candidate commit, checks and relevant untested boundaries in the linked issue or
PR; small direct fixes may use the commit's CI record and an accompanying note. A candidate
includes all of its earlier changes. Verify that it belongs to `dev`, then advance
`main` to that exact commit with a **fast-forward** (preserving history). Any maintainer may do this
under the agreed scope; it does not require a founder-only approval queue.

In a clean checkout, replace `FULL_TESTED_COMMIT_SHA` with the recorded commit:

```bash
git fetch origin &&
git merge-base --is-ancestor origin/main FULL_TESTED_COMMIT_SHA &&
git merge-base --is-ancestor FULL_TESTED_COMMIT_SHA origin/dev &&
git push origin FULL_TESTED_COMMIT_SHA:refs/heads/main
```

Stop if any command fails. If `main` and the candidate have diverged, merge current `main` into
`dev`, resolve and verify the resulting candidate, then retry. A direct fix to `main` must also be
merged back into `dev`. Ordinary fast-forward promotions need no merge back. Avoid routine
cherry-picking or squash/rebase promotion between the long-lived branches: that creates a
different history and may create an untested combination. Keep `dev` when cleaning up merged
branches. Main publication updates the documentation site; it is not a package release.

### Issues and the board

- **In progress:** implementation is underway. **Review:** the implementation, tests and docs
  need human reading and challenge; request additional eyes where useful.
- **Testing:** the feature needs acceptance in the relevant environment, usually after
  integration into `dev`. Tests also run earlier. Small changes can pass directly from Review to
  Done when acceptance and promotion are complete.
- **Done:** the full issue criteria are verified, required changes are on `main`, and affected
  documentation is current. A partial PR does not complete its parent issue.

Closing keywords in a PR targeting `dev` do not close its issue while `main` is the default.
Use explicit issue references during development, then close completed issues and set Done after
promotion. The promoting maintainer updates those issues and the board, or names who will.
Review, acceptance and promotion are recorded manually; a green CI run or merged PR
does not close an issue on its own.

## Grow into shared stewardship

Core and extension developers share a path into maintainership: contribute useful work, preserve
compatibility, review changes, and discuss concerns with the community. The shared Discord is a
place for that ongoing conversation; record accepted decisions and their evidence in the
repository so others can follow and challenge them. Contributions remain welcome through GitHub
without a Discord account.

Maintainer responsibility follows demonstrated work and an explicit scope, independently of
employment or founding status. There is no fixed-size inner circle to join. The future
[source roster](docs/adr/17-packaging.md#forge-neutral-source-trust) and
[Evolution promotion roster](docs/adr/18-evolution.md#future-quorum-roster) describe individual
credentials and collective decisions for keeping a shared canon. Those protocols remain Designed;
today, maintainers use explicit repository permissions and human review. Community participation
does not itself issue credentials or authorize a release.

## Supported Environment

- Python supports `>=3.12,<3.16`; `.python-version` pins 3.15.0 for repository, release,
  documentation, and Altar tooling. Use `uv` 0.13.0 for dependencies and commands.
- The Vessel uses the stable `python:3.14.8-slim-bookworm` base. Core Python CI selects both
  3.14.8 and 3.15.0; the manual Python and PostgreSQL jobs use the same two versions. These
  configured lanes keep the repository and Vessel interpreters under explicit checks; passing
  portable tests does not qualify a Linux image or database deployment.
- Host operation targets a free and open-source Linux stack with systemd, cgroup v2, and rootless
  Podman/Quadlet. Most repository tests use isolated substitutes and do not prove that a real host
  works; [Summoning](docs/summoning.md) owns the live-host prerequisites and rite.
- Frontend work uses Node.js 24.20.0 (`.nvmrc`) and npm 12.0.2
  (`clients/web/package.json`): supported ranges are 24.20.x-or-newer within Node 24 and
  12.0.x-or-newer within npm 12, starting at 12.0.2. npm 12 keeps dependency lifecycle
  scripts blocked unless explicitly approved; the Linux Altar build requires no such approvals.
- Android client setup and focused checks are in [the client README](clients/android/README.md).
  Its Gradle gates are separate from the Python and web-client commands below.

Companion client checks use JDK 17 and a pinned Gradle wrapper. The Kotlin/JVM interaction tests
need no Android SDK. Building the opt-in Android application requires the SDK; its instrumented
tests also require a selected device or emulator. The [Android client README](clients/android/README.md)
owns those commands and their evidence boundaries.

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
must own that location. Use an ordinary test-data path such as a fresh `/tmp` directory, outside
protected authority roots such as `~/.codex`; mount-authority tests deliberately reject those roots.

Pull requests and pushes to `dev` and `main` run **Core Python CI**: repository lint, formatting and strict
typing, followed by `make test-ci`. This explicit selection covers configuration, database model
contracts, release archive checks, native server admission, operator control, failed or masked unit
deletion previews, credential and contributed-secret checks, init binding-site refusal,
animation/dispatch/orchestration, core Run and delegated-job logic, extensions, agents and web contracts,
Scout destination/parser/supervisor contracts and qualification-receipt freshness,
plus configuration, extension contribution, reconstructed Bridge resume, and the inactive Blockworld
placement workflow.
It uses in-process substitutes, requires no container daemon, running database, systemd service,
model or GPU, and does not prove host operation.
`CI_PYTEST_TARGETS` in the Makefile owns the exact selection. Reproduce it locally with:

```bash
make lint format-check type-check
make test-ci
```

The **Repository Checks** workflow remains manually dispatched: full `make check`, disposable
PostgreSQL, Altar check/build with the generated-diff guard, and a clean documentation build.
Host-dependent Quadlet/filesystem differences on GitHub runners remain unresolved; a core-CI
pass does not waive these broader checks for a change that needs them. The Pages workflow builds
documentation on `main`; the tag/manual release-candidate workflow remains a separate
non-publishing artifact receipt. `make test` and `make check` retain their full non-container
selection; `make test-ci` does not replace them for final verification.

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

The separate opt-in [warm-model Bridge proof](docs/sepulcher/animator/soulstone/engines/vllm.md#join-one-reply-to-durable-bridge)
joins streaming inference, SAQ, PostgreSQL and retained history across two application boots.
Its separate Linux process-restart selection uses two sequential spawn children. Both need an
explicit external loopback profile and never start the model; the page owns bounded commands
and receipt requirements.

Real private-manager tests require a fresh task-owned delegated user service. A private bus and
HOME alone do not isolate cgroups: another manager could migrate unrelated processes from its
inherited cgroup. The harness verifies the exact transient unit, delegation, ancestry, writable
cgroup and exclusive task processes before launching; it never falls back to the installed
manager. Ordinary unavailable environments skip; an explicitly required proof fails.

The separate native stop proof runs three ordered cases: required-close failure, clean closure,
then reference-connection loss after clean exit capture. It uses the actual generated native
command with an explicit inert application factory. It exercises signed HTTP admission and
Vessel-first dependency retention; it does not qualify a deployed model body.
Run from the checkout with a fresh external basetemp:

```bash
proof_unit="lychd-proof-native-$$.service"
systemd-run --user --unit="$proof_unit" --collect --wait --pipe --service-type=exec \
  --property=Delegate=yes --property=TasksMax=128 --property=RuntimeMaxSec=150 \
  --property=TimeoutStopSec=10 --property="WorkingDirectory=$PWD" \
  --setenv="LYCHD_SYSTEMD_PROOF_OUTER_UNIT=$proof_unit" --setenv=LYCHD_REQUIRE_SYSTEMD_PROOF=1 \
  /usr/bin/make test N=0 PYTEST_TARGETS=tests/integration/test_native_stop_systemd.py \
  PYTEST_BASETEMP=/tmp/lychd-native-stop-proof
```

Inspect all three case receipts and cleanup beneath basetemp. Confirm the exact outer unit is collected
and its cgroup is absent or empty. Requested CPU or memory properties do not establish effective
limits; inspect the actual cgroup files when those limits are required.

The separate Linux target-switch proof requires the installed Quadlet generator, an ordinary
rootless Podman cache containing the exact Python image pinned in its test, and a responding user
session bus. It exports that image without network access, then uses a private image store and
user manager. Read the test's resource and cleanup contract before opting in:

```bash
proof_unit="lychd-proof-quadlet-$$.service"
systemd-run --user --unit="$proof_unit" --collect --wait --pipe --service-type=exec \
  --property=Delegate=yes --property=RuntimeMaxSec=1000 --property=TimeoutStopSec=30 \
  --property="WorkingDirectory=$PWD" --setenv="LYCHD_SYSTEMD_PROOF_OUTER_UNIT=$proof_unit" \
  --setenv=LYCHD_REQUIRE_QUADLET_PROOF=1 /usr/bin/make test M=container N=0 \
  PYTEST_TARGETS=tests/integration/test_systemd_quadlet_transaction.py \
  PYTEST_BASETEMP=/tmp/lychd-quadlet-proof
```

Choose a fresh, short `PYTEST_BASETEMP` path. The proof needs up to 1 GiB of temporary storage
(monitored, not quota-enforced), retains its receipt there, and refuses missing prerequisites when
explicitly required. It does not start production units, load a model or qualify the full
Orchestrator/Host Reactor path. Without the opt-in flag, the live case skips.

The separate embedding transport proof requires Linux, a working ordinary rootless Podman
cache with the exact image pinned by the tracked public embedding fixture, and the already
available public Qwen3-Embedding-0.6B Q8_0 file. It verifies the file size and SHA-256 before
Podman access; it never downloads, copies, relabels or modifies the model file. Keep that file
quiescent throughout the run. On SELinux hosts, prepare a dedicated public fixture with a
container-readable shared context (`container_file_t:s0`); a private MCS label left by another
container is insufficient. The test neither disables SELinux nor relabels the supplied file.

```bash
LYCHD_REQUIRE_EMBEDDING_PROOF=1 LYCHD_EMBEDDING_FIXTURE=/absolute/path/Qwen3-Embedding-0.6B-Q8_0.gguf make test M=container N=0 PYTEST_TARGETS=tests/integration/test_llamacpp_embedding_runtime.py PYTEST_BASETEMP=/tmp/lychd-embedding-proof
```

Choose a fresh basetemp path. Without the flag, the live case skips before artifact or engine
access; with it, missing prerequisites fail. The proof creates one uniquely owned disposable
container with no network, host ports or GPU, then enters only its network namespace to exercise
the actual registry, Dispatcher and HTTPX embedding driver. The server has a CPU limit of 60 seconds and
an address-space limit of 4 GiB, the child 30 seconds/2 GiB, and bounded output. These
are process limits, not cgroup quotas. Work is bounded to 175 seconds and cleanup has 30 seconds;
artifact hashing is outside that work clock. Inspect `embedding-runtime/receipt.json` beneath
the test's basetemp directory for both proof and cleanup success. This qualifies transport
against an externally started runtime; it does not prove Orchestrator activation or Archive
semantic recall. The ordinary image cache and its shared helper lifetime remain operator-owned.

Scout's separate Linux x86-64 extraction proof requires an already installed Bubblewrap and a
reviewed dedicated CPython installation. Outside the checkout, prepare a JSON profile with
absolute `bwrap` and `python_root` paths plus a `libraries` array containing the individual
`ld-linux-x86-64.so.2`, `libc.so.6`, `libdl.so.2`, `libgcc_s.so.1`, `libm.so.6`,
`libpthread.so.0`, `librt.so.1` and `libutil.so.1` paths. The interpreter root must contain
`bin/python3` and `lib`, with no operator material or credentials. Keep these files quiescent.
The proof fingerprints the dedicated runtime tree up to 512 MiB/20,000 entries; it neither
installs a runtime nor mounts a broad host library directory.

```bash
LYCHD_REQUIRE_SCOUT_EXTRACTION_PROOF=1 LYCHD_SCOUT_EXTRACTION_PROFILE=/absolute/path/runtime.json make test M=container N=0 PYTEST_TARGETS=tests/integration/test_scout_extraction_runtime.py PYTEST_BASETEMP=/tmp/lychd-scout-extraction-proof
```

Use a fresh basetemp path. Without the flag this live test skips; with it, missing prerequisites
fail. The proof uses synthetic bytes, a temporary local socket and disposable namespace workers.
It verifies extraction, host-access denial, CPU/address-space/process limits, pipe flooding and
termination after timeout, cancellation and supervisor death, including observed new-session
descendants. It performs no external request. Each extraction has five seconds plus two seconds
for cleanup; the complete proof includes several such cases and bounded runtime hashing. The
generated `receipt.json` stays below basetemp; the sanitized maintained receipt is in
[Scout's fixtures](tests/fixtures/scout/linux-extraction-runtime.json). A source change invalidates
that receipt's freshness test and requires review and requalification. This proves only the
identified local extractor, not Scout Fetch, workflow integration or the general Coffin boundary.

Scout's DNS/TLS proof uses real local servers inside a fresh Linux user/network namespace. It
requires `unshare`, `ip`, OpenSSL and the installed Python dependencies. Only loopback exists;
the public-classified fixture address below is assigned inside that isolated namespace, never
to a host interface. From the checkout, with a fresh basetemp path:

```bash
LYCHD_SCOUT_HOST_NETNS="$(readlink /proc/self/ns/net)" \
LYCHD_REQUIRE_SCOUT_FETCH_PROOF=1 UV_NO_SYNC=1 UV_OFFLINE=1 \
unshare --user --map-root-user --net sh -c '
  ip link set lo up &&
  ip addr add 93.184.216.34/32 dev lo &&
  make test M=container N=0 PYTEST_TARGETS=tests/integration/test_scout_fetch_runtime.py PYTEST_BASETEMP=/tmp/lychd-scout-fetch-proof
'
```

Set `LYCHD_SCOUT_EXTRACTION_PROFILE` to the reviewed profile above to include the real extraction
child in the passage. Without it, the receipt explicitly leaves extraction untested. The proof
checks actual DNS answers, pinned TLS/SNI/Host, certificate refusal, HTTP framing, mixed-address
refusal, redirect admission and the final HTTP handoff gate. Its generated `receipt.json` contains
source/dependency identities and observed checks; ephemeral certificate keys stay in basetemp.
The maintained receipt and source-freshness test qualify this isolated mechanism profile, not a
production authorizer, durable Scout attempt, workflow, public website or SearXNG service.

The separate current-authority proof uses the same isolated namespace, but joins the production
credential owner, policy, Run fence and network gate to those real servers. In the command above,
use `LYCHD_REQUIRE_SCOUT_AUTHORITY_PROOF=1` and
`PYTEST_TARGETS=tests/integration/test_scout_authority_runtime.py`, with another fresh basetemp.
It needs no extraction profile. It checks the exact GET, path/query substitution, authority
revocation during TLS, finite network budgets and measured gate accounting. Preparation and
claim values are explicit fixtures: this does not exercise database admission, extraction
authorization or inference. Its [maintained receipt](tests/fixtures/scout/linux-authority-runtime.json)
and freshness test bind the authority, transport, fixture and dependency versions actually tested.

The composed Scout proof uses that same namespace command with
`LYCHD_REQUIRE_SCOUT_COMPOSED_PROOF=1`,
`PYTEST_TARGETS=tests/integration/test_scout_composed_runtime.py`, a fresh basetemp, and the
required `LYCHD_SCOUT_EXTRACTION_PROFILE`. It also requires the installed `container-test`
dependencies, the local `/var/run/docker.sock` daemon and an already cached
`pgvector/pgvector:pg18-trixie` image. It selects the cached image ID without pulling and creates
one uniquely owned PostgreSQL container with no IP network or published port, 512 MiB memory,
one CPU and 128 PIDs. Only a dedicated temporary socket directory is mounted; any permission or
SELinux label adaptation stays within that directory. Database API calls have ten-second
timeouts and readiness has a thirty-second polling deadline; the composed async passage has
sixty seconds, with bounded extraction and network cleanup. Runtime hashing is separate.

The proof exercises real credential admission, durable native consent, store-issued claim,
current network authority, fixed extraction, settlement and retained turns. It also challenges
revocation during TLS and refetch after service reconstruction. Explicit node calls and a
`FunctionModel` leave HTTP routing, SAQ process execution, durable Graph checkpoint/resume and
model inference unqualified. The receipt passes only after database, volume and socket-directory
cleanup. Inspect the generated `receipt.json`; its [sanitized maintained copy](tests/fixtures/scout/linux-composed-runtime.json)
and freshness test bind the critical source and dependency identities. This does not repeat the
extractor's separate adversarial qualification or establish general host compatibility.

The optional offline music engineering profile runs without the Vessel or a native Composition:

```bash
uv sync --locked --group music-probe --inexact
uv run --locked --group music-probe python scripts/music_probe.py --help
uv run --locked --group music-probe pytest tests/unit/compositions tests/unit/system/services/test_music_probe.py tests/unit/system/services/test_comfy_probe.py
```

The `music-probe` group installs DawDreamer and NumPy for finite native audio proofs; it is not a
Vessel dependency. The typing group includes NumPy's array annotations without installing
DawDreamer. Native audio tests explicitly skip when DawDreamer is absent; the group-enabled gate
must execute them. Pure recipe, CLI and Comfy transport tests require no running model or service.
Keep recipes, imported media and results in explicit absolute paths outside every checkout.
[Workbench](docs/compositions/riffmaw/workbench.md) owns the supported probe operations and limits.

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

Run Python checks and the clean documentation build sequentially. The clean build removes
Zensical's default `.cache`, which also holds repository test temporary directories. Keep any
explicit uv cache outside that directory while performing the clean build.

Check local file links and fragments, including links into a renamed heading. A moved page needs
its incoming links, parent index, compatibility anchors, and the owning `.nav.yml` updated
together. The architecture suite checks the delivery ledger and its evidence routes; the clean
build checks the published tree. `make docs` serves the Hexanomicon at `http://localhost:7778` for
local reading and layout inspection.

Zensical's built-in [Awesome Nav](https://zensical.org/docs/compatibility/mkdocs/plugins/#awesome-nav)
reads `docs/.nav.yml` for the top-level order and section-local `.nav.yml` files for their pages.
Paths are relative to the file's directory. Add a page to its section's list where readers should
encounter it; a new subsection can have its own `.nav.yml` and be referenced by directory name.
The lists preserve a deliberate reading order: new files are not automatically added to the menu.
No separate Awesome Pages or Awesome Nav package is required. `zensical.toml` keeps the renderer,
theme, extensions, and site metadata.

### Browser development and its backend

Frontend checks and the static build need the Python and Node dependencies above, but no running
Vessel, database, GPU, or model. Start there for a first frontend contribution.

For local backend validation, run `make developer-fixture` in one terminal and
`make frontend-dev` in another. With the default listener settings, the fixture uses
`http://127.0.0.1:8000`; Vite serves the source client at `http://127.0.0.1:5173` and forwards
`/api` and `/schema` to it. Vite alone can load the shell, but API reads need the fixture.

Each fixture start prints username `magus` and a fresh password in its terminal. It reads no
operator configuration or secrets and starts no database, queue worker, model, or Host Reactor. Its
memory state ends with the process. One labelled synthetic conversation and failed Run supply
sample data for Bridge, Orb, and the exact Pattern revision in Loom. The failed status records
no graph, model, or host execution. All mutations are refused, including requests with valid
credentials and CSRF.

Browser login, credential reuse, and the interactive Bridge–Orb–Loom journey remain unqualified.
The pending manual acceptance check uses a dedicated local browser profile: open
`http://127.0.0.1:5173/api/v1/altar/status`, authenticate with the terminal credentials, then open
`http://127.0.0.1:5173/bridge` and follow the synthetic Run into Orb and its exact Pattern in
Loom. Check that authentication carries across those reads. These commands and backend tests
alone do not qualify that browser workflow; [State of Work](docs/state-of-the-work.md#current-evidence-envelope)
records the evidence boundary.

The fixture admits the exact Vite origin through the normal Host, CORS, Origin, authentication,
and CSRF boundaries. Keep credentials out of Vite configuration, URLs, environment variables,
and source; preserve the browser's Origin. Do not connect this preview to the installation used
for Summoning. Real-host browser acceptance uses the compiled Altar at Litestar's own origin
and follows [Summoning](docs/summoning.md). The disposable fixture grants no production macOS
support or Linux host qualification.

### Test Selection

Start with the closest test that can fail, then widen by boundary. For example:

```bash
make test PYTEST_TARGETS="tests/unit" K="expression"
make test PYTEST_TARGETS="tests/integration"
make coverage
```

`K` selects test names. `M` replaces the default `not container` marker expression; include
`not container` when a custom marker selection should retain that exclusion. Most tests are
classified by directory, and the registered `unit` and `slow` markers are currently unapplied. `M=unit` therefore collects
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
