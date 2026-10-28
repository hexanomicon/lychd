"""Owner-authored local publication queue, independent of chat and native execution.

Only the host selects this private directory and the edge's exact destinations.
The queue never interprets commands, generates content, or retries HTTP effects.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
from collections.abc import Generator
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from lychd.interface.discord.rest import SUPPRESS_EMBEDS, DiscordRest, EffectResult

MAX_BACKLOG = 32
MAX_BODY = 1900
MAX_TTL = 3600
PRIVATE_FILE_MODE = 0o600
STAGING_LINK_COUNT = 2
_ENTRY = re.compile(r"([0-9a-f-]{36})\.json\Z")
_FINAL = re.compile(r"[0-9a-f-]{36}\.(?:json|body|receipt)\Z")
_PENDING = re.compile(r"\.pending-[0-9a-f]{32}\Z")


def _fail(code: str) -> None:
    raise ValueError(code)


def _identity(value: str) -> str:
    if not re.fullmatch(r"[1-9][0-9]{0,19}", value) or int(value) > 2**64 - 1:
        _fail("publication_identity")
    return value


def _private(fd: int, *, directory: bool = False) -> None:
    info = os.fstat(fd)
    valid = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if (
        not valid
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
        or (not directory and info.st_nlink != 1)
    ):
        _fail("publication_permissions")


def _read(fd: int, name: str, limit: int) -> bytes:
    child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        _private(child)
        raw = os.read(child, limit + 1)
        if len(raw) > limit:
            _fail("publication_size")
        return raw
    finally:
        os.close(child)


def _write(fd: int, name: str, raw: bytes) -> None:
    pending = f".pending-{uuid4().hex}"
    child = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        _private(child)
        position = 0
        while position < len(raw):
            count = os.write(child, raw[position:])
            if count == 0:
                _fail("publication_write")
            position += count
        os.fsync(child)
        os.link(pending, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
        os.unlink(pending, dir_fd=fd)
        os.fsync(fd)
    finally:
        os.close(child)
        with suppress(FileNotFoundError):
            os.unlink(pending, dir_fd=fd)


def _retire_pending_aliases(fd: int) -> None:
    """Finish only a crashed no-replace link whose complete final name already exists."""
    names = os.listdir(fd)
    finals = {
        (info.st_dev, info.st_ino)
        for name in names
        if _FINAL.fullmatch(name)
        for info in (os.stat(name, dir_fd=fd, follow_symlinks=False),)
    }
    changed = False
    for name in names:
        if not _PENDING.fullmatch(name):
            continue
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if (
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == PRIVATE_FILE_MODE
            and info.st_nlink == STAGING_LINK_COUNT
            and (info.st_dev, info.st_ino) in finals
        ):
            os.unlink(name, dir_fd=fd)
            changed = True
    if changed:
        os.fsync(fd)


def _retained_result(
    rest: DiscordRest, *, key: str, path: str, body: dict[str, Any], scope: str
) -> EffectResult | None:
    """Adopt exact prior transport evidence before considering a new contact."""
    key_digest = hashlib.sha256(key.encode()).hexdigest()
    previous = next((item for item in rest.journal.inspect() if item.effect_key_digest == key_digest), None)
    if previous is None:
        return None
    payload = json.dumps(
        {"method": "POST", "path": path, "body": body},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    if (
        previous.payload_digest != hashlib.sha256(payload.encode()).hexdigest()
        or previous.scope_digest != hashlib.sha256(scope.encode()).hexdigest()
        or previous.method != "POST"
        or previous.target != "channel_messages"
    ):
        return EffectResult(status="unknown", code="publication_binding")
    if previous.status in {"attempting", "unknown"}:
        return EffectResult(status="unknown", remote_id=previous.remote_id, code=previous.code or "effect_unresolved")
    return EffectResult(
        status="succeeded" if previous.status == "succeeded" else "rejected",
        remote_id=previous.remote_id,
        code=previous.code,
    )


class Publication(BaseModel):
    """Bounded local request; no authority is derived from its content."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)
    publication_id: str
    channel_id: str
    created_at: datetime
    expires_at: datetime
    body_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


def _new_contact_refusal(
    publication: Publication, allowed_channels: frozenset[str], effect_time: datetime
) -> EffectResult | None:
    """Check current authority only when no earlier transport attempt owns the outcome."""
    if (
        publication.channel_id not in allowed_channels
        or publication.created_at.tzinfo is None
        or publication.expires_at.tzinfo is None
        or publication.created_at > effect_time
        or not timedelta(0) < publication.expires_at - publication.created_at <= timedelta(hours=1)
    ):
        return EffectResult(status="rejected", code="publication_scope")
    if publication.expires_at <= effect_time:
        return EffectResult(status="rejected", code="publication_expired")
    return None


