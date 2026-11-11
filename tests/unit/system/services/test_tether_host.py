"""Native host effect ports reject foreign incarnations and prove subtree closure."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest

from lychd.system.operator.process import ProcessResult
from lychd.system.services.tether import host
from lychd.system.services.tether.models import TetherError

if TYPE_CHECKING:
    from lychd.domain.tether.compiler import RuntimeConfig

IDENTITY = "a" * 64
OTHER = "b" * 64
IMAGE = "c" * 64
POD = "d" * 64
NAME = "lychd-tether-1234567890abcdef-ssh-123456789abc"
UNIT_GROUP = f"/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/app.slice/{NAME}.service"
INVOCATION = "f" * 32
DIGEST = "sha256:" + "e" * 64


def retained() -> dict[str, Any]:
    return {
        "container_id": IDENTITY,
        "container_name": NAME,
        "unit_name": NAME + ".service",
        "pod_id": POD,
        "image_id": IMAGE,
        "netns": 20,
        "invocation_id": INVOCATION,
        "unit_cgroup": UNIT_GROUP,
        "cgroup": f"/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/app.slice/libpod-{IDENTITY}.scope",
    }


def container() -> dict[str, Any]:
    return {
        "Id": IDENTITY,
        "Name": NAME,
        "Image": IMAGE,
        "ImageDigest": DIGEST,
        "Pod": POD,
        "State": {"Running": True, "Pid": 1234},
    }


class Runner:
    def __init__(self) -> None:
        """Observe argv without executing any host process."""
        self.calls: list[tuple[str, ...]] = []
        self.outcomes: dict[tuple[str, ...], ProcessResult] = {}

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        assert timeout_s > 0
        self.calls.append(argv)
        command = argv[1:]
        if argv[0] == "/tools/podman":
            assert command[0] == "--remote=false"
            command = command[1:]
        return self.outcomes.get(command, ProcessResult(argv, 0))

    def run_with_input(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        input_text: str,
    ) -> ProcessResult:
        del argv, timeout_s, input_text
        pytest.fail("Host control must not send secret input")


@pytest.fixture
def port(monkeypatch: pytest.MonkeyPatch) -> tuple[host.TetherHost, Runner]:
    runner = Runner()

    def fake_trusted_host_tool(name: str) -> str:
        return "/tools/" + name

    monkeypatch.setattr(host, "trusted_host_tool", fake_trusted_host_tool)
    service = host.TetherHost(runner)

    def fake_owned_unit(_name: str) -> dict[str, str]:
        return {
            "LoadState": "loaded",
            "ActiveState": "inactive",
            "SubState": "dead",
            "MainPID": "0",
            "ControlPID": "0",
            "Job": "0",
        }

    monkeypatch.setattr(
        service,
        "owned_unit",
        fake_owned_unit,
    )

    def fake_unit_incarnation(name: str) -> dict[str, str]:
        return {
            "InvocationID": INVOCATION,
            "ControlGroup": UNIT_GROUP if name == NAME + ".service" else UNIT_GROUP.rsplit("/", 1)[0] + "/" + name,
        }

    monkeypatch.setattr(
        service,
        "unit_incarnation",
        fake_unit_incarnation,
    )

    def fake_unit_closed(_name: str) -> bool:
        return False

    monkeypatch.setattr(service, "_unit_closed", fake_unit_closed)
    return service, runner


@pytest.mark.parametrize(
    ("variable", "value"),
    [("CONTAINER_HOST", "ssh://foreign.invalid/run/podman.sock"), ("CONTAINER_CONNECTION", "foreign-engine")],
)
def test_host_observations_force_local_engine_despite_ambient_connections(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    service, runner = port
    monkeypatch.setenv(variable, value)
    runner.outcomes[("container", "inspect", IDENTITY)] = ProcessResult((), 0, json.dumps([container()]))
    runner.outcomes[("pod", "exists", POD)] = ProcessResult((), 1)
    assert service.row("container", IDENTITY) == container()
    assert service.exists("container", IDENTITY)
    assert not service.exists("pod", POD)
    service.command("podman", "exec", IDENTITY, "true")
    service.command("systemctl", "--user", "show", NAME + ".service")
    service.command("ip", "-j", "-4", "address", "show")
    assert runner.calls == [
        ("/tools/podman", "--remote=false", "container", "inspect", IDENTITY),
        ("/tools/podman", "--remote=false", "container", "exists", IDENTITY),
        ("/tools/podman", "--remote=false", "pod", "exists", POD),
        ("/tools/podman", "--remote=false", "exec", IDENTITY, "true"),
        ("/tools/systemctl", "--user", "show", NAME + ".service"),
        ("/tools/ip", "-j", "-4", "address", "show"),
    ]


def test_absence_distinguishes_uncertainty(
    port: tuple[host.TetherHost, Runner],
) -> None:
    service, runner = port
    command = ("container", "exists", IDENTITY)
    runner.outcomes[command] = ProcessResult((), 1)
    assert not service.exists("container", IDENTITY)
    runner.outcomes[command] = ProcessResult((), 125, stderr="private diagnostic")
    with pytest.raises(TetherError, match="uncertain"):
        service.exists("container", IDENTITY)


def test_command_refuses_failure_without_reflecting_private_diagnostics(
    port: tuple[host.TetherHost, Runner],
) -> None:
    service, runner = port
    runner.outcomes[("container", "inspect", IDENTITY)] = ProcessResult((), 125, "private stdout", "private stderr")
    with pytest.raises(TetherError, match="suppressed") as failure:
        service.command("podman", "container", "inspect", IDENTITY)
    assert "private stdout" not in str(failure.value)
    assert "private stderr" not in str(failure.value)


def test_stop_refuses_named_replacement_when_retained_id_is_absent(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port

    def fake_exists(_kind: str, identity: str) -> bool:
        return identity == NAME

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_row(_kind: str, _identity: str) -> dict[str, Any]:
        return {**container(), "Id": OTHER}

    monkeypatch.setattr(service, "row", fake_row)

    def fake_cgroup_empty(_group: str) -> bool:
        return True

    monkeypatch.setattr(service, "cgroup_empty", fake_cgroup_empty)
    with pytest.raises(TetherError):
        service.stop(retained())
    assert not runner.calls


def test_stop_refuses_foreign_unit_before_any_effect(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port

    def fake_exists(_kind: str, _identity: str) -> bool:
        return True

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_row(_kind: str, _identity: str) -> dict[str, Any]:
        return container()

    monkeypatch.setattr(service, "row", fake_row)

    def fake_cgroup_empty(_group: str) -> bool:
        return True

    monkeypatch.setattr(service, "cgroup_empty", fake_cgroup_empty)
    record = retained()
    record["unit_name"] = "lychd-vessel.service"
    with pytest.raises(TetherError):
        service.stop(record)
    assert not runner.calls


@pytest.mark.parametrize("field", ["Id", "Image", "Pod", "Name"])
def test_stop_refuses_changed_incarnation_before_effect(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    service, runner = port
    row = container()
    row[field] = OTHER

    def fake_exists(_kind: str, _identity: str) -> bool:
        return True

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_row(_kind: str, _identity: str) -> dict[str, Any]:
        return row

    monkeypatch.setattr(service, "row", fake_row)
    with pytest.raises(TetherError):
        service.stop(retained())
    assert not runner.calls


def test_stop_refuses_name_rebound_to_other_container(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port

    def fake_exists(_kind: str, _identity: str) -> bool:
        return True

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_row(_kind: str, identity: str) -> dict[str, Any]:
        return container() if identity == IDENTITY else {**container(), "Id": OTHER}

    monkeypatch.setattr(
        service,
        "row",
        fake_row,
    )
    with pytest.raises(TetherError):
        service.stop(retained())
    assert not runner.calls


def test_repeated_stop_of_absent_incarnation_cancels_restart(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port

    def fake_exists(_kind: str, _identity: str) -> bool:
        return False

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_cgroup_empty(_group: str) -> bool:
        return True

    monkeypatch.setattr(service, "cgroup_empty", fake_cgroup_empty)
    service.stop(retained())
    service.stop(retained())
    assert runner.calls == [("/tools/systemctl", "--user", "stop", NAME + ".service")] * 2


def test_stop_waits_for_entire_retained_cgroup(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port
    observations: list[str] = []

    def fake_exists(_kind: str, _identity: str) -> bool:
        return not runner.calls

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_row(_kind: str, _identity: str) -> dict[str, Any]:
        return container()

    monkeypatch.setattr(service, "row", fake_row)

    def empty(group: str) -> bool:
        observations.append(group)
        return len(observations) > 1

    monkeypatch.setattr(service, "cgroup_empty", empty)

    def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(host.time, "sleep", fake_sleep)
    service.stop(retained())
    assert observations == [retained()["cgroup"], retained()["cgroup"]]
    assert runner.calls == [("/tools/systemctl", "--user", "stop", NAME + ".service")]


def test_stop_does_not_claim_closure_while_descendants_survive(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port

    def fake_exists(_kind: str, _identity: str) -> bool:
        return True

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_row(_kind: str, _identity: str) -> dict[str, Any]:
        return container()

    monkeypatch.setattr(service, "row", fake_row)

    def fake_cgroup_empty(_group: str) -> bool:
        return False

    monkeypatch.setattr(service, "cgroup_empty", fake_cgroup_empty)
    times = iter((0.0, 11.0))
    monkeypatch.setattr(host.time, "monotonic", lambda: next(times))
    with pytest.raises(TetherError, match="closure"):
        service.stop(retained())
    assert runner.calls == [("/tools/systemctl", "--user", "stop", NAME + ".service")]


def test_cgroup_observer_includes_descendant_tasks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    group = f"/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/app.slice/libpod-{IDENTITY}.scope"
    root = tmp_path / group.lstrip("/")
    child = root / "nested"
    child.mkdir(parents=True)
    (root / "cgroup.procs").write_text("")
    (child / "cgroup.procs").write_text("1234\n")
    original = Path

    def fake_path(value: str) -> Path:
        return tmp_path if str(value) == "/sys/fs/cgroup" else original(value)

    monkeypatch.setattr(
        host,
        "Path",
        fake_path,
    )
    assert not host.TetherHost.cgroup_empty(group)
    (child / "cgroup.procs").write_text("")
    assert host.TetherHost.cgroup_empty(group)


def test_capture_rejects_host_or_core_namespace(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _runner = port
    config = cast("RuntimeConfig", SimpleNamespace(name=NAME))
    image = {"id": IMAGE, "digest": DIGEST}
    rows = {
        ("container", NAME): container(),
        ("pod", "lychd-tether-1234567890abcdef"): {
            "Id": POD,
            "Name": "lychd-tether-1234567890abcdef",
        },
        ("container", IDENTITY): container(),
        ("container", "lychd-vessel"): {"State": {"Pid": 4321}},
    }

    def fake_row(kind: str, identity: str) -> dict[str, Any]:
        return rows[kind, identity]

    monkeypatch.setattr(service, "row", fake_row)

    def fake_exists(_kind: str, _identity: str) -> bool:
        return True

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_process_cgroup(_pid: int) -> str:
        return retained()["cgroup"]

    monkeypatch.setattr(service, "process_cgroup", fake_process_cgroup)

    def fake_unit_incarnation(_name: str) -> dict[str, str]:
        return {"InvocationID": INVOCATION, "ControlGroup": UNIT_GROUP}

    monkeypatch.setattr(
        service,
        "unit_incarnation",
        fake_unit_incarnation,
    )
    namespaces = {
        "/proc/self/ns/net": 10,
        "/proc/1234/ns/net": 10,
        "/proc/4321/ns/net": 30,
    }

    def fake_path(*values: str) -> Path | SimpleNamespace:
        return (
            SimpleNamespace(stat=lambda: SimpleNamespace(st_ino=namespaces[values[0]]))
            if len(values) == 1 and values[0] in namespaces
            else Path(*values)
        )

    monkeypatch.setattr(
        host,
        "Path",
        fake_path,
    )
    with pytest.raises(TetherError, match="host network"):
        service.capture(config, image)
    namespaces["/proc/1234/ns/net"] = 30
    with pytest.raises(TetherError, match="Core network"):
        service.capture(config, image)
    namespaces["/proc/1234/ns/net"] = 20
    result = service.capture(config, image)
    assert result == retained()


def test_observe_requires_exact_generation_and_policy(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _runner = port
    payload = {
        "role": "imported-relay",
        "network_id": "remote",
        "installation_epoch": "f" * 32,
        "generation": 3,
        "policy_digest": "e" * 64,
    }
    config = cast("RuntimeConfig", SimpleNamespace(name=NAME, payload=payload))
    response = {**payload, "enabled": True}

    def fake_command(*_args: str) -> str:
        return json.dumps(response)

    monkeypatch.setattr(service, "command", fake_command)
    assert service.observe(config) == response
    response["generation"] = 2
    with pytest.raises(TetherError, match="acknowledged"):
        service.observe(config)
    response["generation"] = 3
    response["policy_digest"] = "d" * 64
    with pytest.raises(TetherError, match="acknowledged"):
        service.observe(config)


@pytest.mark.parametrize("suffix", [f"libpod-{IDENTITY}.scope", f"{NAME}.service/libpod-payload-{IDENTITY}"])
def test_exact_payload_subtree_includes_nested_children(suffix: str) -> None:
    prefix = UNIT_GROUP.rsplit("/", 1)[0]
    expected = prefix + "/" + suffix
    assert host._container_group(expected + "/nested", IDENTITY, UNIT_GROUP) == expected  # pyright: ignore[reportPrivateUsage] - exact subtree boundary probe


@pytest.mark.parametrize(
    "group",
    [
        "/system.slice/foreign.service",
        UNIT_GROUP + "/libpod-payload-" + OTHER,
        UNIT_GROUP,
    ],
)
def test_foreign_or_broad_cgroup_refused(group: str) -> None:
    with pytest.raises(TetherError):
        host._container_group(group, IDENTITY, UNIT_GROUP)  # pyright: ignore[reportPrivateUsage] - direct negative boundary probe


def test_stop_refuses_new_unit_invocation(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port

    def fake_exists(_kind: str, _identity: str) -> bool:
        return False

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_cgroup_empty(_group: str) -> bool:
        return True

    monkeypatch.setattr(service, "cgroup_empty", fake_cgroup_empty)

    def fake_unit_incarnation(_name: str) -> dict[str, str]:
        return {"InvocationID": "1" * 32, "ControlGroup": UNIT_GROUP}

    monkeypatch.setattr(
        service,
        "unit_incarnation",
        fake_unit_incarnation,
    )
    with pytest.raises(TetherError):
        service.stop(retained())
    assert not runner.calls


@pytest.mark.parametrize("extra", ["InvocationID=duplicate\n", "Unknown=field\n", "Id=foreign.service\n"])
def test_unit_incarnation_refuses_ambiguous_fields(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, extra: str
) -> None:
    service, _runner = port
    content = f"Id={NAME}.service\nInvocationID={INVOCATION}\nControlGroup={UNIT_GROUP}\n" + extra

    def fake_command(*_args: str) -> str:
        return content

    monkeypatch.setattr(service, "command", fake_command)
    with pytest.raises(TetherError):
        host.TetherHost.unit_incarnation(service, NAME + ".service")


def test_unit_incarnation_retains_exact_values(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _runner = port
    content = f"Id={NAME}.service\nInvocationID={INVOCATION}\nControlGroup={UNIT_GROUP}\n"

    def fake_command(*_args: str) -> str:
        return content

    monkeypatch.setattr(service, "command", fake_command)
    assert host.TetherHost.unit_incarnation(service, NAME + ".service") == {
        "InvocationID": INVOCATION,
        "ControlGroup": UNIT_GROUP,
    }


def pod_retained() -> dict[str, Any]:
    name = "lychd-tether-1234567890abcdef"
    return {
        "pod_id": POD,
        "pod_name": name,
        "unit_name": name + "-pod.service",
        "infra_id": IDENTITY,
        "infra_cgroup": retained()["cgroup"],
        "netns": 20,
        "invocation_id": INVOCATION,
        "unit_cgroup": UNIT_GROUP.rsplit("/", 1)[0] + "/" + name + "-pod.service",
    }


def test_pod_stop_refuses_foreign_members(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port
    record = pod_retained()

    def fake_exists(_kind: str, _identity: str) -> bool:
        return True

    monkeypatch.setattr(service, "exists", fake_exists)
    row = {
        "Id": POD,
        "Name": record["pod_name"],
        "InfraContainerID": IDENTITY,
        "Containers": [{"Id": IDENTITY}, {"Id": OTHER}],
    }

    def fake_row(_kind: str, _identity: str) -> dict[str, Any]:
        return row

    monkeypatch.setattr(service, "row", fake_row)
    with pytest.raises(TetherError):
        service.stop_pod(record)
    assert not runner.calls


def test_pod_stop_refuses_name_replacement(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port
    record = pod_retained()

    def fake_exists(_kind: str, identity: str) -> bool:
        return identity == record["pod_name"]

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_row(_kind: str, _identity: str) -> dict[str, Any]:
        return {"Id": OTHER}

    monkeypatch.setattr(service, "row", fake_row)
    with pytest.raises(TetherError):
        service.stop_pod(record)
    assert not runner.calls


@pytest.mark.parametrize("pod", [False, True])
def test_repeated_stop_after_binding_retired_has_no_effect(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, *, pod: bool
) -> None:
    service, runner = port

    def fake_exists(_kind: str, _identity: str) -> bool:
        return False

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_cgroup_empty(_group: str) -> bool:
        return True

    monkeypatch.setattr(service, "cgroup_empty", fake_cgroup_empty)

    def fake_unit_closed(_name: str) -> bool:
        return True

    monkeypatch.setattr(service, "_unit_closed", fake_unit_closed)

    def fake_owned_unit(_name: str) -> dict[str, str]:
        return pytest.fail("Retired binding must not need ownership")

    monkeypatch.setattr(service, "owned_unit", fake_owned_unit)
    if pod:
        assert service.pod_closed(pod_retained())
        service.stop_pod(pod_retained())
    else:
        assert service.closed(retained())
        service.stop(retained())
    assert not runner.calls


@pytest.mark.parametrize(
    ("load", "active", "job", "code", "expected"),
    [
        ("not-found", "inactive", "0", 4, True),
        ("loaded", "inactive", "0", 0, True),
        ("loaded", "active", "0", 0, False),
        ("loaded", "inactive", "42", 0, False),
    ],
)
def test_closed_unit_observation_requires_no_pending_restart(
    port: tuple[host.TetherHost, Runner], load: str, active: str, job: str, code: int, *, expected: bool
) -> None:
    service, runner = port
    props = ("Id", "LoadState", "ActiveState", "SubState", "MainPID", "ControlPID", "Job")
    argv = ("--user", "show", NAME + ".service", *("--property=" + key for key in props))
    values = (NAME + ".service", load, active, "dead", "0", "0", job)
    runner.outcomes[argv] = ProcessResult(
        (), code, "".join(key + "=" + value + "\n" for key, value in zip(props, values, strict=True))
    )
    assert host.TetherHost._unit_closed(service, NAME + ".service") is expected  # pyright: ignore[reportPrivateUsage] - bypass fixture replacement to exercise observation


@pytest.mark.parametrize("body_exists", [True, False])
def test_unretained_stop_never_adopts_a_body(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, *, body_exists: bool
) -> None:
    service, runner = port

    def fake_exists(_kind: str, _identity: str) -> bool:
        return body_exists

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_cgroup_empty(_group: str) -> bool:
        return True

    monkeypatch.setattr(service, "cgroup_empty", fake_cgroup_empty)
    if body_exists:
        with pytest.raises(TetherError):
            service.stop_unretained(NAME)
        assert not runner.calls
    else:
        service.stop_unretained(NAME)
        assert runner.calls == [("/tools/systemctl", "--user", "stop", NAME + ".service")]


def test_unretained_stop_quiescent_retired_unit_has_no_effect(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port

    def fake_exists(_kind: str, _identity: str) -> bool:
        return False

    monkeypatch.setattr(service, "exists", fake_exists)

    def fake_unit_closed(_name: str) -> bool:
        return True

    monkeypatch.setattr(service, "_unit_closed", fake_unit_closed)

    def fake_unit_incarnation(_name: str) -> dict[str, str]:
        return pytest.fail("No authority required for no effect")

    monkeypatch.setattr(service, "unit_incarnation", fake_unit_incarnation)
    service.stop_unretained(NAME)
    assert not runner.calls


@pytest.mark.parametrize("fault", ["none", "foreign-image", "foreign-cgroup", "changed-invocation", "inactive"])
def test_core_requires_image_and_current_owned_payload(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    service, runner = port
    core_group = UNIT_GROUP.rsplit("/", 1)[0] + "/lychd-vessel.service"
    row = {**container(), "Name": "lychd-vessel", "Image": OTHER if fault == "foreign-image" else IMAGE}

    def fake_row(kind: str, _identity: str) -> dict[str, Any]:
        return {"Id": IMAGE} if kind == "image" else row

    monkeypatch.setattr(service, "row", fake_row)

    def fake_owned_unit(_name: str) -> dict[str, str]:
        return {"LoadState": "loaded", "ActiveState": "inactive" if fault == "inactive" else "active"}

    monkeypatch.setattr(
        service,
        "owned_unit",
        fake_owned_unit,
    )
    calls: list[str] = []

    def incarnation(_name: str) -> dict[str, str]:
        calls.append(_name)
        return {
            "InvocationID": "1" * 32 if fault == "changed-invocation" and len(calls) > 1 else INVOCATION,
            "ControlGroup": core_group,
        }

    monkeypatch.setattr(service, "unit_incarnation", incarnation)

    def fake_process_cgroup(_pid: int) -> str:
        return (UNIT_GROUP if fault == "foreign-cgroup" else core_group) + "/libpod-payload-" + IDENTITY

    monkeypatch.setattr(
        service,
        "process_cgroup",
        fake_process_cgroup,
    )
    if fault == "none":
        service.require_core("example/core:admitted")
    else:
        with pytest.raises(TetherError):
            service.require_core("example/core:admitted")
    assert not runner.calls


class FailedRoleObservation(Runner):
    """Model terminal manager observations separately from body and cgroup absence."""

    def __init__(self, group: str = "") -> None:
        super().__init__()
        self.fields: dict[str, str] = {
            "Id": NAME + ".service",
            "LoadState": "loaded",
            "ActiveState": "failed",
            "SubState": "failed",
            "MainPID": "0",
            "ControlPID": "0",
            "Job": "",
            "NRestarts": "0",
            "InvocationID": INVOCATION,
            "ControlGroup": group,
        }
        self.owned_calls = 0
        self.groups: list[str] = []
        self.bodies: list[str] = []
        self.present: set[str] = set()
        self.nonempty: set[str] = set()
        self.drift: dict[str, str] = {}
        self.foreign_at = 0
        self.appear = ""

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        assert timeout_s > 0
        assert argv[:4] == ("/tools/systemctl", "--user", "show", NAME + ".service")
        self.calls.append(argv)
        properties = tuple(argument.removeprefix("--property=") for argument in argv[4:])
        assert set(properties) == set(self.fields)
        return ProcessResult(argv, 0, "".join(key + "=" + self.fields[key] + "\n" for key in properties))

    def owned_unit(self, name: str) -> dict[str, str]:
        assert name == NAME + ".service"
        self.owned_calls += 1
        if self.owned_calls == self.foreign_at:
            message = "Effective owned unit replaced"
            raise TetherError(message)
        if self.owned_calls == 1 and self.appear:
            self.present.add(self.appear)
        if self.owned_calls == 2:
            self.fields.update(self.drift)
        return dict(self.fields)

    def exists(self, kind: str, identity: str) -> bool:
        assert kind == "container"
        assert identity in {IDENTITY, NAME}
        self.bodies.append(identity)
        return identity in self.present

    def cgroup_empty(self, group: str) -> bool:
        self.groups.append(group)
        return group not in self.nonempty


def failed_role_port(
    service: host.TetherHost, monkeypatch: pytest.MonkeyPatch, group: str = ""
) -> FailedRoleObservation:
    observed = FailedRoleObservation(group)
    service.runner = observed
    monkeypatch.setattr(service, "owned_unit", observed.owned_unit)
    monkeypatch.setattr(service, "exists", observed.exists)
    monkeypatch.setattr(service, "cgroup_empty", observed.cgroup_empty)
    return observed


@pytest.mark.parametrize("group", ["", UNIT_GROUP])
@pytest.mark.parametrize("job", ["", "0"])
def test_retained_failed_role_with_vanished_body_closes_without_effect(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, group: str, job: str
) -> None:
    service, _runner = port
    observed = failed_role_port(service, monkeypatch, group)
    observed.fields["Job"] = job
    service.stop(retained())
    service.stop(retained())
    assert observed.owned_calls == 4
    assert len(observed.calls) == 4
    assert set(observed.groups) == {retained()["cgroup"], UNIT_GROUP}
    assert observed.bodies.count(IDENTITY) == 4
    assert observed.bodies.count(NAME) == 4


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Id", "foreign.service"),
        ("LoadState", "not-found"),
        ("MainPID", "5"),
        ("ControlPID", "5"),
        ("Job", "42"),
        ("NRestarts", "1"),
        ("NRestarts", ""),
        ("InvocationID", "e" * 32),
        ("InvocationID", ""),
        ("ControlGroup", UNIT_GROUP + "/foreign"),
    ],
)
def test_failed_role_closure_refuses_unproved_terminal_state(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, field: str, value: str
) -> None:
    service, _runner = port
    observed = failed_role_port(service, monkeypatch)
    observed.fields[field] = value
    with pytest.raises(TetherError):
        service.closed(retained())


@pytest.mark.parametrize(
    ("active", "substate"), [("active", "running"), ("activating", "auto-restart"), ("failed", "auto-restart")]
)
def test_restarting_role_does_not_acquire_terminal_failure_closure(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, active: str, substate: str
) -> None:
    service, _runner = port
    observed = failed_role_port(service, monkeypatch)
    observed.fields.update(ActiveState=active, SubState=substate)
    assert not service.closed(retained())
    assert not observed.calls


@pytest.mark.parametrize("identity", [IDENTITY, NAME])
def test_failed_role_closure_refuses_body_appearing_during_proof(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, identity: str
) -> None:
    service, _runner = port
    observed = failed_role_port(service, monkeypatch)
    observed.appear = identity
    with pytest.raises(TetherError):
        service.closed(retained())
    assert observed.owned_calls == 1


@pytest.mark.parametrize("group", [retained()["cgroup"], UNIT_GROUP])
def test_failed_role_closure_requires_both_retained_subtrees_empty(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, group: str
) -> None:
    service, _runner = port
    observed = failed_role_port(service, monkeypatch)
    observed.nonempty.add(group)
    if group == UNIT_GROUP:
        with pytest.raises(TetherError):
            service.closed(retained())
    else:
        assert not service.closed(retained())


@pytest.mark.parametrize("observation", [1, 2])
def test_failed_role_closure_requires_effective_ownership_on_both_observations(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, observation: int
) -> None:
    service, _runner = port
    observed = failed_role_port(service, monkeypatch)
    observed.foreign_at = observation
    with pytest.raises(TetherError, match="Effective owned unit replaced"):
        service.closed(retained())
    assert observed.owned_calls == observation


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("InvocationID", "e" * 32),
        ("ControlGroup", UNIT_GROUP),
        ("Job", "42"),
        ("MainPID", "5"),
        ("NRestarts", "1"),
        ("ActiveState", "active"),
    ],
)
def test_failed_role_closure_refuses_manager_drift_between_observations(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, field: str, value: str
) -> None:
    service, _runner = port
    observed = failed_role_port(service, monkeypatch)
    observed.drift[field] = value
    with pytest.raises(TetherError):
        service.closed(retained())
    assert observed.owned_calls == 2
