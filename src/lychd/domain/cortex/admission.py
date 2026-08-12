"""Loop-confined single-flight coordination for idempotent Run admission."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

__all__ = ["RunAdmissionCoordinator"]

type _AdmissionKey = tuple[str, str]


@dataclass
class _PendingAdmission:
    """One scoped admission key's completion signal."""

    event: asyncio.Event = field(default_factory=asyncio.Event)


class RunAdmissionCoordinator:
    """Serialize same-key admission on the single Topology-A event loop."""

    __slots__ = ("_pending",)

    def __init__(self) -> None:
        """Create an empty key-to-admission map."""
        self._pending: dict[_AdmissionKey, _PendingAdmission] = {}

    def begin(self, key: _AdmissionKey) -> bool:
        """Elect one admission writer; concurrent callers become waiters."""
        if key in self._pending:
            return False
        self._pending[key] = _PendingAdmission()
        return True

    def finish(self, key: _AdmissionKey) -> None:
        """Release the writer and wake every same-key waiter."""
        pending = self._pending.pop(key, None)
        if pending is not None:
            pending.event.set()

    async def wait(self, key: _AdmissionKey) -> None:
        """Wait for the current writer, if any, to finish."""
        pending = self._pending.get(key)
        if pending is not None:
            await pending.event.wait()
