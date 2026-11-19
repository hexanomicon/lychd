"""Short-lived Nexus presence over explicitly paired local replica folders."""

from __future__ import annotations

import asyncio
import base64
import os
import stat
import struct
import time
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, Self
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken

from lychd.domain.intercom.presence import Availability, ColleagueObservation, PresenceBoard, PresenceIntent
from lychd.system.path_policy import physically_contains

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path

    from lychd.config.settings.presence import PresenceSettings

_INTERVAL = 5
_SECOND = 1_000_000_000
_LEASE = 30 * _SECOND
_SKEW = 3 * _SECOND
_SESSION = 3600 * _SECOND
_DIRECTORY_MODE = 0o700
_MAX_FILE_BYTES = 512
_KEY_BYTES = 32
_FRAME = struct.Struct("!4sccQQ")
_CODES = {"ready": b"R", "busy": b"B", "hidden": b"H"}


class AudienceChangedError(ValueError):
    """The roster displayed by the browser belongs to another service generation."""


def _timestamp(ns: int) -> datetime:
    return datetime.fromtimestamp(ns / _SECOND, UTC)


def _directory(path: Path, stack: ExitStack) -> int:
    # POSIX descriptor traversal is loaded only when the operator selects this profile.
    from lychd.system.services.file_publication_settlement import open_existing_directory

    fd = open_existing_directory(path)
    stack.callback(os.close, fd)
    if stat.S_IMODE(os.fstat(fd).st_mode) != _DIRECTORY_MODE:
        msg = "Presence requires an owner-only local directory."
        raise ValueError(msg)
    return fd


def _read(directory: int, filename: str, *, secret: bool = False) -> bytes:
    fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > _MAX_FILE_BYTES:
            msg = "Invalid presence file."
            raise ValueError(msg)
        if secret and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            msg = "Presence keys must be owner-only."
            raise ValueError(msg)
        data = os.read(fd, _MAX_FILE_BYTES + 1)
        if len(data) != info.st_size:
            msg = "Incomplete presence file."
            raise ValueError(msg)
        return data
    finally:
        os.close(fd)


@dataclass
class _Pair:
    name: str
    directory: int
    slot: str
    cipher: Fernet
    newest: int = 0
    expires: int = 0
    observed: int = 0
    remote_deadline: int = 0
    newest_frame: bytes = b""
    last_issued: int = 0
    withdraw_until: int = 0
    availability: Literal["ready", "busy", "unknown"] = "unknown"
    publication: Literal["waiting", "published", "unavailable"] = "waiting"
    valid: bool = False

    def observe(self, now: int) -> None:
        other = "a" if self.slot == "b" else "b"
        self.valid = False
        try:
            data = self.cipher.decrypt(_read(self.directory, f"{other}.lease"))
            profile, slot, code, issued, expires = _FRAME.unpack(data)
        except (OSError, ValueError, InvalidToken, struct.error):
            return
        if (
            profile != b"LYP1"
            or slot != other.encode()
            or code not in _CODES.values()
            or issued < self.newest
            or (issued == self.newest and data != self.newest_frame)
            or issued > now + _SKEW
            or expires <= issued
            or not now < expires <= issued + _LEASE
        ):
            return
        if issued > self.newest:
            self.newest = issued
            self.newest_frame = data
            self.observed = min(now, issued)
            self.expires = self.observed + (expires - issued)
            self.remote_deadline = time.monotonic_ns() + self.expires - now
        self.availability = "ready" if code == b"R" else "busy" if code == b"B" else "unknown"
        self.valid = True

    def publish(self, choice: Availability, until: int, now: int) -> None:
        """Atomically publish a complete encrypted observation to this pair only."""
        issued = max(now, self.last_issued + 1)
        expires = min(now + _LEASE, until)
        if issued >= expires or issued > now + _SKEW:
            msg = "Clock cannot issue a fresh presence observation."
            raise OSError(msg)
        frame = _FRAME.pack(b"LYP1", self.slot.encode(), _CODES[choice], issued, expires)
        token = self.cipher.encrypt(frame)
        temporary = f".presence-{uuid4().hex}"
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600, dir_fd=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(token)
            os.replace(temporary, f"{self.slot}.lease", src_dir_fd=self.directory, dst_dir_fd=self.directory)
            self.last_issued = issued
        finally:
            with suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=self.directory)

    def announce(self, choice: Availability, until: int) -> None:
        now = time.time_ns()
        if choice == "hidden":
            until = self.withdraw_until
        if until <= now:
            self.publication = "waiting"
            return
        try:
            self.publish(choice, until, now)
        except OSError:
            self.publication = "unavailable"
        else:
            self.publication = "published"
            self.withdraw_until = 0


