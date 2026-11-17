---
title: Privileges
---

# Privileges

Privileges govern host or root effects. When a contribution needs such an effect, integrate with the
owned [privilege
service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/privilege.py),
define the precise request and refusal, and test the boundary using the [privilege service
tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_privilege.py).
The [Privilege Covenant](../../adr/10-privilege.md) owns the authorization and recovery law for
these effects.

An application [permission](permissions.md) answers whether an actor may request an action; it does
not automatically authorize the host effect. The effect handler must check the authority actually
presented to it. Likewise, registration in any extension store is not a privilege grant.

There is no generic privilege registration store in the current [extension
context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py). Additions
currently require Core integration and focused verification. The accepted future extension seam
should be read within the Covenant, not as instructions for an extension to run arbitrary privileged
code. Where an effect generates runtime evidence, its owner records it;
[Oculus](../aspects/oculus.md) describes the current observation surface.
