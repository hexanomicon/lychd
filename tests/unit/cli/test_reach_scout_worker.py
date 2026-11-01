"""Separate standing catalogue authority, durable reservations and hostile returns."""

from __future__ import annotations

import asyncio
import io
import json
import os
import stat
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import Mock

import pytest
from scripts import reach_scout_worker as worker

from lychd.compositions.reach.research_wire import (
    ResearchJob,
    ResearchOptions,
    ResearchRuntimeProfile,
    ResearchSource,
)
from lychd.domain.scout.destination import preflight_destination
from lychd.domain.scout.extraction import ExtractedText, ExtractionCode, ExtractionError
from lychd.domain.scout.transport import FetchCode, FetchError, NetworkHandoff, NetworkTarget
from lychd.system.services.scout_fetch import FetchedPage, FetchObservation
from lychd.system.services.scout_http import HttpResponseParser


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Keep private runtime custody outside the image checkout's pytest cache."""
    with TemporaryDirectory(prefix="reach-scout-", dir="/tmp") as directory:
        yield Path(directory)


def profile(**changes: Any) -> ResearchRuntimeProfile:
    return ResearchRuntimeProfile(
        source_kind="operator_public_catalogue",
        public_catalogue_authorized=True,
        policy_revision=1,
        revocation_generation=0,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        catalogue=ResearchOptions(
            enabled=True,
            sources=(
                ResearchSource(
                    id="jjk",
                    title="Operator selected source",
                    url="https://example.com/guide",
                    focus=("Panda", "Cursed Corpse"),
                ),
            ),
        ),
        allowed_subject_ids=("operator",),
        allowed_channel_ids=("channel",),
        allowed_dm_user_ids=("operator",),
        resolver_address="1.1.1.1",
        resolver_custody_statement="Operator selected recursive resolver custody",
    ).model_copy(update=changes)


def job(**changes: Any) -> ResearchJob:
    return ResearchJob(
        event_id="event", subject_id="operator", conversation_id="channel", direct=False, source_ids=("jjk",)
    ).model_copy(update=changes)


def prepare(tmp_path: Path, selected: ResearchRuntimeProfile | None = None) -> tuple[worker.CurrentProfile, Path]:
    path = tmp_path / "profile.json"
    path.write_text((selected or profile()).model_dump_json())
    path.chmod(0o600)
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    return worker.CurrentProfile.load(path), state


def install_acquisition(
    monkeypatch: pytest.MonkeyPatch, *, text: str = "Panda is an attributed fictional character."
) -> tuple[Mock, Mock]:
    body = b"untrusted original response body"
    fetched, extracted = Mock(), Mock()

    async def fetch(*args: object, **kwargs: Any) -> FetchedPage:
        fetched(*args, **kwargs)
        observation = FetchObservation(
            preflight_destination("https://example.com/guide"),
            ("93.184.216.34",),
            "93.184.216.34",
            200,
            64,
            len(body),
            len(body),
            len(body),
            "a" * 64,
        )
        return FetchedPage("text/plain", body, (observation,))

    async def extract(*args: object, **kwargs: Any) -> ExtractedText:
        extracted(*args, **kwargs)
        kwargs["lifecycle"]._child = "reaped"
        return ExtractedText(
            "text/plain",
            text,
            sha256(body).hexdigest(),
            "a" * 64,
            sha256(text.encode()).hexdigest(),
            "plain-text@1",
            (),
        )

    monkeypatch.setattr(worker, "fetch_static_page", fetch)
    monkeypatch.setattr(worker, "extract_static_text", extract)
    return fetched, extracted


@pytest.mark.asyncio
async def test_admitted_source_has_bounded_attribution_and_no_body_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current, state = prepare(tmp_path)
    text = "prefix " * 1000 + "PANDA is a Cursed Corpse. " + "tail " * 1000
    fetched, extracted = install_acquisition(monkeypatch, text=text)
    (result,) = await worker.research(current, state, job())
    assert result.status == "ok"
    assert result.http_status == 200
    assert result.id == "web:jjk"
    assert result.title == current.profile.catalogue.sources[0].title
    assert result.url == "https://example.com/guide"
    assert len(result.text) == 4000
    assert "PANDA" in result.text
    assert result.excerpt_start == 6500
    assert result.source_chars == len(text)
    assert result.truncated
    assert result.text == text[result.excerpt_start : result.excerpt_start + 4000]
    assert result.text_digest == sha256(result.text.encode()).hexdigest()
    assert result.receipt_id == worker.receipt_identity("event", "jjk")
    assert fetched.call_args.kwargs["permitted_redirects"] == ()
    assert fetched.call_args.kwargs["ca_file"] == worker.CA_FILE
    assert extracted.call_args.kwargs["runtime"].python_root == Path("/opt/scout-python")
    retained = (state / "journal.json").read_text()
    assert "PANDA" not in retained
    assert "untrusted" not in retained
    assert "example.com" not in retained
    assert set(json.loads(retained)) == {"profile_digest", "attempts"}


