---
title: Models
---

# Models

A persistent model belongs to Core's database schema. Follow an existing [UUIDBase
model](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/models/naming.py), place the new
mapping with the owned models, and import it in the explicit [model
catalogue](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/models/__init__.py). The
[migration
environment](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/env.py) imports
that catalogue to populate Alembic metadata; a new file alone is not discovered. Provide the
corresponding [Alembic
migration](https://github.com/hexanomicon/lychd/tree/main/src/lychd/db/migrations/versions/). Verify
schema evolution with the focused [migration generation
tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_migration_generation.py)
and the relevant database integration tests. The [Persistence Covenant](../../adr/06-persistence.md)
owns the persistence boundary.

There is no model store in the current [extension registration
context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py). Importing
a model or adding a registration does not give an extension authority over migrations. Schema
changes need the owned Core and migration path; a future contribution seam is not a current package
API.

Define ownership, lifecycle and access along with the table. A stored row is not an authorization
decision: the operation that reads or writes it must enforce its own authority. Use the application
action's [permission boundary](permissions.md), and preserve the provenance and recovery obligations
of the data concerned.
