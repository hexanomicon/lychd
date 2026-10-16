"""Opt-in clean process restart proof using the historical warm Bridge guards.

The existing external profile and serial opt-in admit one disposable cached
PostgreSQL and at most three synthetic streamed model POSTs. Two sequential
spawned children each boot the real application; only the first admits inference.
Secrets travel in memory, child output is discarded, and receipts contain bounded
metadata only. This does not qualify crash recovery, a deployed Vessel or a browser.
Keep the existing outer runner timeout and owned-container cleanup protection.
"""

# pyright: reportPrivateUsage=false
# The Docker SDK remains an optional integration-test dependency.
# pyright: reportMissingImports=false

from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing
import os
import secrets
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit
from uuid import uuid4

import pydantic_ai.models
import pytest
from pydantic import SecretStr
from pydantic_ai.models import override_allow_model_requests
from scripts.local_model_probe import ProbeProfile

from lychd.config.settings.root import SettingsSnapshot
from lychd.domain.animation.schemas import ConcurrencyIntent, GenerationProfile
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstoneConfig
from tests.integration import test_local_bridge_runtime as proof

if TYPE_CHECKING:
    from multiprocessing.connection import Connection

    from lychd.interface.web.altar_services import AltarServices

pytestmark = [pytest.mark.integration, pytest.mark.container]
local_bridge_profile = proof.local_bridge_profile
_MAX_PAYLOAD = 4092  # One payload plus its four-byte Pipe header fits Linux PIPE_BUF.
_MAX_RECEIPT = 65_536


def _failure_metadata(error: BaseException) -> dict[str, Any]:
    metadata: dict[str, Any] = {"error_type": type(error).__name__[:64]}
    trace = error.__traceback__
    for _ in range(64):
        if trace is None:
            break
        filename = Path(trace.tb_frame.f_code.co_filename).name
        if (
            filename in {Path(__file__).name, "test_local_bridge_runtime.py", "test_production_wiring.py"}
            and trace.tb_frame.f_code.co_name != "_require"
        ):
            metadata.update(error_file=filename, error_line=trace.tb_lineno)
        trace = trace.tb_next
    return metadata


def _retained_boot(
    client: Any, services: AltarServices, boundary: proof._ModelBoundary, key: str, previous: dict[str, Any] | None
) -> dict[str, Any]:
    marker = ""
    if previous is None:
        marker = f"joined-bridge-{secrets.token_hex(12)}"
        headers = proof._csrf_headers(client)
        created = client.post("/api/v1/bridge/sessions", headers=headers)
        proof._require(created.status_code == 201, "process_bridge_session_admission_failed")
        session_id = created.json()["session"]["id"]
        boundary.deadline = time.monotonic() + boundary.profile.deadline_seconds
        boundary.admitted = True
        try:
            with override_allow_model_requests(allow_model_requests=True):
                accepted = client.post(
                    f"/api/v1/bridge/sessions/{session_id}/messages",
                    json={
                        "prompt": f"Return the final structured reply with answer exactly {marker} and fragments [].",
                        "request_id": str(uuid4()),
                    },
                    headers=headers,
                )
                proof._require(accepted.status_code == 200, "process_bridge_turn_admission_failed")
                run_id = accepted.json()["run_id"]
                client.blocking_portal.call(proof._wait_settled, services, run_id, boundary.deadline)
        finally:
            boundary.admitted = False
    else:
        session_id, run_id = previous["session_id"], previous["run_id"]
    proof._assert_orb_done(client, run_id)
    history = client.blocking_portal.call(proof._history, services, session_id, run_id, key)
    response = client.get(f"/api/v1/bridge/sessions/{session_id}")
    proof._require(response.status_code == 200, "process_bridge_session_read_failed")
    turns = response.json()["session"]["turns"]
    retained: dict[str, Any] = {
        "session_id": session_id,
        "run_id": run_id,
        "history_sha256": proof._digest(history),
        "turns_sha256": proof._digest(turns),
    }
    if previous is None:
        observations = proof._observe_history(history, boundary.profile, marker)
        proof._require(len(turns) == 2 and turns[-1]["content"] == marker, "process_bridge_settled_turns_invalid")
        proof._require(turns[-1]["state"] == "settled", "process_bridge_turn_not_settled")
        proof._require(boundary.posts == len(observations), "process_bridge_unretained_response")
        retained["responses"] = observations
    else:
        for name in ("history_sha256", "turns_sha256"):
            proof._require(retained[name] == previous[name], "process_bridge_retained_content_changed")
        proof._require(boundary.posts == 0, "process_bridge_second_boot_inference")
    return retained


