from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import httpx
import pytest

from lychd.config.settings.root import get_settings
from lychd.domain.animation.capabilities import CapabilityPhase
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.extensions.builtin.animator.exllamav3 import (
    ExLlamaV3Connector,
    TabbyAPIAuthKeys,
    TabbyAPIAuthSecretError,
    TabbyAPIControlPlane,
    TabbyAPIControlPlaneError,
    load_tabbyapi_auth_keys,
)
from lychd.extensions.builtin.animator.runtimes import ExLlamaV3RuntimeAdapter
from lychd.extensions.builtin.animator.soulstones import ExLlamaV3SoulstoneConfig
from lychd.system.schemas import QuadletContainer, QuadletPod
from lychd.system.services.scribe import ScribeService
from lychd.system.unit_names import animator_target_unit

respx = pytest.importorskip("respx")

_BASE_URL = "http://tabby:5000/v1"
_API_KEY = "data-plane-test-key-00000000000001"
_ADMIN_KEY = "control-plane-test-key-0000000001"
_ADMIN_HEADERS = {"Authorization": f"Bearer {_ADMIN_KEY}"}


def _write_auth_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    name: str = "tabby_exl3_auth",
    api_key: str = _API_KEY,
    admin_key: str = _ADMIN_KEY,
) -> None:
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(tmp_path))
    (tmp_path / name).write_text(
        f'{{"api_key":"{api_key}","admin_key":"{admin_key}"}}',
        encoding="utf-8",
    )


def _control_plane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TabbyAPIControlPlane:
    _write_auth_secret(tmp_path, monkeypatch)
    control = TabbyAPIControlPlane()
    control.register_runtime(_BASE_URL, "tabby_exl3_auth")
    return control


class _HangingSSE(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b'data: {"status":"processing","module":1,"modules":2}\n\n'
        await asyncio.Event().wait()

    async def aclose(self) -> None:
        return


class _BrokenSSE(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b'data: {"status":"processing","module":1,"modules":2}\n\n'
        message = "tabby process disappeared"
        raise httpx.ReadError(message)

    async def aclose(self) -> None:
        return


def _stone() -> ExLlamaV3SoulstoneConfig:
    return ExLlamaV3SoulstoneConfig.model_validate(
        {
            "name": "exl3-router",
            "auth_secret_name": "tabby_exl3_auth",
            "volumes": ["/data/models:/app/models:ro"],
            "models": [
                {
                    "id": "daily-driver",
                    "path": "/app/models/qwen-exl3",
                    "format": "EXL3",
                },
                {
                    "id": "small",
                    "path": "/app/models/small-exl3",
                },
            ],
        }
    )


def test_tabbyapi_auth_keys_do_not_leak_through_repr() -> None:
    keys = TabbyAPIAuthKeys(api_key=_API_KEY, admin_key=_ADMIN_KEY)
    assert _API_KEY not in repr(keys)
    assert _ADMIN_KEY not in repr(keys)


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ("not-json", "JSON object"),
        ('{"api_key":"one","api_key":"two","admin_key":"three"}', "Duplicate JSON key"),
        (f'{{"api_key":"short","admin_key":"{_ADMIN_KEY}"}}', "no valid api_key"),
        (f'{{"api_key":"{_API_KEY}","admin_key":"short"}}', "no valid admin_key"),
        (f'{{"api_key":"{_API_KEY}","admin_key":"{_API_KEY}"}}', "distinct API and admin"),
        (
            f'{{"api_key":["{_API_KEY}","{_ADMIN_KEY}"],"admin_key":"{_ADMIN_KEY}"}}',
            "distinct API and admin",
        ),
        (f'{{"api_key":"{_API_KEY}\\u0000","admin_key":"{_ADMIN_KEY}"}}', "no valid api_key"),
        (f'{{"api_key":"{_API_KEY}","admin_key":"{_ADMIN_KEY}é"}}', "no valid admin_key"),
    ],
)
def test_tabbyapi_auth_document_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    document: str,
    message: str,
) -> None:
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(tmp_path))
    (tmp_path / "tabby_auth").write_text(document, encoding="utf-8")

    with pytest.raises(TabbyAPIAuthSecretError, match=message):
        load_tabbyapi_auth_keys("tabby_auth")


