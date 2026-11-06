"""Metadata parity for the generated naming migration and refusal to erase history."""

from __future__ import annotations

import importlib
from typing import Any, cast

import pytest
from sqlalchemy import Table

from lychd.db.models.naming import NamingRecord
from tests.unit.db.test_dictation import Operations, columns, constraints


def test_generated_migration_parity_and_guarded_downgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("lychd.db.migrations.versions.0027_primus_naming")
    operations = Operations()
    monkeypatch.setattr(module, "op", operations)
    module.upgrade()
    assert module.revision == "0027"
    assert module.down_revision == "0026"
    model = cast("Table[Any]", NamingRecord.__table__)
    assert isinstance(model, Table)
    assert columns(operations.tables[0]) == columns(model)
    assert constraints(operations.tables[0]) == constraints(model)
    assert not model.foreign_keys
    operations.sql.clear()
    module.downgrade()
    assert "ACCESS EXCLUSIVE" in operations.sql[2]
    assert "IF EXISTS" in operations.sql[3]
    assert "RAISE EXCEPTION" in operations.sql[3]
