"""`requires_scopes` — a Litestar guard over the authenticated Sigil's scopes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.exceptions import PermissionDeniedException

from lychd.domain.codex.scopes import scopes_satisfied
from lychd.domain.codex.sigil import Sigil

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.connection import ASGIConnection
    from litestar.handlers.base import BaseRouteHandler

    # A Litestar guard: called with (connection, handler); raises to deny. Typed
    # concretely (litestar's own `Guard` alias is partially unknown to the checker).
    _Guard = Callable[[ASGIConnection[Any, Any, Any, Any], BaseRouteHandler], None]

__all__ = ["requires_scopes"]


def requires_scopes(*required: str) -> _Guard:
    """Build a guard requiring every named scope on the connection Sigil."""

    def guard(connection: ASGIConnection[Any, Any, Any, Any], _handler: BaseRouteHandler) -> None:
        # Reading `connection.user` raises a framework configuration error when
        # authentication middleware is absent. Missing identity is an ordinary
        # authorization denial, never a 500.
        try:
            sigil: Any = connection.scope["user"]
        except KeyError:
            sigil = None
        if not isinstance(sigil, Sigil) or not scopes_satisfied(sigil.scopes, required):
            msg = f"This sigil lacks the required scope(s): {', '.join(required)}."
            raise PermissionDeniedException(detail=msg)

    return guard
