---
title: Commands
---

# Commands

To add a Pulse operation, start with the service that owns its inputs, effects, and errors.
Expose it through an existing Core verb in the
[CLI commands](https://github.com/hexanomicon/lychd/blob/main/src/lychd/cli/commands.py)
and command assembly. Follow the [CLI tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py)
for invocation and refusal. An operation that touches protected data needs the caller's current
[permission](permissions.md). A host effect also goes through its [privilege](privileges.md) owner,
which records the outcome.

The Pulse's root grammar is closed. A new root verb requires a decision in the
[CLI Covenant](../../adr/19-cli.md). Its future extension route is a typed operation under a
host-owned verb. The current [extension context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py)
provides no hook for registering commands or Click callbacks.
