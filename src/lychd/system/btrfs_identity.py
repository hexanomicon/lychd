"""Shared parsing for bounded ``btrfs subvolume show`` evidence."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

BTRFS_FIRST_FREE_OBJECTID = 256
BTRFS_SUBVOLUME_BOUNDARY_INODES = frozenset({2, 256})


@dataclass(frozen=True, slots=True)
class BtrfsSubvolumeObservation:
    """Stable positive identity of one live Btrfs subvolume."""

    uuid: str
    subvolume_id: int

    def __post_init__(self) -> None:
        """Canonicalize UUID and reject Btrfs's reserved object-ID range."""
        object.__setattr__(self, "uuid", str(UUID(self.uuid)))
        if self.subvolume_id < BTRFS_FIRST_FREE_OBJECTID:
            message = "Btrfs subvolume ID is in the reserved object range."
            raise ValueError(message)


def parse_subvolume_show(
    content: str,
) -> BtrfsSubvolumeObservation | None:
    """Parse UUID and ID from bounded ``btrfs subvolume show`` output."""
    fields: dict[str, str] = {}
    for raw_line in content.splitlines():
        key, separator, value = raw_line.strip().partition(":")
        if separator:
            fields.setdefault(key.casefold(), value.strip())
    raw_uuid = fields.get("uuid")
    raw_id = fields.get("subvolume id")
    if raw_uuid is None or raw_id is None:
        return None
    try:
        return BtrfsSubvolumeObservation(
            uuid=raw_uuid,
            subvolume_id=int(raw_id),
        )
    except (TypeError, ValueError):
        return None


__all__ = (
    "BTRFS_FIRST_FREE_OBJECTID",
    "BTRFS_SUBVOLUME_BOUNDARY_INODES",
    "BtrfsSubvolumeObservation",
    "parse_subvolume_show",
)
