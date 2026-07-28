"""pin immutable Pattern manifests to Runs

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-29 00:00:00.000000

Existing pre-pin rows receive an explicit legacy-unversioned marker. It is not a
claim that they executed the current registry revision.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["data_downgrades", "data_upgrades", "downgrade", "schema_downgrades", "schema_upgrades", "upgrade"]

revision = "0002"
down_revision = "0001"
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
    """Add the durable Pattern snapshot."""
    op.add_column(
        "run",
        sa.Column(
            "pattern_manifest",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def data_upgrades() -> None:
    """Mark existing rows honestly as unversioned rather than guessing a revision."""
    op.execute(
        """
        UPDATE run
        SET pattern_manifest = jsonb_build_object(
            'schema_version', 0,
            'key', workflow_name,
            'revision', 'legacy-unversioned',
            'checkpoint_schema', 'unknown',
            'nodes', '[]'::jsonb,
            'edges', '[]'::jsonb,
            'digest', NULL
        )
        WHERE pattern_manifest = '{}'::jsonb
        """
    )
    op.alter_column("run", "pattern_manifest", server_default=None)


def data_downgrades() -> None:
    """No standalone data downgrade is required."""


def schema_downgrades() -> None:
    """Remove the Pattern snapshot."""
    op.drop_column("run", "pattern_manifest")
