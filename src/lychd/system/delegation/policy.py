"""Immutable security policy for bounded delegated-agent coffins."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Final, TypeGuard

from lychd.domain.delegation.models import DelegatedAgentProfile

_IDENTIFIER: Final[re.Pattern[str]] = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}")
_DNS_LABEL: Final[re.Pattern[str]] = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_MAX_MEMORY_BYTES: Final[int] = 64 * 1024**3
_MAX_FILE_SIZE_BYTES: Final[int] = 8 * 1024**3
_MAX_OUTPUT_BYTES: Final[int] = 64 * 1024**2
_MAX_CPU_SECONDS: Final[int] = 86_400
_MAX_WALL_TIME_SECONDS: Final[int] = 14_400
_MAX_PROCESSES: Final[int] = 256
_MAX_TCP_PORT: Final[int] = 65_535
_TLS_PORT: Final[int] = 443
_CONTROL_CHARACTER_LIMIT: Final[int] = 32
_MAX_HOST_LENGTH: Final[int] = 253


CoffinProfile = DelegatedAgentProfile


class FilesystemAccess(StrEnum):
    READ = "read"
    WRITE = "write"
    READ_WRITE = "readwrite"


@dataclass(frozen=True, slots=True)
class FilesystemGrant:
    path: PurePosixPath
    access: FilesystemAccess

    def __post_init__(self) -> None:
        """Canonicalize the grant path before the policy compares roots."""
        if not _is_filesystem_access(self.access):
            message = "Filesystem grant access must be a fixed access enum"
            raise TypeError(message)
        object.__setattr__(self, "path", confined_absolute_path(self.path, field="grant path"))


@dataclass(frozen=True, slots=True)
class CoffinFilesystemPolicy:
    """The complete visible job tree for one coffin."""

    profile: CoffinProfile
    job_root: PurePosixPath
    workspace_root: PurePosixPath
    scratch_root: PurePosixPath
    artifacts_root: PurePosixPath
    grants: tuple[FilesystemGrant, ...]

    def __post_init__(self) -> None:
        """Reject grants outside or ambiguously nested within the job tree."""
        if not _is_coffin_profile(self.profile):
            message = "Filesystem profile must be a fixed coffin profile"
            raise TypeError(message)
        job_root = confined_absolute_path(self.job_root, field="job root")
        workspace_root = confined_absolute_path(self.workspace_root, field="workspace root")
        scratch_root = confined_absolute_path(self.scratch_root, field="scratch root")
        artifacts_root = confined_absolute_path(self.artifacts_root, field="artifacts root")
        object.__setattr__(self, "job_root", job_root)
        object.__setattr__(self, "workspace_root", workspace_root)
        object.__setattr__(self, "scratch_root", scratch_root)
        object.__setattr__(self, "artifacts_root", artifacts_root)

        roots = (workspace_root, scratch_root, artifacts_root)
        if any(not root.is_relative_to(job_root) or root == job_root for root in roots):
            message = "All coffin roots must be strict children of the job root"
            raise ValueError(message)
        if any(
            left == right or left.is_relative_to(right) or right.is_relative_to(left)
            for index, left in enumerate(roots)
            for right in roots[index + 1 :]
        ):
            message = "Workspace, scratch, and artifact roots must be disjoint"
            raise ValueError(message)

        expected_paths = frozenset(roots)
        actual_paths = tuple(grant.path for grant in self.grants)
        if len(actual_paths) != len(set(actual_paths)) or frozenset(actual_paths) != expected_paths:
            message = "Filesystem grants must cover each coffin root exactly once"
            raise ValueError(message)
        expected_access = {
            workspace_root: (
                FilesystemAccess.READ if self.profile is not CoffinProfile.CANDIDATE else FilesystemAccess.READ_WRITE
            ),
            scratch_root: FilesystemAccess.READ_WRITE,
            artifacts_root: FilesystemAccess.READ_WRITE,
        }
        if any(grant.access is not expected_access[grant.path] for grant in self.grants):
            message = "Filesystem grants do not match the selected coffin profile"
            raise ValueError(message)

    @classmethod
    def for_profile(
        cls,
        profile: CoffinProfile,
        *,
        job_root: PurePosixPath,
        workspace_root: PurePosixPath,
        scratch_root: PurePosixPath,
        artifacts_root: PurePosixPath,
    ) -> CoffinFilesystemPolicy:
        workspace_access = FilesystemAccess.READ_WRITE if profile is CoffinProfile.CANDIDATE else FilesystemAccess.READ
        return cls(
            profile=profile,
            job_root=job_root,
            workspace_root=workspace_root,
            scratch_root=scratch_root,
            artifacts_root=artifacts_root,
            grants=(
                FilesystemGrant(workspace_root, workspace_access),
                FilesystemGrant(scratch_root, FilesystemAccess.READ_WRITE),
                FilesystemGrant(artifacts_root, FilesystemAccess.READ_WRITE),
            ),
        )


@dataclass(frozen=True, slots=True)
class GateEndpoint:
    """The sole network destination visible to the delegated agent."""

    host: str
    port: int = 443
    tls: bool = True
    request_path: str = "/v1/delegation/**"

    def __post_init__(self) -> None:
        """Accept only the TLS endpoint shape understood by this contract."""
        if self.host != self.host.lower() or not _valid_host(self.host):
            message = "Gate host must be a lowercase DNS name or IP address"
            raise ValueError(message)
        if not _is_strict_integer(self.port) or not 1 <= self.port <= _MAX_TCP_PORT:
            message = "Gate port must be in the TCP port range"
            raise ValueError(message)
        if self.tls is not True or self.port != _TLS_PORT:
            message = "The current coffin contract requires a TLS Provider Gate on port 443"
            raise ValueError(message)
        if not self.request_path.startswith("/") or ".." in self.request_path.split("/"):
            message = "Gate request path must be an absolute traversal-free path"
            raise ValueError(message)
        if any(character.isspace() or ord(character) < _CONTROL_CHARACTER_LIMIT for character in self.request_path):
            message = "Gate request path contains unsafe characters"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class CoffinNetworkPolicy:
    """Fail-closed egress policy: the Provider Gate is the only destination."""

    gate: GateEndpoint
    direct_provider_access: bool = False

    def __post_init__(self) -> None:
        """Prevent callers from weakening the Gate-only network boundary."""
        if self.direct_provider_access:
            message = "Delegated agents may not receive direct provider access"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class CoffinResourcePolicy:
    """Hard outer ceilings that a future effectful supervisor must enforce."""

    memory_bytes: int
    cpu_seconds: int
    wall_time_seconds: int
    max_processes: int
    max_file_size_bytes: int
    max_output_bytes: int

    def __post_init__(self) -> None:
        """Validate every outer resource ceiling against the audited maximum."""
        _bounded(self.memory_bytes, maximum=_MAX_MEMORY_BYTES, field="memory_bytes")
        _bounded(self.cpu_seconds, maximum=_MAX_CPU_SECONDS, field="cpu_seconds")
        _bounded(self.wall_time_seconds, maximum=_MAX_WALL_TIME_SECONDS, field="wall_time_seconds")
        _bounded(self.max_processes, maximum=_MAX_PROCESSES, field="max_processes")
        _bounded(self.max_file_size_bytes, maximum=_MAX_FILE_SIZE_BYTES, field="max_file_size_bytes")
        _bounded(self.max_output_bytes, maximum=_MAX_OUTPUT_BYTES, field="max_output_bytes")


@dataclass(frozen=True, slots=True)
class CoffinPolicy:
    job_id: str
    profile: CoffinProfile
    filesystem: CoffinFilesystemPolicy
    network: CoffinNetworkPolicy
    resources: CoffinResourcePolicy

    def __post_init__(self) -> None:
        """Validate the identifier used for derived profile names."""
        validate_identifier(self.job_id, field="job_id")
        if not _is_coffin_profile(self.profile):
            message = "Policy profile must be a fixed coffin profile"
            raise TypeError(message)
        if self.filesystem.profile is not self.profile:
            message = "Coffin policy and filesystem profile must match"
            raise ValueError(message)


def confined_absolute_path(value: str | PurePosixPath, *, field: str) -> PurePosixPath:
    """Accept only canonical absolute POSIX paths below filesystem root."""
    raw = str(value)
    if (
        not raw.startswith("/")
        or raw == "/"
        or raw.endswith("/")
        or "\\" in raw
        or "\x00" in raw
        or any(character.isspace() or ord(character) < _CONTROL_CHARACTER_LIMIT for character in raw)
    ):
        message = f"{field} must be a canonical absolute POSIX path below /"
        raise ValueError(message)
    components = raw.split("/")[1:]
    if any(component in {"", ".", ".."} for component in components):
        message = f"{field} contains traversal or non-canonical components"
        raise ValueError(message)
    path = PurePosixPath(raw)
    if str(path) != raw:
        message = f"{field} must be canonical"
        raise ValueError(message)
    return path


def validate_identifier(value: str, *, field: str) -> str:
    if _IDENTIFIER.fullmatch(value) is None:
        message = f"{field} contains unsupported characters"
        raise ValueError(message)
    return value


def _bounded(value: object, *, maximum: int, field: str) -> None:
    if not _is_strict_integer(value) or not 1 <= value <= maximum:
        message = f"{field} must be between 1 and {maximum}"
        raise ValueError(message)


def _is_coffin_profile(value: object) -> bool:
    return isinstance(value, CoffinProfile)


def _is_filesystem_access(value: object) -> bool:
    return isinstance(value, FilesystemAccess)


def _is_strict_integer(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_host(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        if len(value) > _MAX_HOST_LENGTH or value.endswith(".") or "*" in value:
            return False
        return all(_DNS_LABEL.fullmatch(label) is not None for label in value.split("."))
    return True


__all__ = (
    "CoffinFilesystemPolicy",
    "CoffinNetworkPolicy",
    "CoffinPolicy",
    "CoffinProfile",
    "CoffinResourcePolicy",
    "FilesystemAccess",
    "FilesystemGrant",
    "GateEndpoint",
    "confined_absolute_path",
    "validate_identifier",
)
