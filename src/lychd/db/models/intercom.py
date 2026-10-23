"""Restricted outbound peer custody; no persisted value confers live authority."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, LargeBinary, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class IntercomPeer(UUIDAuditBase):
    """Immutable enrolled identity with monotonic current authority generations."""

    __tablename__ = "intercom_peer"
    __table_args__ = (
        CheckConstraint(
            "key_version >= 1 AND policy_generation >= 1 AND revocation_generation >= 0", name="generations"
        ),
    )
    enrollment: Mapped[dict[str, Any]] = mapped_column(JSONB)
    enrollment_digest: Mapped[str] = mapped_column(String(64))
    key_version: Mapped[int] = mapped_column(BigInteger)
    policy_generation: Mapped[int] = mapped_column(BigInteger)
    revocation_generation: Mapped[int] = mapped_column(BigInteger)
    revoked: Mapped[bool]
    policy: Mapped[dict[str, Any]] = mapped_column(JSONB)


class IntercomCredential(UUIDAuditBase):
    """Append-only public verification credential versions, never private keys."""

    __tablename__ = "intercom_credential"
    __table_args__ = (
        UniqueConstraint("peer_id", "version", name="uq_intercom_credential_version"),
        UniqueConstraint("peer_id", "key_id", name="uq_intercom_credential_key_id"),
        UniqueConstraint("peer_id", "public_key_digest", name="uq_intercom_credential_public_key"),
        CheckConstraint("version >= 1", name="version"),
    )
    peer_id: Mapped[UUID] = mapped_column(ForeignKey("intercom_peer.id", ondelete="RESTRICT"))
    version: Mapped[int] = mapped_column(BigInteger)
    key_id: Mapped[str] = mapped_column(String(200))
    public_key_pem: Mapped[bytes] = mapped_column(LargeBinary)
    public_key_digest: Mapped[str] = mapped_column(String(64))
    record: Mapped[dict[str, Any]] = mapped_column(JSONB)
    record_digest: Mapped[str] = mapped_column(String(64))


class IntercomDeclaration(UUIDAuditBase):
    """Attributed complete public-text assertion, independently from task intent."""

    __tablename__ = "intercom_declaration"
    peer_id: Mapped[UUID] = mapped_column(ForeignKey("intercom_peer.id", ondelete="RESTRICT"))
    operation_id: Mapped[UUID]
    policy_generation: Mapped[int] = mapped_column(BigInteger)
    record: Mapped[dict[str, Any]] = mapped_column(JSONB)
    record_digest: Mapped[str] = mapped_column(String(64))


class IntercomTask(UUIDAuditBase):
    """One sealed local intent; local closure and foreign execution stay distinct."""

    __tablename__ = "intercom_task"
    __table_args__ = (
        CheckConstraint(
            "policy_generation >= 1 AND key_version >= 1 AND revocation_generation >= 0", name="generations"
        ),
        CheckConstraint(
            "(native_run_id IS NULL AND native_station IS NULL AND native_request_id IS NULL "
            "AND native_binding_digest IS NULL AND native_pattern_digest IS NULL AND native_enqueue_seq IS NULL "
            "AND native_step_id IS NULL AND native_occurrence_id IS NULL) OR "
            "(native_run_id IS NOT NULL AND native_station IS NOT NULL AND native_request_id IS NOT NULL "
            "AND native_binding_digest IS NOT NULL AND native_pattern_digest IS NOT NULL "
            "AND native_enqueue_seq IS NOT NULL AND native_enqueue_seq >= 0 "
            "AND native_step_id IS NOT NULL AND native_occurrence_id IS NOT NULL)",
            name="native_binding_complete",
        ),
        UniqueConstraint(
            "native_run_id", "native_station", "native_request_id", name="uq_intercom_task_native_request"
        ),
    )
    peer_id: Mapped[UUID] = mapped_column(ForeignKey("intercom_peer.id", ondelete="RESTRICT"))
    declaration_id: Mapped[UUID] = mapped_column(ForeignKey("intercom_declaration.id", ondelete="RESTRICT"))
    operation_id: Mapped[UUID]
    purpose: Mapped[str] = mapped_column(String(200))
    task_schema: Mapped[str] = mapped_column(String(300))
    expires_at: Mapped[datetime]
    policy_generation: Mapped[int] = mapped_column(BigInteger)
    key_version: Mapped[int] = mapped_column(BigInteger)
    revocation_generation: Mapped[int] = mapped_column(BigInteger)
    record: Mapped[dict[str, Any]] = mapped_column(JSONB)
    record_digest: Mapped[str] = mapped_column(String(64))
    local_status: Mapped[str] = mapped_column(String(24))
    foreign_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    foreign_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    terminal_record: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    native_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("run.id", ondelete="RESTRICT"), nullable=True)
    native_station: Mapped[str | None] = mapped_column(String(100), nullable=True)
    native_request_id: Mapped[UUID | None] = mapped_column(nullable=True)
    native_binding_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    native_pattern_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    native_enqueue_seq: Mapped[int | None] = mapped_column(nullable=True)
    native_step_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    native_occurrence_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    adoption_closed: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    closure_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    native_reauthorizations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )


class IntercomOutbox(UUIDAuditBase):
    """Sealed semantic request; a submit claim is permanent across uncertainty."""

    __tablename__ = "intercom_outbox"
    task_id: Mapped[UUID] = mapped_column(ForeignKey("intercom_task.id", ondelete="RESTRICT"), unique=True)
    body: Mapped[bytes] = mapped_column(LargeBinary)
    body_digest: Mapped[str] = mapped_column(String(64))
    submit_claimed: Mapped[bool]


class IntercomTransmission(UUIDAuditBase):
    """Every physical wrapper and its full irreversible conservative charge."""

    __tablename__ = "intercom_transmission"
    __table_args__ = (
        CheckConstraint("method IN ('SendMessage','GetTask','CancelTask')", name="method"),
        CheckConstraint("status IN ('claimed','received','refused','unknown')", name="status"),
        CheckConstraint("application_bytes > 0 AND network_bytes >= application_bytes", name="charges"),
        CheckConstraint("accepted_network_bytes >= 0 AND accepted_network_bytes <= network_bytes", name="accepted"),
    )
    task_id: Mapped[UUID] = mapped_column(ForeignKey("intercom_task.id", ondelete="RESTRICT"))
    method: Mapped[str] = mapped_column(String(16))
    policy_generation: Mapped[int] = mapped_column(BigInteger)
    key_version: Mapped[int] = mapped_column(BigInteger)
    revocation_generation: Mapped[int] = mapped_column(BigInteger)
    application_bytes: Mapped[int] = mapped_column(BigInteger)
    network_bytes: Mapped[int] = mapped_column(BigInteger)
    accepted_network_bytes: Mapped[int] = mapped_column(BigInteger)
    record: Mapped[dict[str, Any]] = mapped_column(JSONB)
    record_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    settlement: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class IntercomCapacity(UUIDAuditBase):
    """Stable permanent ceilings; credential and configuration labels cannot reset."""

    __tablename__ = "intercom_capacity"
    __table_args__ = (
        UniqueConstraint("scope", "scope_id", name="uq_intercom_capacity_scope"),
        CheckConstraint("scope IN ('host','purpose','peer','task')", name="scope"),
        CheckConstraint("uses_limit >= 0 AND uses_charged >= 0 AND uses_charged <= uses_limit", name="uses"),
        CheckConstraint(
            "application_limit >= 0 AND application_charged >= 0 AND application_charged <= application_limit",
            name="application",
        ),
        CheckConstraint(
            "network_limit >= 0 AND network_charged >= 0 AND network_charged <= network_limit", name="network"
        ),
    )
    scope: Mapped[str] = mapped_column(String(12))
    scope_id: Mapped[str] = mapped_column(String(200))
    uses_limit: Mapped[int] = mapped_column(BigInteger)
    application_limit: Mapped[int] = mapped_column(BigInteger)
    network_limit: Mapped[int] = mapped_column(BigInteger)
    uses_charged: Mapped[int] = mapped_column(BigInteger)
    application_charged: Mapped[int] = mapped_column(BigInteger)
    network_charged: Mapped[int] = mapped_column(BigInteger)