class PublicationQueue:
    """A single consumer of a no-follow, owner-only local queue."""

    def __init__(self, root: Path, *, allowed_channels: frozenset[str]) -> None:
        """Bind exact host-selected destinations without reading content."""
        if not root.is_absolute() or not allowed_channels:
            _fail("publication_configuration")
        self.root = root
        self.allowed_channels = frozenset(_identity(value) for value in allowed_channels)
        with self.lock():
            pass

    @contextmanager
    def lock(self) -> Generator[int]:
        with suppress(FileExistsError):
            self.root.mkdir(mode=0o700)
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        lock_fd = None
        try:
            _private(fd, directory=True)
            lock_fd = os.open(".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            _private(lock_fd)
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _retire_pending_aliases(fd)
            yield fd
        finally:
            if lock_fd is not None:
                os.close(lock_fd)
            os.close(fd)

    @staticmethod
    def _receipt(fd: int, publication: Publication, result: EffectResult) -> None:
        raw = json.dumps(
            {
                "publication_id": publication.publication_id,
                "body_digest": publication.body_digest,
                "status": result.status,
                "code": result.code,
                "remote_id": result.remote_id,
            },
            sort_keys=True,
        ).encode()
        _write(fd, f"{publication.publication_id}.receipt", raw)
        if result.status != "unknown":
            os.unlink(f"{publication.publication_id}.body", dir_fd=fd)
            os.unlink(f"{publication.publication_id}.json", dir_fd=fd)
            os.fsync(fd)

    async def process_once(self, rest: DiscordRest, *, now: datetime | None = None) -> int:
        """Consume at most 32 requests; persisted receipts fence every later scan."""
        processed = 0
        with self.lock() as fd:
            names = sorted(name for name in os.listdir(fd) if _ENTRY.fullmatch(name))  # noqa: PTH208
            if len(names) > MAX_BACKLOG:
                _fail("publication_backlog")
            for name in names:
                publication = Publication.model_validate_json(_read(fd, name, 2048))
                identifier = str(UUID(publication.publication_id))
                if name != f"{identifier}.json":
                    _fail("publication_identity")
                try:
                    _read(fd, f"{identifier}.receipt", 2048)
                except FileNotFoundError:
                    pass
                else:
                    continue
                raw = _read(fd, f"{identifier}.body", MAX_BODY * 4)
                text = raw.decode("utf-8")
                if not 1 <= len(text) <= MAX_BODY or hashlib.sha256(raw).hexdigest() != publication.body_digest:
                    _fail("publication_body")
                key = f"publication:{rest.application_id}:{identifier}"
                path = f"/channels/{publication.channel_id}/messages"
                body: dict[str, Any] = {
                    "content": text,
                    "flags": SUPPRESS_EMBEDS,
                    "allowed_mentions": {"parse": []},
                    "nonce": hashlib.sha256(key.encode()).hexdigest()[:25],
                    "enforce_nonce": True,
                }
                scope = f"{key}:{publication.channel_id}"
                result = _retained_result(rest, key=key, path=path, body=body, scope=scope)
                effect_time = now if now is not None else datetime.now(UTC)
                if result is None:
                    result = _new_contact_refusal(publication, self.allowed_channels, effect_time)
                if result is None:
                    result = await rest.write(
                        "POST",
                        path,
                        body,
                        effect_key=key,
                        scope=scope,
                    )
                    if result.code in {"effect_unresolved", "scope_unresolved"}:
                        result = EffectResult(status="unknown", code=result.code)
                self._receipt(fd, publication, result)
                processed += 1
        return processed


def _external_path(path: Path, *, allow_missing_leaf: bool = False) -> None:
    """Reject checkout-owned private material and symlinks on the host producer."""
    if not path.is_absolute() or ".." in path.parts or ".git" in path.parts:
        _fail("publication_external_path")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        if (current / ".git").exists() or (current / ".git").is_symlink():
            _fail("publication_external_path")
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            if allow_missing_leaf and current == path:
                return
            raise
        if stat.S_ISLNK(info.st_mode):
            _fail("publication_external_path")
    if current.is_dir() and ((current / ".git").exists() or (current / ".git").is_symlink()):
        _fail("publication_external_path")


def queue_publication(
    root: Path,
    *,
    body_file: Path,
    channel_id: str,
    publication_id: str,
    ttl_seconds: int = 3600,
) -> str:
    """Queue explicitly supplied owner content; the file body never enters argv."""
    identifier = str(UUID(publication_id))
    if identifier != publication_id or type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_TTL:
        _fail("publication_identity")
    _external_path(root, allow_missing_leaf=True)
    _external_path(body_file)
    body_fd = os.open(body_file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        _private(body_fd)
        raw = os.read(body_fd, MAX_BODY * 4 + 1)
    finally:
        os.close(body_fd)
    text = raw.decode("utf-8")
    if not 1 <= len(text) <= MAX_BODY:
        _fail("publication_body")
    now = datetime.now(UTC)
    publication = Publication(
        publication_id=identifier,
        channel_id=_identity(channel_id),
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
        body_digest=hashlib.sha256(raw).hexdigest(),
    )
    queue = PublicationQueue(root, allowed_channels=frozenset({channel_id}))
    with queue.lock() as fd:
        names = os.listdir(fd)  # noqa: PTH208 - inspect the pinned no-follow directory descriptor
        if any(name.startswith(f"{identifier}.") for name in names):
            _fail("publication_duplicate")
        if sum(bool(_ENTRY.fullmatch(name)) for name in names) >= MAX_BACKLOG:
            _fail("publication_backlog")
        _write(fd, f"{identifier}.body", raw)
        _write(fd, f"{identifier}.json", publication.model_dump_json().encode())
    return identifier


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    queued = sub.add_parser("queue")
    queued.add_argument("--queue-dir", type=Path, required=True)
    queued.add_argument("--body-file", type=Path, required=True)
    queued.add_argument("--channel-id", required=True)
    queued.add_argument("--publication-id", required=True)
    queued.add_argument("--ttl-seconds", type=int, default=3600)
    args = parser.parse_args(argv)
    try:
        identifier = queue_publication(
            args.queue_dir,
            body_file=args.body_file,
            channel_id=args.channel_id,
            publication_id=args.publication_id,
            ttl_seconds=args.ttl_seconds,
        )
    except (ValueError, OSError):
        parser.exit(1, "reach_publication:queue_rejected\n")
    sys.stdout.write(f"{identifier}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
