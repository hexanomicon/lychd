"""Trusted host admission and custody for one disposable public-source scout.

The broker exposes a frozen catalogue, an acknowledgement handshake and one fixed
container entrypoint. Source text and foreign diagnostics never select host code,
credentials, paths or network destinations.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from lychd.compositions.reach.operator_model_wire import OperatorConversationProfile
from lychd.compositions.reach.operator_wire import strict_json
from lychd.compositions.reach.policy import prepare_turn
from lychd.compositions.reach.research_wire import (
    OperatorResearchRequest,
    OperatorResearchResponse,
    ReachResearchAcknowledgement,
    ReachResearchProgress,
    ResearchJob,
    ResearchRuntimeProfile,
    SourceReadResult,
)
from lychd.compositions.reach.schemas import ReachPolicy

MAX_PROFILE_BYTES = 16_384
MAX_SCOUT_OUTPUT_BYTES = 49_152
MAX_SCOUT_ERROR_BYTES = 8192
MAX_SEEN_EVENTS = 1000
ACK_TIMEOUT_SECONDS = 20
SCOUT_TIMEOUT_SECONDS = 70
_IMAGE = re.compile(r"sha256:[0-9a-f]{64}")
_CONTAINER = re.compile(r"[0-9a-f]{64}")


def _now() -> datetime:
    return datetime.now(UTC)


def _external_path(path: Path) -> None:
    if (
        not path.is_absolute()
        or any(part in {".", ".."} for part in path.parts)
        or any(char in str(path) for char in ":,\r\n\x00")
    ):
        msg = "research_path"
        raise ValueError(msg)
    for current in reversed((path, *path.parents)):
        if current.is_symlink() or (current.is_dir() and (current / ".git").exists()):
            msg = "research_path"
            raise ValueError(msg)


def _private_directory(path: Path) -> None:
    _external_path(path)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        msg = "research_directory"
        raise ValueError(msg)


def _regular_bytes(path: Path, limit: int, *, private: bool) -> bytes:
    _external_path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        info = os.fstat(source.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or (private and info.st_mode & 0o077)
            or info.st_size > limit
        ):
            msg = "research_file"
            raise ValueError(msg)
        raw = source.read(limit + 1)
    if len(raw) > limit:
        msg = "research_file"
        raise ValueError(msg)
    return raw


def _engine_environment() -> dict[str, str]:
    result = {"PATH": os.environ.get("PATH", os.defpath), "LANG": "C.UTF-8"}
    host = os.environ.get("DOCKER_HOST")
    if host is not None:
        if not host.startswith("unix:///") or any(char in host for char in "\r\n\x00"):
            msg = "research_engine_host"
            raise ValueError(msg)
        result["DOCKER_HOST"] = host
    return result


async def _bounded_read(reader: asyncio.StreamReader, limit: int) -> bytes:
    result = bytearray()
    while chunk := await reader.read(min(8192, limit + 1 - len(result))):
        result.extend(chunk)
        if len(result) > limit:
            msg = "research_worker_limit"
            raise ValueError(msg)
    return bytes(result)


async def _retire(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    with suppress(ProcessLookupError):
        process.terminate()
    try:
        await asyncio.wait_for(process.wait(), 5)
    except TimeoutError:
        with suppress(ProcessLookupError):
            process.kill()
        await asyncio.wait_for(process.wait(), 5)


@dataclass(frozen=True)
class _PendingAcknowledgement:
    request_id: str
    binding_digest: str
    future: asyncio.Future[bool]


class _ScoutSettlement:
    """Remember caller cancellation while joining owned spawn and cleanup tasks."""

    def __init__(self) -> None:
        """Capture the caller's cancellation baseline before acquiring a child."""
        self.caller = asyncio.current_task()
        self.initial_cancels = self.caller.cancelling() if self.caller is not None else 0
        self.cancelled = False

    async def join[T](self, owned: asyncio.Future[T]) -> T:
        while True:
            try:
                return await asyncio.shield(owned)
            except asyncio.CancelledError:
                if owned.cancelled():
                    raise
                self.cancelled = True

    def propagate(self) -> None:
        if self.cancelled and self.caller is not None and self.caller.cancelling() > self.initial_cancels:
            raise asyncio.CancelledError


