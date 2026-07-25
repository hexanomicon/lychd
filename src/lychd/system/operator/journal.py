"""Bounded, read-only journald access over exact operator targets."""

from __future__ import annotations

from dataclasses import dataclass

from lychd.system.operator.models import OperatorError, OperatorTarget
from lychd.system.operator.process import ProcessInvocationError, ProcessRunner
from lychd.system.operator.targets import OperatorTargetResolver

_JOURNAL_TIMEOUT_SECONDS = 10.0
_DEFAULT_LINES = 100
_MAX_LINES = 10_000


@dataclass(frozen=True)
class JournalRead:
    """Captured log text and the exact units used to obtain it."""

    target: OperatorTarget
    units: tuple[str, ...]
    content: str


class JournalService:
    """Read user-journal entries without shell expansion or mutation."""

    def __init__(
        self,
        *,
        targets: OperatorTargetResolver,
        runner: ProcessRunner,
        journalctl_bin: str | None,
    ) -> None:
        """Bind exact target resolution and one optional journal executable."""
        self._targets = targets
        self._runner = runner
        self._journalctl = journalctl_bin

    def read(
        self,
        target: OperatorTarget = OperatorTarget.SYSTEM,
        *,
        lines: int = _DEFAULT_LINES,
    ) -> JournalRead:
        """Read a bounded tail for exact owned units."""
        if not 1 <= lines <= _MAX_LINES:
            message = f"lines must be between 1 and {_MAX_LINES}"
            raise ValueError(message)
        units = self._targets.observation_units(target)
        if not units:
            message = f"No exact owned journal units resolve for target '{target.value}'."
            raise OperatorError(message)
        if self._journalctl is None:
            message = "journalctl is unavailable."
            raise OperatorError(message)
        argv = (
            self._journalctl,
            "--user",
            "--no-pager",
            "--lines",
            str(lines),
            *(argument for unit in units for argument in ("--unit", unit)),
        )
        try:
            result = self._runner.run(argv, timeout_s=_JOURNAL_TIMEOUT_SECONDS)
        except ProcessInvocationError as exc:
            message = f"journalctl failed: {exc}"
            raise OperatorError(message) from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit {result.returncode}"
            message = f"journalctl failed: {detail}"
            raise OperatorError(message)
        return JournalRead(target=target, units=units, content=result.stdout)
