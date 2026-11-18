---
title: Routes
---

# Routes

To expose an application operation over HTTP, follow a Core controller such as
[Scavenger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/api/scavenger.py).
Declare the request, response, and required scopes on the handler. Register the controller in
[application assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py).
The [Scavenger tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_scavenger.py)
exercise its published OpenAPI shape, accepted requests, and operation-specific refusals.
The [app factory tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_app_factory.py)
exercise the assembled Host, authentication, Origin, and CSRF boundaries through Atlas.

Validate transport input at the controller and enforce current
[permission](permissions.md) at the operation. Where the service emits runtime activity, it owns
the evidence. [Oculus](../aspects/oculus.md) explains the distinction between a declaration
a reader can inspect and an observed event. The current
[extension context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py)
provides no HTTP route hook.
