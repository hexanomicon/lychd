"""Host harness boundaries exercised without a container daemon or live credentials."""

from __future__ import annotations

import asyncio
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from scripts import reach_operator as operator

from lychd.interface.discord.admin import DeveloperLayout, GuildSnapshot, ServerPlan
from lychd.interface.discord.operator_cli import load_plan

IMAGE = "sha256:" + "a" * 64
SECRET = "synthetic.token_value_only_for_test"  # noqa: S105 - inert local fixture
POLICY = """schema_version = 1
application_id = "101"
bot_user_id = "102"
guild_id = "103"
allowed_channel_ids = ["104"]
[[rules]]
name = "operator"
user_ids = ["105"]
actions = ["answer_docs"]
"""


def files(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    policy, token, images, state = (tmp_path / name for name in ("policy.toml", "token", "images.json", "state"))
    operator.write_private(policy, POLICY.encode())
    operator.write_private(token, SECRET.encode())
    operator.write_private(images, operator.json_bytes({"schema_version": 1, "core": IMAGE, "edge": IMAGE}))
    return policy, token, images, state


def test_token_is_local_private_and_never_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def prompt(_prompt: str) -> str:
        return SECRET

    monkeypatch.setattr(operator.getpass, "getpass", prompt)
    path = tmp_path / "private" / "discord-token"
    operator.token_file(path)
    assert path.read_text() == SECRET
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    with pytest.raises(ValueError, match="operator_file_exists"):
        operator.token_file(path)
    assert capsys.readouterr().out == ""


def test_paths_refuse_checkouts_symlinks_and_relative_paths(tmp_path: Path) -> None:
    checkout = tmp_path / "repo"
    checkout.mkdir()
    (checkout / ".git").mkdir()
    for path in (checkout / "token", Path("relative")):
        with pytest.raises(ValueError, match=r"operator_(checkout|path)"):
            operator.external_path(path)
    link = tmp_path / "link"
    link.symlink_to(checkout, target_is_directory=True)
    with pytest.raises(ValueError, match="operator_symlink"):
        operator.external_path(link / "token")


def test_export_uses_exact_committed_blobs_and_ignores_dirty_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "examples/reach").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "examples/reach/public-docs.txt").write_text("README.md\ndocs/index.md\n")
    (repo / "README.md").write_text("Committed public text\n")
    (repo / "docs/index.md").write_text("Committed documentation\n")
    for arguments in (
        ["git", "init", "--quiet"],
        ["git", "add", "README.md", "docs/index.md"],
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "Fixture",
        ],
    ):
        subprocess.run(arguments, cwd=repo, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603 - closed local fixture commands
    (repo / "README.md").write_text("Dirty private synthetic text\n")
    output = tmp_path / "export"
    revision = operator.export_corpus(output, root=repo)
    manifest = json.loads((output / "manifest.json").read_bytes())
    assert manifest["source_revision"] == revision
    assert len(revision) == 40
    assert (output / "000.md").read_text() == "Committed public text\n"
    assert "Dirty private" not in "".join(path.read_text() for path in output.iterdir())
    assert manifest["documents"][0]["url"].endswith(f"/{revision}/README.md")
    with pytest.raises(ValueError, match="corpus_output_exists"):
        operator.export_corpus(output, root=repo)


def test_exact_images_and_private_instance_lock(tmp_path: Path) -> None:
    _, _, images, state = files(tmp_path)
    assert operator.load_images(images) == {"core": IMAGE, "edge": IMAGE}
    with operator.instance_lock(state), pytest.raises(BlockingIOError), operator.instance_lock(state):
        pytest.fail("Second generation acquired the same partition")
    images.write_text('{"schema_version":1,"core":"latest","edge":"latest"}')
    with pytest.raises(ValueError, match="operator_images"):
        operator.load_images(images)


def test_container_boundary_has_no_host_socket_ports_or_environment(tmp_path: Path) -> None:
    args = operator.container_arguments("podman", IMAGE, tmp_path / "cid", offline=True)
    assert "--network=none" in args
    assert "--read-only" in args
    assert "--cap-drop=ALL" in args
    assert "--security-opt=no-new-privileges" in args
    assert "--userns=keep-id" in args
    assert not any(
        "socket" in item or "docker.sock" in item or item in {"--publish", "--env", "--privileged"} for item in args
    )


def test_host_environment_excludes_provider_and_discord_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setenv("LYCHD_DATABASE_URL", SECRET)
    environment = operator.safe_environment("docker")
    assert SECRET not in environment.values()
    assert environment["LYCHD_TEST_ENGINE"] == "docker"


class Writer:
    def __init__(self) -> None:
        self.raw = bytearray()

    def write(self, value: bytes) -> None:
        self.raw.extend(value)

    async def drain(self) -> None:
        return


@pytest.mark.parametrize(
    "raw",
    [b"x" * (operator.WIRE_LIMIT + 1) + b"\n", b'{"x":1,"x":2}\n', b"truncated"],
    ids=["oversized", "duplicate", "truncated"],
)
@pytest.mark.asyncio
async def test_relay_refuses_oversize_duplicate_and_partial_frames(raw: bytes) -> None:
    reader = asyncio.StreamReader(limit=operator.WIRE_LIMIT)
    reader.feed_data(raw)
    reader.feed_eof()
    writer = Writer()
    with pytest.raises((ValueError, asyncio.LimitOverrunError)):
        await operator.relay(reader, writer)  # type: ignore[arg-type] - structural fixture for a write-only pipe
    assert writer.raw == b""


@pytest.mark.asyncio
async def test_diagnostics_preserve_readiness_but_hide_foreign_text(capsys: pytest.CaptureFixture[str]) -> None:
    reader = asyncio.StreamReader()
    reader.feed_data(b"reach_discord:ready\nforeign message content\nTraceback (most recent call last):\n")
    reader.feed_eof()
    await operator.diagnostics(reader)
    assert capsys.readouterr().err == "reach_discord:ready\nreach_child_diagnostic\nreach_child_diagnostic\n"


class Process:
    def __init__(self) -> None:
        self.stdout = asyncio.StreamReader()
        self.stderr = asyncio.StreamReader()
        self.stdin = Writer()
        self.stdout.feed_eof()
        self.stderr.feed_eof()
        self.returncode: int | None = None
        self.terminated = asyncio.Event()

    async def wait(self) -> int:
        await self.terminated.wait()
        assert self.returncode is not None
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -15
        self.terminated.set()

    def kill(self) -> None:
        self.returncode = -9
        self.terminated.set()


@pytest.mark.asyncio
async def test_first_child_eof_retires_both_and_cleans_only_owned_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    children: list[Process] = []
    removed: list[Path] = []

    async def create(*_args: Any, **_kwargs: Any) -> Process:
        child = Process()
        children.append(child)
        return child

    async def remove(_engine: str, cidfile: Path) -> None:
        removed.append(cidfile)

    monkeypatch.setattr(operator.asyncio, "create_subprocess_exec", create)
    monkeypatch.setattr(operator, "remove_owned", remove)
    identities = (tmp_path / "core.cid", tmp_path / "edge.cid")
    result = await operator.supervise("docker", (["docker", "core"], ["docker", "edge"]), identities)
    assert result == 1
    assert len(children) == 2
    assert all(child.terminated.is_set() for child in children)
    assert removed == list(identities)


def test_run_mounts_exact_inputs_and_never_token_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy, token, images, state = files(tmp_path)
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "manifest.json").write_text("{}")
    observed: list[list[str]] = []

    async def supervise(_engine: str, commands: tuple[list[str], list[str]], _ids: tuple[Path, Path]) -> int:
        observed.extend(commands)
        return 0

    monkeypatch.setattr(operator, "supervise", supervise)
    args = operator.parser().parse_args(
        [
            "run",
            "--policy",
            str(policy),
            "--token-file",
            str(token),
            "--state-dir",
            str(state),
            "--images",
            str(images),
            "--corpus-dir",
            str(corpus),
            "--engine",
            "docker",
        ]
    )
    assert operator.run_containers(args) == 0
    core, edge = observed
    assert "--network=none" in core
    assert "--network=none" not in edge
    assert SECRET not in " ".join(core + edge)
    assert not any("docker.sock" in item or ":/home" in item or item == "--publish" for item in core + edge)
    assert str(token) not in " ".join(core)
    assert "/work/scripts/reach_worker.py" in core


