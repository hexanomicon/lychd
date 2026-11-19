from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Never
from uuid import uuid4

import httpx2
import pytest
from click import ClickException
from click.testing import CliRunner
from scripts.music_probe import CHECKOUT_ROOT, cli, external_path, read_json_file

from lychd.domain.comfy_probe import (
    ComfyArtifact,
    ComfyProfile,
    ComfyRequest,
    MutableInput,
    OutputOpening,
    canonical_json,
    json_digest,
)
from lychd.system.services.comfy_probe import ComfyProbe, ProbeRefusedError

pytest_plugins = ["tests.music_probe_support"]


def test_schema_and_demo_work_without_native_import(probe_path: Path) -> None:
    runner = CliRunner()
    schema = runner.invoke(cli, ["schema"])
    assert schema.exit_code == 0
    assert json.loads(schema.output)["title"] == "RenderRecipe"
    recipe = probe_path / "recipe.json"
    result = runner.invoke(cli, ["demo", "--bars", "1", "--output", str(recipe)])
    assert result.exit_code == 0
    before = recipe.read_bytes()
    second = runner.invoke(cli, ["demo", "--output", str(recipe)])
    assert second.exit_code != 0
    assert recipe.read_bytes() == before
    validated = runner.invoke(cli, ["validate", str(recipe)])
    assert validated.exit_code == 0
    assert json.loads(validated.output)["recipe_digest"] == json.loads(result.output)["recipe_digest"]
    for kind, title in (("comfy-profile", "ComfyProfile"), ("comfy-request", "ComfyRequest")):
        result = runner.invoke(cli, ["schema", kind])
        assert result.exit_code == 0
        assert json.loads(result.output)["title"] == title


def test_render_timeout_refuses_outside_worker_bound_before_files_or_processes(probe_path: Path) -> None:
    result = CliRunner().invoke(
        cli, ["render", str(probe_path / "missing.json"), "--workspace", str(probe_path / "work"), "--timeout", "31"]
    )
    assert result.exit_code == 2
    assert "--timeout" in result.output
    assert not (probe_path / "work").exists()


def test_private_probe_paths_refuse_checkout_relative_and_symlink(probe_path: Path) -> None:
    for path in (CHECKOUT_ROOT / "private.json", Path("relative.json")):
        with pytest.raises(ClickException, match=r"outside|absolute"):
            external_path(path)
    link = probe_path / "link"
    link.symlink_to(probe_path, target_is_directory=True)
    with pytest.raises(ClickException, match="symlink"):
        external_path(link / "private.json")


def test_json_reads_bound_input_bytes(probe_path: Path) -> None:
    oversized = probe_path / "oversized.json"
    oversized.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(ClickException, match="byte limit"):
        read_json_file(oversized)


@pytest.fixture
def comfy_profile() -> ComfyProfile:
    graph = canonical_json({"1": {"class_type": "AudioSave", "inputs": {"seed": 1}}})
    return ComfyProfile(
        endpoint="http://127.0.0.1:8188",
        deployment_revision="test-only",
        review_reference="no-live-authority",
        workflow_json=graph,
        workflow_sha256=json_digest(graph),
        allowed_node_classes=("AudioSave",),
        models=(),
        mutable_inputs=(
            MutableInput(name="seed", node_id="1", input_name="seed", kind="integer", minimum=0, maximum=2),
        ),
        outputs=(
            OutputOpening(
                node_id="1", kind="audio", receiving_owner="riffmaw.music", extensions=(".wav",), max_bytes=8
            ),
        ),
    )


def test_comfy_cli_prepare_recovers_named_occurrence(probe_path: Path, comfy_profile: ComfyProfile) -> None:
    profile_path = probe_path / "profile.json"
    profile_path.write_text(comfy_profile.model_dump_json())
    request_path = probe_path / "request.json"
    request = ComfyRequest(profile_sha256=comfy_profile.digest, inputs_json='{"seed":1}')
    request_path.write_text(request.model_dump_json())
    args = [
        "comfy",
        "prepare",
        "--profile",
        str(profile_path),
        "--request",
        str(request_path),
        "--workspace",
        str(probe_path),
    ]
    occurrence = str(uuid4())
    named_args = [*args, "--occurrence", occurrence]
    runner = CliRunner()
    first = runner.invoke(cli, named_args)
    assert first.exit_code == 0, first.output
    assert json.loads(first.output)["occurrence_id"] == occurrence
    receipt = probe_path / f"{occurrence}.json"
    original = receipt.read_bytes()

    repeated = runner.invoke(cli, named_args)
    assert repeated.exit_code == 0, repeated.output
    assert repeated.output == first.output
    assert receipt.read_bytes() == original

    independent = runner.invoke(cli, args)
    assert independent.exit_code == 0, independent.output
    assert json.loads(independent.output)["occurrence_id"] != occurrence

    request_path.write_text(request.model_copy(update={"inputs_json": '{"seed":2}'}).model_dump_json())
    conflict = runner.invoke(cli, named_args)
    assert conflict.exit_code != 0
    assert isinstance(conflict.exception, ProbeRefusedError)
    assert "identity changed" in str(conflict.exception)
    assert receipt.read_bytes() == original


def test_comfy_cli_repairs_pinned_stage_without_load_or_http(
    probe_path: Path, comfy_profile: ComfyProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    probe = ComfyProbe(comfy_profile, probe_path, (CHECKOUT_ROOT,))
    attempt = probe.prepare(ComfyRequest(profile_sha256=comfy_profile.digest, inputs_json='{"seed":1}'))
    digest = hashlib.sha256(b"WAVE").hexdigest()
    local = f"{attempt.occurrence_id}-0-{digest}.wav"
    artifact = ComfyArtifact(
        node_id="1",
        kind="audio",
        receiving_owner="riffmaw.music",
        filename="sound.wav",
        subfolder="",
        storage_type="output",
        local_filename=local,
        sha256=digest,
        size_bytes=4,
    )
    attempt = attempt.model_copy(
        update={"state": "succeeded", "provider_id": str(attempt.occurrence_id), "artifacts": (artifact,)}
    )
    receipt = probe_path / f"{attempt.occurrence_id}.json"
    receipt.write_text(attempt.model_dump_json())
    original = receipt.read_bytes()
    stage = probe_path / f".comfy-stage-v1-{attempt.occurrence_id}-0"
    stage.write_bytes(b"WAVE")
    with pytest.raises(ProbeRefusedError, match="missing"):
        probe.load(attempt.occurrence_id)
    profile_path = probe_path / "profile.json"
    profile_path.write_text(comfy_profile.model_dump_json())

    def forbid_http_client(**_options: object) -> Never:
        pytest.fail("repair must not construct an HTTP client")

    monkeypatch.setattr(httpx2, "AsyncClient", forbid_http_client)
    result = CliRunner().invoke(
        cli,
        [
            "comfy",
            "attempt",
            "repair",
            str(attempt.occurrence_id),
            "--profile",
            str(profile_path),
            "--workspace",
            str(probe_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == attempt.model_dump(mode="json")
    assert receipt.read_bytes() == original
    assert (probe_path / local).read_bytes() == b"WAVE"
    assert not stage.exists()
