"""Query only an explicitly bound remote person's own Horizon pose.

This port never owns, stops or mutates either client. Client observations are
not authenticated game identity or server-authoritative world receipts.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import socket
import stat
import struct
from pathlib import Path
from typing import Any, Literal, cast

from lychd.lib.asyncio import complete_under_cancellation
from lychd.system.services.horizon_control import (
    MAX_CONTROL_TIMEOUT,
    MAX_REPLY_BYTES,
    MIN_CONTROL_TIMEOUT,
    HorizonBinding,
    HorizonControlError,
)

POSITION_COMPONENTS = 3
CLOSE_TIMEOUT_S = 0.1


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate JSON key."
            raise ValueError(msg)
        result[key] = value
    return result


def _constant(_: str) -> Any:
    msg = "Non-finite JSON number."
    raise ValueError(msg)


def _finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        msg = "Non-finite JSON number."
        raise ValueError(msg)
    return result


def _process_start(pid: int) -> int:
    return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])


def _peer_credentials(writer: asyncio.StreamWriter) -> tuple[int, int, int]:
    peer = writer.get_extra_info("socket")
    if peer is None or not hasattr(socket, "SO_PEERCRED"):
        msg = "Linux peer credentials are required."
        raise HorizonControlError(msg)
    return struct.unpack("3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))


def _finite_real(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _endpoint_identity(path: Path) -> tuple[int, int]:
    if not path.is_absolute() or ".." in path.parts:
        msg = "Endpoint must be an absolute path without traversal."
        raise HorizonControlError(msg)
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode):
            msg = "Endpoint path must contain only real directories."
            raise HorizonControlError(msg)
    parent_info = path.parent.lstat()
    info = path.lstat()
    if (
        parent_info.st_uid != os.getuid()
        or parent_info.st_mode & 0o077
        or not stat.S_ISSOCK(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o022
    ):
        msg = "Endpoint must be owned, not publicly writable, and inside a private real owned directory."
        raise HorizonControlError(msg)
    return info.st_dev, info.st_ino


def _validate_binding(binding: HorizonBinding) -> None:
    labels = (binding.server_address, binding.client_name, binding.dimension)
    if (
        binding.mode != "remote"
        or type(binding.pid) is not int
        or binding.pid <= 0
        or type(binding.start_ticks) is not int
        or binding.start_ticks <= 0
        or not _finite_real(binding.timeout_s)
        or not MIN_CONTROL_TIMEOUT <= binding.timeout_s <= MAX_CONTROL_TIMEOUT
        or type(binding.world) is not str
        or binding.world != binding.world.strip()
        or any(type(value) is not str or not value.strip() or value != value.strip() for value in labels)
    ):
        msg = "Observation requires an exact remote client binding and finite timeout."
        raise HorizonControlError(msg)


class HorizonTargetObserver:
    """Read one remote person's own state without acquiring action ownership.

    Both clients remain explicitly pinned. Any failed read or closure permanently
    retires this instance; a later call cannot return a retained sample. Opt-in
    cancellation settlement finishes a finite read and discards its late sample
    before propagating caller cancellation; it grants no continued action authority.
    """

    def __init__(
        self, binding: HorizonBinding, *, bot_binding: HorizonBinding, settle_cancelled_reads: bool = False
    ) -> None:
        """Retain explicit bindings without touching either endpoint."""
        if type(settle_cancelled_reads) is not bool:
            msg = "Cancellation settlement requires an explicit boolean choice."
            raise HorizonControlError(msg)
        self.binding = binding
        self.bot_binding = bot_binding
        self._settle_cancelled_reads = settle_cancelled_reads
        self._inodes: tuple[tuple[int, int], tuple[int, int]] | None = None
        self._started = False
        self._closed = False
        self._lock = asyncio.Lock()
        self._writer: asyncio.StreamWriter | None = None

    def _check_identity(self) -> None:
        if self._closed or self._inodes is None:
            msg = "Target observer is closed or not open."
            raise HorizonControlError(msg)
        for binding, inode in zip((self.binding, self.bot_binding), self._inodes, strict=True):
            if _endpoint_identity(binding.endpoint) != inode or _process_start(binding.pid) != binding.start_ticks:
                msg = "Pinned endpoint or client process generation changed."
                raise HorizonControlError(msg)

    async def open(self) -> None:
        """Pin distinct clients and verify a fresh exact-person observation."""
        if self._started or self._closed:
            msg = "Target observer cannot be reopened."
            raise HorizonControlError(msg)
        self._started = True
        try:
            _validate_binding(self.binding)
            _validate_binding(self.bot_binding)
            if (
                self.binding.pid == self.bot_binding.pid
                or self.binding.endpoint == self.bot_binding.endpoint
                or (self.binding.server_address, self.binding.world, self.binding.dimension)
                != (self.bot_binding.server_address, self.bot_binding.world, self.bot_binding.dimension)
            ):
                msg = "Target and bot require distinct clients with matching remote address, dimension and labels."
                raise HorizonControlError(msg)  # noqa: TRY301 - permanently close failed admission
            self._inodes = (_endpoint_identity(self.binding.endpoint), _endpoint_identity(self.bot_binding.endpoint))
            if self._inodes[0] == self._inodes[1]:
                msg = "Target and bot cannot share a socket inode."
                raise HorizonControlError(msg)  # noqa: TRY301 - permanently close failed admission
            await self.observe()
        except BaseException:
            await self.aclose()
            raise

    async def _query(self, command: Literal["state", "status"]) -> dict[str, Any]:
        """Issue one hardcoded query with a fresh credential and generation check."""
        writer: asyncio.StreamWriter | None = None
        try:
            async with asyncio.timeout(self.binding.timeout_s):
                self._check_identity()
                reader, writer = await asyncio.open_unix_connection(str(self.binding.endpoint), limit=MAX_REPLY_BYTES)
                self._writer = writer
                pid, uid, _ = _peer_credentials(writer)
                if pid != self.binding.pid or uid != os.getuid():
                    msg = "Observation peer differs from the pinned person."
                    raise HorizonControlError(msg)
                self._check_identity()
                writer.write(b"state\n" if command == "state" else b"status\n")
                await writer.drain()
                raw = await reader.readline()
                self._check_identity()
                if not raw.endswith(b"\n") or len(raw) > MAX_REPLY_BYTES:
                    msg = "Observation reply is incomplete or too large."
                    raise HorizonControlError(msg)
                try:
                    value = json.loads(
                        raw.decode("utf-8"),
                        object_pairs_hook=_object,
                        parse_constant=_constant,
                        parse_float=_finite_float,
                    )
                except (ValueError, RecursionError) as exc:
                    msg = "Observation reply is not strict bounded JSON."
                    raise HorizonControlError(msg) from exc
                if type(value) is not dict or "error" in value:
                    msg = "Observation reply must be a successful JSON object."
                    raise HorizonControlError(msg)
                return cast("dict[str, Any]", value)
        finally:
            if writer is not None:
                writer.close()
                try:
                    async with asyncio.timeout(CLOSE_TIMEOUT_S):
                        await writer.wait_closed()
                finally:
                    if self._writer is writer:
                        self._writer = None

    def _validate_observation(self, state: dict[str, Any], status: dict[str, Any]) -> None:
        server = status.get("server")
        player = state.get("player")
        if type(server) is not dict or type(player) is not dict:
            msg = "Target server or own player is unavailable."
            raise HorizonControlError(msg)
        server = cast("dict[str, Any]", server)
        player = cast("dict[str, Any]", player)
        position = player.get("position")
        if (
            server.get("address") != self.binding.server_address
            or server.get("name") != self.binding.client_name
            or server.get("joined") is not True
            or server.get("loaded") is not True
            or state.get("world") != self.binding.world
            or state.get("dimension") != self.binding.dimension
            or state.get("screen") != "playing"
            or state.get("paused") is not False
            or not _finite_real(player.get("health"))
            or player["health"] <= 0
            or type(position) is not list
            or len(cast("list[Any]", position)) != POSITION_COMPONENTS
            or not all(_finite_real(value) for value in cast("list[Any]", position))
        ):
            msg = "Current target identity, world, health or own pose is unavailable or changed."
            raise HorizonControlError(msg)

    async def observe(self) -> dict[str, Any]:
        """Return only a fresh own-state sample; never correlate player arrays."""
        if not self._settle_cancelled_reads:
            return await self._observe()
        observation = asyncio.create_task(self._observe(), name="horizon-target-observation")
        try:
            return await asyncio.shield(observation)
        except asyncio.CancelledError as cancellation:
            try:
                await complete_under_cancellation(observation)
            except BaseException:  # noqa: BLE001 - preserve caller cancellation after owned failure settlement
                # The finite read owns failure retirement; the caller still owns
                # its original cancellation, never the late sample or error.
                raise cancellation from None
            raise

    async def _observe(self) -> dict[str, Any]:
        """Bound the complete read, including lock wait, and retire on failure."""
        try:
            async with asyncio.timeout(self.binding.timeout_s * 2):
                async with self._lock:
                    self._check_identity()
                    state = await self._query("state")
                    status = await self._query("status")
                    self._validate_observation(state, status)
                    self._check_identity()
                    return state
        except BaseException:
            await self.aclose()
            raise

    async def aclose(self) -> None:
        """Disarm reads and close a waiting query without sending stop or locks."""
        self._closed = True
        writer = self._writer
        if writer is not None:
            writer.close()
