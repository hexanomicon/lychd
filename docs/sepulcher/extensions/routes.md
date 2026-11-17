---
title: Routes
---

# Routes

A route exposes an application operation over HTTP. Add one today in Core: define the controller and
its request and response boundaries alongside existing [web
controllers](https://github.com/hexanomicon/lychd/tree/main/src/lychd/interface/web/), then wire it
into [application assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py). The
[app factory tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_app_factory.py)
and the relevant controller tests show how to check assembly and behavior. Check authorization at
the operation boundary as well as transport input; see [Permissions](permissions.md).

Routes are currently hardwired in the application and controllers. The [extension
context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py) has no
route hook, so a registration shim cannot add an endpoint. An accepted extension seam is not an
executable route recipe. Do not interpret a registered descriptor or an inspection as a network
endpoint or a grant to call it.

Where an operation produces runtime activity, the owning service supplies evidence.
[Oculus](../aspects/oculus.md) describes the narrow declarations and inspections currently
available; a route or graph description does not establish that an operation ran. Follow the
existing controller's error and access tests for the precise refusal the new operation needs.
