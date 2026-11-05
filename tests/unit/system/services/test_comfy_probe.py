import fcntl
import hashlib
import json
import os
import stat
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import httpx2
import pytest
from pydantic import ValidationError

from lychd.domain.comfy_probe import (
    ComfyArtifact,
    ComfyAttempt,
    ComfyProfile,
    ComfyRequest,
    MutableInput,
    OutputOpening,
    canonical_json,
    json_digest,
)
from lychd.system.services.comfy_probe import ComfyProbe, ProbeRefusedError

pytest_plugins = ["tests.music_probe_support"]


@pytest.fixture
def profile() -> ComfyProfile:
    graph = canonical_json({"1": {"class_type": "AudioSave", "inputs": {"seed": 1}}})
    return ComfyProfile(
        endpoint="http://127.0.0.1:8188",
        deployment_revision="reviewed-test-revision",
        review_reference="test-only-profile-no-live-authority",
        workflow_json=graph,
        workflow_sha256=json_digest(graph),
        allowed_node_classes=("AudioSave",),
        models=(),
        mutable_inputs=(
            MutableInput(
                name="seed",
                node_id="1",
                input_name="seed",
                kind="integer",
                minimum=0.0,
                maximum=100.0,
            ),
        ),
        outputs=(
            OutputOpening(
                node_id="1",
                kind="audio",
                receiving_owner="riffmaw.music",
                extensions=(".wav",),
                max_bytes=8,
            ),
        ),
        client_prompt_id_supported=True,
    )


def request_for(profile: ComfyProfile, seed: int = 1) -> ComfyRequest:
    return ComfyRequest(profile_sha256=profile.digest, inputs_json=canonical_json({"seed": seed}))


def probe_for(
    probe_path: Path, profile: ComfyProfile, handler: Callable[[httpx2.Request], httpx2.Response]
) -> ComfyProbe:
    return ComfyProbe(
        profile,
        probe_path,
        (Path(__file__).resolve().parents[4],),
        httpx2.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_lost_ack_resume_and_empty_history_never_resubmit(probe_path: Path, profile: ComfyProfile) -> None:
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.method + " " + request.url.path)
        if request.url.path == "/prompt":
            msg = "ack lost"
            raise httpx2.ReadTimeout(msg, request=request)
        return httpx2.Response(
            200,
            json={"queue_running": [], "queue_pending": []} if request.url.path == "/queue" else {},
        )

    probe = probe_for(probe_path, profile, handler)
    initial = probe.prepare(request_for(profile))
    unknown = await probe.submit(initial)
    assert unknown.state == "indeterminate"
    resumed = probe_for(probe_path, profile, handler).prepare(request_for(profile), initial.occurrence_id)
    assert resumed.state == "indeterminate"
    assert (await probe.reconcile(resumed)).state == "indeterminate"
    with pytest.raises(ProbeRefusedError, match="already crossed"):
        await probe.submit(initial)
    assert calls.count("POST /prompt") == 1


@pytest.mark.asyncio
async def test_old_dialect_unknown_ack_does_not_query_fabricated_id(probe_path: Path, profile: ComfyProfile) -> None:
    profile = ComfyProfile.model_validate({**profile.model_dump(), "client_prompt_id_supported": False})
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        if request.url.path == "/prompt":
            assert "prompt_id" not in json.loads(request.content)
            return httpx2.Response(200, json={"prompt_id": "not-an-id"})
        return httpx2.Response(200, json={"queue_running": [], "queue_pending": []})

    probe = probe_for(probe_path, profile, handler)
    attempt = await probe.submit(probe.prepare(request_for(profile)))
    assert (await probe.reconcile(attempt)).provider_id is None
    assert calls == ["/prompt", "/queue"]


