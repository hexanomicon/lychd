"""Finite Discord REST effects with a separate, content-free operator journal.

This journal records external attempts, not native Run/Graph execution. Unknown
attempts require operator reconciliation; neither reconstruction nor a new plan
authorizes replay. No response body, credential or message text is retained.
"""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import os
import re
import stat
import threading
import uuid
from collections.abc import AsyncGenerator, Generator, Iterable
from contextlib import asynccontextmanager, contextmanager, suppress
from http import HTTPStatus
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import quote

import httpx2
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lychd.compositions.reach.expressions import REACTIONS, Reaction, validate_gif_url
from lychd.interface.observation import ObservedOperation, OperationObserver
from lychd.lib.http import create_async_http_client, create_async_http_transport

_BASE = "https://discord.com/api/v10"
_MAX_RESPONSE = 2 * 1024 * 1024
_TIMEOUT = httpx2.Timeout(10.0, connect=5.0, pool=5.0)
_ID = re.compile(r"[1-9][0-9]{0,19}\Z")
_RECORD = re.compile(r"[a-f0-9]{64}\.json\Z")
_DIGEST = r"^[a-f0-9]{64}$"
_MAX_RECORD = 8192
_MAX_MESSAGE = 2000
_MAX_MESSAGE_PARTS = 6
_EPHEMERAL = 1 << 6
SUPPRESS_EMBEDS = 1 << 2
SUPPRESS_NOTIFICATIONS = 1 << 12
_BASELINE_ROLES = 2
type _Target = Literal[
    "guild_roles",
    "guild_channels",
    "channel",
    "channel_messages",
    "message_reaction",
    "interaction_original",
    "interaction_followup",
    "guild_member_role",
    "introduction",
]


class DiscordRestError(RuntimeError):
    """A fixed public code; provider exceptions and URLs never cross this edge."""

    def __init__(self, code: str) -> None:
        """Expose only the fixed classification supplied by this adapter."""
        self.code = code
        super().__init__(code)


class _Value(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)


class EffectResult(_Value):
    """Content-free result; unknown means the effect may have happened."""

    status: Literal["succeeded", "rejected", "unknown"]
    remote_id: str | None = Field(default=None, pattern=r"^[1-9][0-9]{0,19}$")
    code: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,63}$")


class EffectRecord(_Value):
    """Inspectable attempt metadata, with caller labels stored only as hashes."""

    effect_key_digest: str = Field(pattern=_DIGEST)
    payload_digest: str = Field(pattern=_DIGEST)
    scope_digest: str = Field(pattern=_DIGEST)
    method: Literal["POST", "PATCH", "PUT"]
    target: _Target
    status: Literal["attempting", "succeeded", "rejected", "unknown"]
    remote_id: str | None = Field(default=None, pattern=r"^[1-9][0-9]{0,19}$")
    code: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,63}$")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _object(value: object) -> dict[str, Any] | None:
    return cast("dict[str, Any]", value) if isinstance(value, dict) else None


def _id(value: object) -> str:
    if type(value) is not str or not _ID.fullmatch(value) or int(value) > 2**64 - 1:
        code = "invalid_identity"
        raise DiscordRestError(code)
    return value


def _owner() -> tuple[int, object | None]:
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    return threading.get_ident(), task


