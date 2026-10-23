"""Close narrow ORM-created PostgreSQL fixtures over their actual FK referents."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Table


def with_referenced_tables(tables: Iterable[Table]) -> list[Table]:
    """Keep the requested tables and every transitive referenced table exactly once."""
    closed = list(dict.fromkeys(tables))
    seen = set(closed)
    for table in closed:
        references = {foreign_key.column.table for foreign_key in table.foreign_keys}
        for referenced in sorted(references, key=lambda item: item.key):
            if referenced not in seen:
                closed.append(referenced)
                seen.add(referenced)
    return closed