def test_replay_changed_input_profile_and_mutable_bounds_refuse(probe_path: Path, profile: ComfyProfile) -> None:
    probe = probe_for(probe_path, profile, lambda _: httpx2.Response(500))
    attempt = probe.prepare(request_for(profile))
    with pytest.raises(ProbeRefusedError, match="identity changed"):
        probe.prepare(request_for(profile, 2), attempt.occurrence_id)
    changed = ComfyProfile.model_validate({**profile.model_dump(), "deployment_revision": "another-revision"})
    with pytest.raises(ProbeRefusedError):
        probe_for(probe_path, changed, lambda _: httpx2.Response(500)).prepare(
            request_for(changed), attempt.occurrence_id
        )
    with pytest.raises(ValueError, match="bounds"):
        probe.prepare(request_for(profile, 101))
    with pytest.raises(ValueError, match="scalar type"):
        profile.prompt(
            ComfyRequest(
                profile_sha256=profile.digest,
                inputs_json=canonical_json({"seed": True}),
            )
        )
    with pytest.raises(ValidationError):
        profile.endpoint = "http://127.0.0.1:9999"
    independent = profile.prompt(request_for(profile))
    independent["1"]["inputs"]["seed"] = 90
    assert profile.prompt(request_for(profile))["1"]["inputs"]["seed"] == 1


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://localhost:8188",
        "http://127.0.0.1:8188/",
        "https://127.0.0.1:8188",
        "http://user:secret@127.0.0.1:8188",
        "http://192.0.2.1:8188",
    ],
)
def test_nonliteral_or_credential_endpoints_refuse(profile: ComfyProfile, endpoint: str) -> None:
    with pytest.raises(ValueError, match=r"Endpoint|loopback|address|descriptor|component|extension|bound"):
        ComfyProfile.model_validate({**profile.model_dump(), "endpoint": endpoint})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "descriptor",
    [
        {"filename": "../secret.wav", "subfolder": "", "type": "output"},
        {"filename": "sound.wav", "subfolder": "../secret", "type": "output"},
        {"filename": "sound.wav", "subfolder": "", "type": "input"},
        {"filename": "sound.exe", "subfolder": "", "type": "output"},
        {"filename": "sound.wav", "subfolder": "", "type": "output", "preview": "jpeg"},
    ],
)
async def test_malicious_outputs_refuse(probe_path: Path, profile: ComfyProfile, descriptor: dict[str, str]) -> None:
    await exercise_output(probe_path, profile, descriptor, b"WAVE", expect_failure=True)


async def exercise_output(
    probe_path: Path,
    profile: ComfyProfile,
    descriptor: dict[str, str],
    content: bytes,
    *,
    expect_failure: bool = False,
) -> None:
    occurrence = uuid4()
    prompt = profile.prompt(request_for(profile))

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/prompt":
            payload = json.loads(request.content)
            assert payload["prompt_id"] == str(occurrence)
            return httpx2.Response(200, json={"prompt_id": str(occurrence), "node_errors": {}})
        if request.url.path.startswith("/history/"):
            return httpx2.Response(
                200,
                json={
                    str(occurrence): {
                        "prompt": [0, str(occurrence), prompt],
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {"1": {"audio": [descriptor]}},
                    }
                },
            )
        assert request.url.path == "/view"
        assert set(request.url.params) == {"filename", "subfolder", "type"}
        return httpx2.Response(200, content=content)

    probe = probe_for(probe_path, profile, handler)
    attempt = await probe.submit(probe.prepare(request_for(profile), occurrence))
    if expect_failure:
        with pytest.raises(ValueError, match=r"Endpoint|loopback|address|descriptor|component|extension|bound"):
            await probe.fetch_outputs(await probe.reconcile(attempt))
        assert not list(probe_path.glob("*.wav"))  # noqa: ASYNC240 - finite test inspection
        assert not list(probe_path.glob(".media-*"))  # noqa: ASYNC240 - finite test inspection
        return
    attempt = await probe.fetch_outputs(await probe.reconcile(attempt))
    artifact = attempt.artifacts[0]
    assert artifact.receiving_owner == "riffmaw.music"
    assert artifact.sha256 == hashlib.sha256(content).hexdigest()
    assert artifact.local_filename is not None
    assert (probe_path / artifact.local_filename).read_bytes() == content
    assert artifact.size_bytes == len(content)


@pytest.mark.asyncio
async def test_success_fetches_raw_audio_with_digest(probe_path: Path, profile: ComfyProfile) -> None:
    await exercise_output(
        probe_path,
        profile,
        {"filename": "sound.wav", "subfolder": "", "type": "output"},
        b"WAVE",
    )


@pytest.mark.asyncio
async def test_output_overrun_cleans_partial(probe_path: Path, profile: ComfyProfile) -> None:
    await exercise_output(
        probe_path,
        profile,
        {"filename": "sound.wav", "subfolder": "", "type": "output"},
        b"over-bound",
        expect_failure=True,
    )


