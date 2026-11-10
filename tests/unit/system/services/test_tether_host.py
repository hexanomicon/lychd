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
        return self.outcomes.get(argv[1:], ProcessResult(argv, 0))

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
    monkeypatch.setattr(host, "trusted_host_tool", lambda name: "/tools/" + name)
    service = host.TetherHost(runner)
    monkeypatch.setattr(
        service,
        "owned_unit",
        lambda _name: {
            "LoadState": "loaded",
            "ActiveState": "inactive",
            "SubState": "dead",
            "MainPID": "0",
            "ControlPID": "0",
            "Job": "0",
        },
    )
    monkeypatch.setattr(
        service,
        "unit_incarnation",
        lambda name: {
            "InvocationID": INVOCATION,
            "ControlGroup": UNIT_GROUP if name == NAME + ".service" else UNIT_GROUP.rsplit("/", 1)[0] + "/" + name,
        },
    )
    monkeypatch.setattr(service, "_unit_closed", lambda _name: False)
    return service, runner


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
    monkeypatch.setattr(service, "exists", lambda _kind, identity: identity == NAME)
    monkeypatch.setattr(service, "row", lambda _kind, _identity: {**container(), "Id": OTHER})
    monkeypatch.setattr(service, "cgroup_empty", lambda _group: True)
    with pytest.raises(TetherError):
        service.stop(retained())
    assert not runner.calls


def test_stop_refuses_foreign_unit_before_any_effect(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: True)
    monkeypatch.setattr(service, "row", lambda _kind, _identity: container())
    monkeypatch.setattr(service, "cgroup_empty", lambda _group: True)
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
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: True)
    monkeypatch.setattr(service, "row", lambda _kind, _identity: row)
    with pytest.raises(TetherError):
        service.stop(retained())
    assert not runner.calls


def test_stop_refuses_name_rebound_to_other_container(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: True)
    monkeypatch.setattr(
        service,
        "row",
        lambda _kind, identity: container() if identity == IDENTITY else {**container(), "Id": OTHER},
    )
    with pytest.raises(TetherError):
        service.stop(retained())
    assert not runner.calls


def test_repeated_stop_of_absent_incarnation_cancels_restart(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: False)
    monkeypatch.setattr(service, "cgroup_empty", lambda _group: True)
    service.stop(retained())
    service.stop(retained())
    assert runner.calls == [("/tools/systemctl", "--user", "stop", NAME + ".service")] * 2


def test_stop_waits_for_entire_retained_cgroup(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port
    observations: list[str] = []
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: not runner.calls)
    monkeypatch.setattr(service, "row", lambda _kind, _identity: container())

    def empty(group: str) -> bool:
        observations.append(group)
        return len(observations) > 1

    monkeypatch.setattr(service, "cgroup_empty", empty)
    monkeypatch.setattr(host.time, "sleep", lambda _seconds: None)
    service.stop(retained())
    assert observations == [retained()["cgroup"], retained()["cgroup"]]
    assert runner.calls == [("/tools/systemctl", "--user", "stop", NAME + ".service")]


