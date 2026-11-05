"""Explicit host operator harness for disposable Reach development containers.

This harness exports committed public sources and supervises isolated children.
It never constructs a Core application, Graph, database or inference runtime on
the host. No command installs a service or starts an automatic restart policy.
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import getpass
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable, Generator, Sequence
from contextlib import contextmanager, nullcontext, suppress
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, NoReturn, cast
from uuid import uuid4

from lychd.compositions.reach.documents import (
    LEGACY_MAX_CORPUS_BYTES,
    LEGACY_MAX_DOCUMENTS,
    MAX_CORPUS_BYTES,
    MAX_CORPUS_DOCUMENTS,
    MAX_CORPUS_MANIFEST_BYTES,
    MAX_DOCUMENT_BYTES,
    CorpusManifest,
    decode_public_text,
    public_project_path,
)
from lychd.compositions.reach.operator_diagnostics import diagnostic_bytes, parse_diagnostic, write_diagnostic_line
from lychd.compositions.reach.operator_model_wire import OperatorModelRequest
from lychd.compositions.reach.operator_observation import ReachPatternObservation
from lychd.compositions.reach.operator_trace import ReachTraceEvent, error_code
from lychd.compositions.reach.operator_wire import ReachWorkerReady, ReachWorkerResult
from lychd.compositions.reach.research_wire import (
    OperatorResearchRequest,
    OperatorResearchResponse,
    ReachResearchProgress,
)
from lychd.interface.discord.operator_io import load_policy
from lychd.interface.observation import OperationObservation

if __package__:
    from scripts.reach_model_broker import MODEL_ENDPOINT, OperatorModelBroker, validate_endpoint
    from scripts.reach_observation import ReachObservationPublisher
    from scripts.reach_podman_model import PodmanModelTransport
    from scripts.reach_research_broker import OperatorResearchBroker
    from scripts.reach_trace_archive import TraceArchive
    from scripts.reach_trace_capture import TraceCapture
else:
    from reach_model_broker import MODEL_ENDPOINT, OperatorModelBroker, validate_endpoint
    from reach_observation import ReachObservationPublisher
    from reach_podman_model import PodmanModelTransport
    from reach_research_broker import OperatorResearchBroker
    from reach_trace_archive import TraceArchive
    from reach_trace_capture import TraceCapture

ROOT = Path(__file__).resolve().parents[1]
WIRE_LIMIT = 65_536
DOCUMENT_LIMIT = MAX_DOCUMENT_BYTES
CORPUS_LIMIT = MAX_CORPUS_BYTES
MAX_DOCUMENTS = MAX_CORPUS_DOCUMENTS
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
EDGE_INPUTS = (
    "scripts/generate_python_third_party_notices.py",
    "clients/discord/pyproject.toml",
    "clients/discord/uv.lock",
    "clients/discord/Containerfile",
    "src/lychd/interface/observation.py",
    "src/lychd/interface/http_observation.py",
    "src/lychd/lib/__init__.py",
    "src/lychd/lib/http.py",
    *(
        f"src/lychd/compositions/reach/{name}.py"
        for name in (
            "__init__",
            "schemas",
            "policy",
            "operator_wire",
            "operator_client",
            "operator_diagnostics",
            "operator_trace",
            "conversation_session",
            "expressions",
            "research_wire",
        )
    ),
    *(
        f"src/lychd/interface/discord/{name}.py"
        for name in (
            "__init__",
            "schemas",
            "events",
            "operator_io",
            "live",
            "rest",
            "admin",
            "operator_cli",
            "publications",
            "onboarding",
            "messages",
            "history",
            "followups",
        )
    ),
)


def _fail(code: str) -> NoReturn:
    raise ValueError(code)


def external_path(path: Path) -> Path:
    """Refuse relative paths, symlink ancestors and every containing Git checkout."""
    if (
        not path.is_absolute()
        or any(part in {".", ".."} for part in path.parts)
        or any(char in str(path) for char in ":,\r\n")
    ):
        _fail("operator_path")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            _fail("operator_symlink")
        if current.exists() and current.is_dir() and (current / ".git").exists():
            _fail("operator_checkout")
    for parent in (path, *path.parents):
        if (parent / ".git").exists():
            _fail("operator_checkout")
    return path


def private_directory(path: Path) -> Path:
    """Create missing ancestors privately and require the final directory to be owner-only."""
    external_path(path)
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for item in reversed(missing):
        item.mkdir(mode=0o700)
    metadata = path.stat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        _fail("operator_directory_permissions")
    return path


def read_regular(path: Path, limit: int, *, private: bool = False) -> bytes:
    """Read only an explicitly selected regular, bounded, non-symlink file."""
    external_path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or (
            private and (metadata.st_uid != os.getuid() or metadata.st_mode & 0o077)
        ):
            _fail("operator_file_permissions")
        raw = source.read(limit + 1)
    if len(raw) > limit:
        _fail("operator_file_limit")
    return raw


def write_private(path: Path, raw: bytes) -> None:
    """Publish a complete owner-only file without replacing any existing path."""
    external_path(path)
    private_directory(path.parent)
    temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, path, follow_symlinks=False)
    finally:
        temporary.unlink(missing_ok=True)


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode() + b"\n"


def strict_object(raw: bytes) -> dict[str, Any]:
    """Do not let duplicate manifest keys or nonfinite JSON become operator authority."""

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                _fail("operator_duplicate_key")
            result[key] = value
        return result

    def constant(_value: str) -> Any:
        _fail("operator_json")

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        _fail("operator_json")
    return cast("dict[str, Any]", value)


def token_file(path: Path) -> None:
    """Acquire a credential exclusively from the local terminal, never argv or environment."""
    external_path(path)
    if path.exists():
        _fail("operator_file_exists")
    token = getpass.getpass("Discord bot token (local terminal only): ")
    if re.fullmatch(r"[A-Za-z0-9_.-]{20,512}", token) is None:
        _fail("credential_shape")
    write_private(path, token.encode("ascii"))


def safe_environment(engine: str) -> dict[str, str]:
    """Keep normal host engine discovery while excluding project and provider credentials."""
    permitted = (
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "LANG",
        "LC_ALL",
        "XDG_RUNTIME_DIR",
        "XDG_CONFIG_HOME",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_CONFIG",
        "DOCKER_BUILDKIT",
        "CONTAINER_HOST",
        "CONTAINERS_CONF",
        "REGISTRY_AUTH_FILE",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
    )
    result = {name: os.environ[name] for name in permitted if name in os.environ}
    result["LYCHD_TEST_ENGINE"] = engine
    result["LYCHD_TEST_PYTHON"] = "3.15.0"
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    return result


def command(
    arguments: Sequence[str],
    *,
    root: Path = ROOT,
    engine: str = "podman",
    limit: int = WIRE_LIMIT,
    capture: bool = True,
    accepted_exit_codes: tuple[int, ...] = (0,),
) -> bytes:
    """Run a fixed tool, admitting only explicit exit codes and bounded captured output."""
    with tempfile.TemporaryFile() as output:
        completed = subprocess.run(  # noqa: S603 - closed git/OCI argv assembled by this trusted host harness
            list(arguments),
            cwd=root,
            env=safe_environment(engine),
            stdout=output,
            stderr=subprocess.DEVNULL,
            timeout=1800,
            check=False,
        )
        if completed.returncode not in accepted_exit_codes:
            _fail("operator_command_failed")
        if not capture:
            return b""
        output.seek(0)
        raw = output.read(limit + 1)
    if len(raw) > limit:
        _fail("operator_command_output")
    return raw


def _corpus_tree(root: Path, revision: str) -> dict[str, tuple[str, str, int]]:
    """Inspect immutable Git modes and sizes without following checkout links or reading files."""
    raw = command(
        ["git", "ls-tree", "--full-tree", "-r", "-z", "-l", revision], root=root, limit=MAX_CORPUS_MANIFEST_BYTES
    )
    result: dict[str, tuple[str, str, int]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, separator, path_raw = record.partition(b"\t")
        fields = metadata.decode("ascii").split()
        if not separator or len(fields) != 4:  # noqa: PLR2004 - fixed Git tree record grammar
            _fail("corpus_tree")
        mode, kind, _object_id, size = fields
        path = path_raw.decode("utf-8", errors="strict")
        result[path] = (mode, kind, int(size) if size != "-" else -1)
    return result


def _corpus_paths(root: Path, tree: dict[str, tuple[str, str, int]], *, project_files: bool) -> list[str]:
    if project_files:
        paths = sorted(path for path in tree if public_project_path(path))
        limit = MAX_DOCUMENTS
    else:
        catalogue = (root / "examples/reach/public-docs.txt").read_text(encoding="utf-8").splitlines()
        paths = [line.strip() for line in catalogue if line.strip() and not line.lstrip().startswith("#")]
        limit = LEGACY_MAX_DOCUMENTS
        if any(
            re.fullmatch(r"(?:README\.md|CONTRIBUTING\.md|docs/[A-Za-z0-9_./-]+\.md)", path) is None
            or not public_project_path(path)
            for path in paths
        ):
            _fail("corpus_catalogue")
    if not 1 <= len(paths) <= limit or len(paths) != len(set(paths)):
        _fail("corpus_catalogue")
    if any(path not in tree or tree[path][0] not in {"100644", "100755"} or tree[path][1] != "blob" for path in paths):
        _fail("corpus_git_mode")
    return paths


def _corpus_source(
    root: Path, revision: str, path: str, size: int, *, project_files: bool
) -> tuple[bytes, Literal["document_limit", "not_text"] | None]:
    """Read one pinned text blob or record its explicit project-profile omission."""
    if project_files and size > DOCUMENT_LIMIT:
        return b"", "document_limit"
    raw = command(["git", "show", f"{revision}:{path}"], root=root, limit=DOCUMENT_LIMIT)
    try:
        decode_public_text(raw)
    except ValueError:
        if not project_files:
            raise
        return b"", "not_text"
    return raw, None


def export_corpus(output: Path, revision: str = "HEAD", *, root: Path = ROOT, project_files: bool = False) -> str:
    """Export pinned public blobs, with whole-project text explicitly selected by the operator.

    The default retains the small documentation catalogue. The project profile
    records oversize/non-text omissions, refuses symlinks and aggregate overflow,
    and never reads dirty, ignored or untracked project files. Neither export
    contains Git metadata, a directory tree, or executable filesystem authority.
    """
    external_path(output)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        _fail("corpus_output_exists")
    resolved = (
        command(["git", "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}"], root=root)
        .decode("ascii")
        .strip()
    )
    if re.fullmatch(r"[0-9a-f]{40}", resolved) is None:
        _fail("corpus_revision")
    tree = _corpus_tree(root, resolved)
    paths = _corpus_paths(root, tree, project_files=project_files)
    documents: list[dict[str, str]] = []
    omissions: list[dict[str, str]] = []
    contents: list[bytes] = []
    total = 0
    for path in paths:
        raw, omission = _corpus_source(root, resolved, path, tree[path][2], project_files=project_files)
        if omission is not None:
            omissions.append({"path": path, "reason": omission})
            continue
        total += len(raw)
        if total > (CORPUS_LIMIT if project_files else LEGACY_MAX_CORPUS_BYTES):
            _fail("corpus_limit")
        index = len(documents)
        contents.append(raw)
        documents.append(
            {
                "path": path,
                "url": f"https://github.com/hexanomicon/lychd/blob/{resolved}/{path}",
                "sha256": sha256(raw).hexdigest(),
                "file": f"{index:04}.txt" if project_files else f"{index:03}.md",
            }
        )
    manifest = CorpusManifest.model_validate(
        {
            "schema_version": 2 if project_files else 1,
            "source_revision": resolved,
            "documents": tuple(documents),
            "omissions": tuple(omissions),
        }
    )
    manifest_value = manifest.model_dump(mode="json")
    if not project_files:
        manifest_value.pop("omissions")
    manifest_raw = json_bytes(manifest_value)
    if len(manifest_raw) > MAX_CORPUS_MANIFEST_BYTES:
        _fail("corpus_manifest_limit")
    private_directory(output)
    # The manifest is published last; an interrupted export is never admissible.
    for document, raw in zip(documents, contents, strict=True):
        write_private(output / document["file"], raw)
    write_private(output / "manifest.json", manifest_raw)
    return resolved


def load_images(path: Path) -> dict[str, str]:
    record = strict_object(read_regular(path, WIRE_LIMIT, private=True))
    if (
        set(record) != {"schema_version", "core", "edge"}
        or type(record["schema_version"]) is not int
        or record["schema_version"] != 1
    ):
        _fail("operator_images")
    if any(not isinstance(record[name], str) or IMAGE_ID.fullmatch(record[name]) is None for name in ("core", "edge")):
        _fail("operator_images")
    return {"core": record["core"], "edge": record["edge"]}


def _retain_image(engine: str, role: Literal["core", "edge"], identity: str, *, root: Path) -> None:
    """Keep the selected image addressable when a later build replaces its build tag."""
    if IMAGE_ID.fullmatch(identity) is None:
        _fail("operator_image_identity")
    tag = f"localhost/lychd-reach-{role}:{identity.removeprefix('sha256:')}"
    command([engine, "image", "tag", identity, tag], root=root, engine=engine, capture=False)
    observed = (
        command(
            [engine, "image", "inspect", "--format", "{{.Id}}", tag],
            root=root,
            engine=engine,
        )
        .decode("ascii")
        .strip()
    )
    if observed != identity:
        _fail("operator_image_retention")


def build_images(engine: str, output: Path, *, root: Path = ROOT) -> None:
    """Build, retain and import-check exact images before publishing their record.

    The shared Core build tag requires sequential invocations. The edge import
    check has no credentials, host mounts or network access.
    """
    external_path(output)
    if output.exists():
        _fail("operator_file_exists")
    command(["bash", "scripts/container_checks.sh", "--build-only"], root=root, engine=engine, capture=False)
    core = (
        command(
            [engine, "image", "inspect", "--format", "{{.Id}}", "localhost/lychd-checks:python-3.15.0"],
            root=root,
            engine=engine,
        )
        .decode()
        .strip()
    )
    if IMAGE_ID.fullmatch(core) is None:
        _fail("operator_image_identity")
    _retain_image(engine, "core", core, root=root)
    with tempfile.TemporaryDirectory(prefix="lychd-reach-edge-") as temporary:
        context = Path(temporary)
        for relative in EDGE_INPUTS:
            source, target = root / relative, context / relative
            if source.is_symlink() or not source.is_file():
                _fail("operator_build_input")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        (context / ".dockerignore").write_text("")
        (context / ".containerignore.build").write_text("")
        iidfile = context / "image.id"
        build = [engine, "build", "--file", str(context / "clients/discord/Containerfile"), "--iidfile", str(iidfile)]
        if engine == "podman":
            build += [
                "--ignorefile",
                str(context / ".containerignore.build"),
                "--memory",
                "4g",
                "--cpu-period",
                "100000",
                "--cpu-quota",
                "200000",
            ]
        elif os.environ.get("DOCKER_BUILDKIT", "1") == "0":
            build += ["--memory", "4g", "--cpu-period", "100000", "--cpu-quota", "200000"]
        else:
            build += ["--resource", "memory=4g", "--resource", "cpu-period=100000", "--resource", "cpu-quota=200000"]
        command([*build, str(context)], root=root, engine=engine, capture=False)
        edge = iidfile.read_text().strip()
        if re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", edge) is None:
            _fail("operator_image_identity")
        edge = edge if edge.startswith("sha256:") else f"sha256:{edge}"
        _retain_image(engine, "edge", edge, root=root)
        smoke = container_arguments(engine, edge, context / "smoke.cid", offline=True)
        command(
            [
                *smoke,
                "--rm",
                "--entrypoint",
                "python",
                edge,
                "-c",
                (
                    "import signal; signal.alarm(30); "
                    "import lychd.interface.discord.live; import lychd.interface.discord.operator_cli"
                ),
            ],
            root=root,
            engine=engine,
            capture=False,
        )
    write_private(output, json_bytes({"schema_version": 1, "core": core, "edge": edge}))


@contextmanager
def instance_lock(state: Path) -> Generator[None]:
    """One owner holds the state partition; lock custody never grants a child host control."""
    private_directory(state)
    descriptor = os.open(state / "operator.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            _fail("operator_lock")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def container_arguments(engine: str, image: str, cidfile: Path, *, offline: bool) -> list[str]:
    """Build a closed boundary without published ports or inherited environment."""
    if IMAGE_ID.fullmatch(image) is None:
        _fail("operator_image_identity")
    result = [
        engine,
        "run",
        "--pull=never",
        "--interactive",
        "--cidfile",
        str(cidfile),
        "--read-only",
        "--log-driver=none",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit",
        "128",
        "--memory",
        "1g",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=256m",  # noqa: S108 - isolated, size-limited container tmpfs
        "--user",
        f"{os.getuid()}:{os.getgid()}",
    ]
    if engine == "podman":
        result += ["--userns=keep-id"]
    if offline:
        result += ["--network=none"]
    return result


def bind(source: Path, destination: str, *, readonly: bool = True) -> list[str]:
    external_path(source)
    return ["--volume", f"{source}:{destination}:{'ro' if readonly else 'rw'},Z"]


def capture_descriptors(value: dict[str, Any], raw: bytes, capture: TraceCapture | None) -> bool:
    """Consume only a bounded Core inspection frame without forwarding it to the edge."""
    if value.get("kind") != "reach_pattern_observation":
        return False
    with suppress(ValueError, TypeError):
        declaration = ReachPatternObservation.model_validate_json(raw)
        if capture is not None:
            capture.descriptors(declaration)
    return True


def capture_worker_frame(value: dict[str, Any], raw: bytes, capture: TraceCapture | None) -> None:
    """Record a native worker's typed control frame without changing forwarding."""
    if capture is None:
        return
    if value.get("kind") == "ready":
        capture.ready(ReachWorkerReady.model_validate_json(raw))
    elif value.get("kind") == "result":
        capture.result(ReachWorkerResult.model_validate_json(raw))


