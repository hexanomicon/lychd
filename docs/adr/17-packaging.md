---
title: 17. Packaging
icon: material/package-variant-closed
---

# :material-package-variant-closed: 17. Packaging

!!! abstract "Context and Problem Statement"
    The Forge binds source, dependencies, generated client material, notices, and build evidence
    into inspectable artifacts. Rebirth is a later activation decision: a successful build is not
    permission to publish, migrate, restart, or activate a body.

## Requirements

- Runtime imports live in wheel metadata; contributor tools stay in dependency groups.
- Every candidate binds one clean Git object, version, generated Altar, and legal set.
- Archives are inspected outside a populated developer environment.
- A running body does not install or rewrite its own trusted dependencies.
- Future composed bodies need an inspectable closure and conflict report before activation.
- Keep collaboration, canonical source selection, verification execution, release authorization,
  artifact publication, and public projection as separately evidenced and replaceable offices.
- Bind any collective release authorization to an immutable source object, artifact closure,
  verification evidence, and versioned signer policy rather than a branch, pull request, runner,
  or forge account.

## Considered Options

| Option | Decision | Why |
| --- | --- | --- |
| Install into the running Vessel | Rejected | It merges build and runtime authority and defeats review, rollback, and notice accounting. |
| Let one builder define the architecture | Rejected | BuildKit, Nix, or another tool may change; inputs, outputs, and receipts are the contract. |
| Source-bound wheel, sdist, static client, and Vessel image | Selected foundation | Present Python, npm, OCI, and repository tooling can inspect these artifacts. |
| Automatic synthesis and Rebirth | Designed | Useful future law, but no end-to-end Forge or promotion controller exists. |

## Decision Outcome

LychD uses **source-bound packaging**: review eligibility requires source identity, version,
dependency declaration, generated client, notices, and checks to agree. The repository implements
that for Python release-candidate archives and holds a checked-in Vessel definition. Publication,
synthesized extension bodies, and activation are distinct work.

### Candidate identity and archive audit

`src/lychd/__about__.py` is Hatch's version source. Version preparation changes reviewed files;
it does not commit, tag, push, or publish. `pyproject.toml` separates installed CLI, application,
database, worker, and agent dependencies from documentation, test, lint, and typing groups.
`postgres-binary` is a local convenience extra, not a production dependency. `uv.lock` records a
resolved Python closure and hashes for frozen repository and image builds; a wheel carries
compatible constraints, neither that lock nor vendored dependencies.

The wheel contains `src/lychd`, including compiled Altar material under `src/lychd/public/`. The
sdist keeps the Containerfile, strict `.containerignore`, Python and frontend locks, frontend
source, scripts, source, tests, and legal files.
The auditor requires one wheel and one sdist for the declared version; checks MPL-2.0 metadata,
byte-identical notices, exact-source Altar payloads, required sdist members, any `v<version>`
release tag; and writes SHA-256 checksums.

Its isolated-install gate creates a fresh environment, resolves and installs the wheel and its
dependencies, checks consistency, invokes the CLI, imports the Litestar root, and exercises
internal Reactor and database help. That establishes sufficient metadata for that resolution, not
package-for-package equality with `uv.lock`.

### One body before any build

A future coupled-organ Forge must first bind Core and organ revisions, manifests, locks, build
tools, platform, base-image digests, and system packages. It resolves dependency and platform
conflicts away from the active runtime; records every input, generated file, legal obligation, and
output digest; binds separately compiled deployment intent from [Containers](08-containers.md) and
[Configuration](12-configuration.md); then verifies the whole body before promotion.

Pre-v1 in-process organs are coupled source, not an extension ABI. Compiled organs require an
explicit manifest, platform check, and activation path; arbitrary shared-object scanning is
forbidden. External-service Animators remain the independent compatibility boundary. This is
Designed: no Crypt scanner, signed synthesis manifest, or packaging-to-materialization coupling
exists.

