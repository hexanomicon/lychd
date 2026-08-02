"""retain Nexus swap admission identities

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-02 01:00:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID, DateTimeUTC
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["downgrade", "upgrade"]

revision = "0007"
down_revision = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create the durable request-id admission fence for operator transitions."""
    op.create_table(
        "nexus_swap_request",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_nexus_swap_request"),
        sa.UniqueConstraint("request_id", name="uq_nexus_swap_request_request_id"),
    )


def downgrade() -> None:
    """Remove only an empty Nexus admission fence; retained identities are safety state."""
    op.execute(sa.text("LOCK TABLE nexus_swap_request IN ACCESS EXCLUSIVE MODE"))
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM nexus_swap_request LIMIT 1) THEN
                    RAISE EXCEPTION
                        'LychD migration 0007 downgrade requires an empty nexus_swap_request fence';
                END IF;
            END
            $$;
            """
        )
    )
    op.drop_table("nexus_swap_request")