@pytest.mark.asyncio
async def test_successful_duplicate_has_receipt_but_never_reconstructs_material(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current, state = prepare(tmp_path)
    fetched, _ = install_acquisition(monkeypatch)
    (original,) = await worker.research(current, state, job())
    (duplicate,) = await worker.research(current, state, job())
    assert fetched.call_count == 1
    assert duplicate.status == "unavailable"
    assert duplicate.http_status is None
    assert duplicate.reason == "material_unavailable"
    assert duplicate.text == ""
    assert duplicate.source_digest is None
    assert duplicate.receipt_id == original.receipt_id


@pytest.mark.parametrize("text", ["", " \t\n"], ids=["empty", "whitespace"])
@pytest.mark.asyncio
async def test_empty_successful_extraction_is_explicitly_unavailable_and_stays_charged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    current, state = prepare(tmp_path, profile(max_attempts=1))
    fetched, extracted = install_acquisition(monkeypatch, text=text)
    (result,) = await worker.research(current, state, job())
    assert result.status == "unavailable"
    assert result.reason == "no_extractable_text"
    assert result.http_status == 200
    assert result.text == ""
    assert result.source_digest is None
    assert result.text_digest is None
    assert result.receipt_id == worker.receipt_identity("event", "jjk")
    assert fetched.call_count == 1
    assert extracted.call_count == 1
    (duplicate,) = await worker.research(current, state, job())
    (exhausted,) = await worker.research(current, state, job(event_id="another-event"))
    assert duplicate.reason == "material_unavailable"
    assert duplicate.receipt_id == result.receipt_id
    assert exhausted.reason == "budget"
    assert fetched.call_count == 1
    assert extracted.call_count == 1
    rows = json.loads((state / "journal.json").read_bytes())["attempts"]
    assert rows[result.receipt_id]["status"] == "refused"
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_changed_event_binding_refuses_with_no_contact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    current, state = prepare(tmp_path)
    fetched, _ = install_acquisition(monkeypatch)
    await worker.research(current, state, job())
    (changed,) = await worker.research(current, state, job(direct=True, conversation_id="dm-channel"))
    assert fetched.call_count == 1
    assert changed.status == "refused"
    assert changed.reason == "changed_request"


@pytest.mark.asyncio
async def test_restarted_unsettled_claim_stays_charged_and_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current, state = prepare(tmp_path, profile(max_attempts=1))
    fetched, _ = install_acquisition(monkeypatch)
    selected_job = job()
    source = current.profile.catalogue.sources[0]
    receipt = worker.receipt_identity(selected_job.event_id, source.id)
    binding = sha256(
        json.dumps(
            {
                "job": selected_job.model_dump(mode="json"),
                "source": source.model_dump(mode="json"),
                "profile": current.profile.digest,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    with worker.AttemptJournal(state, current.profile) as journal:
        assert journal.claim(receipt, binding) == "fresh"
    (duplicate,) = await worker.research(current, state, selected_job)
    (exhausted,) = await worker.research(current, state, job(event_id="new-event"))
    assert duplicate.reason == "material_unavailable"
    assert exhausted.reason == "budget"
    assert not fetched.called
    rows = json.loads((state / "journal.json").read_bytes())["attempts"]
    assert rows[receipt]["status"] == "unknown"
    assert len(rows) == 1


@pytest.mark.parametrize("ceiling", ["max_attempts", "max_connects", "max_transmissions", "max_wire_bytes"])
def test_each_cumulative_dimension_is_reserved_before_execution(tmp_path: Path, ceiling: str) -> None:
    selected = profile(
        **{
            ceiling: {"max_attempts": 1, "max_connects": 3, "max_transmissions": 512, "max_wire_bytes": 1048576}[
                ceiling
            ]
        }
    )
    current, state = prepare(tmp_path, selected)
    with worker.AttemptJournal(state, current.profile) as journal:
        assert journal.claim("a" * 64, "b" * 64) == "fresh"
        journal.settle("a" * 64, "refused")
        assert journal.claim("c" * 64, "d" * 64) == "budget"


def test_profile_change_cannot_reset_partition_or_receipt_identity(tmp_path: Path) -> None:
    current, state = prepare(tmp_path)
    with worker.AttemptJournal(state, current.profile) as journal:
        assert journal.claim(worker.receipt_identity("event", "jjk"), "a" * 64) == "fresh"
    replacement = current.profile.model_copy(update={"policy_revision": 2})
    with pytest.raises(worker.ResearchRefusedError), worker.AttemptJournal(state, replacement):
        pass
    assert worker.receipt_identity("event", "jjk") == worker.receipt_identity("event", "jjk")
    assert worker.receipt_identity("event", "jjk") != worker.receipt_identity("event", "other")


def test_partition_lock_serializes_whole_jobs(tmp_path: Path) -> None:
    current, state = prepare(tmp_path)
    with (
        worker.AttemptJournal(state, current.profile),
        pytest.raises(BlockingIOError),
        worker.AttemptJournal(state, current.profile),
    ):
        pass


def test_checkout_cannot_hold_private_attempt_custody() -> None:
    with (
        pytest.raises(worker.ResearchRefusedError),
        worker.AttemptJournal(worker.ROOT / ".cache" / "unadmitted-research", profile()),
    ):
        pass


@pytest.mark.asyncio
async def test_uncertain_reservation_acknowledgement_never_starts_network_or_replays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current, state = prepare(tmp_path)
    fetched, _ = install_acquisition(monkeypatch)
    original_fsync = os.fsync
    directory_syncs = 0

    def uncertain(descriptor: int) -> None:
        nonlocal directory_syncs
        original_fsync(descriptor)
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            directory_syncs += 1
        if directory_syncs == 2:
            message = "private storage diagnostic"
            raise OSError(message)

    monkeypatch.setattr(os, "fsync", uncertain)
    with pytest.raises(OSError, match="private storage diagnostic"):
        await worker.research(current, state, job())
    assert not fetched.called
    monkeypatch.setattr(os, "fsync", original_fsync)
    (result,) = await worker.research(current, state, job())
    assert result.reason == "material_unavailable"
    assert not fetched.called
    rows = json.loads((state / "journal.json").read_bytes())["attempts"]
    assert rows[worker.receipt_identity("event", "jjk")]["status"] == "unknown"


@pytest.mark.asyncio
async def test_cancellation_retains_unknown_charge_and_cannot_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current, state = prepare(tmp_path)

    async def cancelled(*_args: object, **_kwargs: object) -> FetchedPage:
        raise asyncio.CancelledError

    monkeypatch.setattr(worker, "fetch_static_page", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await worker.research(current, state, job())
    (result,) = await worker.research(current, state, job())
    assert result.reason == "material_unavailable"
    rows = json.loads((state / "journal.json").read_bytes())["attempts"]
    assert rows[worker.receipt_identity("event", "jjk")]["status"] == "unknown"


@pytest.mark.parametrize("target", ["profile", "state", "journal", "lock", "parent"])
def test_symlinked_authority_and_custody_refuse(tmp_path: Path, target: str) -> None:
    current, state = prepare(tmp_path)
    if target == "parent":
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(OSError, match=r"Too many levels|Not a directory"):
            worker.CurrentProfile.load(alias / "profile.json")
        return
    path = (
        current.path
        if target == "profile"
        else state
        if target == "state"
        else state / ("journal.json" if target == "journal" else "lock")
    )
    if path.exists():
        saved = path.with_name(path.name + ".real")
        path.rename(saved)
    else:
        saved = tmp_path / "foreign"
        saved.write_text("{}")
        saved.chmod(0o600)
    path.symlink_to(saved, target_is_directory=target == "state")
    with pytest.raises((OSError, worker.ResearchRefusedError)):  # noqa: PT012 - exercise the same boundary across path kinds
        if target == "profile":
            worker.CurrentProfile.load(path)
        else:
            with worker.AttemptJournal(state, current.profile):
                pass


@pytest.mark.parametrize("target", ["profile", "state", "journal", "lock"])
def test_group_or_world_accessible_authority_refuses(tmp_path: Path, target: str) -> None:
    current, state = prepare(tmp_path)
    if target in {"journal", "lock"}:
        with worker.AttemptJournal(state, current.profile):
            pass
    path = (
        current.path
        if target == "profile"
        else state
        if target == "state"
        else state / ("journal.json" if target == "journal" else "lock")
    )
    path.chmod(0o755 if target == "state" else 0o644)
    with pytest.raises(worker.ResearchRefusedError):  # noqa: PT012 - exercise the same boundary across path kinds
        if target == "profile":
            worker.CurrentProfile.load(path)
        else:
            with worker.AttemptJournal(state, current.profile):
                pass


@pytest.mark.parametrize(
    "changes",
    [
        {"subject_id": "other"},
        {"conversation_id": "other"},
        {"source_ids": ("unknown",)},
        {"source_ids": ("jjk", "jjk")},
        {"direct": True, "subject_id": "other"},
    ],
)
@pytest.mark.asyncio
async def test_whole_job_selector_refusal_precedes_journal_and_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changes: dict[str, Any]
) -> None:
    current, state = prepare(tmp_path)
    fetched, _ = install_acquisition(monkeypatch)
    with pytest.raises(worker.ResearchRefusedError):
        await worker.research(current, state, job(**changes))
    assert not fetched.called
    assert list(state.iterdir()) == []


@pytest.mark.asyncio
async def test_expired_profile_never_reserves_or_contacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    current, state = prepare(tmp_path)
    fetched, _ = install_acquisition(monkeypatch)
    expired = replace(
        current, profile=current.profile.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)})
    )
    with pytest.raises(worker.ResearchRefusedError):
        await worker.research(expired, state, job())
    assert not fetched.called
    assert list(state.iterdir()) == []


@pytest.mark.parametrize("phase", ["extract", "consume"])
@pytest.mark.asyncio
async def test_profile_change_after_await_fences_next_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    current, state = prepare(tmp_path)
    _, extracted = install_acquisition(monkeypatch)
    original_fetch = worker.fetch_static_page
    original_extract = worker.extract_static_text

    def revoke() -> None:
        current.path.write_text(current.profile.model_copy(update={"revocation_generation": 1}).model_dump_json())

    async def fetch(*args: Any, **kwargs: Any) -> FetchedPage:
        result = await original_fetch(*args, **kwargs)
        revoke()
        return result

    async def extract(*args: Any, **kwargs: Any) -> ExtractedText:
        result = await original_extract(*args, **kwargs)
        revoke()
        return result

    monkeypatch.setattr(
        worker,
        "fetch_static_page" if phase == "extract" else "extract_static_text",
        fetch if phase == "extract" else extract,
    )
    (result,) = await worker.research(current, state, job())
    assert result.status == "unavailable"
    assert result.text == ""
    assert extracted.call_count == (0 if phase == "extract" else 1)
    assert result.http_status == 200


def dns_query(hostname: str, family: int) -> bytes:
    name = b"".join(bytes([len(part)]) + part.encode() for part in hostname.split("."))
    body = b"\x12\x34\x01\x00\x00\x01" + b"\x00" * 6 + name + b"\x00" + family.to_bytes(2, "big") + b"\x00\x01"
    return len(body).to_bytes(2, "big") + body


def resolve(gate: worker.CatalogueNetworkGate, current: worker.CurrentProfile) -> None:
    target = NetworkTarget(current.profile.resolver_address, 53, "example.com", "resolver")
    for family in (1, 28):
        assert gate.handoff(NetworkHandoff(target, "connect", b"", None), lambda: 0) == 0
        query = dns_query("example.com", family)
        assert gate.handoff(NetworkHandoff(target, "dns", query, query), lambda query=query: len(query)) == len(query)


@pytest.mark.asyncio
async def test_native_gate_has_exact_dns_tls_http_road_and_one_action(tmp_path: Path) -> None:
    current, _ = prepare(tmp_path)
    candidate = preflight_destination("https://example.com/guide")
    gate = worker.CatalogueNetworkGate(current, candidate, worker.time.monotonic() + 30)
    resolve(gate, current)
    target = NetworkTarget("93.184.216.34", 443, "example.com", "origin")
    action = Mock(return_value=0)
    gate.handoff(NetworkHandoff(target, "connect", b"", None), action)
    action.assert_called_once_with()
    gate.handoff(NetworkHandoff(target, "tls", b"encrypted hello", None), lambda: len(b"encrypted hello"))
    application = worker.serialize_get(candidate)
    gate.handoff(NetworkHandoff(target, "http", b"ciphertext", application), lambda: len(b"ciphertext"))
    # These counters are owned gate invariants, without a public accounting projection.
    assert gate._connects == 3  # pyright: ignore[reportPrivateUsage]
    assert gate._transmissions == 4  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "target",
    [
        NetworkTarget("8.8.8.8", 53, "example.com", "resolver"),
        NetworkTarget("1.1.1.1", 54, "example.com", "resolver"),
        NetworkTarget("1.1.1.1", 53, "other.example", "resolver"),
        NetworkTarget("1.1.1.1", 53, "example.com", "origin"),
    ],
)
@pytest.mark.asyncio
async def test_substituted_resolver_never_calls_action(tmp_path: Path, target: NetworkTarget) -> None:
    current, _ = prepare(tmp_path)
    gate = worker.CatalogueNetworkGate(
        current, preflight_destination("https://example.com/guide"), worker.time.monotonic() + 30
    )
    action = Mock(return_value=0)
    with pytest.raises(FetchError):
        gate.handoff(NetworkHandoff(target, "connect", b"", None), action)
    action.assert_not_called()