def _child_boot(  # noqa: PLR0915 - one bounded application boot and its cleanup report
    sender: Connection, snapshot: SettingsSnapshot, profile: ProbeProfile, previous: dict[str, Any] | None
) -> None:
    """Report only after ordinary application shutdown and process-local cleanup."""
    from litestar.testing import TestClient

    from lychd.app import create_app
    from lychd.db.engine import dispose_engine
    from lychd.domain.cortex.substrate import get_run_substrate

    with Path(os.devnull).open("w", encoding="utf-8") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    logging.disable(logging.CRITICAL)
    pydantic_ai.models.ALLOW_MODEL_REQUESTS = False
    boundary, actuator = proof._ModelBoundary(profile), proof._RefusingActuator()
    report: dict[str, Any] = {
        "outcome": "failed",
        "pid": os.getpid(),
        "parent_pid": os.getppid(),
        "start_method": multiprocessing.get_start_method(),
        "boot": 1 if previous is None else 2,
    }
    try:
        settings = snapshot.materialize()
        key = f"bootstrap-joined:chat:{profile.model_id}"
        rune = VllmSoulstoneConfig(
            name="bootstrap-joined",
            base_url=profile.base_url,  # pyright: ignore[reportArgumentType] - validated explicit profile
            port=urlsplit(profile.base_url).port,
            served_model_id=profile.model_id,
            concurrency=ConcurrencyIntent(dedicated=False),
            generation=GenerationProfile(
                max_context=profile.context_tokens, max_tokens=profile.max_tokens, temperature=0
            ),
        )
        with pytest.MonkeyPatch.context() as patch:
            guard = Path(settings.orchestration.switching.host_reactor_dir).parent / "runtime-guard"
            patch.setattr("lychd.system.constants.PATH_RUNTIME_GUARD_DIR", guard)
            proof._configure_factory(patch, settings=settings, rune=rune, actuator=actuator, boundary=boundary)
            app = create_app()
            with TestClient(app=app, base_url="http://127.0.0.1:7134") as client:
                password = settings.server.web.access_password
                proof._require(password is not None, "process_bridge_access_password_missing")
                client.auth = ("magus", password.get_secret_value() if password is not None else "")
                report["retained"] = _retained_boot(client, proof._ready(app, key), boundary, key, previous)
                report["warm"] = True
        report["outcome"] = "passed"
    except BaseException as exc:  # noqa: BLE001 - no child exception text may cross the boundary
        report.update(_failure_metadata(exc))
    finally:
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
        except BaseException as exc:  # noqa: BLE001 - cleanup uncertainty remains failure metadata
            report.update(_failure_metadata(exc), engine_disposed=False)
        if (
            boundary.violations
            or actuator.calls
            or not report["substrate_unpublished"]
            or not report["engine_disposed"]
        ):
            report["outcome"] = "failed"
        payload = json.dumps(report, sort_keys=True).encode()
        if len(payload) > _MAX_PAYLOAD:
            report = {"outcome": "failed", "error_type": "child_metadata_too_large"}
            payload = json.dumps(report).encode()
        try:
            sender.send_bytes(payload)
        finally:
            sender.close()
    if report["outcome"] != "passed":
        raise SystemExit(1)


