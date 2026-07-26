from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from lychd.system.operator.process import SubprocessRunner

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_descriptor_runner_passes_only_explicit_fds(
    mocker: MockerFixture,
) -> None:
    """Pinned authority reaches the child without broad descriptor inheritance."""
    argv = ("/usr/bin/btrfs", "subvolume", "show", "/proc/self/fd/17/data")
    run = mocker.patch(
        "lychd.system.operator.process.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=argv,
            returncode=0,
            stdout="verified",
            stderr="",
        ),
    )

    result = SubprocessRunner().run_with_fds(
        argv,
        timeout_s=3.0,
        pass_fds=(17,),
    )

    assert result.stdout == "verified"
    run.assert_called_once_with(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=3.0,
        pass_fds=(17,),
    )
