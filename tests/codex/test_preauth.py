"""Preauthorization + consent floor: censor, constraints, ZTE, in-memory match."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lychd.domain.codex.ledger import InMemoryConsentLedger
from lychd.domain.codex.runes import CodexPreauthRune
from lychd.domain.codex.schemas import censor, constraints_admit
from lychd.domain.codex.sigil import Sigil


def _sigil(name: str = "magus") -> Sigil:
    return Sigil(name=name, scopes=frozenset({"*"}))


# -- censor -----------------------------------------------------------------


def test_censor_scrubs_secret_shaped_keys() -> None:
    payload = {
        "api_key": "sk-123",
        "password": "hunter2",
        "access_token": "t",
        "credential_blob": "c",
        "reason": "please",
        "nested": {"secret_value": "x", "safe": "ok"},
        "items": [{"token": "y"}, "plain"],
    }
    censored = censor(payload)
    assert censored["api_key"] == "‹censored›"  # noqa: RUF001
    assert censored["password"] == "‹censored›"  # noqa: RUF001, S105
    assert censored["access_token"] == "‹censored›"  # noqa: RUF001, S105
    assert censored["credential_blob"] == "‹censored›"  # noqa: RUF001
    assert censored["reason"] == "please"
    assert censored["nested"]["secret_value"] == "‹censored›"  # noqa: RUF001, S105
    assert censored["nested"]["safe"] == "ok"
    assert censored["items"][0]["token"] == "‹censored›"  # noqa: RUF001, S105
    assert censored["items"][1] == "plain"


# -- constraints_admit (fail-closed) ----------------------------------------


def test_constraints_empty_admits_anything() -> None:
    assert constraints_admit({}, {"anything": 1}) is True


def test_constraints_unknown_key_is_fail_closed() -> None:
    assert constraints_admit({"bogus": True}, {}) is False


def test_constraints_args_allowlist() -> None:
    constraints = {"args": {"capability_key": ["chat:local", "chat:remote"]}}
    assert constraints_admit(constraints, {"capability_key": "chat:local"}) is True
    assert constraints_admit(constraints, {"capability_key": "chat:evil"}) is False


def test_constraints_path_prefixes() -> None:
    constraints = {"path_prefixes": ["/home/lych/work"]}
    assert constraints_admit(constraints, {"path": "/home/lych/work/x"}) is True
    assert constraints_admit(constraints, {"path": "/etc/passwd"}) is False


# -- ZTE bounded invariant --------------------------------------------------


def test_zte_requires_bounds() -> None:
    with pytest.raises(ValueError, match="BOUNDED"):
        CodexPreauthRune(slug="z", klass="zte", tool_pattern="*")


def test_zte_bounded_is_valid() -> None:
    rune = CodexPreauthRune(
        slug="z",
        klass="zte",
        tool_pattern="request_coven_swap",
        constraints={"args": {"capability_key": ["chat:local"]}},
        expires_at=datetime.now(UTC) + timedelta(days=1),
        max_uses=2,
    )
    assert rune.klass == "zte"


# -- InMemoryConsentLedger preauth match / exhaustion -----------------------


def _preauth(**kw: object) -> CodexPreauthRune:
    base: dict[str, object] = {"slug": "p", "tool_pattern": "request_coven_swap"}
    base.update(kw)
    return CodexPreauthRune(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_preauth_auto_grants() -> None:
    ledger = InMemoryConsentLedger(preauths=[_preauth()])
    decision = await ledger.park(
        run_id="r1",
        tool_name="request_coven_swap",
        tool_call_id="c1",
        call_ids=("c1",),
        args={"reason": "why"},
        sigil=_sigil(),
    )
    assert decision.status == "granted"
    assert decision.preauth_slug == "p"
    assert await ledger.verdict(decision.consent_id) is True


@pytest.mark.asyncio
async def test_preauth_exhaustion_falls_to_pending() -> None:
    ledger = InMemoryConsentLedger(preauths=[_preauth(max_uses=1)])
    first = await ledger.park(
        run_id="r1", tool_name="request_coven_swap", tool_call_id="c1", call_ids=("c1",), args={}, sigil=_sigil()
    )
    second = await ledger.park(
        run_id="r2", tool_name="request_coven_swap", tool_call_id="c2", call_ids=("c2",), args={}, sigil=_sigil()
    )
    assert first.status == "granted"
    assert second.status == "pending"  # budget exhausted → live consent required
    assert await ledger.verdict(second.consent_id) is None


@pytest.mark.asyncio
async def test_preauth_constraint_miss_falls_to_pending() -> None:
    rune = _preauth(constraints={"args": {"capability_key": ["chat:local"]}})
    ledger = InMemoryConsentLedger(preauths=[rune])
    decision = await ledger.park(
        run_id="r1",
        tool_name="request_coven_swap",
        tool_call_id="c1",
        call_ids=("c1",),
        args={"capability_key": "chat:evil"},
        sigil=_sigil(),
    )
    assert decision.status == "pending"


@pytest.mark.asyncio
async def test_park_pending_then_decide() -> None:
    ledger = InMemoryConsentLedger()
    decision = await ledger.park(
        run_id="r1", tool_name="request_coven_swap", tool_call_id="c1", call_ids=("c1",), args={}, sigil=_sigil()
    )
    assert decision.status == "pending"
    assert await ledger.pending_count() == 1
    view = await ledger.decide(decision.consent_id, approved=True, decided_by="magus")
    assert view is not None
    assert view.status == "granted"
    assert view.decided_by == "magus"
    assert await ledger.verdict(decision.consent_id) is True
    assert await ledger.pending_count() == 0
    # idempotent: a settled verdict is never re-decided
    again = await ledger.decide(decision.consent_id, approved=False, decided_by="other")
    assert again is not None
    assert again.status == "granted"