async def relay(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    *,
    requests_only: bool = False,
    capture: TraceCapture | None = None,
) -> None:
    """Forward bounded objects; the conversation edge may submit only typed worker requests."""
    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except asyncio.IncompleteReadError as error:
            if error.partial:
                _fail("operator_truncated_frame")
            return
        if len(raw) > WIRE_LIMIT:
            _fail("operator_frame_limit")
        value = strict_object(raw)
        if not requests_only and capture_descriptors(value, raw, capture):
            continue
        if requests_only:
            from lychd.compositions.reach.operator_wire import parse_request_line

            request = parse_request_line(raw)
            if capture is not None:
                capture.request(request)
        else:
            capture_worker_frame(value, raw, capture)
        writer.write(raw)
        await writer.drain()


def authorize_research_synthesis(payload: str, broker: OperatorResearchBroker) -> Callable[[], None] | None:
    """Bind the source envelope to one issued, currently authorized local consumption."""
    generation = strict_object(payload.encode())
    messages = generation.get("messages")
    prompt: dict[str, Any] = {}
    if isinstance(messages, list) and messages:
        last: Any = cast("list[Any]", messages)[-1]
        if isinstance(last, dict):
            content = cast("dict[str, Any]", last).get("content")
            if isinstance(content, str):
                with suppress(ValueError):
                    prompt = strict_object(content.encode())
    if prompt.get("research_phase") == "synthesis":
        return broker.authorize_consume(str(prompt.get("research_request_id", "")))
    if broker.material_pending:
        _fail("research_consume_binding")
    return None