class OperatorResearchBroker:
    """Admit one exact event once and settle the scout before releasing its slot."""

    def __init__(
        self,
        profile: OperatorConversationProfile,
        policy: ReachPolicy,
        *,
        runtime_profile_path: Path,
        state_dir: Path,
        image: str,
        engine: Literal["docker"] = "docker",
    ) -> None:
        """Validate dedicated private authority and state without starting a process."""
        if engine != "docker" or _IMAGE.fullmatch(image) is None:
            msg = "research_image"
            raise ValueError(msg)
        _private_directory(runtime_profile_path.parent)
        _private_directory(state_dir)
        if (
            runtime_profile_path.name != "profile.json"
            or state_dir == runtime_profile_path.parent
            or state_dir in runtime_profile_path.parents
            or runtime_profile_path.parent in state_dir.parents
        ):
            msg = "research_path_overlap"
            raise ValueError(msg)
        self.profile = profile
        self.policy = policy
        self.runtime_profile_path = runtime_profile_path
        self.state_dir = state_dir
        self.image = image
        self.engine = engine
        self._environment = _engine_environment()
        runtime = self._load_runtime_profile()
        if not profile.research.enabled or runtime.catalogue != profile.research or _now() >= runtime.expires_at:
            msg = "research_authority"
            raise ValueError(msg)
        self._runtime_digest = runtime.digest
        self._pending: dict[str, _PendingAcknowledgement] = {}
        self._seen: set[tuple[str, str, str]] = set()
        self._seen_calls: set[str] = set()
        self._busy = False
        self._poisoned = False
        self._material_request: OperatorResearchRequest | None = None

    def _load_runtime_profile(self) -> ResearchRuntimeProfile:
        _private_directory(self.runtime_profile_path.parent)
        if tuple(self.runtime_profile_path.parent.iterdir()) != (self.runtime_profile_path,):
            msg = "research_authority_directory"
            raise ValueError(msg)
        raw = _regular_bytes(self.runtime_profile_path, MAX_PROFILE_BYTES, private=True)
        strict_json(raw)
        return ResearchRuntimeProfile.model_validate_json(raw)

    def _admission(self, request: OperatorResearchRequest) -> str | None:
        if request.binding_digest != self.profile.digest or request.event.action != "converse":
            return "research_binding"
        if self._poisoned or self._busy:
            return "research_unavailable"
        identity = (request.event.platform, request.event.account_id, request.event.event_id)
        if identity in self._seen or request.call_id in self._seen_calls:
            return "research_duplicate"
        if len(self._seen) >= MAX_SEEN_EVENTS:
            return "research_generation_budget"
        if len(set(request.source_ids)) != len(request.source_ids) or not set(request.source_ids).issubset(
            {source.id for source in self.profile.research.sources}
        ):
            return "research_source"
        return self._fresh_authority(request)

    def _fresh_authority(self, request: OperatorResearchRequest) -> str | None:  # noqa: PLR0911 - closed authority refusal order
        try:
            runtime = self._load_runtime_profile()
        except (OSError, ValueError):
            return "research_authority"
        now = _now()
        event = request.event
        if runtime.digest != self._runtime_digest or now >= runtime.expires_at:
            return "research_authority"
        if not prepare_turn(self.policy, event, now=now).allowed:
            return "research_event"
        if event.subject_id not in runtime.allowed_subject_ids:
            return "research_subject"
        if event.trigger == "message":
            if event.subject_id not in runtime.allowed_dm_user_ids:
                return "research_target"
        elif event.conversation_id not in runtime.allowed_channel_ids:
            return "research_target"
        return None

    def acknowledge(self, acknowledgement: ReachResearchAcknowledgement) -> None:
        """Accept one exact edge observation before any source acquisition starts."""
        pending = self._pending.get(acknowledgement.call_id)
        if (
            pending is None
            and acknowledgement.call_id in self._seen_calls
            and acknowledgement.binding_digest == self.profile.digest
        ):
            return
        if (
            pending is None
            or pending.future.done()
            or acknowledgement.request_id != pending.request_id
            or acknowledgement.binding_digest != pending.binding_digest
        ):
            msg = "research_acknowledgement"
            raise ValueError(msg)
        pending.future.set_result(acknowledgement.accepted)

    def authorize_consume(self, request_id: str) -> Callable[[], None]:
        """Issue one non-bearer current check for this exact local synthesis handoff."""
        request = self._material_request
        if request is None or request.request_id != request_id or self._fresh_authority(request) is not None:
            msg = "research_consume"
            raise ValueError(msg)
        self._material_request = None

        def require_current() -> None:
            if self._fresh_authority(request) is not None:
                msg = "research_consume"
                raise ValueError(msg)

        return require_current

    @property
    def material_pending(self) -> bool:
        return self._material_request is not None

    def settled(self, request_id: str) -> None:
        """Withdraw unconsumed transient material after this exact terminal result."""
        if self._material_request is not None and self._material_request.request_id == request_id:
            self._material_request = None

    @staticmethod
    def _refuse(request: OperatorResearchRequest, reason: str) -> OperatorResearchResponse:
        return OperatorResearchResponse(
            call_id=request.call_id,
            request_id=request.request_id,
            binding_digest=request.binding_digest,
            status="refused",
            reason=reason,
        )

    async def handle(  # noqa: PLR0911 - explicit bounded handshake and acquisition settlement
        self,
        request: OperatorResearchRequest,
        send_progress: Callable[[ReachResearchProgress], Awaitable[None]],
    ) -> OperatorResearchResponse:
        """Await the delivered interpretation, then perform at most one fixed scout job."""
        reason = self._admission(request)
        if reason is not None:
            return self._refuse(request, reason)
        self._seen.add((request.event.platform, request.event.account_id, request.event.event_id))
        self._seen_calls.add(request.call_id)
        self._busy = True
        future = asyncio.get_running_loop().create_future()
        self._pending[request.call_id] = _PendingAcknowledgement(request.request_id, request.binding_digest, future)
        try:
            async with asyncio.timeout(ACK_TIMEOUT_SECONDS):
                await send_progress(
                    ReachResearchProgress(
                        call_id=request.call_id,
                        request_id=request.request_id,
                        binding_digest=request.binding_digest,
                        text=request.plan,
                    )
                )
                accepted = await future
            if not accepted:
                return self._refuse(request, "research_acknowledgement")
            reason = self._fresh_authority(request)
            if reason is not None:
                return self._refuse(request, reason)
            sources = await self._scout(request) if request.source_ids else ()
            if self._poisoned:
                return self._refuse(request, "research_cleanup")
            reason = self._fresh_authority(request)
            if reason is not None:
                return self._refuse(request, reason)
            self._material_request = request
            return OperatorResearchResponse(
                call_id=request.call_id,
                request_id=request.request_id,
                binding_digest=request.binding_digest,
                status="ok",
                sources=sources,
            )
        except TimeoutError:
            return self._refuse(request, "research_timeout")
        except (OSError, ValueError, TypeError):
            return self._refuse(request, "research_protocol")
        finally:
            self._pending.pop(request.call_id, None)
            if not future.done():
                future.cancel()
            self._busy = False

    def _command(self, state: Path, scratch: Path) -> list[str]:
        return [
            self.engine,
            "--config",
            str(scratch / "engine-config"),
            "run",
            "--pull=never",
            "--interactive",
            "--cidfile",
            str(scratch / "container.id"),
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--security-opt=seccomp=unconfined",
            "--security-opt=label=disable",
            "--security-opt=systempaths=unconfined",
            "--network=host",
            "--pids-limit=128",
            "--memory=512m",
            "--cpus=1",
            "--log-driver=none",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=64m",  # noqa: S108 - private, bounded container tmpfs
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--mount",
            f"type=bind,src={self.runtime_profile_path.parent},dst=/run/research-authority,readonly",
            "--mount",
            f"type=bind,src={state},dst=/state/research",
            "--workdir=/work",
            "--entrypoint=python",
            self.image,
            "/work/scripts/reach_scout_worker.py",
            "--profile",
            "/run/research-authority/profile.json",
            "--state-dir",
            "/state/research",
        ]

    async def _cleanup(self, process: asyncio.subprocess.Process | None, scratch: Path) -> None:
        try:
            if process is not None:
                try:
                    await _retire(process)
                except (OSError, TimeoutError):
                    self._poisoned = True
            cidfile = scratch / "container.id"
            if not cidfile.exists():
                self._poisoned = self._poisoned or process is not None
                return
            identity = _regular_bytes(cidfile, 128, private=False).decode("ascii").strip()
            if _CONTAINER.fullmatch(identity) is None:
                self._poisoned = True
                return
            cleanup = await asyncio.create_subprocess_exec(
                self.engine,
                "--config",
                str(scratch / "engine-config"),
                "rm",
                "--force",
                identity,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=self._environment,
            )
            try:
                result = await asyncio.wait_for(cleanup.wait(), 15)
                self._poisoned = self._poisoned or bool(result)
            finally:
                await _retire(cleanup)
        except asyncio.CancelledError:
            self._poisoned = True
            raise
        except (OSError, ValueError, TimeoutError):
            self._poisoned = True

    def _sources(self, raw: bytes, request: OperatorResearchRequest) -> tuple[SourceReadResult, ...]:
        parsed = strict_json(raw)
        if not isinstance(parsed, list):
            msg = "research_worker_protocol"
            raise TypeError(msg)
        values = cast("list[object]", parsed)
        if len(values) != len(request.source_ids):
            msg = "research_worker_protocol"
            raise ValueError(msg)
        sources = tuple(SourceReadResult.model_validate(value) for value in values)
        catalogue = {source.id: source for source in self.profile.research.sources}
        for source_id, result in zip(request.source_ids, sources, strict=True):
            expected = catalogue[source_id]
            if (result.id, result.title, result.url) != (f"web:{source_id}", expected.title, expected.url) or (
                result.status == "ok" and result.source_chars < result.excerpt_start + len(result.text)
            ):
                msg = "research_worker_binding"
                raise ValueError(msg)
        return sources

    async def _receive_scout(
        self, process: asyncio.subprocess.Process, job: ResearchJob, tasks: list[asyncio.Task[bytes]]
    ) -> bytes:
        if process.stdin is None or process.stdout is None or process.stderr is None:
            msg = "research_worker_pipes"
            raise ValueError(msg)
        tasks.extend(
            (
                asyncio.create_task(_bounded_read(process.stdout, MAX_SCOUT_OUTPUT_BYTES)),
                asyncio.create_task(_bounded_read(process.stderr, MAX_SCOUT_ERROR_BYTES)),
            )
        )
        process.stdin.write(job.model_dump_json().encode("utf-8") + b"\n")
        await process.stdin.drain()
        process.stdin.close()
        await process.stdin.wait_closed()
        stdout, _stderr = await asyncio.gather(*tasks)
        if await process.wait():
            msg = "research_worker_failed"
            raise ValueError(msg)
        return stdout

    async def _scout(self, request: OperatorResearchRequest) -> tuple[SourceReadResult, ...]:
        _private_directory(self.state_dir)
        state = self.state_dir / "scout"
        state.mkdir(mode=0o700, exist_ok=True)
        _private_directory(state)
        scratch = Path(tempfile.mkdtemp(prefix="scout-", dir=self.state_dir))
        (scratch / "engine-config").mkdir(mode=0o700)
        job = ResearchJob(
            event_id=request.event.event_id,
            subject_id=request.event.subject_id,
            conversation_id=request.event.conversation_id,
            direct=request.event.trigger == "message",
            source_ids=request.source_ids,
        )
        process: asyncio.subprocess.Process | None = None
        spawn: asyncio.Task[asyncio.subprocess.Process] | None = None
        tasks: list[asyncio.Task[bytes]] = []
        settlement = _ScoutSettlement()
        cleanup_proved = False
        try:
            async with asyncio.timeout(SCOUT_TIMEOUT_SECONDS):
                spawn = asyncio.create_task(
                    asyncio.create_subprocess_exec(
                        *self._command(state, scratch),
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=self._environment,
                        limit=MAX_SCOUT_OUTPUT_BYTES + 1,
                    )
                )
                process = await settlement.join(spawn)
                settlement.propagate()
                stdout = await self._receive_scout(process, job, tasks)
                return self._sources(stdout, request)
        finally:
            if spawn is not None and (not spawn.done() or spawn.cancelled()):
                self._poisoned = True
            cleanup = asyncio.create_task(self._cleanup(process, scratch))
            try:
                await settlement.join(cleanup)
                cleanup_proved = not self._poisoned
            finally:
                if not cleanup_proved:
                    self._poisoned = True
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await settlement.join(asyncio.gather(*tasks, return_exceptions=True))
                if cleanup_proved:
                    shutil.rmtree(scratch)
                settlement.propagate()
