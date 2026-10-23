"""Bind native public peer tasks to exact Run owners without replaying sovereign work.

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-22

Schema operations are derived from ORM metadata against actual revision0016.
The generation receipt retains the unwrapped Alembic output. Transactional locks,
legacy-owner audits and retained-evidence downgrade refusal are lifecycle law.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["downgrade", "upgrade"]

revision = "0017"
down_revision = "0016"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Audit legacy wait owners, then add native ownership atomically."""
    op.execute(sa.text('LOCK TABLE "run", intercom_task IN ACCESS EXCLUSIVE MODE'))
    op.execute(
        sa.text("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM run WHERE consent_id IS NOT NULL AND delegated_job_id IS NOT NULL LIMIT 1
            ) THEN
                RAISE EXCEPTION 'Native peer migration requires exclusive existing Run wait owners';
            END IF;
            IF EXISTS (
                SELECT 1 FROM run WHERE status = 'awaiting_delegate' AND delegated_job_id IS NULL LIMIT 1
            ) THEN
                RAISE EXCEPTION 'Native peer migration cannot infer an existing delegated wait owner';
            END IF;
            IF EXISTS (
                SELECT 1 FROM run WHERE status = 'awaiting_peer'
                  OR source = 'peer_public'
                  OR (intent -> 'admitted_peer' IS NOT NULL AND intent -> 'admitted_peer' <> 'null'::jsonb)
                LIMIT 1
            ) THEN
                RAISE EXCEPTION 'Native peer migration cannot infer preexisting native peer ownership';
            END IF;
        END
        $$;
    """)
    )
    op.add_column("intercom_task", sa.Column("native_run_id", GUID(length=16), nullable=True))
    op.add_column("intercom_task", sa.Column("native_station", sa.String(length=100), nullable=True))
    op.add_column("intercom_task", sa.Column("native_request_id", GUID(length=16), nullable=True))
    op.add_column("intercom_task", sa.Column("native_binding_digest", sa.String(length=64), nullable=True))
    op.add_column("intercom_task", sa.Column("native_pattern_digest", sa.String(length=64), nullable=True))
    op.add_column("intercom_task", sa.Column("native_enqueue_seq", sa.Integer(), nullable=True))
    op.add_column("intercom_task", sa.Column("native_step_id", sa.String(length=128), nullable=True))
    op.add_column("intercom_task", sa.Column("native_occurrence_id", sa.String(length=128), nullable=True))
    op.add_column(
        "intercom_task", sa.Column("adoption_closed", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    op.add_column("intercom_task", sa.Column("closure_reason", sa.String(length=32), nullable=True))
    op.add_column(
        "intercom_task",
        sa.Column(
            "native_reauthorizations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_intercom_task_native_request", "intercom_task", ["native_run_id", "native_station", "native_request_id"]
    )
    op.create_foreign_key(
        op.f("fk_intercom_task_native_run_id_run"),
        "intercom_task",
        "run",
        ["native_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column("run", sa.Column("peer_task_id", GUID(length=16), nullable=True))
    op.create_index(op.f("ix_run_peer_task_id"), "run", ["peer_task_id"], unique=False)
    op.create_foreign_key(
        "fk_run_peer_task_id_intercom_task",
        "run",
        "intercom_task",
        ["peer_task_id"],
        ["id"],
        ondelete="RESTRICT",
        use_alter=True,
    )
    op.create_check_constraint(
        op.f("ck_intercom_task_native_binding_complete"),
        "intercom_task",
        "(native_run_id IS NULL AND native_station IS NULL AND native_request_id IS NULL AND native_binding_digest IS NULL AND native_pattern_digest IS NULL AND native_enqueue_seq IS NULL AND native_step_id IS NULL AND native_occurrence_id IS NULL) OR (native_run_id IS NOT NULL AND native_station IS NOT NULL AND native_request_id IS NOT NULL AND native_binding_digest IS NOT NULL AND native_pattern_digest IS NOT NULL AND native_enqueue_seq IS NOT NULL AND native_enqueue_seq >= 0 AND native_step_id IS NOT NULL AND native_occurrence_id IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_run_single_wait_owner"),
        "run",
        "(CASE WHEN consent_id IS NULL THEN 0 ELSE 1 END + CASE WHEN delegated_job_id IS NULL THEN 0 ELSE 1 END + CASE WHEN peer_task_id IS NULL THEN 0 ELSE 1 END) <= 1",
    )
    op.create_check_constraint(
        op.f("ck_run_waiting_peer_owner"), "run", "status <> 'awaiting_peer' OR peer_task_id IS NOT NULL"
    )


def downgrade() -> None:
    """Retain every native source/task relation and local closure, including terminal Runs."""
    op.execute(sa.text('LOCK TABLE "run", intercom_task IN ACCESS EXCLUSIVE MODE'))
    op.execute(
        sa.text("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM run WHERE peer_task_id IS NOT NULL OR status = 'awaiting_peer'
                  OR source = 'peer_public'
                  OR (intent -> 'admitted_peer' IS NOT NULL AND intent -> 'admitted_peer' <> 'null'::jsonb)
                LIMIT 1
            ) OR EXISTS (
                SELECT 1 FROM intercom_task WHERE native_run_id IS NOT NULL
                  OR native_station IS NOT NULL OR native_request_id IS NOT NULL
                  OR native_binding_digest IS NOT NULL OR native_pattern_digest IS NOT NULL
                  OR native_enqueue_seq IS NOT NULL OR native_step_id IS NOT NULL
                  OR native_occurrence_id IS NOT NULL OR adoption_closed
                  OR closure_reason IS NOT NULL OR native_reauthorizations <> '[]'::jsonb
                LIMIT 1
            ) THEN
                RAISE EXCEPTION 'Retained native peer custody prevents downgrade';
            END IF;
        END
        $$;
    """)
    )
    op.drop_constraint(op.f("ck_run_waiting_peer_owner"), "run", type_="check")
    op.drop_constraint(op.f("ck_run_single_wait_owner"), "run", type_="check")
    op.drop_constraint(op.f("ck_intercom_task_native_binding_complete"), "intercom_task", type_="check")
    op.drop_constraint("fk_run_peer_task_id_intercom_task", "run", type_="foreignkey")
    op.drop_index(op.f("ix_run_peer_task_id"), table_name="run")
    op.drop_column("run", "peer_task_id")
    op.drop_constraint(op.f("fk_intercom_task_native_run_id_run"), "intercom_task", type_="foreignkey")
    op.drop_constraint("uq_intercom_task_native_request", "intercom_task", type_="unique")
    op.drop_column("intercom_task", "native_reauthorizations")
    op.drop_column("intercom_task", "closure_reason")
    op.drop_column("intercom_task", "adoption_closed")
    op.drop_column("intercom_task", "native_occurrence_id")
    op.drop_column("intercom_task", "native_step_id")
    op.drop_column("intercom_task", "native_enqueue_seq")
    op.drop_column("intercom_task", "native_pattern_digest")
    op.drop_column("intercom_task", "native_binding_digest")
    op.drop_column("intercom_task", "native_request_id")
    op.drop_column("intercom_task", "native_station")
    op.drop_column("intercom_task", "native_run_id")
