# type: ignore
"""phylactery first light

Revision ID: 0001
Revises:
Create Date: 2026-07-06 00:00:00.000000

Hand-authored first migration for the Phylactery. Creates the pgvector
extension and the seven Wave-1 tables (session, run, step, consent, karma,
soulstone_record, codex_preauthorization) in FK-dependency order.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID, DateTimeUTC
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["data_downgrades", "data_upgrades", "downgrade", "schema_downgrades", "schema_upgrades", "upgrade"]

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
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
    """Schema upgrade migrations go here."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "session",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("sigil_name", sa.String(length=100), nullable=False),
        sa.Column("message_history", JSONB(), nullable=False),
        sa.Column("meta", JSONB(), nullable=False),
        sa.Column("last_run_id", GUID(length=16), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_session"),
    )
    op.create_index("ix_session_sigil_name", "session", ["sigil_name"], unique=False)

    op.create_table(
        "run",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("workflow_name", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("sigil_name", sa.String(length=100), nullable=False),
        sa.Column("intent", JSONB(), nullable=False),
        sa.Column("capability_key", sa.String(length=200), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", DateTimeUTC(timezone=True), nullable=True),
        sa.Column("finished_at", DateTimeUTC(timezone=True), nullable=True),
        sa.Column("session_id", GUID(length=16), nullable=True),
        sa.Column("queue_name", sa.String(length=50), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("enqueue_seq", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("stasis_path", sa.String(length=500), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"], name="fk_run_session_id_session", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_run"),
    )
    op.create_index("ix_run_workflow_name", "run", ["workflow_name"], unique=False)
    op.create_index("ix_run_status", "run", ["status"], unique=False)
    op.create_index("ix_run_session_id", "run", ["session_id"], unique=False)

    op.create_table(
        "step",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("run_id", GUID(length=16), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("node_key", sa.String(length=100), nullable=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"], name="fk_step_run_id_run", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_step"),
        sa.UniqueConstraint("run_id", "seq", name="uq_step_run_seq"),
    )
    op.create_index("ix_step_run_id", "step", ["run_id"], unique=False)

    op.create_table(
        "consent",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("run_id", GUID(length=16), nullable=False),
        sa.Column("tool_name", sa.String(length=200), nullable=False),
        sa.Column("tool_call_id", sa.String(length=100), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("decided_by", sa.String(length=100), nullable=True),
        sa.Column("decided_at", DateTimeUTC(timezone=True), nullable=True),
        sa.Column("preauth_slug", sa.String(length=100), nullable=True),
        sa.Column("expires_at", DateTimeUTC(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"], name="fk_consent_run_id_run", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_consent"),
    )
    op.create_index("ix_consent_run_status", "consent", ["run_id", "status"], unique=False)

    op.create_table(
        "karma",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(), nullable=True),
        sa.Column("meta", JSONB(), nullable=False),
        sa.Column("session_id", GUID(length=16), nullable=True),
        sa.Column("run_id", GUID(length=16), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["session.id"], name="fk_karma_session_id_session", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"], name="fk_karma_run_id_run", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_karma"),
    )
    op.create_index("ix_karma_kind", "karma", ["kind"], unique=False)

    op.create_table(
        "soulstone_record",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("runtime", sa.String(length=50), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("rune_hash", sa.String(length=64), nullable=False),
        sa.Column("spec", JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_bound_at", DateTimeUTC(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_soulstone_record"),
        sa.UniqueConstraint("name", name="uq_soulstone_record_name"),
    )

    op.create_table(
        "codex_preauthorization",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("klass", sa.String(length=20), nullable=False),
        sa.Column("sigil_pattern", sa.String(length=100), nullable=False),
        sa.Column("tool_pattern", sa.String(length=200), nullable=False),
        sa.Column("constraints", JSONB(), nullable=False),
        sa.Column("expires_at", DateTimeUTC(timezone=True), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("uses", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("granted_by", sa.String(length=100), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_codex_preauthorization"),
        sa.UniqueConstraint("slug", name="uq_codex_preauthorization_slug"),
    )


def schema_downgrades() -> None:
    """Schema downgrade migrations go here."""
    op.drop_table("codex_preauthorization")
    op.drop_table("soulstone_record")
    op.drop_index("ix_karma_kind", table_name="karma")
    op.drop_table("karma")
    op.drop_index("ix_consent_run_status", table_name="consent")
    op.drop_table("consent")
    op.drop_index("ix_step_run_id", table_name="step")
    op.drop_table("step")
    op.drop_index("ix_run_session_id", table_name="run")
    op.drop_index("ix_run_status", table_name="run")
    op.drop_index("ix_run_workflow_name", table_name="run")
    op.drop_table("run")
    op.drop_index("ix_session_sigil_name", table_name="session")
    op.drop_table("session")
    # NOTE: the `vector` extension is intentionally NOT dropped on downgrade.


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
