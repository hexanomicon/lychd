"""Private, bounded host diagnostic observations; never application recovery truth."""

from __future__ import annotations

import fcntl
import json
import os
import queue
import sqlite3
import stat
import threading
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import TracebackType
from typing import Any, NoReturn, Self
from urllib.parse import quote
from uuid import UUID

from lychd.compositions.reach.operator_diagnostics import write_diagnostic_line
from lychd.compositions.reach.operator_trace import MAX_TRACE_BYTES, ReachTraceEvent, trace_bytes

DATABASE_NAME = "trace.sqlite3"
QUEUE_CAPACITY = 256
MAX_EVENTS = 100_000
RETENTION_DAYS = 30
MAX_DATABASE_BYTES = 128 * 1024 * 1024
_PAGE_SIZE = 4096
_APPLICATION_ID = 0x4C595452
_VERSION = 1
_BATCH_SIZE = 32
_BATCH_SECONDS = 0.1
_MAINTENANCE_SECONDS = 60.0
_MAX_WAIT_SECONDS = 30
_MAX_QUERY_RECORDS = 1000
_MAX_LINK_IDENTITIES = 256
_MAX_PLATFORM_ID_CHARS = 20
_SPACE_RETRIES = 4
_INSERT_RESERVE_PAGES = 12
_MIN_RESERVE_PAGES = 16
_MIN_RETIREMENT_ROWS = 64
_FAILURES = frozenset({"error", "failed", "refused", "unavailable", "unknown", "rejected", "cancelled"})
_IDENTITIES = ("run_id", "request_id", "call_id", "platform_event_id")
_SCHEMA = (
    (
        "CREATE TABLE archive_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
        "next_ingest INTEGER NOT NULL, dropped_total INTEGER NOT NULL, pruned_total INTEGER NOT NULL, "
        "write_failures INTEGER NOT NULL, producer_gaps INTEGER NOT NULL)"
    ),
    (
        "CREATE TABLE events (ingest_id INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, "
        "received_at TEXT NOT NULL, producer TEXT NOT NULL, generation TEXT, run_id TEXT, request_id TEXT, "
        "call_id TEXT, platform_event_id TEXT, name TEXT NOT NULL, status TEXT NOT NULL, "
        "trace_seq INTEGER NOT NULL, failure INTEGER NOT NULL CHECK(failure IN (0,1)), "
        f"record_json TEXT NOT NULL CHECK(length(record_json)<={MAX_TRACE_BYTES}))"
    ),
    *(f"CREATE INDEX events_{name} ON events ({name}, ingest_id)" for name in (*_IDENTITIES, "generation")),
    "CREATE INDEX events_received ON events (received_at, ingest_id)",
    "CREATE INDEX events_failure ON events (failure, ingest_id)",
    "CREATE INDEX events_producer ON events (producer, generation, ingest_id)",
)


class TraceArchiveError(ValueError):
    """A fixed diagnostic category, without database or foreign input text."""


def _refuse(code: str = "trace_archive_unavailable") -> NoReturn:
    raise TraceArchiveError(code)


def _now() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _private(descriptor: int, *, directory: bool) -> os.stat_result:
    info = os.fstat(descriptor)
    expected = 0o700 if directory else 0o600
    valid = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if (
        not valid
        or stat.S_IMODE(info.st_mode) != expected
        or info.st_uid != os.getuid()
        or (not directory and info.st_nlink != 1)
    ):
        _refuse("trace_archive_unsafe_path")
    return info


def _root(path: Path, *, create: bool) -> int:
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        _refuse("trace_archive_unsafe_path")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink() or (current / ".git").exists():
            _refuse("trace_archive_unsafe_path")
        if not current.exists() and create:
            current.mkdir(mode=0o700)
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        _private(descriptor, directory=True)
        _check_files(descriptor)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _check_files(root_fd: int) -> None:
    for name in os.listdir(root_fd):
        if name not in {DATABASE_NAME, DATABASE_NAME + "-journal", "writer.lock"}:
            _refuse("trace_archive_unsafe_path")
        try:
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
        except FileNotFoundError:
            if name == DATABASE_NAME + "-journal":
                continue
            raise
        try:
            _private(descriptor, directory=False)
        finally:
            os.close(descriptor)


