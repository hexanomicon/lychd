"""Pure compiler and observation boundary for the nono 0.66 contract."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Final, Protocol

from lychd.system.delegation.policy import (
    CoffinPolicy,
    CoffinResourcePolicy,
    FilesystemAccess,
    confined_absolute_path,
)
from lychd.system.host_tools import TrustedExecutable

_SUPPORTED_NONO_SERIES: Final[tuple[int, int]] = (0, 66)
_MIN_LANDLOCK_ABI: Final[int] = 6
_VERSION: Final[re.Pattern[str]] = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)")
_MAX_ARGUMENTS: Final[int] = 256
_MAX_ARGUMENT_BYTES: Final[int] = 32_768
_SEMANTIC_VERSION_PARTS: Final[int] = 3
_ALLOWED_ENVIRONMENT: Final[tuple[str, ...]] = (
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "TERM",
    "TMPDIR",
    "LYCHD_GATE_ENDPOINT",
    "LYCHD_GATE_GRANT",
)
_DENIED_ENVIRONMENT: Final[tuple[str, ...]] = (
    "ANTHROPIC_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AZURE_OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)


class NonoCapability(StrEnum):
    FILESYSTEM = "filesystem"
    TCP_NETWORK = "tcp_network"
    SIGNAL_SCOPING = "signal_scoping"
    PROCESS_INFO_SCOPING = "process_info_scoping"
    ENDPOINT_POLICY = "endpoint_policy"
    ENVIRONMENT_FILTERING = "environment_filtering"


_REQUIRED_CAPABILITIES: Final[frozenset[NonoCapability]] = frozenset(NonoCapability)


@dataclass(frozen=True, slots=True)
class RawNonoObservation:
    """Structured output supplied by a startup probe adapter."""

    version: str
    landlock_abi: int
    capabilities: frozenset[NonoCapability]


class NonoObservationPort(Protocol):
    """Effect boundary for the startup version/capability probe."""

    def observe(self, executable: TrustedExecutable) -> RawNonoObservation: ...


@dataclass(frozen=True, slots=True)
class ValidatedNonoRuntime:
    """An attested executable whose observed runtime satisfies our contract."""

    executable: TrustedExecutable
    version: tuple[int, int, int]
    landlock_abi: int
    capabilities: frozenset[NonoCapability]

    def __post_init__(self) -> None:
        """Reject runtime observations outside the audited nono contract."""
        if (
            len(self.version) != _SEMANTIC_VERSION_PARTS
            or any(not _is_nonnegative_integer(part) for part in self.version)
            or not _is_nonnegative_integer(self.landlock_abi)
        ):
            message = "nono runtime version and Landlock ABI must be non-negative integers"
            raise TypeError(message)
        if self.version[:2] != _SUPPORTED_NONO_SERIES:
            message = "Only the audited nono 0.66 series is accepted"
            raise ValueError(message)
        if self.landlock_abi < _MIN_LANDLOCK_ABI:
            message = "nono requires Landlock ABI 6 or newer"
            raise ValueError(message)
        missing = _REQUIRED_CAPABILITIES - self.capabilities
        if missing:
            names = ", ".join(sorted(capability.value for capability in missing))
            message = f"nono is missing required capabilities: {names}"
            raise ValueError(message)

    @classmethod
    def from_observation(
        cls,
        executable: TrustedExecutable,
        observation: RawNonoObservation,
    ) -> ValidatedNonoRuntime:
        match = _VERSION.fullmatch(observation.version)
        if match is None:
            message = "nono version must be a complete semantic version"
            raise ValueError(message)
        version = (
            int(match["major"]),
            int(match["minor"]),
            int(match["patch"]),
        )
        return cls(
            executable=executable,
            version=version,
            landlock_abi=observation.landlock_abi,
            capabilities=observation.capabilities,
        )


def observe_nono(executable: TrustedExecutable, observer: NonoObservationPort) -> ValidatedNonoRuntime:
    """Observe once at startup and fail closed before accepting coffin work."""
    return ValidatedNonoRuntime.from_observation(executable, observer.observe(executable))


@dataclass(frozen=True, slots=True)
class GuestCommand:
    """A literal argv; shells and relative executable resolution are excluded."""

    argv: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject shell-style resolution, controls, and unbounded argv."""
        if not self.argv or len(self.argv) > _MAX_ARGUMENTS:
            message = "Guest command must contain between 1 and 256 arguments"
            raise ValueError(message)
        confined_absolute_path(self.argv[0], field="guest executable")
        for argument in self.argv:
            encoded = argument.encode("utf-8")
            if (
                not encoded
                or len(encoded) > _MAX_ARGUMENT_BYTES
                or "\x00" in argument
                or "\n" in argument
                or "\r" in argument
            ):
                message = "Guest argv contains an empty, oversized, or control-bearing argument"
                raise ValueError(message)


