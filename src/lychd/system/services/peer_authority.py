"""One-loop current operator/object policy for the outbound peer profile.

Actual LocalOperatorAccess markers authenticate calls. Policy and peer fences
remain synchronous so revocation wins before a later socket handoff or result
admission. Durable rows and equal attribution fields never become live grants.
"""

from __future__ import annotations

import asyncio
from typing import NoReturn
from uuid import UUID

from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.peer import PeerAuthorityError, PeerObject, PeerPolicy


def _refuse(code: str) -> NoReturn:
    raise PeerAuthorityError(code) from None


class PeerAuthority:
    """A mandatory exact bootstrap policy bound to one current control loop."""

    def __init__(self, *, access: LocalOperatorAccess, policy: PeerPolicy) -> None:
        """Bind the actual credential owner and explicit bootstrap selectors."""
        if type(access) is not LocalOperatorAccess or type(policy) is not PeerPolicy:
            _refuse("configuration")
        access.bind_control_loop()
        self._access = access
        self._policy = policy
        self._loop = asyncio.get_running_loop()
        self._fenced: set[UUID] = set()
        self._uncertain: set[UUID] = set()
        self._retired_keys: set[tuple[UUID, int]] = set()

    @property
    def policy(self) -> PeerPolicy:
        return self._policy

    def check_authentication(self, authentication: object) -> None:
        """Authenticate before resolving an opaque retained Run identity.

        This grants no object action. The caller must check its exact retained
        target immediately after that lookup and before returning any data.
        """
        if asyncio.get_running_loop() is not self._loop or not self._access.current(authentication):
            _refuse("authentication")

    def check(self, authentication: object, action: str, target: PeerObject) -> None:
        """Check the real marker and every explicit selector without yielding."""
        self._check(authentication, action, target, allow_fenced=False)

    def _check(
        self,
        authentication: object,
        action: str,
        target: PeerObject,
        *,
        allow_fenced: bool,
        allow_uncertain: bool = False,
    ) -> None:
        if asyncio.get_running_loop() is not self._loop:
            _refuse("control-loop")
        if not self._access.current(authentication):
            _refuse("authentication")
        policy = self._policy
        if (
            (target.peer_id in self._fenced and not allow_fenced)
            or (target.peer_id in self._uncertain and not allow_uncertain)
            or action not in policy.actions
            or target.purpose not in policy.purposes
            or target.category not in policy.categories
            or target.task_schema not in policy.task_schemas
            or target.peer_id not in policy.peers
            or target.endpoint not in policy.endpoints
        ):
            _refuse("policy")

    def check_local_evidence(self, authentication: object, target: PeerObject) -> None:
        """Authorize body-free local inspection without reopening a remote road."""
        self._check(authentication, "inspect", target, allow_fenced=True, allow_uncertain=True)

    def check_revocation_completion(self, authentication: object, target: PeerObject) -> None:
        """Recheck the actual marker and selectors without reopening the revoked peer."""
        self._check(authentication, "revoke", target, allow_fenced=True)

    def current_binding(self, subject: str, generation: UUID) -> bool:
        return self._access.current_binding(subject, generation)

    def fence(self, peer_id: UUID) -> None:
        """Fence before any persistence await; no receipt can reopen this instance."""
        if asyncio.get_running_loop() is not self._loop:
            _refuse("control-loop")
        self._fenced.add(peer_id)

    def retire_key(self, peer_id: UUID, version: int) -> None:
        """Fence old-key handoffs permanently before a rotation persistence await."""
        if asyncio.get_running_loop() is not self._loop:
            _refuse("control-loop")
        self._retired_keys.add((peer_id, version))

    def credential_current(self, peer_id: UUID, version: int) -> bool:
        return (peer_id, version) not in self._retired_keys

    def uncertain(self, peer_id: UUID) -> None:
        """Retain local refusal after an unacknowledged authority mutation."""
        self._uncertain.add(peer_id)

    def replace_policy(self, policy: PeerPolicy) -> None:
        """Narrow or change policy immediately; durable mismatch stays fail-closed."""
        if asyncio.get_running_loop() is not self._loop or policy.generation <= self._policy.generation:
            _refuse("policy-generation")
        self._policy = policy
