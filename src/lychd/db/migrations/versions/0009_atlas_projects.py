"""retain Atlas Projects and exact mutation receipts

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-06 00:00:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID, DateTimeUTC
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["downgrade", "upgrade"]

revision = "0009"
down_revision = "0008"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add undertaking documents without rewriting Session or Run identities."""
    op.create_table(
        "atlas_project",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("sigil_name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("document", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("creation_digest", sa.String(length=64), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("ck_atlas_project_positive_version")),
        sa.PrimaryKeyConstraint("id", name="pk_atlas_project"),
    )
    op.create_index("ix_atlas_project_sigil_name", "atlas_project", ["sigil_name"])
    op.create_table(
        "atlas_request",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("project_id", GUID(length=16), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["atlas_project.id"], name="fk_atlas_request_project_id_atlas_project", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_atlas_request"),
    )
    op.create_index("ix_atlas_request_project_id", "atlas_request", ["project_id"])


def downgrade() -> None:
    """Refuse erasure of retained operator material while holding both tables locked."""
    op.execute(sa.text("LOCK TABLE atlas_project, atlas_request IN ACCESS EXCLUSIVE MODE"))
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM atlas_project LIMIT 1)
                   OR EXISTS (SELECT 1 FROM atlas_request LIMIT 1) THEN
                    RAISE EXCEPTION
                        'LychD migration 0009 downgrade requires empty atlas_project and atlas_request tables';
                END IF;
            END
            $$;
            """
        )
    )
    op.drop_index("ix_atlas_request_project_id", table_name="atlas_request")
    op.drop_table("atlas_request")
    op.drop_index("ix_atlas_project_sigil_name", table_name="atlas_project")
    op.drop_table("atlas_project")
