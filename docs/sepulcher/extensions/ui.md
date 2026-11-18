---
title: UI
---

# UI

For a new interactive view, change the compiled client and connect it to the application
operation that owns the data. Start at the
[web contributor guide](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/README.md),
then follow the [controller assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py)
and [page tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py).
Enforce authorization in the operation even when the client hides an unavailable control.
[Frontend](../../adr/15-frontend.md) owns the browser architecture.

To describe a component or score for the host to display, an extension may instead contribute
[observation or inspection data](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py).
[Oculus](../aspects/oculus.md) explains what a declaration establishes and where a view needs
observed activity. The host chooses how to render these descriptions. It accepts no executable
UI plugins, extension HTML, JavaScript, or Svelte imports.