def test_tabbyapi_auth_document_must_exist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(tmp_path))

    with pytest.raises(TabbyAPIAuthSecretError, match="unavailable"):
        load_tabbyapi_auth_keys("missing")


def test_tabbyapi_auth_document_must_be_utf8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(tmp_path))
    (tmp_path / "tabby_auth").write_bytes(b"\xff\xfe")

    with pytest.raises(TabbyAPIAuthSecretError, match="unavailable"):
        load_tabbyapi_auth_keys("tabby_auth")


def test_exllamav3_plan_is_dynamic_and_uses_pinned_private_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_auth_secret(tmp_path, monkeypatch)
    stone = _stone()
    adapter = ExLlamaV3RuntimeAdapter()
    registry = RuntimeAdapterRegistry(adapters=[adapter])

    runtime = registry.build_runtime(stone)
    assert runtime is not None
    connector = cast("ExLlamaV3Connector", runtime.connector)
    plan = registry.plan(stone)
    specs = registry.build_capability_specs(stone)

    assert stone.quadlet.image.startswith("ghcr.io/theroyallab/tabbyapi@sha256:")
    assert connector.runtime_model_name("daily-driver") == "qwen-exl3"
    assert connector.model_id_for_runtime("qwen-exl3") == "daily-driver"
    assert connector._resolve_api_key() == _API_KEY  # pyright: ignore[reportPrivateUsage]
    assert connector.get_model(model_id="daily-driver").model_name == "qwen-exl3"
    assert {spec.model_id for spec in specs} == {"daily-driver", "small"}
    assert all(spec.is_dynamic for spec in specs)
    assert all(spec.metadata["server"] == "tabbyapi" for spec in specs)
    assert plan.exec_args == []
    assert plan.env_overrides["TABBY_NETWORK_DISABLE_AUTH"] == "false"
    assert plan.env_overrides["TABBY_LOG_LEVEL"] == "WARNING"
    assert plan.env_overrides["TABBY_MODEL_MODEL_NAME"] == ""
    assert plan.secrets == ["tabby_exl3_auth,target=/app/api_tokens.yml,mode=0444"]
    assert plan.unit_binds_to == ["lychd-vessel.service"]
    assert "--shm-size=8g" not in plan.podman_args
    assert "--tmpfs=/app/logs:rw,nosuid,nodev,noexec,mode=1777" in plan.podman_args
    assert not any(argument.startswith("--ulimit=") for argument in plan.podman_args)


def test_exllamav3_transmutation_isolates_auth_and_sizes_shared_ipc() -> None:
    registry = RuntimeAdapterRegistry(adapters=[ExLlamaV3RuntimeAdapter()])
    manifests = Transmuter(settings=get_settings(), runtime_planner=registry).transmute_all([_stone()])
    pod = next(manifest for manifest in manifests if isinstance(manifest, QuadletPod))
    containers = {manifest.container_name: manifest for manifest in manifests if isinstance(manifest, QuadletContainer)}
    tabby = containers["lychd-exl3-router"]
    vessel = containers["lychd-vessel"]

    assert pod.shm_size == "8g"
    assert tabby.secrets == ["tabby_exl3_auth,target=/app/api_tokens.yml,mode=0444"]
    assert tabby.binds_to == [animator_target_unit("exl3-router"), "lychd-vessel.service"]
    assert "lychd-vessel.service" in tabby.after
    assert "--shm-size=8g" not in tabby.podman_args
    assert "tabby_exl3_auth" in vessel.secrets
    assert "tabby_exl3_auth" not in containers["lychd-phylactery"].secrets
    assert "tabby_exl3_auth" not in containers["lychd-migrate"].secrets
    rendered_truth = "\n".join(manifest.model_dump_json() for manifest in manifests)
    assert _API_KEY not in rendered_truth
    assert _ADMIN_KEY not in rendered_truth


