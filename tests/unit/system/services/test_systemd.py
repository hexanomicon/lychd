from __future__ import annotations

import pytest

from lychd.system.operator import ProcessInvocationError, ProcessResult
from lychd.system.services.systemd import (
    SystemdUserManager,
    SystemdUserManagerError,
)


class _Runner:
    def __init__(
        self,
        *,
        result: ProcessResult | None = None,
        error: ProcessInvocationError | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[tuple[tuple[str, ...], float]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        self.calls.append((argv, timeout_s))
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def test_daemon_reload_uses_literal_argv_and_mandatory_timeout() -> None:
    runner = _Runner(
        result=ProcessResult(
            argv=(),
            returncode=0,
        )
    )

    SystemdUserManager(
        systemctl_bin="/usr/bin/systemctl",
        runner=runner,
    ).daemon_reload()

    assert runner.calls == [
        (
            ("/usr/bin/systemctl", "--user", "daemon-reload"),
            30.0,
        )
    ]


def test_daemon_reload_wraps_timeout_as_typed_failure() -> None:
    runner = _Runner(
        error=ProcessInvocationError("command exceeded its timeout"),
    )

    with pytest.raises(
        SystemdUserManagerError,
        match="could not complete.*exceeded its timeout",
    ):
        SystemdUserManager(
            systemctl_bin="/usr/bin/systemctl",
            runner=runner,
        ).daemon_reload()


def test_daemon_reload_wraps_nonzero_exit_as_typed_failure() -> None:
    runner = _Runner(
        result=ProcessResult(
            argv=(),
            returncode=1,
            stderr="Failed to connect to bus",
        )
    )

    with pytest.raises(
        SystemdUserManagerError,
        match="daemon-reload failed: Failed to connect to bus",
    ):
        SystemdUserManager(
            systemctl_bin="/usr/bin/systemctl",
            runner=runner,
        ).daemon_reload()