def test_stop_does_not_claim_closure_while_descendants_survive(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: True)
    monkeypatch.setattr(service, "row", lambda _kind, _identity: container())
    monkeypatch.setattr(service, "cgroup_empty", lambda _group: False)
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
    monkeypatch.setattr(
        host,
        "Path",
        lambda value: tmp_path if str(value) == "/sys/fs/cgroup" else original(value),
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
    monkeypatch.setattr(service, "row", lambda kind, identity: rows[kind, identity])
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: True)
    monkeypatch.setattr(service, "process_cgroup", lambda _pid: retained()["cgroup"])
    monkeypatch.setattr(
        service,
        "unit_incarnation",
        lambda _name: {"InvocationID": INVOCATION, "ControlGroup": UNIT_GROUP},
    )
    namespaces = {
        "/proc/self/ns/net": 10,
        "/proc/1234/ns/net": 10,
        "/proc/4321/ns/net": 30,
    }
    monkeypatch.setattr(
        host,
        "Path",
        lambda *values: (
            SimpleNamespace(stat=lambda: SimpleNamespace(st_ino=namespaces[values[0]]))
            if len(values) == 1 and values[0] in namespaces
            else Path(*values)
        ),
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
    monkeypatch.setattr(service, "command", lambda *_args: json.dumps(response))
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
    assert host._container_group(expected + "/nested", IDENTITY, UNIT_GROUP) == expected


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
        host._container_group(group, IDENTITY, UNIT_GROUP)


def test_stop_refuses_new_unit_invocation(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: False)
    monkeypatch.setattr(service, "cgroup_empty", lambda _group: True)
    monkeypatch.setattr(
        service,
        "unit_incarnation",
        lambda _name: {"InvocationID": "1" * 32, "ControlGroup": UNIT_GROUP},
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
    monkeypatch.setattr(service, "command", lambda *_args: content)
    with pytest.raises(TetherError):
        host.TetherHost.unit_incarnation(service, NAME + ".service")


def test_unit_incarnation_retains_exact_values(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _runner = port
    content = f"Id={NAME}.service\nInvocationID={INVOCATION}\nControlGroup={UNIT_GROUP}\n"
    monkeypatch.setattr(service, "command", lambda *_args: content)
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
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: True)
    row = {
        "Id": POD,
        "Name": record["pod_name"],
        "InfraContainerID": IDENTITY,
        "Containers": [{"Id": IDENTITY}, {"Id": OTHER}],
    }
    monkeypatch.setattr(service, "row", lambda _kind, _identity: row)
    with pytest.raises(TetherError):
        service.stop_pod(record)
    assert not runner.calls


def test_pod_stop_refuses_name_replacement(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, runner = port
    record = pod_retained()
    monkeypatch.setattr(service, "exists", lambda _kind, identity: identity == record["pod_name"])
    monkeypatch.setattr(service, "row", lambda _kind, _identity: {"Id": OTHER})
    with pytest.raises(TetherError):
        service.stop_pod(record)
    assert not runner.calls


@pytest.mark.parametrize("pod", [False, True])
def test_repeated_stop_after_binding_retired_has_no_effect(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, *, pod: bool
) -> None:
    service, runner = port
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: False)
    monkeypatch.setattr(service, "cgroup_empty", lambda _group: True)
    monkeypatch.setattr(service, "_unit_closed", lambda _name: True)
    monkeypatch.setattr(service, "owned_unit", lambda _name: pytest.fail("Retired binding must not need ownership"))
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
    assert host.TetherHost._unit_closed(service, NAME + ".service") is expected


@pytest.mark.parametrize("body_exists", [True, False])
def test_unretained_stop_never_adopts_a_body(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, *, body_exists: bool
) -> None:
    service, runner = port
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: body_exists)
    monkeypatch.setattr(service, "cgroup_empty", lambda _group: True)
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
    monkeypatch.setattr(service, "exists", lambda _kind, _identity: False)
    monkeypatch.setattr(service, "_unit_closed", lambda _name: True)
    monkeypatch.setattr(service, "unit_incarnation", lambda _name: pytest.fail("No authority required for no effect"))
    service.stop_unretained(NAME)
    assert not runner.calls


@pytest.mark.parametrize("fault", ["none", "foreign-image", "foreign-cgroup", "changed-invocation", "inactive"])
def test_core_requires_image_and_current_owned_payload(
    port: tuple[host.TetherHost, Runner], monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    service, runner = port
    core_group = UNIT_GROUP.rsplit("/", 1)[0] + "/lychd-vessel.service"
    row = {**container(), "Name": "lychd-vessel", "Image": OTHER if fault == "foreign-image" else IMAGE}
    monkeypatch.setattr(service, "row", lambda kind, _identity: {"Id": IMAGE} if kind == "image" else row)
    monkeypatch.setattr(
        service,
        "owned_unit",
        lambda _name: {"LoadState": "loaded", "ActiveState": "inactive" if fault == "inactive" else "active"},
    )
    calls = []

    def incarnation(_name: str) -> dict[str, str]:
        calls.append(_name)
        return {
            "InvocationID": "1" * 32 if fault == "changed-invocation" and len(calls) > 1 else INVOCATION,
            "ControlGroup": core_group,
        }

    monkeypatch.setattr(service, "unit_incarnation", incarnation)
    monkeypatch.setattr(
        service,
        "process_cgroup",
        lambda _pid: (UNIT_GROUP if fault == "foreign-cgroup" else core_group) + "/libpod-payload-" + IDENTITY,
    )
    if fault == "none":
        service.require_core("example/core:admitted")
    else:
        with pytest.raises(TetherError):
            service.require_core("example/core:admitted")
    assert not runner.calls