def test_cancel_and_checkout_symlink_fences(probe_path: Path, profile: ComfyProfile) -> None:
    probe = probe_for(probe_path, profile, lambda _: pytest.fail("unexpected network"))
    with pytest.raises(ProbeRefusedError, match="global interruption"):
        probe.cancel(probe.prepare(request_for(profile)))
    with pytest.raises(ProbeRefusedError, match="outside"):
        ComfyProbe(profile, probe_path, (probe_path,))
    symlink = probe_path / "linked"
    symlink.symlink_to(probe_path, target_is_directory=True)
    with pytest.raises(ProbeRefusedError, match="symlink"):
        ComfyProbe(profile, symlink, (Path("/checkout"),))


def test_boolean_opening_admits_bool_and_refuses_integer() -> None:
    opening = MutableInput(name="enabled", node_id="1", input_name="enabled", kind="boolean")
    opening.admit(value=True)
    opening.admit(value=False)
    with pytest.raises(ValueError, match="scalar type"):
        opening.admit(1)


def test_receipt_fifo_refuses_without_waiting_for_a_writer(probe_path: Path, profile: ComfyProfile) -> None:
    occurrence = uuid4()
    os.mkfifo(probe_path / f"{occurrence}.json")
    probe = probe_for(probe_path, profile, lambda _: pytest.fail("unexpected network"))
    with pytest.raises(ProbeRefusedError, match="regular file"):
        probe.load(occurrence)


@pytest.mark.parametrize(("minimum", "maximum"), [(float("nan"), 1.0), (0.0, float("inf")), (2.0, 1.0)])
def test_numeric_opening_requires_finite_ordered_bounds(minimum: float, maximum: float) -> None:
    with pytest.raises(ValidationError, match="finite ordered"):
        MutableInput(name="seed", node_id="1", input_name="seed", kind="integer", minimum=minimum, maximum=maximum)


def test_artifact_metadata_is_all_present_or_all_absent() -> None:
    from lychd.domain.comfy_probe import ComfyArtifact

    fields = {
        "node_id": "1",
        "kind": "audio",
        "receiving_owner": "riffmaw.music",
        "filename": "sound.wav",
        "subfolder": "",
        "storage_type": "output",
    }
    for metadata in (
        {"local_filename": "sound.wav"},
        {"sha256": "0" * 64},
        {"size_bytes": 4},
        {"sha256": "0" * 64, "size_bytes": 4},
    ):
        with pytest.raises(ValidationError, match="all present"):
            ComfyArtifact.model_validate({**fields, **metadata})


