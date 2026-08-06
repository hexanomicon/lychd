from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from ipaddress import ip_interface, ip_network

import pytest
from pydantic import ValidationError

from lychd.domain.tether.models import (
    TetherIntent,
    TetherInterfaceIntent,
    TetherPeerIntent,
    TetherPeerState,
)

PUBLIC_KEY_ONE = base64.b64encode(bytes(range(32))).decode()
PUBLIC_KEY_TWO = base64.b64encode(bytes(range(1, 33))).decode()


def _interface(*, peer_limit: int = 4) -> TetherInterfaceIntent:
    return TetherInterfaceIntent(
        addresses=(ip_interface("10.44.0.1/24"), ip_interface("fd44::1/64")),
        listen_port=51820,
        private_key_secret_name="tether_private_key",  # noqa: S106 - secret name, not value
        peer_limit=peer_limit,
    )


def _peer(
    peer_id: str,
    public_key: str,
    route: str,
    *,
    state: TetherPeerState = TetherPeerState.ENABLED,
) -> TetherPeerIntent:
    return TetherPeerIntent(
        peer_id=peer_id,
        revision=1,
        public_key=public_key,
        preshared_key_secret_name=f"tether_{peer_id}_psk",
        allowed_routes=(ip_network(route),),
        endpoint="vpn.example.test:51820",
        persistent_keepalive_seconds=25,
        state=state,
        revoked_at=datetime.now(UTC) if state is TetherPeerState.REVOKED else None,
    )


def test_tether_intent_is_secret_reference_only_and_json_serializable() -> None:
    intent = TetherIntent(
        revision=1,
        interface=_interface(),
        peers=(_peer("phone", PUBLIC_KEY_ONE, "10.44.0.2/32"),),
    )

    payload = intent.model_dump_json()
    decoded = json.loads(payload)

    assert "tether_private_key" in payload
    assert "tether_phone_psk" in payload
    assert "private_key" not in decoded["interface"]
    assert "preshared_key" not in decoded["peers"][0]


def test_tether_rejects_duplicate_keys_and_overlapping_active_routes() -> None:
    first = _peer("one", PUBLIC_KEY_ONE, "10.44.0.0/25")
    with pytest.raises(ValidationError, match="public keys must be unique"):
        TetherIntent(
            revision=1,
            interface=_interface(),
            peers=(first, _peer("two", PUBLIC_KEY_ONE, "10.44.0.128/25")),
        )
    with pytest.raises(ValidationError, match="overlaps"):
        TetherIntent(
            revision=1,
            interface=_interface(),
            peers=(first, _peer("two", PUBLIC_KEY_TWO, "10.44.0.64/26")),
        )


def test_revoked_routes_do_not_claim_live_address_space() -> None:
    intent = TetherIntent(
        revision=1,
        interface=_interface(),
        peers=(
            _peer("old", PUBLIC_KEY_ONE, "10.44.0.0/25", state=TetherPeerState.REVOKED),
            _peer("new", PUBLIC_KEY_TWO, "10.44.0.64/26"),
        ),
    )

    assert intent.peers[0].state is TetherPeerState.REVOKED


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://vpn.example.test:51820",
        "user@vpn.example.test:51820",
        "2001:db8::1:51820",
        "vpn.example.test:0",
        "vpn.example.test:not-a-port",
    ],
)
def test_tether_endpoint_grammar_is_bounded(endpoint: str) -> None:
    with pytest.raises(ValidationError):
        TetherPeerIntent(
            peer_id="phone",
            revision=1,
            public_key=PUBLIC_KEY_ONE,
            allowed_routes=(ip_network("10.44.0.2/32"),),
            endpoint=endpoint,
        )


def test_private_key_values_and_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        TetherInterfaceIntent.model_validate(
            {
                "addresses": ("10.44.0.1/24",),
                "listen_port": 51820,
                "private_key_secret_name": "tether_private_key",
                "private_key": "raw-private-key",
            }
        )
