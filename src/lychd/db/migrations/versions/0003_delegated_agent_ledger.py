"""retain delegated-agent jobs and semantic events

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-29 00:00:00.000000
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID, DateTimeUTC
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["data_downgrades", "data_upgrades", "downgrade", "schema_downgrades", "schema_upgrades", "upgrade"]

revision = "0003"
down_revision = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            schema_upgrades()
            data_upgrades()


def downgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            data_downgrades()
            schema_downgrades()


def schema_upgrades() -> None:
    """Create the durable job identity and append-only semantic event ledger."""
    op.add_column("run", sa.Column("delegated_job_id", sa.String(length=128), nullable=True))
    op.create_index("ix_run_delegated_job_id", "run", ["delegated_job_id"], unique=False)

    op.create_table(
        "delegated_agent_job",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", GUID(length=16), nullable=False),
        sa.Column("runtime", sa.String(length=128), nullable=False),
        sa.Column("profile", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request", JSONB(), nullable=False),
        sa.Column("result", JSONB(), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["run.id"],
            name="fk_delegated_agent_job_run_id_run",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_delegated_agent_job"),
        sa.UniqueConstraint("job_id", name="uq_delegated_agent_job_job_id"),
        sa.UniqueConstraint("request_id", name="uq_delegated_agent_job_request_id"),
    )
    op.create_index("ix_delegated_agent_job_run_id", "delegated_agent_job", ["run_id"], unique=False)
    op.create_index("ix_delegated_agent_job_runtime", "delegated_agent_job", ["runtime"], unique=False)
    op.create_index("ix_delegated_agent_job_status", "delegated_agent_job", ["status"], unique=False)

    op.create_table(
        "delegated_agent_event",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("job_record_id", GUID(length=16), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_record_id"],
            ["delegated_agent_job.id"],
            name="fk_delegated_agent_event_job_record_id_delegated_agent_job",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_delegated_agent_event"),
        sa.UniqueConstraint("event_id", name="uq_delegated_agent_event_event_id"),
        sa.UniqueConstraint(
            "job_record_id",
            "seq",
            name="uq_delegated_agent_event_job_seq",
        ),
    )
    op.create_index(
        "ix_delegated_agent_event_job_record_id",
        "delegated_agent_event",
        ["job_record_id"],
        unique=False,
    )


def schema_downgrades() -> None:
    """Remove delegated-agent persistence without touching parent Runs."""
    op.drop_index("ix_delegated_agent_event_job_record_id", table_name="delegated_agent_event")
    op.drop_table("delegated_agent_event")
    op.drop_index("ix_delegated_agent_job_status", table_name="delegated_agent_job")
    op.drop_index("ix_delegated_agent_job_runtime", table_name="delegated_agent_job")
    op.drop_index("ix_delegated_agent_job_run_id", table_name="delegated_agent_job")
    op.drop_table("delegated_agent_job")
    op.drop_index("ix_run_delegated_job_id", table_name="run")
    op.drop_column("run", "delegated_job_id")


def data_upgrades() -> None:
    """No legacy delegated-agent rows exist before this migration."""


def data_downgrades() -> None:
    """No standalone data downgrade is required."""
