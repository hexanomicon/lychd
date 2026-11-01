"""One OCI-only operator catalogue read with durable, non-replayable admission.

This worker owns a separate standing public-catalogue profile. It does not mint
native Bridge authentication, consent, Runs or Scout store claims. Network and
extraction mechanisms are reused under its own synchronous gate and journal.
"""

from __future__ import annotations

import argparse
import asyncio
import errno
import fcntl
import json
import logging
import os
import re
import stat
import sys
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, Self, cast
from uuid import uuid4

from lychd.compositions.reach.operator_wire import strict_json
from lychd.compositions.reach.research_wire import (
    ResearchJob,
    ResearchRuntimeProfile,
    ResearchSource,
    SourceReadResult,
)
from lychd.domain.scout.destination import (
    DestinationCandidate,
    classify_destination_addresses,
    preflight_destination,
)
from lychd.domain.scout.extraction import ExtractedText, ExtractionCode, ExtractionError
from lychd.domain.scout.transport import FetchCode, FetchError, NetworkHandoff, NetworkTarget
from lychd.system.services.scout_dns import ResolverEndpoint
from lychd.system.services.scout_extraction import (
    ExtractionLifecycle,
    ScoutExtractionRuntime,
    extract_static_text,
)
from lychd.system.services.scout_fetch import fetch_static_page
from lychd.system.services.scout_http import serialize_get

MAX_INPUT_BYTES = 8192
MAX_OUTPUT_BYTES = 49_152
MAX_PROFILE_BYTES = 32_768
MAX_JOURNAL_BYTES = 512 * 1024
ATTEMPT_CONNECTS = 3
ATTEMPT_TRANSMISSIONS = 512
ATTEMPT_WIRE_BYTES = 1024 * 1024
MAX_CHUNK_BYTES = 16 * 1024
EXCERPT_CHARS = 4000
FOCUS_PREFIX_CHARS = 500
PRIVATE_FILE_MODE = 0o600
PRIVATE_DIRECTORY_MODE = 0o700
DNS_FAMILIES = 2
HTTPS_PORT = 443
MAX_DNS_MESSAGE_BYTES = 512
CA_FILE = Path("/etc/ssl/certs/ca-certificates.crt")
ROOT = Path(__file__).resolve().parents[1]
_DIGEST = re.compile(r"[0-9a-f]{64}")
_STATUSES = frozenset({"claimed", "unknown", "succeeded", "refused"})
_CONNECTING = frozenset({0, errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY, errno.EINTR})
_LIBRARY_NAMES = (
    "ld-linux-x86-64.so.2",
    "libc.so.6",
    "libdl.so.2",
    "libgcc_s.so.1",
    "libm.so.6",
    "libpthread.so.0",
    "librt.so.1",
    "libutil.so.1",
)


class ResearchRefusedError(ValueError):
    """A fixed local outcome that never contains rejected source or input data."""

    def __init__(self) -> None:
        """Keep rejected authority and external content out of diagnostics."""
        super().__init__("research_refused")


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return sha256(raw.encode("utf-8")).hexdigest()


def _journal_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, item in pairs:
        if key in result:
            raise ResearchRefusedError
        result[key] = item
    return result


def _invalid_journal_constant(_value: str) -> object:
    raise ResearchRefusedError


def receipt_identity(event_id: str, source_id: str) -> str:
    """Keep occurrence identity independent of process, application and profile."""
    return _digest([event_id, source_id])


def _directory(path: Path) -> int:
    if not path.is_absolute() or ".." in path.parts:
        raise ResearchRefusedError
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in path.parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _private_regular(descriptor: int) -> None:
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != PRIVATE_FILE_MODE:
        raise ResearchRefusedError
    if info.st_nlink != 1:
        raise ResearchRefusedError


def _read_at(directory: int, name: str, limit: int) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=directory)
    try:
        _private_regular(descriptor)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        if not raw or len(raw) > limit:
            raise ResearchRefusedError
        return raw
    finally:
        os.close(descriptor)