@pytest.mark.parametrize(
    "mutation", ["dns", "private", "hostname", "port", "http", "expiry", "revocation", "transmissions", "bytes"]
)
@pytest.mark.asyncio
async def test_hostile_handoffs_refuse_before_syscall(tmp_path: Path, mutation: str) -> None:
    current, _ = prepare(tmp_path)
    gate = worker.CatalogueNetworkGate(
        current, preflight_destination("https://example.com/guide"), worker.time.monotonic() + 30
    )
    target = NetworkTarget("93.184.216.34", 443, "example.com", "origin")
    action = Mock(return_value=0)
    if mutation == "dns":
        resolver = NetworkTarget(current.profile.resolver_address, 53, "example.com", "resolver")
        gate.handoff(NetworkHandoff(resolver, "connect", b"", None), lambda: 0)
        query = dns_query("secret.other.example", 1)
        handoff = NetworkHandoff(resolver, "dns", query, query)
    else:
        resolve(gate, current)
        if mutation == "private":
            target = NetworkTarget("127.0.0.1", 443, "example.com", "origin")
        if mutation == "hostname":
            target = NetworkTarget(target.address, 443, "other.example", "origin")
        if mutation == "port":
            target = NetworkTarget(target.address, 444, "example.com", "origin")
        handoff = NetworkHandoff(target, "connect", b"", None)
        if mutation in {"http", "expiry", "revocation", "transmissions", "bytes"}:
            gate.handoff(handoff, lambda: 0)
            handoff = (
                NetworkHandoff(target, "http", b"wire", b"GET /secret HTTP/1.1\r\n")
                if mutation == "http"
                else NetworkHandoff(target, "tls", b"wire", None)
            )
            if mutation == "expiry":
                # Seed the time boundary without a wait or a global clock replacement.
                gate._deadline = worker.time.monotonic() - 1  # pyright: ignore[reportPrivateUsage]
            if mutation == "revocation":
                current.path.write_bytes(current.path.read_bytes() + b" ")
            if mutation == "transmissions":
                # Exercise the exhausted reservation before another syscall is admitted.
                gate._transmissions = worker.ATTEMPT_TRANSMISSIONS  # pyright: ignore[reportPrivateUsage]
            if mutation == "bytes":
                gate._wire_bytes = worker.ATTEMPT_WIRE_BYTES  # pyright: ignore[reportPrivateUsage]
    with pytest.raises((ValueError, OSError)):
        gate.handoff(handoff, action)
    action.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_send_holds_charge_and_does_not_expose_foreign_error(tmp_path: Path) -> None:
    current, _ = prepare(tmp_path)
    gate = worker.CatalogueNetworkGate(
        current, preflight_destination("https://example.com/guide"), worker.time.monotonic() + 30
    )
    resolve(gate, current)
    target = NetworkTarget("93.184.216.34", 443, "example.com", "origin")
    gate.handoff(NetworkHandoff(target, "connect", b"", None), lambda: 0)
    # The offered-byte debit must survive an uncertain syscall outcome.
    before = gate._wire_bytes  # pyright: ignore[reportPrivateUsage]

    def broken() -> int:
        message = "foreign secret diagnostic"
        raise OSError(message)

    with pytest.raises(OSError, match="foreign secret diagnostic"):
        gate.handoff(NetworkHandoff(target, "tls", b"ciphertext", None), broken)
    assert gate.uncertain
    assert gate._wire_bytes == before + len(b"ciphertext")  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("failure", ["fetch", "extract", "cleanup", "hostile_record"])
