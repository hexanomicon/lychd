"""Opt-in generator transport proof; never execute generated Podman commands.

The hand-written public fixture qualifies upstream GlobalArgs/Service transport
only. It does not prove LychD emission, local routing, an actual store or issue3.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import suppress
from pathlib import Path
from typing import cast

import pytest

from lychd.system.host_tools import trusted_executable, trusted_podman_user_generator_executable

pytestmark = pytest.mark.integration
_PREFIX = (
    "--remote=false",
    "--root=/lychd-context-conformance/store",
    "--runroot=/lychd-context-conformance/run",
    "--storage-driver=overlay",
    "--storage-opt=overlay.mountopt=nodev",
    "--volumepath=/lychd-context-conformance/store/volumes",
)
_HOST_ENV = {
    "HOME": "/lychd-context-conformance/home",
    "XDG_CONFIG_HOME": "/lychd-context-conformance/config",
    "XDG_DATA_HOME": "/lychd-context-conformance/data",
    "XDG_RUNTIME_DIR": "/lychd-context-conformance/run",
    "PATH": "/usr/bin:/bin",
}
_UNSET = "CONTAINER_HOST CONTAINER_CONNECTION CONTAINERS_CONF CONTAINERS_CONF_OVERRIDE CONTAINERS_STORAGE_CONF STORAGE_DRIVER STORAGE_OPTS PODMAN_CONNECTIONS_CONF"
_CONTAINER = {"ExecStart": ("run",), "ExecStop": ("rm",), "ExecStopPost": ("rm",), "ExecReload": ("exec",)}
_POD = {
    "ExecStartPre": ("pod", "create"),
    "ExecStart": ("pod", "start"),
    "ExecStop": ("pod", "stop"),
    "ExecStopPost": ("pod", "rm"),
}


def _assert_transport(text: str, commands: dict[str, tuple[str, ...]], executable: str) -> None:
    """Accept only the fixture's simple systemd token grammar, never shell parsing."""
    rows: dict[str, list[str]] = {}
    section = ""
    for line in text.splitlines():
        if line.startswith("["):
            section = line
        elif section == "[Service]" and "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            rows.setdefault(key, []).append(value)
    assert {key for key in rows if key.startswith("Exec")} == set(commands), "lifecycle coverage changed"
    environment = [token for value in rows.get("Environment", []) for token in value.split()]
    for key, value in _HOST_ENV.items():
        assert [token for token in environment if token.startswith(key + "=")] == [f"{key}={value}"], (
            "host environment missing, repeated or changed"
        )
    assert not any(token.split("=", 1)[0] in _UNSET.split() for token in environment), "routing selector reintroduced"
    assert rows.get("UnsetEnvironment") == [_UNSET], "host routing selectors not unset"
    for key, action in commands.items():
        assert len(rows[key]) == 1, "duplicate lifecycle command"
        words = rows[key][0].removeprefix("-").split()
        assert all(re.fullmatch(r"[A-Za-z0-9_./:@%+=,$-]+", word) for word in words), "unsupported systemd quoting"
        assert words[: 1 + len(_PREFIX)] == [executable, *_PREFIX], "context prefix absent or changed"
        tail = words[1 + len(_PREFIX) :]
        assert tail[: len(action)] == list(action), "global arguments must precede subcommand"
        assert not any(
            word.startswith(("--root", "--runroot", "--storage-", "--volumepath", "--remote", "--connection", "--url"))
            for word in tail
        ), "duplicate or foreign global selector"
        assert not any(f"{name}=" in word for name in _HOST_ENV for word in tail), "host environment moved into guest"


def _generate(argv: list[str], environment: dict[str, str]) -> tuple[int, bytes, bytes, int]:  # noqa: C901, PLR0912, PLR0915 - one auditable owner
    """One owned generator, five-second wall, bounded captures; never run output."""
    if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL or threading.active_count() != 1:
        message = "foreign child reaper or thread"
        raise RuntimeError(message)
    captures = [bytearray(), bytearray()]
    deadline = time.monotonic() + 5
    process = subprocess.Popen(  # noqa: S603 - trusted generator, fixed public fixture, no shell
        argv,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        assert process.stdout is not None
        assert process.stderr is not None
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate((process.stdout, process.stderr)):
                selector.register(stream, selectors.EVENT_READ, index)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    message = "generator wall exceeded"
                    raise RuntimeError(message)
                for key, _ in selector.select(min(remaining, 0.05)):
                    index = cast("int", key.data)
                    chunk = os.read(key.fd, min(65536, 262145 - len(captures[index])))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        captures[index].extend(chunk)
                        if len(captures[index]) > 262144:
                            message = "generator output exceeded"
                            raise RuntimeError(message)
        code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
    finally:
        # This sole owner never reaps before signalling; no post-reap numeric-group kill.
        try:
            if process.returncode is None:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=2)
        finally:
            try:
                if process.stdout is not None:
                    process.stdout.close()
            finally:
                try:
                    if process.stderr is not None:
                        process.stderr.close()
                finally:
                    try:
                        os.killpg(process.pid, 0)
                    except ProcessLookupError:
                        pass
                    else:
                        pytest.fail("generator descendant group remains; closure unknown")
    return code, bytes(captures[0]), bytes(captures[1]), process.pid


def _synthetic_unit(commands: dict[str, tuple[str, ...]]) -> str:
    host = "\n".join(f"Environment={key}={value}" for key, value in _HOST_ENV.items())
    lines = [f"{key}=/usr/bin/podman {' '.join(_PREFIX)} {' '.join(value)}" for key, value in commands.items()]
    return "[Service]\n" + host + "\nUnsetEnvironment=" + _UNSET + "\n" + "\n".join(lines) + "\n"