class EffectJournal:
    """Atomic/fsynced private attempt records under an explicit absolute directory.

    ``lock()`` is nonblocking and reentrant for the owning task and instance, so
    an administrator may hold it across an entire apply. Every HTTP write also
    claims its attempt under that same lock. Other tasks and processes refuse.
    """

    def __init__(self, root: Path) -> None:
        """Create or validate the explicit private attempt directory."""
        if not root.is_absolute():
            code = "journal_absolute_path_required"
            raise DiscordRestError(code)
        self.root = root
        self._depth = 0
        self._owner: tuple[int, object | None] | None = None
        self._root_fd: int | None = None
        self._session_root: int | None = None
        self._session_lock: int | None = None
        self._by_key: dict[str, EffectRecord] | None = None
        self._by_scope: dict[str, dict[str, EffectRecord]] = {}
        self._unresolved: dict[str, int] = {}
        self._poisoned = False
        try:
            root.mkdir(mode=0o700)
        except FileExistsError:
            pass
        except OSError:
            code = "journal_unavailable"
            raise DiscordRestError(code) from None
        with self.lock():
            pass

    @staticmethod
    def _private(fd: int, *, directory: bool) -> None:
        info = os.fstat(fd)
        mode = 0o700 if directory else 0o600
        valid_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
        if (
            not valid_type
            or stat.S_IMODE(info.st_mode) != mode
            or info.st_uid != os.getuid()
            or (not directory and info.st_nlink != 1)
        ):
            code = "journal_unsafe_permissions"
            raise DiscordRestError(code)

    def _acquire_root(self) -> tuple[int, int]:
        root_fd = lock_fd = None
        try:
            root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self._private(root_fd, directory=True)
            lock_fd = os.open(".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=root_fd)
            self._private(lock_fd, directory=False)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                code = "journal_busy"
                raise DiscordRestError(code) from None
        except OSError:
            if lock_fd is not None:
                os.close(lock_fd)
            if root_fd is not None:
                os.close(root_fd)
            code = "journal_unavailable"
            raise DiscordRestError(code) from None
        except BaseException:
            if lock_fd is not None:
                os.close(lock_fd)
            if root_fd is not None:
                os.close(root_fd)
            raise
        return root_fd, lock_fd

    @contextmanager
    def session(self) -> Generator[None]:
        """Lease one writer generation; reload receipts before creating a volatile index."""
        if self._session_root is not None or self._depth:
            code = "journal_busy"
            raise DiscordRestError(code)
        self._session_root, self._session_lock = self._acquire_root()
        self._poisoned = False
        try:
            with self.lock():
                records = self._inspect_locked()
                self._by_key = {}
                for record in records:
                    self._index_record(record)
            yield
        finally:
            self.close()

    def close(self) -> None:
        """Release a retired generation; an active transaction keeps its lease fenced."""
        if self._depth:
            self._poisoned = True
            code = "journal_busy"
            raise DiscordRestError(code)
        if self._session_lock is not None:
            os.close(self._session_lock)
        if self._session_root is not None:
            os.close(self._session_root)
        self._session_lock = self._session_root = None
        self._by_key = None
        self._by_scope.clear()
        self._unresolved.clear()
        self._poisoned = False

    @contextmanager
    def lock(self) -> Generator[None]:
        """Own a short transaction independently of the generation's process lease."""
        owner = _owner()
        if self._poisoned:
            code = "journal_unavailable"
            raise DiscordRestError(code)
        if self._depth:
            if self._owner != owner:
                code = "journal_busy"
                raise DiscordRestError(code)
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return
        root_fd, lock_fd = (self._session_root, None) if self._session_root is not None else self._acquire_root()
        try:
            self._private(root_fd, directory=True)
            self._owner, self._root_fd, self._depth = owner, root_fd, 1
            yield
        except OSError:
            code = "journal_unavailable"
            raise DiscordRestError(code) from None
        finally:
            self._owner, self._root_fd, self._depth = None, None, 0
            if lock_fd is not None:
                os.close(lock_fd)
                os.close(root_fd)

    def _fd(self) -> int:
        if self._poisoned:
            code = "journal_unavailable"
            raise DiscordRestError(code)
        if self._root_fd is None or self._owner != _owner():
            code = "journal_lock_required"
            raise DiscordRestError(code)
        return self._root_fd

    def inspect(self) -> tuple[EffectRecord, ...]:
        """Read metadata without resetting, acknowledging or replaying attempts."""
        with self.lock():
            return (
                tuple(self._by_key[key] for key in sorted(self._by_key))
                if self._by_key is not None
                else self._inspect_locked()
            )

    def lookup(self, effect_key: str) -> EffectRecord | None:
        with self.lock():
            key = _digest(effect_key)
            if self._by_key is not None:
                return self._by_key.get(key)
            return next((record for record in self._inspect_locked() if record.effect_key_digest == key), None)

    def scope_records(self, scope: str) -> tuple[EffectRecord, ...]:
        with self.lock():
            key = _digest(scope)
            if self._by_key is not None:
                return tuple(self._by_scope.get(key, {}).values())
            return tuple(record for record in self._inspect_locked() if record.scope_digest == key)

    def scope_unresolved(self, scope: str) -> bool:
        with self.lock():
            if self._by_key is not None:
                return bool(self._unresolved.get(_digest(scope)))
            return any(record.status in {"attempting", "unknown"} for record in self.scope_records(scope))

    def _index_record(self, record: EffectRecord) -> None:
        if self._by_key is None:
            return
        previous = self._by_key.get(record.effect_key_digest)
        if previous is not None:
            self._by_scope[previous.scope_digest].pop(previous.effect_key_digest)
            if previous.status in {"attempting", "unknown"}:
                self._unresolved[previous.scope_digest] -= 1
        self._by_key[record.effect_key_digest] = record
        self._by_scope.setdefault(record.scope_digest, {})[record.effect_key_digest] = record
        if record.status in {"attempting", "unknown"}:
            self._unresolved[record.scope_digest] = self._unresolved.get(record.scope_digest, 0) + 1

    def _inspect_locked(self) -> tuple[EffectRecord, ...]:
        root_fd = self._fd()
        records: list[EffectRecord] = []
        # A fresh open file description gives every scan its own directory cursor,
        # including repeated reentrant inspection under the outer apply lock.
        scan_fd = os.open(".", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        try:
            names = sorted(os.listdir(scan_fd))  # noqa: PTH208 - scan the pinned no-follow directory descriptor
        finally:
            os.close(scan_fd)
        for name in names:
            if name == ".lock" or re.fullmatch(r"\.pending-[a-f0-9]{32}", name):
                continue
            if not _RECORD.fullmatch(name):
                code = "journal_invalid_record"
                raise DiscordRestError(code)
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=root_fd)
            try:
                self._private(fd, directory=False)
                raw = os.read(fd, _MAX_RECORD + 1)
            finally:
                os.close(fd)
            if len(raw) > _MAX_RECORD:
                code = "journal_invalid_record"
                raise DiscordRestError(code)
            try:
                record = EffectRecord.model_validate_json(raw)
            except ValidationError:
                code = "journal_invalid_record"
                raise DiscordRestError(code) from None
            if name != f"{record.effect_key_digest}.json":
                code = "journal_invalid_record"
                raise DiscordRestError(code)
            records.append(record)
        return tuple(records)

    def _save(self, record: EffectRecord) -> None:
        try:
            self._save_record(record)
            self._index_record(record)
        except BaseException:
            if self._session_root is not None:
                self._poisoned = True
            raise

    def _save_record(self, record: EffectRecord) -> None:
        root_fd = self._fd()
        temporary = f".pending-{uuid.uuid4().hex}"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root_fd)
        try:
            self._private(fd, directory=False)
            raw = record.model_dump_json().encode("utf-8")
            position = 0
            while position < len(raw):
                written = os.write(fd, raw[position:])
                if written == 0:
                    code = "journal_unavailable"
                    raise DiscordRestError(code)
                position += written
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.replace(temporary, f"{record.effect_key_digest}.json", src_dir_fd=root_fd, dst_dir_fd=root_fd)
            os.fsync(root_fd)
        finally:
            with suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=root_fd)

    def claim(
        self,
        *,
        effect_key: str,
        payload_digest: str,
        scope: str,
        method: Literal["POST", "PATCH", "PUT"],
        target: _Target,
    ) -> EffectRecord | EffectResult:
        """Claim while the caller holds ``lock()``, before making any request."""
        self._fd()
        if not effect_key or not scope:
            return EffectResult(status="rejected", code="invalid_effect_identity")
        key_hash, scope_hash = _digest(effect_key), _digest(scope)
        # A session's index is valid only while its exclusive OS lease remains held.
        records = self._inspect_locked() if self._by_key is None else ()
        previous = (
            self._by_key.get(key_hash)
            if self._by_key is not None
            else next((record for record in records if record.effect_key_digest == key_hash), None)
        )
        if previous is not None:
            if previous.payload_digest != payload_digest or previous.scope_digest != scope_hash:
                return EffectResult(status="rejected", code="effect_payload_changed")
            if previous.status in {"attempting", "unknown"}:
                return EffectResult(status="rejected", code="effect_unresolved")
            status = "succeeded" if previous.status == "succeeded" else "rejected"
            return EffectResult(status=status, remote_id=previous.remote_id, code=previous.code)
        unresolved = (
            bool(self._unresolved.get(scope_hash))
            if self._by_key is not None
            else any(
                record.scope_digest == scope_hash and record.status in {"attempting", "unknown"} for record in records
            )
        )
        if unresolved:
            return EffectResult(status="rejected", code="scope_unresolved")
        record = EffectRecord(
            effect_key_digest=key_hash,
            payload_digest=payload_digest,
            scope_digest=scope_hash,
            method=method,
            target=target,
            status="attempting",
        )
        self._save(record)
        return record

    def settle(self, record: EffectRecord, result: EffectResult) -> None:
        self._save(
            record.model_copy(update={"status": result.status, "remote_id": result.remote_id, "code": result.code})
        )

    def mark_unknown(self, effect_key: str, *, code: str) -> None:
        """Fence an accepted write when subsequent resource reconciliation fails."""
        if code not in {
            "create_reconciliation_mismatch",
            "create_reconciliation_failed",
            "patch_reconciliation_mismatch",
            "patch_reconciliation_failed",
        }:
            code = "invalid_reconciliation_code"
            raise DiscordRestError(code)
        with self.lock():
            record = self.lookup(effect_key)
            if record is None:
                code = "journal_effect_missing"
                raise DiscordRestError(code)
            self.settle(record, EffectResult(status="unknown", remote_id=record.remote_id, code=code))