@pytest.mark.asyncio
async def test_failures_are_closed_and_cleanup_uncertainty_is_not_refunded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    current, state = prepare(tmp_path, profile(max_attempts=1))
    fetched, _ = install_acquisition(monkeypatch)

    async def fail(*args: object, **kwargs: Any) -> Any:
        if failure == "fetch":
            raise FetchError(FetchCode.MEDIA)
        if failure == "cleanup":
            kwargs["lifecycle"]._child = None
            raise ExtractionError(ExtractionCode.CLEANUP)
        if failure == "extract":
            message = "<html>foreign diagnostic and secret</html>"
            raise ValueError(message)
        kwargs["lifecycle"]._child = "reaped"
        return {"text": "<html>foreign secret</html>", "url": "https://evil.example/"}

    monkeypatch.setattr(worker, "fetch_static_page" if failure == "fetch" else "extract_static_text", fail)
    (result,) = await worker.research(current, state, job())
    assert result.status == "unavailable"
    assert result.http_status == (None if failure == "fetch" else 200)
    assert result.text == ""
    assert "foreign" not in result.model_dump_json()
    assert "evil" not in result.model_dump_json()
    (denied,) = await worker.research(current, state, job(event_id="next"))
    assert denied.reason == "budget"
    rows = json.loads((state / "journal.json").read_bytes())["attempts"]
    assert rows[worker.receipt_identity("event", "jjk")]["status"] == (
        "unknown" if failure in {"cleanup", "extract"} else "refused"
    )
    assert fetched.call_count == (0 if failure == "fetch" else 1)


