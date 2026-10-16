"""Dependency-leaf immutable mechanical values shared by request and compiler."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

_MAX_PATH_BYTES = 4096
_MAX_MODEL_BYTES = 256


class CliRuntimeKind(StrEnum):
    """Explicitly supported noninteractive wire protocols."""

    CODEX = "codex"
    CLAUDE = "claude"


def require_cli_kind(kind: CliRuntimeKind) -> None:
    if type(kind) is not CliRuntimeKind:
        msg = "An exact supported CLI runtime kind is required."
        raise ValueError(msg)


def reviewed_cli_version(kind: CliRuntimeKind) -> str:
    """Return the exact CLI help revision this launch contract was reviewed against."""
    require_cli_kind(kind)
    return "0.159.2" if kind is CliRuntimeKind.CODEX else "2.1.296"


@dataclass(frozen=True, slots=True)
class CliLimits:
    """Capture and wall bounds; host resource/Gate budgets are additional requirements."""

    max_stdout_bytes: int = 1_048_576
    max_stderr_bytes: int = 16_384
    max_record_bytes: int = 262_144
    wall_seconds: int = 300

    def __post_init__(self) -> None:
        """Reject absent or unbounded capture/deadline limits."""
        for value, maximum in (
            (self.max_stdout_bytes, 1_048_576),
            (self.max_stderr_bytes, 16_384),
            (self.max_record_bytes, self.max_stdout_bytes),
            (self.wall_seconds, 86_400),
        ):
            if type(value) is not int or not 0 < value <= maximum:
                msg = "CLI limits must be positive bounded integers."
                raise ValueError(msg)


def validate_cli_path(value: str) -> PurePosixPath:
    """Check bounded canonical syntax; the host owns real-path verification."""
    if type(value) is not str:
        msg = "CLI paths must be bounded canonical absolute POSIX paths."
        raise ValueError(msg)
    path = PurePosixPath(value)
    if (
        not value.startswith("/")
        or value.startswith("//")
        or str(path) != value
        or ".." in path.parts
        or not value.isprintable()
        or len(value.encode()) > _MAX_PATH_BYTES
    ):
        msg = "CLI paths must be bounded canonical absolute POSIX paths."
        raise ValueError(msg)
    return path


@dataclass(frozen=True, slots=True)
class CliWorkspace:
    """Syntactic roots only: the host must verify real paths and mount authority."""

    job_root: str
    workspace: str
    scratch: str
    artifacts: str

    def __post_init__(self) -> None:
        """Reject ambiguous or overlapping root intent."""
        root = validate_cli_path(self.job_root)
        children = tuple(validate_cli_path(value) for value in (self.workspace, self.scratch, self.artifacts))
        if root == PurePosixPath("/") or any(root not in child.parents for child in children):
            msg = "Workspace, scratch and artifacts must be strict children of the job root."
            raise ValueError(msg)
        if any(a == b or a in b.parents or b in a.parents for i, a in enumerate(children) for b in children[i + 1 :]):
            msg = "CLI workspace roots must be disjoint."
            raise ValueError(msg)


def validate_cli_model(model: str) -> None:
    """Require an explicit model identity without interpreting vendor settings."""
    if (
        type(model) is not str
        or not model
        or model.startswith("-")
        or len(model.encode()) > _MAX_MODEL_BYTES
        or any(not (char.isascii() and (char.isalnum() or char in "._:/-")) for char in model)
    ):
        msg = "An explicit bounded model identifier is required."
        raise ValueError(msg)