@dataclass(frozen=True)
class CurrentProfile:
    """Pin actual private configuration bytes and recheck before each effect."""

    path: Path
    profile: ResearchRuntimeProfile
    raw_digest: str

    @classmethod
    def load(cls, path: Path) -> CurrentProfile:
        directory = _directory(path.parent)
        try:
            raw = _read_at(directory, path.name, MAX_PROFILE_BYTES)
        finally:
            os.close(directory)
        strict_json(raw)
        profile = ResearchRuntimeProfile.model_validate_json(raw)
        current = cls(path, profile, sha256(raw).hexdigest())
        current.require_current()
        return current

    def require_current(self) -> None:
        """Fence later work on removal, replacement, expiry or generation change."""
        directory = _directory(self.path.parent)
        try:
            raw = _read_at(directory, self.path.name, MAX_PROFILE_BYTES)
        finally:
            os.close(directory)
        if sha256(raw).hexdigest() != self.raw_digest or datetime.now(UTC) >= self.profile.expires_at:
            raise ResearchRefusedError

    def sources_for(self, job: ResearchJob) -> tuple[ResearchSource, ...]:
        self.require_current()
        profile = self.profile
        if job.subject_id not in profile.allowed_subject_ids or len(set(job.source_ids)) != len(job.source_ids):
            raise ResearchRefusedError
        if job.direct:
            if job.subject_id not in profile.allowed_dm_user_ids:
                raise ResearchRefusedError
        elif job.conversation_id not in profile.allowed_channel_ids:
            raise ResearchRefusedError
        sources = {item.id: item for item in profile.catalogue.sources}
        if any(source_id not in sources for source_id in job.source_ids):
            raise ResearchRefusedError
        return tuple(sources[source_id] for source_id in job.source_ids)