async def model_relay(  # noqa: C901 - closed readiness/result/model/research wire branches
    reader: asyncio.StreamReader,
    edge_writer: asyncio.StreamWriter,
    core_writer: asyncio.StreamWriter,
    broker: OperatorModelBroker,
    research_broker: OperatorResearchBroker | None = None,
    capture: TraceCapture | None = None,
) -> None:
    """Keep model frames on the trusted host pipe and expose only public results."""

    async def progress(value: ReachResearchProgress) -> None:
        edge_writer.write(value.model_dump_json().encode() + b"\n")
        await edge_writer.drain()

    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except asyncio.IncompleteReadError as error:
            if error.partial:
                _fail("operator_truncated_frame")
            return
        if len(raw) > WIRE_LIMIT:
            _fail("operator_frame_limit")
        value = strict_object(raw)
        if capture_descriptors(value, raw, capture):
            continue
        if value.get("kind") in {"ready", "result"}:
            capture_worker_frame(value, raw, capture)
            if value.get("kind") == "result" and research_broker is not None:
                research_broker.settled(str(value.get("request_id", "")))
            edge_writer.write(raw)
            await edge_writer.drain()
        elif value.get("kind") == "model_request":
            request = OperatorModelRequest.model_validate_json(raw)
            response = await handle_model_request(broker, request, research_broker)
            await write_core_response(core_writer, response)
        elif value.get("kind") == "research_request" and research_broker is not None:
            research_request = OperatorResearchRequest.model_validate_json(raw)
            research_response = await handle_research_request(research_request, research_broker, progress, capture)
            await write_core_response(core_writer, research_response.model_dump_json())
        else:
            _fail("operator_core_frame")


