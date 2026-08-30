"""Static schema and migration contract for the Run delivery outbox."""

from __future__ import annotations

from typing import cast

from sqlalchemy import CheckConstraint, Table, UniqueConstraint

from lychd.db.models import RunDelivery


def test_run_delivery_model_owns_exact_hops_and_publication_state() -> None:
    table = cast("Table", RunDelivery.__table__)
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    checks = {constraint.name for constraint in table.constraints if isinstance(constraint, CheckConstraint)}
    indexes = {str(index.name): index for index in table.indexes}
    foreign_key = next(iter(table.c.run_id.foreign_keys))

    assert ("run_id", "enqueue_seq") in unique_columns
    assert foreign_key.target_fullname == "run.id"
    assert foreign_key.ondelete == "CASCADE"
    assert checks == {
        "ck_run_delivery_state",
        "ck_run_delivery_publish_attempts_nonnegative",
        "ck_run_delivery_enqueue_seq_nonnegative",
        "ck_run_delivery_priority_range",
    }
    active_index = indexes["uq_run_delivery_one_active"]
    assert active_index.unique is True
    assert tuple(column.name for column in active_index.columns) == ("run_id",)
    assert active_index.dialect_options["postgresql"]["where"] is not None
