---
title: Bindings
icon: material/link-lock
---

# :material-link-lock: Bindings

Bindings are the Altar's user-facing configuration surface.

They reflect the **[Codex](../../sepulcher/codex.md)** without replacing it as the source of truth. The purpose is to make important connections and policies visible from the interface.

Bindings expose safe handles for:

- provider and Portal references
- secret names, not secret values
- identity and Sigil bindings
- privacy and egress policy
- approval and autonomy policy
- Altar preferences
- safe links to the underlying Codex locations

Bindings should make the system legible without teaching users to edit generated artifacts or bypass the Codex.

Bindings are the top-level settings instrument. Per-session controls such as temperature, local behavior, pinned context, or a Coven request may appear in the [Altar](./index.md) session rail, but durable provider, policy, identity, and preference surfaces belong here.
