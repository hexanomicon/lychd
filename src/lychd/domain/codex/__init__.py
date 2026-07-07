"""The Codex floor: identity (Sigil), scope grammar, consent, preauthorization.

Import law: `domain/codex` imports `db.models` + config ONLY. `agents` and
`interface/web` import codex; `domain/cortex` MUST NOT (the engine sees consent
only through the ledger port's string ids).
"""

from __future__ import annotations

from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.ledger import CodexConsentLedger, ConsentLedger, InMemoryConsentLedger
from lychd.domain.codex.middleware import SigilAuthMiddleware, sigil_auth_middleware
from lychd.domain.codex.runes import CodexPreauthRune, CodexRune
from lychd.domain.codex.schemas import (
    ConsentDecision,
    ConsentStatusValue,
    ConsentView,
    censor,
    constraints_admit,
)
from lychd.domain.codex.scopes import scopes_satisfied
from lychd.domain.codex.sigil import Sigil

__all__ = [
    "CodexConsentLedger",
    "CodexPreauthRune",
    "CodexRune",
    "ConsentDecision",
    "ConsentLedger",
    "ConsentStatusValue",
    "ConsentView",
    "InMemoryConsentLedger",
    "Sigil",
    "SigilAuthMiddleware",
    "censor",
    "constraints_admit",
    "requires_scopes",
    "scopes_satisfied",
    "sigil_auth_middleware",
]