@pytest.mark.parametrize("head", [b"HTTP/1.1 403 Forbidden\r\n\r\n", b"malformed\r\n\r\n"])
@pytest.mark.asyncio
async def test_parser_http_status_reaches_unavailable_source_without_foreign_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, head: bytes
) -> None:
    current, state = prepare(tmp_path)
    _, extracted = install_acquisition(monkeypatch)

    async def refused(*_args: object, **_kwargs: object) -> FetchedPage:
        HttpResponseParser().feed(head)
        pytest.fail("Refused response unexpectedly accepted")

    monkeypatch.setattr(worker, "fetch_static_page", refused)
    (result,) = await worker.research(current, state, job())
    assert result.status == "unavailable"
    assert result.reason == "fetch_protocol"
    assert result.http_status == (403 if b"403" in head else None)
    assert result.text == ""
    assert "Forbidden" not in result.model_dump_json()
    extracted.assert_not_called()


def test_casefold_focus_preserves_original_unicode_offsets() -> None:
    text = "ß" * 600 + "PANDA" + "z" * 5000
    excerpt, start = worker.project_excerpt(text, ("panda",))
    assert start == 100
    assert excerpt == text[100:4100]
    assert worker.project_excerpt("Cursed Corpse first and Panda later", ("Panda", "cursed corpse"))[1] == 0