def test_invalid_inputs_have_fixed_diagnostics(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert operator.main(["export-corpus", "--output", "relative"]) == 1
    assert capsys.readouterr().err == "reach_operator_refused\n"


def test_selected_checks_token_metadata_without_reading_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy, token, images, state = files(tmp_path)
    original = operator.read_regular

    def read(path: Path, limit: int, *, private: bool = False) -> bytes:
        assert path != token
        return original(path, limit, private=private)

    monkeypatch.setattr(operator, "read_regular", read)
    args = operator.parser().parse_args(
        [
            "admin-plan",
            "--policy",
            str(policy),
            "--token-file",
            str(token),
            "--images",
            str(images),
            "--state-dir",
            str(state),
            "--owner-id",
            "105",
            "--output",
            str(tmp_path / "plan.json"),
        ]
    )
    selected, effects = operator.select_operator_files(args)
    assert selected == {"core": IMAGE, "edge": IMAGE}
    assert effects == state / "effects"


def test_generated_admin_plan_envelope_loads_in_apply_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy, token, images, state = files(tmp_path)
    output = tmp_path / "plan.json"
    now = datetime(2026, 10, 27, tzinfo=UTC)
    plan = ServerPlan(
        created_at=now,
        expires_at=now + timedelta(minutes=15),
        layout=DeveloperLayout(application_id="101", bot_user_id="102", guild_id="103", owner_id="105"),
        snapshot=GuildSnapshot(
            application_id="101",
            bot_user_id="102",
            guild_id="103",
            owner_id="105",
            roles=(),
            channels=(),
            bot_role_ids=(),
        ),
        existing=(),
        operations=(),
    )
    envelope = {"plan": plan.model_dump(mode="json"), "digest": plan.digest}

    def command(_arguments: Any, **_kwargs: Any) -> bytes:
        return operator.json_bytes(envelope)

    async def remove(_engine: str, _cidfile: Path) -> None:
        return

    monkeypatch.setattr(operator, "command", command)
    monkeypatch.setattr(operator, "remove_owned", remove)
    args = operator.parser().parse_args(
        [
            "admin-plan",
            "--policy",
            str(policy),
            "--token-file",
            str(token),
            "--images",
            str(images),
            "--state-dir",
            str(state),
            "--owner-id",
            "105",
            "--output",
            str(output),
        ]
    )
    assert operator.admin_containers(args) == 0
    assert json.loads(output.read_bytes()) == envelope
    assert load_plan(output, plan.digest) == plan


def test_workspace_preserves_cid_evidence_after_cleanup_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = operator.private_directory(tmp_path / "state")

    def unsettled() -> None:
        with operator.generation_workspace(state, "generation-") as directory:
            (directory / "core.cid").write_text("a" * 64)
            message = "operator_cleanup_failed"
            raise ValueError(message)

    with pytest.raises(ValueError, match="operator_cleanup_failed"):
        unsettled()
    retained = list(state.glob("generation-*"))
    assert len(retained) == 1
    assert (retained[0] / "core.cid").read_text() == "a" * 64
    assert capsys.readouterr().err == "reach_operator_scratch_retained\n"
    with operator.generation_workspace(state, "admin-") as settled:
        (settled / "edge.cid").write_text("b" * 64)
    assert not settled.exists()


@pytest.mark.parametrize("status", ["unknown", "rejected"])
def test_admin_apply_preserves_structured_failure_and_exit_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], status: str
) -> None:
    policy, token, images, state = files(tmp_path)
    plan = tmp_path / "plan.json"
    operator.write_private(plan, b"{}")
    result: dict[str, Any] = {"status": status, "code": "scope_unresolved", "operations": [], "resources": []}

    def command(_arguments: Any, **kwargs: Any) -> bytes:
        assert kwargs["accepted_exit_codes"] == (0, 2)
        return operator.json_bytes(result)

    async def remove(_engine: str, _cidfile: Path) -> None:
        return

    monkeypatch.setattr(operator, "command", command)
    monkeypatch.setattr(operator, "remove_owned", remove)
    args = operator.parser().parse_args(
        [
            "admin-apply",
            "--policy",
            str(policy),
            "--token-file",
            str(token),
            "--images",
            str(images),
            "--state-dir",
            str(state),
            "--plan",
            str(plan),
            "--expect-digest",
            "a" * 64,
        ]
    )
    assert operator.admin_containers(args) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out) == result
    assert captured.err == ""


@pytest.mark.parametrize("accepted", [(0,), (0, 2)])
def test_command_admits_nonzero_output_only_when_explicitly_selected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, accepted: tuple[int, ...]
) -> None:
    def run(arguments: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        kwargs["stdout"].write(b'{"status":"unknown"}\n')
        assert kwargs["stderr"] == subprocess.DEVNULL
        return subprocess.CompletedProcess(arguments, 2)

    monkeypatch.setattr(operator.subprocess, "run", run)
    if 2 in accepted:
        assert operator.command(["fixture"], root=tmp_path, accepted_exit_codes=accepted) == b'{"status":"unknown"}\n'
    else:
        with pytest.raises(ValueError, match="operator_command_failed"):
            operator.command(["fixture"], root=tmp_path, accepted_exit_codes=accepted)
