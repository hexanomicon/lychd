"""Finite, resumable classic Comfy probe with no physical submit retry."""

import asyncio
import fcntl
import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID, uuid4

import httpx2

from lychd.domain.comfy_probe import (
    MAX_JSON_BYTES,
    MAX_OUTPUT_BYTES,
    ComfyArtifact,
    ComfyAttempt,
    ComfyProfile,
    ComfyRequest,
    canonical_json,
    json_digest,
    safe_component,
)
from lychd.lib.http import create_http_ssl_context

MAX_SUBFOLDER_LENGTH = 256
MIN_QUEUE_COLUMNS = 3


class ProbeRefusedError(ValueError):
    """The probe cannot perform the requested effect within its pinned closure."""


class ComfyProbe:
    """External technical files are not Phylactery or native ServiceJob attempts.

    The caller supplies every checkout root; the workspace must already exist outside
    them without symlink components. This fence is not process or engine containment.
    """

    def __init__(
        self,
        profile: ComfyProfile,
        workspace: Path,
        checkout_roots: tuple[Path, ...],
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        """Revalidate the reviewed profile and bind its external workspace."""
        if not checkout_roots or not workspace.is_absolute() or not workspace.is_dir():
            msg = "An existing absolute external workspace and checkout fences are required"
            raise ProbeRefusedError(msg)
        self.profile = ComfyProfile.model_validate_json(profile.model_dump_json())
        self.workspace = workspace
        self.checkout_roots = tuple(root.resolve() for root in checkout_roots)
        self.transport = transport
        self._fence()

    def _fence(self) -> None:
        if any(part.is_symlink() for part in (self.workspace, *self.workspace.parents)):
            msg = "Workspace has a symlink component"
            raise ProbeRefusedError(msg)
        resolved = self.workspace.resolve()
        if any(resolved == root or root in resolved.parents for root in self.checkout_roots):
            msg = "Probe material must live outside every checkout"
            raise ProbeRefusedError(msg)

    @contextmanager
    def _locked(self, occurrence: UUID) -> Generator[Path]:
        self._fence()
        path = self.workspace / f"{occurrence}.json"
        lock = self.workspace / f"{occurrence}.lock"
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if path.is_symlink():
                msg = "Receipt may not be a symlink"
                raise ProbeRefusedError(msg)
            yield path
        finally:
            os.close(fd)

    def _write(self, path: Path, attempt: ComfyAttempt) -> None:
        fd, temporary = tempfile.mkstemp(dir=self.workspace, prefix=".receipt-")
        try:
            with os.fdopen(fd, "w") as output:
                output.write(attempt.model_dump_json())
                output.flush()
                os.fsync(output.fileno())
            Path(temporary).replace(path)
            self._sync_workspace()
        finally:
            Path(temporary).unlink(missing_ok=True)

    def _sync_workspace(self) -> None:
        self._fence()
        directory = os.open(self.workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def _read(self, path: Path) -> ComfyAttempt:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 2 * MAX_JSON_BYTES:
                msg = "Receipt must be a bounded regular file"
                raise ProbeRefusedError(msg)
            raw = source.read(2 * MAX_JSON_BYTES + 1)
        if len(raw) > 2 * MAX_JSON_BYTES or len(raw) != info.st_size:
            msg = "Receipt exceeds bound"
            raise ProbeRefusedError(msg)
        return ComfyAttempt.model_validate_json(raw)

    def _current(self, attempt: ComfyAttempt, path: Path) -> ComfyAttempt:
        current = self._bound_current(attempt, path)
        for index, artifact in enumerate(current.artifacts):
            if artifact.local_filename is not None:
                self._verify_local(current.occurrence_id, index, artifact)
        return current

    def _bound_current(self, attempt: ComfyAttempt, path: Path) -> ComfyAttempt:
        """Validate immutable receipt identity separately from installed bytes."""
        current = self._read(path)
        request = ComfyRequest(profile_sha256=current.profile_sha256, inputs_json=current.inputs_json)
        if current.profile_sha256 != self.profile.digest:
            msg = "Receipt profile identity changed"
            raise ProbeRefusedError(msg)
        prompt = self.profile.prompt(request)
        if (
            current.occurrence_id != attempt.occurrence_id
            or current.profile_sha256 != self.profile.digest
            or current.request_sha256 != request.digest
            or current.request_sha256 != attempt.request_sha256
            or current.prompt_sha256 != json_digest(canonical_json(prompt))
        ):
            msg = "Receipt, occurrence, profile or input identity changed"
            raise ProbeRefusedError(msg)
        counts: dict[tuple[str, str], int] = {}
        total = 0
        for index, artifact in enumerate(current.artifacts):
            opening = next(
                (
                    item
                    for item in self.profile.outputs
                    if (item.node_id, item.kind) == (artifact.node_id, artifact.kind)
                ),
                None,
            )
            if (
                opening is None
                or artifact.receiving_owner != opening.receiving_owner
                or Path(artifact.filename).suffix.lower() not in opening.extensions
            ):
                msg = "Receipt output is outside the reviewed profile"
                raise ProbeRefusedError(msg)
            key = (artifact.node_id, artifact.kind)
            counts[key] = counts.get(key, 0) + 1
            if counts[key] > opening.max_files:
                msg = "Receipt output count exceeds the reviewed profile"
                raise ProbeRefusedError(msg)
            if artifact.size_bytes is not None:
                if artifact.size_bytes > opening.max_bytes:
                    msg = "Receipt output bytes exceed the reviewed profile"
                    raise ProbeRefusedError(msg)
                total += artifact.size_bytes
                self._local_path(current.occurrence_id, index, artifact)
        if total > MAX_OUTPUT_BYTES:
            msg = "Retained artifact bytes exceed the total bound"
            raise ProbeRefusedError(msg)
        if current.state == "succeeded" and set(counts) != {(item.node_id, item.kind) for item in self.profile.outputs}:
            msg = "Receipt is missing required output openings"
            raise ProbeRefusedError(msg)
        return current

    def _local_path(self, occurrence: UUID, index: int, artifact: ComfyArtifact) -> Path:
        if artifact.local_filename is None or artifact.sha256 is None or artifact.size_bytes is None:
            msg = "Fetched artifact metadata is incomplete"
            raise ProbeRefusedError(msg)
        expected = f"{occurrence}-{index}-{artifact.sha256}{Path(artifact.filename).suffix.lower()}"
        if artifact.local_filename != expected:
            msg = "Retained filename is not bound to occurrence, index, digest and extension"
            raise ProbeRefusedError(msg)
        return self.workspace / expected

    def _verify_local(self, occurrence: UUID, index: int, artifact: ComfyArtifact) -> None:
        self._verify_file(self._local_path(occurrence, index, artifact), artifact)

    def _verify_file(self, path: Path, artifact: ComfyArtifact) -> None:
        if artifact.size_bytes is None or artifact.sha256 is None:
            msg = "Fetched artifact metadata is incomplete"
            raise ProbeRefusedError(msg)
        self._fence()
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size != artifact.size_bytes:
                    msg = "Retained artifact is not a regular file with its pinned size"
                    raise ProbeRefusedError(msg)
                digest = hashlib.sha256()
                size = 0
                while chunk := source.read(MAX_JSON_BYTES):
                    size += len(chunk)
                    if size > artifact.size_bytes:
                        msg = "Retained artifact exceeds pinned bytes"
                        raise ProbeRefusedError(msg)
                    digest.update(chunk)
        except OSError as error:
            msg = "Retained artifact is missing or cannot be safely read"
            raise ProbeRefusedError(msg) from error
        if size != artifact.size_bytes or digest.hexdigest() != artifact.sha256:
            msg = "Retained artifact digest or size changed"
            raise ProbeRefusedError(msg)

    def prepare(self, request: ComfyRequest, occurrence_id: UUID | None = None) -> ComfyAttempt:
        prompt = self.profile.prompt(request)
        attempt = ComfyAttempt(
            occurrence_id=occurrence_id or uuid4(),
            profile_sha256=self.profile.digest,
            request_sha256=request.digest,
            inputs_json=request.inputs_json,
            prompt_sha256=json_digest(canonical_json(prompt)),
            state="prepared",
        )
        with self._locked(attempt.occurrence_id) as path:
            if path.exists():
                return self._current(attempt, path)
            self._write(path, attempt)
        return attempt

    def load(self, occurrence_id: UUID) -> ComfyAttempt:
        """Resume the pinned durable occurrence without authorizing another submit."""
        with self._locked(occurrence_id) as path:
            attempt = self._read(path)
            if attempt.occurrence_id != occurrence_id:
                msg = "Receipt occurrence does not match its durable filename"
                raise ProbeRefusedError(msg)
            return self._current(attempt, path)

    def _client(self) -> httpx2.AsyncClient:
        return httpx2.AsyncClient(
            verify=create_http_ssl_context(),
            transport=self.transport,
            timeout=httpx2.Timeout(15.0),
            follow_redirects=False,
            trust_env=False,
            headers={"Accept-Encoding": "identity"},
        )

    async def _json(self, method: str, route: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        async with (
            asyncio.timeout(30),
            self._client() as client,
            client.stream(method, self.profile.endpoint + route, json=payload) as response,
        ):
            response.raise_for_status()
            if response.headers.get("Content-Encoding", "identity") != "identity":
                msg = "Encoded provider response is refused"
                raise ProbeRefusedError(msg)
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > MAX_JSON_BYTES:
                    msg = "Provider JSON exceeds bound"
                    raise ProbeRefusedError(msg)
        value: Any = json.loads(body)
        if not isinstance(value, dict):
            msg = "Provider response is not an object"
            raise ProbeRefusedError(msg)
        return cast("dict[str, Any]", value)

    async def submit(self, attempt: ComfyAttempt) -> ComfyAttempt:
        with self._locked(attempt.occurrence_id) as path:
            current = self._current(attempt, path)
            if current.state != "prepared":
                msg = "This occurrence already crossed the submit fence; reconcile it"
                raise ProbeRefusedError(msg)
            current = current.model_copy(update={"state": "indeterminate"})
            self._write(path, current)
        request = ComfyRequest(profile_sha256=current.profile_sha256, inputs_json=current.inputs_json)
        payload: dict[str, Any] = {
            "prompt": self.profile.prompt(request),
            "client_id": str(current.occurrence_id),
        }
        if self.profile.client_prompt_id_supported:
            payload["prompt_id"] = str(current.occurrence_id)
        try:
            ack = await self._json("POST", "/prompt", payload)
            provider = ack.get("prompt_id")
            if not isinstance(provider, str) or str(UUID(provider)) != provider or ack.get("node_errors"):
                return current
            if self.profile.client_prompt_id_supported and provider != str(current.occurrence_id):
                return current
        except (httpx2.HTTPError, ValueError, TimeoutError):
            return current
        with self._locked(attempt.occurrence_id) as path:
            current = self._current(attempt, path)
            if current.state != "indeterminate":
                return current
            current = current.model_copy(update={"provider_id": provider, "state": "acknowledged"})
            self._write(path, current)
        return current

    def _artifacts(self, outputs: Any) -> tuple[ComfyArtifact, ...]:  # noqa: C901 - hostile descriptor boundary
        if not isinstance(outputs, dict):
            msg = "Malformed output map"
            raise ProbeRefusedError(msg)
        allowed = {(item.node_id, item.kind): item for item in self.profile.outputs}
        artifacts: list[ComfyArtifact] = []
        observed: set[tuple[str, str]] = set()
        for node, raw_kinds in cast("dict[str, Any]", outputs).items():
            kinds = cast("dict[str, Any]", raw_kinds)
            if not isinstance(raw_kinds, dict):
                msg = "Malformed node output"
                raise ProbeRefusedError(msg)
            for kind, descriptors in kinds.items():
                opening = allowed.get((node, kind))
                if (
                    opening is None
                    or not isinstance(descriptors, list)
                    or not descriptors
                    or len(cast("list[Any]", descriptors)) > opening.max_files
                ):
                    msg = "Undeclared output or file count exceeded"
                    raise ProbeRefusedError(msg)
                observed.add((node, kind))
                for raw_descriptor in cast("list[Any]", descriptors):
                    descriptor = cast("dict[str, Any]", raw_descriptor)
                    if not isinstance(raw_descriptor, dict) or set(descriptor) != {
                        "filename",
                        "subfolder",
                        "type",
                    }:
                        msg = "Malformed output descriptor"
                        raise ProbeRefusedError(msg)
                    filename, subfolder, storage = (descriptor[key] for key in ("filename", "subfolder", "type"))
                    if (
                        not isinstance(filename, str)
                        or not isinstance(subfolder, str)
                        or len(subfolder) > MAX_SUBFOLDER_LENGTH
                        or storage not in {"output", "temp"}
                    ):
                        msg = "Invalid output descriptor"
                        raise ProbeRefusedError(msg)
                    safe_component(filename)
                    if subfolder:
                        for component in subfolder.split("/"):
                            safe_component(component)
                    if Path(filename).suffix.lower() not in opening.extensions:
                        msg = "Undeclared output extension"
                        raise ProbeRefusedError(msg)
                    artifacts.append(
                        ComfyArtifact(
                            node_id=node,
                            kind=cast('Literal["audio", "images", "video"]', kind),
                            receiving_owner=opening.receiving_owner,
                            filename=filename,
                            subfolder=subfolder,
                            storage_type=cast('Literal["output", "temp"]', storage),
                        )
                    )
        if observed != set(allowed):
            msg = "Technical success requires every declared output opening"
            raise ProbeRefusedError(msg)
        return tuple(artifacts)

    async def reconcile(self, attempt: ComfyAttempt) -> ComfyAttempt:  # noqa: C901, PLR0912 - one reconciliation boundary
        with self._locked(attempt.occurrence_id) as path:
            current = self._current(attempt, path)
        if current.state == "prepared" or current.state in {"succeeded", "failed"}:
            return current
        provider = current.provider_id
        if provider is None and self.profile.client_prompt_id_supported:
            provider = str(current.occurrence_id)
        history = await self._json("GET", f"/history/{provider}") if provider is not None else {}
        entry: Any = history.get(provider) if provider is not None else None
        updates: dict[str, Any] = {}
        if entry is not None:
            if not isinstance(entry, dict) or not isinstance(cast("dict[str, Any]", entry).get("status"), dict):
                msg = "Malformed history status"
                raise ProbeRefusedError(msg)
            entry = cast("dict[str, Any]", entry)
            prompt: Any = entry.get("prompt")
            if (
                not isinstance(prompt, list)
                or len(cast("list[Any]", prompt)) < MIN_QUEUE_COLUMNS
                or prompt[1] != provider
                or json_digest(canonical_json(prompt[2])) != current.prompt_sha256
            ):
                msg = "History does not match the pinned physical request"
                raise ProbeRefusedError(msg)
            status = cast("dict[str, Any]", entry["status"])
            if status.get("completed") is True and status.get("status_str") == "success":
                updates = {
                    "state": "succeeded",
                    "provider_id": provider,
                    "artifacts": self._artifacts(entry.get("outputs")),
                }
            elif status.get("status_str") == "error":
                updates = {"state": "failed", "provider_id": provider}
        else:
            queue = await self._json("GET", "/queue")
            for key, state in (
                ("queue_running", "running"),
                ("queue_pending", "queued"),
            ):
                rows = queue.get(key)
                if not isinstance(rows, list):
                    msg = "Malformed queue"
                    raise ProbeRefusedError(msg)
                for row in cast("list[Any]", rows):
                    if (
                        provider is not None
                        and isinstance(row, list)
                        and len(cast("list[Any]", row)) >= MIN_QUEUE_COLUMNS
                        and row[1] == provider
                    ):
                        if json_digest(canonical_json(row[2])) != current.prompt_sha256:
                            msg = "Queue identity has a different prompt"
                            raise ProbeRefusedError(msg)
                        updates = {"state": state, "provider_id": provider}
            # Absence preserves prior uncertainty; it never proves no physical effect.
        with self._locked(attempt.occurrence_id) as path:
            current = self._current(attempt, path)
            if current.state not in {"succeeded", "failed"}:
                current = current.model_copy(update=updates)
                self._write(path, current)
        return current

    async def fetch_outputs(self, attempt: ComfyAttempt) -> ComfyAttempt:
        with self._fetch_locked(attempt.occurrence_id):
            return await self._fetch_outputs(attempt)

    @contextmanager
    def _fetch_locked(self, occurrence: UUID) -> Generator[None]:
        self._fence()
        fd = os.open(self.workspace / f"{occurrence}.fetch.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def _stage_path(self, occurrence: UUID, index: int) -> Path:
        return self.workspace / f".comfy-stage-v1-{occurrence}-{index}"

    def _require_pinned_stages(self, attempt: ComfyAttempt) -> None:
        for index, artifact in enumerate(attempt.artifacts):
            stage = self._stage_path(attempt.occurrence_id, index)
            if artifact.local_filename is None and (stage.exists() or stage.is_symlink()):
                msg = "Unpinned staging bytes require manual reconciliation; refetch is forbidden"
                raise ProbeRefusedError(msg)

    def _install_staged(self, occurrence: UUID, index: int, artifact: ComfyArtifact) -> None:
        """Install only exact pinned bytes; preserve conflicting evidence on failure."""
        destination = self._local_path(occurrence, index, artifact)
        stage = self._stage_path(occurrence, index)
        staged = stage.exists() or stage.is_symlink()
        if staged:
            self._verify_file(stage, artifact)
        if destination.exists() or destination.is_symlink():
            self._verify_local(occurrence, index, artifact)
        else:
            if not staged:
                msg = "Retained artifact and its pinned staging bytes are missing"
                raise ProbeRefusedError(msg)
            os.link(stage, destination, follow_symlinks=False)
        # Also settle a prior link whose directory fsync acknowledgement was lost.
        self._sync_workspace()
        self._verify_local(occurrence, index, artifact)
        if staged:
            stage.unlink()
            self._sync_workspace()

    def repair_materialization(self, occurrence_id: UUID) -> ComfyAttempt:
        """Reconcile exact pinned local staging without HTTP or receipt mutation.

        Missing or damaged bytes and pre-pin staging ambiguity remain refusals.
        This repairs file installation, never provider execution or media meaning.
        """
        with self._fetch_locked(occurrence_id), self._locked(occurrence_id) as path:
            attempt = self._read(path)
            if attempt.occurrence_id != occurrence_id:
                msg = "Receipt occurrence does not match its durable filename"
                raise ProbeRefusedError(msg)
            current = self._bound_current(attempt, path)
            if current.state != "succeeded":
                msg = "Materialization repair requires reconciled technical success"
                raise ProbeRefusedError(msg)
            self._require_pinned_stages(current)
            for index, artifact in enumerate(current.artifacts):
                if artifact.local_filename is not None:
                    self._install_staged(occurrence_id, index, artifact)
            return self._current(current, path)

    def _publish_artifact(
        self, attempt: ComfyAttempt, index: int, artifact: ComfyArtifact, temporary: Path, size: int, digest: str
    ) -> None:
        local = f"{attempt.occurrence_id}-{index}-{digest}{Path(artifact.filename).suffix.lower()}"
        destination = self.workspace / local
        if destination.exists() or destination.is_symlink():
            msg = "A new output destination must not already exist"
            raise ProbeRefusedError(msg)
        fetched = ComfyArtifact.model_validate(
            {**artifact.model_dump(), "local_filename": local, "sha256": digest, "size_bytes": size}
        )
        with self._locked(attempt.occurrence_id) as path:
            current = self._current(attempt, path)
            if current.artifacts[index] != artifact:
                msg = "Output descriptor changed before publication"
                raise ProbeRefusedError(msg)
            artifacts = list(current.artifacts)
            artifacts[index] = fetched
            current = current.model_copy(update={"artifacts": tuple(artifacts)})
            # Retain deterministic bytes before pinning the receipt. A pre-pin crash
            # remains ambiguous; a post-pin crash can repair exactly this local stage.
            stage = self._stage_path(attempt.occurrence_id, index)
            os.link(temporary, stage, follow_symlinks=False)
            self._sync_workspace()
            self._write(path, current)
            self._install_staged(attempt.occurrence_id, index, fetched)

    async def _fetch_outputs(self, attempt: ComfyAttempt) -> ComfyAttempt:
        with self._locked(attempt.occurrence_id) as path:
            current = self._current(attempt, path)
        if current.state != "succeeded":
            msg = "Outputs require reconciled technical success"
            raise ProbeRefusedError(msg)
        self._require_pinned_stages(current)
        total = sum(item.size_bytes or 0 for item in current.artifacts)
        for index, artifact in enumerate(current.artifacts):
            if artifact.local_filename is not None:
                continue
            opening = next(
                item for item in self.profile.outputs if (item.node_id, item.kind) == (artifact.node_id, artifact.kind)
            )
            params = {
                "filename": artifact.filename,
                "subfolder": artifact.subfolder,
                "type": artifact.storage_type,
            }
            self._fence()
            fd, temporary = tempfile.mkstemp(dir=self.workspace, prefix=".media-")
            digest = hashlib.sha256()
            size = 0
            try:
                async with (
                    asyncio.timeout(30),
                    self._client() as client,
                    client.stream("GET", self.profile.endpoint + "/view", params=params) as response,
                ):
                    response.raise_for_status()
                    if response.headers.get("Content-Encoding", "identity") != "identity":
                        msg = "Encoded media response is refused"
                        raise ProbeRefusedError(msg)
                    with os.fdopen(fd, "wb") as output:
                        fd = -1
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            total += len(chunk)
                            if size > opening.max_bytes or total > MAX_OUTPUT_BYTES:
                                msg = "Output byte bound exceeded"
                                raise ProbeRefusedError(msg)
                            digest.update(chunk)
                            output.write(chunk)
                        output.flush()
                        os.fsync(output.fileno())
                if size == 0:
                    msg = "Empty output is refused"
                    raise ProbeRefusedError(msg)
                self._publish_artifact(attempt, index, artifact, Path(temporary), size, digest.hexdigest())
            finally:
                if fd >= 0:
                    os.close(fd)
                Path(temporary).unlink(missing_ok=True)  # noqa: ASYNC240 - bounded temporary-file cleanup
        return self.load(attempt.occurrence_id)

    def cancel(self, attempt: ComfyAttempt) -> None:
        with self._locked(attempt.occurrence_id) as path:
            self._current(attempt, path)
        msg = "Targeted cancellation is unproven for this profile; global interruption is forbidden"
        raise ProbeRefusedError(msg)
