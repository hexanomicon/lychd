"""Opt-in production source CLI/TCP Bridge reply across two clean native boots.

Reuses the external warm-model admission and historical durable/model oracles.
Settings, Runes, the request hook and refusing actuator are explicit test
composition; the production factory, services, native launcher and TCP stay real.
This is not installed-command, managed-model, browser or crash qualification.
Metadata stays in external pytest scratch. An uncontained child preserves its
PostgreSQL dependency for the outer operator watchdog to reconcile.
"""

# pyright: reportPrivateUsage=false
# Container SDKs remain optional and are imported only by the opt-in selection.
# pyright: reportMissingImports=false

from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing
import os
import resource
import secrets
import signal
import socket
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlsplit
from uuid import uuid4

import httpx2
import pydantic_ai.models
import pytest
from pydantic import SecretStr
from pydantic_ai.models import override_allow_model_requests
from scripts.local_model_probe import ProbeProfile

from lychd.config.settings.root import SettingsSnapshot
from lychd.domain.animation.schemas import ConcurrencyIntent, GenerationProfile
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstoneConfig
from tests.integration import test_local_bridge_process_restart as process_proof
from tests.integration import test_local_bridge_runtime as proof
from tests.integration.test_server_process import _group_exists

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from multiprocessing.connection import Connection

    from litestar import Litestar

    from lychd.interface.web.altar_services import AltarServices

pytestmark = [pytest.mark.integration, pytest.mark.container]
local_bridge_profile = proof.local_bridge_profile
_ROOT = Path(__file__).resolve().parents[2]
_STARTUP_SECONDS = 10
_ORB_SECONDS = 15
_LIMITS = {
    "AS": (resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3)),
    "CPU": (resource.RLIMIT_CPU, (90, 100)),
    "FSIZE": (resource.RLIMIT_FSIZE, (8 * 1024**2, 8 * 1024**2)),
    "NOFILE": (resource.RLIMIT_NOFILE, (256, 256)),
    "CORE": (resource.RLIMIT_CORE, (0, 0)),
}


def _failure(error: BaseException) -> dict[str, Any]:
    metadata: dict[str, Any] = {"error_type": type(error).__name__[:64]}
    trace = error.__traceback__
    while trace is not None:
        if Path(trace.tb_frame.f_code.co_filename).name == Path(__file__).name:
            metadata.update(error_file=Path(__file__).name, error_line=trace.tb_lineno)
        trace = trace.tb_next
    return metadata


async def _tcp_ready(client: httpx2.AsyncClient) -> dict[str, str]:
    """Startup alone retries GETs; WARM can precede the native socket bind."""
    async with asyncio.timeout(_STARTUP_SECONDS):
        while True:
            try:
                status = await client.get("/api/v1/altar/status")
            except httpx2.TransportError:
                await asyncio.sleep(0.02)
                continue
            proof._require(status.status_code == 200, "native_bridge_status_refused")
            token = client.cookies.get("csrftoken")
            proof._require(token is not None, "native_bridge_csrf_cookie_missing")
            return {"x-csrftoken": cast("str", token)}


async def _orb_done(client: httpx2.AsyncClient, run_id: str) -> None:
    """Preserve the production-wiring Orb oracle over asynchronous real TCP."""
    async with asyncio.timeout(_ORB_SECONDS):
        while True:
            response = await client.get(f"/api/v1/orb/runs/{run_id}?limit=100")
            proof._require(response.status_code == 200, "native_bridge_orb_read_failed")
            evidence = response.json()["evidence"]
            proof._require(
                [event["seq"] for event in evidence] == list(range(len(evidence))), "native_bridge_orb_order_invalid"
            )
            if evidence and evidence[-1]["kind"] == "done":
                return
            await asyncio.sleep(0.05)


async def _refusals(
    client: httpx2.AsyncClient, services: AltarServices, session_id: str, headers: dict[str, str]
) -> dict[str, int]:
    """Exercise refused Run admission, rather than merely refused session creation."""
    controls: dict[str, dict[str, Any]] = {
        "no_auth": {"auth": None, "headers": headers},
        "wrong_auth": {"auth": ("magus", "wrong"), "headers": headers},
        "foreign_origin": {"headers": {**headers, "origin": "https://foreign.invalid"}},
        "missing_csrf": {"headers": {}},
    }
    statuses: dict[str, int] = {}
    for name, options in controls.items():
        response = await client.post(
            f"/api/v1/bridge/sessions/{session_id}/messages",
            json={"prompt": "This refused synthetic turn must never execute.", "request_id": str(uuid4())},
            **options,
        )
        statuses[name] = response.status_code
        proof._require(response.status_code == (401 if name.endswith("auth") else 403), "native_bridge_refusal_failed")
    proof._require(not await services.ledger.list_run_summaries(limit=1), "native_bridge_refusal_admitted_run")
    return statuses