async def handle_research_request(
    request: OperatorResearchRequest,
    broker: OperatorResearchBroker,
    progress: Callable[[ReachResearchProgress], Awaitable[None]],
    capture: TraceCapture | None,
) -> OperatorResearchResponse:
    """Observe the bounded acquisition handoff without retaining its material."""
    binding = request.correlation.model_dump(exclude_none=True) if request.correlation else {}
    started = time.monotonic()
    if capture is not None:
        capture.host.record("research_call", status="started", call_id=request.call_id, **binding)
    try:
        response = await broker.handle(request, progress)
    except (Exception, asyncio.CancelledError) as error:
        if capture is not None:
            capture.host.record(
                "research_call",
                status="cancelled" if isinstance(error, asyncio.CancelledError) else "error",
                code=error_code(error),
                call_id=request.call_id,
                duration_ms=min(86_400_000, int((time.monotonic() - started) * 1000)),
                **binding,
            )
        raise
    if capture is not None:
        capture.host.record(
            "research_call",
            status=response.status,
            call_id=request.call_id,
            duration_ms=min(86_400_000, int((time.monotonic() - started) * 1000)),
            **binding,
        )
        for source in response.sources:
            capture.host.record(
                "source_read",
                status=source.status,
                source_id=source.id,
                call_id=request.call_id,
                http_status=source.http_status,
                chars=len(source.text),
                truncated=source.truncated,
                code="fetch_protocol"
                if source.reason == "fetch_protocol"
                else "source_unavailable"
                if source.status != "ok"
                else None,
                **binding,
            )
    return response


