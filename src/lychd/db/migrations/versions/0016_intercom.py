"""Durable outbound Intercom task, authority, outbox and capacity custody.

Revision ID: 0016
Revises: 0015

Schema operations are Alembic-derived against disposable PostgreSQL at 0015.
Wrappers preserve transactional DDL and refuse erasing any retained custody.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from advanced_alchemy.types import GUID, DateTimeUTC
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016"
down_revision = "0015"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create the ORM-derived schema in one PostgreSQL DDL transaction."""
    op.create_table(
        "intercom_capacity",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("scope", sa.String(length=12), nullable=False),
        sa.Column("scope_id", sa.String(length=200), nullable=False),
        sa.Column("uses_limit", sa.BigInteger(), nullable=False),
        sa.Column("application_limit", sa.BigInteger(), nullable=False),
        sa.Column("network_limit", sa.BigInteger(), nullable=False),
        sa.Column("uses_charged", sa.BigInteger(), nullable=False),
        sa.Column("application_charged", sa.BigInteger(), nullable=False),
        sa.Column("network_charged", sa.BigInteger(), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.CheckConstraint("scope IN ('host','purpose','peer','task')", name=op.f("ck_intercom_capacity_scope")),
        sa.CheckConstraint(
            "application_limit >= 0 AND application_charged >= 0 AND application_charged <= application_limit",
            name=op.f("ck_intercom_capacity_application"),
        ),
        sa.CheckConstraint(
            "network_limit >= 0 AND network_charged >= 0 AND network_charged <= network_limit",
            name=op.f("ck_intercom_capacity_network"),
        ),
        sa.CheckConstraint(
            "uses_limit >= 0 AND uses_charged >= 0 AND uses_charged <= uses_limit",
            name=op.f("ck_intercom_capacity_uses"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intercom_capacity")),
        sa.UniqueConstraint("scope", "scope_id", name="uq_intercom_capacity_scope"),
    )
    op.create_table(
        "intercom_peer",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("enrollment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enrollment_digest", sa.String(length=64), nullable=False),
        sa.Column("key_version", sa.BigInteger(), nullable=False),
        sa.Column("policy_generation", sa.BigInteger(), nullable=False),
        sa.Column("revocation_generation", sa.BigInteger(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.CheckConstraint(
            "key_version >= 1 AND policy_generation >= 1 AND revocation_generation >= 0",
            name=op.f("ck_intercom_peer_generations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intercom_peer")),
    )
    op.create_table(
        "intercom_credential",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("peer_id", GUID(length=16), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("key_id", sa.String(length=200), nullable=False),
        sa.Column("public_key_pem", sa.LargeBinary(), nullable=False),
        sa.Column("public_key_digest", sa.String(length=64), nullable=False),
        sa.Column("record", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("record_digest", sa.String(length=64), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("ck_intercom_credential_version")),
        sa.ForeignKeyConstraint(
            ["peer_id"],
            ["intercom_peer.id"],
            name=op.f("fk_intercom_credential_peer_id_intercom_peer"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intercom_credential")),
        sa.UniqueConstraint("peer_id", "key_id", name="uq_intercom_credential_key_id"),
        sa.UniqueConstraint("peer_id", "public_key_digest", name="uq_intercom_credential_public_key"),
        sa.UniqueConstraint("peer_id", "version", name="uq_intercom_credential_version"),
    )
    op.create_table(
        "intercom_declaration",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("peer_id", GUID(length=16), nullable=False),
        sa.Column("operation_id", GUID(length=16), nullable=False),
        sa.Column("policy_generation", sa.BigInteger(), nullable=False),
        sa.Column("record", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("record_digest", sa.String(length=64), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["peer_id"],
            ["intercom_peer.id"],
            name=op.f("fk_intercom_declaration_peer_id_intercom_peer"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intercom_declaration")),
    )
    op.create_table(
        "intercom_task",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("peer_id", GUID(length=16), nullable=False),
        sa.Column("declaration_id", GUID(length=16), nullable=False),
        sa.Column("operation_id", GUID(length=16), nullable=False),
        sa.Column("purpose", sa.String(length=200), nullable=False),
        sa.Column("task_schema", sa.String(length=300), nullable=False),
        sa.Column("expires_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("policy_generation", sa.BigInteger(), nullable=False),
        sa.Column("key_version", sa.BigInteger(), nullable=False),
        sa.Column("revocation_generation", sa.BigInteger(), nullable=False),
        sa.Column("record", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("record_digest", sa.String(length=64), nullable=False),
        sa.Column("local_status", sa.String(length=24), nullable=False),
        sa.Column("foreign_task_id", sa.String(length=128), nullable=True),
        sa.Column("foreign_status", sa.String(length=32), nullable=True),
        sa.Column("terminal_record", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.CheckConstraint(
            "policy_generation >= 1 AND key_version >= 1 AND revocation_generation >= 0",
            name=op.f("ck_intercom_task_generations"),
        ),
        sa.ForeignKeyConstraint(
            ["declaration_id"],
            ["intercom_declaration.id"],
            name=op.f("fk_intercom_task_declaration_id_intercom_declaration"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["peer_id"], ["intercom_peer.id"], name=op.f("fk_intercom_task_peer_id_intercom_peer"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intercom_task")),
    )
    op.create_table(
        "intercom_outbox",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("task_id", GUID(length=16), nullable=False),
        sa.Column("body", sa.LargeBinary(), nullable=False),
        sa.Column("body_digest", sa.String(length=64), nullable=False),
        sa.Column("submit_claimed", sa.Boolean(), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["intercom_task.id"],
            name=op.f("fk_intercom_outbox_task_id_intercom_task"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intercom_outbox")),
        sa.UniqueConstraint("task_id"),
        sa.UniqueConstraint("task_id", name=op.f("uq_intercom_outbox_task_id")),
    )
    op.create_table(
        "intercom_transmission",
        sa.Column("id", GUID(length=16), nullable=False),
        sa.Column("task_id", GUID(length=16), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("policy_generation", sa.BigInteger(), nullable=False),
        sa.Column("key_version", sa.BigInteger(), nullable=False),
        sa.Column("revocation_generation", sa.BigInteger(), nullable=False),
        sa.Column("application_bytes", sa.BigInteger(), nullable=False),
        sa.Column("network_bytes", sa.BigInteger(), nullable=False),
        sa.Column("accepted_network_bytes", sa.BigInteger(), nullable=False),
        sa.Column("record", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("record_digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("settlement", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", DateTimeUTC(timezone=True), nullable=False),
        sa.CheckConstraint(
            "method IN ('SendMessage','GetTask','CancelTask')", name=op.f("ck_intercom_transmission_method")
        ),
        sa.CheckConstraint(
            "status IN ('claimed','received','refused','unknown')", name=op.f("ck_intercom_transmission_status")
        ),
        sa.CheckConstraint(
            "accepted_network_bytes >= 0 AND accepted_network_bytes <= network_bytes",
            name=op.f("ck_intercom_transmission_accepted"),
        ),
        sa.CheckConstraint(
            "application_bytes > 0 AND network_bytes >= application_bytes",
            name=op.f("ck_intercom_transmission_charges"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["intercom_task.id"],
            name=op.f("fk_intercom_transmission_task_id_intercom_task"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intercom_transmission")),
    )


def downgrade() -> None:
    """Lock all seven tables before refusing any retained identity or charge."""
    op.execute(
        sa.text(
            "LOCK TABLE intercom_capacity, intercom_peer, intercom_credential, intercom_declaration, intercom_task, intercom_outbox, intercom_transmission IN ACCESS EXCLUSIVE MODE"
        )
    )
    op.execute(
        sa.text(
            "DO $$ BEGIN IF EXISTS (SELECT 1 FROM intercom_capacity LIMIT 1) OR EXISTS (SELECT 1 FROM intercom_peer LIMIT 1) OR EXISTS (SELECT 1 FROM intercom_credential LIMIT 1) OR EXISTS (SELECT 1 FROM intercom_declaration LIMIT 1) OR EXISTS (SELECT 1 FROM intercom_task LIMIT 1) OR EXISTS (SELECT 1 FROM intercom_outbox LIMIT 1) OR EXISTS (SELECT 1 FROM intercom_transmission LIMIT 1) THEN RAISE EXCEPTION 'Retained Intercom custody prevents downgrade'; END IF; END $$;"
        )
    )
    op.drop_table("intercom_transmission")
    op.drop_table("intercom_outbox")
    op.drop_table("intercom_task")
    op.drop_table("intercom_declaration")
    op.drop_table("intercom_credential")
    op.drop_table("intercom_peer")
    op.drop_table("intercom_capacity")