@pytest.mark.parametrize("commands", [_CONTAINER, _POD])
def test_context_transport_oracle_accepts_complete_fixture(commands: dict[str, tuple[str, ...]]) -> None:
    _assert_transport(_synthetic_unit(commands), commands, "/usr/bin/podman")
    _assert_transport(_synthetic_unit(commands) + "Environment=UNIT_METADATA=fixture\n", commands, "/usr/bin/podman")


@pytest.mark.parametrize(
    "fault", ["old", "cleanup", "late", "duplicate", "reordered", "root", "nodev", "foreign", "guest", "reload"]
)
def test_context_transport_oracle_refuses_faults(fault: str) -> None:
    text = _synthetic_unit(_CONTAINER)
    prefix = " ".join(_PREFIX)
    if fault == "old":
        text = text.replace(prefix + " ", "")
    elif fault == "cleanup":
        text = text.replace(f"ExecStopPost=/usr/bin/podman {prefix}", "ExecStopPost=/usr/bin/podman")
    elif fault == "late":
        text = text.replace(f"{prefix} run", f"run {prefix}")
    elif fault == "duplicate":
        text = text.replace(f"{prefix} run", f"{prefix} run {_PREFIX[1]}")
    elif fault == "reordered":
        text = text.replace(prefix, " ".join(reversed(_PREFIX)))
    elif fault == "root":
        text = text.replace(_PREFIX[1], "--root=/foreign/store")
    elif fault == "nodev":
        text = text.replace(_PREFIX[4], "--storage-opt=overlay.mountopt=nosuid")
    elif fault == "foreign":
        text = text.replace("/usr/bin/podman", "/foreign/podman")
    elif fault == "guest":
        text = text.replace("Environment=HOME=", "GuestEnvironment=HOME=")
    else:
        text = "\n".join(line for line in text.splitlines() if not line.startswith("ExecReload="))
    with pytest.raises(AssertionError):
        _assert_transport(text, _CONTAINER, "/usr/bin/podman")


def test_real_quadlet_global_context_reaches_every_lifecycle(tmp_path: Path) -> None:
    """Require explicit opt-in; no manager, image lookup, store or container operation."""
    if os.environ.get("LYCHD_REQUIRE_QUADLET_PROOF") != "1":
        pytest.skip("set LYCHD_REQUIRE_QUADLET_PROOF=1 for the generator-only proof")
    assert sys.platform == "linux", "required generator proof needs Linux"
    generator = trusted_podman_user_generator_executable()
    podman = trusted_executable("podman")
    assert generator is not None, "required trusted generator unavailable"
    assert podman is not None, "required trusted Podman identity unavailable"
    tools = {tool.path: hashlib.sha256(Path(tool.path).read_bytes()).hexdigest() for tool in (generator, podman)}
    with tempfile.TemporaryDirectory(prefix="lychd-context-generator-", dir="/tmp", delete=False) as scratch:
        root = Path(scratch)
        for name in ("quadlet", "generated", "home", "config", "data", "run"):
            (root / name).mkdir(mode=0o700)
        service = (
            "[Service]\n"
            + "\n".join(f"Environment={key}={value}" for key, value in _HOST_ENV.items())
            + "\nUnsetEnvironment="
            + _UNSET
            + "\n"
        )
        prefix = "GlobalArgs=" + " ".join(_PREFIX) + "\n"
        (root / "quadlet/context.pod").write_text("[Pod]\nPodName=lychd-context-conformance\n" + prefix + service)
        (root / "quadlet/context.container").write_text(
            "[Container]\nImage=localhost/lychd-context-conformance:fixture\nContainerName=lychd-context-conformance\nPod=context.pod\nReloadCmd=/bin/true\n"
            + prefix
            + service
        )
        environment = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(root / "home"),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_RUNTIME_DIR": str(root / "run"),
            "QUADLET_UNIT_DIRS": str(root / "quadlet"),
            "LANG": "C.UTF-8",
        }
        (tmp_path / "quadlet-context-intent.json").write_text(
            json.dumps({"scratch": str(root), "generator": generator.path}) + "\n"
        )
        code, stdout, stderr, pid = _generate([generator.path, "--user", str(root / "generated")], environment)
        assert code == 0, (code, stdout.decode(errors="replace"), stderr.decode(errors="replace"))
        assert not stderr, stderr.decode(errors="replace")
        units = {name: (root / "generated" / name).read_text() for name in ("context.service", "context-pod.service")}
        _assert_transport(units["context.service"], _CONTAINER, podman.path)
        _assert_transport(units["context-pod.service"], _POD, podman.path)
        assert tools == {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in tools}, (
            "tool bytes changed"
        )
        (tmp_path / "quadlet-context-generation.json").write_text(
            json.dumps(
                {
                    "scope": "upstream generator transport only; no LychD emission/store/routing/issue3 closure",
                    "tools_sha256": tools,
                    "environment": environment,
                    "global_prefix": _PREFIX,
                    "generated_unit_sha256": {
                        name: hashlib.sha256(text.encode()).hexdigest() for name, text in units.items()
                    },
                    "returncode": code,
                    "stdout_bytes": len(stdout),
                    "stderr_bytes": len(stderr),
                    "generator_pid_and_pgid": pid,
                    "generator_reaped_and_group_observed_absent": True,
                    "generated_commands_executed": False,
                    "manager_or_Podman_started": False,
                },
                indent=2,
            )
            + "\n"
        )
        shutil.rmtree(root)  # Only a fully settled, passing case removes its exact scratch.