async def handle_model_request(
    broker: OperatorModelBroker, request: OperatorModelRequest, research_broker: OperatorResearchBroker | None
) -> str:
    """Issue the local consumption guard only for the pending research synthesis."""
    authorize = None
    if research_broker is not None and request.operation == "generate":
        authorize = authorize_research_synthesis(request.payload_json, research_broker)
    response = (
        await broker.handle(request, authorize=authorize) if authorize is not None else await broker.handle(request)
    )
    return response.model_dump_json()


async def write_core_response(writer: asyncio.StreamWriter, response: str) -> None:
    """Keep every host response within the same bounded Core pipe dialect."""
    encoded = response.encode() + b"\n"
    if len(encoded) > WIRE_LIMIT:
        _fail("operator_frame_limit")
    writer.write(encoded)
    await writer.drain()


async def research_edge_relay(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    broker: OperatorResearchBroker,
    capture: TraceCapture | None = None,
) -> None:
    """Consume exact progress acknowledgements and forward only normalized requests."""
    from lychd.compositions.reach.operator_wire import parse_request_line
    from lychd.compositions.reach.research_wire import ReachResearchAcknowledgement

    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except asyncio.IncompleteReadError as error:
            if error.partial:
                _fail("operator_truncated_frame")
            return
        if len(raw) > WIRE_LIMIT:
            _fail("operator_frame_limit")
        value = strict_object(raw)
        if value.get("kind") == "progress_ack":
            broker.acknowledge(ReachResearchAcknowledgement.model_validate_json(raw))
        else:
            request = parse_request_line(raw)
            if capture is not None:
                capture.request(request)
            writer.write(raw)
            await writer.drain()


def capture_structured(raw: bytes, role: str, capture: TraceCapture) -> bool:
    """Validate one closed child record and pass its actual pipe role to custody checks."""
    try:
        value = strict_object(raw)
        if value.get("kind") == "operation_observation":
            capture.operation(OperationObservation.model_validate_json(raw), role)
            return True
        if value.get("kind") == "reach_trace":
            event = ReachTraceEvent.model_validate_json(raw)
            if event.producer == role:
                capture.child(event, role)
                return True
    except (ValueError, UnicodeError, RecursionError):
        return False
    return False


async def diagnostics(  # noqa: C901 - role custody, legacy diagnostics and closed readiness codes
    reader: asyncio.StreamReader,
    *,
    role: Literal["core", "edge"] = "edge",
    capture: TraceCapture | None = None,
) -> None:
    """Admit closed Core observations and fixed codes; reject foreign diagnostic bodies."""
    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            return
        if capture is not None and raw.startswith(b"{") and capture_structured(raw, role, capture):
            continue
        if role == "core" and raw.startswith(b"{"):
            try:
                record = parse_diagnostic(raw)
            except (ValueError, UnicodeError, RecursionError):
                pass
            else:
                write_diagnostic_line(diagnostic_bytes(record))
                continue
        try:
            code = raw.decode("ascii").strip()
        except UnicodeError:
            code = ""
        admitted = code if re.fullmatch(r"(?:reach_discord:)?[a-z][a-z0-9_]{0,63}", code) else "reach_child_diagnostic"
        if capture is not None:
            if role == "edge" and admitted in {
                "reach_discord:ready",
                "reach_discord:connecting",
                "reach_discord:disconnected",
            }:
                capture.host.record(
                    "gateway",
                    status="ok"
                    if admitted.endswith(":ready")
                    else "started"
                    if admitted.endswith(":connecting")
                    else "unavailable",
                    generation=capture.generation,
                )
            elif admitted == "reach_child_diagnostic" or admitted.endswith("_failed"):
                capture.host.record(
                    "child_diagnostic", status="error", code="protocol_error", generation=capture.generation
                )
        write_diagnostic_line((admitted + "\n").encode("ascii"))


async def retire(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), 5)
        except TimeoutError:
            process.kill()
            await process.wait()