class AttemptJournal:
    """Exclusive private custody; reservations never refund or reset by profile."""

    def __init__(self, directory: Path, profile: ResearchRuntimeProfile) -> None:
        """Bind one partition without opening it or manufacturing a reservation."""
        self._path, self._profile = directory, profile
        self._directory = self._lock = -1
        self._attempts: dict[str, dict[str, str]] = {}

    def __enter__(self) -> Self:
        """Lock the whole job and retain unfinished occurrences as unknown."""
        if self._path.is_relative_to(ROOT):
            raise ResearchRefusedError
        self._directory = _directory(self._path)
        try:
            info = os.fstat(self._directory)
            if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != PRIVATE_DIRECTORY_MODE:
                raise ResearchRefusedError  # noqa: TRY301 - keep directory ownership adjacent to its open
            self._lock = os.open(
                "lock",
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                0o600,
                dir_fd=self._directory,
            )
            _private_regular(self._lock)
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                raw = _read_at(self._directory, "journal.json", MAX_JOURNAL_BYTES)
            except FileNotFoundError:
                self._persist()
            else:
                self._load(raw)
                if any(row["status"] == "claimed" for row in self._attempts.values()):
                    for row in self._attempts.values():
                        if row["status"] == "claimed":
                            row["status"] = "unknown"
                    self._persist()
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *_exc: object) -> None:
        """Close only owned descriptors; durable reservations remain retained."""
        for name in ("_lock", "_directory"):
            descriptor = getattr(self, name)
            if descriptor >= 0:
                os.close(descriptor)
                setattr(self, name, -1)

    def _load(self, raw: bytes) -> None:
        decoded: object = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_journal_object, parse_constant=_invalid_journal_constant
        )
        if type(decoded) is not dict:
            raise ResearchRefusedError
        value = cast("dict[str, Any]", decoded)
        if (
            set(value) != {"profile_digest", "attempts"}
            or value["profile_digest"] != self._profile.digest
            or type(value["attempts"]) is not dict
        ):
            raise ResearchRefusedError
        attempts = cast("dict[str, Any]", value["attempts"])
        if len(attempts) > self._profile.max_attempts:
            raise ResearchRefusedError
        for key, decoded_row in attempts.items():
            if type(decoded_row) is not dict:
                raise ResearchRefusedError
            row = cast("dict[str, Any]", decoded_row)
            if (
                type(key) is not str
                or _DIGEST.fullmatch(key) is None
                or set(row) != {"binding", "status"}
                or type(row["binding"]) is not str
                or _DIGEST.fullmatch(row["binding"]) is None
                or type(row["status"]) is not str
                or row["status"] not in _STATUSES
            ):
                raise ResearchRefusedError
        self._attempts = cast("dict[str, dict[str, str]]", attempts)
        self._check_capacity(len(attempts))

    def _persist(self) -> None:
        raw = json.dumps(
            {"profile_digest": self._profile.digest, "attempts": self._attempts},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
        if len(raw) > MAX_JOURNAL_BYTES:
            raise ResearchRefusedError
        temporary = f"journal-{uuid4()}.tmp"
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=self._directory,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(descriptor)
            os.replace(temporary, "journal.json", src_dir_fd=self._directory, dst_dir_fd=self._directory)
            os.fsync(self._directory)
        finally:
            os.close(descriptor)
            with suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=self._directory)

    def _check_capacity(self, attempts: int) -> None:
        profile = self._profile
        if (
            attempts > profile.max_attempts
            or attempts * ATTEMPT_CONNECTS > profile.max_connects
            or attempts * ATTEMPT_TRANSMISSIONS > profile.max_transmissions
            or attempts * ATTEMPT_WIRE_BYTES > profile.max_wire_bytes
        ):
            raise ResearchRefusedError

    def claim(self, receipt: str, binding: str) -> Literal["fresh", "unavailable", "changed", "budget"]:
        """Return an execution opportunity only after acknowledged durable reserve."""
        previous = self._attempts.get(receipt)
        if previous is not None:
            return "unavailable" if previous["binding"] == binding else "changed"
        try:
            self._check_capacity(len(self._attempts) + 1)
        except ResearchRefusedError:
            return "budget"
        self._attempts[receipt] = {"binding": binding, "status": "claimed"}
        self._persist()
        return "fresh"

    def settle(self, receipt: str, status: Literal["succeeded", "refused", "unknown"]) -> None:
        if self._attempts[receipt]["status"] != "claimed":
            raise ResearchRefusedError
        self._attempts[receipt]["status"] = status
        self._persist()


