"""Pure generation and revocation fencing for Tether public intent."""

from __future__ import annotations

from lychd.domain.tether.models import TetherIntent, TetherPeerState

__all__ = ["TetherPolicyError", "validate_tether_reconciliation"]


class TetherPolicyError(ValueError):
    """Raised when a candidate generation would revive or rewind peer authority."""


def validate_tether_reconciliation(previous: TetherIntent, candidate: TetherIntent) -> None:
    """Require forward public intent and forbid implicit revival of revoked peers."""
    if candidate.revision <= previous.revision:
        msg = "Tether reconciliation requires a strictly newer intent revision."
        raise TetherPolicyError(msg)
    candidate_peers = {peer.peer_id: peer for peer in candidate.peers}
    for previous_peer in previous.peers:
        current = candidate_peers.get(previous_peer.peer_id)
        if current is None:
            msg = (
                f"Tether peer {previous_peer.peer_id!r} must remain as explicit public intent; "
                "removal requires a retained revocation tombstone."
            )
            raise TetherPolicyError(msg)
        if current.revision < previous_peer.revision:
            msg = f"Tether peer {previous_peer.peer_id!r} revision cannot move backward."
            raise TetherPolicyError(msg)
        if previous_peer.state is TetherPeerState.REVOKED and current.state is not TetherPeerState.REVOKED:
            msg = f"Tether peer {previous_peer.peer_id!r} cannot be revived by reconciliation."
            raise TetherPolicyError(msg)
        if current != previous_peer and current.revision <= previous_peer.revision:
            msg = f"Tether peer {previous_peer.peer_id!r} changes require a newer peer revision."
            raise TetherPolicyError(msg)
