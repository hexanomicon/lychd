---
title: Permissions
---

# Permissions

Someone who can inspect a market observation may still lack permission to delete it.
Follow those two operations through the [Scavenger controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/api/scavenger.py).
Reading requires `altar:read`. Deletion requires `runs:cancel` and a current decision about
this actor and observation. The [controller tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_scavenger.py)
include revocation during a read and a separate denial at deletion.

For a new action, name the actor, resource, and effect. Apply the
[scope guard](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/guards.py)
to the authenticated caller's Sigil. Have the owning service check current authority on the
exact operation, including after a wait. Exercise both admission and refusal. The credential
authenticates the caller. The Sigil carries bounded claims without that secret.

Add application actions in Core. The [extension context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py)
has no permission store. [IAM](../../adr/38-iam.md) owns grants and revocation. If the action
also changes the host, follow [Privileges](privileges.md) for the additional effect boundary.
