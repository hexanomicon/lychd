from __future__ import annotations

import json
from pathlib import PurePosixPath

import pytest

from lychd.system.delegation.nono import (
    GuestCommand,
    NonoCapability,
    NonoCommandCompiler,
    RawNonoObservation,
    ValidatedNonoRuntime,
    observe_nono,
)
from lychd.system.delegation.policy import (
    CoffinFilesystemPolicy,
    CoffinNetworkPolicy,
    CoffinPolicy,
    CoffinProfile,
    CoffinResourcePolicy,
    GateEndpoint,
)
from lychd.system.host_tools import TrustedExecutable


def _observation(
    *,
    version: str = "0.66.0",
    landlock_abi: int = 6,
    capabilities: frozenset[NonoCapability] | None = None,
) -> RawNonoObservation:
    return RawNonoObservation(
        version=version,
        landlock_abi=landlock_abi,
        capabilities=frozenset(NonoCapability) if capabilities is None else capabilities,
    )


def _runtime() -> ValidatedNonoRuntime:
    return ValidatedNonoRuntime.from_observation(
        TrustedExecutable("/usr/bin/nono", device=1, inode=2),
        _observation(),
    )


def _policy() -> CoffinPolicy:
    filesystem = CoffinFilesystemPolicy.for_profile(
        CoffinProfile.CANDIDATE,
        job_root=PurePosixPath("/var/lib/lychd/coffins/job-1"),
        workspace_root=PurePosixPath("/var/lib/lychd/coffins/job-1/workspace"),
        scratch_root=PurePosixPath("/var/lib/lychd/coffins/job-1/scratch"),
        artifacts_root=PurePosixPath("/var/lib/lychd/coffins/job-1/artifacts"),
    )
    return CoffinPolicy(
        job_id="job-1",
        profile=CoffinProfile.CANDIDATE,
        filesystem=filesystem,
        network=CoffinNetworkPolicy(GateEndpoint("gate.lychd.invalid")),
        resources=CoffinResourcePolicy(
            memory_bytes=1024**3,
            cpu_seconds=300,
            wall_time_seconds=600,
            max_processes=32,
            max_file_size_bytes=1024**3,
            max_output_bytes=1024**2,
        ),
    )


class _Observer:
    def __init__(self, observation: RawNonoObservation) -> None:
        self.observation = observation
        self.received: TrustedExecutable | None = None

    def observe(self, executable: TrustedExecutable) -> RawNonoObservation:
        self.received = executable
        return self.observation


def test_startup_observation_binds_attested_executable_to_supported_contract() -> None:
    executable = TrustedExecutable("/usr/bin/nono", device=7, inode=11)
    observer = _Observer(_observation())

    runtime = observe_nono(executable, observer)

    assert observer.received is executable
    assert runtime.executable is executable
    assert runtime.version == (0, 66, 0)


@pytest.mark.parametrize(
    "observation",
    [
        _observation(version="0.67.0"),
        _observation(version="nono 0.66.0"),
        _observation(landlock_abi=5),
        _observation(capabilities=frozenset(NonoCapability) - {NonoCapability.PROCESS_INFO_SCOPING}),
    ],
)
def test_startup_observation_fails_closed_on_contract_drift(observation: RawNonoObservation) -> None:
    with pytest.raises(ValueError, match="nono|Landlock|capabilities|version"):
        ValidatedNonoRuntime.from_observation(
            TrustedExecutable("/usr/bin/nono", device=1, inode=2),
            observation,
        )


def test_compiler_emits_literal_nono_066_argv_and_fail_closed_profile() -> None:
    compiler = NonoCommandCompiler(PurePosixPath("/run/lychd/nono-profiles"))
    command = GuestCommand(("/opt/agents/codex", "exec", "--profile=/tmp/evil"))

    first = compiler.compile(_runtime(), _policy(), command)
    second = compiler.compile(_runtime(), _policy(), command)
    document = json.loads(first.profile_document)

    assert first == second
    assert first.argv == (
        "/usr/bin/nono",
        "run",
        "--silent",
        "--profile",
        "/run/lychd/nono-profiles/job-1.json",
        "--workdir",
        "/var/lib/lychd/coffins/job-1/workspace",
        "--",
        "/opt/agents/codex",
        "exec",
        "--profile=/tmp/evil",
    )
    assert document["filesystem"]["allow"] == [
        "/var/lib/lychd/coffins/job-1/workspace",
        "/var/lib/lychd/coffins/job-1/scratch",
        "/var/lib/lychd/coffins/job-1/artifacts",
    ]
    assert document["network"]["allow_domain"] == [
        {
            "domain": "gate.lychd.invalid",
            "endpoints": [{"method": "POST", "path": "/v1/delegation/**"}],
        }
    ]
    assert "deny_credentials" in document["groups"]["include"]
    assert "user_tools" not in document["groups"]["include"]
    assert document["security"] == {
        "capability_elevation": False,
        "process_info_mode": "isolated",
        "signal_mode": "isolated",
    }
    assert document["linux"]["af_unix_mediation"] == "pathname"
    assert first.requires_outer_resource_enforcement is True


def test_compiled_material_never_contains_a_provider_credential() -> None:
    invocation = NonoCommandCompiler(PurePosixPath("/run/lychd/nono-profiles")).compile(
        _runtime(),
        _policy(),
        GuestCommand(("/opt/agents/codex",)),
    )
    secret = b"sk-live-this-must-never-cross-the-coffin"

    assert secret not in invocation.profile_document
    assert all(secret.decode() not in value for value in invocation.argv)


@pytest.mark.parametrize(
    "argv",
    [
        (),
        ("codex",),
        ("/opt/agents/codex\n/bin/sh",),
        ("/opt/agents/codex", ""),
        ("/opt/agents/../bin/codex",),
    ],
)
def test_guest_command_rejects_resolution_and_control_attacks(argv: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="Guest|guest"):
        GuestCommand(argv)


def test_profile_root_must_be_canonical_and_confined() -> None:
    with pytest.raises(ValueError, match="canonical|traversal"):
        NonoCommandCompiler(PurePosixPath("/run/lychd/../etc"))
