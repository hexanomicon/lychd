"""add the durable Run delivery outbox

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-01 00:00:00.000000

Legacy nonterminal Runs cannot reveal whether their current hop is fresh or resumed.
The migration therefore refuses that state instead of fabricating delivery semantics;
historical terminal Runs remain historical and receive no synthetic delivery rows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID, DateTimeUTC
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["data_downgrades", "data_upgrades", "downgrade", "schema_downgrades", "schema_upgrades", "upgrade"]

revision = "0004"
down_revision = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    data_upgrades()
    schema_upgrades()


def downgrade() -> None:
    data_downgrades()
    schema_downgrades()


def schema_upgrades() -> None:
    """Create the durable publication record for exact Run delivery hops."""
    op.create_table(
        "run_delivery",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("run_id", GUID(length=16), nullable=False),
        sa.Column("enqueue_seq", sa.Integer(), nullable=False),
        sa.Column("queue_name", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("resume", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("state", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("publish_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("published_at", DateTimeUTC(timezone=True), nullable=True),
        sa.Column("claimed_at", DateTimeUTC(timezone=True), nullable=True),
        sa.Column("settled_at", DateTimeUTC(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('held', 'pending', 'published', 'claimed', 'settled')",
            name="ck_run_delivery_state",
        ),
        sa.CheckConstraint(
            "publish_attempts >= 0",
            name="ck_run_delivery_publish_attempts_nonnegative",
        ),
        sa.CheckConstraint(
            "enqueue_seq >= 0",
            name="ck_run_delivery_enqueue_seq_nonnegative",
        ),
        sa.CheckConstraint(
            "priority BETWEEN 0 AND 100",
            name="ck_run_delivery_priority_range",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["run.id"],
            name="fk_run_delivery_run_id_run",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_run_delivery"),
        sa.UniqueConstraint(
            "run_id",
            "enqueue_seq",
            name="uq_run_delivery_run_enqueue_seq",
        ),
    )
    op.create_index(
        "ix_run_delivery_state_queue_name",
        "run_delivery",
        ["state", "queue_name"],
        unique=False,
    )
    op.create_index(
        "uq_run_delivery_one_active",
        "run_delivery",
        ["run_id"],
        unique=True,
        postgresql_where=sa.text("state <> 'settled'"),
    )


def data_upgrades() -> None:
    """Refuse to guess delivery mode for legacy work that is still active."""
    # Held through the Alembic transaction: an old writer cannot insert or
    # reactivate a Run after the refusal check and before the outbox exists.
    op.execute("LOCK TABLE run IN ACCESS EXCLUSIVE MODE")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM run
                WHERE status NOT IN ('done', 'failed', 'cancelled')
            ) THEN
                RAISE EXCEPTION
                    'LychD migration 0004 requires all nonterminal Runs to be drained';
            END IF;
        END
        $$
        """
    )


def data_downgrades() -> None:
    """Refuse to discard exact delivery authority while any Run is live."""
    op.execute("LOCK TABLE run IN ACCESS EXCLUSIVE MODE")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM run
                WHERE status NOT IN ('done', 'failed', 'cancelled')
            ) THEN
                RAISE EXCEPTION
                    'LychD migration 0004 downgrade requires all nonterminal Runs to be drained';
            END IF;
        END
        $$
        """
    )


def schema_downgrades() -> None:
    """Remove the delivery outbox without changing parent Runs."""
    op.drop_index("uq_run_delivery_one_active", table_name="run_delivery")
    op.drop_index("ix_run_delivery_state_queue_name", table_name="run_delivery")
    op.drop_table("run_delivery")