def test_exllamav3_control_secret_cannot_be_mounted_by_another_soulstone() -> None:
    registry = RuntimeAdapterRegistry(adapters=[ExLlamaV3RuntimeAdapter()])
    reader = GenericSoulstoneConfig.model_validate(
        {
            "name": "secret-reader",
            "quadlet": {"image": "example/reader"},
            "secret_env_files": {"STOLEN": "tabby_exl3_auth"},
        }
    )

    with pytest.raises(ValueError, match="cannot alias a Soulstone control-plane secret"):
        Transmuter(settings=get_settings(), runtime_planner=registry).transmute_all([_stone(), reader])


def test_exllamav3_rendered_quadlets_keep_auth_scoped_and_opaque(tmp_path: Path) -> None:
    manifests = Transmuter(
        settings=get_settings(),
        runtime_planner=RuntimeAdapterRegistry(adapters=[ExLlamaV3RuntimeAdapter()]),
    ).transmute_all([_stone()])
    output_dir = tmp_path / "quadlet"
    systemd_dir = tmp_path / "systemd"
    output_dir.mkdir()
    systemd_dir.mkdir()
    ScribeService(output_dir=output_dir, systemd_dir=systemd_dir).generate_all(manifests)

    tabby = (output_dir / "lychd-exl3-router.container").read_text(encoding="utf-8")
    vessel = (output_dir / "lychd-vessel.container").read_text(encoding="utf-8")
    phylactery = (output_dir / "lychd-phylactery.container").read_text(encoding="utf-8")
    migrator = (output_dir / "lychd-migrate.container").read_text(encoding="utf-8")
    rendered = f"{tabby}\n{vessel}\n{phylactery}\n{migrator}"

    assert "Secret=tabby_exl3_auth,target=/app/api_tokens.yml,mode=0444" in tabby
    assert "Secret=tabby_exl3_auth" in vessel
    assert "tabby_exl3_auth" not in phylactery
    assert "tabby_exl3_auth" not in migrator
    assert _API_KEY not in rendered
    assert _ADMIN_KEY not in rendered


