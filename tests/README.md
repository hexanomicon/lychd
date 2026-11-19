# Qualification profiles

[CONTRIBUTING](../CONTRIBUTING.md#quality-checks) owns ordinary checks and command selection.
This reference covers profiles that need an explicit database, model, namespace or host boundary.
[State of Work](../docs/state-of-the-work.md#current-evidence-envelope) owns maintained results
and retired observations; a passing substitute test does not qualify the external system.

## Before running a profile

Core tests execute in an admitted OCI image. The ordinary
[wrapper](../scripts/container_checks.sh) forwards selection variables, not arbitrary proof flags,
files, sockets or credentials. A profile needs its own adapter for those inputs. A host-native
Core pytest invocation is not a fallback.

The Docker PostgreSQL harness and dedicated Scout OCI adapter below have explicit launch routes.
The other model/private-manager/composed recipes retain requirements for a future admitted OCI
adaptation; their `text` blocks are selection references, not working host launch commands.
Retired native receipts cannot qualify a new image or occurrence.

Use fresh task-owned scratch outside protected authority roots. Optional cases skip before external
access when not selected; explicitly required proofs fail on missing prerequisites. Inspect both
proof and cleanup evidence, and reconcile uncertain effects before admitting another occurrence.
Profile selection alone proves neither its enforcement nor successful settlement.

## Disposable PostgreSQL, Intercom and Atlas

The separate `container-test` group is included in the check image. To admit the Docker daemon
socket and host networking for disposable PostgreSQL:

```bash
LYCHD_TEST_ENGINE=docker LYCHD_TEST_DAEMON_SOCKET=/absolute/path/to/owned-docker.sock make test-containers
```

The socket must be an explicit absolute local path. This trusted daemon-capable harness disables
its container SELinux label boundary without relabeling the socket; ordinary checks retain their
label boundary. It may pull the pinned `pgvector` image and grants no daemon authority to the
production Vessel. Ryuk is unprivileged by default. A deliberately selected rootless compatibility
profile may use `TESTCONTAINERS_RYUK_PRIVILEGED=true make test-containers`; never export that as
the repository default. [Ward's receipt](../docs/state-of-the-work.md#remote-iam) records its scope.

[Intercom](../docs/sepulcher/intercom.md)'s outbound custody and migration modules additionally require an explicit
disposable `LYCHD_INTERCOM_TEST_DATABASE_URL`; its migration module needs empty public Intercom
tables. They do not start a container implicitly. Independent SDK qualification uses a separate
Python environment and test-only signing middleware, not a production dependency.
The [paired receiver suite](integration/test_intercom_inbox_pg.py) migrates an isolated schema
per test and accepts the same explicit disposable database URL. With the URL unset, it starts
the disposable PostgreSQL container supplied by the manual test profile.
`uv run --locked python scripts/intercom_lab.py --help` performs no external effect.

Atlas also accepts `LYCHD_ATLAS_TEST_DATABASE_URL` inside the OCI profile for a daemon-free
sidecar. It requires literal host `canvas-postgres:5432` and database `canvas_test` on an
operator-created internal network. No Docker socket, host networking or production database is
admitted to the test container. The operator owns both temporary containers and cleanup; the
module recreates only its two Atlas tables.

## Quadlet and private-manager adaptation

Real private-manager tests require a fresh task-owned delegated user service. A private bus/HOME
alone does not isolate cgroups: another manager could migrate unrelated processes. Verify the
exact transient unit, delegation, ancestry, writable cgroup and exclusive task processes before
launching; never fall back to the installed manager. The signed-stop host-native proof is retired;
current container lifecycle completion needs its own authenticated, qualified passage.

The [target-switch proof](integration/test_systemd_quadlet_transaction.py) needs the installed
Quadlet generator, an ordinary rootless Podman cache containing its exact pinned Python image,
and a responding user session bus. It exports the image without network access and uses a private
image store and manager. Retained selection recipe, requiring an admitted OCI adaptation:

```text
proof_unit="lychd-proof-quadlet-$$.service"
systemd-run --user --unit="$proof_unit" --collect --wait --pipe --service-type=exec \
  --property=Delegate=yes --property=RuntimeMaxSec=1000 --property=TimeoutStopSec=30 \
  --property="WorkingDirectory=$PWD" --setenv="LYCHD_SYSTEMD_PROOF_OUTER_UNIT=$proof_unit" \
  --setenv=LYCHD_REQUIRE_QUADLET_PROOF=1 /usr/bin/make test M=container N=0 \
  PYTEST_TARGETS=tests/integration/test_systemd_quadlet_transaction.py \
  PYTEST_BASETEMP=/tmp/lychd-quadlet-proof
```

Use a fresh short basetemp; allow up to 1 GiB scratch, monitored rather than quota-enforced.
Inspect the retained receipt and cleanup. This proof starts no production units or model and
qualifies neither the full Orchestrator nor Host Reactor path.

## Embedding transport adaptation

The [embedding proof](integration/test_llamacpp_embedding_runtime.py) requires Linux, ordinary
rootless Podman with the exact image in the [public fixture](fixtures/embeddings/qwen3-06b-q8-b9445.json), and an
already available public Qwen3-Embedding-0.6B Q8_0 file. It verifies size/SHA-256 before Podman
access and never downloads, copies, relabels or modifies the model. Keep it quiescent. On SELinux,
prepare a dedicated public fixture with shared `container_file_t:s0`; another container's private
MCS label is insufficient. The test does not disable SELinux.

Retained selection for an admitted OCI adaptation:

```text
LYCHD_REQUIRE_EMBEDDING_PROOF=1 LYCHD_EMBEDDING_FIXTURE=/absolute/path/Qwen3-Embedding-0.6B-Q8_0.gguf make test M=container N=0 PYTEST_TARGETS=tests/integration/test_llamacpp_embedding_runtime.py PYTEST_BASETEMP=/tmp/lychd-embedding-proof
```

The proof owns one disposable model container without network, host ports or GPU and enters only
its network namespace to exercise the registry, Dispatcher and HTTPX driver. The model's CPU and
address-space bounds are 60 seconds/4 GiB; the child gets 30 seconds/2 GiB and bounded output.
These are process limits, not cgroup quotas. Work has 175 seconds plus 30 seconds for cleanup;
artifact hashing is outside that clock. Inspect `embedding-runtime/receipt.json` under basetemp
for proof and cleanup success. The ordinary image cache and shared helper lifetime remain
operator-owned. This tests externally started transport, not activation or Archive recall.

## Semantic memory adaptation

The fixed Archive proof joins authenticated in-process ASGI, real PostgreSQL and the registered
CPU embedding profile above. Its lifecycle cases cover candidate exclusion, promotion/derivation,
attributed recall/resolution, correction/rederivation, revocation and replay. It permits at most
eight embedding operations/16 POSTs/4,088 input tokens and generates no answer.

An admitted OCI adaptation needs the quiescent model/cache above, `container-test` dependencies,
a local Docker socket and cached PostgreSQL image
`sha256:1963bc48febf543433baa1ce3edcc6cc08154de722e22495f86681cc9a849026`.
It must not pull images or select a warm service. The retained native user-unit observation does
not establish current container qualification.

The helper owns the networkless model container, a networkless PostgreSQL container with a fresh
Unix-socket directory and anonymous data, and an FD-pinned model-namespace loopback relay.
PostgreSQL has observed 512 MiB/zero-swap/one-CPU/128-PID cgroup limits; model bounds remain per
process and relay limits are observed separately. The trusted outer caller needs Podman user
namespaces. Only the model's zero-capability/NoNewPrivileges state is asserted; this is no
aggregate host or untrusted-guest containment guarantee.

Inspect `archive-semantic-native/receipt.json` and workflow/fence journals under fresh basetemp:
proof, cleanup, closed clients and zero leases must pass. After any failure, independently
reconcile recorded units, PID groups/cgroups, owned containers, volume, listener and socket before
another occurrence. Preserve unrelated work, warm services, model bytes and retained data.
[The Archive evidence record](../docs/state-of-the-work.md#karma-semantic-memory) owns the maintained scope;
these synthetic cases do not prove semantic browser delivery, retrieval quality or autonomy.

The separate [semantic-answer proof](integration/test_semantic_answer_native_runtime.py) needs
its own fresh scoped warm-Chat relay and private six-key `ProbeProfile`, admitted through
`LYCHD_SEMANTIC_ANSWER_CHAT_PROFILE` and `LYCHD_REQUIRE_SEMANTIC_ANSWER_NATIVE_PROOF=1`.
The ordinary Archive selection does not admit this relay. Reserve four embedding operations/eight
POSTs and the raw helper's two-Chat outer ceiling of 256 output tokens each.

The active `generated-answer-and-empty-recall-v2` occurrence tightens that to **one** Chat call:
A needs an attributed answer ending in strict `stop`; B refuses revoked authority before Chat;
C yields labelled deterministic empty recall with no Chat grant, Context assembly or SDK suffix.
There is no prior-history replay. A `length` result fails even if text is useful. Historical v1
spending stays recorded; each occurrence needs fresh admission. Admit actual model/readiness
request allowances, shared leases, SQL ownership and cleanup. Independently inspect source/content
and physical settlement; SDK history/replay equality are test-backed reports, not independently
reconstructed evidence. [The maintained receipt](fixtures/archive/native-semantic-answer-runtime-2026-10-19.json)
binds critical source through `_sources(ANSWER_PROFILE)` and does not qualify installed startup,
browser delivery, automatic crash recovery, general answer quality or aggregate containment.

## Scout static and RSS extraction adaptation

For the separate Linux x86-64 extraction proof, prepare a JSON profile outside the checkout with
absolute `bwrap` and dedicated `python_root` paths, plus a `libraries` array of absolute paths for
these eight individual files:
`ld-linux-x86-64.so.2`, `libc.so.6`, `libdl.so.2`, `libgcc_s.so.1`, `libm.so.6`, `libpthread.so.0`,
`librt.so.1`, `libutil.so.1`. The installed interpreter root must contain `bin/python3` and `lib`,
without operator material or credentials. Keep files quiescent. Runtime fingerprinting is bounded
to 512 MiB/20,000 entries; the proof installs nothing and mounts no broad host library directory.

Selection reference for the admitted adapter:

```text
LYCHD_REQUIRE_SCOUT_EXTRACTION_PROOF=1 LYCHD_SCOUT_EXTRACTION_PROFILE=/absolute/path/runtime.json make test M=container N=0 PYTEST_TARGETS=tests/integration/test_scout_extraction_runtime.py PYTEST_BASETEMP=/tmp/lychd-scout-extraction-proof
```

Synthetic bytes, a local socket and disposable workers exercise extraction, host-access denial,
CPU/address-space/process limits, pipe flooding and settlement after timeout/cancellation/parent
death, including new-session descendants. Each extraction gets five seconds plus two for cleanup;
the overall proof includes several cases and bounded hashing. Review basetemp's raw `receipt.json`
before admitting the [sanitized static fixture](fixtures/scout/linux-extraction-runtime.json).
Changed source requires freshness review and requalification; this is neither Fetch nor a general
Coffin/workflow proof.

RSS uses the same runtime, Expat 2.6+ and enabled reparse deferral. Run the static proof first on
the complete current closure; supply its **actual generated raw receipt**, not the sanitized fixture:

```text
LYCHD_REQUIRE_SCOUT_EXTRACTION_PROOF=1 \
LYCHD_REQUIRE_SCOUT_RSS_EXTRACTION_PROOF=1 \
LYCHD_SCOUT_EXTRACTION_PROFILE=/absolute/path/runtime.json \
LYCHD_SCOUT_STATIC_EXTRACTION_RECEIPT=/absolute/current-run/receipt.json \
make test M=container N=0 \
  PYTEST_TARGETS=tests/integration/test_scout_rss_extraction_runtime.py \
  K=test_scout_rss_extraction_host_boundary PYTEST_BASETEMP=/tmp/lychd-scout-rss-proof
```

Use a second fresh basetemp; hold source/runtime unchanged through both proofs. Inspect the RSS
receipt and process settlement before admitting a [maintained copy](fixtures/scout/linux-rss-extraction-runtime.json).
CI checks its six source fingerprints and static-runtime agreement. RSS adds actual child calls,
launch/protocol, output, timeout and cancellation cases; static owns the shared host/resource/death
cases. Neither qualifies feed admission, acquisition, digest custody or watching.

## Scout OCI network and extraction qualification

The dedicated adapter runs static extraction → DNS/TLS → current authority, unchanged and in that
order, using real local servers in an isolated Linux x86-64 namespace. Local `trusted-scout-c2`
requires Docker 29.7.2/API 1.55, runc 1.5.1 and host `curl`, `sha256sum`, `python3`, `timeout`.
Host Python uses only stdlib metadata/Unix-socket engine control; Core tests use Python 3.15.0 in
OCI. Select an existing artifact directory outside the checkout; each run allocates a fresh child:

```bash
LYCHD_SCOUT_QUALIFICATION_PROFILE=trusted-scout-c2 \
LYCHD_SCOUT_QUALIFICATION_OUTPUT=/absolute/existing/artifact-directory \
  bash scripts/container_scout_qualification.sh
```

Manual **Repository Checks**, `scope=scout`, selects separate `trusted-scout-ci-c1` on the chosen
revision. Default `scope=contracts` retains Python/PostgreSQL checks. CI pins the official Docker
setup action and Docker 29.9.3/API 1.56/runc 1.5.2. Controller and CLI must share the explicit local
Unix socket; remote endpoints, context overrides, different engines and automatic fallback refuse.
No daemon socket enters the test container. `--build-only` builds images without qualification.

The [controller](../scripts/scout_qualification.py) and its
[profile tests](architecture/test_scout_qualification_profile.py) own exact inventories and custody
checks. The adapter derives from the source-bound image, verifies its exact ID/base layers, adds
Bubblewrap/ip/OpenSSL and a dedicated CPython plus eight library paths. Builds may fetch official
images, Debian and locked Python dependencies. A uniquely owned tag binds the base; a config ID
is not a registry manifest digest. The checked immutable Moby seccomp profile adds only required
namespace/mount operations; no privileged-container, unconfined-seccomp or host-pytest fallback.
The fixed runtime search path is `/runtime/lib:/lib64`, without procfs-based `$ORIGIN` resolution.

Both profiles deliberately relax the test container's label boundary for trusted setup. Local C2
disables only its SELinux container label, preserving host enforcement and ordinary checks. Its
controller compares complete engine defaults, replacing read-only `/proc/sys` with `/proc/sys/kernel`
and 18 masks, including seven non-user subtrees and eleven user-quota leaves. After a fresh user
namespace, setup sees its own quota interfaces; those masks are not worker confinement. The
untrusted worker must have empty read-only root, no procfs/network/unrelated descriptors, and no
nested-namespace authority. Actual outer/fresh-child observations and unchanged host quota/namespace
identity are required; inventory drift refuses rather than extending the profile.

CI-c1 additionally loads one owned named AppArmor policy with `userns` and `flags=(unconfined)`
for trusted outer setup. The outer process and fresh child retain that exact label/mode; this is
not LSM confinement. Its Azure kernel lacks `crypto`: the declared eight-entry top-level inventory
masks six non-user/non-kernel subtrees; twelve user-quota entries/eleven masks stay unchanged.
The fresh-child observer receives only the selected profile and an empty environment. Loading
refuses existing policies, compiles without cache, adds without replacement and compares compiled
input to kernel-exported bytes. Cleanup needs matching source/binary/kernel identities, terminal
controller custody and no container using the policy, including unexpected unlabelled users.
Ambiguity preserves the policy and fails until ephemeral runner teardown. Global AppArmor userns
restriction stays enabled; no host sysctl or AppArmor service is changed. This setup is CI-only.

The container has no checkout/HOME/daemon mounts and `--network=none`; setup assigns
`93.184.216.34/32` only to its loopback, then drops to the ordinary check user with all capabilities
cleared and `no_new_privs`. Readback must show 2 GiB/two CPUs/256 PIDs, a distinct network namespace,
only loopback and no external route. Static proves the actual runtime's hostile-input and
settlement boundary. DNS/TLS receives the extraction profile and checks DNS, pinned TLS/SNI/Host,
certificates, framing, mixed addresses, redirects and final handoff. The separate authority proof
needs no extraction profile; it joins production credential/policy/Run-fence/network gates and
checks exact GET, substitution, revocation during TLS, budgets and accounting. Its preparation and
claim are fixtures, not database admission, extraction authorization or inference.

Exports contain generated sanitized receipts, bounded logs/build diagnostics, engine/image,
source/profile/seccomp hashes, capability evidence and settlement. CI retains them seven days;
test basetemps and ephemeral TLS keys remain in the removed container. Inspect actual results and
cleanup before replacing maintained fixtures; dispatch does not update/admit them automatically.
The [OCI static receipt](fixtures/scout/linux-oci-extraction-runtime.json) binds its recipe/runtime/lock
and paired network proofs separately from historical static/RSS evidence. These proofs qualify
isolated mechanisms, not durable attempts, a workflow, production authorizer, public website or SearXNG.

## Scout composed and Scavenger adaptation

The [composed proof](integration/test_scout_composed_runtime.py) requires its own admitted OCI
adaptation; the network adapter above does not execute it. Select
`LYCHD_REQUIRE_SCOUT_COMPOSED_PROOF=1`, the test path, a fresh basetemp and reviewed
`LYCHD_SCOUT_EXTRACTION_PROFILE`. Supply `container-test` dependencies, local `/var/run/docker.sock`
and already cached `pgvector/pgvector:pg18-trixie`, selecting its image ID without pulling.

It owns one networkless/unpublished PostgreSQL container with 512 MiB/one CPU/128 PIDs and only a
dedicated temporary socket-directory mount; any permission/SELinux adjustment stays in that
directory. DB API calls get ten seconds, readiness thirty, the async passage sixty; extraction
and network cleanup are bounded separately, as is runtime hashing. It checks credential/consent/
store-claim/network/extraction/settlement/retained-turn behavior, revocation during TLS and refetch
after reconstruction. Explicit node calls and `FunctionModel` do not qualify HTTP routing, SAQ,
durable Graph checkpoint/resume or model inference. Success includes DB/volume/socket cleanup;
inspect raw `receipt.json` before the [sanitized fixture](fixtures/scout/linux-composed-runtime.json).
The extractor's adversarial qualification remains separate.

Scavenger's observation profile uses the native store and reference-only Run/Graph handoff with
an already available disposable PostgreSQL fixture, never an installed-profile database. It also
requires the observed loopback-only namespace and launcher's `LYCHD_SCOUT_HOST_NETNS` identity.
The future admitted adapter must run the whole selection inside that boundary:

```text
LYCHD_REQUIRE_SCAVENGER_PG_PROOF=1 make test M=container N=0 \
  PYTEST_TARGETS=tests/integration/test_scavenger_feed_pg.py \
  PYTEST_BASETEMP=/tmp/lychd-scavenger-feed-proof
```

Real acquisition in that file additionally requires `LYCHD_REQUIRE_SCOUT_COMPOSED_PROOF=1`,
reviewed `LYCHD_SCOUT_EXTRACTION_PROFILE`, and the composed cached-image/socket prerequisites.
Use a new basetemp; observe namespace, database and cleanup rather than assuming flags enforce them.
No maintained-success or installed-cutover claim follows. Public Internet, SAQ process/restart,
model operation, recurring cadence, Search and mobile remain outside this proof; platform-agent
construction is not native containment evidence.

## Optional music probes

Offline engineering tools need neither a Vessel nor a native Composition:

```bash
uv sync --locked --group music-probe --inexact
uv run --locked --group music-probe python scripts/music_probe.py --help
```

`music-probe` adds DawDreamer/NumPy for finite audio proofs, not Vessel dependencies; the typing
group supplies NumPy annotations without DawDreamer. Native audio tests skip if DawDreamer is
absent. To qualify this group, admit an OCI check image containing it; default checks and host
pytest do not establish that gate. Pure recipe, CLI and Comfy transport tests need no model/service.
Keep recipes, media and results at explicit absolute paths outside checkouts.
[Workbench](../docs/compositions/riffmaw/workbench.md) owns probe operations and limits.
