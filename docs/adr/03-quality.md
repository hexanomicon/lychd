---
title: 3. Quality
icon: material/check-all
---

# :material-check-all: 3. Quality

A contributor should be able to reproduce a failed check without reconstructing someone else's
workstation. LychD therefore keeps a small, shared toolchain and makes each gate explicit about the
claim it can support.

## Decision Outcome

The Python environment uses **uv**, **Ruff**, **BasedPyright**, and **pytest**. The Makefile gives
contributors and automation one command grammar; [CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#setup-and-commands)
owns setup and exact command examples.

### The Python Pillars

| Tool | Responsibility |
| --- | --- |
| uv | Resolve dependencies, retain `uv.lock`, and execute tools in the managed environment. |
| Ruff | Lint and format under the deliberate rules and exceptions in `pyproject.toml`. |
| BasedPyright | Check `src/lychd` in strict mode, with the same implementation locally and in CI. |
| pytest | Establish regression evidence within the taxonomy and limits of [Testing](04-testing.md). |

Reproducibility depends on committed configuration as well as tool choice. The selected tools
share that configuration, and dependency changes go through the uv environment; any exception
must appear in reviewed configuration. The older Poetry, mypy, Flake8, and Black/isort stack was a
credible alternative, but divided environment and lint/format responsibility among more
independently configured tools.

### Cross-stack gates

A complete change can cross several evidence boundaries. Keep their results separate:

| Gate | What it establishes |
| --- | --- |
| Python umbrella | Non-mutating lint, format, strict typing, and ordinary tests. Applying formatting requires an explicit command. |
| Disposable PostgreSQL | Explicit database and lifecycle receipts against the selected container profile. |
| Altar check and build | Generated OpenAPI agreement, client checks, and the compiled static projection under `src/lychd/public/`. |
| Companion interaction | Kotlin/JVM compilation and client-local state traces under the pinned Gradle harness; no Android device or native service qualification. |
| Companion Android | Application compilation, lint and ViewModel checks; separate instrumented Activity checks establish behavior only on the selected emulator or device. |
| Documentation build | The published Hexanomicon can be generated from its maintained source and navigation. |

Frontend work has its own gates, as does Android work; neither runs silently under the Python
umbrella. Both frontend gates regenerate the API contract, and the build also updates the tracked
static projection. Review that output with the source that produced it. A generated diff guard
catches disagreement.

Automatic pull-request, `dev` and `main` checks run repository lint, formatting, strict typing and the
explicit core test selection owned by `make test-ci`. That selection uses in-process substitutes
and excludes real host and container qualification. The full four-lane Repository Checks workflow
remains manual while host-runner compatibility is unresolved; changes still require the broader
gates appropriate to their boundary. The Pages workflow separately supplies the clean documentation
gate and deployment artifact on `main`. The tag/manual release-candidate workflow remains separate:
a green core check does not bind release archives or prove installation on a host.

[Frontend](15-frontend.md#decision-lock-and-reopening-gate) owns the exact Node/npm pins and
single client vocabulary. Bun, a second lock/runtime, Tailwind, or another styling compiler must
meet that Covenant's reopening gate before admission. The client currently uses strict
TypeScript, `svelte-check`, and Vitest/jsdom, with native CSS inspected directly. Editor
configuration selects `markdownlint` for Markdown and Red Hat YAML for YAML and Docker Compose.
TOML and JSON have no repository-selected formatter; editor assistance is not another CI receipt.

The Companion client keeps its Gradle wrapper, Kotlin and Android plugins, strict dependency
locks, and artifact verification under the Android client root. JDK 17 runs both the SDK-free
interaction checks and the opt-in application build. The
[client README](https://github.com/hexanomicon/lychd/blob/main/clients/android/README.md) owns exact
setup and commands. Wrapper and dependency changes carry their pins and checksums. A passing
interaction test does not establish device behavior; application and device checks do not establish
native Companion authority or qualify every declared Android version.

## Consequences

A tool or configuration change must carry its lockfile, generated-output, and documentation
consequences with it. Shared gates then make defects reproducible, while each gate's declared
scope keeps a repository pass from becoming an unsupported host or production-browser claim.
[State of Work](../state-of-the-work.md) owns delivery interpretation;
[Packaging](17-packaging.md) owns artifact identity and promotion boundaries.