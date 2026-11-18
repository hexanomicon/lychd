---
title: Models
---

# Models

To persist a new kind of record, follow an existing
[`UUIDBase` model](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/models/naming.py).
Define who owns the row, who may read or change it, and how it survives or expires. The
[permission](permissions.md) check belongs to the operation that accesses it.

1. Add the mapping to Core's database models and import it in the explicit
   [model catalogue](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/models/__init__.py).
   The [Alembic environment](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/env.py)
   imports this catalogue to obtain the metadata.
2. Supply the corresponding [migration](https://github.com/hexanomicon/lychd/tree/main/src/lychd/db/migrations/versions/).
   Exercise the revision against PostgreSQL. The [Blockworld migration cases](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_migrations_pg.py)
   compare the migrated columns with the ORM models, cycle an empty schema, and check that
   downgrade refuses retained records. Choose cases that cover your revision's data and recovery
   contract. The [revision-generation test](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_migration_generation.py)
   checks the formatting hooks on a new revision file.

The current [extension context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py)
has no model store. Schema evolution follows the Core migration path and the provenance and
recovery obligations of [Persistence](../../adr/06-persistence.md).
