"""Real TCP/native-launcher receipts with an explicit synthetic application factory."""

from __future__ import annotations

import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from http.client import HTTPConnection
from pathlib import Path
from typing import cast

import pytest

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/web/server_process_app.py"
_OBSERVATION_SECONDS = 10.0
_STOP_SECONDS = 5.0


def _group_exists(group: int) -> bool:
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    return True


@dataclass
class _Child:
    process: subprocess.Popen[bytes]
    port: int
    token: str
    log: Path
    case: str
    passed: bool = False

    def text(self) -> str:
        return self.log.read_text(errors="replace")

    def wait_event(self, event: str) -> None:
        deadline = time.monotonic() + _OBSERVATION_SECONDS
        while time.monotonic() < deadline:
            if event in self.text():
                return
            assert self.process.poll() is None, self.text()[-4000:]
            time.sleep(0.01)
        pytest.fail(f"Missing synthetic event {event}: {self.text()[-4000:]}")

    def request(self, path: str, *, timeout: float = _STOP_SECONDS) -> tuple[int, dict[str, str]]:
        connection = HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            body = response.read(4097)
            assert len(body) <= 4096
            result: object = json.loads(body)
            assert isinstance(result, dict)
            mapping = cast("dict[object, object]", result)
            assert all(isinstance(key, str) and isinstance(value, str) for key, value in mapping.items())
            return response.status, cast("dict[str, str]", mapping)
        finally:
            connection.close()

    def ready(self) -> None:
        deadline = time.monotonic() + _OBSERVATION_SECONDS
        while time.monotonic() < deadline:
            assert self.process.poll() is None, self.text()[-4000:]
            try:
                if self.request("/ready", timeout=0.2) == (200, {"marker": self.token}):
                    return
            except (OSError, ValueError):
                pass
            time.sleep(0.02)
        pytest.fail(f"Synthetic listener was not ready: {self.text()[-4000:]}")

    def signal_stop(self) -> None:
        self.process.send_signal(signal.SIGTERM)

    def settled(self, *, success: bool) -> None:
        code = self.process.wait(timeout=_STOP_SECONDS)
        assert (code == 0) is success, self.text()[-4000:]
        assert self.text().count("fixture-startup-enter") == 1
        assert self.text().count("fixture-close-enter:0") == 1
        assert "synthetic-service-close-before-callback-retirement" not in self.text()
        if self.case != "close-failure":
            assert self.text().count("fixture-close-complete") == 1


@contextmanager
def _child(tmp_path: Path, case: str) -> Generator[_Child]:
    with socket.socket() as selector:
        selector.bind(("127.0.0.1", 0))
        port = selector.getsockname()[1]
    token = secrets.token_hex(16)
    environment = {
        "PATH": "/usr/bin:/bin",
        "PYTHONNOUSERSITE": "1",
        "LYCHD_TEST_SERVER_PORT": str(port),
        "LYCHD_TEST_SERVER_TOKEN": token,
        "LYCHD_TEST_SERVER_CASE": case,
    }
    log = tmp_path / "process.log"
    with log.open("xb") as output:
        process = subprocess.Popen(  # noqa: S603 - fixed interpreter/fixture, synthetic allowlisted environment
            [sys.executable, str(_FIXTURE)],
            cwd=tmp_path,
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    child = _Child(process, port, token, log, case)
    try:
        assert os.getpgid(process.pid) == process.pid
        # The outer acceptance owner can reconcile this exact child even if the
        # pytest group is interrupted. Keep identifiers in private scratch only.
        start = Path(f"/proc/{process.pid}/stat").read_text().rpartition(") ")[2].split()[19]
        (tmp_path / "process-identity.json").write_text(
            json.dumps({"pid": process.pid, "group": process.pid, "start_time": start, "fixture": str(_FIXTURE)}) + "\n"
        )
        yield child
    finally:
        if _group_exists(process.pid):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=_STOP_SECONDS)
        except subprocess.TimeoutExpired:
            if _group_exists(process.pid):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=_STOP_SECONDS)
        if _group_exists(process.pid):
            os.killpg(process.pid, signal.SIGKILL)
        deadline = time.monotonic() + _STOP_SECONDS
        while _group_exists(process.pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        absent = not _group_exists(process.pid)
        (tmp_path / "receipt.json").write_text(
            json.dumps(
                {
                    "schema": "synthetic-native-server-process@1",
                    "case": case,
                    "assertions_passed": child.passed,
                    "exit_code": process.returncode,
                    "owned_group_absent": absent,
                    "factory": "explicit-inert-Litestar",
                    "production_services_or_units_exercised": False,
                },
                indent=2,
            )
            + "\n"
        )
        assert absent, f"Owned synthetic process group {process.pid} survived cleanup"


@pytest.mark.parametrize("case", ["clean", "close-failure", "startup-failure", "warmup-stop"])
def test_native_launcher_exposes_required_lifespan_outcomes(tmp_path: Path, case: str) -> None:
    with _child(tmp_path, case) as child:
        if case == "startup-failure":
            child.settled(success=False)
            assert "synthetic-required-startup-failure" in child.text()
        elif case == "warmup-stop":
            child.wait_event("fixture-startup-enter")
            child.signal_stop()
            child.settled(success=False)
            assert "fixture-startup-complete" not in child.text()
        else:
            child.ready()
            assert child.request("/raw/%70ath") == (200, {"marker": child.token, "raw_path": "/raw/%70ath"})
            child.signal_stop()
            child.settled(success=case == "clean")
            if case == "close-failure":
                assert "synthetic-required-close-failure" in child.text()
        child.passed = True


def test_native_stop_retires_pending_http_before_services(tmp_path: Path) -> None:
    with _child(tmp_path, "pending") as child:
        child.ready()
        with ThreadPoolExecutor(max_workers=1) as requests:
            pending = requests.submit(child.request, "/hold")
            child.wait_event("fixture-request-enter")
            child.signal_stop()
            assert pending.result(timeout=_STOP_SECONDS) == (200, {"marker": child.token})
        child.settled(success=True)
        assert child.text().index("fixture-request-complete") < child.text().index("fixture-request-finally")
        assert child.text().index("fixture-request-finally") < child.text().index("fixture-close-enter:0")
        child.passed = True


@pytest.mark.parametrize("repeat_signal", [False, True])
def test_native_stop_retires_postresponse_python_callback(tmp_path: Path, *, repeat_signal: bool) -> None:
    case = "background-repeat" if repeat_signal else "background"
    with _child(tmp_path, case) as child:
        child.ready()
        assert child.request("/background") == (200, {"marker": child.token})
        child.wait_event("fixture-tail-enter")
        assert "fixture-tail-complete" not in child.text()
        child.signal_stop()
        if repeat_signal:
            time.sleep(0.05)
            child.signal_stop()
        child.settled(success=True)
        assert child.text().index("fixture-tail-complete") < child.text().index("fixture-tail-finally")
        assert child.text().index("fixture-tail-finally") < child.text().index("fixture-close-enter:0")
        child.passed = True