def _connection(path: Path, *, readonly: bool) -> sqlite3.Connection:
    uri = f"file:{quote(str(path), safe='/')}?mode={'ro' if readonly else 'rw'}"
    connection = sqlite3.connect(uri, uri=True, timeout=0.1, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=100")
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.execute("PRAGMA temp_store=MEMORY")
    if readonly:
        connection.execute("PRAGMA query_only=ON")
    return connection


def _validate_schema(connection: sqlite3.Connection) -> None:
    if (
        connection.execute("PRAGMA application_id").fetchone()[0] != _APPLICATION_ID
        or connection.execute("PRAGMA user_version").fetchone()[0] != _VERSION
        or connection.execute("PRAGMA page_size").fetchone()[0] != _PAGE_SIZE
        or connection.execute("PRAGMA journal_mode").fetchone()[0] != "delete"
    ):
        _refuse("trace_archive_schema")
    actual = {row[0]: row[1] for row in connection.execute("SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL")}
    expected = {statement.split()[2]: statement for statement in _SCHEMA}
    if actual != expected:
        _refuse("trace_archive_schema")
    row = connection.execute("SELECT * FROM archive_meta").fetchall()
    if (
        len(row) != 1
        or any(type(value) is not int or value < 0 for value in row[0])
        or row[0]["singleton"] != 1
        or row[0]["next_ingest"] < 1
    ):
        _refuse("trace_archive_schema")
    if connection.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
        _refuse("trace_archive_corrupt")


@dataclass(frozen=True, slots=True)
class _Observation:
    event: ReachTraceEvent
    raw: str
    received_at: str


@dataclass(slots=True)
class _Barrier:
    done: threading.Event = field(default_factory=threading.Event)
    success: bool = False


class TraceArchive:
    """One finite host writer; producers never wait for storage or queue capacity."""

    def __init__(self, directory: Path) -> None:
        """Admit a private partition and wait at most five seconds for schema validation."""
        self.directory = directory
        self._queue: queue.Queue[_Observation | _Barrier] = queue.Queue(QUEUE_CAPACITY)
        self._state = threading.Lock()
        self._closing = threading.Event()
        self._ready = threading.Event()
        self._startup_error: str | None = None
        self._pending_drops = self._pending_failures = 0
        self._persisted_drops = self._persisted_failures = 0
        self._producer_heads: dict[tuple[str, str], int] = {}
        self._capture_failed = False
        self._drained = False
        self._root_fd = self._lock_fd = self._db_fd = -1
        try:
            self._root_fd = _root(directory, create=True)
            self._lock_fd = os.open(
                "writer.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self._root_fd
            )
            _private(self._lock_fd, directory=False)
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._created = not (directory / DATABASE_NAME).exists()
            flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
            if self._created:
                flags |= os.O_CREAT | os.O_EXCL
            self._db_fd = os.open(DATABASE_NAME, flags, 0o600, dir_fd=self._root_fd)
            self._db_identity = _private(self._db_fd, directory=False)
        except (OSError, ValueError):
            self._release()
            code = "trace_archive_unsafe_path"
            raise TraceArchiveError(code) from None
        self._thread = threading.Thread(target=self._run, name="reach-trace-writer", daemon=True)
        self._thread.start()
        if not self._ready.wait(5):
            self.close()
            _refuse()
        if self._startup_error is not None:
            self._thread.join(2)
            _refuse(self._startup_error)

    def __enter__(self) -> Self:
        """Keep archive ownership within the supervisor's explicit lifetime."""
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Attempt the same finite drain on normal exit and exception unwinding."""
        self.close()

    def _release(self) -> None:
        for name in ("_db_fd", "_lock_fd", "_root_fd"):
            descriptor = getattr(self, name)
            if descriptor >= 0:
                os.close(descriptor)
                setattr(self, name, -1)

    def _attest(self) -> None:
        root_info = self.directory.stat(follow_symlinks=False)
        pinned = _private(self._root_fd, directory=True)
        info = (self.directory / DATABASE_NAME).stat(follow_symlinks=False)
        if (root_info.st_dev, root_info.st_ino) != (pinned.st_dev, pinned.st_ino) or (info.st_dev, info.st_ino) != (
            self._db_identity.st_dev,
            self._db_identity.st_ino,
        ):
            _refuse("trace_archive_unsafe_path")
        _private(self._db_fd, directory=False)
        _check_files(self._root_fd)

    def emit(self, event: ReachTraceEvent) -> None:
        """Validate detached allowlisted bytes and drop immediately when capture is occupied."""
        try:
            raw = trace_bytes(event)
            detached = ReachTraceEvent.model_validate_json(raw)
            observation = _Observation(detached, raw.decode("ascii").rstrip("\n"), _timestamp(_now()))
        except (ValueError, TypeError, UnicodeError):
            with self._state:
                self._pending_drops += 1
            return
        with self._state:
            if self._closing.is_set():
                self._pending_drops += 1
                return
            try:
                self._queue.put_nowait(observation)
            except queue.Full:
                self._pending_drops += 1

    def flush(self, timeout: float = 2) -> bool:
        """Explicitly wait for prior intake and counters; ordinary producers never call this."""
        if not 0 < timeout <= _MAX_WAIT_SECONDS or self._closing.is_set():
            return False
        deadline = time.monotonic() + timeout
        barrier = _Barrier()
        try:
            self._queue.put(barrier, timeout=timeout)
        except queue.Full:
            return False
        return barrier.done.wait(max(0, deadline - time.monotonic())) and barrier.success

    def close(self, timeout: float = 2) -> bool:
        """Stop intake and drain within the caller's finite deadline."""
        if not 0 < timeout <= _MAX_WAIT_SECONDS:
            return False
        with self._state:
            self._closing.set()
        self._thread.join(timeout)
        return not self._thread.is_alive() and self._drained

    def health(self) -> dict[str, int | bool]:
        """Expose local capture health without interpreting an execution outcome."""
        with self._state:
            return {
                "queued": self._queue.qsize(),
                "dropped_total": self._persisted_drops + self._pending_drops,
                "write_failures": self._persisted_failures + self._pending_failures,
                "closed": self._closing.is_set(),
            }

    def _run(self) -> None:
        connection = None
        try:
            connection = _connection(self.directory / DATABASE_NAME, readonly=False)
            self._attest()
            deadline = time.monotonic() + 4
            connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            if self._created:
                connection.execute(f"PRAGMA page_size={_PAGE_SIZE}")
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
                for statement in _SCHEMA:
                    connection.execute(statement)
                connection.execute("INSERT INTO archive_meta VALUES (1,1,0,0,0,0)")
                connection.execute(f"PRAGMA application_id={_APPLICATION_ID}")
                connection.execute(f"PRAGMA user_version={_VERSION}")
                connection.execute("COMMIT")
                os.fsync(self._root_fd)
            _validate_schema(connection)
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute(f"PRAGMA max_page_count={MAX_DATABASE_BYTES // _PAGE_SIZE}")
            metadata = connection.execute("SELECT * FROM archive_meta").fetchone()
            self._persisted_drops = metadata["dropped_total"]
            self._persisted_failures = metadata["write_failures"]
            self._attest()
            connection.set_progress_handler(None, 0)
            if not self._commit(connection, [], force=True):
                _refuse()
            self._ready.set()
            self._consume(connection)
        except (OSError, ValueError, sqlite3.Error):
            if not self._ready.is_set():
                self._startup_error = "trace_archive_schema"
            self._ready.set()
        finally:
            if connection is not None:
                connection.close()
            self._release()

    def _consume(self, connection: sqlite3.Connection) -> None:
        batch: list[_Observation] = []
        deadline = time.monotonic() + _BATCH_SECONDS
        maintenance_deadline = time.monotonic() + _MAINTENANCE_SECONDS
        while True:
            if self._closing.is_set() and self._queue.empty():
                self._drained = self._commit(connection, batch, force=True)
                return
            try:
                value = self._queue.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty:
                maintenance_due = time.monotonic() >= maintenance_deadline
                self._commit(connection, batch, force=maintenance_due)
                if maintenance_due:
                    maintenance_deadline = time.monotonic() + _MAINTENANCE_SECONDS
                batch.clear()
                deadline = time.monotonic() + _BATCH_SECONDS
                continue
            if isinstance(value, _Barrier):
                value.success = self._commit(connection, batch, force=True)
                batch.clear()
                deadline = time.monotonic() + _BATCH_SECONDS
                value.done.set()
            else:
                batch.append(value)
                if len(batch) >= _BATCH_SIZE:
                    self._commit(connection, batch)
                    batch.clear()
                    deadline = time.monotonic() + _BATCH_SECONDS

    @staticmethod
    def _retire_oldest(connection: sqlite3.Connection, count: int) -> int:
        if count <= 0:
            return 0
        return connection.execute(
            "DELETE FROM events WHERE ingest_id IN (SELECT ingest_id FROM events ORDER BY ingest_id LIMIT ?)",
            (count,),
        ).rowcount

    def _reserve_space(self, connection: sqlite3.Connection, incoming: int, attempt: int) -> int:
        """Retire a bounded oldest prefix before inserts, including under byte pressure."""
        count = connection.execute("SELECT count(*) FROM events").fetchone()[0]
        pruned = self._retire_oldest(connection, max(0, count + incoming - MAX_EVENTS))
        remaining = count - pruned
        page_count = connection.execute("PRAGMA page_count").fetchone()[0]
        free_pages = connection.execute("PRAGMA freelist_count").fetchone()[0]
        capacity = MAX_DATABASE_BYTES // _PAGE_SIZE
        reserve = min(max(_MIN_RESERVE_PAGES, incoming * _INSERT_RESERVE_PAGES), max(_MIN_RESERVE_PAGES, capacity // 4))
        if attempt == _SPACE_RETRIES - 1:
            retirement = remaining
        elif attempt:
            retirement = max(1, remaining - remaining // (2**attempt))
        elif incoming and capacity - page_count + free_pages < reserve:
            retirement = max(_MIN_RETIREMENT_ROWS, incoming * 8, remaining // 8)
        else:
            retirement = 0
        return pruned + self._retire_oldest(connection, retirement)

    def _commit(
        self,
        connection: sqlite3.Connection,
        observations: list[_Observation],
        *,
        force: bool = False,
    ) -> bool:
        with self._state:
            dropped, failures = self._pending_drops, self._pending_failures
            self._pending_drops = self._pending_failures = 0
        if not observations and not dropped and not failures and not force:
            return True
        values = list(observations)
        if dropped or failures:
            gap = ReachTraceEvent(
                producer="host",
                name="capture_gap",
                status="unavailable",
                code="capture_unavailable" if failures else "queue_full",
                count=min(dropped, 2**31 - 1),
            )
            values.insert(0, _Observation(gap, trace_bytes(gap).decode("ascii").rstrip("\n"), _timestamp(_now())))
        for attempt in range(_SPACE_RETRIES):
            try:
                self._attest()
                duplicate_drops = self._append_transaction(connection, values, dropped, failures, attempt)
            except (OSError, ValueError, sqlite3.Error) as error:
                if connection.in_transaction:
                    with suppress(sqlite3.Error):
                        connection.execute("ROLLBACK")
                if (
                    isinstance(error, sqlite3.Error)
                    and getattr(error, "sqlite_errorcode", None) == sqlite3.SQLITE_FULL
                    and attempt < _SPACE_RETRIES - 1
                ):
                    continue
                with self._state:
                    self._pending_drops += dropped + len(observations)
                    self._pending_failures += failures + 1
                if not self._capture_failed:
                    write_diagnostic_line(b"reach_trace_capture_unavailable\n")
                    self._capture_failed = True
                return False
            else:
                with self._state:
                    self._persisted_drops += dropped + duplicate_drops
                    self._persisted_failures += failures
                if self._capture_failed:
                    write_diagnostic_line(b"reach_trace_capture_recovered\n")
                    self._capture_failed = False
                return True
        return False

    def _append_transaction(
        self,
        connection: sqlite3.Connection,
        values: list[_Observation],
        dropped: int,
        failures: int,
        attempt: int,
    ) -> int:
        connection.execute("BEGIN IMMEDIATE")
        metadata = connection.execute("SELECT * FROM archive_meta").fetchone()
        next_ingest = metadata["next_ingest"]
        heads = dict(self._producer_heads)
        for observation in values:
            event = observation.event
            if event.trace_seq and event.generation is not None and (event.producer, event.generation) not in heads:
                previous = connection.execute(
                    "SELECT trace_seq FROM events WHERE producer=? AND generation=? AND trace_seq>0 "
                    "ORDER BY ingest_id DESC LIMIT 1",
                    (event.producer, event.generation),
                ).fetchone()
                heads[event.producer, event.generation] = previous[0] if previous is not None else 0
        cutoff = _timestamp(_now() - timedelta(days=RETENTION_DAYS))
        pruned = connection.execute("DELETE FROM events WHERE received_at < ?", (cutoff,)).rowcount
        pruned += self._reserve_space(connection, len(values), attempt)
        gaps = 0
        duplicate_drops = 0
        for observation in values:
            event = observation.event
            existing = connection.execute(
                "SELECT record_json FROM events WHERE event_id=?", (event.event_id,)
            ).fetchone()
            if existing is not None:
                if existing[0] != observation.raw:
                    duplicate_drops += 1
                continue
            if event.trace_seq and event.generation is not None:
                key = event.producer, event.generation
                gaps += max(0, event.trace_seq - heads[key] - 1)
                heads[key] = max(heads[key], event.trace_seq)
            connection.execute(
                "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    next_ingest,
                    event.event_id,
                    observation.received_at,
                    event.producer,
                    event.generation,
                    event.run_id,
                    event.request_id,
                    event.call_id,
                    event.platform_event_id,
                    event.name,
                    event.status,
                    event.trace_seq,
                    int(event.status in _FAILURES),
                    observation.raw,
                ),
            )
            next_ingest += 1
        retained = connection.execute("SELECT count(*) FROM events").fetchone()[0]
        pruned += self._retire_oldest(connection, max(0, retained - MAX_EVENTS))
        connection.execute(
            "UPDATE archive_meta SET next_ingest=?, dropped_total=dropped_total+?, "
            "write_failures=write_failures+?, pruned_total=pruned_total+?, producer_gaps=producer_gaps+?",
            (next_ingest, dropped + duplicate_drops, failures, pruned, gaps),
        )
        connection.execute("COMMIT")
        while len(heads) > _MAX_LINK_IDENTITIES:
            heads.pop(next(iter(heads)))
        self._producer_heads = heads
        return duplicate_drops


def _time_filter(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            _refuse("trace_query_invalid")
        return _timestamp(parsed)
    except (ValueError, TypeError, AttributeError):
        code = "trace_query_invalid"
        raise TraceArchiveError(code) from None


def _query_identity(name: str, value: str | None) -> None:
    if value is None:
        return
    try:
        if name == "platform_event_id":
            if (
                not value.isascii()
                or not value.isdigit()
                or not 1 <= int(value) <= 2**64 - 1
                or len(value) > _MAX_PLATFORM_ID_CHARS
                or str(int(value)) != value
            ):
                _refuse("trace_query_invalid")
        elif str(UUID(value)) != value:
            _refuse("trace_query_invalid")
    except (ValueError, TypeError, AttributeError):
        code = "trace_query_invalid"
        raise TraceArchiveError(code) from None


def _related(  # noqa: C901, PLR0912 - bounded typed identity closure is explicit
    connection: sqlite3.Connection,
    identities: dict[str, str],
    generation: str | None,
    cutoff: str,
) -> tuple[str, list[str], bool]:
    """Follow recorded identity links; no timing, newest-row or pending-request guesses."""
    if not identities:
        return "1", [], False
    pools: dict[str, set[str]] = {
        name: {value} if (value := identities.get(name)) is not None else set() for name in _IDENTITIES
    }
    bounded = False
    predicates: list[str] = []
    arguments: list[str] = []
    for _ in range(3):
        predicates, arguments = [], []
        for name in ("run_id", "request_id", "call_id"):
            if pools[name]:
                predicates.append(f"{name} IN ({','.join('?' for _ in pools[name])})")
                arguments.extend(sorted(pools[name]))
        if "platform_event_id" in identities:
            predicates.append("platform_event_id=?")
            arguments.append(identities["platform_event_id"])
        where = "(" + " OR ".join(predicates) + ")"
        if generation is not None:
            where += " AND generation=?"
            arguments.append(generation)
        where += " AND received_at>=?"
        arguments.append(cutoff)
        rows = connection.execute(
            f"SELECT DISTINCT run_id,request_id,call_id,platform_event_id FROM events WHERE {where} LIMIT ?",  # noqa: S608 - only fixed predicates; values remain bound parameters
            [*arguments, _MAX_LINK_IDENTITIES + 1],
        ).fetchall()
        bounded |= len(rows) > _MAX_LINK_IDENTITIES
        changed = False
        for row in rows[:_MAX_LINK_IDENTITIES]:
            for name in _IDENTITIES:
                value = row[name]
                if value is not None and value not in pools[name]:
                    if len(pools[name]) >= _MAX_LINK_IDENTITIES:
                        bounded = True
                    else:
                        pools[name].add(value)
                        changed = True
        if not changed:
            break
    else:
        bounded = True
    predicates, arguments = [], []
    for name in ("run_id", "request_id", "call_id"):
        if pools[name]:
            predicates.append(f"{name} IN ({','.join('?' for _ in pools[name])})")
            arguments.extend(sorted(pools[name]))
    if pools["platform_event_id"]:
        predicate = f"platform_event_id IN ({','.join('?' for _ in pools['platform_event_id'])})"
        if "platform_event_id" not in identities:
            predicate += " AND run_id IS NULL AND request_id IS NULL AND call_id IS NULL"
        predicates.append("(" + predicate + ")")
        arguments.extend(sorted(pools["platform_event_id"]))
    return "(" + " OR ".join(predicates) + ")", arguments, bounded


def query_archive(  # noqa: C901, PLR0912, PLR0915 - one bounded read snapshot and explicit query dialect
    directory: Path,
    *,
    run_id: str | None = None,
    request_id: str | None = None,
    platform_event_id: str | None = None,
    generation: str | None = None,
    call_id: str | None = None,
    since: datetime | str | None = None,
    until: datetime | str | None = None,
    failures: bool = False,
    limit: int = 100,
    runs: bool = False,
    latest: bool = False,
) -> dict[str, Any]:
    """Read a bounded retained suffix through fixed predicates and explicit identity links."""
    identities = {
        name: value
        for name, value in {
            "run_id": run_id,
            "request_id": request_id,
            "platform_event_id": platform_event_id,
            "call_id": call_id,
        }.items()
        if value is not None
    }
    if type(limit) is not int or not 1 <= limit <= _MAX_QUERY_RECORDS or len(identities) > 1 or (latest and identities):
        _refuse("trace_query_invalid")
    for name, value in {**identities, "generation": generation}.items():
        _query_identity(name, value)
    lower, upper = _time_filter(since), _time_filter(until)
    cutoff = _timestamp(_now() - timedelta(days=RETENTION_DAYS))
    if lower is not None and upper is not None and lower > upper:
        _refuse("trace_query_invalid")
    root_fd = -1
    connection = None
    try:
        root_fd = _root(directory, create=False)
        connection = _connection(directory / DATABASE_NAME, readonly=True)
        deadline = time.monotonic() + 2
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        _validate_schema(connection)
        connection.execute("BEGIN")
        if latest:
            row = connection.execute(
                "SELECT run_id FROM events WHERE run_id IS NOT NULL AND (? IS NULL OR generation=?) "
                "AND received_at>=? ORDER BY ingest_id DESC LIMIT 1",
                (generation, generation, cutoff),
            ).fetchone()
            if row is not None:
                identities = {"run_id": row[0]}
        where, arguments, links_truncated = _related(connection, identities, generation, cutoff)
        if latest and not identities:
            where = "0"
        where += " AND received_at>=?"
        arguments.append(cutoff)
        for name, value, operator in (
            ("generation", generation, "="),
            ("received_at", lower, ">="),
            ("received_at", upper, "<="),
        ):
            if value is not None:
                where += f" AND {name}{operator}?"
                arguments.append(value)
        if failures:
            where += " AND failure=1"
        metadata = connection.execute("SELECT * FROM archive_meta").fetchone()
        bounds_sql = (
            "SELECT count(*) AS count, min(ingest_id) AS first_ingest_id, max(ingest_id) AS last_ingest_id, "
            "min(received_at) AS first_received_at, max(received_at) AS last_received_at FROM events"
        )
        physical_bounds = dict(connection.execute(bounds_sql).fetchone())
        bounds = dict(connection.execute(bounds_sql + " WHERE received_at>=?", (cutoff,)).fetchone())
        result: dict[str, Any] = {
            "schema_version": 1,
            "capture": "durable_best_effort",
            "completeness": "not_established",
            "retained_bounds": bounds,
            "truncated": False,
            "links_truncated": links_truncated,
            "physical_bounds": physical_bounds,
            "expired_retained_count": physical_bounds["count"] - bounds["count"],
            "retention_cutoff": cutoff,
            "pruned_total": metadata["pruned_total"],
            "dropped_total": metadata["dropped_total"],
            "write_failures": metadata["write_failures"],
            "producer_gaps": metadata["producer_gaps"],
            "retention": {"days": RETENTION_DAYS, "max_events": MAX_EVENTS, "max_database_bytes": MAX_DATABASE_BYTES},
            "selection": identities,
            "records": [],
        }
        if runs:
            rows = connection.execute(
                f"SELECT run_id,count(*) AS retained_events,min(ingest_id) AS first_ingest_id, "  # noqa: S608 - only fixed predicates; values remain bound parameters
                f"max(ingest_id) AS last_ingest_id FROM events WHERE ({where}) AND run_id IS NOT NULL "
                "GROUP BY run_id ORDER BY last_ingest_id DESC LIMIT ?",
                [*arguments, limit + 1],
            ).fetchall()
            result["truncated"] = len(rows) > limit
            result["runs"] = [dict(row) for row in rows[:limit]]
        else:
            rows = connection.execute(
                f"SELECT ingest_id,received_at,record_json FROM events WHERE {where} ORDER BY ingest_id DESC LIMIT ?",  # noqa: S608 - only fixed predicates; values remain bound parameters
                [*arguments, limit + 1],
            ).fetchall()
            result["truncated"] = len(rows) > limit
            for row in reversed(rows[:limit]):
                event = ReachTraceEvent.model_validate_json(row["record_json"])
                result["records"].append(
                    {
                        "ingest_id": row["ingest_id"],
                        "received_at": row["received_at"],
                        "event": json.loads(trace_bytes(event)),
                    }
                )
    except TraceArchiveError:
        raise
    except (OSError, ValueError, sqlite3.Error):
        code = "trace_archive_unavailable"
        raise TraceArchiveError(code) from None
    else:
        return result
    finally:
        if connection is not None:
            connection.close()
        if root_fd >= 0:
            os.close(root_fd)
