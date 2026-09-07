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

The older Poetry, mypy, Flake8, and Black/isort stack remains a credible alternative. It was not
selected because it spreads environment and lint/format responsibility across more independently
configured tools. The selected tools share committed configuration, so contributors can
reproduce the same checks. Dependency changes go through the uv environment; any exception
must be recorded in reviewed configuration.

### Cross-stack gates

A complete change can cross several evidence boundaries. Keep their results separate:

| Gate | What it establishes |
| --- | --- |
| Python umbrella | Non-mutating lint, format, strict typing, and ordinary tests. Applying formatting requires an explicit command. |
| Disposable PostgreSQL | Explicit database and lifecycle receipts against the selected container profile. |
| Altar check and build | Generated OpenAPI agreement, client checks, and the compiled static projection under `src/lychd/public/`. |
| Documentation build | The published Hexanomicon can be generated from its maintained source and navigation. |

The Python umbrella does not silently run frontend work. Both frontend gates regenerate the API
contract; the build also changes the tracked static projection, which belongs in review with the
source that produced it. A generated diff guard catches disagreement.

Pull requests expose all four lanes independently. A push to `main` repeats the first three;
the Pages workflow supplies the clean documentation gate and deployment artifact in one build.
The tag/manual release-candidate workflow remains separate: a green source change does not bind
release archives or prove installation on a host.

[Frontend](15-frontend.md#decision-lock-and-reopening-gate) owns the exact Node/npm pins and
single client vocabulary. Bun, a second lock/runtime, Tailwind, or another styling compiler must
meet that Covenant's reopening gate before admission. The client currently uses strict
TypeScript, `svelte-check`, and Vitest/jsdom, with native CSS inspected directly. Editor
configuration routes Markdown through `markdownlint`, and TOML, YAML, and JSON through Prettier;
editor assistance is not another CI receipt.

## Consequences

Changes to a tool or its configuration carry their lockfile, generated-output, and documentation
consequences. Shared gates make defects reproducible, while exact scope prevents a passing
repository check from becoming an unsupported host or production-browser claim.
[State of Work](../state-of-the-work.md) retains delivery interpretation; [Packaging](17-packaging.md)
retains artifact identity and promotion boundaries.