@pytest.mark.asyncio
async def test_two_tabby_runtimes_keep_data_and_admin_keys_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second_api = "second-data-plane-key-00000000000001"
    second_admin = "second-control-plane-key-00000000001"
    _write_auth_secret(tmp_path, monkeypatch)
    _write_auth_secret(
        tmp_path,
        monkeypatch,
        name="tabby_second_auth",
        api_key=second_api,
        admin_key=second_admin,
    )
    second = ExLlamaV3SoulstoneConfig.model_validate(
        {
            "name": "exl3-second",
            "port": 5001,
            "base_url": "http://localhost:5001/v1",
            "auth_secret_name": "tabby_second_auth",
            "volumes": ["/data/models:/app/models:ro"],
            "models": [{"id": "second", "path": "/app/models/second-exl3"}],
        }
    )
    control = TabbyAPIControlPlane()
    registry = RuntimeAdapterRegistry(adapters=[ExLlamaV3RuntimeAdapter(control_plane=control)])
    first_runtime = registry.build_runtime(_stone())
    second_runtime = registry.build_runtime(second)
    assert first_runtime is not None
    assert second_runtime is not None
    first_connector = cast("ExLlamaV3Connector", first_runtime.connector)
    second_connector = cast("ExLlamaV3Connector", second_runtime.connector)
    assert first_connector._resolve_api_key() == _API_KEY  # pyright: ignore[reportPrivateUsage]
    assert second_connector._resolve_api_key() == second_api  # pyright: ignore[reportPrivateUsage]

    first_headers = {"Authorization": f"Bearer {_ADMIN_KEY}"}
    second_headers = {"Authorization": f"Bearer {second_admin}"}
    with respx.mock:
        for port, headers, model_id in (
            (5000, first_headers, "qwen-exl3"),
            (5001, second_headers, "second-exl3"),
        ):
            root = f"http://localhost:{port}"
            respx.get(f"{root}/health", headers=headers).mock(
                return_value=httpx.Response(200, json={"status": "healthy"})
            )
            respx.get(f"{root}/v1/models", headers=headers).mock(
                return_value=httpx.Response(200, json={"data": [{"id": model_id}]})
            )
            respx.get(f"{root}/v1/model", headers=headers).mock(
                return_value=httpx.Response(503, json={"detail": "No models are currently loaded."})
            )
        await control.inspect(base_url=first_connector.base_url)
        await control.inspect(base_url=second_connector.base_url)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"volumes": []}, "only the read-only /app/models mount"),
        ({"volumes": ["/data/models:/app/models"]}, "mounted read-only"),
        (
            {
                "volumes": [
                    "/data/models:/app/models:ro",
                    "/data/fake-auth:/app/api_tokens.yml:ro",
                ]
            },
            "only the read-only /app/models mount",
        ),
        (
            {
                "model_dir": "/app",
                "volumes": ["/data/override:/app:ro"],
                "models": [{"id": "shadow", "path": "/app/shadow"}],
            },
            "fixed at /app/models",
        ),
        ({"exec": ["main.py"]}, "exec passthrough"),
        ({"env_vars": {"TABBY_MODEL_MODEL_NAME": "surprise"}}, "env_vars are closed"),
        ({"env_vars": {"SAFE": "ok\nExec=/bin/sh"}}, "env_vars are closed"),
        ({"secret_env_files": {"LEAK": "lychd_db_password"}}, "secret_env_files are closed"),
        ({"devices": ["nvidia.com/gpu=all\nExec=/bin/sh"]}, "NVIDIA CDI selectors"),
        ({"disable_auth": True}, "Input should be False"),
        ({"model_format": "EXL2"}, "EXL3 or RAW"),
        ({"auth_secret_name": "safe,target=/tmp/evil"}, "option-safe Podman secret name"),
        ({"auth_secret_name": "safe\n"}, "option-safe Podman secret name"),
        ({"quadlet": {"image": "ghcr.io/example/unverified:latest"}}, "digest-pinned TabbyAPI"),
        (
            {
                "models": [
                    {
                        "id": "escape",
                        "path": "/app/models/..",
                    }
                ]
            },
            "path must end",
        ),
        (
            {"models": [{"id": "inert", "path": "/app/models/inert", "runtime_id": "inert"}]},
            "Extra inputs are not permitted",
        ),
        (
            {"models": [{"id": "control", "path": "/app/models/control\nname"}]},
            "path must end",
        ),
        ({"base_url": "https://localhost:5000/v1"}, "must use plain HTTP"),
        ({"base_url": "http://user:secret@localhost:5000/v1"}, "embedded credentials"),
        ({"base_url": "http://localhost:5000/v1?mode=unsafe"}, "query or fragment"),
    ],
)
def test_exllamav3_rejects_lifecycle_bypasses(override: dict[str, object], message: str) -> None:
    payload = {
        "name": "guarded",
        "auth_secret_name": "tabby_guarded_auth",
        "volumes": ["/data/models:/app/models:ro"],
        "models": [{"id": "model", "path": "/app/models/model"}],
        **override,
    }
    with pytest.raises(ValueError, match=message):
        ExLlamaV3SoulstoneConfig.model_validate(payload)


@pytest.mark.asyncio
async def test_tabbyapi_healthy_without_model_is_activatable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy", "issues": []})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"object": "list", "data": [{"id": "qwen-exl3"}]})
        )
        respx.get("http://tabby:5000/v1/model", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(503, json={"detail": "No models are currently loaded."})
        )
        lifecycle = await control.inspect(base_url=_BASE_URL)

    assert lifecycle.health == "ok"
    assert lifecycle.active_model is None
    assert lifecycle.available_models == ["qwen-exl3"]


@pytest.mark.asyncio
async def test_tabbyapi_refuses_unregistered_unauthenticated_control() -> None:
    with pytest.raises(TabbyAPIControlPlaneError, match="no registered auth secret"):
        await TabbyAPIControlPlane().inspect(base_url=_BASE_URL)


@pytest.mark.asyncio
async def test_tabbyapi_successful_current_model_requires_an_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy", "issues": []})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"data": [{"id": "qwen-exl3"}]})
        )
        respx.get("http://tabby:5000/v1/model", headers=_ADMIN_HEADERS).mock(return_value=httpx.Response(200, json={}))
        with pytest.raises(TabbyAPIControlPlaneError, match="without a non-empty id") as caught:
            await control.inspect(base_url=_BASE_URL)

    assert caught.value.unreachable is False


