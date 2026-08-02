"""separate Rune presence from operator enablement

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-02 00:10:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["downgrade", "upgrade"]

revision = "0006"
down_revision = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Track whether Rune-owned authority exists in the current source generation."""
    op.add_column(
        "codex_preauthorization",
        sa.Column("source_present", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )


def downgrade() -> None:
    """Collapse source presence back into the legacy enabled flag."""
    op.execute(
        """
        UPDATE codex_preauthorization
        SET enabled = false
        WHERE granted_by = 'codex:rune' AND source_present = false
        """
    )
    op.drop_column("codex_preauthorization", "source_present")
