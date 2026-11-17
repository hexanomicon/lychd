---
title: Commands
---

# Commands

The Pulse uses a closed root command grammar. To add behavior today, implement the owned operation
behind an existing public verb in Core's [CLI
commands](https://github.com/hexanomicon/lychd/blob/main/src/lychd/cli/commands.py) and its
assembly, following the [CLI
tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py) for invocation and
refusal. A change to the root grammar requires an explicit amendment of the CLI Covenant. Define the
operation's inputs, effects and errors at its owning service; a command is an entry point, not
authority to bypass that service. The [CLI Covenant](../../adr/19-cli.md) owns the grammar and
safeguards.

The current [extension
context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py) exposes no
command store. An extension cannot attach a Click callback to the root grammar. The accepted future
direction is typed operations under a host-owned verb, not arbitrary extension callbacks; that seam
is not an executable package API today.

For commands that affect protected application data or the host, enforce the corresponding
[permission](permissions.md) or [privilege](privileges.md) at the real operation boundary. Test
denial as well as success, and use the effect owner's execution evidence rather than treating the
presence of a command as proof it ran.
