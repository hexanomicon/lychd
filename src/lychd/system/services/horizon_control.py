"""Explicit Linux Unix-socket session; observations are not server receipts.

No discovery, process launch, account files, TCP transport, or automatic replay.
An exclusive sibling lock coordinates cooperating sessions for one endpoint.
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import math
import os
import socket
import stat
import struct
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from lychd.domain.cortex.cancellation import RunEffectFence

MAX_REPLY_BYTES = 262144
MAX_CHAT_CHARS = 200
GOTO_PARTS = 8
POINT_PARTS = 4
RENDER_SIZE_PARTS = 2
MIN_ACTION_SECONDS = 0.25
MAX_ACTION_SECONDS = 5
DELETE_CHARACTER = 127
MAX_OWNERSHIP_BYTES = 16384
MAX_CHECKOUT_ROOTS = 32
MAX_COMMAND_BYTES = 2048
MIN_CONTROL_TIMEOUT = 0.1
MAX_CONTROL_TIMEOUT = 10
FIRST_PRINTABLE = 32
MIN_CELL_COORDINATE = -(2**31)
MAX_CELL_COORDINATE = 2**31 - 1
MIN_PLACEMENT_TIMEOUT = 6


class HorizonControlError(RuntimeError):
    """A refused or uncertain local control boundary."""


class HorizonNotSentError(HorizonControlError):
    """The physical handoff was fenced before any command bytes were written."""


@dataclass(frozen=True, kw_only=True)
class HorizonBinding:
    """Operator-pinned local process and client-reported world/server labels.

    Labels are observations, not authenticated game identity or a durable epoch.
    PID plus process start ticks protect against PID reuse within this session.
    """

    endpoint: Path
    pid: int
    start_ticks: int
    world: str
    dimension: str
    mode: Literal["remote", "singleplayer_lab"] = "remote"
    server_address: str = ""
    client_name: str = ""
    timeout_s: float = 5.0


@dataclass(frozen=True, kw_only=True)
class ControlOutcome:
    kind: Literal["client_observed", "refused", "client_error", "outcome_unknown"]
    detail: str
    observation: dict[str, Any] | None = None


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


def _project_renderer(renderer: dict[str, Any]) -> dict[str, Any]:
    selected = {
        key: renderer[key]
        for key in ("gpu", "vendor", "driver", "device_type", "backend", "present_mode")
        if type(renderer.get(key)) is str
    }
    selected.update(
        {
            key: renderer[key]
            for key in (
                "drawn_sections",
                "section_draws",
                "section_draw_calls",
                "culled_sections",
                "uploaded_bytes",
                "resident_sections",
                "arena_bytes",
                "section_vertex_bytes",
                "gpu_allocated_bytes",
                "gpu_reserved_bytes",
            )
            if type(renderer.get(key)) is int
        }
    )
    for key in ("gpu_allocated_bytes", "gpu_reserved_bytes"):
        if key in renderer and renderer[key] is None:
            selected[key] = None
    raw_size = renderer.get("size")
    size = cast("list[Any]", raw_size) if type(raw_size) is list else []
    if len(size) == RENDER_SIZE_PARTS and all(type(value) is int for value in size):
        selected["size"] = list(size)
    return selected


def _project_status(status: dict[str, Any]) -> dict[str, Any]:
    """Expose only operational leaves; raw diagnostics never enter observations."""
    result = {
        key: status[key]
        for key, expected in (("screen", str), ("dimension", str), ("creative", bool))
        if type(status.get(key)) is expected
    }
    result.update(
        {
            key: status[key]
            for key in (
                "frames",
                "ticks",
                "day_time",
                "render_distance",
                "chunks",
                "mobs",
                "block_entities",
                "pending_chunks",
                "generated_chunks",
                "meshed_sections",
                "dirty_light",
            )
            if type(status.get(key)) is int
        }
    )
    result.update(
        {
            key: status[key]
            for key in ("fps", "uptime_seconds")
            if type(status.get(key)) is int or (type(status.get(key)) is float and math.isfinite(status[key]))
        }
    )
    if "renderer" in status and status["renderer"] is None:
        result["renderer"] = None
    elif type(status.get("renderer")) is dict:
        result["renderer"] = _project_renderer(cast("dict[str, Any]", status["renderer"]))
    if "server" in status:
        if status["server"] is None:
            result["server"] = None
        elif type(status["server"]) is dict:
            server = cast("dict[str, Any]", status["server"])
            result["server"] = {
                key: server[key]
                for key, expected in (("address", str), ("name", str), ("joined", bool), ("loaded", bool))
                if type(server.get(key)) is expected
            }
        else:
            msg = "Client status server binding must be an object or null."
            raise HorizonControlError(msg)
    if "error" in status:
        result["error"] = "Client status reported an error."
    return result


def _ownership_root() -> Path:
    return Path("/tmp") / f"lychd-horizon-assist-{os.getuid()}"  # noqa: S108 - validated private per-user directory, never a shared file


def _process_start(pid: int) -> int:
    data = Path(f"/proc/{pid}/stat").read_text()
    return int(data.rsplit(")", 1)[1].split()[19])


def _generation_live(pid: int, start_ticks: int) -> bool:
    try:
        return _process_start(pid) == start_ticks
    except FileNotFoundError:
        return False


def _read_record(fd: int) -> dict[str, Any] | None:
    os.lseek(fd, 0, os.SEEK_SET)
    raw = os.read(fd, MAX_OWNERSHIP_BYTES + 1)
    if not raw:
        return None
    decoded = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
    if type(decoded) is not dict:
        msg = "Ownership record must be an object."
        raise HorizonControlError(msg)
    value = cast("dict[str, Any]", decoded)
    if (
        len(raw) > MAX_OWNERSHIP_BYTES
        or set(value) != {"pid", "start_ticks", "endpoint", "state"}
        or type(value["pid"]) is not int
        or value["pid"] <= 0
        or type(value["start_ticks"]) is not int
        or value["start_ticks"] <= 0
        or type(value["endpoint"]) is not str
        or value["state"] not in {"active", "clean", "unknown"}
    ):
        msg = "Malformed ownership record; operator reconciliation is required."
        raise HorizonControlError(msg)
    return value


def _write_record(fd: int, record: dict[str, Any]) -> None:
    data = json.dumps(record, sort_keys=True).encode()
    os.lseek(fd, 0, os.SEEK_SET)
    remaining = memoryview(data)
    while remaining:
        written = os.write(fd, remaining)
        if written <= 0:
            msg = "Ownership record write made no progress."
            raise HorizonControlError(msg)
        remaining = remaining[written:]
    os.ftruncate(fd, len(data))
    os.fsync(fd)


def _validate_action_line(line: str, query: bool) -> None:  # noqa: FBT001 - port contract carries query semantics
    parts = line.split()
    valid = line in {"state", "status"} if query else False
    if not query and len(parts) == POINT_PARTS and parts[0] == "place":
        try:
            values = tuple(int(value) for value in parts[1:])
            valid = line == "place " + " ".join(str(value) for value in values) and all(
                MIN_CELL_COORDINATE <= value <= MAX_CELL_COORDINATE for value in values
            )
        except ValueError:
            valid = False
    if not query and line.startswith("chat "):
        text = line[5:]
        valid = bool(text) and text == text.strip() and not text.startswith("/") and len(text) <= MAX_CHAT_CHARS
    if not query and len(parts) in {POINT_PARTS, GOTO_PARTS} and parts[0] in {"look-at", "goto"}:
        try:
            valid = all(math.isfinite(float(value)) for value in parts[1:4])
            if parts[0] == "goto":
                valid = (
                    valid
                    and len(parts) == GOTO_PARTS
                    and parts[4:7] == ["--near", "1.5", "--timeout"]
                    and MIN_ACTION_SECONDS <= float(parts[7]) <= MAX_ACTION_SECONDS
                )
            else:
                valid = valid and len(parts) == POINT_PARTS
        except ValueError:
            valid = False
    if not valid or any(ord(char) < FIRST_PRINTABLE or ord(char) == DELETE_CHARACTER for char in line):
        msg = "Command is outside the closed assist dialect."
        raise HorizonControlError(msg)


class HorizonControlSession:
    """Own one endpoint and at most one finite action, until explicit closure."""

    def __init__(self, binding: HorizonBinding) -> None:
        """Bind explicit parameters without acquiring the endpoint."""
        self.binding = binding
        self.fence_guard = RunEffectFence()
        self._lock_fd: int | None = None
        self._generation_fd: int | None = None
        self._quarantined = False
        self._new_endpoint_record = False
        self._inode: tuple[int, int] | None = None
        self._owner: str | None = None
        self._pending: asyncio.Task[dict[str, Any]] | None = None
        self._attempts: dict[str, ControlOutcome] = {}
        self._contain_lock = asyncio.Lock()
        self._armed = False
        self._uncertain = False
        self._query_count = 0

    @property
    def attempts(self) -> dict[str, ControlOutcome]:
        """Return detached attempt dispositions, without granting replay."""
        return dict(self._attempts)

    @property
    def query_count(self) -> int:
        """Count query lines handed to a socket in this controller process."""
        return self._query_count

    def _endpoint_identity(self) -> tuple[int, int]:
        path = self.binding.endpoint
        if not path.is_absolute() or any(part.is_symlink() for part in (path, *path.parents)):
            msg = "Endpoint must be an absolute path without symlinks."
            raise HorizonControlError(msg)
        info = path.stat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            msg = "Endpoint must be an owned Unix socket."
            raise HorizonControlError(msg)
        return info.st_dev, info.st_ino

    def _check_process(self) -> None:
        # /proc/PID/stat comm may contain spaces and closing parentheses.
        if _process_start(self.binding.pid) != self.binding.start_ticks:
            msg = "Client process generation changed."
            raise HorizonControlError(msg)

    def _record(self, state: str) -> dict[str, Any]:
        return {
            "pid": self.binding.pid,
            "start_ticks": self.binding.start_ticks,
            "endpoint": str(self.binding.endpoint),
            "state": state,
        }

    def _acquire_generation(self) -> None:  # noqa: C901, PLR0915 - one descriptor-owned generation admission transaction
        root = _ownership_root()
        with suppress(FileExistsError):
            root.mkdir(mode=0o700)
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or root.is_symlink():
            msg = "Ownership directory must be a private real owned directory."
            raise HorizonControlError(msg)
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        generation_fd: int | None = None
        try:
            if self._lock_fd is None:
                msg = "Endpoint ownership was not acquired."
                raise HorizonControlError(msg)
            previous = _read_record(self._lock_fd)
            if previous is None and not self._new_endpoint_record:
                msg = "Empty existing endpoint record requires operator reconciliation."
                raise HorizonControlError(msg)
            if previous is not None:
                same = (previous["pid"], previous["start_ticks"]) == (self.binding.pid, self.binding.start_ticks)
                if (same and previous["state"] != "clean") or (
                    not same and _generation_live(previous["pid"], previous["start_ticks"])
                ):
                    msg = "Prior endpoint generation remains live or uncertain; restart/reconciliation is required."
                    raise HorizonControlError(msg)
            name = f"{self.binding.pid}-{self.binding.start_ticks}.json"
            new_generation = True
            try:
                generation_fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=root_fd)
            except FileExistsError:
                new_generation = False
                generation_fd = os.open(name, os.O_RDWR | os.O_NOFOLLOW, dir_fd=root_fd)
            generation_info = os.fstat(generation_fd)
            if (
                not stat.S_ISREG(generation_info.st_mode)
                or generation_info.st_uid != os.getuid()
                or generation_info.st_nlink != 1
                or generation_info.st_mode & 0o077
            ):
                msg = "Invalid client generation record."
                raise HorizonControlError(msg)
            fcntl.flock(generation_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            record = _read_record(generation_fd)
            if record is None and not new_generation:
                msg = "Empty existing generation record requires operator reconciliation."
                raise HorizonControlError(msg)
            if record is not None and (
                record["pid"] != self.binding.pid
                or record["start_ticks"] != self.binding.start_ticks
                or record["state"] != "clean"
            ):
                msg = "Client generation is quarantined or was interrupted; restart/reconciliation is required."
                raise HorizonControlError(msg)
            _write_record(generation_fd, self._record("active"))
            os.fsync(root_fd)
            _write_record(self._lock_fd, self._record("active"))
            parent_fd = os.open(self.binding.endpoint.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
            self._generation_fd = generation_fd
            generation_fd = None
        finally:
            if generation_fd is not None:
                os.close(generation_fd)
            os.close(root_fd)

    def _settle_records(self, state: str) -> None:
        if self._generation_fd is not None:
            _write_record(self._generation_fd, self._record(state))
            if self._lock_fd is None:
                msg = "Endpoint ownership disappeared before settlement."
                raise HorizonControlError(msg)
            _write_record(self._lock_fd, self._record(state))

    async def open(self) -> None:
        """Acquire endpoint ownership and verify the supplied observation binding."""
        if self._lock_fd is not None:
            msg = "Session is already open."
            raise HorizonControlError(msg)
        if self.binding.pid <= 0 or not MIN_CONTROL_TIMEOUT <= self.binding.timeout_s <= MAX_CONTROL_TIMEOUT:
            msg = "Invalid process or timeout bound."
            raise HorizonControlError(msg)
        if self.binding.mode == "singleplayer_lab" and (
            type(self.binding.world) is not str or not self.binding.world.strip()
        ):
            msg = "Single-player lab requires a nonempty observed world label."
            raise HorizonControlError(msg)
        self._inode = self._endpoint_identity()
        lock_path = self.binding.endpoint.with_name(self.binding.endpoint.name + ".lychd-assist.lock")
        self._new_endpoint_record = True
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            self._new_endpoint_record = False
            fd = os.open(lock_path, os.O_RDWR | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_nlink != 1
                or info.st_mode & 0o077
            ):
                msg = "Invalid endpoint ownership lock."
                raise HorizonControlError(msg)  # noqa: TRY301 - close the acquired descriptor on refusal
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_fd = fd
            self._check_process()
            self._acquire_generation()
            await self.observe()
            self._armed = True
        except BaseException:
            try:
                # No action can issue until open has returned, so admission failure is clean.
                self._settle_records("clean")
            finally:
                if self._generation_fd is not None:
                    os.close(self._generation_fd)
                    self._generation_fd = None
                self._lock_fd = None
                os.close(fd)
            raise

    async def _exchange(  # noqa: C901 - verify binding, send boundary and strict reply in one owned connection
        self, line: str, *, issue_run: str | None = None, authorize: Callable[[], None] | None = None
    ) -> dict[str, Any]:
        """Read one strict JSON object, projecting status before any consumer sees it."""
        if self._lock_fd is None or self._endpoint_identity() != self._inode:
            msg = "Endpoint generation changed or session is closed."
            raise HorizonControlError(msg)
        if not line or len(line.encode()) > MAX_COMMAND_BYTES or any(ord(char) < FIRST_PRINTABLE for char in line):
            msg = "Invalid control line."
            raise HorizonControlError(msg)
        self._check_process()
        writer: asyncio.StreamWriter | None = None
        try:
            async with asyncio.timeout(self.binding.timeout_s):
                reader, writer = await asyncio.open_unix_connection(str(self.binding.endpoint), limit=MAX_REPLY_BYTES)
                peer = writer.get_extra_info("socket")
                if peer is None or not hasattr(socket, "SO_PEERCRED"):
                    msg = "Linux peer credentials are required."
                    raise HorizonNotSentError(msg)
                pid, uid, _ = struct.unpack("3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if pid != self.binding.pid or uid != os.getuid() or self._endpoint_identity() != self._inode:
                    msg = "Control peer differs from the pinned client."
                    raise HorizonControlError(msg)
                try:
                    self._check_process()
                except (OSError, ValueError, HorizonControlError) as exc:
                    msg = "Client process generation changed before write."
                    raise HorizonNotSentError(msg) from exc
                if issue_run is not None and (not self._armed or self.fence_guard.reason(issue_run, 0)):
                    msg = "Action fenced immediately before physical send."
                    raise HorizonNotSentError(msg)
                if authorize is not None:
                    try:
                        authorize()
                    except ValueError as exc:
                        msg = "Session authority refused immediately before send."
                        raise HorizonNotSentError(msg) from exc
                writer.write(line.encode() + b"\n")
                self._query_count += int(line in {"state", "status", "inventory"} or line.startswith("block "))
                await writer.drain()
                raw = await reader.readline()
                if not raw.endswith(b"\n") or len(raw) > MAX_REPLY_BYTES:
                    msg = "Control reply is incomplete or too large."
                    raise HorizonControlError(msg)
                value = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant, parse_float=_finite_float)
                if type(value) is not dict:
                    msg = "Control reply must be a JSON object."
                    raise HorizonControlError(msg)
                return (
                    _project_status(cast("dict[str, Any]", value))
                    if line == "status"
                    else cast("dict[str, Any]", value)
                )
        finally:
            if writer is not None:
                writer.close()
                await writer.wait_closed()

    async def observe(self) -> dict[str, Any]:
        """Recheck current client labels; never correlate unordered player lists."""
        state = await self._exchange("state")
        status = await self._exchange("status")
        raw_server = status.get("server")
        raw_player = state.get("player")
        server = cast("dict[str, Any]", raw_server) if type(raw_server) is dict else None
        player = cast("dict[str, Any]", raw_player) if type(raw_player) is dict else None
        remote_matches = (
            server is not None
            and bool(self.binding.server_address)
            and bool(self.binding.client_name)
            and server.get("address") == self.binding.server_address
            and server.get("name") == self.binding.client_name
            and server.get("joined") is True
            and server.get("loaded") is True
        )
        mode_matches = (self.binding.mode == "remote" and remote_matches) or (
            self.binding.mode == "singleplayer_lab" and "server" in status and raw_server is None
        )
        if (
            "error" in state
            or "error" in status
            or state.get("world") != self.binding.world
            or state.get("dimension") != self.binding.dimension
            or state.get("screen") != "playing"
            or state.get("paused") is not False
            or player is None
            or type(player.get("health")) not in (float, int)
            or player["health"] <= 0
            or not mode_matches
        ):
            self._armed = False
            msg = "Current client/world binding is unavailable or changed."
            raise HorizonControlError(msg)
        return state

    def _require_inspection(self) -> None:
        if self._lock_fd is None or not self._armed:
            msg = "Inspection requires an open, armed session."
            raise HorizonControlError(msg)

    async def _inspect(self, cell: tuple[int, int, int] | None) -> dict[str, Any]:
        self._require_inspection()
        line = "inventory" if cell is None else f"block {cell[0]} {cell[1]} {cell[2]}"
        try:
            async with asyncio.timeout(self.binding.timeout_s):
                await self.observe()
                observation = await self._exchange(line, authorize=self._require_inspection)
                if "error" in observation:
                    msg = "Client inspection reported an error."
                    raise HorizonControlError(msg)  # noqa: TRY301 - every failed read disarms this session
                self._require_inspection()
                if self._endpoint_identity() != self._inode:
                    msg = "Endpoint generation changed during inspection."
                    raise HorizonControlError(msg)  # noqa: TRY301 - reject a replaced endpoint after its reply
                self._check_process()
        except asyncio.CancelledError:
            self._armed = False
            raise
        except (OSError, ValueError, HorizonControlError, TimeoutError) as exc:
            self._armed = False
            msg = "Current client inspection is unavailable."
            raise HorizonControlError(msg) from exc
        return observation

    async def inspect_cell(self, x: int, y: int, z: int) -> dict[str, Any]:
        """Read one exact i32 cell under fresh binding checks; consume no effect attempt."""
        if any(
            type(value) is not int or not MIN_CELL_COORDINATE <= value <= MAX_CELL_COORDINATE for value in (x, y, z)
        ):
            msg = "Cell coordinates require original i32 integers."
            raise HorizonControlError(msg)
        return await self._inspect((x, y, z))

    async def inspect_inventory(self) -> dict[str, Any]:
        """Read raw held/inventory observations without selecting or moving any item."""
        return await self._inspect(None)

    async def invoke(  # noqa: C901, PLR0911, PLR0912 - distinguish refusal, handoff and post-observation
        self, run_id: str, line: str, *, query: bool = False, authorize: Callable[[dict[str, Any]], None] | None = None
    ) -> ControlOutcome:
        """Attempt one command per Run; a retained attempt is never sent again."""
        if run_id in self._attempts:
            return self._attempts[run_id]
        _validate_action_line(line, query)
        if self._owner is not None or not self._armed or self.fence_guard.reason(run_id, 0):
            return ControlOutcome(kind="refused", detail="Session unavailable, busy or fenced.")
        if line.startswith("place ") and self.binding.timeout_s < MIN_PLACEMENT_TIMEOUT:
            return ControlOutcome(
                kind="refused", detail="Placement requires a control timeout of at least six seconds."
            )
        self._owner = run_id
        try:
            try:
                state = await self.observe()
                if state.get("busy") is not None:
                    return ControlOutcome(kind="refused", detail="Client already has an active action.")
            except (OSError, ValueError, HorizonControlError, TimeoutError):
                self._armed = False
                return ControlOutcome(kind="refused", detail="Client binding could not be verified.")
            if not self._armed or self.fence_guard.reason(run_id, 0):
                return ControlOutcome(kind="refused", detail="Session fenced before send.")
            self._attempts[run_id] = ControlOutcome(
                kind="outcome_unknown", detail="Command attempt retained before send."
            )
            self._uncertain = True
            self._pending = asyncio.create_task(
                self._exchange(
                    line, issue_run=run_id, authorize=(lambda: authorize(state)) if authorize is not None else None
                ),
                name=f"horizon:{run_id}",
            )
            try:
                observation = await asyncio.shield(self._pending)
            except HorizonNotSentError:
                result = ControlOutcome(kind="refused", detail="Current authority refused before send.")
                self._attempts[run_id] = result
                self._uncertain = False
                return result
            except asyncio.CancelledError:
                self.fence(run_id, "cancelled")
                raise
            except (OSError, ValueError, HorizonControlError, TimeoutError):
                self._armed = False
                return self._attempts[run_id]
            try:
                after = await self.observe()
                if after.get("busy") is not None:
                    self._armed = False
                    return self._attempts[run_id]
            except (OSError, ValueError, HorizonControlError, TimeoutError):
                self._armed = False
                return self._attempts[run_id]
            if "error" in observation or (not query and observation.get("ok") is not True):
                result = ControlOutcome(
                    kind="client_error",
                    detail="Client reported an error; prior effects may remain.",
                    observation=observation,
                )
            else:
                result = ControlOutcome(
                    kind="client_observed", detail="Client response only; no server receipt.", observation=observation
                )
            self._attempts[run_id] = result
            self._uncertain = False
            return result
        finally:
            if not self._uncertain:
                self._pending = None
                self._owner = None

    def fence(self, run_id: str, reason: str) -> None:
        self.fence_guard.fence(run_id, reason)

    def fence_claim(self, run_id: str, enqueue_seq: int, reason: str) -> None:
        # This one-attempt adapter cannot resume a failed claim under the same
        # Run identity. Retire the whole Run even when the worker fences a
        # nonzero claim; handoff checks deliberately have no successor claim.
        self.fence_guard.fence_claim(run_id, enqueue_seq, reason)
        self.fence(run_id, reason)

    def fence_all(self, reason: str) -> None:
        self._armed = False
        self.fence_guard.fence_all(reason)

    async def contain(self, run_id: str) -> None:
        """Stop on another connection and drain the original command before idle proof.

        A first stop can overtake the original command in Horizon's queue. Repeat
        until its original reply is terminal, then stop and observe idle once more.
        """
        self.fence(run_id, "containment")
        async with self._contain_lock:
            if self._owner != run_id:
                return
            try:
                async with asyncio.timeout(self.binding.timeout_s * 3):
                    for _ in range(3):
                        stopped = await self._exchange("stop")
                        if stopped.get("ok") is not True:
                            msg = "Client did not acknowledge stop."
                            raise HorizonControlError(msg)  # noqa: TRY301 - disarm the session on failed stop
                        pending = self._pending
                        if pending is None or pending.done():
                            if pending is not None:
                                # Retrieve failures; no response is not terminal game proof.
                                with suppress(HorizonNotSentError):
                                    pending.result()
                            state = await self.observe()
                            if state.get("busy") is None:
                                self._owner = None
                                self._pending = None
                                self._uncertain = False
                                return
                        if pending is not None:
                            await asyncio.wait({pending}, timeout=self.binding.timeout_s / 3)
                    msg = "Original action has not settled after stop."
                    raise HorizonControlError(msg)  # noqa: TRY301 - disarm unresolved work
            except BaseException:
                self._armed = False
                raise

    async def contain_all(self) -> None:
        self.fence_all("shutdown")
        if self._owner is not None:
            await self.contain(self._owner)

    async def aclose(self) -> None:
        """Release ownership only after owned work has stopped or closure refuses."""
        try:
            await self.contain_all()
        except BaseException:
            self._quarantined = True
            self._settle_records("unknown")
            raise
        finally:
            if not self._quarantined:
                self._settle_records("clean")
            pending = self._pending
            if pending is not None and not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            if self._lock_fd is not None:
                os.close(self._lock_fd)
                self._lock_fd = None
            if self._generation_fd is not None:
                os.close(self._generation_fd)
                self._generation_fd = None


def load_assist_profile(profile_path: Path) -> tuple[HorizonBinding, dict[str, Any], Path]:  # noqa: C901, PLR0915 - validate the complete private input boundary before returning a profile
    """Read only the supplied bounded public profile and private workspace metadata."""
    checkout = Path(__file__).resolve().parents[4]
    if (
        not profile_path.is_absolute()
        or any(part.is_symlink() for part in (profile_path, *profile_path.parents))
        or profile_path.resolve().is_relative_to(checkout)
    ):
        msg = "Profile must be an explicit absolute path outside the checkout."
        raise HorizonControlError(msg)
    descriptor = os.open(profile_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_REPLY_BYTES:
            msg = "Profile must be a bounded regular file."
            raise HorizonControlError(msg)
        raw = stream.read(MAX_REPLY_BYTES + 1)
        after = os.fstat(stream.fileno())
        current = profile_path.stat(follow_symlinks=False)

        def signature(value: os.stat_result) -> tuple[int, int, int, int, int]:
            return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns

        if len(raw) != info.st_size or signature(info) != signature(after) or signature(info) != signature(current):
            msg = "Profile changed or was replaced during the bounded read."
            raise HorizonControlError(msg)
        decoded = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant, parse_float=_finite_float)
    if type(decoded) is not dict:
        msg = "Profile must be an object."
        raise HorizonControlError(msg)
    document = cast("dict[str, Any]", decoded)
    if set(document) != {"binding", "policy", "workspace", "checkout_roots"}:
        msg = "Profile requires exactly binding, policy, workspace and checkout_roots."
        raise HorizonControlError(msg)
    raw_declared = document["checkout_roots"]
    if type(raw_declared) is not list:
        msg = "Checkout roots must be a list."
        raise HorizonControlError(msg)
    declared = cast("list[Any]", raw_declared)
    if not declared or len(declared) > MAX_CHECKOUT_ROOTS or any(type(root) is not str for root in declared):
        msg = "Declare a nonempty bounded list of absolute checkout directories."
        raise HorizonControlError(msg)
    roots = [checkout]
    for value in declared:
        root = Path(value)
        if not root.is_absolute() or any(part.is_symlink() for part in (root, *root.parents)) or not root.is_dir():
            msg = "Checkout roots must be existing absolute directories without symlinks."
            raise HorizonControlError(msg)
        roots.append(root.resolve(strict=True))
    if (
        type(document["workspace"]) is not str
        or type(document["binding"]) is not dict
        or type(document["policy"]) is not dict
    ):
        msg = "Workspace must be a path string; binding and policy must be objects."
        raise HorizonControlError(msg)
    workspace = Path(document["workspace"])
    if (
        not workspace.is_absolute()
        or any(workspace.resolve().is_relative_to(root) or root.is_relative_to(workspace.resolve()) for root in roots)
        or any(part.is_symlink() for part in (workspace, *workspace.parents))
        or not workspace.is_dir()
        or workspace.stat().st_uid != os.getuid()
        or workspace.stat().st_mode & 0o077
    ):
        msg = "Workspace must be private, owned and disjoint from every checkout in both directions."
        raise HorizonControlError(msg)
    workspace = workspace.resolve(strict=True)
    if not profile_path.resolve().is_relative_to(workspace) or any(
        profile_path.resolve().is_relative_to(root) for root in roots
    ):
        msg = "Profile must remain inside the private workspace and outside every checkout."
        raise HorizonControlError(msg)
    binding_data = dict(cast("dict[str, Any]", document["binding"]))
    binding_data["endpoint"] = Path(binding_data["endpoint"])
    return HorizonBinding(**binding_data), cast("dict[str, Any]", document["policy"]), workspace


async def run_assist_cli(profile_path: Path, text: str, *, transcript: bool = False) -> dict[str, Any]:
    """Run one explicitly configured local request and retain private JSONL evidence.

    The supplied profile, socket and workspace are operator inputs; this function
    reads no Settings, account, token or environment configuration files.
    """
    from uuid import uuid4

    from lychd.compositions.blockworld.horizon_assist import (
        AssistPolicy,
        AssistRequest,
        HorizonAssistService,
        parse_text,
    )
    from lychd.compositions.blockworld.horizon_assist_runtime import LocalAssistRunner

    binding, policy_document, workspace = await asyncio.to_thread(load_assist_profile, profile_path)
    control = HorizonControlSession(binding)
    policy = AssistPolicy.model_validate_json(json.dumps(policy_document))
    request = AssistRequest(
        request_id=str(uuid4()), action=parse_text(text), transcript=text, source="transcript" if transcript else "text"
    )
    evidence_path = workspace / f"horizon-assist-{request.request_id}.jsonl"
    runner = LocalAssistRunner(HorizonAssistService(policy, control), control)
    evidence_fd = os.open(evidence_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(evidence_fd, "w", encoding="utf-8") as evidence:
        await control.open()
        try:
            await runner.open()
            run_id = await runner.submit(request)
            try:
                await runner.wait(run_id)
            except asyncio.CancelledError:
                await runner.cancel()
                raise
            finally:
                if runner.services is not None:
                    await runner.services.bus.wait_persisted(run_id)
                    events = await runner.services.ledger.list_events(run_id, limit=100)
                    for event in events:
                        evidence.write(event.model_dump_json() + "\n")
                    evidence.flush()
                    os.fsync(evidence.fileno())
            result = runner.assist.results.get(request.request_id)
            return {
                "run_id": run_id,
                "delivery": "experimental_process_local",
                "evidence": str(evidence_path),
                "result": result.model_dump(mode="json") if result is not None else None,
            }
        finally:
            await runner.aclose()


def assist_main(arguments: list[str] | None = None) -> None:
    """Expose an opt-in one-action command with SIGINT as its priority stop."""
    import argparse

    parser = argparse.ArgumentParser(description="Experimental local Horizon assistance; client observations only.")
    parser.add_argument(
        "--profile",
        required=True,
        type=Path,
        help="Private JSON profile with binding, policy, workspace and nonempty checkout_roots.",
    )
    parser.add_argument("--text", required=True, help="One exact English/Slovak instruction.")
    parser.add_argument(
        "--transcript", action="store_true", help="Attribute text as an externally supplied transcript."
    )
    options = parser.parse_args(arguments)
    try:
        result = asyncio.run(run_assist_cli(options.profile, options.text, transcript=options.transcript))
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    import sys

    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