async def remove_owned(engine: str, cidfile: Path) -> None:
    """Remove only a validated exact identity emitted by this invocation's engine."""
    if not await asyncio.to_thread(cidfile.exists):
        return
    identity = (await asyncio.to_thread(read_regular, cidfile, 128)).decode("ascii").strip()
    if CONTAINER_ID.fullmatch(identity) is None:
        _fail("operator_container_identity")
    process = await asyncio.create_subprocess_exec(
        engine,
        "rm",
        "--force",
        identity,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        env=safe_environment(engine),
    )
    try:
        result = await asyncio.wait_for(process.wait(), 15)
    except TimeoutError:
        await retire(process)
        _fail("operator_cleanup_failed")
    if result:
        _fail("operator_cleanup_failed")


async def supervise(  # noqa: C901, PLR0912 - explicit two-child settlement and exact-ID cleanup
    engine: str,
    commands: tuple[list[str], list[str]],
    cidfiles: tuple[Path, Path],
    *,
    broker: OperatorModelBroker | None = None,
    research_broker: OperatorResearchBroker | None = None,
    capture: TraceCapture | None = None,
) -> int:
    """First EOF, child failure or signal retires both processes and exact owned containers."""
    children: list[asyncio.subprocess.Process] = []
    tasks: list[asyncio.Task[Any]] = []
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stopped.set)
    status = 1
    heartbeat = asyncio.create_task(capture.heartbeat()) if capture is not None else None
    try:
        for arguments in commands:
            children.append(  # noqa: PERF401 - sequential spawn retains first child if the second fails
                await asyncio.create_subprocess_exec(
                    *arguments,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    limit=WIRE_LIMIT,
                    env=safe_environment(engine),
                )
            )
        core, edge = children
        if (
            core.stdout is None
            or core.stdin is None
            or edge.stdout is None
            or edge.stdin is None
            or core.stderr is None
            or edge.stderr is None
        ):
            _fail("operator_child_pipe")
        tasks = [
            asyncio.create_task(
                relay(core.stdout, edge.stdin, capture=capture)
                if broker is None
                else model_relay(core.stdout, edge.stdin, core.stdin, broker, research_broker, capture)
            ),
            asyncio.create_task(
                relay(edge.stdout, core.stdin, requests_only=True, capture=capture)
                if research_broker is None
                else research_edge_relay(edge.stdout, core.stdin, research_broker, capture)
            ),
            asyncio.create_task(core.wait()),
            asyncio.create_task(edge.wait()),
            asyncio.create_task(stopped.wait()),
        ]
        diagnostic_tasks = [
            asyncio.create_task(diagnostics(core.stderr, role="core", capture=capture)),
            asyncio.create_task(diagnostics(edge.stderr, role="edge", capture=capture)),
        ]
        tasks.extend(diagnostic_tasks)
        done, _ = await asyncio.wait(tasks[:5], return_when=asyncio.FIRST_COMPLETED)
        if stopped.is_set():
            status = 130
        else:
            for task in done:
                value = task.result()
                if type(value) is int:
                    status = value if value >= 0 else 128 - value
    finally:
        if heartbeat is not None:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
        for task in tasks[:5]:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks[:5], return_exceptions=True)
        for child in children:
            await retire(child)
        try:
            async with asyncio.timeout(2):
                await asyncio.gather(*tasks[5:], return_exceptions=True)
        except TimeoutError:
            for task in tasks[5:]:
                task.cancel()
            await asyncio.gather(*tasks[5:], return_exceptions=True)
        if capture is not None:
            capture.close(status)
        errors: list[OSError | ValueError] = []
        for cidfile in cidfiles:
            try:
                await remove_owned(engine, cidfile)
            except (OSError, ValueError) as error:
                errors.append(error)
        for signum in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(signum)
        if errors:
            _fail("operator_cleanup_failed")
    return status