@pytest.mark.asyncio
async def test_tabbyapi_malformed_inventory_is_protocol_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy", "issues": []})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"data": {"id": "not-a-list"}})
        )
        with pytest.raises(TabbyAPIControlPlaneError, match="no data list") as caught:
            await control.inspect(base_url=_BASE_URL)

    assert caught.value.unreachable is False


@pytest.mark.parametrize(
    "data",
    [
        [{"id": "qwen-exl3"}, "not-a-card"],
        [{"id": "qwen-exl3"}, {}],
        [{"id": "qwen-exl3"}, {"id": ""}],
    ],
)
@pytest.mark.asyncio
async def test_tabbyapi_rejects_every_malformed_inventory_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    data: list[object],
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy"})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"data": data})
        )
        with pytest.raises(TabbyAPIControlPlaneError, match="entry"):
            await control.inspect(base_url=_BASE_URL)


@pytest.mark.parametrize("slots", [True, False, 0, -1, "4"])
@pytest.mark.asyncio
async def test_tabbyapi_rejects_invalid_max_batch_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    slots: object,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy"})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"data": [{"id": "qwen-exl3"}]})
        )
        respx.get("http://tabby:5000/v1/model", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"id": "qwen-exl3", "parameters": {"max_batch_size": slots}})
        )
        with pytest.raises(TabbyAPIControlPlaneError, match="positive integer"):
            await control.inspect(base_url=_BASE_URL)


@pytest.mark.parametrize("status", [204, 302])
@pytest.mark.asyncio
async def test_tabbyapi_load_requires_pinned_http_200_acceptance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.post("http://tabby:5000/v1/model/load", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(status, text="not accepted")
        )
        with pytest.raises(TabbyAPIControlPlaneError, match=f"status {status}"):
            await control.load_model(_BASE_URL, "qwen-exl3")

    assert control._loads == {}  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_tabbyapi_same_model_callers_share_rejected_acceptance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def reject(base_url: str, operation: Any) -> None:
        entered.set()
        await release.wait()
        control._record_load_error(  # pyright: ignore[reportPrivateUsage]
            control._runtime_key(base_url),  # pyright: ignore[reportPrivateUsage]
            operation,
            TabbyAPIControlPlaneError("rejected once", status=400),
        )

    monkeypatch.setattr(control, "_drive_model_load", reject)
    first = asyncio.create_task(control.load_model(_BASE_URL, "qwen-exl3"))
    await entered.wait()
    second = asyncio.create_task(control.load_model(_BASE_URL, "qwen-exl3"))
    await asyncio.sleep(0)
    release.set()
    results = await asyncio.gather(first, second, return_exceptions=True)

    assert all(isinstance(result, TabbyAPIControlPlaneError) for result in results)
    assert control._loads == {}  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_tabbyapi_preaccept_rejection_does_not_poison_health_or_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.post("http://tabby:5000/v1/model/load", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(401, json={"detail": "bad control key"})
        )
        with pytest.raises(TabbyAPIControlPlaneError, match="status 401"):
            await control.load_model(_BASE_URL, "qwen-exl3")

    with respx.mock:
        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy"})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"data": [{"id": "old-model"}, {"id": "qwen-exl3"}]})
        )
        respx.get("http://tabby:5000/v1/model", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"id": "old-model"})
        )
        lifecycle = await control.inspect(base_url=_BASE_URL)

    assert lifecycle.health == "ok"
    assert lifecycle.active_model == "old-model"

    terminal = 'data: {"model_type":"model","module":1,"modules":1,"status":"finished"}\n\n'
    with respx.mock:
        respx.post("http://tabby:5000/v1/model/load", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, text=terminal, headers={"content-type": "text/event-stream"})
        )
        assert await control.load_model(_BASE_URL, "qwen-exl3") is True
        operation = next(iter(control._loads.values()))  # pyright: ignore[reportPrivateUsage]
        assert operation.task is not None
        await asyncio.wait_for(operation.task, timeout=1.0)


