"""Fixed distro program behavior and readiness boundary; no network qualification."""

from __future__ import annotations

# Probe the standalone script's private, fixed runtime boundaries.
# pyright: reportPrivateUsage=false
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lychd.domain.tether.models import render_nftables, render_wireguard_public
from lychd.system.services.tether import runtime
from tests.unit.system.services.test_tether_operations import make_peer, make_plan


def test_standalone_nft_policy_matches_the_domain_compiler_exactly() -> None:
    plan, peer = make_plan(), make_peer()
    public = render_wireguard_public(plan, peer).model_dump(mode="json")
    assert runtime.nft_policy(public) == render_nftables(plan, peer)
    assert "ct state new,established accept" in runtime.nft_policy(public)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("peer_address", "8.8.8.8/32"),
        ("server_address", "10.77.0.1/24"),
        ("listen_port", 53),
        ("ssh_port", True),
        ("interface", "eth0"),
        ("interface", "wg0;id"),
        ("unknown", "value"),
    ],
)
def test_runtime_revalidates_closed_public_projection(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    public = render_wireguard_public(make_plan(), make_peer()).model_dump(mode="json")
    public[field] = value
    monkeypatch.setattr(runtime, "_read", lambda *_: json.dumps(public))
    with pytest.raises((RuntimeError, ValueError)):
        runtime._public()


def test_wireguard_installs_nft_before_interface_and_notifies_after_readback(monkeypatch: pytest.MonkeyPatch) -> None:
    public = render_wireguard_public(make_plan(), make_peer()).model_dump(mode="json")
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(runtime, "_public", lambda: public)
    monkeypatch.setattr(runtime, "_read", lambda *_: make_peer().wireguard_public_key)
    monkeypatch.setattr(runtime, "_run", lambda argv, **_: calls.append(argv) or "")
    monkeypatch.setattr(runtime, "_verify", lambda _: calls.append(("verified",)))
    monkeypatch.setattr(runtime, "_notify_ready", lambda: calls.append(("READY=1",)))
    monkeypatch.setattr(runtime.time, "sleep", MagicMock(side_effect=KeyboardInterrupt))
    with pytest.raises(KeyboardInterrupt):
        runtime.wireguard()
    assert calls[0] == ("/usr/sbin/nft", "-f", "-")
    assert calls.index(("verified",)) < calls.index(("READY=1",))
    assert any(argv[:2] == ("/usr/bin/wg", "setconf") for argv in calls)
    assert calls[-1] == ("/usr/sbin/ip", "link", "delete", "dev", "wgaltar")
    assert all(make_peer().wireguard_public_key not in str(argv) for argv in calls)


def test_no_ready_notification_after_policy_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runtime, "_public", lambda: render_wireguard_public(make_plan(), make_peer()).model_dump(mode="json")
    )
    monkeypatch.setattr(runtime, "_run", MagicMock(side_effect=RuntimeError("nft failed")))
    notify = MagicMock()
    monkeypatch.setattr(runtime, "_notify_ready", notify)
    with pytest.raises(RuntimeError, match="nft failed"):
        runtime.wireguard()
    notify.assert_not_called()


def test_image_has_only_standard_distro_runtime_and_exact_entry() -> None:
    root = Path(__file__).resolve().parents[4]
    image = (root / "Containerfile.tether").read_text()
    assert "wireguard-tools iproute2 nftables openssh-server" in image
    assert '"/usr/bin/python3", "/usr/libexec/lychd-tether-runtime", "wireguard"' in image
    assert "COPY src/lychd/system/services/tether/runtime.py" in image
    assert "uv sync" not in image


def test_nft_transaction_uses_exclusive_create_and_failure_never_adds_interface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime, "_public", lambda: render_wireguard_public(make_plan(), make_peer()).model_dump(mode="json")
    )
    calls: list[tuple[str, ...]] = []

    def existing_table(argv: tuple[str, ...], *, content: str | None = None, **_: object) -> str:
        calls.append(argv)
        assert content is not None
        assert content.startswith("create table inet lychd_tether\n")
        msg = "exclusive table already exists"
        raise RuntimeError(msg)

    monkeypatch.setattr(runtime, "_run", existing_table)
    with pytest.raises(RuntimeError, match="already exists"):
        runtime.wireguard()
    assert calls == [("/usr/sbin/nft", "-f", "-")]