async def _exercise(  # noqa: PLR0915 - one finite TCP/durable conjunction
    app: Litestar,
    boundary: proof._ModelBoundary,
    key: str,
    port: int,
    password: str,
    previous: dict[str, Any] | None,
    report: dict[str, Any],
) -> dict[str, Any]:
    services = proof._ready(app, key)
    session_id = run_id = marker = ""
    settled = False
    async with httpx2.AsyncClient(
        base_url=f"http://127.0.0.1:{port}",
        auth=("magus", password),
        trust_env=False,
        follow_redirects=False,
        timeout=1,
    ) as client:
        headers = await _tcp_ready(client)
        report["tcp_ready"] = True
        try:
            if previous is None:
                created = await client.post("/api/v1/bridge/sessions", headers=headers)
                proof._require(created.status_code == 201, "native_bridge_session_admission_failed")
                session_id = created.json()["session"]["id"]
                report["auth_csrf_negatives"] = await _refusals(client, services, session_id, headers)
                proof._require(boundary.posts == 0, "native_bridge_refusal_sent_model_post")
                report["negative_run_count"] = 0
                marker = f"native-bridge-{secrets.token_hex(12)}"
                boundary.deadline = time.monotonic() + boundary.profile.deadline_seconds
                boundary.admitted = True
                with override_allow_model_requests(allow_model_requests=True):
                    async with asyncio.timeout_at(boundary.deadline):
                        accepted = await client.post(
                            f"/api/v1/bridge/sessions/{session_id}/messages",
                            json={
                                "prompt": f"Return the final structured reply with answer exactly {marker} and fragments [].",
                                "request_id": str(uuid4()),
                            },
                            headers=headers,
                        )
                        proof._require(accepted.status_code == 200, "native_bridge_turn_admission_failed")
                        run_id = accepted.json()["run_id"]
                    await proof._wait_settled(services, run_id, boundary.deadline)
                boundary.admitted = False
                settled = True
            else:
                session_id, run_id = previous["session_id"], previous["run_id"]
            await _orb_done(client, run_id)
            async with asyncio.timeout(10):
                history = await proof._history(services, session_id, run_id, key)
            response = await client.get(f"/api/v1/bridge/sessions/{session_id}")
            proof._require(response.status_code == 200, "native_bridge_session_read_failed")
            turns = response.json()["session"]["turns"]
            retained: dict[str, Any] = {
                "session_id": session_id,
                "run_id": run_id,
                "history_sha256": proof._digest(history),
                "turns_sha256": proof._digest(turns),
            }
            if previous is None:
                observations = proof._observe_history(history, boundary.profile, marker)
                proof._require(
                    len(turns) == 2 and turns[-1]["content"] == marker and turns[-1]["state"] == "settled",
                    "native_bridge_settled_turns_invalid",
                )
                proof._require(boundary.posts == len(observations), "native_bridge_unretained_response")
                retained["responses"] = observations
            else:
                proof._require(boundary.posts == 0, "native_bridge_second_boot_inference")
                for name in ("history_sha256", "turns_sha256"):
                    proof._require(retained[name] == previous[name], "native_bridge_retained_content_changed")
        except BaseException:
            boundary.admitted = False
            if previous is None and session_id and not settled:
                report["external_compute_unknown"] = boundary.posts > 0
                async with asyncio.timeout(proof._CLEANUP_SECONDS):
                    run = await services.ledger.get_nonterminal_for_session(session_id)
                    if run is not None:
                        await services.run_engine.cancel(run.run_id)
            raise
        else:
            return retained
        finally:
            boundary.admitted = False


async def _exercise_and_stop(
    app: Litestar,
    boundary: proof._ModelBoundary,
    key: str,
    port: int,
    password: str,
    previous: dict[str, Any] | None,
    report: dict[str, Any],
) -> None:
    try:
        report["retained"] = await _exercise(app, boundary, key, port, password, previous, report)
        report["exercise_passed"] = True
    except BaseException as error:  # noqa: BLE001 - no task failure or private content escapes observation
        report.update(_failure(error), exercise_passed=False)
    finally:
        boundary.admitted = False
        os.kill(os.getpid(), signal.SIGTERM)


