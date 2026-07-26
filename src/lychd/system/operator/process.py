"""Injected, argv-only subprocess boundary for host observation and actuation."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProcessResult:
    """Bounded subprocess outcome retained without raising on command status."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""


class ProcessRunner(Protocol):
    """Port implemented by the real host and deterministic test doubles."""

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        """Execute one literal argument vector without a shell."""
        ...


class InputProcessRunner(ProcessRunner, Protocol):
    """Bounded process port that can carry a secret through standard input."""

    def run_with_input(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        input_text: str,
    ) -> ProcessResult:
        """Execute literal argv with one non-echoed text payload."""
        ...


class DescriptorProcessRunner(ProcessRunner, Protocol):
    """Process port that can inherit an explicit bounded descriptor set."""

    def run_with_fds(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        pass_fds: tuple[int, ...],
    ) -> ProcessResult:
        """Execute literal argv while preserving only the named descriptors."""
        ...


class ProcessInvocationError(RuntimeError):
    """A host executable could not start or exceeded its mandatory timeout."""


class SubprocessRunner:
    """Run literal host commands with captured output and a mandatory timeout."""

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        """Execute one command without shell expansion, sudo, or stdin."""
        try:
            completed = subprocess.run(  # noqa: S603 - argv comes from typed allowlisted services
                argv,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            message = f"Cannot execute {argv[0]!r}: {exc}"
            raise ProcessInvocationError(message) from exc
        return ProcessResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def run_with_input(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        input_text: str,
    ) -> ProcessResult:
        """Execute a bounded command while streaming one secret via stdin."""
        try:
            completed = subprocess.run(  # noqa: S603 - argv comes from typed allowlisted services
                argv,
                input=input_text,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            message = f"Cannot execute {argv[0]!r}: {exc}"
            raise ProcessInvocationError(message) from exc
        return ProcessResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def run_with_fds(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        pass_fds: tuple[int, ...],
    ) -> ProcessResult:
        """Execute a bounded command with an explicit inherited descriptor set."""
        try:
            completed = subprocess.run(  # noqa: S603 - argv comes from typed allowlisted services
                argv,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                pass_fds=pass_fds,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            message = f"Cannot execute {argv[0]!r}: {exc}"
            raise ProcessInvocationError(message) from exc
        return ProcessResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
