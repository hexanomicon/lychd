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
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Any, NoReturn, cast
from uuid import uuid4

from lychd.interface.discord.operator_io import load_policy

ROOT = Path(__file__).resolve().parents[1]
WIRE_LIMIT = 65_536
DOCUMENT_LIMIT = 524_288
CORPUS_LIMIT = 2_097_152
MAX_DOCUMENTS = 32
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
EDGE_INPUTS = (
    "scripts/generate_python_third_party_notices.py",
    "clients/discord/pyproject.toml",
    "clients/discord/uv.lock",
    "clients/discord/Containerfile",
    *(f"src/lychd/compositions/reach/{name}.py" for name in ("__init__", "schemas", "policy", "operator_wire")),
    *(
        f"src/lychd/interface/discord/{name}.py"
        for name in ("__init__", "schemas", "events", "operator_io", "live", "rest", "admin", "operator_cli")
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


def export_corpus(output: Path, revision: str = "HEAD", *, root: Path = ROOT) -> str:
    """Export only catalogue-listed committed blobs, detached from dirty/private working files."""
    external_path(output)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        _fail("corpus_output_exists")
    catalogue = (root / "examples/reach/public-docs.txt").read_text(encoding="utf-8").splitlines()
    paths = [line.strip() for line in catalogue if line.strip() and not line.lstrip().startswith("#")]
    if not 1 <= len(paths) <= MAX_DOCUMENTS or len(paths) != len(set(paths)):
        _fail("corpus_catalogue")
    if any(
        re.fullmatch(r"(?:README\.md|CONTRIBUTING\.md|docs/[A-Za-z0-9_./-]+\.md)", path) is None
        or any(part in {"", ".", ".."} for part in path.split("/"))
        for path in paths
    ):
        _fail("corpus_catalogue")
    resolved = (
        command(["git", "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}"], root=root)
        .decode("ascii")
        .strip()
    )
    if re.fullmatch(r"[0-9a-f]{40}", resolved) is None:
        _fail("corpus_revision")
    documents: list[dict[str, str]] = []
    contents: list[bytes] = []
    total = 0
    for index, path in enumerate(paths):
        raw = command(["git", "show", f"{resolved}:{path}"], root=root, limit=DOCUMENT_LIMIT)
        total += len(raw)
        raw.decode("utf-8", errors="strict")
        if total > CORPUS_LIMIT:
            _fail("corpus_limit")
        contents.append(raw)
        documents.append(
            {
                "path": path,
                "url": f"https://github.com/hexanomicon/lychd/blob/{resolved}/{path}",
                "sha256": sha256(raw).hexdigest(),
                "file": f"{index:03}.md",
            }
        )
    private_directory(output)
    # The manifest is published last; an interrupted export is never admissible.
    for document, raw in zip(documents, contents, strict=True):
        write_private(output / document["file"], raw)
    write_private(
        output / "manifest.json", json_bytes({"schema_version": 1, "source_revision": resolved, "documents": documents})
    )
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


def build_images(engine: str, output: Path, *, root: Path = ROOT) -> None:
    """Build exact images with separate bounded source contexts, never secret mounts."""
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


async def relay(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Forward complete bounded JSON objects only; EOF ends this generation."""
    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except asyncio.IncompleteReadError as error:
            if error.partial:
                _fail("operator_truncated_frame")
            return
        if len(raw) > WIRE_LIMIT:
            _fail("operator_frame_limit")
        strict_object(raw)
        writer.write(raw)
        await writer.drain()


async def diagnostics(reader: asyncio.StreamReader) -> None:
    """Expose fixed codes only; foreign traces or message content never reach the terminal."""
    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            return
        code = raw.decode("ascii", errors="ignore").strip()
        admitted = code if re.fullmatch(r"(?:reach_discord:)?[a-z][a-z0-9_]{0,63}", code) else "reach_child_diagnostic"
        sys.stderr.write(admitted + "\n")


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


async def supervise(engine: str, commands: tuple[list[str], list[str]], cidfiles: tuple[Path, Path]) -> int:  # noqa: C901, PLR0912 - explicit two-child settlement and exact-ID cleanup
    """First EOF, child failure or signal retires both processes and exact owned containers."""
    children: list[asyncio.subprocess.Process] = []
    tasks: list[asyncio.Task[Any]] = []
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stopped.set)
    status = 1
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
            asyncio.create_task(relay(core.stdout, edge.stdin)),
            asyncio.create_task(relay(edge.stdout, core.stdin)),
            asyncio.create_task(core.wait()),
            asyncio.create_task(edge.wait()),
            asyncio.create_task(stopped.wait()),
        ]
        diagnostic_tasks = [
            asyncio.create_task(diagnostics(core.stderr)),
            asyncio.create_task(diagnostics(edge.stderr)),
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
        for child in children:
            await retire(child)
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
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


def run_containers(args: argparse.Namespace) -> int:
    images, effects = select_operator_files(args)
    external_path(args.corpus_dir)
    if not args.corpus_dir.is_dir() or not (args.corpus_dir / "manifest.json").is_file():
        _fail("corpus_missing")
    policy = load_policy(args.policy)
    if bool(policy.context_message_limit) != args.history:
        _fail("history_policy_flag_mismatch")
    with (
        instance_lock(args.state_dir),
        generation_workspace(args.state_dir, "generation-") as temporary,
    ):
        generation = Path(temporary)
        generic = generation / "policy.json"
        write_private(generic, policy.to_reach_policy().model_dump_json().encode())
        core_cid, edge_cid = generation / "core.cid", generation / "edge.cid"
        core = container_arguments(args.engine, images["core"], core_cid, offline=True)
        core += bind(generic, "/run/reach/policy.json") + bind(args.corpus_dir, "/run/reach/corpus")
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
        edge = container_arguments(args.engine, images["edge"], edge_cid, offline=False)
        edge += (
            bind(args.policy, "/run/reach/policy.toml")
            + bind(args.token_file, "/run/secrets/discord-token")
            + bind(effects, "/state/effects", readonly=False)
        )
        edge += [
            images["edge"],
            "--policy",
            "/run/reach/policy.toml",
            "--token-file",
            "/run/secrets/discord-token",
            "--effects-dir",
            "/state/effects",
        ]
        if args.sync_commands:
            edge.append("--sync-commands")
        if args.history:
            edge.append("--history")
        for identity in args.admin_user:
            if re.fullmatch(r"[1-9][0-9]{0,19}", identity) is None:
                _fail("operator_admin_identity")
            edge += ["--admin-user", identity]
        return asyncio.run(supervise(args.engine, (core, edge), (core_cid, edge_cid)))


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
            child.add_argument("--sync-commands", action="store_true")
            child.add_argument("--history", action="store_true")
            child.add_argument("--admin-user", action="append", default=[])
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
            print(json.dumps({"source_revision": export_corpus(args.output, args.revision), "path": str(args.output)}))  # noqa: T201
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
