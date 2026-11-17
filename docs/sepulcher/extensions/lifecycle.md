---
title: Lifecycle
---

# Lifecycle

Select a package explicitly and register its contributions during assembly. Built-ins require an
entry in the [catalogue](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/catalog.py);
a directory alone is not selectable. For example, the integration fixture selects Phoenix:

```toml
[extensions]
builtins = ["observability/phoenix"]
crypt = []
```

Both lists default to empty. The complete Phoenix
[registration shim](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/phoenix/register.py)
is:

```python
from __future__ import annotations

from lychd.extensions.context import ExtensionRegistrationContext


def register(context: ExtensionRegistrationContext) -> None:
    from lychd.extensions.builtin.observability.phoenix.config import ObservabilityConfig, PhoenixSettings
    from lychd.extensions.builtin.observability.phoenix.contributor import PhoenixQuadletContributor

    context.runes.add_schema(ObservabilityConfig)
    context.runes.add_schema(PhoenixSettings)
    context.transmutation.add_contributor(PhoenixQuadletContributor())
```

The host attributes these registrations to `builtin:observability/phoenix`. Selection makes them
available; an active [Rune](runes.md) is needed to produce the [service](services.md).

## Apply the registration contract in Crypt

A private package is selected explicitly:

```toml
[extensions]
builtins = []
crypt = ["my-private-organ"]
```

Its exact shim is `PATH_EXTENSIONS_DIR/my-private-organ/register.py`; [Crypt](../crypt.md) explains
the source location. The activation ID must be canonical and POSIX-relative, without traversal or
aliases. Only the selected shim is resolved: there is no environment or entry-point scan. Its
synchronous `register(context)` returns `None` and may import relative siblings in its synthetic
package namespace; adjacent unselected packages remain unimported. Crypt Python is trusted,
runs in process, and shares memory. This pre-v1 path accepts coupling to internal refactors;
[ADR 05](../../adr/05-extensions.md) owns trust and compatibility.

## Finish a bounded contribution

Registration stores seal after assembly; `get_settings()` and `get_extensions()` retain the current
process generation. Changes to code, dependencies, contribution contracts, or selection require a
restart or replacement. Removing Phoenix's selector in a new process removes its contribution,
while retaining Runes and storage. It does not implement installation, uninstallation, rollback,
or automated Evolution. See [State of Work](../../state-of-the-work.md#extension-activation-contributions).

Test the affected behavior and a fresh generation. The
[configuration integration test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_extension_configuration.py)
checks default-disabled imports, selected provenance, cached Settings, retained data after disabling,
and that an unselected failing Crypt shim is not imported. The
[admission tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_admission.py)
cover collisions and import failures. Run:

```sh
make test PYTEST_TARGETS="tests/integration/test_extension_configuration.py tests/unit/extensions" N=0
```

Follow the [contribution quality checks](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#quality-checks)
for the applicable gates.
