from __future__ import annotations

import pytest

from lychd.domain.web.swap_requests import InMemorySwapRequestLedger


@pytest.mark.asyncio
async def test_in_memory_admission_preserves_the_first_target_without_expiry() -> None:
    ledger = InMemorySwapRequestLedger()

    first = await ledger.claim(request_id="request-1", target="chat:first")
    repeat = await ledger.claim(request_id="request-1", target="chat:first")
    conflict = await ledger.claim(request_id="request-1", target="chat:second")

    assert first.created is True
    assert repeat.created is False
    assert conflict.created is False
    assert conflict.target == "chat:first"