@pytest.mark.asyncio
async def test_tabbyapi_rejects_inconsistent_finished_model_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    malformed = 'data: {"model_type":"model","module":1,"modules":2,"status":"finished"}\n\n'
    with respx.mock:
        respx.post("http://tabby:5000/v1/model/load", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, text=malformed, headers={"content-type": "text/event-stream"})
        )
        assert await control.load_model(_BASE_URL, "qwen-exl3") is True
        operation = next(iter(control._loads.values()))  # pyright: ignore[reportPrivateUsage]
        assert operation.task is not None
        await asyncio.wait_for(operation.task, timeout=1.0)

    assert operation.ambiguous is True
    assert "counter" in str(operation.uncertainty)


@pytest.mark.asyncio
async def test_tabbyapi_load_consumes_all_sse_stages_then_confirms_current_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sse = (
        'data: {"model_type":"vision","module":1,"modules":1,"status":"finished"}\n\n'
        'data: {"model_type":"model","module":1,"modules":2,"status":"processing"}\n\n'
        'data: {"model_type":"model","module":2,"modules":2,"status":"finished"}\n\n'
    )
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.post("http://tabby:5000/v1/model/load", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})
        )
        assert await control.load_model(_BASE_URL, "qwen-exl3") is True
        operation = next(iter(control._loads.values()))  # pyright: ignore[reportPrivateUsage]
        assert operation.task is not None
        await asyncio.wait_for(operation.task, timeout=1.0)

        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy"})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"data": [{"id": "qwen-exl3"}]})
        )
        respx.get("http://tabby:5000/v1/model", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(
                200,
                json={"id": "qwen-exl3", "parameters": {"max_batch_size": 4}},
            )
        )
        lifecycle = await control.inspect(base_url=_BASE_URL)

    assert lifecycle.health == "ok"
    assert lifecycle.active_model == "qwen-exl3"
    assert lifecycle.total_slots == 4
    assert control._loads == {}  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_tabbyapi_terminal_load_missing_after_restart_releases_fence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = 'data: {"model_type":"model","module":1,"modules":1,"status":"finished"}\n\n'
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.post("http://tabby:5000/v1/model/load", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, text=terminal, headers={"content-type": "text/event-stream"})
        )
        assert await control.load_model(_BASE_URL, "qwen-exl3") is True
        operation = next(iter(control._loads.values()))  # pyright: ignore[reportPrivateUsage]
        assert operation.task is not None
        await asyncio.wait_for(operation.task, timeout=1.0)

        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy"})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"data": [{"id": "qwen-exl3"}, {"id": "small-exl3"}]})
        )
        respx.get("http://tabby:5000/v1/model", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(503, json={"detail": "No models are currently loaded."})
        )
        lifecycle = await control.inspect(base_url=_BASE_URL)

    assert lifecycle.health == "ok"
    assert lifecycle.raw["load_reconciliation"] == "finished_stream_without_active_model"
    assert control._loads == {}  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_tabbyapi_midstream_crash_is_contained_until_vessel_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.post("http://tabby:5000/v1/model/load", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(
                200,
                stream=_BrokenSSE(),
                headers={"content-type": "text/event-stream"},
            )
        )
        assert await control.load_model(_BASE_URL, "qwen-exl3") is True
        operation = next(iter(control._loads.values()))  # pyright: ignore[reportPrivateUsage]
        assert operation.task is not None
        await asyncio.wait_for(operation.task, timeout=1.0)

        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy"})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"data": [{"id": "qwen-exl3"}, {"id": "small-exl3"}]})
        )
        respx.get("http://tabby:5000/v1/model", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(503, json={"detail": "No models are currently loaded."})
        )
        lifecycle = await control.inspect(base_url=_BASE_URL)

    assert lifecycle.health == "error"
    assert "Restart the caged Vessel" in str(lifecycle.raw["load_error"])
    with pytest.raises(TabbyAPIControlPlaneError, match="refusing concurrent load"):
        await control.load_model(_BASE_URL, "small-exl3")


