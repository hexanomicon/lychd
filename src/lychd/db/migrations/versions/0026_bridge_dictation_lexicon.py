"""Explicit approved private vocabulary.

Revision ID: 0026
Revises: 0025
Create Date: 2026-11-03

Candidate metadata counterpart; parent verifies schema parity before admission.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID, DateTimeUTC
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision = "0026"
down_revision = "0025"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("SET LOCAL statement_timeout = '5s'"))
    op.execute(sa.text("SET LOCAL lock_timeout = '2s'"))
    op.create_table(
        "bridge_dictation_lexicon_rule",
        sa.Column("owner", sa.String(256), nullable=False),
        sa.Column("language", sa.String(35), nullable=False),
        sa.Column("heard", sa.String(128), nullable=False),
        sa.Column("replacement", sa.String(128), nullable=False),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("expires_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "char_length(owner) BETWEEN 1 AND 256", name=op.f("ck_bridge_dictation_lexicon_rule_owner_bound")
        ),
        sa.CheckConstraint(
            "char_length(language) BETWEEN 2 AND 35 AND language = lower(language)",
            name=op.f("ck_bridge_dictation_lexicon_rule_language_bound"),
        ),
        sa.CheckConstraint(
            "char_length(heard) BETWEEN 1 AND 128", name=op.f("ck_bridge_dictation_lexicon_rule_heard_bound")
        ),
        sa.CheckConstraint(
            "char_length(replacement) BETWEEN 1 AND 128",
            name=op.f("ck_bridge_dictation_lexicon_rule_replacement_bound"),
        ),
        sa.CheckConstraint(
            "expires_at > created_at AND expires_at <= created_at + INTERVAL '30 days'",
            name=op.f("ck_bridge_dictation_lexicon_rule_retention_bound"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bridge_dictation_lexicon_rule")),
        sa.UniqueConstraint("owner", "language", "heard", name="uq_bridge_dictation_lexicon_owner_language_heard"),
    )


def downgrade() -> None:
    """Rollback is not permission to erase retained approvals."""
    op.execute(sa.text("SET LOCAL statement_timeout = '5s'"))
    op.execute(sa.text("SET LOCAL lock_timeout = '2s'"))
    op.execute(sa.text("LOCK TABLE bridge_dictation_lexicon_rule IN ACCESS EXCLUSIVE MODE"))
    op.execute(
        sa.text("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM bridge_dictation_lexicon_rule LIMIT 1) THEN
                RAISE EXCEPTION 'Retained vocabulary approvals prevent downgrade';
            END IF;
        END
        $$;
    """)
    )
    op.drop_table("bridge_dictation_lexicon_rule")
