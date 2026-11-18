---
title: Privileges
---

# Privileges

An application [permission](permissions.md) can let someone request a service transition.
The host still has to decide whether that exact transition is allowed. For a working example,
follow a request into the [Host Reactor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/reactor.py).
It takes custody of a typed intent, rechecks it against host state, and records the observed
outcome. The [Reactor tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_reactor.py)
exercise refusal, crash recovery, and the case where an uncertain outcome fences later effects.

The [privilege service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/privilege.py)
has a narrower job. It prepares the handshakes directory and checks its owner and mode.
Its [tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_privilege.py)
cover that directory boundary.

A new host effect requires a Core change. Define its closed request, trusted producer and
consumer, configuration owner, refusal, recovery, and evidence under the
[Privilege Covenant](../../adr/10-privilege.md). The current
[extension context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py)
has no privilege store. Package selection grants no host authority.