def _child_boot(  # noqa: C901, PLR0915 - bounded child boot, real CLI and final cleanup metadata
    sender: Connection,
    snapshot: SettingsSnapshot,
    profile: ProbeProfile,
    previous: dict[str, Any] | None,
    port: int,
    root: Path,
) -> None:
    boundary, actuator = proof._ModelBoundary(profile), proof._RefusingActuator()
    report: dict[str, Any] = {"outcome": "failed", "external_compute_unknown": False}
    with Path(os.devnull).open("w", encoding="utf-8") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    logging.disable(logging.CRITICAL)
    pydantic_ai.models.ALLOW_MODEL_REQUESTS = False
    try:
        os.setsid()
        os.chdir(root)
        proof._require(not (root / ".env").exists(), "native_bridge_dotenv_forbidden")
        # Per-process only, after interpreter/module startup; no aggregate/GPU guarantee.
        for limit, values in _LIMITS.values():
            resource.setrlimit(limit, values)
        report.update(
            pid=os.getpid(),
            parent_pid=os.getppid(),
            group=os.getpgrp(),
            start_time=_start_time(os.getpid()),
            start_method=multiprocessing.get_start_method(),
            limits_per_process={name: resource.getrlimit(limit) for name, (limit, _) in _LIMITS.items()},
        )
        from lychd.__main__ import cli
        from lychd.interface.web import lifespan

        settings = snapshot.materialize()
        password = settings.server.web.access_password
        proof._require(password is not None, "native_bridge_access_password_missing")
        key = f"bootstrap-joined:chat:{profile.model_id}"
        rune = VllmSoulstoneConfig(
            name="bootstrap-joined",
            base_url=profile.base_url,  # pyright: ignore[reportArgumentType] - admitted explicit profile
            port=urlsplit(profile.base_url).port,
            served_model_id=profile.model_id,
            concurrency=ConcurrencyIntent(dedicated=False),
            generation=GenerationProfile(
                max_context=profile.context_tokens, max_tokens=profile.max_tokens, temperature=0
            ),
        )
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                "lychd.system.constants.PATH_RUNTIME_GUARD_DIR",
                Path(settings.orchestration.switching.host_reactor_dir).parent / "runtime-guard",
            )
            proof._configure_factory(patch, settings=settings, rune=rune, actuator=actuator, boundary=boundary)
            real_lifespan = lifespan.altar_services_lifespan

            @asynccontextmanager
            async def observed_lifespan(app: Litestar) -> AsyncGenerator[None]:
                async with real_lifespan(app):
                    proof._ready(app, key)
                    report["warm"] = True
                    task = asyncio.create_task(
                        _exercise_and_stop(
                            app, boundary, key, port, cast("SecretStr", password).get_secret_value(), previous, report
                        )
                    )
                    try:
                        yield
                    finally:
                        if not task.done():
                            task.cancel()
                        async with asyncio.timeout(proof._CLEANUP_SECONDS):
                            await task
                report["lifespan_closed"] = True

            patch.setattr(lifespan, "altar_services_lifespan", observed_lifespan)
            cli.main(
                args=["serve", "--host", "127.0.0.1", "--port", str(port)],
                prog_name="lychd",
                standalone_mode=False,
            )
            report["cli_returned"] = True
    except BaseException as error:  # noqa: BLE001 - report bounded metadata after required cleanup
        report.update(_failure(error))
    finally:
        from lychd.db.engine import dispose_engine
        from lychd.domain.cortex.substrate import get_run_substrate

        boundary.admitted = False
        pydantic_ai.models.ALLOW_MODEL_REQUESTS = False
        report.update(
            model_posts=boundary.posts, boundary_violations=boundary.violations, lifecycle_calls=actuator.calls
        )
        try:
            get_run_substrate()
        except RuntimeError:
            report["substrate_unpublished"] = True
        else:
            report["substrate_unpublished"] = False
        try:
            asyncio.run(dispose_engine())
            report["engine_disposed"] = True
        except BaseException as error:  # noqa: BLE001 - cleanup uncertainty cannot pass
            report.update(_failure(error), engine_disposed=False)
        if (
            all(report.get(name) is True for name in ("cli_returned", "exercise_passed", "lifespan_closed", "warm"))
            and report["substrate_unpublished"]
            and report["engine_disposed"]
            and not boundary.violations
            and actuator.calls == 0
            and not report["external_compute_unknown"]
        ):
            report["outcome"] = "passed"
        payload = json.dumps(report, sort_keys=True).encode()
        if len(payload) > process_proof._MAX_PAYLOAD:
            report = {"outcome": "failed", "error_type": "child_metadata_too_large"}
            payload = json.dumps(report).encode()
        try:
            sender.send_bytes(payload)
        finally:
            sender.close()
    if report["outcome"] != "passed":
        raise SystemExit(1)