class CatalogueNetworkGate:
    """One same-loop native passage; profile changes deny the next syscall."""

    def __init__(self, current: CurrentProfile, candidate: DestinationCandidate, deadline: float) -> None:
        """Use only after the journal has durably reserved this exact occurrence."""
        self._loop = asyncio.get_running_loop()
        self._current, self._candidate, self._deadline = current, candidate, deadline
        self._request = serialize_get(candidate)
        self._resolver = NetworkTarget(current.profile.resolver_address, 53, candidate.hostname, "resolver")
        self._origin: NetworkTarget | None = None
        self._dns_started = self._dns_finished = self._dns_offset = 0
        self._dns_message: bytes | None = None
        self._pending: tuple[str, bytes, bytes | None] | None = None
        self._connects = self._transmissions = self._wire_bytes = 0
        self._closed = self._busy = self.uncertain = False

    def close(self) -> None:
        self._closed = True

    def _check(self, handoff: NetworkHandoff) -> None:
        if (
            asyncio.get_running_loop() is not self._loop
            or self._closed
            or self._busy
            or time.monotonic() >= self._deadline
        ):
            raise FetchError(FetchCode.EGRESS)
        self._current.require_current()
        if (
            type(handoff) is not NetworkHandoff
            or type(handoff.target) is not NetworkTarget
            or type(handoff.wire_bytes) is not bytes
            or len(handoff.wire_bytes) > MAX_CHUNK_BYTES
            or handoff.phase not in {"connect", "dns", "tls", "http"}
            or (handoff.application_bytes is not None and type(handoff.application_bytes) is not bytes)
        ):
            raise FetchError(FetchCode.EGRESS)
        if handoff.phase == "connect":
            self._check_connect(handoff)
        elif not handoff.wire_bytes:
            raise FetchError(FetchCode.EGRESS)
        elif handoff.phase == "dns":
            self._check_dns(handoff)
        elif (
            self._origin is None
            or handoff.target != self._origin
            or (handoff.phase == "tls" and handoff.application_bytes is not None)
            or (handoff.phase == "http" and handoff.application_bytes != self._request)
        ):
            raise FetchError(FetchCode.EGRESS)
        if self._pending is not None and self._pending != (
            handoff.phase,
            handoff.wire_bytes,
            handoff.application_bytes,
        ):
            raise FetchError(FetchCode.EGRESS)
        if (
            self._connects + int(handoff.phase == "connect") > ATTEMPT_CONNECTS
            or self._transmissions + int(handoff.phase != "connect") > ATTEMPT_TRANSMISSIONS
            or self._wire_bytes + len(handoff.wire_bytes) > ATTEMPT_WIRE_BYTES
        ):
            raise FetchError(FetchCode.LIMIT)

    def _check_connect(self, handoff: NetworkHandoff) -> None:
        if handoff.wire_bytes or handoff.application_bytes is not None or self._pending is not None:
            raise FetchError(FetchCode.EGRESS)
        if handoff.target.role == "resolver":
            if (
                handoff.target != self._resolver
                or self._candidate.ip_literal is not None
                or self._origin is not None
                or self._dns_started != self._dns_finished
                or self._dns_started >= DNS_FAMILIES
            ):
                raise FetchError(FetchCode.EGRESS)
        elif (
            handoff.target.role != "origin"
            or self._origin is not None
            or handoff.target.hostname != self._candidate.hostname
            or handoff.target.port != HTTPS_PORT
            or (self._candidate.ip_literal is None and self._dns_finished != DNS_FAMILIES)
        ):
            raise FetchError(FetchCode.EGRESS)
        else:
            classify_destination_addresses(
                self._candidate, hostname=handoff.target.hostname, addresses=(handoff.target.address,)
            )

    def _check_dns(self, handoff: NetworkHandoff) -> None:
        message = handoff.application_bytes
        if (
            handoff.target != self._resolver
            or self._origin is not None
            or self._dns_started != self._dns_finished + 1
            or message is None
            or len(message) > MAX_DNS_MESSAGE_BYTES
        ):
            raise FetchError(FetchCode.EGRESS)
        qname = b"".join(bytes([len(part)]) + part.encode("ascii") for part in self._candidate.hostname.split("."))
        question = qname + b"\x00" + (1 if self._dns_finished == 0 else 28).to_bytes(2, "big") + b"\x00\x01"
        tail = b"\x01\x00\x00\x01" + b"\x00" * 6 + question
        if (
            len(message) != len(tail) + 4
            or int.from_bytes(message[:2], "big") != len(message) - 2
            or message[4:] != tail
            or (self._dns_message is not None and message != self._dns_message)
            or handoff.wire_bytes != message[self._dns_offset : self._dns_offset + MAX_CHUNK_BYTES]
        ):
            raise FetchError(FetchCode.EGRESS)

    def handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:  # noqa: C901, PLR0912 - explicit synchronous check/debit/syscall settlement
        """Check and charge before exactly one synchronous, nonblocking syscall."""
        try:
            self._check(handoff)
        except BaseException:
            self._closed = True
            raise
        self._busy = True
        self._connects += int(handoff.phase == "connect")
        self._transmissions += int(handoff.phase != "connect")
        self._wire_bytes += len(handoff.wire_bytes)
        if handoff.phase == "connect":
            if handoff.target.role == "resolver":
                self._dns_started += 1
            else:
                self._origin = handoff.target
        elif handoff.phase == "dns":
            self._dns_message = handoff.application_bytes
        try:
            count = action()
            if type(count) is not int or (handoff.phase != "connect" and not 0 <= count <= len(handoff.wire_bytes)):
                self.uncertain = True
                raise FetchError(FetchCode.TRANSPORT)  # noqa: TRY301 - invalid syscall return is an uncertain effect
            if handoff.phase == "connect":
                if count not in _CONNECTING:
                    self._closed = True
            else:
                self._accepted(handoff, count)
        except (BlockingIOError, InterruptedError):
            if handoff.phase == "connect":
                self.uncertain = self._closed = True
            else:
                self._accepted(handoff, 0)
            raise
        except BaseException:
            self.uncertain = self._closed = True
            raise
        finally:
            self._busy = False
        return count

    def _accepted(self, handoff: NetworkHandoff, count: int) -> None:
        suffix = handoff.wire_bytes[count:]
        self._pending = (handoff.phase, suffix, handoff.application_bytes) if suffix else None
        if handoff.phase == "dns":
            self._dns_offset += count
            if self._dns_message is not None and self._dns_offset == len(self._dns_message):
                self._dns_finished += 1
                self._dns_offset = 0
                self._dns_message = None


