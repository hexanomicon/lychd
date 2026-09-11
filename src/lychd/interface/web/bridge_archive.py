"""Bounded metadata-only Bridge archive pages and validated continuation cursors."""

from __future__ import annotations

import base64
import binascii
from typing import TYPE_CHECKING

from litestar.exceptions import ValidationException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from lychd.domain.web.contracts import SessionPage, SessionSummary
from lychd.domain.web.sessions import SESSION_PAGE_SIZE

_MAX_CURSOR_LENGTH = 512

if TYPE_CHECKING:
    from lychd.domain.codex.ledger import ConsentLedger
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.web.sessions import SessionStorePort


class _SessionCursor(BaseModel):
    """Stable timestamp/id keyset, carrying no authorization or executable text."""

    model_config = ConfigDict(extra="forbid", strict=True)

    created_at: AwareDatetime
    id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


async def read_session_page(
    sessions: SessionStorePort,
    consents: ConsentLedger,
    runs: RunLedger,
    *,
    cursor: str | None = None,
) -> SessionPage:
    """Read one archive page and its grouped pending counts without history."""
    before = None
    if cursor is not None:
        if len(cursor) > _MAX_CURSOR_LENGTH:
            raise ValidationException(detail="Invalid session archive cursor.")
        try:
            decoded = _SessionCursor.model_validate_json(base64.b64decode(cursor, altchars=b"-_", validate=True))
            before = decoded.created_at, decoded.id
        except (ValueError, binascii.Error) as exc:
            raise ValidationException(detail="Invalid session archive cursor.") from exc
    records = await sessions.list_session_summaries(before=before)
    page = records[:SESSION_PAGE_SIZE]

    async def run_session_id(run_id: str) -> str | None:
        run = await runs.get(run_id)
        return run.session_id if run is not None else None

    counts = await consents.pending_counts_for_sessions(
        frozenset(item.id for item in page), run_session_id=run_session_id
    )
    next_cursor = None
    if len(records) > SESSION_PAGE_SIZE:
        last = page[-1]
        key = _SessionCursor(created_at=last.created_at, id=last.id)
        next_cursor = base64.urlsafe_b64encode(key.model_dump_json().encode()).decode("ascii")
    return SessionPage(
        sessions=[
            SessionSummary(
                id=item.id, title=item.title, created_at=item.created_at, pending_count=counts.get(item.id, 0)
            )
            for item in page
        ],
        next_cursor=next_cursor,
    )