def _child_environment(root: Path) -> dict[str, str]:
    """Filter before spawn, including source projection when borrowing another venv."""
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(Path.home()),
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": os.pathsep.join((str(_ROOT / "src"), str(_ROOT))),
        "XDG_CONFIG_HOME": str(root / "config"),
        "XDG_DATA_HOME": str(root / "data"),
        "XDG_STATE_HOME": str(root / "state"),
        "XDG_CACHE_HOME": str(root / "cache"),
        "XDG_RUNTIME_DIR": str(root / "runtime"),
        "TMPDIR": str(root / "tmp"),
    }


def _listener_closed(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return False
    except ConnectionRefusedError:
        return True
    except OSError:
        return False


def _start_time(pid: int) -> str:
    return Path(f"/proc/{pid}/stat").read_text().rpartition(") ")[2].split()[19]


def _settle_child(child: Any, port: int) -> dict[str, Any]:
    """Return absence evidence; forced settlement is always distinct from success."""
    forced = child.is_alive() or _group_exists(child.pid)
    if forced:
        for signum in (signal.SIGTERM, signal.SIGKILL):
            if _group_exists(child.pid):
                os.killpg(child.pid, signum)
            elif child.is_alive():
                os.kill(child.pid, signum)
            child.join(proof._CLEANUP_SECONDS / 2)
            if not child.is_alive() and not _group_exists(child.pid):
                break
    settled = {
        "pid": child.pid,
        "exitcode": child.exitcode,
        "reaped": not child.is_alive(),
        "group_absent": not _group_exists(child.pid),
        "listener_closed": _listener_closed(port),
        "forced_termination": forced,
    }
    settled["contained"] = all(settled[name] for name in ("reaped", "group_absent", "listener_closed"))
    return settled


def _spawn_boot(
    snapshot: SettingsSnapshot, profile: ProbeProfile, previous: dict[str, Any] | None, port: int, root: Path
) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    reader, sender = context.Pipe(duplex=False)
    child = context.Process(target=_child_boot, args=(sender, snapshot, profile, previous, port, root), daemon=False)
    report: dict[str, Any] = {"outcome": "failed", "joined": False, "forced_termination": False, "contained": False}
    try:
        environment = _child_environment(root)
        for name in ("config", "data", "state", "cache", "runtime", "tmp"):
            (root / name).mkdir(parents=True, mode=0o700)
        with pytest.MonkeyPatch.context() as patch:
            for name in tuple(os.environ):
                patch.delenv(name)
            for name, value in environment.items():
                patch.setenv(name, value)
            child.start()
        proof._require(child.pid is not None, "native_bridge_child_pid_missing")
        start_time = _start_time(cast("int", child.pid))
        # Let the outer owner reconcile this exact session even if pytest is interrupted.
        (root / "process-identity.json").write_text(
            json.dumps({"pid": child.pid, "group": child.pid, "start_time": start_time, "fixture": str(__file__)})
            + "\n",
            encoding="utf-8",
        )
        sender.close()
        child.join(profile.deadline_seconds + 2 * proof._CLEANUP_SECONDS + _STARTUP_SECONDS)
        proof._require(not child.is_alive(), "native_bridge_child_exit_timeout")
        report["joined"] = True
        proof._require(reader.poll(0), "native_bridge_child_report_missing")
        received = json.loads(reader.recv_bytes(process_proof._MAX_PAYLOAD))
        proof._require(isinstance(received, dict), "native_bridge_child_report_invalid")
        report.update(received)
        proof._require(
            report.get("pid") == report.get("group") == child.pid
            and report.get("parent_pid") == os.getpid()
            and report.get("start_time") == start_time
            and report.get("start_method") == "spawn",
            "native_bridge_child_identity_invalid",
        )
    except BaseException as error:  # noqa: BLE001 - start/transport failures retain no private input
        report.update(_failure(error), outcome="failed")
    finally:
        reader.close()
        sender.close()
        try:
            if child.pid is not None:
                report.update(_settle_child(child, port))
            if not child.is_alive():
                child.close()
        except BaseException as error:  # noqa: BLE001 - preserve PG on any uncertain child cleanup
            report.update(_failure(error), outcome="failed", contained=False)
    if (
        not report["joined"]
        or not report["contained"]
        or report["forced_termination"]
        or report.get("exitcode") != 0
        or report.get("boundary_violations") != []
        or report.get("lifecycle_calls") != 0
        or report.get("external_compute_unknown") is not False
        or not all(
            report.get(name) is True
            for name in (
                "cli_returned",
                "exercise_passed",
                "lifespan_closed",
                "warm",
                "tcp_ready",
                "engine_disposed",
                "substrate_unpublished",
            )
        )
    ):
        report["outcome"] = "failed"
    return report


def test_native_tcp_bridge_retains_one_reply_across_clean_process_boots(  # noqa: PLR0915 - bounded two-boot PG receipt
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, local_bridge_profile: ProbeProfile
) -> None:
    from docker.errors import NotFound

    from lychd.db.bootstrap import bootstrap_database

    profile = local_bridge_profile
    proof._require(sys.platform == "linux", "native_bridge_requires_linux")
    proof._require(not tmp_path.resolve().is_relative_to(_ROOT), "native_bridge_external_scratch_required")
    receipt: dict[str, Any] = {
        "outcome": "failed",
        "source_revision_declared": profile.source_revision,
        "application": "production-source-cli-two-native-tcp-boots",
        "aggregate_native_resource_limit": False,
        "boots": [],
    }
    destination = tmp_path / "local-bridge-native-tcp" / "receipt.json"
    destination.parent.mkdir()
    postgres, container_id, safe_to_stop = None, None, True
    try:
        postgres = proof._cached_postgres(monkeypatch, receipt)
        postgres.start()
        container_id = postgres.get_wrapped_container().id
        settings = proof._settings(
            postgres.get_connection_url(host="127.0.0.1"),
            tmp_path / "control",
            f"bootstrap-joined:chat:{profile.model_id}",
            SecretStr(secrets.token_urlsafe(32)),
        )
        snapshot = SettingsSnapshot.capture(settings)
        bootstrap_database(settings)
        bootstrap_database(settings)
        with socket.socket() as selector:
            selector.bind(("127.0.0.1", 0))
            port = selector.getsockname()[1]
        previous = None
        for boot_number in (1, 2):
            safe_to_stop = False
            boot = _spawn_boot(snapshot, profile, previous, port, tmp_path / f"boot-{boot_number}")
            receipt["boots"].append(boot)
            safe_to_stop = boot["contained"] is True
            proof._require(boot["outcome"] == "passed", "native_bridge_child_failed")
            proof._require(
                boot["parent_pid"] == os.getpid() and boot["group"] == boot["pid"],
                "native_bridge_child_identity_invalid",
            )
            previous = {
                name: boot["retained"][name] for name in ("session_id", "run_id", "history_sha256", "turns_sha256")
            }
        first, second = receipt["boots"]
        proof._require(first["pid"] != second["pid"], "native_bridge_reused_child_identity")
        proof._require(
            0 < first["model_posts"] <= proof._POST_LIMIT and second["model_posts"] == 0,
            "native_bridge_post_count_invalid",
        )
        receipt["outcome"] = "passed"
    except BaseException as error:  # noqa: BLE001 - no exception text or private input in receipt
        receipt.update(_failure(error), outcome="failed")
    finally:
        if postgres is not None:
            if safe_to_stop:
                try:
                    postgres.stop()
                    client = postgres.get_docker_client().client
                    try:
                        if container_id is not None:
                            try:
                                client.api.inspect_container(container_id)
                            except NotFound:
                                receipt["postgres_removed"] = True
                    finally:
                        client.close()
                except BaseException as error:  # noqa: BLE001 - incomplete PG cleanup cannot pass
                    receipt.update(_failure(error), outcome="failed")
            else:
                receipt.update(postgres_preserved=True, postgres_id=container_id, outcome="failed")
        if receipt.get("postgres_removed") is not True:
            receipt["outcome"] = "failed"
        payload = json.dumps(receipt, indent=2, sort_keys=True)
        if len(payload.encode()) > process_proof._MAX_RECEIPT:
            payload = json.dumps({"outcome": "failed", "error_type": "receipt_metadata_too_large"})
            receipt["outcome"] = "failed"
        destination.write_text(payload + "\n", encoding="utf-8")
        proof._require(receipt["outcome"] == "passed", "native_bridge_proof_or_cleanup_failed")
