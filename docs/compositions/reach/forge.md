---
title: Forge
icon: material/source-repository
---

# Forge

Read a bounded issue conversation or prepare a timeline comment about a release. Forge keeps
repository correspondence separate from permission to change or execute the software discussed.

The current `ForgeTarget` selects a local connection, repository and positive `issue_number`.
`ConnectedPolicy` admits exact targets and read/send operations. [GitHub](connected-work/github.md)
is the implemented provider: its request builder accepts an exact `owner/name` repository and
prepares bounded comment reads or a new issue/PR timeline comment through GitHub.com routes.

A timeline comment is not a diff review, formal approval, merge, code write, release or workflow
run. App installation and delegated user access have separate authority requirements; the offline
builder authenticates neither. The [GitHub study](connected-work/github.md) owns the proposed
installation, event, permission and reconciliation contract.

## Radicle boundary

Radicle remains unsupported by the request builder. Its node/key identity, repository RID and
issue/patch objects need their own provider profile and may need a separate target schema.
Replacing a GitHub hostname would not establish that contract. Local acceptance and peer
replication would also be different receipt claims. The
[Radicle user guide](https://radicle.dev/guides/user) is the external reference, not compatibility
evidence for this implementation.

[Connected preparation](connected-work/preparation.md) places a GitHub comment beside email and
chat in a finite WUPHF plan. It prepares every target before returning a result, without code
execution, transport or a second workflow engine.

[Reach](index.md)
