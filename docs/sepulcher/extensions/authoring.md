---
title: Extension authoring
icon: material/toy-brick-plus-outline
---

# Authoring an extension

Phoenix is an optional built-in extension that registers typed configuration and contributes a
container definition to Transmutation. Follow it from selection through registration, Rune
loading, Quadlet projection, and tests to learn where a contribution belongs and what evidence
a change needs.

The [extension index](index.md) maps the Extension Domains. [ADR 05](../../adr/05-extensions.md)
owns admission and compatibility; [ADR 12](../../adr/12-configuration.md) owns configuration.
This guide follows one package through those contracts.

First follow the contribution guide's
[Setup and Commands](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#setup-and-commands),
then run this focused test selection from the checkout:

```sh
make test PYTEST_TARGETS="tests/integration/test_extension_configuration.py tests/unit/extensions" N=0
```

The configuration integration test creates its own temporary Codex and Crypt directories and
runs separate Python interpreters. The snippets below explain that fixture's selection,
configuration, and projection path. In an installation, `lychd.toml` and Rune documents live
beneath the operator's Codex; [Codex](../codex.md) owns that operating workflow.

## Select and register Phoenix

In the test's temporary Codex, `lychd.toml` selects Phoenix with:

```toml
[extensions]
builtins = ["observability/phoenix"]
crypt = []
```

Both selections default to empty. A built-in must have an explicit entry in the
[catalogue](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/catalog.py);
adding a directory alone does not make it selectable.

Read Phoenix's
[registration shim](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/phoenix/register.py).
Its synchronous `register(context: ExtensionRegistrationContext) -> None` hook lazily imports
`ObservabilityConfig`, `PhoenixSettings`, and `PhoenixQuadletContributor`, then registers them:

```python
context.runes.add_schema(ObservabilityConfig)
context.runes.add_schema(PhoenixSettings)
context.transmutation.add_contributor(PhoenixQuadletContributor())
```

After registration, the host marks these contributions with
`builtin:observability/phoenix`. This Registrant identity lets a reader trace them back to the
selected package while each receiving store enforces its own contract. Selection makes Phoenix
available during assembly. An active Rune is still needed before it contributes a container.

## Give the contribution a typed Rune

Phoenix's
[configuration module](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/phoenix/config.py)
defines a branch and a leaf. `ObservabilityConfig` has
`path_fragment = Path("observability")`; `PhoenixSettings` adds `Path("phoenix")`, producing the
relative path `observability/phoenix`. The branch cannot own TOML; the leaf can.

A Rune is a frozen, validated top-level TOML instance. The fixture writes its active document at
`<Codex>/runes/observability/phoenix/desk.toml`. This example shows the same configuration shape
with the default image:

```toml
name = "desk-eye"
ui_port = 16006
otlp_port = 14317

[quadlet]
image = "docker.io/arize-ai/phoenix:latest"
```

`PhoenixSettings` rejects unknown fields and validates `name` as a safe service identity. The
example overrides the default name and ports; its image line repeats the typed Quadlet setting's
default. It is a configuration example, with no image pull or live-service receipt. The loader
derives `source_file` from the document's path; do not put that field in TOML.

The schema also supplies a `sample_template`. Its rendered sample is inactive, identified by the
exact first nonempty line:

```toml
# lychd: sample-rune
```

Activation requires a configured document with that marker removed. A selected Phoenix package
with an absent or marked sample Rune still produces no Phoenix container. [Codex](../codex.md)
owns Rune and binding operations.

## Follow the Rune into Quadlet data

Read the
[Phoenix contributor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/phoenix/contributor.py)
next. It requests `ctx.runes.one_or_none(PhoenixSettings)`. No instance produces an empty
contribution; more than one raises an error.

With exactly one active instance, the contributor creates typed `QuadletContribution` data for
one Phoenix container and two pod ports. Trace each value to its source: the Rune supplies
service name, image, and host ports; Settings supplies the database user and Phoenix secret
reference. The container includes migration-gate dependencies, and Transmuter places the host
ports on loopback.

This output is projection data. The [binding workflow](../codex.md#the-rite-of-binding) separately
owns publication and host reconciliation. Follow [External Eyes](oculus.md#external-eyes) for
Phoenix's observability boundary: this example establishes neither a running Phoenix service nor
an application telemetry export path. Phoenix contributes no Animator runtime or CallGrant service.

## Test the complete configuration path

The
[configuration integration test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_extension_configuration.py)
follows the real Settings, extension manager, Rune loader, and Transmuter across separate Python
interpreters. Its assertions cover:

- Default-disabled selection leaves the Phoenix shim unimported.
- Selected Phoenix with an inactive sample has the exact schemas, contributor, and provenance.
- An active Rune is frozen, retains its exact `source_file`, and projects its configured service
  name, image, ports, and Settings-owned database values.
- Editing the Settings file leaves the current process's cached generation unchanged.
- A fresh disabled process produces no Phoenix contribution while the Rune and representative
  retained data bytes survive.
- An unselected Crypt shim that would fail if imported remains unimported.

The fixture writes TOML directly. It does not execute the writer's Linux journaled inscription,
bind units, or prove database recovery. Detailed registration collisions and import failures
belong to the
[admission tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_admission.py).
For a contribution that supplies an Animator, the
[Crypt vertical test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_crypt_extension_vertical.py)
continues through its separate adapter and Dispatcher contracts.

## Apply the registration contract in Crypt

A private package is selected explicitly:

```toml
[extensions]
builtins = []
crypt = ["my-private-organ"]
```

Its exact shim is `PATH_EXTENSIONS_DIR/my-private-organ/register.py`; [Crypt](../crypt.md) explains
the source location. An activation ID must be canonical and POSIX-relative, without traversal or
aliases. The manager resolves only the selected `register.py`, with no environment or entry-point
scan.

The shim uses the same synchronous `register(context)` contract and returns `None`. It may import
relative siblings within its synthetic package namespace; adjacent unselected packages remain
unimported. Crypt code is trusted, runs in process, and shares memory. This pre-v1 path accepts
coupling to internal refactors. Built-ins release with Core; a versioned independent extension API
remains future work under [ADR 05](../../adr/05-extensions.md#7-extension-compatibility-tiers).

## Finish a bounded contribution

Finish by testing a new process generation. `get_settings()` and `get_extensions()` retain the
current generation, and registration stores seal after assembly; edits to code, dependencies,
contribution contracts, or selection require restart or replacement. Removing Phoenix's selector
in the new process removes its contribution while leaving retained Runes and storage alone.
This guide does not implement installation, uninstallation, rollback, or automated Evolution.
[State of Work](../../state-of-the-work.md#extension-activation-contributions) records delivery.

Change the owned schema, registration, or contributor together with a test of the affected
behavior, then rerun the focused selection above. Follow the
[contribution quality checks](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#quality-checks)
for the applicable lint, format, type, and repository gates. Describe the boundary the change
establishes and the evidence that supports it. Follow the
[current collaboration phase](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#branches-and-everyday-collaboration)
for branch and submission procedure.
