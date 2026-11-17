---
title: Services
---

# Services

A package can contribute typed service requirements to Transmutation. Phoenix's
[contributor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/phoenix/contributor.py)
shows how to project an active [Rune](runes.md) into Quadlet data.

## Follow the Rune into Quadlet data

The contributor requests `ctx.runes.one_or_none(PhoenixSettings)`: no instance returns an empty
contribution; more than one raises an error. Exactly one yields a `QuadletContribution` for one
container and two pod ports. The Rune supplies service name, image, and host ports; Settings
supplies the database user and Phoenix secret reference. Keep credentials out of Rune literals.
The container includes migration-gate dependencies, and Transmuter places host ports on loopback.

This is typed projection data. The [binding workflow](../codex.md#the-rite-of-binding) separately
publishes and reconciles host units. The example proves neither a running service nor telemetry
export; [External Eyes](../aspects/oculus.md#external-eyes) describes that observability boundary.
Phoenix contributes no Animator runtime or CallGrant service.

## Test the complete configuration path

The [integration test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_extension_configuration.py)
uses temporary Codex and Crypt directories and separate Python interpreters to exercise Settings,
extension assembly, Rune loading, and Transmuter. It checks the configured service name, image,
ports and Settings-owned database values, along with disabled and inactive cases. The fixture writes
TOML directly: it does not exercise Linux journaled inscription, bind units, or prove database
recovery. Run the focused selection in [Lifecycle](lifecycle.md#finish-a-bounded-contribution),
and add tests for the behavior your contributor owns.
