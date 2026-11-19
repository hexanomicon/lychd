"""Observe two Nexus presence owners through disposable, local paired folders."""

from __future__ import annotations

import asyncio
import secrets
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Literal

from lychd.config.settings.presence import PresencePair, PresenceSettings
from lychd.domain.intercom.presence import Availability, PresenceIntent
from lychd.system.services.colleague_presence import ColleaguePresence


def _open(stack: ExitStack, root: Path, peer: str, slot: Literal["a", "b"], key: str) -> ColleaguePresence:
    # Only the ciphertext directory is shared. Each owner has its own key copy.
    private = root / slot
    private.mkdir(mode=0o700)
    key_file = private / "pair.key"
    key_file.touch(mode=0o600)
    key_file.write_text(key)
    pair = PresencePair(name=peer, slot=slot, directory=root / "exchange", key_file=key_file)
    return stack.enter_context(ColleaguePresence.open(PresenceSettings(pairs=(pair,))))


async def _show(sender: ColleaguePresence, receiver: ColleaguePresence, choice: Availability) -> None:
    intent = PresenceIntent(audience_id=sender.board().audience_id, availability=choice)
    await sender.choose(intent, permitted=lambda: True)
    expected = "unknown" if choice == "hidden" else choice
    await _wait_for_observation(receiver, expected, seconds=12)
    row = receiver.board().peers[0]
    print(f"{row.name} chose {choice}. The other Nexus sees {row.availability}.", flush=True)  # noqa: T201


async def _wait_for_observation(
    receiver: ColleaguePresence, expected: Literal["ready", "busy", "unknown"], *, seconds: int
) -> None:
    async with asyncio.timeout(seconds):
        # A replica observation has no in-process event shared between the two services.
        while receiver.board().peers[0].availability != expected:  # noqa: ASYNC110
            await asyncio.sleep(0.1)


async def _demonstrate(alice: ColleaguePresence, bob: ColleaguePresence) -> None:
    async with asyncio.TaskGroup() as workers:
        workers.create_task(alice.maintain())
        workers.create_task(bob.maintain())
        try:
            await _show(alice, bob, "ready")
            await _show(bob, alice, "busy")
            await _show(alice, bob, "busy")
            await _show(alice, bob, "hidden")
            await bob.stop()
            print("Bob stopped reporting. Waiting for his last report to expire.", flush=True)  # noqa: T201
            await _wait_for_observation(alice, "unknown", seconds=35)
            print("Alice now sees Bob's availability as unknown.", flush=True)  # noqa: T201
        finally:
            await alice.stop()
            await bob.stop()


def main() -> None:
    """Use the normal renewal loop with two independent audiences and local choices."""
    with tempfile.TemporaryDirectory(prefix="lychd-colleagues-") as scratch, ExitStack() as stack:
        root = Path(scratch).resolve()
        (root / "exchange").mkdir(mode=0o700)
        key = secrets.token_hex(32)
        alice = _open(stack, root, "Bob", "a", key)
        bob = _open(stack, root, "Alice", "b", key)
        asyncio.run(_demonstrate(alice, bob))


if __name__ == "__main__":
    main()
