"""Persistent filesystem/object identity, separate from live descriptor guards."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from lychd.lib.json_objects import unique_json_object

if TYPE_CHECKING:
    from lychd.system.operator.process import DescriptorProcessRunner

_MAX_OBSERVATION_BYTES = 1024
_TOP_LEVEL_ID = 5
_FIRST_SUBVOLUME_ID = 256


class PathIdentityError(RuntimeError):
    """The kernel could not prove a supported persistent object identity."""


class PersistentPathIdentity(BaseModel):
    """Exact reboot-persistent identity; never a pathname or mutation grant."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    version: Literal[1] = 1
    filesystem: Literal["btrfs", "ext4"]
    filesystem_uuid: str
    inode: int = Field(gt=0)
    generation: int = Field(ge=0, le=(1 << 32) - 1)
    subvolume_id: int | None = Field(default=None, ge=5, le=(1 << 64) - 1)
    subvolume_uuid: str | None = None

    @field_validator("version", mode="before")
    @classmethod
    def strict_version(cls, value: object) -> object:
        """Reject JSON booleans as schema versions."""
        if type(value) is not int:
            message = "Persistent identity version must be an integer."
            raise ValueError(message)
        return value

    @field_validator("filesystem_uuid", "subvolume_uuid")
    @classmethod
    def canonical_uuid(cls, value: str | None) -> str | None:
        """Only nonzero, canonical UUIDs can name persistent objects."""
        if value is not None and (str(UUID(value)) != value or UUID(value).int == 0):
            message = "Persistent identity requires a nonzero canonical UUID."
            raise ValueError(message)
        return value

    @model_validator(mode="after")
    def containing_root(self) -> PersistentPathIdentity:
        """Btrfs object numbers are scoped to their containing subvolume."""
        if self.filesystem == "ext4":
            valid = self.subvolume_id is None and self.subvolume_uuid is None
        else:
            valid = (self.subvolume_id == _TOP_LEVEL_ID and self.subvolume_uuid is None) or (
                self.subvolume_id is not None
                and self.subvolume_id >= _FIRST_SUBVOLUME_ID
                and self.subvolume_uuid is not None
            )
        if not valid:
            message = "Persistent identity has an invalid containing-root scope."
            raise ValueError(message)
        return self


def observe_identity_fd(
    descriptor: int,
    *,
    runner: DescriptorProcessRunner | None = None,
    timeout_s: float = 5.0,
) -> PersistentPathIdentity:
    """Read only one inherited fd through this source's isolated fixed observer."""
    from lychd.system.operator.process import ProcessInvocationError, SubprocessRunner

    try:
        before = os.fstat(descriptor)
        if not (stat.S_ISDIR(before.st_mode) or stat.S_ISREG(before.st_mode)):
            message = "Persistent identity requires a regular file or directory."
            raise PathIdentityError(message)
        interpreter = Path(sys.executable).resolve(strict=True)
        helper = Path(__file__).resolve(strict=True).with_name("path_identity_observer.py")
        result = (runner or SubprocessRunner()).run_with_fds(
            (str(interpreter), "-I", "-S", str(helper), str(descriptor)),
            timeout_s=timeout_s,
            pass_fds=(descriptor,),
        )
        if result.returncode != 0 or len(result.stdout.encode()) > _MAX_OBSERVATION_BYTES:
            message = "Persistent filesystem identity is unavailable or unsupported."
            raise PathIdentityError(message)
        identity = PersistentPathIdentity.model_validate(
            json.loads(result.stdout, object_pairs_hook=unique_json_object)
        )
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode)) != (
            after.st_dev,
            after.st_ino,
            stat.S_IFMT(after.st_mode),
        ) or identity.inode != before.st_ino:
            message = "Descriptor identity changed during persistent observation."
            raise PathIdentityError(message)
    except (OSError, ValueError, ValidationError, ProcessInvocationError) as exc:
        message = "Persistent filesystem identity observation failed."
        raise PathIdentityError(message) from exc
    return identity


__all__ = ("PathIdentityError", "PersistentPathIdentity", "observe_identity_fd")
