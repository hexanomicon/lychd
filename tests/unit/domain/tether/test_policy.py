from __future__ import annotations

import base64
from datetime import UTC, datetime
from ipaddress import ip_interface, ip_network

import pytest

from lychd.domain.tether.models import (
    TetherIntent,
    TetherInterfaceIntent,
    TetherPeerIntent,
    TetherPeerState,
)
from lychd.domain.tether.policy import TetherPolicyError, validate_tether_reconciliation

PUBLIC_KEY = base64.b64encode(bytes(range(32))).decode()


def _intent(*, intent_revision: int, peer_revision: int, state: TetherPeerState) -> TetherIntent:
    peer = TetherPeerIntent(
        peer_id="phone",
        revision=peer_revision,
        public_key=PUBLIC_KEY,
        allowed_routes=(ip_network("10.44.0.2/32"),),
        state=state,
        revoked_at=datetime(2026, 8, 6, tzinfo=UTC) if state is TetherPeerState.REVOKED else None,
    )
    return TetherIntent(
        revision=intent_revision,
        interface=TetherInterfaceIntent(
            addresses=(ip_interface("10.44.0.1/24"),),
            listen_port=51820,
            private_key_secret_name="tether_private_key",  # noqa: S106 - secret name, not value
        ),
        peers=(peer,),
    )


def test_reconciliation_requires_forward_generation() -> None:
    intent = _intent(intent_revision=2, peer_revision=1, state=TetherPeerState.ENABLED)

    with pytest.raises(TetherPolicyError, match="strictly newer"):
        validate_tether_reconciliation(intent, intent)


def test_reconciliation_cannot_revive_revoked_peer() -> None:
    previous = _intent(intent_revision=2, peer_revision=2, state=TetherPeerState.REVOKED)
    candidate = _intent(intent_revision=3, peer_revision=3, state=TetherPeerState.ENABLED)

    with pytest.raises(TetherPolicyError, match="cannot be revived"):
        validate_tether_reconciliation(previous, candidate)


def test_reconciliation_accepts_forward_revocation() -> None:
    previous = _intent(intent_revision=2, peer_revision=1, state=TetherPeerState.ENABLED)
    candidate = _intent(intent_revision=3, peer_revision=2, state=TetherPeerState.REVOKED)

    validate_tether_reconciliation(previous, candidate)


def test_reconciliation_requires_peer_revision_for_any_peer_change() -> None:
    previous = _intent(intent_revision=2, peer_revision=1, state=TetherPeerState.ENABLED)
    candidate = _intent(intent_revision=3, peer_revision=1, state=TetherPeerState.REVOKED)

    with pytest.raises(TetherPolicyError, match="changes require a newer peer revision"):
        validate_tether_reconciliation(previous, candidate)


def test_reconciliation_cannot_drop_peer_or_revocation_tombstone() -> None:
    previous = _intent(intent_revision=2, peer_revision=2, state=TetherPeerState.REVOKED)
    candidate = TetherIntent(
        revision=3,
        interface=previous.interface,
        peers=(),
    )

    with pytest.raises(TetherPolicyError, match="revocation tombstone"):
        validate_tether_reconciliation(previous, candidate)