def extraction_runtime() -> ScoutExtractionRuntime:
    """Select the qualified image closure, with no host or parser fallback."""
    return ScoutExtractionRuntime(
        Path("/usr/bin/bwrap"),
        Path("/opt/scout-python"),
        tuple(Path("/usr/lib/x86_64-linux-gnu") / name for name in _LIBRARY_NAMES),
    )


def project_excerpt(text: str, focus: tuple[str, ...]) -> tuple[str, int]:
    """Locate the earliest casefolded focus while preserving original offsets."""
    start = 0
    if focus:
        folded: list[str] = []
        positions: list[int] = []
        for index, character in enumerate(text):
            part = character.casefold()
            folded.append(part)
            positions.extend([index] * len(part))
        value = "".join(folded)
        matches = [value.find(term.casefold()) for term in focus]
        found = [positions[index] for index in matches if index >= 0]
        if found:
            start = max(0, min(found) - FOCUS_PREFIX_CHARS)
    return text[start : start + EXCERPT_CHARS], start


def _failure(source: ResearchSource, receipt: str, reason: str, *, refused: bool = False) -> SourceReadResult:
    return SourceReadResult(
        id=f"web:{source.id}",
        title=source.title,
        url=source.url,
        status="refused" if refused else "unavailable",
        receipt_id=receipt,
        reason=reason,
    )


def _source_result(source: ResearchSource, receipt: str, extracted: ExtractedText) -> SourceReadResult:
    """Project verified extraction without treating an empty page as usable evidence."""
    excerpt, start = project_excerpt(extracted.text, source.focus)
    if not excerpt.strip():
        return _failure(source, receipt, "no_extractable_text")
    return SourceReadResult(
        id=f"web:{source.id}",
        title=source.title,
        url=source.url,
        status="ok",
        text=excerpt,
        source_digest=extracted.source_digest,
        text_digest=sha256(excerpt.encode("utf-8")).hexdigest(),
        source_chars=len(extracted.text),
        excerpt_start=start,
        truncated=start > 0 or start + len(excerpt) < len(extracted.text),
        receipt_id=receipt,
    )