### Vessel image and Rebirth boundary

The checked-in multi-stage `Containerfile` uses frozen, non-development, non-editable `uv` sync;
its `.containerignore` admits only declared build inputs from a checkout or source archive;
passes its built virtual environment to the runner; uses `psycopg` with Debian `libpq5` and rejects
`psycopg-binary`; carries project notices and a fail-closed installed-distribution inventory; and
defaults to an unprivileged user with non-writable `/app`.

Those are inspectable image laws, not a hardening or reproducibility certificate. Python and uv
base images plus Debian packages are not all content-pinned or snapshot-pinned; the candidate
workflow builds and retains no OCI image. LychD makes no byte-identical Vessel-image claim. A
future builder, including Nix, must emit equivalent or stronger source, dependency, platform,
legal, and digest receipts.

Candidate construction begins from a clean checkout whose `HEAD` is a full 40- or 64-character
lowercase Git object ID. Frontend verification leaves tracked contracts clean; the exact-source
Altar build may change only `src/lychd/public/`. The candidate target runs Python and frontend
gates, Altar and Hatch builds, archive audit, isolated install, and checksums. Its hosted workflow
has read-only repository permission, short-lived archives, and no publication authority.

A passing candidate is review evidence. Public promotion needs a separately authorized binding of
tag, source revision, archives, image, SBOM or equivalent inventory, and clean-host operation
receipts. [Evolution](18-evolution.md), [Privilege](10-privilege.md), and
[Human in the Loop](25-hitl.md) own migration, restart, and judgment.

### Trust profiles and delivery boundary