@contextmanager
def _observe_request(observed: ObservedOperation | None) -> Generator[None]:
    if observed is None:
        yield
        return
    observed.start()
    try:
        yield
    except asyncio.CancelledError:
        observed.finish("cancelled", error="cancelled")
        raise
    except httpx2.HTTPError as error:
        observed.finish("failed", error="timeout" if isinstance(error, httpx2.TimeoutException) else "transport")
        raise
    except BaseException:
        observed.finish("failed", error="protocol")
        raise
    else:
        observed.finish("succeeded")


async def _response_value(response: httpx2.Response) -> tuple[int, Any]:
    """Read one bounded response while preserving non-success HTTP status."""
    if not HTTPStatus.OK <= response.status_code < HTTPStatus.MULTIPLE_CHOICES:
        return response.status_code, None
    raw = bytearray()
    async for chunk in response.aiter_bytes(chunk_size=65536):
        if len(raw) + len(chunk) > _MAX_RESPONSE:
            code = "response_too_large"
            raise DiscordRestError(code)
        raw.extend(chunk)
    if response.status_code == HTTPStatus.NO_CONTENT and not raw:
        return response.status_code, None
    try:
        return response.status_code, json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        code = "invalid_response"
        raise DiscordRestError(code) from None


class DiscordRest:
    """Bot-authenticated, fixed-origin REST with explicit identity/resource binding."""

    def __init__(
        self,
        *,
        token: str,
        application_id: str,
        bot_user_id: str,
        guild_id: str,
        journal: EffectJournal,
        client: httpx2.AsyncClient | None = None,
        observer: OperationObserver | None = None,
    ) -> None:
        """Bind the credential to explicit expected identities and one guild."""
        if type(token) is not str or not re.fullmatch(r"[A-Za-z0-9._-]{1,4096}", token):
            code = "invalid_token"
            raise DiscordRestError(code)
        self.application_id = _id(application_id)
        self.bot_user_id = _id(bot_user_id)
        self.guild_id = _id(guild_id)
        self.journal = journal
        self._token = token
        self.observer = observer
        self._verified = False
        self._channels: set[str] = set()
        self._direct_channels: dict[str, str] = {}
        self._member_roles: frozenset[str] = frozenset()
        self._introduction_channel: str | None = None
        self._effects_lock = asyncio.Lock()
        self._owns_client = client is None
        self._client = client or create_async_http_client(
            transport=create_async_http_transport(),
            timeout=_TIMEOUT,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @asynccontextmanager
    async def _effect(self) -> AsyncGenerator[None]:
        """Queue local writers before claiming the nonblocking cross-process journal lock."""
        async with self._effects_lock:
            with self.journal.lock():
                yield

    def bind_channels(self, ids: Iterable[str]) -> None:
        """Bind channel IDs observed in the authenticated guild snapshot."""
        channels = {_id(value) for value in ids}
        self._channels.update(channels)

    async def bind_direct_channel(self, channel_id: str, subject_id: str) -> None:
        """Verify one observed private recipient; authorize replies and reactions."""
        channel_id, subject_id = _id(channel_id), _id(subject_id)
        if not self._verified or channel_id in self._channels:
            code = "direct_channel_binding"
            raise DiscordRestError(code)
        status, data = await self._request("GET", f"/channels/{channel_id}")
        channel = _object(data)
        raw_recipients = channel.get("recipients") if channel else None
        recipients = cast("list[Any]", raw_recipients) if isinstance(raw_recipients, list) else None
        recipient = _object(recipients[0]) if recipients is not None and len(recipients) == 1 else None
        if (
            status != HTTPStatus.OK
            or channel is None
            or channel.get("id") != channel_id
            or channel.get("type") != 1
            or not isinstance(recipients, list)
            or len(recipients) != 1
            or recipient is None
            or recipient.get("id") != subject_id
            or self._direct_channels.get(channel_id, subject_id) != subject_id
        ):
            code = "direct_channel_binding"
            raise DiscordRestError(code)
        self._direct_channels[channel_id] = subject_id

    def bind_member_roles(self, ids: Iterable[str]) -> None:
        """Bind exactly two operator-validated baseline roles, never everyone."""
        roles = frozenset(_id(value) for value in ids)
        if (
            len(roles) != _BASELINE_ROLES
            or self.guild_id in roles
            or (self._member_roles and roles != self._member_roles)
        ):
            code = "member_role_binding"
            raise DiscordRestError(code)
        self._member_roles = roles

    def bind_introduction_channel(self, channel_id: str) -> None:
        """Freeze the one verified public onboarding destination."""
        channel_id = _id(channel_id)
        if channel_id not in self._channels or self._introduction_channel not in {None, channel_id}:
            code = "introduction_channel_binding"
            raise DiscordRestError(code)
        self._introduction_channel = channel_id

    async def get_message(self, channel_id: str, message_id: str) -> dict[str, Any]:
        """Read one exact message only inside an already observed guild channel."""
        channel_id, message_id = _id(channel_id), _id(message_id)
        if channel_id not in self._channels:
            code = "route_not_allowed"
            raise DiscordRestError(code)
        status, data = await self._request("GET", f"/channels/{channel_id}/messages/{message_id}")
        resource = _object(data)
        if status != HTTPStatus.OK:
            code = f"http_{status}"
            raise DiscordRestError(code)
        if resource is None or resource.get("id") != message_id or resource.get("channel_id") != channel_id:
            code = "message_binding"
            raise DiscordRestError(code)
        return resource

    async def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        observation: ObservedOperation | None = None,
    ) -> tuple[int, Any]:
        """Observe only a real transport entry; retain status even if response decoding fails."""
        observed = observation or (self.observer.operation(f"http.{method.lower()}") if self.observer else None)
        headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
        if not path.startswith("/webhooks/"):
            headers["Authorization"] = f"Bot {self._token}"
        try:
            with _observe_request(observed):
                async with self._client.stream(
                    method,
                    _BASE + path,
                    json=body,
                    headers=headers,
                    follow_redirects=False,
                    timeout=_TIMEOUT,
                ) as response:
                    if observed is not None:
                        observed.http_status = response.status_code
                    return await _response_value(response)
        except httpx2.HTTPError:
            code = "network_error"
            raise DiscordRestError(code) from None

    async def verify_identity(self) -> None:
        """Independently verify the bot user and owning application before writes."""
        self._verified = False
        user_status, user_data = await self._request("GET", "/users/@me")
        app_status, application_data = await self._request("GET", "/oauth2/applications/@me")
        user, application = _object(user_data), _object(application_data)
        if (
            user_status != HTTPStatus.OK
            or app_status != HTTPStatus.OK
            or user is None
            or user.get("id") != self.bot_user_id
            or user.get("bot") is not True
            or application is None
            or application.get("id") != self.application_id
        ):
            code = "identity_mismatch"
            raise DiscordRestError(code)
        self._verified = True

    def _route(self, method: str, path: str) -> _Target | Literal["guild"]:
        if type(path) is not str or not path.startswith("/") or any(c in path for c in ("?", "#", "%", "\\")):
            code = "route_not_allowed"
            raise DiscordRestError(code)
        guild = f"/guilds/{self.guild_id}"
        if method == "GET" and path in {guild, f"{guild}/members/{self.bot_user_id}"}:
            return "guild"
        if path == f"{guild}/roles" and method in {"GET", "POST"}:
            return "guild_roles"
        if path == f"{guild}/channels" and method in {"GET", "POST"}:
            return "guild_channels"
        channel = re.fullmatch(r"/channels/([1-9][0-9]{0,19})(/messages)?", path)
        if channel and channel[1] in self._direct_channels and channel[2] == "/messages" and method == "POST":
            return "channel_messages"
        if channel and channel[1] in self._channels:
            if channel[2] is None and method in {"GET", "PATCH"}:
                return "channel"
            if channel[2] == "/messages" and method == "POST":
                return "channel_messages"
        code = "route_not_allowed"
        raise DiscordRestError(code)

    async def get(self, path: str) -> Any:
        self._route("GET", path)
        status, data = await self._request("GET", path)
        if status != HTTPStatus.OK:
            code = f"http_{status}"
            raise DiscordRestError(code)
        if path == f"/guilds/{self.guild_id}/channels":
            if not isinstance(data, list):
                code = "invalid_response"
                raise DiscordRestError(code)
            channels = cast("list[Any]", data)
            ids: list[str] = []
            for item in channels:
                channel = _object(item)
                if channel is None or channel.get("guild_id", self.guild_id) != self.guild_id:
                    code = "invalid_response"
                    raise DiscordRestError(code)
                ids.append(_id(channel.get("id")))
            self.bind_channels(ids)
            return channels
        return data

    async def write(
        self,
        method: Literal["POST", "PATCH"],
        path: str,
        body: dict[str, Any],
        *,
        effect_key: str,
        scope: str,
    ) -> EffectResult:
        target = self._route(method, path)
        if target == "guild" or type(body) is not dict:
            return EffectResult(status="rejected", code="invalid_write")
        if target == "guild_roles":
            permissions = body.get("permissions", "0")
            if (
                type(permissions) is not str
                or not re.fullmatch(r"[0-9]{1,20}", permissions)
                or int(permissions) > 2**64 - 1
                or int(permissions) & 8
            ):
                return EffectResult(status="rejected", code="unsafe_permissions")
        async with self._effect():
            return await self._write(method, path, body, effect_key=effect_key, scope=scope, target=target)

    async def _write(
        self,
        method: Literal["POST", "PATCH", "PUT"],
        path: str,
        body: dict[str, Any],
        *,
        effect_key: str,
        scope: str,
        target: _Target,
        empty_success_id: str | None = None,
    ) -> EffectResult:
        if not self._verified:
            return EffectResult(status="rejected", code="identity_not_verified")
        if method not in {"POST", "PATCH", "PUT"} or type(body) is not dict:
            return EffectResult(status="rejected", code="invalid_write")
        try:
            payload = json.dumps(
                {"method": method, "path": path, "body": body},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            frozen_body = json.loads(payload)["body"]
        except (ValueError, TypeError, RecursionError):
            return EffectResult(status="rejected", code="invalid_payload")
        with self.journal.lock():
            claim = self.journal.claim(
                effect_key=effect_key,
                payload_digest=_digest(payload),
                scope=scope,
                method=method,
                target=target,
            )
            if isinstance(claim, EffectResult):
                return claim
            observed = self.observer.operation(f"discord.{target}") if self.observer else None
            try:
                status, data = await self._request(method, path, frozen_body, observation=observed)
            except DiscordRestError as error:
                result = EffectResult(status="unknown", code=error.code)
            except asyncio.CancelledError:
                self.journal.settle(claim, EffectResult(status="unknown", code="cancelled"))
                if observed is not None:
                    observed.settle("unknown")
                raise
            else:
                result = (
                    EffectResult(status="succeeded", remote_id=empty_success_id)
                    if status == HTTPStatus.NO_CONTENT and method == "PUT" and empty_success_id is not None
                    else self._result(status, data)
                )
            self.journal.settle(claim, result)
            if observed is not None:
                observed.settle("failed" if result.status == "rejected" else result.status)
            return result

    async def ensure_member_role(self, user_id: str, role_id: str, *, event_id: str) -> EffectResult:
        """Add one admitted baseline role without replacing existing memberships."""
        user_id, role_id, event_id = _id(user_id), _id(role_id), _id(event_id)
        if role_id not in self._member_roles:
            return EffectResult(status="rejected", code="member_role_binding")
        scope = f"member-role:{self.application_id}:{self.guild_id}:{user_id}:{role_id}"
        key = f"{scope}:{event_id}"
        if not self._verified:
            return EffectResult(status="rejected", code="identity_not_verified")
        async with self._effect():
            retained = self.journal.lookup(key) is not None or self.journal.scope_unresolved(scope)
            if not retained:
                try:
                    roles = await self.get(f"/guilds/{self.guild_id}/roles")
                except DiscordRestError:
                    return EffectResult(status="rejected", code="member_role_authority")
                rows = cast("list[object]", roles) if isinstance(roles, list) else []
                role = next(
                    (row for raw in rows if (row := _object(raw)) is not None and row.get("id") == role_id), None
                )
                if role is None or role.get("permissions") != "0" or role.get("managed", False):
                    return EffectResult(status="rejected", code="member_role_authority")
            return await self._write(
                "PUT",
                f"/guilds/{self.guild_id}/members/{user_id}/roles/{role_id}",
                {},
                effect_key=key,
                scope=scope,
                target="guild_member_role",
                empty_success_id=user_id,
            )

    async def publish_introduction(  # noqa: PLR0911 - each return fences a distinct external effect precondition
        self, channel_id: str, text: str, *, subject_id: str, event_id: str
    ) -> EffectResult:
        """Create one member-bound introduction or edit its retained bot-owned message."""
        channel_id, subject_id, event_id = _id(channel_id), _id(subject_id), _id(event_id)
        if channel_id != self._introduction_channel:
            return EffectResult(status="rejected", code="introduction_channel_binding")
        if type(text) is not str or not 1 <= len(text) <= _MAX_MESSAGE:
            return EffectResult(status="rejected", code="invalid_message")
        key = f"introduction:{self.application_id}:{self.guild_id}:{channel_id}:{subject_id}"
        async with self._effect():
            if self.journal.scope_unresolved(key):
                return EffectResult(status="rejected", code="introduction_unresolved")
            previous = next(
                (
                    r
                    for r in self.journal.scope_records(key)
                    if r.target == "introduction" and r.method == "POST" and r.status == "succeeded"
                ),
                None,
            )
            body: dict[str, Any] = {"content": text, "flags": SUPPRESS_EMBEDS, "allowed_mentions": {"parse": []}}
            if previous is None:
                body.update(nonce=_digest(key)[:25], enforce_nonce=True)
                return await self._write(
                    "POST",
                    f"/channels/{channel_id}/messages",
                    body,
                    effect_key=f"{key}:event:{event_id}",
                    scope=key,
                    target="introduction",
                )
            if previous.remote_id is None or previous.target != "introduction" or previous.method != "POST":
                return EffectResult(status="unknown", code="introduction_binding")
            try:
                resource = await self.get_message(channel_id, previous.remote_id)
            except DiscordRestError:
                return EffectResult(status="rejected", code="introduction_original_unavailable")
            author = _object(resource.get("author"))
            if (
                author is None
                or author.get("id") != self.bot_user_id
                or not author.get("bot")
                or resource.get("webhook_id")
            ):
                return EffectResult(status="rejected", code="introduction_author")
            body["flags"] = int(resource.get("flags", 0)) | SUPPRESS_EMBEDS
            if resource.get("content") == text and int(resource.get("flags", 0)) & SUPPRESS_EMBEDS:
                return EffectResult(status="succeeded", remote_id=previous.remote_id)
            return await self._write(
                "PATCH",
                f"/channels/{channel_id}/messages/{previous.remote_id}",
                body,
                effect_key=f"{key}:event:{event_id}",
                scope=key,
                target="introduction",
            )

    @staticmethod
    def _result(status: int, data: Any) -> EffectResult:
        resource = _object(data)
        if HTTPStatus.BAD_REQUEST <= status < HTTPStatus.INTERNAL_SERVER_ERROR:
            return EffectResult(status="rejected", code=f"http_{status}")
        if (
            HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES
            and resource is not None
            and isinstance(resource.get("id"), str)
        ):
            try:
                return EffectResult(status="succeeded", remote_id=_id(resource["id"]))
            except DiscordRestError:
                return EffectResult(status="unknown", code="invalid_response")
        return EffectResult(
            status="unknown", code="invalid_response" if status < HTTPStatus.MULTIPLE_CHOICES else f"http_{status}"
        )

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: Reaction,
        *,
        event_id: str,
        phase: Literal["seen", "reply"] = "reply",
    ) -> EffectResult:
        """React once to the admitted incoming event in an already bound channel."""
        try:
            channel_id, message_id, event_id = _id(channel_id), _id(message_id), _id(event_id)
        except DiscordRestError as error:
            return EffectResult(status="rejected", code=error.code)
        if type(emoji) is not str or emoji not in REACTIONS:
            return EffectResult(status="rejected", code="invalid_reaction")
        if type(phase) is not str or phase not in {"seen", "reply"}:
            return EffectResult(status="rejected", code="invalid_reaction_phase")
        if message_id != event_id:
            return EffectResult(status="rejected", code="reaction_message_binding")
        if channel_id not in self._channels and channel_id not in self._direct_channels:
            return EffectResult(status="rejected", code="reaction_channel_binding")
        key = f"reaction:{self.application_id}:{event_id}:{phase}"
        scope = f"reaction:{self.application_id}:{channel_id}:{event_id}:{phase}"
        async with self._effect():
            return await self._write(
                "PUT",
                f"/channels/{channel_id}/messages/{message_id}/reactions/{quote(emoji, safe='')}/@me",
                {},
                effect_key=key,
                scope=scope,
                target="message_reaction",
                empty_success_id=message_id,
            )

    async def send_gif(self, channel_id: str, url: str, *, event_id: str, reply_to: str) -> EffectResult:
        """Send one exact validated GIF URL as a silent reply with previews enabled."""
        try:
            channel_id, event_id, reply_to = _id(channel_id), _id(event_id), _id(reply_to)
        except DiscordRestError as error:
            return EffectResult(status="rejected", code=error.code)
        if reply_to != event_id:
            return EffectResult(status="rejected", code="gif_reply_binding")
        try:
            url = validate_gif_url(url)
        except ValueError:
            return EffectResult(status="rejected", code="invalid_gif_url")
        key = f"gif:{self.application_id}:{event_id}"
        scope = f"gif:{self.application_id}:{channel_id}:{event_id}"
        body: dict[str, Any] = {
            "content": url,
            "flags": SUPPRESS_NOTIFICATIONS,
            "allowed_mentions": {"parse": [], "replied_user": False},
            "nonce": _digest(scope)[:25],
            "enforce_nonce": True,
            "message_reference": {
                "message_id": reply_to,
                "channel_id": channel_id,
                "fail_if_not_exists": False,
            },
        }
        try:
            return await self.write("POST", f"/channels/{channel_id}/messages", body, effect_key=key, scope=scope)
        except DiscordRestError as error:
            if error.code != "route_not_allowed":
                raise
            return EffectResult(status="rejected", code=error.code)

    async def send_message(
        self,
        channel_id: str,
        text: str,
        *,
        event_id: str,
        reply_to: str | None = None,
        phase: Literal["ack", "plan", "final"] | None = None,
        part: int = 0,
        silent: bool = False,
    ) -> EffectResult:
        """Send text with clickable links, suppressed previews and no mentions."""
        channel_id, event_id = _id(channel_id), _id(event_id)
        if phase not in {None, "ack", "plan", "final"} or type(part) is not int or not 0 <= part < _MAX_MESSAGE_PARTS:
            return EffectResult(status="rejected", code="invalid_message_phase")
        if (phase != "final" and part != 0) or type(silent) is not bool:
            return EffectResult(status="rejected", code="invalid_message_phase")
        if type(text) is not str or not 1 <= len(text) <= _MAX_MESSAGE:
            return EffectResult(status="rejected", code="invalid_message")
        suffix = f":{phase}:{part}" if phase is not None else ""
        nonce = _digest(f"{self.application_id}:{channel_id}:{event_id}{suffix}")[:25]
        body: dict[str, Any] = {
            "content": text,
            "flags": SUPPRESS_EMBEDS | (SUPPRESS_NOTIFICATIONS if silent else 0),
            "allowed_mentions": {"parse": []},
            "nonce": nonce,
            "enforce_nonce": True,
        }
        if reply_to is not None:
            body["allowed_mentions"]["replied_user"] = False
            body["message_reference"] = {
                "message_id": _id(reply_to),
                "channel_id": channel_id,
                "fail_if_not_exists": False,
            }
        return await self.write(
            "POST",
            f"/channels/{channel_id}/messages",
            body,
            effect_key=f"message:{self.application_id}:{event_id}{suffix}",
            scope=f"message:{self.application_id}:{channel_id}:{event_id}{suffix}",
        )

    async def edit_interaction_original(self, interaction_token: str, text: str, *, event_id: str) -> EffectResult:
        """Complete the deferred response without generating link previews."""
        event_id = _id(event_id)
        if type(interaction_token) is not str or not re.fullmatch(r"[A-Za-z0-9._-]{1,2048}", interaction_token):
            return EffectResult(status="rejected", code="invalid_interaction_token")
        if type(text) is not str or not 1 <= len(text) <= _MAX_MESSAGE:
            return EffectResult(status="rejected", code="invalid_message")
        async with self._effect():
            return await self._write(
                "PATCH",
                f"/webhooks/{self.application_id}/{interaction_token}/messages/@original",
                {"content": text, "flags": SUPPRESS_EMBEDS, "allowed_mentions": {"parse": []}},
                effect_key=f"interaction:{self.application_id}:{event_id}",
                scope=f"interaction:{self.application_id}:{event_id}",
                target="interaction_original",
            )

    async def send_interaction_followup(
        self,
        interaction_token: str,
        text: str,
        *,
        event_id: str,
        part: int,
    ) -> EffectResult:
        """Send a private continuation of this exact deferred interaction."""
        event_id = _id(event_id)
        if type(interaction_token) is not str or not re.fullmatch(r"[A-Za-z0-9._-]{1,2048}", interaction_token):
            return EffectResult(status="rejected", code="invalid_interaction_token")
        if (
            type(part) is not int
            or not 1 <= part < _MAX_MESSAGE_PARTS
            or type(text) is not str
            or not 1 <= len(text) <= _MAX_MESSAGE
        ):
            return EffectResult(status="rejected", code="invalid_message")
        async with self._effect():
            return await self._write(
                "POST",
                f"/webhooks/{self.application_id}/{interaction_token}",
                {"content": text, "flags": SUPPRESS_EMBEDS | _EPHEMERAL, "allowed_mentions": {"parse": []}},
                effect_key=f"interaction:{self.application_id}:{event_id}:part:{part}",
                scope=f"interaction:{self.application_id}:{event_id}:part:{part}",
                target="interaction_followup",
            )
