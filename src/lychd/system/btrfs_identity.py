"""Shared Btrfs identity values and bounded descriptor observation."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

if TYPE_CHECKING:
    from lychd.system.operator.process import DescriptorProcessRunner

BTRFS_FIRST_FREE_OBJECTID = 256
BTRFS_SUBVOLUME_BOUNDARY_INODES = frozenset({2, 256})
_MAX_OBSERVATION_BYTES = 256
_MAX_SUBVOLUME_ID = (1 << 64) - 1


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


def observe_subvolume_fd(
    descriptor: int, *, runner: DescriptorProcessRunner, timeout_s: float
) -> BtrfsSubvolumeObservation | None:
    """Observe one inherited leaf through this exact source's isolated helper."""
    from lychd.system.operator.process import ProcessInvocationError

    try:
        interpreter = Path(sys.executable).resolve(strict=True)
        helper = Path(__file__).resolve(strict=True).with_name("btrfs_observer.py")
        result = runner.run_with_fds(
            (str(interpreter), "-I", "-S", str(helper), str(descriptor)),
            timeout_s=timeout_s,
            pass_fds=(descriptor,),
        )
    except (OSError, ProcessInvocationError):
        return None
    if result.returncode != 0 or len(result.stdout.encode(errors="replace")) > _MAX_OBSERVATION_BYTES:
        return None
    try:
        payload: object = json.loads(result.stdout)
        if not isinstance(payload, dict):
            return None
        data = cast("dict[str, Any]", payload)
        if (
            set(data) != {"uuid", "subvolume_id"}
            or not isinstance(data["uuid"], str)
            or type(data["subvolume_id"]) is not int
            or data["subvolume_id"] > _MAX_SUBVOLUME_ID
        ):
            return None
        return BtrfsSubvolumeObservation(uuid=data["uuid"], subvolume_id=data["subvolume_id"])
    except (ValueError, TypeError):
        return None


__all__ = (
    "BTRFS_FIRST_FREE_OBJECTID",
    "BTRFS_SUBVOLUME_BOUNDARY_INODES",
    "BtrfsSubvolumeObservation",
    "observe_subvolume_fd",
    "parse_subvolume_show",
)
