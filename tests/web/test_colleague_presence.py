"""Paired Nexus boards use expiring encrypted files and exact local audience consent."""

from __future__ import annotations

import os
import secrets
import shutil
import time
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from lychd.config.settings.presence import PresencePair, PresenceSettings
from lychd.system.services.colleague_presence import ColleaguePresence

if TYPE_CHECKING:
    from pathlib import Path

    from tests.web.conftest import AsgiClient

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Descriptor-relative presence folder profile")


def _settings(root: Path, slot: Literal["a", "b"], name: str, key: str) -> PresenceSettings:
    replica = root / "replica"
    secrets_dir = root / "keys"
    replica.mkdir(mode=0o700, parents=True)
    secrets_dir.mkdir(mode=0o700)
    key_file = secrets_dir / "pair"
    key_file.write_text(key)
    key_file.chmod(0o600)
    return PresenceSettings(pairs=(PresencePair(name=name, slot=slot, directory=replica, key_file=key_file),))


def test_two_paired_nexus_operators(  # noqa: PLR0915 - One paired history checks replay, withdrawal, expiry and revocation.
    altar_client: AsgiClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = tmp_path / "alice", tmp_path / "bob"
    key = secrets.token_hex(32)
    settings_a = _settings(first, "a", "Bob", key)
    settings_b = _settings(second, "b", "Alice", key)
    now = time.time_ns()
    monkeypatch.setattr(time, "time_ns", lambda: now)
    with ColleaguePresence.open(settings_a) as alice, ColleaguePresence.open(settings_b) as bob:

        def choose(owner: ColleaguePresence, status: str) -> None:
            altar_client.app.state.colleague_presence = owner
            snapshot = altar_client.get("/api/v1/nexus").json()["presence"]
            response = altar_client.post(
                "/api/v1/nexus/presence",
                json={"availability": status, "audience_id": snapshot["audience_id"]},
            )
            assert response.status_code == 200
            assert response.json()["sharing"] == status

        def copy_report(sender: Path, receiver: Path, slot: str) -> None:
            shutil.copyfile(sender / "replica" / slot, receiver / "replica" / slot)

        assert not list((first / "replica").iterdir())
        choose(alice, "ready")
        ready = (first / "replica/a.lease").read_bytes()
        assert b"ready" not in ready
        copy_report(first, second, "a.lease")
        choose(bob, "busy")
        assert bob.board().peers[0].availability == "ready"
        copy_report(second, first, "b.lease")
        now += 1_000_000_000
        choose(alice, "busy")
        assert alice.board().peers[0].availability == "busy"
        copy_report(first, second, "a.lease")
        choose(bob, "busy")
        assert bob.board().peers[0].availability == "busy"

        (second / "replica/a.lease").write_bytes(ready)
        choose(bob, "busy")
        assert bob.board().peers[0].availability == "unknown"
        (second / "replica/a.lease").write_bytes((second / "replica/b.lease").read_bytes())
        choose(bob, "busy")
        assert bob.board().peers[0].availability == "unknown"
        copy_report(first, second, "a.lease")
        choose(bob, "busy")
        assert bob.board().peers[0].availability == "busy"
        now += 1_000_000_000

        # The previous Busy report is still live. A failed withdrawal must remain retryable.
        def fail_replace(*_args: object, **_kwargs: object) -> None:
            msg = "Temporary replica failure"
            raise OSError(msg)

        with monkeypatch.context() as fault:
            fault.setattr(os, "replace", fail_replace)
            choose(alice, "hidden")
            assert alice.board().peers[0].publication == "unavailable"
        choose(alice, "hidden")
        copy_report(first, second, "a.lease")
        choose(bob, "busy")
        assert bob.board().peers[0].availability == "unknown"
        assert alice.board().sharing_until is None
        now += 1_000_000_000
        choose(alice, "ready")
        copy_report(first, second, "a.lease")
        choose(bob, "busy")
        assert bob.board().peers[0].availability == "ready"
        now += 31_000_000_000
        assert bob.board().peers[0].availability == "unknown"
        now += 3_600_000_000_000
        assert bob.board().sharing == "hidden"
        now -= 3_600_000_000_000
        assert bob.board().sharing == "hidden"
        altar_client.app.state.local_operator_access.revoke()
        assert alice.board().sharing == "hidden"


def test_absent_and_restarted_pairing_reject_mutation(altar_client: AsgiClient, tmp_path: Path) -> None:
    intent = {"availability": "ready", "audience_id": str(uuid4())}
    assert altar_client.get("/api/v1/nexus").json()["presence"] is None
    assert altar_client.post("/api/v1/nexus/presence", json=intent).status_code == 404
    settings = _settings(tmp_path, "a", "Bob", secrets.token_hex(32))
    with ColleaguePresence.open(settings) as first:
        intent["audience_id"] = str(first.board().audience_id)
    with ColleaguePresence.open(settings) as second:
        altar_client.app.state.colleague_presence = second
        assert altar_client.post("/api/v1/nexus/presence", json=intent).status_code == 409
        assert not list(settings.pairs[0].directory.iterdir())


def test_pair_refuses_shared_keys_unsafe_placement_and_permissions(tmp_path: Path) -> None:
    key = secrets.token_hex(32)
    a = _settings(tmp_path / "one", "a", "One", key).pairs[0]
    b = _settings(tmp_path / "two", "a", "Two", key).pairs[0]
    with pytest.raises(ValueError, match="dedicated"), ColleaguePresence.open(PresenceSettings(pairs=(a, b))):
        pytest.fail("Shared key accepted")
    with pytest.raises(ValidationError, match="outside"):
        PresenceSettings(pairs=(a.model_copy(update={"key_file": a.directory / "secret"}),))
    alias = tmp_path / "redirected-keys"
    alias.symlink_to(a.directory, target_is_directory=True)
    aliased = a.model_copy(update={"key_file": alias / "key"})
    with (
        pytest.raises(ValueError, match="physical custody"),
        ColleaguePresence.open(PresenceSettings(pairs=(aliased,))),
    ):
        pytest.fail("Exchange directory accepted as key custody")
    a.key_file.chmod(0o644)
    with pytest.raises(ValueError, match="owner-only"), ColleaguePresence.open(PresenceSettings(pairs=(a,))):
        pytest.fail("Public key file accepted")