def test_fixed_runtime_has_no_fallback_or_request_selected_paths() -> None:
    runtime = worker.extraction_runtime()
    assert runtime.bwrap == Path("/usr/bin/bwrap")
    assert runtime.python_root == Path("/opt/scout-python")
    assert len(runtime.libraries) == 8
    assert {path.parent for path in runtime.libraries} == {Path("/usr/lib/x86_64-linux-gnu")}


@pytest.mark.parametrize(
    "raw", [b"private malformed input", b'{"event_id":"a","event_id":"b"}\n', b"x" * (worker.MAX_INPUT_BYTES + 1)]
)
def test_main_invalid_frames_are_nonzero_fixed_and_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], raw: bytes
) -> None:
    monkeypatch.setattr(worker, "_require_image", lambda: None)
    monkeypatch.setattr(worker.sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))
    assert worker.main(["--profile", str(tmp_path / "missing"), "--state-dir", str(tmp_path / "missing")]) == 1
    captured = capsys.readouterr()
    assert captured.out == "[]\n"
    assert captured.err == "reach_scout_worker_refused\n"
    assert len(captured.out.encode()) <= worker.MAX_OUTPUT_BYTES


def test_main_requires_oci_before_reading_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unavailable_file(_path: Path) -> bool:
        return False

    monkeypatch.setattr(worker.Path, "is_file", unavailable_file)
    assert (
        worker.main(["--profile", str(tmp_path / "private-name"), "--state-dir", str(tmp_path / "private-name")]) == 1
    )
    captured = capsys.readouterr()
    assert captured.out == "[]\n"
    assert captured.err == "reach_scout_worker_refused\n"
