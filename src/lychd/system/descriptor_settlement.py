"""Generic descriptor ownership and peer-failure settlement primitives."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn, Protocol

from lychd.system.interruptions import find_terminal_interruption

DIRECTORY_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW


class SettlementErrorFactory(Protocol):
    """Construct domain-specific evidence from generic settlement truth."""

    def __call__(
        self,
        message: str,
        *,
        failures: tuple[BaseException, ...],
        outcome: str,
    ) -> BaseException:
        """Return one domain-specific settlement error."""
        ...


class DirectoryComponentErrorFactory(Protocol):
    """Translate one ordinary descriptor-relative component-open failure."""

    def __call__(
        self,
        path: Path,
        error: OSError,
    ) -> BaseException:
        """Return caller-domain evidence for the failed component."""
        ...


class UnsafeDirectoryPathErrorFactory(Protocol):
    """Translate one lexically unsafe directory path."""

    def __call__(self, path: Path) -> BaseException:
        """Return caller-domain evidence for the unsafe path."""
        ...


@dataclass(slots=True)
class DescriptorSet:
    """Own descriptors until each has been transferred or closed exactly once."""

    _owned: list[int] = field(default_factory=list)

    def add(self, descriptor: int) -> int:
        """Take ownership of one descriptor."""
        self._owned.append(descriptor)
        return descriptor

    def transfer(self, descriptor: int) -> int:
        """Release one descriptor to another explicit owner without closing it."""
        self._owned.remove(descriptor)
        return descriptor

    def close(self, descriptor: int) -> None:
        """Attempt one close after dropping local authority to retry it."""
        self._owned.remove(descriptor)
        os.close(descriptor)

    def settle(self) -> tuple[BaseException, ...]:
        """Attempt every remaining close and retain all failures."""
        failures: list[BaseException] = []
        while self._owned:
            descriptor = self._owned.pop()
            try:
                os.close(descriptor)
            except BaseException as exc:  # noqa: BLE001 - every peer must settle
                failures.append(exc)
        return tuple(failures)


@dataclass(slots=True)
class FailureLedger:
    """Collect peer failures before surfacing verified transaction truth."""

    error_factory: SettlementErrorFactory
    subject: str = "Settlement"
    failures: list[BaseException] = field(default_factory=list)

    def record(self, *failures: BaseException) -> None:
        """Retain failures in observation order."""
        self.failures.extend(failures)

    def record_all(self, failures: tuple[BaseException, ...]) -> None:
        """Retain a settled peer batch."""
        self.failures.extend(failures)

    def raise_if_any(
        self,
        *,
        message: str,
        outcome: str,
        terminal_note: str,
        verified: bool,
    ) -> None:
        """Surface native cancellation only when the postcondition is verified."""
        if not self.failures:
            return
        failures = tuple(self.failures)
        terminal = next(
            (interruption for failure in failures if (interruption := find_terminal_interruption(failure)) is not None),
            None,
        )
        evidence = self.error_factory(
            message,
            failures=failures,
            outcome=outcome,
        )
        if verified and terminal is not None:
            terminal.add_note(terminal_note)
            companions = tuple(failure for failure in failures if failure is not terminal)
            if companions:
                raise terminal from evidence
            raise terminal
        raise evidence from (terminal or failures[0])

    def raise_primary_after_verified_settlement(
        self,
        primary: BaseException,
        *,
        outcome: str,
        terminal_note: str,
    ) -> NoReturn:
        """Preserve a primary error after exact settlement of all side effects."""
        terminal = find_terminal_interruption(primary)
        if terminal is not None:
            terminal.add_note(terminal_note)
            if self.failures:
                evidence = self.error_factory(
                    f"{self.subject} completed with additional cleanup failures.",
                    failures=(primary, *self.failures),
                    outcome=outcome,
                )
                raise terminal from evidence
            raise terminal
        if self.failures:
            cleanup_terminal = next(
                (
                    interruption
                    for failure in self.failures
                    if (interruption := find_terminal_interruption(failure)) is not None
                ),
                None,
            )
            evidence = self.error_factory(
                f"{self.subject} completed with cleanup failures.",
                failures=(primary, *self.failures),
                outcome=outcome,
            )
            if cleanup_terminal is not None:
                cleanup_terminal.add_note(terminal_note)
                evidence.__cause__ = primary
                raise cleanup_terminal from evidence
            raise evidence from primary
        raise primary


def directory_chain_start(
    path: Path,
    *,
    unsafe_error: UnsafeDirectoryPathErrorFactory,
) -> tuple[Path, tuple[str, ...]]:
    """Resolve a traversal start and reject lexical escape components."""
    start = Path(path.anchor) if path.is_absolute() else Path.cwd()
    components = path.parts[1:] if path.is_absolute() else path.parts
    if any(component in {"", ".", ".."} for component in components):
        raise unsafe_error(path)
    return start, components


def open_directory_path(
    path: Path,
    *,
    failure_ledger: FailureLedger,
    component_error: DirectoryComponentErrorFactory,
    unsafe_error: UnsafeDirectoryPathErrorFactory,
    terminal_note: str,
) -> int:
    """Open a path component-by-component without following symbolic links.

    The caller supplies domain-specific evidence while this primitive owns and
    settles every intermediate descriptor. The returned leaf descriptor is the
    caller's responsibility.
    """
    descriptors = DescriptorSet()
    current_path, components = directory_chain_start(
        path,
        unsafe_error=unsafe_error,
    )
    current_fd = descriptors.add(os.open(current_path, DIRECTORY_OPEN_FLAGS))
    try:
        for component in components:
            next_path = current_path / component
            try:
                next_fd = descriptors.add(
                    os.open(
                        component,
                        DIRECTORY_OPEN_FLAGS,
                        dir_fd=current_fd,
                    )
                )
            except OSError as exc:
                translated = component_error(next_path, exc)
                raise translated from exc
            descriptors.close(current_fd)
            current_fd = next_fd
            current_path = next_path
    except BaseException as exc:  # noqa: BLE001 - settle every acquired descriptor
        failure_ledger.record_all(descriptors.settle())
        failure_ledger.raise_primary_after_verified_settlement(
            exc,
            outcome="unchanged",
            terminal_note=terminal_note,
        )
    return descriptors.transfer(current_fd)


__all__ = (
    "DIRECTORY_OPEN_FLAGS",
    "DescriptorSet",
    "DirectoryComponentErrorFactory",
    "FailureLedger",
    "SettlementErrorFactory",
    "UnsafeDirectoryPathErrorFactory",
    "directory_chain_start",
    "open_directory_path",
)
