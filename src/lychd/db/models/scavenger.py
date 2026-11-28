"""One pending/retained finite field and permanent content-free deletion tombstones."""

from __future__ import annotations

from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class ScavengerObservation(UUIDAuditBase):
    """Application-owned payloads, separate from immutable Run and Webcrawler custody."""

    __tablename__ = "scavenger_observation"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_scavenger_observation_run_id"),
        UniqueConstraint("slot", name="uq_scavenger_observation_slot"),
        CheckConstraint("status IN ('reserved','bound','committed','deleted')", name="status"),
        CheckConstraint("slot IS NULL OR slot = 1", name="one_slot"),
        CheckConstraint("(status = 'deleted') = (slot IS NULL)", name="retained_slot"),
        CheckConstraint(
            "(status = 'deleted' AND seed_bytes IS NULL AND filter_bytes IS NULL AND observation_bytes IS NULL) OR "
            "(status <> 'deleted' AND seed_bytes IS NOT NULL AND filter_bytes IS NOT NULL)",
            name="payload_disposition",
        ),
        CheckConstraint(
            "(status = 'committed' AND observation_bytes IS NOT NULL AND observation_digest IS NOT NULL) OR "
            "(status <> 'committed' AND observation_bytes IS NULL)",
            name="result_disposition",
        ),
        CheckConstraint("status NOT IN ('bound','committed') OR run_id IS NOT NULL", name="run_custody"),
        CheckConstraint("seed_bytes IS NULL OR octet_length(seed_bytes) <= 16384", name="seed_bound"),
        CheckConstraint("filter_bytes IS NULL OR octet_length(filter_bytes) <= 2048", name="filter_bound"),
        CheckConstraint(
            "observation_bytes IS NULL OR octet_length(observation_bytes) <= 262144", name="observation_bound"
        ),
    )
    owner: Mapped[str] = mapped_column(String(100))
    request_digest: Mapped[str] = mapped_column(String(64))
    seed_digest: Mapped[str] = mapped_column(String(64))
    initial_filter_digest: Mapped[str] = mapped_column(String(64))
    configuration_digest: Mapped[str] = mapped_column(String(64))
    slot: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("run.id", ondelete="RESTRICT"), nullable=True)
    seed_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    filter_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    observation_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    observation_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
