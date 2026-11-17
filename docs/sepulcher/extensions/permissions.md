---
title: Permissions
---

# Permissions

Permissions govern application actions and scopes. When adding an action, define what is being
requested, who may perform it, and where the owning service checks that authority. Existing [local
access
service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/local_access.py)
and [web access
tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_local_access.py) provide a
concrete boundary to study. Test both an admitted action and refusal, including any change in
authority between admission and effect.

A Sigil carries secret-free identity and bounded authority for an admitted request. It is not an
extension artifact or the credential that authenticated the caller. Registering a descriptor, Tool,
or other contribution does not grant its caller permission. The actual handler must check the real
authority for the requested operation. The [IAM Covenant](../../adr/38-iam.md) owns identity, grants
and revocation; consult it when defining the action's boundary.

Today this is Core integration: the [extension
context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py) does not
expose a permission store. A future extension seam cannot confer a grant merely by naming a scope.
Host or root effects have a separate [Privilege](privileges.md) boundary, even when an application
action initiates them.