def test_duplicate_and_contradictory_model_pins_refuse(profile: ComfyProfile) -> None:
    from lychd.domain.comfy_probe import ModelPin

    graph = canonical_json(
        {
            "1": {"class_type": "AudioSave", "inputs": {"seed": 1, "model_name": "model.safetensors"}},
            "2": {"class_type": "AudioSave", "inputs": {"model_name": "model.safetensors"}},
        }
    )
    first = ModelPin(node_id="1", input_name="model_name", filename="model.safetensors", sha256="0" * 64)
    second = ModelPin(node_id="2", input_name="model_name", filename="model.safetensors", sha256="1" * 64)
    for pins, reason in (((first, first), "Duplicate"), ((first, second), "Contradictory")):
        with pytest.raises(ValidationError, match=reason):
            ComfyProfile.model_validate(
                {**profile.model_dump(), "workflow_json": graph, "workflow_sha256": json_digest(graph), "models": pins}
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("empty", [False, True])
async def test_all_declared_output_openings_are_required(
    probe_path: Path, profile: ComfyProfile, *, empty: bool
) -> None:
    second = OutputOpening(node_id="1", kind="images", receiving_owner="atelier.studio", extensions=(".png",))
    profile = ComfyProfile.model_validate({**profile.model_dump(), "outputs": (*profile.outputs, second)})
    occurrence = uuid4()
    prompt = profile.prompt(request_for(profile))
    descriptor = {"filename": "sound.wav", "subfolder": "", "type": "output"}
    outputs = {"1": {"audio": [descriptor]}}
    if empty:
        outputs["1"]["images"] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/prompt":
            return httpx2.Response(200, json={"prompt_id": str(occurrence)})
        return httpx2.Response(
            200,
            json={
                str(occurrence): {
                    "prompt": [0, str(occurrence), prompt],
                    "status": {"completed": True, "status_str": "success"},
                    "outputs": outputs,
                }
            },
        )

    probe = probe_for(probe_path, profile, handler)
    attempt = await probe.submit(probe.prepare(request_for(profile), occurrence))
    with pytest.raises(ProbeRefusedError, match="file count" if empty else "every declared"):
        await probe.reconcile(attempt)


@pytest.mark.asyncio
async def test_partial_fetch_resume_pins_prior_bytes_and_never_refetches(
    probe_path: Path, profile: ComfyProfile
) -> None:
    opening = OutputOpening.model_validate({**profile.outputs[0].model_dump(), "max_files": 2})
    profile = ComfyProfile.model_validate({**profile.model_dump(), "outputs": (opening,)})
    occurrence = uuid4()
    prompt = profile.prompt(request_for(profile))
    second_ready = False
    views: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/prompt":
            return httpx2.Response(200, json={"prompt_id": str(occurrence)})
        if request.url.path.startswith("/history/"):
            outputs = {
                "1": {
                    "audio": [
                        {"filename": name, "subfolder": "", "type": "output"} for name in ("first.wav", "second.wav")
                    ]
                }
            }
            return httpx2.Response(
                200,
                json={
                    str(occurrence): {
                        "prompt": [0, str(occurrence), prompt],
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": outputs,
                    }
                },
            )
        filename = request.url.params["filename"]
        views.append(filename)
        if filename == "first.wav":
            return httpx2.Response(200, content=b"EDIT" if second_ready else b"WAVE")
        return httpx2.Response(200, content=b"GOOD") if second_ready else httpx2.Response(503)

    probe = probe_for(probe_path, profile, handler)
    attempt = await probe.reconcile(await probe.submit(probe.prepare(request_for(profile), occurrence)))
    with pytest.raises(httpx2.HTTPStatusError):
        await probe.fetch_outputs(attempt)
    partial = probe.load(occurrence)
    assert partial.artifacts[0].sha256 == hashlib.sha256(b"WAVE").hexdigest()
    assert partial.artifacts[1].local_filename is None
    second_ready = True
    resumed = await probe.fetch_outputs(partial)
    assert resumed.artifacts[0] == partial.artifacts[0]
    assert resumed.artifacts[1].sha256 == hashlib.sha256(b"GOOD").hexdigest()
    assert views == ["first.wav", "second.wav", "second.wav"]
    assert await probe.fetch_outputs(attempt) == resumed
    assert views == ["first.wav", "second.wav", "second.wav"]


@pytest.mark.asyncio
@pytest.mark.parametrize("damage", ["missing", "corrupt", "symlink", "wrong_name"])
async def test_retained_artifact_damage_refuses_load_and_fetch(
    probe_path: Path, profile: ComfyProfile, damage: str
) -> None:
    occurrence = uuid4()
    prompt = profile.prompt(request_for(profile))
    views = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal views
        if request.url.path == "/prompt":
            return httpx2.Response(200, json={"prompt_id": str(occurrence)})
        if request.url.path.startswith("/history/"):
            return httpx2.Response(
                200,
                json={
                    str(occurrence): {
                        "prompt": [0, str(occurrence), prompt],
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {"1": {"audio": [{"filename": "sound.wav", "subfolder": "", "type": "output"}]}},
                    }
                },
            )
        views += 1
        return httpx2.Response(200, content=b"WAVE")

    probe = probe_for(probe_path, profile, handler)
    attempt = await probe.fetch_outputs(
        await probe.reconcile(await probe.submit(probe.prepare(request_for(profile), occurrence)))
    )
    artifact = attempt.artifacts[0]
    assert artifact.local_filename is not None
    path = probe_path / artifact.local_filename
    if damage == "missing":
        path.unlink()
    elif damage == "corrupt":
        path.write_bytes(b"EDIT")
    elif damage == "symlink":
        path.unlink()
        path.symlink_to(probe_path / "foreign.wav")
        (probe_path / "foreign.wav").write_bytes(b"WAVE")
    else:
        receipt = probe_path / f"{occurrence}.json"
        raw = json.loads(receipt.read_text())
        raw["artifacts"][0]["local_filename"] = "foreign.wav"
        receipt.write_text(json.dumps(raw))
    with pytest.raises(ProbeRefusedError, match="Retained"):
        probe.load(occurrence)
    with pytest.raises(ProbeRefusedError, match="Retained"):
        await probe.fetch_outputs(attempt)
    assert views == 1


@pytest.mark.asyncio
async def test_interrupted_materialization_receipt_never_claims_retained_bytes(
    probe_path: Path, profile: ComfyProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    occurrence = uuid4()
    prompt = profile.prompt(request_for(profile))

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/prompt":
            return httpx2.Response(200, json={"prompt_id": str(occurrence)})
        if request.url.path.startswith("/history/"):
            return httpx2.Response(
                200,
                json={
                    str(occurrence): {
                        "prompt": [0, str(occurrence), prompt],
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {"1": {"audio": [{"filename": "sound.wav", "subfolder": "", "type": "output"}]}},
                    }
                },
            )
        return httpx2.Response(200, content=b"WAVE")

    real_link = os.link

    def interrupted_link(source: Path, destination: Path, *, follow_symlinks: bool = True) -> None:
        if destination.suffix == ".wav":
            msg = "publication interrupted"
            raise OSError(msg)
        real_link(source, destination, follow_symlinks=follow_symlinks)

    probe = probe_for(probe_path, profile, handler)
    attempt = await probe.reconcile(await probe.submit(probe.prepare(request_for(profile), occurrence)))
    monkeypatch.setattr(os, "link", interrupted_link)
    with pytest.raises(OSError, match="publication interrupted"):
        await probe.fetch_outputs(attempt)
    receipt = json.loads((probe_path / f"{occurrence}.json").read_text())
    assert receipt["artifacts"][0]["sha256"] == hashlib.sha256(b"WAVE").hexdigest()
    with pytest.raises(ProbeRefusedError, match="missing"):
        probe.load(occurrence)
    stage = probe_path / f".comfy-stage-v1-{occurrence}-0"
    assert stage.read_bytes() == b"WAVE"
    receipt_bytes = (probe_path / f"{occurrence}.json").read_bytes()
    monkeypatch.setattr(os, "link", real_link)
    restarted = probe_for(probe_path, profile, lambda _: pytest.fail("repair must not use HTTP"))
    repaired = restarted.repair_materialization(occurrence)
    assert repaired.model_dump(mode="json") == receipt
    assert (probe_path / f"{occurrence}.json").read_bytes() == receipt_bytes
    assert restarted.load(occurrence) == repaired
    assert restarted.repair_materialization(occurrence) == repaired
    assert (probe_path / receipt["artifacts"][0]["local_filename"]).read_bytes() == b"WAVE"
    assert not stage.exists()


@pytest.mark.asyncio
async def test_resume_total_bound_counts_prior_retained_bytes(
    probe_path: Path, profile: ComfyProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lychd.system.services import comfy_probe

    monkeypatch.setattr(comfy_probe, "MAX_OUTPUT_BYTES", 7)
    opening = OutputOpening.model_validate({**profile.outputs[0].model_dump(), "max_files": 2})
    profile = ComfyProfile.model_validate({**profile.model_dump(), "outputs": (opening,)})
    occurrence = uuid4()
    prompt = profile.prompt(request_for(profile))
    second_ready = False
    views: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/prompt":
            return httpx2.Response(200, json={"prompt_id": str(occurrence)})
        if request.url.path.startswith("/history/"):
            outputs = {
                "1": {
                    "audio": [
                        {"filename": name, "subfolder": "", "type": "output"} for name in ("first.wav", "second.wav")
                    ]
                }
            }
            return httpx2.Response(
                200,
                json={
                    str(occurrence): {
                        "prompt": [0, str(occurrence), prompt],
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": outputs,
                    }
                },
            )
        filename = request.url.params["filename"]
        views.append(filename)
        if filename == "first.wav":
            return httpx2.Response(200, content=b"WAVE")
        return httpx2.Response(200, content=b"GOOD") if second_ready else httpx2.Response(503)

    probe = probe_for(probe_path, profile, handler)
    attempt = await probe.reconcile(await probe.submit(probe.prepare(request_for(profile), occurrence)))
    with pytest.raises(httpx2.HTTPStatusError):
        await probe.fetch_outputs(attempt)
    partial = probe.load(occurrence)
    second_ready = True
    with pytest.raises(ProbeRefusedError, match="byte bound"):
        await probe.fetch_outputs(partial)
    assert probe.load(occurrence) == partial
    assert views == ["first.wav", "second.wav", "second.wav"]


@pytest.mark.parametrize(
    "remote", ["https://example.invalid/private.wav", "http://127.0.0.1:9999/audio.wav", "file:///tmp/audio.wav"]
)
def test_mutable_remote_input_refuses_before_attempt_or_transport(probe_path: Path, remote: str) -> None:
    graph = canonical_json({"1": {"class_type": "AudioLoader", "inputs": {"audio": "local.wav"}}})
    selected = ComfyProfile(
        endpoint="http://127.0.0.1:8188",
        deployment_revision="reviewed-test",
        review_reference="test-only",
        workflow_json=graph,
        workflow_sha256=json_digest(graph),
        allowed_node_classes=("AudioLoader",),
        models=(),
        mutable_inputs=(MutableInput(name="audio", node_id="1", input_name="audio", kind="text"),),
        outputs=(OutputOpening(node_id="1", kind="audio", receiving_owner="riffmaw.music", extensions=(".wav",)),),
    )
    calls: list[httpx2.Request] = []
    probe = probe_for(probe_path, selected, lambda request: calls.append(request) or httpx2.Response(200))
    request = ComfyRequest(profile_sha256=selected.digest, inputs_json=canonical_json({"audio": remote}))
    with pytest.raises(ValueError, match="remote input"):
        probe.prepare(request)
    assert not calls
    assert not list(probe_path.glob("*.json"))
    ordinary = ComfyRequest(profile_sha256=selected.digest, inputs_json=canonical_json({"audio": "local-take.wav"}))
    assert selected.prompt(ordinary)["1"]["inputs"]["audio"] == "local-take.wav"


def test_copied_unvalidated_profile_refused_before_binding(probe_path: Path, profile: ComfyProfile) -> None:
    invalid = profile.model_copy(update={"endpoint": "https://example.invalid"})
    with pytest.raises(ValueError, match="loopback"):
        probe_for(probe_path, invalid, lambda _: httpx2.Response(200))
    assert not list(probe_path.glob("*.json"))


def staged_attempt(probe_path: Path, profile: ComfyProfile) -> tuple[ComfyProbe, ComfyAttempt, Path, Path]:
    """Reconstruct a post-pin receipt and its exact local publication stage."""
    probe = probe_for(probe_path, profile, lambda _: pytest.fail("local repair must not use HTTP"))
    attempt = probe.prepare(request_for(profile))
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
    (probe_path / f"{attempt.occurrence_id}.json").write_text(attempt.model_dump_json())
    stage = probe_path / f".comfy-stage-v1-{attempt.occurrence_id}-0"
    stage.write_bytes(b"WAVE")
    return probe, attempt, stage, probe_path / local


@pytest.mark.parametrize("damage", ["missing", "corrupt", "symlink", "directory", "fifo", "oversized"])
def test_repair_refuses_invalid_stage_without_mutating_receipt(
    probe_path: Path, profile: ComfyProfile, damage: str
) -> None:
    probe, attempt, stage, destination = staged_attempt(probe_path, profile)
    stage.unlink()
    if damage == "corrupt":
        stage.write_bytes(b"EDIT")
    elif damage == "symlink":
        foreign = probe_path / "foreign.wav"
        foreign.write_bytes(b"WAVE")
        stage.symlink_to(foreign)
    elif damage == "directory":
        stage.mkdir()
    elif damage == "fifo":
        os.mkfifo(stage)
    elif damage == "oversized":
        stage.write_bytes(b"TOO-LARGE")
    receipt = probe_path / f"{attempt.occurrence_id}.json"
    original = receipt.read_bytes()
    with pytest.raises(ProbeRefusedError, match="Retained"):
        probe.repair_materialization(attempt.occurrence_id)
    assert receipt.read_bytes() == original
    assert not destination.exists()
    assert stage.exists() == (damage != "missing")


@pytest.mark.parametrize("damage", ["corrupt", "symlink", "directory", "fifo"])
def test_repair_preserves_conflicting_final_and_exact_stage(
    probe_path: Path, profile: ComfyProfile, damage: str
) -> None:
    probe, attempt, stage, destination = staged_attempt(probe_path, profile)
    if damage == "corrupt":
        destination.write_bytes(b"EDIT")
    elif damage == "symlink":
        destination.symlink_to(stage)
    elif damage == "directory":
        destination.mkdir()
    else:
        os.mkfifo(destination)
    original_inode = destination.lstat().st_ino
    with pytest.raises(ProbeRefusedError, match="Retained"):
        probe.repair_materialization(attempt.occurrence_id)
    assert destination.lstat().st_ino == original_inode
    assert stage.read_bytes() == b"WAVE"


@pytest.mark.asyncio
async def test_pre_pin_stage_refuses_repair_and_refetch_before_http(probe_path: Path, profile: ComfyProfile) -> None:
    probe, attempt, stage, destination = staged_attempt(probe_path, profile)
    unpinned = attempt.artifacts[0].model_copy(update={"local_filename": None, "sha256": None, "size_bytes": None})
    attempt = attempt.model_copy(update={"artifacts": (unpinned,)})
    receipt = probe_path / f"{attempt.occurrence_id}.json"
    receipt.write_text(attempt.model_dump_json())
    original = receipt.read_bytes()
    with pytest.raises(ProbeRefusedError, match="Unpinned"):
        probe.repair_materialization(attempt.occurrence_id)
    with pytest.raises(ProbeRefusedError, match="Unpinned"):
        await probe.fetch_outputs(probe.load(attempt.occurrence_id))
    assert stage.read_bytes() == b"WAVE"
    assert receipt.read_bytes() == original
    assert not destination.exists()


@pytest.mark.parametrize(
    "changed", ["occurrence_id", "profile_sha256", "request_sha256", "prompt_sha256", "local_filename", "filename"]
)
def test_repair_revalidates_receipt_identity_before_installing(
    probe_path: Path, profile: ComfyProfile, changed: str
) -> None:
    probe, attempt, stage, destination = staged_attempt(probe_path, profile)
    receipt = probe_path / f"{attempt.occurrence_id}.json"
    raw = json.loads(receipt.read_text())
    if changed in {"local_filename", "filename"}:
        raw["artifacts"][0][changed] = "foreign.txt"
    else:
        raw[changed] = str(uuid4()) if changed == "occurrence_id" else "0" * 64
    receipt.write_text(json.dumps(raw))
    original = receipt.read_bytes()
    with pytest.raises(ProbeRefusedError):
        probe.repair_materialization(attempt.occurrence_id)
    assert receipt.read_bytes() == original
    assert stage.read_bytes() == b"WAVE"
    assert not destination.exists()


@pytest.mark.asyncio
async def test_repair_and_fetch_share_exclusive_lock(probe_path: Path, profile: ComfyProfile) -> None:
    probe, attempt, stage, destination = staged_attempt(probe_path, profile)
    with (probe_path / f"{attempt.occurrence_id}.fetch.lock").open("w") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            probe.repair_materialization(attempt.occurrence_id)
        with pytest.raises(BlockingIOError):
            await probe.fetch_outputs(attempt)
    assert stage.read_bytes() == b"WAVE"
    assert not destination.exists()


@pytest.mark.asyncio
async def test_repair_preserves_prior_files_then_fetches_only_unpinned_output(
    probe_path: Path, profile: ComfyProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lychd.system.services import comfy_probe

    opening = profile.outputs[0].model_copy(update={"max_files": 3})
    profile = ComfyProfile.model_validate({**profile.model_dump(), "outputs": (opening,)})
    probe, attempt, stage, destination = staged_attempt(probe_path, profile)
    stage.rename(destination)
    first = attempt.artifacts[0]
    second = first.model_copy(
        update={"filename": "second.wav", "local_filename": f"{attempt.occurrence_id}-1-{first.sha256}.wav"}
    )
    third = first.model_copy(
        update={"filename": "third.wav", "local_filename": None, "sha256": None, "size_bytes": None}
    )
    attempt = attempt.model_copy(update={"artifacts": (first, second, third)})
    receipt = probe_path / f"{attempt.occurrence_id}.json"
    receipt.write_text(attempt.model_dump_json())
    second_stage = probe_path / f".comfy-stage-v1-{attempt.occurrence_id}-1"
    second_stage.write_bytes(b"WAVE")
    monkeypatch.setattr(comfy_probe, "MAX_OUTPUT_BYTES", 12)
    original = receipt.read_bytes()
    repaired = probe.repair_materialization(attempt.occurrence_id)
    assert repaired == attempt
    assert receipt.read_bytes() == original
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "GET"
        assert request.url.path == "/view"
        calls.append(request.url.params["filename"])
        return httpx2.Response(200, content=b"GOOD")

    result = await probe_for(probe_path, profile, handler).fetch_outputs(repaired)
    assert calls == ["third.wav"]
    assert result.artifacts[:2] == repaired.artifacts[:2]
    assert result.artifacts[2].sha256 == hashlib.sha256(b"GOOD").hexdigest()
    assert destination.read_bytes() == b"WAVE"


def test_repair_does_not_advance_unknown_submission(probe_path: Path, profile: ComfyProfile) -> None:
    probe = probe_for(probe_path, profile, lambda _: pytest.fail("repair must not use HTTP"))
    attempt = probe.prepare(request_for(profile)).model_copy(update={"state": "indeterminate"})
    receipt = probe_path / f"{attempt.occurrence_id}.json"
    receipt.write_text(attempt.model_dump_json())
    original = receipt.read_bytes()
    with pytest.raises(ProbeRefusedError, match="technical success"):
        probe.repair_materialization(attempt.occurrence_id)
    assert receipt.read_bytes() == original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault", ["stage_sync", "receipt_replace", "receipt_sync", "final_sync", "stage_unlink", "cleanup_sync"]
)
async def test_publication_faults_preserve_repairable_or_ambiguous_evidence(  # noqa: C901 - explicit publication fault matrix
    probe_path: Path, profile: ComfyProfile, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    occurrence = uuid4()
    prompt = profile.prompt(request_for(profile))

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/prompt":
            return httpx2.Response(200, json={"prompt_id": str(occurrence)})
        if request.url.path.startswith("/history/"):
            return httpx2.Response(
                200,
                json={
                    str(occurrence): {
                        "prompt": [0, str(occurrence), prompt],
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {"1": {"audio": [{"filename": "sound.wav", "subfolder": "", "type": "output"}]}},
                    }
                },
            )
        return httpx2.Response(200, content=b"WAVE")

    probe = probe_for(probe_path, profile, handler)
    attempt = await probe.reconcile(await probe.submit(probe.prepare(request_for(profile), occurrence)))
    real_sync, real_replace, real_unlink = os.fsync, Path.replace, Path.unlink
    directory_syncs = 0
    sync_faults = {"stage_sync": 1, "receipt_sync": 2, "final_sync": 3, "cleanup_sync": 4}
    stage = probe_path / f".comfy-stage-v1-{occurrence}-0"
    failure = "publication interrupted"

    def interrupted_sync(fd: int) -> None:
        nonlocal directory_syncs
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            directory_syncs += 1
            if directory_syncs == sync_faults.get(fault):
                raise OSError(failure)
        real_sync(fd)

    def interrupted_replace(source: Path, target: Path) -> Path:
        if fault == "receipt_replace":
            raise OSError(failure)
        return real_replace(source, target)

    def interrupted_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if fault == "stage_unlink" and path == stage:
            raise OSError(failure)
        real_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", interrupted_sync)
        patch.setattr(Path, "replace", interrupted_replace)
        patch.setattr(Path, "unlink", interrupted_unlink)
        with pytest.raises(OSError, match="publication interrupted"):
            await probe.fetch_outputs(attempt)
    receipt = probe_path / f"{occurrence}.json"
    original = receipt.read_bytes()
    restarted = probe_for(probe_path, profile, lambda _: pytest.fail("recovery must not use HTTP"))
    if fault in {"stage_sync", "receipt_replace"}:
        with pytest.raises(ProbeRefusedError, match="Unpinned"):
            restarted.repair_materialization(occurrence)
        with pytest.raises(ProbeRefusedError, match="Unpinned"):
            await restarted.fetch_outputs(restarted.load(occurrence))
        assert stage.read_bytes() == b"WAVE"
    else:
        repaired = restarted.repair_materialization(occurrence)
        assert restarted.load(occurrence) == repaired
        assert restarted.repair_materialization(occurrence) == repaired
        assert repaired.artifacts[0].sha256 == hashlib.sha256(b"WAVE").hexdigest()
        assert not stage.exists()
    assert receipt.read_bytes() == original
