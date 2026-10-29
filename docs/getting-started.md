---
title: Getting Started
icon: material/rocket-launch
---

# Getting Started

LychD is **pre-alpha**. Use this page to choose the right first path; do not treat Designed
behaviour as delivered. [State of Work](state-of-the-work.md) owns maturity claims—start with its
[outcome matrix](state-of-the-work.md#outcome-matrix).

## Choose a path

| You need… | Go here |
| --- | --- |
| Architecture of one request through the body | [Map](map.md) |
| Contributor checkout, lanes, quality gates, and branch rules | [CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md) |
| Isolated Altar/backend fixture without a live host install | [CONTRIBUTING — developer fixture](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#quality-checks) and issue [#53](https://github.com/hexanomicon/lychd/issues/53) |
| Live Linux host acceptance (init → bind → model → reply) | [Summoning](summoning.md) — **not end-to-end yet** |
| Vocabulary | [Lexicon](lexicon/index.md) |

Windows and macOS are **unsupported hosting platforms**, including Linux guests on those hosts.
Partners who develop from Windows should use a supported remote or dedicated Linux host for
Summoning and host proofs; repository Core checks still run inside the OCI check image.

## First hour on a checkout

These steps verify the repository on a machine with a working OCI engine (rootless Podman by
default). They do **not** prove a managed installation or a model reply.

```bash
git clone https://github.com/hexanomicon/lychd.git
cd lychd
make install
make lint format-check type-check
make test-ci
```

Frontend-only work also needs Node from `.nvmrc` and `make frontend-install`, then the checks in
[CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#setup-and-commands).

Claim one open issue before changing a shared contract. From **2 November 2026**, ordinary pull
requests target `dev`; until then, follow the
[current collaboration phase](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#branches-and-everyday-collaboration).

## Alpha status in one glance

| Scenario | Answer now |
| --- | --- |
| CLI bootstrap | Partial — see State of Work |
| Local text chat | Partial — retained receipts; general quality pending |
| Browser safety | Loopback only |
| Full Summoning on a real host | Not yet supported end to end |
| Remote IAM / federation / production release | Unsupported or Designed |

Read the matching State of Work section before claiming a capability in an issue, PR, or demo.
