---
title: Extensions
icon: material/toy-brick-outline
---

# :material-toy-brick-outline: Extensions

Add one concrete capability to LychD, then follow it into configuration, execution, and evidence.
Choose the guide for what you want to contribute. Each names the current integration path:
some use a package registration store; others require a Core change or describe an accepted
contract whose public contribution mechanism remains Designed.

## Choose a contribution

| Guide | Start here to add… |
| --- | --- |
| [Spells](spells.md) | A named semantic action and its implementation. |
| [Patterns](patterns.md) | A workflow lineage and an immutable Scroll revision. |
| [Agents](agents.md) | A typed cognitive step with declared instructions, tools, and results. |
| [Tools](tools.md) | An operation a model or workflow can request under its owner's authority. |
| [Runes](runes.md) | A configuration schema and a validated named instance. |
| [Animators](animators/index.md) | A local or remote capability service, including its [Connector](animators/connectors.md). |
| [Delegation](delegation.md) | An adapter for an external runtime's bounded task and tool loop. |
| [Routes](routes.md) | An HTTP endpoint and its request, response, and authority contract. |
| [Models](models.md) | Persistent database records and their migration path. |
| [Jobs](jobs.md) | Durable background work with explicit settlement and recovery. |
| [Permissions](permissions.md) | Application actions, resource scopes, and permission checks. |
| [Privileges](privileges.md) | A separately authorized privileged host operation. |
| [UI](ui.md) | A supported Altar projection or a reviewed native interface change. |
| [Commands](commands.md) | An operation within the host-owned CLI grammar. |
| [Services](services.md) | A service's physical requirements and supported deployment contribution. |

For a complete first example, follow Phoenix through [Runes](runes.md) and [Services](services.md).
[Codex](../codex.md) remains the operator's guide to configuration as a whole.
To implement a complete application, follow [Composition implementation](../../compositions/implementation.md).

## Select a package

A built-in or private Crypt package enters only through explicit selection and a synchronous
`register(context)` hook. The host attributes each contribution to its Registrant and seals the
assembled generation. Selection supplies registration, while the receiving owner controls use.
[Lifecycle](lifecycle.md) covers the hook, trust, compatibility, restart, and removal boundaries.

A package can contribute to several owners. The [Aspects](../aspects/index.md) map explains those
responsibilities; it is not a catalogue of installable or replaceable plugins.
[ADR 05](../../adr/05-extensions.md) owns extension law, and
[State of Work](../../state-of-the-work.md#extension-activation-contributions) owns current delivery.

Observation belongs beside the contribution it describes: known topology can be projected from
its declaration, while activity comes from the executing owner. Each relevant guide links that
path. [Oculus](../aspects/oculus.md) retains the shared observation contracts and the explicit
integration of external sources.
