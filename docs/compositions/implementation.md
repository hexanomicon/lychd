---
title: Implementation
---

# Implementation

Where does an accepted application become something a developer can run? Follow
[Creation investigation](creation/index.md) from its application rules to the
[setting that enables it](creation/index.md#current-local-authority). If you are still deciding who owns the work, start with
[Choosing a Home](choosing-a-home.md). The [portfolio](index.md) holds the accepted contracts.

## Find the application in Core

Creation owns the question under investigation, the candidate answer and the attributed verdict.
Its Composition identity is `creation.investigation`, revision `2`. The serial work that
produces the candidate and checks it has its own Pattern, `creation.investigate@2`.

| Question | Where to look in Creation |
| --- | --- |
| What can someone submit, read back or continue? | [schemas.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/creation/schemas.py) defines the typed request and case records. |
| Who may act on this case, and what counts as a result? | [services.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/creation/services.py) holds the application policy, investigation service and AgentSpecs. |
| In what order do the constructor and verifier work? | [workflow.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/creation/workflow.py) builds the serial Workflow. |
| What turns this design on for a particular installation? | [`_build_creation`](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/altar_services.py) checks the selection and assembles the pieces. |

Open the builder and follow the early return. With no `settings.weaver.creation` selection,
it returns no Creation service and leaves the Workflow registry as it found it. When selected,
Creation requires PostgreSQL, local credentials and the built-in registry. The builder joins
`DbCreationStore` and `LocalCreationPolicy` to `InvestigationService`, registers the Workflow
and its active revision, and installs its Agent builders. The
[assembly test](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_creation.py)
exercises both settings without opening a database.

For another native application, put the records, policy, finish judgment and any Pattern catalogue
under `src/lychd/compositions/<identity>/`. Compositions enter through explicit Core assembly.
There is no universal registration API or Crypt loader for these directories. A client or document application can have a different
shape. Add a database, Workflow or HTTP surface when its work requires one. Reusing an Aspect leaves the application responsible for its identity
and [revision and retirement decisions](../adr/28-workflow.md#composition-identity-revision-and-retirement).

## Test the part that could fail

Suppose a worker stops after storing a candidate and before a verifier rules on it. What should
survive? Creation's [PostgreSQL integration test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_creation_postgres_vertical.py)
injects a failure just after adoption. On restart the original Run is marked failed and the case
still has its candidate. An explicitly authorized continuation gets a new Run. The verifier can
reject that same candidate even though the second Run finishes successfully. This is a simulated
interruption in a worker test. [State of Work](../state-of-the-work.md#smith-forge-promotion)
records which broker and process-death histories still need evidence.

For other changes, start where the behavior lives.

- For an HTTP change, follow the [controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/api/creation.py) from its explicit inclusion in [app.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py) to the service check for the case and action. The [web tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_creation.py) exercise refusal and duplicate input. [Routes](../sepulcher/extensions/routes.md) and [Permissions](../sepulcher/extensions/permissions.md) cover adding this surface.
- For a storage change, Creation's store lives in `src/lychd/db/creation.py` and its tables in `src/lychd/db/models/creation.py`. Include new SQLAlchemy tables in the explicit model catalogue and follow [Models and migrations](../sepulcher/extensions/models.md).
- For a new execution step, follow [Patterns](../sepulcher/extensions/patterns.md) and [Agents](../sepulcher/extensions/agents.md). If the change is how a person sees the result, use the [UI guide](../sepulcher/extensions/ui.md). The API and client present the application's verdict.

Choose a test with an observable consequence for your change, such as a refused action, a replay,
a cancellation or a result left uncertain by interruption. The
[portfolio delivery record](../state-of-the-work.md#composition-portfolio-delivery) distinguishes
a design the project has accepted from an application someone can select and run.