Security's profiles need their own dependency closure, entrypoint, policy, legal inventory, and
digest; a shared base layer does not merge authority. The Vessel has a checked-in definition but
no maintained published-image receipt. Tomb has no image, queue, executor, or `nono` integration.
Delegated execution retains typed containment-profile intent and a no-effect reference adapter, but
Coffin and Provider Gate policy remain Designed with no lower-trust image or effectful supervisor.
The [public release chain](../state-of-the-work.md#public-release-artifact-chain),
[Tomb](../state-of-the-work.md#tomb-untrusted-execution),
[delegated execution](../state-of-the-work.md#delegated-agent-execution), and
[Smith/Forge promotion](../state-of-the-work.md#smith-forge-promotion) own their actual state.

### Future forge-neutral source and release trust {#forge-neutral-source-trust}

GitHub is the current public early-development surface for discovery, review, manually dispatched
candidate workflows, and published documentation. It is not a permanent constitutional
dependency: candidate identity is the full Git object ID, evidence is portable, and no GitHub
branch, pull request, Actions run, Pages deployment, organization role, or account is sufficient
release authority. Website and CDN projection remain separable from source custody.

[Radicle's Git replication protocol](https://radicle.dev/guides/protocol) is the first concrete
candidate for a future distributed source canon, not a current dependency or delivery claim. It
may provide replicated repository identity, namespaced signed references, and
[threshold canonical references](https://radicle.dev/2025/08/12/canonical-references); it does not
replace the website, discovery surfaces, package registries, builders, verification plans, or
artifact mirrors. Forgejo, GitHub, and later projections remain valid collaboration surfaces. Once
an explicit cutover selects another canon, however, they are downstream mirrors rebuilt from it:
there is no bidirectional “newest branch wins” merge and no second canonical `main`. Contributions
arriving through a mirror are proposals until admitted by the canonical-source policy.

#### Human seats and source selection

The proposed initial source policy uses a versioned roster of six independently controlled human
maintainer seats and a threshold of four. A later quorum design chooses its roster and threshold explicitly
in each governance epoch from its compromise, unavailability, conflict, safety, and liveness
assumptions; neither the previous ratio nor mathematical majority changes it implicitly.

A person receives one vote regardless of device count. Maintainers publish work under personal references
or branches and collectively nominate an exact Git object; they never share one private “main
key.” Signed namespaced references show that eligible protocol keys published that object, and a
canonical reference may be synthesized when the configured threshold agrees. A separately
verified epoch roster must bind each eligible key to one human seat. These facts do not by
themselves prove conscious human review, successful verification, release approval, or safe
activation.

#### Credential custody and roster recovery

Seat authority is independent from protocol and machinery. A Radicle identity or delegate set
cannot silently redefine LychD's release roster. Seed nodes, mirrors, bots, CI runners, and
deployment hosts are not human seats. Seed-only transport credentials remain separate from human
seat authority. A reviewed source protocol may intrinsically couple a maintainer's transport
identity to namespaced-reference signing, as Radicle does; that combined credential is limited to
source publication and receives no CI, promotion, deployment, migration, or lifecycle authority.
Those higher-trust domains use distinct individual credentials and never share a team key.
Promotion credentials should be more strongly protected than ordinary online collaboration keys
and are never installed in an untrusted builder. Rotation or revocation changes future eligibility
without rewriting historically valid evidence.

An ordinary roster transition requires the preceding epoch's threshold authorization. Any
exceptional recovery rule must itself be threshold-authorized and bound into that preceding epoch,
may only reconstruct the roster under its stated failure conditions, and cannot endorse a
candidate or authorize a live effect. Key loss or compromise without either freezes selection and
promotion rather than revealing a founder master key.

#### Portable verification

Verification is also forge-neutral. A versioned plan and its receipts, not the service that ran
them, form the interface. A local workstation, isolated host or VM, GitHub or Forgejo runner, or a
future Radicle adapter may execute the same plan. Each receipt binds the exact source object,
resolved inputs, plan and tool versions, platform and containment context, command results, and
output digests. Host-level Podman, systemd, migration, or recovery claims still require the
operator boundary defined by [Testing](04-testing.md); a green container cannot attest its own
host. Changing the candidate or any bound input invalidates affected receipts and signatures.
Deterministic failure cannot be outvoted.

#### Conditions for a canonical cutover

Radicle becomes eligible for canonical use only after all of these gates pass:

1. A reviewed public-history boundary contains only material intended for durable replication;
   peer-replicated Git objects must be treated as difficult or impossible to retract.
2. Six human seats have independent custody, documented rotation and revocation, and rehearsed
   loss, compromise, founder-absence, two-seat-absence, no-quorum, stale-signature, and replay
   cases.
3. At least two independently administered availability domains seed or replicate the repository,
   maintainers retain recoverable copies, and loss plus mirror-rebuild drills pass. Storage,
   bandwidth, upgrade, and monitoring cost is measured on the intended operating hardware.
4. The exact-object verifier, portable attestation receipts, and signed promotion envelope exist
   independently of any forge or CI product.
5. Adoption review pins and tests the then-current protocol and implementation, including identity
   amendments, device and key recovery, canonical-reference quorum, partition and cross-version
   behavior, and the current
   [signed-reference security record](https://radicle.dev/2026/03/30/disclosure-of-vulnerability-in-signed-references).
6. [State of Work](../state-of-the-work.md#smith-forge-promotion) records the proven topology and
   recovery evidence before the canonical cutover.

Until those gates pass, GitHub remains the current collaboration route and Radicle may be used only
as an experimental replica. No distributed repository identity, canonical-reference verifier,
maintainer quorum roster, key-custody system, independent attestation plane, or Radicle node is delivered today.

## Consequences

!!! success "Positive"
    Archives retain reviewed source and legal material, generated frontend drift is bounded, and
    forge and builder choices stay replaceable because immutable objects and receipts—not vendor
    vocabulary—define success.

!!! failure "Negative"
    Candidate work repeats substantial Python and frontend checks; resolver installation and
    mutable operating-system inputs leave reproducibility gaps, while publication and activation
    await separately authorized promotion. Distributed custody later adds roster governance, key
    operations, independent replicas, monitoring, and recovery drills.