@dataclass(frozen=True, slots=True)
class NonoInvocation:
    """Compiled inputs for a future supervisor; this object launches nothing."""

    argv: tuple[str, ...]
    profile_path: PurePosixPath
    profile_document: bytes
    environment_names: tuple[str, ...]
    resources: CoffinResourcePolicy
    requires_outer_resource_enforcement: bool = True

    def __post_init__(self) -> None:
        """Keep the resource-supervisor requirement non-optional."""
        if not self.requires_outer_resource_enforcement:
            message = "Coffin resource enforcement cannot be disabled"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class NonoCommandCompiler:
    """Compile policy to the audited nono 0.66 profile/argv shape."""

    profile_root: PurePosixPath

    def __post_init__(self) -> None:
        """Canonicalize the trusted-plane profile materialization root."""
        object.__setattr__(
            self,
            "profile_root",
            confined_absolute_path(self.profile_root, field="nono profile root"),
        )

    def compile(
        self,
        runtime: ValidatedNonoRuntime,
        policy: CoffinPolicy,
        command: GuestCommand,
    ) -> NonoInvocation:
        # Re-run invariants so a hand-constructed runtime cannot weaken startup checks.
        ValidatedNonoRuntime(
            executable=runtime.executable,
            version=runtime.version,
            landlock_abi=runtime.landlock_abi,
            capabilities=runtime.capabilities,
        )
        profile_path = self.profile_root / f"{policy.job_id}.json"
        if profile_path.parent != self.profile_root:
            message = "Derived nono profile path escaped its control root"
            raise ValueError(message)
        profile_document = _compile_profile(policy)
        argv = (
            runtime.executable.path,
            "run",
            "--silent",
            "--profile",
            str(profile_path),
            "--workdir",
            str(policy.filesystem.workspace_root),
            "--",
            *command.argv,
        )
        return NonoInvocation(
            argv=argv,
            profile_path=profile_path,
            profile_document=profile_document,
            environment_names=_ALLOWED_ENVIRONMENT,
            resources=policy.resources,
        )


def _compile_profile(policy: CoffinPolicy) -> bytes:
    filesystem: dict[str, list[str]] = {"read": [], "write": [], "allow": []}
    access_key = {
        FilesystemAccess.READ: "read",
        FilesystemAccess.WRITE: "write",
        FilesystemAccess.READ_WRITE: "allow",
    }
    for grant in policy.filesystem.grants:
        filesystem[access_key[grant.access]].append(str(grant.path))

    gate = policy.network.gate
    document = {
        "meta": {
            "description": "LychD bounded delegated-agent coffin",
            "name": f"lychd-coffin-{policy.job_id}",
            "version": "1.0.0",
        },
        "groups": {
            "include": [
                "deny_credentials",
                "deny_keychains_linux",
                "deny_browser_data_linux",
                "deny_shell_history",
                "deny_shell_configs",
                "system_read_linux_core",
            ]
        },
        "filesystem": filesystem,
        "network": {
            "allow_domain": [
                {
                    "domain": gate.host,
                    "endpoints": [{"method": "POST", "path": gate.request_path}],
                }
            ]
        },
        "environment": {
            "allow_vars": list(_ALLOWED_ENVIRONMENT),
            "deny_vars": list(_DENIED_ENVIRONMENT),
        },
        "security": {
            "capability_elevation": False,
            "process_info_mode": "isolated",
            "signal_mode": "isolated",
        },
        "linux": {"af_unix_mediation": "pathname"},
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def _is_nonnegative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


__all__ = (
    "GuestCommand",
    "NonoCapability",
    "NonoCommandCompiler",
    "NonoInvocation",
    "NonoObservationPort",
    "RawNonoObservation",
    "ValidatedNonoRuntime",
    "observe_nono",
)