class ColleaguePresence:
    """Own one finite audience, local sharing session and periodic file exchange."""

    def __init__(self, pairs: tuple[_Pair, ...]) -> None:
        """Begin hidden and retain only process-local sharing authority."""
        self._pairs = pairs
        self._audience = uuid4()
        self._choice: Availability = "hidden"
        self._until = 0
        self._deadline = 0
        self._permitted: Callable[[], bool] | None = None
        self._lock = asyncio.Lock()
        self._stopped = asyncio.Event()
        self._observations = self._collect()

    @classmethod
    @contextmanager
    def open(cls, settings: PresenceSettings) -> Generator[Self]:
        """Pin owner-controlled directory descriptors and unique pair keys for this boot."""
        if os.name != "posix":
            msg = "Nexus pair folders require POSIX directory descriptors."
            raise ValueError(msg)
        seen_keys: set[bytes] = set()
        seen_dirs: set[tuple[int, int]] = set()
        pairs: list[_Pair] = []
        for pair in settings.pairs:
            for other in settings.pairs:
                if physically_contains(pair.directory, other.key_file) or (
                    pair != other and physically_contains(pair.directory, other.directory)
                ):
                    msg = "Presence keys and exchange directories must have disjoint physical custody."
                    raise ValueError(msg)
        with ExitStack() as stack:
            for pair in settings.pairs:
                directory = _directory(pair.directory, stack)
                info = os.fstat(directory)
                identity = (info.st_dev, info.st_ino)
                with ExitStack() as keys:
                    key_dir = _directory(pair.key_file.parent, keys)
                    key = bytes.fromhex(_read(key_dir, pair.key_file.name, secret=True).decode("ascii").strip())
                if len(key) != _KEY_BYTES or key in seen_keys or identity in seen_dirs:
                    msg = "Each presence pair requires a dedicated 256-bit key and exchange folder."
                    raise ValueError(msg)
                seen_keys.add(key)
                seen_dirs.add(identity)
                pairs.append(_Pair(pair.name, directory, pair.slot, Fernet(base64.urlsafe_b64encode(key))))
            yield cls(tuple(pairs))

    def _collect(self) -> tuple[tuple[ColleagueObservation, int], ...]:
        return tuple(
            (
                ColleagueObservation(
                    name=pair.name,
                    availability=pair.availability if pair.valid else "unknown",
                    observed_at=_timestamp(pair.observed) if pair.observed else None,
                    expires_at=_timestamp(pair.expires) if pair.expires else None,
                    publication=pair.publication,
                ),
                pair.remote_deadline,
            )
            for pair in self._pairs
        )

    def _sharing(self) -> Availability:
        if self._choice != "hidden" and (
            time.time_ns() >= self._until
            or time.monotonic_ns() >= self._deadline
            or self._permitted is None
            or not self._permitted()
        ):
            self._choice = "hidden"
            self._permitted = None
        return self._choice

    def board(self) -> PresenceBoard:
        """Age each observation against the signed deadline even between refreshes."""
        now = time.time_ns()
        observed = _timestamp(now)
        elapsed = time.monotonic_ns()
        sharing = self._sharing()
        return PresenceBoard(
            audience_id=self._audience,
            sharing=sharing,
            sharing_until=_timestamp(self._until) if sharing != "hidden" else None,
            peers=[
                peer
                if (
                    peer.observed_at
                    and peer.expires_at
                    and peer.observed_at <= observed < peer.expires_at
                    and elapsed < deadline
                )
                else peer.model_copy(update={"availability": "unknown"})
                for peer, deadline in self._observations
            ],
        )

    def _observe(self) -> None:
        for pair in self._pairs:
            pair.observe(time.time_ns())

    async def choose(self, intent: PresenceIntent, *, permitted: Callable[[], bool]) -> PresenceBoard:
        """Bind the operator choice to this boot and the current operator credential."""
        async with self._lock:
            if intent.audience_id != self._audience or self._stopped.is_set() or not permitted():
                raise AudienceChangedError
            previous = self._sharing()
            self._permitted = permitted
            self._choice = intent.availability
            if self._choice == "hidden":
                self._until = self._deadline = 0
                for pair in self._pairs:
                    pair.withdraw_until = time.time_ns() + _LEASE
            elif self._choice != previous:
                self._until = time.time_ns() + _SESSION
                self._deadline = time.monotonic_ns() + _SESSION
            await self._tick()
            return self.board()

    async def _tick(self) -> None:
        # Settle reads before the pinned directory descriptors can be retired.
        worker = asyncio.create_task(asyncio.to_thread(self._observe))
        try:
            await asyncio.shield(worker)
        except asyncio.CancelledError:
            await worker
            raise
        choice = self._sharing()
        for pair in self._pairs:
            if self._stopped.is_set() or self._permitted is None or not self._permitted():
                pair.publication = "waiting"
            else:
                # The fixed-size local replacement and current permission share the control loop.
                until = min(self._until, time.time_ns() + self._deadline - time.monotonic_ns())
                pair.announce(choice, until)
        self._observations = self._collect()

    async def maintain(self) -> None:
        """Refresh even with the browser closed and release the lock between observations."""
        while not self._stopped.is_set():
            async with self._lock:
                if self._stopped.is_set():
                    break
                await self._tick()
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=_INTERVAL)
            except TimeoutError:
                continue

    def fence(self) -> None:
        """End future publication before any shutdown await."""
        self._stopped.set()
        self._permitted = None
        self._choice = "hidden"

    async def stop(self) -> None:
        """Fence future work and drain every already admitted file operation."""
        self.fence()
        async with self._lock:
            self._choice = "hidden"
            self._until = 0