@pytest.mark.asyncio
async def test_tabbyapi_stream_error_becomes_error_not_false_warmth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    error_sse = 'data: {"error":{"message":"CUDA out of memory","trace":null}}\n\n'
    with respx.mock:
        respx.post("http://tabby:5000/v1/model/load", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, text=error_sse, headers={"content-type": "text/event-stream"})
        )
        assert await control.load_model(_BASE_URL, "qwen-exl3") is True
        operation = next(iter(control._loads.values()))  # pyright: ignore[reportPrivateUsage]
        assert operation.task is not None
        await asyncio.wait_for(operation.task, timeout=1.0)

        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy"})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"data": [{"id": "qwen-exl3"}]})
        )
        respx.get("http://tabby:5000/v1/model", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(503, json={"detail": "No models are currently loaded."})
        )
        lifecycle = await control.inspect(base_url=_BASE_URL)

    assert lifecycle.health == "error"
    assert "CUDA out of memory" in str(lifecycle.raw["load_error"])


@pytest.mark.asyncio
async def test_tabbyapi_ambiguous_stream_yields_to_verified_current_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    truncated_sse = (
        'data: {"model_type":"vision","status":"finished","module":1,"modules":1}\n\n'
        'data: {"model_type":"model","status":"processing","module":1,"modules":2}\n\n'
    )
    with respx.mock:
        respx.post("http://tabby:5000/v1/model/load", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, text=truncated_sse, headers={"content-type": "text/event-stream"})
        )
        assert await control.load_model(_BASE_URL, "qwen-exl3") is True
        operation = next(iter(control._loads.values()))  # pyright: ignore[reportPrivateUsage]
        assert operation.task is not None
        await asyncio.wait_for(operation.task, timeout=1.0)
        assert operation.ambiguous is True
        assert operation.error is None

        respx.get("http://tabby:5000/health", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"status": "healthy"})
        )
        respx.get("http://tabby:5000/v1/models", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"data": [{"id": "qwen-exl3"}]})
        )
        respx.get("http://tabby:5000/v1/model", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(200, json={"id": "qwen-exl3"})
        )
        lifecycle = await control.inspect(base_url=_BASE_URL)

    assert lifecycle.health == "ok"
    assert lifecycle.active_model == "qwen-exl3"
    assert control._loads == {}  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_tabbyapi_abandon_cancels_only_observer_and_retains_tombstone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = _control_plane(tmp_path, monkeypatch)
    with respx.mock:
        respx.post("http://tabby:5000/v1/model/load", headers=_ADMIN_HEADERS).mock(
            return_value=httpx.Response(
                200,
                stream=_HangingSSE(),
                headers={"content-type": "text/event-stream"},
            )
        )
        assert await control.load_model(_BASE_URL, "qwen-exl3") is True
        await control.abandon_model_load(_BASE_URL, "qwen-exl3")

    operation = next(iter(control._loads.values()))  # pyright: ignore[reportPrivateUsage]
    assert operation.task is None
    assert operation.ambiguous is True
    assert operation.error is None
    with pytest.raises(TabbyAPIControlPlaneError, match="refusing concurrent load") as caught:
        await control.load_model(_BASE_URL, "small-exl3")
    assert caught.value.ambiguous is True


@pytest.mark.asyncio
async def test_exllamav3_probe_maps_stable_ids_and_dynamic_phases() -> None:
    stone = _stone()

    class StubControl(TabbyAPIControlPlane):
        async def inspect_animator(self, animator: Any) -> AnimatorLifecycle:
            return AnimatorLifecycle(
                runtime="exllamav3",
                base_url=animator.connector.base_url,
                mode="dynamic",
                health="ok",
                supports_router=True,
                active_model="qwen-exl3",
                loaded_models=["qwen-exl3"],
                available_models=["qwen-exl3", "small-exl3"],
            )

    adapter = ExLlamaV3RuntimeAdapter(control_plane=StubControl())
    registry = RuntimeAdapterRegistry(adapters=[adapter])
    runtime = registry.build_runtime(stone)
    assert runtime is not None
    specs = registry.build_capability_specs(stone)
    states = await registry.probe_capability_states(runtime, specs)
    by_id = {spec.model_id: state for spec, state in zip(specs, states, strict=True)}

    assert by_id["daily-driver"].phase is CapabilityPhase.WARM
    assert by_id["daily-driver"].active_model_id == "daily-driver"
    assert by_id["small"].phase is CapabilityPhase.ACTIVATABLE
