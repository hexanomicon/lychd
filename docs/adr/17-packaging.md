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
sdist keeps the Containerfile, frontend source and lock, scripts, source, tests, and legal files.
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
Coffin has Partial policy objects and a no-effect adapter, but no lower-trust image or effectful
supervisor. The [public release chain](../state-of-the-work.md#public-release-artifact-chain),
[Tomb](../state-of-the-work.md#tomb-untrusted-execution),
[delegated execution](../state-of-the-work.md#delegated-agent-execution), and
[Smith/Forge promotion](../state-of-the-work.md#smith-forge-promotion) own their actual state.

## Consequences

!!! success "Positive"
    Archives retain reviewed source and legal material, generated frontend drift is bounded, and
    builder choice stays replaceable because receipts—not vendor vocabulary—define success.

!!! failure "Negative"
    Candidate work repeats substantial Python and frontend checks; resolver installation and
    mutable operating-system inputs leave reproducibility gaps, while publication and activation
    await separately authorized promotion.
