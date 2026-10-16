"""Offline guards for the opt-in native TCP proof; no daemon, model or listener."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, Mock

import httpx2
import pytest
from scripts.local_model_probe import ProbeProfile

from lychd.config.settings.root import SettingsSnapshot
from tests.integration import test_local_bridge_native_tcp as native

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar import Litestar

    from lychd.interface.web.altar_services import AltarServices


def _profile() -> ProbeProfile:
    return ProbeProfile(
        base_url="http://127.0.0.1:1/v1", model_id="inert-model", source_revision="0" * 40, deadline_seconds=1
    )


def _client(handler: Callable[[httpx2.Request], httpx2.Response]) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(
        base_url="http://127.0.0.1:7134",
        auth=("magus", "inert"),
        transport=httpx2.MockTransport(handler),
        trust_env=False,
    )


@pytest.mark.asyncio
async def test_warm_does_not_substitute_for_delayed_authenticated_tcp_readiness() -> None:
    seen: list[str] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        seen.append(request.method)
        if len(seen) < 3:
            message = "synthetic delayed listener"
            raise httpx2.ConnectError(message, request=request)
        return httpx2.Response(200, json={}, headers={"set-cookie": "csrftoken=inert; Path=/"})

    async with _client(handle) as client:
        assert await native._tcp_ready(client) == {"x-csrftoken": "inert"}
    assert seen == ["GET", "GET", "GET"]


@pytest.mark.asyncio
async def test_readiness_deadline_and_bad_credentials_never_admit_a_post(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def unavailable(request: httpx2.Request) -> httpx2.Response:
        seen.append(request.method)
        message = "synthetic unavailable listener"
        raise httpx2.ConnectError(message, request=request)

    monkeypatch.setattr(native, "_STARTUP_SECONDS", 0.03)
    async with _client(unavailable) as client:
        with pytest.raises(TimeoutError):
            await native._tcp_ready(client)
    async with _client(lambda _: httpx2.Response(401)) as client:
        with pytest.raises(AssertionError, match="native_bridge_status_refused"):
            await native._tcp_ready(client)
    assert seen
    assert set(seen) == {"GET"}


@pytest.mark.asyncio
async def test_async_orb_equivalent_requires_ordered_terminal_evidence() -> None:
    evidence = [[{"seq": 0, "kind": "status"}], [{"seq": 0, "kind": "status"}, {"seq": 1, "kind": "done"}]]
    async with _client(lambda _: httpx2.Response(200, json={"evidence": evidence.pop(0)})) as client:
        await native._orb_done(client, "inert-run")
    assert not evidence
    async with _client(lambda _: httpx2.Response(200, json={"evidence": [{"seq": 1, "kind": "done"}]})) as client:
        with pytest.raises(AssertionError, match="native_bridge_orb_order_invalid"):
            await native._orb_done(client, "inert-run")


@pytest.mark.asyncio
async def test_four_refusal_controls_use_the_run_route_and_verify_run_absence() -> None:
    seen: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(401 if len(seen) <= 2 else 403)

    ledger = SimpleNamespace(list_run_summaries=AsyncMock(return_value=[]))
    async with _client(handle) as client:
        client.auth = ("magus", "inert")
        result = await native._refusals(
            client, cast("AltarServices", SimpleNamespace(ledger=ledger)), "session", {"x-csrftoken": "inert"}
        )
    assert result == {"no_auth": 401, "wrong_auth": 401, "foreign_origin": 403, "missing_csrf": 403}
    assert all(request.method == "POST" and request.url.path.endswith("/session/messages") for request in seen)
    assert "authorization" not in seen[0].headers
    assert seen[1].headers["authorization"] != seen[2].headers["authorization"]
    assert seen[2].headers["origin"] == "https://foreign.invalid"
    assert "x-csrftoken" not in seen[3].headers
    ledger.list_run_summaries.assert_awaited_once_with(limit=1)


@pytest.mark.asyncio
async def test_refused_http_status_cannot_hide_an_admitted_run() -> None:
    count = 0

    def handle(request: httpx2.Request) -> httpx2.Response:
        nonlocal count
        count += 1
        return httpx2.Response(401 if count <= 2 else 403)

    services = cast(
        "AltarServices", SimpleNamespace(ledger=SimpleNamespace(list_run_summaries=AsyncMock(return_value=[object()])))
    )
    async with _client(handle) as client:
        with pytest.raises(AssertionError, match="native_bridge_refusal_admitted_run"):
            await native._refusals(client, services, "session", {"x-csrftoken": "inert"})


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_exercise_failure_is_observed_and_always_requests_native_retirement(
    monkeypatch: pytest.MonkeyPatch,
    cancel: bool,  # noqa: FBT001 - explicit cancellation case
) -> None:
    entered = asyncio.Event()

    async def exercise(*_args: Any) -> dict[str, Any]:
        entered.set()
        if cancel:
            await asyncio.Event().wait()
        message = "private-failure-sentinel"
        raise RuntimeError(message)

    monkeypatch.setattr(native, "_exercise", exercise)
    stop = Mock()
    monkeypatch.setattr(native.os, "kill", stop)
    boundary = native.proof._ModelBoundary(_profile(), admitted=True)
    report: dict[str, Any] = {}
    task = asyncio.create_task(
        native._exercise_and_stop(cast("Litestar", object()), boundary, "key", 7134, "inert", None, report)
    )
    await entered.wait()
    if cancel:
        task.cancel()
    await task
    assert report["exercise_passed"] is False
    assert report["error_type"] == ("CancelledError" if cancel else "RuntimeError")
    assert "private-failure-sentinel" not in json.dumps(report)
    assert boundary.admitted is False
    stop.assert_called_once_with(os.getpid(), signal.SIGTERM)


@pytest.mark.asyncio
async def test_second_boot_hook_refuses_before_real_transport() -> None:
    boundary = native.proof._ModelBoundary(_profile())
    transport = Mock(return_value=httpx2.Response(200))
    async with httpx2.AsyncClient(
        transport=httpx2.MockTransport(transport), event_hooks={"request": [boundary.check]}, trust_env=False
    ) as client:
        with pytest.raises(RuntimeError, match="local_bridge_model_post_refused"):
            await client.post(
                f"{boundary.profile.base_url}/chat/completions",
                json={
                    "model": boundary.profile.model_id,
                    "stream": True,
                    "max_tokens": 256,
                    "tools": [{"type": "function", "function": {"name": "final_result"}}],
                },
            )
    assert boundary.posts == 0
    assert boundary.violations == ["model_post_refused"]
    transport.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", [None, "history_sha256", "turns_sha256"])
async def test_second_boot_reads_identical_state_without_any_post(
    monkeypatch: pytest.MonkeyPatch, changed: str | None
) -> None:
    history = [{"inert": "retained-model-history"}]
    turns = [{"state": "settled", "content": "inert-retained-turn"}]
    previous = {
        "session_id": "inert-session",
        "run_id": "inert-run",
        "history_sha256": native.proof._digest(history),
        "turns_sha256": native.proof._digest(turns),
    }
    if changed is not None:
        previous[changed] = "changed-durable-digest"
    methods: list[str] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        methods.append(request.method)
        assert request.method == "GET"
        if request.url.path.endswith("/status"):
            return httpx2.Response(200, json={}, headers={"set-cookie": "csrftoken=inert; Path=/"})
        if "/orb/" in request.url.path:
            return httpx2.Response(200, json={"evidence": [{"seq": 0, "kind": "done"}]})
        return httpx2.Response(200, json={"session": {"turns": turns}})

    real_client = httpx2.AsyncClient

    def client(**kwargs: Any) -> httpx2.AsyncClient:
        return real_client(transport=httpx2.MockTransport(handle), **kwargs)

    monkeypatch.setattr(native.httpx2, "AsyncClient", client)
    services = object()
    monkeypatch.setattr(native.proof, "_ready", Mock(return_value=services))
    retained_history = AsyncMock(return_value=history)
    monkeypatch.setattr(native.proof, "_history", retained_history)
    boundary = native.proof._ModelBoundary(_profile())
    exercise = native._exercise(cast("Litestar", object()), boundary, "inert-key", 7134, "inert", previous, {})
    if changed is None:
        assert await exercise == previous
    else:
        with pytest.raises(AssertionError, match="native_bridge_retained_content_changed"):
            await exercise
    retained_history.assert_awaited_once_with(services, "inert-session", "inert-run", "inert-key")
    assert methods == ["GET", "GET", "GET"]
    assert boundary.posts == 0
    assert boundary.violations == []


def _report() -> dict[str, Any]:
    return {
        "outcome": "passed",
        "pid": 12345,
        "group": 12345,
        "parent_pid": os.getpid(),
        "start_time": "inert-start",
        "start_method": "spawn",
        **dict.fromkeys(
            (
                "cli_returned",
                "exercise_passed",
                "lifespan_closed",
                "warm",
                "tcp_ready",
                "engine_disposed",
                "substrate_unpublished",
            ),
            True,
        ),
        "boundary_violations": [],
        "lifecycle_calls": 0,
        "external_compute_unknown": False,
    }


def _process_fakes(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any] | None) -> tuple[Any, Any, list[str]]:
    events: list[str] = []
    child = Mock(pid=12345, exitcode=0)
    child.is_alive.return_value = False
    child.start.side_effect = lambda: events.append("start")

    def join(timeout: float) -> None:
        events.append("join")

    def read(limit: int) -> bytes:
        events.append("read")
        return json.dumps(payload).encode()

    child.join.side_effect = join
    reader, sender = Mock(), Mock()
    reader.poll.return_value = payload is not None
    reader.recv_bytes.side_effect = read
    context = SimpleNamespace(Pipe=Mock(return_value=(reader, sender)), Process=Mock(return_value=child))
    monkeypatch.setattr(native.multiprocessing, "get_context", Mock(return_value=context))
    monkeypatch.setattr(native, "_start_time", Mock(return_value="inert-start"))
    monkeypatch.setattr(native, "_group_exists", Mock(return_value=False))
    monkeypatch.setattr(native, "_listener_closed", Mock(return_value=True))
    return child, reader, events


def test_spawn_filters_environment_before_start_then_joins_before_reading(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    child, reader, events = _process_fakes(monkeypatch, _report())
    monkeypatch.setenv("UNRELATED_PROVIDER_KEY", "private-environment-sentinel")
    environment: dict[str, str] = {}
    child.start.side_effect = lambda: (events.append("start"), environment.update(os.environ))
    result = native._spawn_boot(SettingsSnapshot(payload="{}"), _profile(), None, 7134, tmp_path / "boot")
    assert result["outcome"] == "passed"
    assert result["contained"] is True
    assert events == ["start", "join", "read"]
    assert "UNRELATED_PROVIDER_KEY" not in environment
    assert os.environ["UNRELATED_PROVIDER_KEY"] == "private-environment-sentinel"
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert environment["PYTHONPATH"] == os.pathsep.join((str(native._ROOT / "src"), str(native._ROOT)))
    assert environment["HOME"] == str(Path.home())
    reader.recv_bytes.assert_called_once_with(native.process_proof._MAX_PAYLOAD)


@pytest.mark.skipif(sys.platform != "linux", reason="the native child identity requires Linux /proc and pipe bounds")
def test_real_inert_child_reports_limits_and_refuses_snapshot_without_private_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(native, "_listener_closed", Mock(return_value=True))
    marker = "private-snapshot-marker"
    result = native._spawn_boot(
        SettingsSnapshot(payload=json.dumps({"unexpected_native_input": marker})),
        _profile(),
        None,
        1,
        tmp_path / "inert-boot",
    )
    assert result["outcome"] == "failed"
    assert result["error_type"] == "ValidationError"
    assert result["contained"] is True
    assert result["joined"] is True
    assert result["exitcode"] == 1
    assert result["forced_termination"] is False
    assert result["substrate_unpublished"] is True
    assert result["engine_disposed"] is True
    assert result["model_posts"] == result["lifecycle_calls"] == 0
    assert result["boundary_violations"] == []
    assert result["limits_per_process"] == {name: list(values) for name, (_, values) in native._LIMITS.items()}
    assert marker not in json.dumps(result)
    assert "unexpected_native_input" not in json.dumps(result)


@pytest.mark.parametrize("failure", ["missing", "incomplete", "nonzero", "identity", "listener", "forced"])
def test_child_failure_cannot_become_a_clean_native_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    payload = _report()
    if failure == "incomplete":
        del payload["lifespan_closed"]
    if failure == "identity":
        payload["start_time"] = "different-start"
    child, _, _ = _process_fakes(monkeypatch, None if failure == "missing" else payload)
    if failure == "nonzero":
        child.exitcode = 1
    if failure == "listener":
        monkeypatch.setattr(native, "_listener_closed", Mock(return_value=False))
    if failure == "forced":
        child.is_alive.return_value = True

        def stop(pid: int, signum: int) -> None:
            child.is_alive.return_value = False

        monkeypatch.setattr(native.os, "kill", stop)
    result = native._spawn_boot(SettingsSnapshot(payload="{}"), _profile(), None, 7134, tmp_path / "boot")
    assert result["outcome"] == "failed"
    assert result["contained"] is (failure != "listener")
    assert result["forced_termination"] is (failure == "forced")


@pytest.mark.parametrize("contained", [False, True])
def test_failed_first_boot_blocks_second_and_pg_cleanup_requires_absence(
    monkeypatch: pytest.MonkeyPatch,
    contained: bool,  # noqa: FBT001 - dependency preservation cases
) -> None:
    events: list[str] = []
    postgres = Mock()
    postgres.start.side_effect = lambda: events.append("pg-start")
    postgres.stop.side_effect = lambda: events.append("pg-stop")
    postgres.get_wrapped_container.return_value.id = "inert-pg"
    postgres.get_connection_url.return_value = "postgresql+asyncpg://inert:inert@127.0.0.1:1/inert"
    monkeypatch.setattr(native.proof, "_cached_postgres", Mock(return_value=postgres))
    from lychd.db import bootstrap

    monkeypatch.setattr(bootstrap, "bootstrap_database", Mock())
    selector = Mock()
    selector.__enter__ = Mock(return_value=selector)
    selector.__exit__ = Mock(return_value=False)
    selector.getsockname.return_value = ("127.0.0.1", 7134)
    monkeypatch.setattr(native.socket, "socket", lambda: selector)

    def boot(*_args: Any) -> dict[str, Any]:
        events.append("native-settled")
        return {"outcome": "failed", "contained": contained}

    spawn = Mock(side_effect=boot)
    monkeypatch.setattr(native, "_spawn_boot", spawn)
    errors = ModuleType("docker.errors")
    not_found = type("NotFound", (Exception,), {})
    errors.__dict__["NotFound"] = not_found
    monkeypatch.setitem(sys.modules, "docker.errors", errors)
    postgres.get_docker_client.return_value.client.api.inspect_container.side_effect = not_found()
    # The native proof requires external scratch even when pytest's basetemp is in the checkout.
    with TemporaryDirectory(prefix="lychd-native-tcp-unit-", dir="/tmp") as directory:
        scratch = Path(directory)
        with pytest.raises(AssertionError, match="native_bridge_proof_or_cleanup_failed"):
            native.test_native_tcp_bridge_retains_one_reply_across_clean_process_boots(monkeypatch, scratch, _profile())
        assert spawn.call_count == 1
        assert events == (["pg-start", "native-settled", "pg-stop"] if contained else ["pg-start", "native-settled"])
        receipt = json.loads((scratch / "local-bridge-native-tcp/receipt.json").read_text())
        assert receipt["outcome"] == "failed"
        assert receipt.get("postgres_preserved", False) is not contained
        assert receipt.get("postgres_removed", False) is contained
