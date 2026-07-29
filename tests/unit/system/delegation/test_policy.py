from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import PurePosixPath

import pytest

from lychd.system.delegation.policy import (
    CoffinFilesystemPolicy,
    CoffinNetworkPolicy,
    CoffinProfile,
    CoffinResourcePolicy,
    FilesystemAccess,
    FilesystemGrant,
    GateEndpoint,
    confined_absolute_path,
)


def _filesystem(profile: CoffinProfile = CoffinProfile.CANDIDATE) -> CoffinFilesystemPolicy:
    return CoffinFilesystemPolicy.for_profile(
        profile,
        job_root=PurePosixPath("/var/lib/lychd/coffins/job-1"),
        workspace_root=PurePosixPath("/var/lib/lychd/coffins/job-1/workspace"),
        scratch_root=PurePosixPath("/var/lib/lychd/coffins/job-1/scratch"),
        artifacts_root=PurePosixPath("/var/lib/lychd/coffins/job-1/artifacts"),
    )


@pytest.mark.parametrize(
    ("profile", "workspace_access"),
    [
        (CoffinProfile.READ, FilesystemAccess.READ),
        (CoffinProfile.CANDIDATE, FilesystemAccess.READ_WRITE),
        (CoffinProfile.VERIFY, FilesystemAccess.READ),
    ],
)
def test_profiles_fix_workspace_authority(
    profile: CoffinProfile,
    workspace_access: FilesystemAccess,
) -> None:
    policy = _filesystem(profile)

    assert policy.grants[0].access is workspace_access
    assert policy.grants[1].access is FilesystemAccess.READ_WRITE
    assert policy.grants[2].access is FilesystemAccess.READ_WRITE


@pytest.mark.parametrize(
    "attack",
    [
        "relative/workspace",
        "/",
        "/var/lib/../etc",
        "/var//lib/workspace",
        "/var/lib/workspace/",
        "/var/lib/work space",
        "/var/lib/workspace\n/etc",
        r"/var/lib\workspace",
    ],
)
def test_confined_paths_reject_ambiguous_or_escaping_values(attack: str) -> None:
    with pytest.raises(ValueError, match="canonical|traversal"):
        confined_absolute_path(attack, field="attack")


def test_filesystem_roots_must_be_job_local_and_disjoint() -> None:
    with pytest.raises(ValueError, match="strict children"):
        CoffinFilesystemPolicy.for_profile(
            CoffinProfile.READ,
            job_root=PurePosixPath("/var/lib/lychd/coffins/job-1"),
            workspace_root=PurePosixPath("/etc"),
            scratch_root=PurePosixPath("/var/lib/lychd/coffins/job-1/scratch"),
            artifacts_root=PurePosixPath("/var/lib/lychd/coffins/job-1/artifacts"),
        )

    with pytest.raises(ValueError, match="disjoint"):
        CoffinFilesystemPolicy.for_profile(
            CoffinProfile.READ,
            job_root=PurePosixPath("/var/lib/lychd/coffins/job-1"),
            workspace_root=PurePosixPath("/var/lib/lychd/coffins/job-1/workspace"),
            scratch_root=PurePosixPath("/var/lib/lychd/coffins/job-1/workspace/scratch"),
            artifacts_root=PurePosixPath("/var/lib/lychd/coffins/job-1/artifacts"),
        )


def test_policy_values_are_immutable() -> None:
    policy = _filesystem()

    with pytest.raises(FrozenInstanceError):
        policy.job_root = PurePosixPath("/var/lib/replaced")  # type: ignore[misc]


def test_read_profile_cannot_be_relabelled_with_write_authority() -> None:
    policy = _filesystem(CoffinProfile.READ)
    widened_workspace = FilesystemGrant(policy.workspace_root, FilesystemAccess.READ_WRITE)

    with pytest.raises(ValueError, match="selected coffin profile"):
        replace(policy, grants=(widened_workspace, *policy.grants[1:]))


def test_profile_and_resource_types_fail_closed() -> None:
    with pytest.raises(TypeError, match="fixed coffin profile"):
        replace(_filesystem(), profile="candidate")
    with pytest.raises(ValueError, match="memory_bytes"):
        CoffinResourcePolicy(
            memory_bytes=1.5,  # type: ignore[arg-type]
            cpu_seconds=300,
            wall_time_seconds=600,
            max_processes=32,
            max_file_size_bytes=1024**3,
            max_output_bytes=1024**2,
        )


def test_provider_gate_is_the_only_permitted_network_target() -> None:
    endpoint = GateEndpoint("gate.lychd.invalid")

    assert CoffinNetworkPolicy(endpoint).direct_provider_access is False
    with pytest.raises(ValueError, match="direct provider"):
        CoffinNetworkPolicy(endpoint, direct_provider_access=True)
    with pytest.raises(ValueError, match="TLS"):
        GateEndpoint("gate.lychd.invalid", port=80, tls=False)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("memory_bytes", 64 * 1024**3 + 1),
        ("cpu_seconds", 86_401),
        ("wall_time_seconds", 14_401),
        ("max_processes", 257),
        ("max_file_size_bytes", 8 * 1024**3 + 1),
        ("max_output_bytes", 64 * 1024**2 + 1),
    ],
)
def test_resource_policy_rejects_ceiling_bypass(field: str, value: int) -> None:
    values = {
        "memory_bytes": 1024**3,
        "cpu_seconds": 300,
        "wall_time_seconds": 600,
        "max_processes": 32,
        "max_file_size_bytes": 1024**3,
        "max_output_bytes": 1024**2,
    }
    values[field] = value

    with pytest.raises(ValueError, match=field):
        CoffinResourcePolicy(**values)
