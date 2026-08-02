"""add deterministic preauthorization priority

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-02 00:00:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["downgrade", "upgrade"]

revision = "0005"
down_revision = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Give overlapping standing authority a deterministic operator-owned order."""
    op.add_column(
        "codex_preauthorization",
        sa.Column("priority", sa.Integer(), server_default=sa.text("50"), nullable=False),
    )
    op.create_check_constraint(
        "priority_range",
        "codex_preauthorization",
        "priority BETWEEN 0 AND 100",
    )


def downgrade() -> None:
    """Remove explicit ordering while retaining all preauthorization rows."""
    op.drop_constraint(
        "priority_range",
        "codex_preauthorization",
        type_="check",
    )
    op.drop_column("codex_preauthorization", "priority")
