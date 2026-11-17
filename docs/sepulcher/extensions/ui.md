---
title: UI
---

# UI

The current user interface is a host-owned compiled surface. Add a view or interaction in the
relevant Core client and connect it to an owned application operation; the [web contributor
entry](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/README.md), [web controller
assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py) and [web page
tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py) show the host
boundary. Keep authorization in the operation, even when the interface hides an unavailable action.
The [Frontend Covenant](../../adr/15-frontend.md) owns the browser boundary.

Some extension contributions can provide bounded data descriptors for host presentation. For
example, [inspection and observation
registrations](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py)
expose constrained descriptions; [Oculus](../aspects/oculus.md) explains their meaning and limits.
Such data does not register executable behavior or establish runtime activity.

A generic custom UI plugin is not available. Extensions cannot supply arbitrary HTML, JavaScript, or
Svelte imports to the host surface. The current route for a new interactive surface is a Core change
with its own tests, not a registration shim. An accepted future seam must preserve the host's
rendering and authority boundaries.
