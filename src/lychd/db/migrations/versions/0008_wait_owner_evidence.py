"""bind exact wait owners and terminal evidence

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-02 20:30:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["downgrade", "upgrade"]

revision = "0008"
down_revision = "0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add exact Consent ownership and refuse ownerless or evidence-free live truth."""
    op.execute(sa.text('LOCK TABLE "run", consent, delegated_agent_job IN ACCESS EXCLUSIVE MODE'))
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM run WHERE status = 'awaiting_consent' LIMIT 1) THEN
                    RAISE EXCEPTION
                        'LychD migration 0008 cannot infer owners for existing awaiting_consent Runs';
                END IF;
                IF EXISTS (
                    SELECT 1
                    FROM consent
                    WHERE status <> 'pending'
                      AND (decided_by IS NULL OR decided_at IS NULL)
                    LIMIT 1
                ) THEN
                    RAISE EXCEPTION
                        'LychD migration 0008 requires decision receipts for settled Consents';
                END IF;
                IF EXISTS (
                    SELECT 1
                    FROM delegated_agent_job
                    WHERE status IN ('succeeded', 'failed', 'cancelled', 'timed_out', 'lost')
                      AND (
                          result IS NULL
                          OR jsonb_typeof(result) IS DISTINCT FROM 'object'
                          OR result ->> 'job_id' IS DISTINCT FROM job_id
                          OR result ->> 'status' IS DISTINCT FROM status
                      )
                    LIMIT 1
                ) THEN
                    RAISE EXCEPTION
                        'LychD migration 0008 requires exact result evidence for terminal delegated jobs';
                END IF;
            END
            $$;
            """
        )
    )
    op.add_column("run", sa.Column("consent_id", GUID(length=16), nullable=True))
    op.create_index("ix_run_consent_id", "run", ["consent_id"], unique=False)
    op.create_foreign_key(
        "fk_run_consent_id_consent",
        "run",
        "consent",
        ["consent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "waiting_consent_owner",
        "run",
        "status <> 'awaiting_consent' OR consent_id IS NOT NULL",
    )
    op.create_check_constraint(
        "decision_receipt",
        "consent",
        "status = 'pending' OR (decided_by IS NOT NULL AND decided_at IS NOT NULL)",
    )
    op.create_check_constraint(
        "terminal_result",
        "delegated_agent_job",
        "status NOT IN ('succeeded', 'failed', 'cancelled', 'timed_out', 'lost') OR "
        "(result IS NOT NULL "
        "AND jsonb_typeof(result) = 'object' "
        "AND COALESCE(result ->> 'job_id' = job_id, FALSE) "
        "AND COALESCE(result ->> 'status' = status, FALSE))",
    )


def downgrade() -> None:
    """Refuse to erase exact ownership while any Run remains parked on Consent."""
    op.execute(sa.text('LOCK TABLE "run", consent, delegated_agent_job IN ACCESS EXCLUSIVE MODE'))
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM run WHERE status = 'awaiting_consent' LIMIT 1) THEN
                    RAISE EXCEPTION
                        'LychD migration 0008 downgrade requires no awaiting_consent Runs';
                END IF;
            END
            $$;
            """
        )
    )
    op.drop_constraint(
        "terminal_result",
        "delegated_agent_job",
        type_="check",
    )
    op.drop_constraint("decision_receipt", "consent", type_="check")
    op.drop_constraint("waiting_consent_owner", "run", type_="check")
    op.drop_constraint("fk_run_consent_id_consent", "run", type_="foreignkey")
    op.drop_index("ix_run_consent_id", table_name="run")
    op.drop_column("run", "consent_id")