def _spawn_boot(snapshot: SettingsSnapshot, profile: ProbeProfile, previous: dict[str, Any] | None) -> dict[str, Any]:
    """Bound report collection, full exit and forced reaping of one fresh process."""
    context = multiprocessing.get_context("spawn")
    reader, sender = context.Pipe(duplex=False)
    child = context.Process(target=_child_boot, args=(sender, snapshot, profile, previous), daemon=False)
    report: dict[str, Any] = {"outcome": "failed", "joined": False, "forced_termination": False}
    started = False
    deadline = time.monotonic() + profile.deadline_seconds + 2 * proof._CLEANUP_SECONDS
    try:
        child.start()
        started = True
        sender.close()
        # The capped single pipe write fits without a reader. Join first so a
        # partial write can never turn recv_bytes into an unbounded wait.
        child.join(max(0, deadline - time.monotonic()))
        proof._require(not child.is_alive(), "process_bridge_child_exit_timeout")
        report["joined"] = True
        proof._require(reader.poll(0), "process_bridge_child_report_missing")
        received = json.loads(reader.recv_bytes(_MAX_PAYLOAD))
        proof._require(isinstance(received, dict), "process_bridge_child_report_invalid")
        report.update(received)
    except BaseException as exc:  # noqa: BLE001 - contain launch, transport and child failures without content
        report.update(_failure_metadata(exc), outcome="failed")
    finally:
        reader.close()
        sender.close()
        if started and child.is_alive():
            report.update(outcome="failed", forced_termination=True)
            for stop in (child.terminate, child.kill):
                if not child.is_alive():
                    break
                try:
                    stop()
                except OSError as exc:
                    report.update(_failure_metadata(exc))
                child.join(proof._CLEANUP_SECONDS / 2)
        report.update(pid=child.pid, exitcode=child.exitcode, reaped=started and not child.is_alive())
        if not child.is_alive():
            child.close()
    if not report["joined"] or not report["reaped"] or report["exitcode"] != 0:
        report["outcome"] = "failed"
    return report


def test_local_bridge_retains_one_reply_across_independent_process_boots(  # noqa: PLR0915 - bounded process/PG receipt
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, local_bridge_profile: ProbeProfile
) -> None:
    from docker.errors import NotFound

    from lychd.db.bootstrap import bootstrap_database

    profile = local_bridge_profile
    proof._require(sys.platform == "linux", "process_bridge_requires_linux_pipe_bounds")
    receipt: dict[str, Any] = {
        "outcome": "failed",
        "source_revision_declared": profile.source_revision,
        "application": "real-create_app-two-spawned-processes",
        "start_method": "spawn",
        "parent_pid": os.getpid(),
        "boots": [],
    }
    receipt_path = tmp_path / "local-bridge-process-restart" / "receipt.json"
    receipt_path.parent.mkdir()
    postgres, container_id = None, None
    try:
        postgres = proof._cached_postgres(monkeypatch, receipt)
        with postgres:
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
            previous = None
            for _ in range(2):
                boot = _spawn_boot(snapshot, profile, previous)
                receipt["boots"].append(boot)
                proof._require(boot["outcome"] == "passed", "process_bridge_child_failed")
                previous = {
                    name: boot["retained"][name] for name in ("session_id", "run_id", "history_sha256", "turns_sha256")
                }
            first, second = receipt["boots"]
            proof._require(
                all(boot["parent_pid"] == os.getpid() and boot["start_method"] == "spawn" for boot in (first, second)),
                "process_bridge_spawn_parent_invalid",
            )
            proof._require(
                first["pid"] != second["pid"] and os.getpid() not in (first["pid"], second["pid"]),
                "process_bridge_process_identity_invalid",
            )
            proof._require(
                0 < first["model_posts"] <= proof._POST_LIMIT and second["model_posts"] == 0,
                "process_bridge_post_count_invalid",
            )
        receipt["outcome"] = "passed"
    except BaseException as exc:  # noqa: BLE001 - parent failures retain no raw exception or input
        receipt.update(_failure_metadata(exc), outcome="failed")
    finally:
        if postgres is not None:
            try:
                client = postgres.get_docker_client().client
                try:
                    if container_id is not None:
                        try:
                            client.api.inspect_container(container_id)
                        except NotFound:
                            receipt["postgres_removed"] = True
                        else:
                            receipt["postgres_removed"] = False
                finally:
                    client.close()
            except BaseException as exc:  # noqa: BLE001 - incomplete PG cleanup cannot pass
                receipt.update(_failure_metadata(exc), outcome="failed")
        if receipt.get("postgres_removed") is not True:
            receipt["outcome"] = "failed"
        payload = json.dumps(receipt, indent=2, sort_keys=True)
        if len(payload.encode()) > _MAX_RECEIPT:
            receipt = {"outcome": "failed", "error_type": "receipt_metadata_too_large"}
            payload = json.dumps(receipt)
        receipt_path.write_text(payload + "\n", encoding="utf-8")
        proof._require(receipt["outcome"] == "passed", "process_bridge_proof_or_cleanup_failed")