def select_operator_files(args: argparse.Namespace) -> tuple[dict[str, str], Path]:
    for path in (args.policy, args.token_file, args.state_dir, args.images):
        external_path(path)
    descriptor = os.open(args.token_file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            _fail("credential_permissions")
    finally:
        os.close(descriptor)
    private_directory(args.state_dir)
    effects = private_directory(args.state_dir / "effects")
    return load_images(args.images), effects


@contextmanager
def generation_workspace(state: Path, prefix: str) -> Generator[Path]:
    """Retain exact cid evidence when child retirement or cleanup cannot settle."""
    directory = Path(tempfile.mkdtemp(prefix=prefix, dir=state))
    try:
        yield directory
    except BaseException:
        print("reach_operator_scratch_retained", file=sys.stderr)  # noqa: T201 - fixed code, no input disclosure
        raise
    else:
        shutil.rmtree(directory)


def run_containers(args: argparse.Namespace) -> int:  # noqa: C901, PLR0912, PLR0915 - explicit frozen container assembly
    """Freeze selected inputs and join exactly one native/edge process generation."""
    images, effects = select_operator_files(args)
    external_path(args.corpus_dir)
    if not args.corpus_dir.is_dir() or not (args.corpus_dir / "manifest.json").is_file():
        _fail("corpus_missing")
    policy = load_policy(args.policy)
    if bool(policy.context_message_limit) != args.history:
        _fail("history_policy_flag_mismatch")
    if re.fullmatch(r"[a-z][a-z0-9_]{0,31}", args.command_name) is None:
        _fail("operator_command_name")
    profile = None
    if args.conversation_profile is not None:
        from lychd.compositions.reach.operator_model_wire import OperatorConversationProfile

        profile_raw = read_regular(args.conversation_profile, WIRE_LIMIT, private=True)
        strict_object(profile_raw)
        profile = OperatorConversationProfile.model_validate_json(profile_raw)
    if (policy.allowed_reply_channel_ids or policy.allowed_adjacent_followup_channel_ids) and (
        profile is None or not profile.adaptive_context or not args.history
    ):
        _fail("operator_followup_configuration")
    research_broker = None
    if profile is not None and profile.research.enabled:
        if (
            args.engine != "docker"
            or args.model_transport != "podman"
            or not all((args.research_profile, args.research_state_dir, args.research_image))
        ):
            _fail("operator_research_configuration")
        research_broker = OperatorResearchBroker(
            profile,
            policy.to_reach_policy(),
            runtime_profile_path=args.research_profile,
            state_dir=args.research_state_dir,
            image=args.research_image,
        )
    elif any((args.research_profile, args.research_state_dir, args.research_image)):
        _fail("operator_research_configuration")
    onboarding_raw = None
    if args.onboarding_profile is not None:
        onboarding_raw = read_regular(args.onboarding_profile, 4096, private=True)
        strict_object(onboarding_raw)
    validate_endpoint(args.model_endpoint)
    publications = None
    if args.publications_dir is not None:
        publications = private_directory(args.publications_dir)
        if not args.publication_channel:
            _fail("operator_publication_channel")
    elif args.publication_channel:
        _fail("operator_publication_directory")
    for identity in args.publication_channel:
        if re.fullmatch(r"[1-9][0-9]{0,19}", identity) is None:
            _fail("operator_publication_channel")
    with (
        instance_lock(args.state_dir),
        generation_workspace(args.state_dir, "generation-") as temporary,
        TraceArchive(args.state_dir / "traces") as archive,
        (
            ReachObservationPublisher(args.observation_dir, model=profile is not None)
            if args.observation_dir is not None
            else nullcontext()
        ) as observation,
    ):
        corpus_manifest = strict_object(read_regular(args.corpus_dir / "manifest.json", MAX_CORPUS_MANIFEST_BYTES))
        document_ids = frozenset(f"doc:{item['path']}" for item in corpus_manifest.get("documents", []))
        web_ids: frozenset[str] = (
            frozenset(f"web:{item.id}" for item in profile.research.sources) if profile is not None else frozenset()
        )
        capture = TraceCapture(archive.emit, source_ids=document_ids | web_ids, observation=observation)
        generation = Path(temporary)
        generic = generation / "policy.json"
        write_private(generic, policy.to_reach_policy().model_dump_json().encode())
        edge_policy = generation / "edge-policy.toml"
        write_private(edge_policy, read_regular(args.policy, WIRE_LIMIT))
        if load_policy(edge_policy).digest != policy.digest:
            _fail("operator_policy_changed")
        core_cid, edge_cid = generation / "core.cid", generation / "edge.cid"
        core = container_arguments(args.engine, images["core"], core_cid, offline=True)
        core += bind(generic, "/run/reach/policy.json") + bind(args.corpus_dir, "/run/reach/corpus")
        if profile is not None:
            frozen_profile = generation / "conversation.json"
            write_private(frozen_profile, profile.model_dump_json().encode())
            core += bind(frozen_profile, "/run/reach/conversation.json")
        core += [
            "--entrypoint",
            "python",
            images["core"],
            "/work/scripts/reach_worker.py",
            "--policy",
            "/run/reach/policy.json",
            "--corpus-dir",
            "/run/reach/corpus",
        ]
        if profile is not None:
            core += ["--conversation-profile", "/run/reach/conversation.json"]
        edge = container_arguments(args.engine, images["edge"], edge_cid, offline=False)
        edge += (
            bind(edge_policy, "/run/reach/policy.toml")
            + bind(args.token_file, "/run/secrets/discord-token")
            + bind(effects, "/state/effects", readonly=False)
        )
        if publications is not None:
            edge += bind(publications, "/state/publications", readonly=False)
        if onboarding_raw is not None:
            frozen_onboarding = generation / "onboarding.json"
            write_private(frozen_onboarding, onboarding_raw)
            edge += bind(frozen_onboarding, "/run/reach/onboarding.json")
        edge += [
            images["edge"],
            "--policy",
            "/run/reach/policy.toml",
            "--token-file",
            "/run/secrets/discord-token",
            "--effects-dir",
            "/state/effects",
            "--command-name",
            args.command_name,
        ]
        if onboarding_raw is not None:
            edge += ["--onboarding-profile", "/run/reach/onboarding.json"]
        if args.sync_commands:
            edge.append("--sync-commands")
        if args.history:
            edge.append("--history")
        if profile is not None:
            edge.append("--conversation")
        if publications is not None:
            edge += ["--publications-dir", "/state/publications"]
            for identity in args.publication_channel:
                edge += ["--publication-channel", identity]
        for identity in args.admin_user:
            if re.fullmatch(r"[1-9][0-9]{0,19}", identity) is None:
                _fail("operator_admin_identity")
            edge += ["--admin-user", identity]
        if profile is not None:
            return asyncio.run(
                supervise(
                    args.engine,
                    (core, edge),
                    (core_cid, edge_cid),
                    broker=OperatorModelBroker(
                        profile,
                        endpoint=args.model_endpoint,
                        transport=PodmanModelTransport() if args.model_transport == "podman" else None,
                        trace=capture.host,
                    ),
                    research_broker=research_broker,
                    capture=capture,
                )
            )
        return asyncio.run(supervise(args.engine, (core, edge), (core_cid, edge_cid), capture=capture))


def admin_containers(args: argparse.Namespace) -> int:
    images, effects = select_operator_files(args)
    with instance_lock(args.state_dir), generation_workspace(args.state_dir, "admin-") as temporary:
        cidfile = Path(temporary) / "edge.cid"
        arguments = container_arguments(args.engine, images["edge"], cidfile, offline=False)
        arguments += (
            bind(args.policy, "/run/reach/policy.toml")
            + bind(args.token_file, "/run/secrets/discord-token")
            + bind(effects, "/state/effects", readonly=False)
        )
        if args.operation == "admin-apply":
            read_regular(args.plan, WIRE_LIMIT, private=True)
            if re.fullmatch(r"[0-9a-f]{64}", args.expect_digest) is None:
                _fail("operator_plan_digest")
            arguments += bind(args.plan, "/run/reach/plan.json")
        arguments += [
            "--entrypoint",
            "python",
            images["edge"],
            "-m",
            "lychd.interface.discord.operator_cli",
            "--policy",
            "/run/reach/policy.toml",
            "--token-file",
            "/run/secrets/discord-token",
            "--effects-dir",
            "/state/effects",
        ]
        if args.operation == "admin-plan":
            external_path(args.output)
            if args.output.exists():
                _fail("operator_file_exists")
            if re.fullmatch(r"[1-9][0-9]{0,19}", args.owner_id) is None:
                _fail("operator_admin_identity")
            arguments += ["plan", "--owner-id", args.owner_id]
        else:
            arguments += ["apply", "--plan", "/run/reach/plan.json", "--expect-digest", args.expect_digest]
        try:
            accepted = (0, 2) if args.operation == "admin-apply" else (0,)
            result = strict_object(command(arguments, engine=args.engine, accepted_exit_codes=accepted))
            if args.operation == "admin-plan":
                if (
                    set(result) != {"plan", "digest"}
                    or not isinstance(result["plan"], dict)
                    or re.fullmatch(r"[0-9a-f]{64}", str(result["digest"])) is None
                ):
                    _fail("operator_plan")
                write_private(args.output, json_bytes(result))
                print(json.dumps({"digest": result["digest"], "path": str(args.output)}))  # noqa: T201
            else:
                print(json.dumps(result))  # noqa: T201 - bounded explicit operator summary
        finally:
            asyncio.run(remove_owned(args.engine, cidfile))
    return 2 if result.get("status") in {"unknown", "rejected"} else 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subcommands = result.add_subparsers(dest="operation", required=True)
    token = subcommands.add_parser("token")
    token.add_argument("--file", required=True, type=Path)
    export = subcommands.add_parser("export-corpus")
    export.add_argument("--output", required=True, type=Path)
    export.add_argument("--revision", default="HEAD")
    export.add_argument(
        "--project-files",
        action="store_true",
        help="explicitly admit eligible tracked public project text at the pinned revision (64 MiB/8192 paths)",
    )
    build = subcommands.add_parser("build")
    build.add_argument("--engine", choices=("docker", "podman"), default="podman")
    build.add_argument("--images", required=True, type=Path)
    for operation in ("run", "admin-plan", "admin-apply"):
        child = subcommands.add_parser(operation)
        child.add_argument("--engine", choices=("docker", "podman"), default="podman")
        for name in ("policy", "token-file", "state-dir", "images"):
            child.add_argument(f"--{name}", required=True, type=Path)
        if operation == "run":
            child.add_argument("--corpus-dir", required=True, type=Path)
            child.add_argument("--observation-dir", type=Path)
            child.add_argument("--sync-commands", action="store_true")
            child.add_argument("--history", action="store_true")
            child.add_argument("--admin-user", action="append", default=[])
            child.add_argument("--command-name", default="reach")
            child.add_argument("--conversation-profile", type=Path)
            child.add_argument("--onboarding-profile", type=Path)
            child.add_argument("--model-endpoint", default=MODEL_ENDPOINT)
            child.add_argument("--model-transport", choices=("host", "podman"), default="host")
            child.add_argument("--research-profile", type=Path)
            child.add_argument("--research-state-dir", type=Path)
            child.add_argument("--research-image")
            child.add_argument("--publications-dir", type=Path)
            child.add_argument("--publication-channel", action="append", default=[])
        elif operation == "admin-plan":
            child.add_argument("--owner-id", required=True)
            child.add_argument("--output", required=True, type=Path)
        else:
            child.add_argument("--plan", required=True, type=Path)
            child.add_argument("--expect-digest", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.operation == "token":
            token_file(args.file)
        elif args.operation == "export-corpus":
            revision = export_corpus(args.output, args.revision, project_files=args.project_files)
            print(json.dumps({"source_revision": revision, "path": str(args.output)}))  # noqa: T201
        elif args.operation == "build":
            build_images(args.engine, args.images)
        elif args.operation == "run":
            return run_containers(args)
        else:
            return admin_containers(args)
    except KeyboardInterrupt:
        return 130
    except Exception:  # noqa: BLE001 - never render token-bearing or foreign tool diagnostics
        print("reach_operator_refused", file=sys.stderr)  # noqa: T201
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
