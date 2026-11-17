---
title: Implementation
---

# Implementation

Start with [Choosing a Home](choosing-a-home.md) for application design and acceptance, and the [Composition portfolio](index.md) for contracts and examples. This guide follows an accepted design into source. Acceptance, implementation, explicit selection and assembly, and evidenced delivery are separate steps; [State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the last.

Compositions currently integrate through native Core source. This is not a Crypt contribution surface: adding a directory or Markdown contract does not activate an application, and there is no universal Composition registration API.

Put application records and contracts, policy, finish judgment, and any Pattern catalogue under `src/lychd/compositions/<identity>/`. API and client code project those semantics; they should not acquire the application's judgment. Follow the [identity, revision, and retirement contract](../adr/28-workflow.md#composition-identity-revision-and-retirement) when evolving an accepted application. Shared Aspect capabilities do not establish its identity.

[Creation investigation](creation/index.md) supplies one current source journey. Its Composition `creation.investigation`, revision 2, is distinct from its Pattern `creation.investigate@2`. These files describe that implementation, rather than a scaffold every Composition must adopt:

| Responsibility | Creation's source |
| --- | --- |
| Typed values | [schemas.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/creation/schemas.py) |
| Application policy, service, and AgentSpecs | [services.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/creation/services.py) |
| Exact serial Workflow construction | [workflow.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/creation/workflow.py) |
| Explicit selection and assembly | [`_build_creation` in `altar_services.py`](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/altar_services.py) |

That builder composes `DbCreationStore`, `LocalCreationPolicy`, `InvestigationService`, the Workflow, and agents only when `settings.weaver.creation` selects Creation. Its current assembly requires PostgreSQL, local credentials, and the built-in registry; omission provides no Creation service. Those are Creation's conditions, not general authoring prerequisites. Its [API controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/api/creation.py) combines protected route guards with service-level object and action checks, and [app.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py) lists the controller explicitly. Use the [routes](../sepulcher/extensions/routes.md) and [permissions](../sepulcher/extensions/permissions.md) guides when adding that boundary.

Use [Patterns](../sepulcher/extensions/patterns.md) and [Agents](../sepulcher/extensions/agents.md) for the execution definitions, and [UI](../sepulcher/extensions/ui.md) for a client projection.

Persistence is conditional. When an application needs SQLAlchemy tables, place them in `src/lychd/db/models`, include them in the explicit model catalogue, and follow the [models and migrations guide](../sepulcher/extensions/models.md). Creation retains database behavior in `src/lychd/db/creation.py` and tables in `src/lychd/db/models/creation.py`. A document or client application need not adopt its database, service, Workflow, HTTP, or UI shape.

Verify the boundary you actually introduce: refusal, current authority, duplicate or replay behavior, and cancellation or unknown recovery where applicable. Creation's [unit](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_creation.py), [web](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_creation.py), and [PostgreSQL integration](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_creation_postgres_vertical.py) tests are examples, not a universal checklist. Keep delivery claims within [Creation's evidence envelope](../state-of-the-work.md#smith-forge-promotion); focused worker histories do not establish live-broker or process-death recovery.
