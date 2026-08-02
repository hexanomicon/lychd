"""Focused unit receipts for durable Codex policy bindings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import uuid4

import pytest

from lychd.db.models import CodexPreauthorization, Consent
from lychd.domain.codex import ledger as ledger_module
from lychd.domain.codex.ledger import InMemoryConsentLedger
from lychd.domain.codex.services import (
    PREAUTH_DIGEST_PAYLOAD_KEY,
    ConsentService,
    preauth_authorization_digest,
)
from lychd.domain.codex.sigil import Sigil


def _preauth(**overrides: object) -> CodexPreauthorization:
    values: dict[str, object] = {
        "slug": "bounded-edit",
        "klass": "zte",
        "sigil_pattern": "magus",
        "tool_pattern": "edit_file",
        "constraints": {"args": {"mode": ["safe"], "root": ["/work"]}},
        "expires_at": datetime(2030, 1, 1, tzinfo=UTC),
        "max_uses": 3,
        "uses": 1,
        "enabled": True,
        "granted_by": "codex:rune",
        "source_file": "/runes/codex/preauth/bounded-edit.toml",
    }
    values.update(overrides)
    return CodexPreauthorization(**values)


def test_preauth_digest_is_canonical_and_excludes_mutable_runtime_state() -> None:
    first = _preauth()
    same_authority = _preauth(
        constraints={"args": {"root": ["/work"], "mode": ["safe"]}},
        expires_at=datetime(2030, 1, 1, 1, tzinfo=timezone(timedelta(hours=1))),
        uses=99,
        enabled=False,
        source_present=False,
    )

    assert preauth_authorization_digest(first) == preauth_authorization_digest(same_authority)

    changed_policy = _preauth(max_uses=4)
    changed_priority = _preauth(priority=90)
    changed_grantor = _preauth(granted_by="magus:operator")
    assert preauth_authorization_digest(first) != preauth_authorization_digest(changed_policy)
    assert preauth_authorization_digest(first) != preauth_authorization_digest(changed_priority)
    assert preauth_authorization_digest(first) != preauth_authorization_digest(changed_grantor)


class _CaptureCreate:
    def __init__(self) -> None:
        self.auto_commit: bool | None = None

    async def create(self, data: Consent, *, auto_commit: bool) -> Consent:
        self.auto_commit = auto_commit
        return data


@pytest.mark.asyncio
async def test_auto_grant_payload_binds_the_authorizing_preauth() -> None:
    capture = _CaptureCreate()
    service = cast("ConsentService", capture)
    preauth = _preauth()

    row = await ConsentService.request(
        service,
        run_id=str(uuid4()),
        tool_name="edit_file",
        tool_call_id="call-1",
        call_ids=("call-1",),
        payload={"mode": "safe", "token": "secret"},
        preauth=preauth,
        auto_commit=False,
    )

    assert row.payload[PREAUTH_DIGEST_PAYLOAD_KEY] == preauth_authorization_digest(preauth)
    assert row.payload["args"]["token"] == "‹censored›"  # noqa: RUF001, S105
    assert capture.auto_commit is False


@pytest.mark.asyncio
async def test_in_memory_latest_for_run_breaks_timestamp_ties_by_id(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed = datetime(2030, 1, 1, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(ledger_module, "datetime", FrozenDateTime)
    ledger = InMemoryConsentLedger()
    sigil = Sigil(name="magus", scopes=frozenset({"*"}))
    first = await ledger.park(
        run_id="run-1",
        tool_name="edit_file",
        tool_call_id="call-1",
        call_ids=("call-1",),
        args={},
        sigil=sigil,
    )
    second = await ledger.park(
        run_id="run-1",
        tool_name="edit_file",
        tool_call_id="call-2",
        call_ids=("call-2",),
        args={},
        sigil=sigil,
    )

    latest = await ledger.latest_for_run("run-1")
    assert latest is not None
    assert latest.id == max(first.consent_id, second.consent_id)
