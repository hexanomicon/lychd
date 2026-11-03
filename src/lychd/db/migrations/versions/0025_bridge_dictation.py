"""Private owner-scoped dictation custody.

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-03

Candidate metadata counterpart; parent must verify schema parity in OCI before
admission. This migration neither reads old sessions nor imports private history.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID, DateTimeUTC
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision = "0025"
down_revision = "0024"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("SET LOCAL statement_timeout = '5s'"))
    op.execute(sa.text("SET LOCAL lock_timeout = '2s'"))
    op.create_table(
        "bridge_dictation_attempt",
        sa.Column("owner", sa.String(256), nullable=False),
        sa.Column("attempt_id", GUID(length=16), nullable=False),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("expires_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("audio_expires_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("tombstone_until", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=True),
        sa.Column("raw_audio", sa.LargeBinary(), nullable=True),
        sa.Column("raw_size", sa.Integer(), nullable=False),
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "char_length(owner) BETWEEN 1 AND 256", name=op.f("ck_bridge_dictation_attempt_owner_bound")
        ),
        sa.CheckConstraint(
            "expires_at > created_at AND expires_at <= created_at + INTERVAL '30 days'",
            name=op.f("ck_bridge_dictation_attempt_retention_bound"),
        ),
        sa.CheckConstraint(
            "audio_expires_at >= created_at AND audio_expires_at <= created_at + INTERVAL '1 hour'",
            name=op.f("ck_bridge_dictation_attempt_raw_retention_bound"),
        ),
        sa.CheckConstraint(
            "content_json IS NULL OR octet_length(content_json) BETWEEN 1 AND 131072",
            name=op.f("ck_bridge_dictation_attempt_content_bound"),
        ),
        sa.CheckConstraint(
            "(raw_audio IS NULL AND raw_size = 0) OR "
            "(raw_audio IS NOT NULL AND raw_size BETWEEN 46 AND 1048576 AND octet_length(raw_audio) = raw_size)",
            name=op.f("ck_bridge_dictation_attempt_raw_bound"),
        ),
        sa.CheckConstraint(
            "content_json IS NOT NULL OR (raw_audio IS NULL AND raw_size = 0)",
            name=op.f("ck_bridge_dictation_attempt_erasure_complete"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bridge_dictation_attempt")),
        sa.UniqueConstraint("owner", "attempt_id", name="uq_bridge_dictation_attempt_owner_id"),
    )


def downgrade() -> None:
    """Rollback refuses retained private content and replay fences under one lock."""
    op.execute(sa.text("SET LOCAL statement_timeout = '5s'"))
    op.execute(sa.text("SET LOCAL lock_timeout = '2s'"))
    op.execute(sa.text("LOCK TABLE bridge_dictation_attempt IN ACCESS EXCLUSIVE MODE"))
    op.execute(
        sa.text("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM bridge_dictation_attempt LIMIT 1) THEN
                RAISE EXCEPTION 'Retained dictation attempts prevent downgrade';
            END IF;
        END
        $$;
    """)
    )
    op.drop_table("bridge_dictation_attempt")