async def _read_source(  # noqa: C901 - distinct refusal and uncertain settlement paths
    current: CurrentProfile, journal: AttemptJournal, job: ResearchJob, source: ResearchSource
) -> SourceReadResult:
    receipt = receipt_identity(job.event_id, source.id)
    binding = _digest(
        {
            "job": job.model_dump(mode="json"),
            "source": source.model_dump(mode="json"),
            "profile": current.profile.digest,
        }
    )
    disposition = journal.claim(receipt, binding)
    if disposition != "fresh":
        reasons = {"unavailable": "material_unavailable", "changed": "changed_request", "budget": "budget"}
        return _failure(source, receipt, reasons[disposition], refused=disposition != "unavailable")
    gate: CatalogueNetworkGate | None = None
    lifecycle = ExtractionLifecycle()
    status: Literal["succeeded", "refused", "unknown"] = "refused"
    try:
        current.require_current()
        candidate = preflight_destination(source.url)
        deadline = time.monotonic() + 30.0
        gate = CatalogueNetworkGate(current, candidate, deadline)
        async with asyncio.timeout(30):
            page = await fetch_static_page(
                candidate,
                resolver=ResolverEndpoint(current.profile.resolver_address, 53),
                gate=gate,
                ca_file=CA_FILE,
                deadline=deadline,
                permitted_redirects=(),
            )
            current.require_current()
            extracted = await extract_static_text(
                page.body,
                media_type=page.media_type,
                runtime=extraction_runtime(),
                lifecycle=lifecycle,
            )
        current.require_current()
        if (
            type(extracted) is not ExtractedText
            or extracted.media_type != page.media_type
            or extracted.source_digest != sha256(page.body).hexdigest()
            or extracted.text_digest != sha256(extracted.text.encode("utf-8")).hexdigest()
            or lifecycle.child != "reaped"
        ):
            raise ResearchRefusedError  # noqa: TRY301 - validate exact acquired bytes before projecting them
        result = _source_result(source, receipt, extracted)
        status = "succeeded" if result.status == "ok" else "refused"
    except FetchError as exc:
        reason = f"fetch_{exc.code.value}" if type(exc.code) is FetchCode else "fetch_failed"
        return _failure(source, receipt, reason)
    except ExtractionError as exc:
        if exc.code is ExtractionCode.CLEANUP:
            status = "unknown"
        reason = f"extract_{exc.code.value}" if type(exc.code) is ExtractionCode else "extract_failed"
        return _failure(source, receipt, reason)
    except (ResearchRefusedError, TimeoutError):
        return _failure(source, receipt, "current_authority_or_material")
    except asyncio.CancelledError:
        status = "unknown"
        raise
    except Exception:  # noqa: BLE001 - foreign diagnostics are never protocol data
        status = "unknown"
        return _failure(source, receipt, "acquisition_failed")
    finally:
        if gate is not None:
            gate.close()
            if gate.uncertain:
                status = "unknown"
        if lifecycle.child is None:
            status = "unknown"
        journal.settle(receipt, status)
    return result


async def research(current: CurrentProfile, state_dir: Path, job: ResearchJob) -> tuple[SourceReadResult, ...]:
    """Serialize one complete bounded job under the exclusive durable partition."""
    sources = current.sources_for(job)
    with AttemptJournal(state_dir, current.profile) as journal:
        results: list[SourceReadResult] = []
        for source in sources:
            current.require_current()
            results.append(await _read_source(current, journal, job, source))
        return tuple(results)


def _require_image() -> None:
    if not Path("/opt/lychd-test-image").is_file() or not (
        Path("/run/.containerenv").is_file() or Path("/.dockerenv").is_file()
    ):
        raise ResearchRefusedError


def main(argv: list[str] | None = None) -> int:
    """Read one EOF-terminated job; failures expose only fixed local diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    arguments = parser.parse_args(argv)
    previous_level = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        _require_image()
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES or not raw.endswith(b"\n") or raw.count(b"\n") != 1:
            raise ResearchRefusedError  # noqa: TRY301 - reject incomplete framing before parsing
        strict_json(raw)
        job = ResearchJob.model_validate_json(raw)
        current = CurrentProfile.load(arguments.profile)
        results = asyncio.run(research(current, arguments.state_dir, job))
        output = (
            json.dumps(
                [item.model_dump(mode="json") for item in results], ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            + b"\n"
        )
        if len(output) > MAX_OUTPUT_BYTES:
            raise ResearchRefusedError  # noqa: TRY301 - validate the complete frame before stdout handoff
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.flush()
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 130
    except Exception:  # noqa: BLE001 - rejected locators, bodies and errors stay private
        print("[]")  # noqa: T201 - one closed protocol failure frame
        print("reach_scout_worker_refused", file=sys.stderr)  # noqa: T201 - fixed local diagnostic
        return 1
    finally:
        logging.disable(previous_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
