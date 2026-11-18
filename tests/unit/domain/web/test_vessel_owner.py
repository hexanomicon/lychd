"""A duplicate or lost PostgreSQL lock must stop admission and release the session."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import pytest
from litestar import Litestar

from lychd.db.authority import DatabaseAuthorityError
from lychd.interface import vessel_owner

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.asyncio
@pytest.mark.parametrize(("unsafe", "locked"), [(True, False), (False, False), (False, True)])
async def test_database_owner_checks_authority_and_exclusivity(
    mocker: MockerFixture, *, unsafe: bool, locked: bool
) -> None:
    connection = Mock(fetchval=AsyncMock(side_effect=[unsafe, locked]), close=AsyncMock())
    mocker.patch.object(vessel_owner, "database_saq_dsn", return_value="db")
    mocker.patch.object(vessel_owner.asyncpg, "connect", new=AsyncMock(return_value=connection))
    if locked:
        async with vessel_owner.vessel_database_owner(Litestar()):
            connection.close.assert_not_called()
        connection.remove_termination_listener.assert_called_once()
    else:
        with pytest.raises(DatabaseAuthorityError if unsafe else RuntimeError):
            async with vessel_owner.vessel_database_owner(Litestar()):
                pytest.fail("A second or overprivileged Vessel entered lifespan")
    connection.close.assert_awaited_once()
    assert connection.fetchval.await_count == (1 if unsafe else 2)


@pytest.mark.asyncio
async def test_lost_database_session_cancels_vessel(mocker: MockerFixture) -> None:
    connection = Mock(fetchval=AsyncMock(side_effect=[False, True]), close=AsyncMock())
    mocker.patch.object(vessel_owner, "database_saq_dsn", return_value="db")
    mocker.patch.object(vessel_owner.asyncpg, "connect", new=AsyncMock(return_value=connection))
    admitted = asyncio.Event()

    async def serve() -> None:
        async with vessel_owner.vessel_database_owner(Litestar()):
            admitted.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(serve())
    await admitted.wait()
    callback = connection.add_termination_listener.call_args.args[0]
    callback(connection)
    with pytest.raises(asyncio.CancelledError, match="exclusive database session"):
        await task
    connection.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_native_stop_authenticates_only_the_current_generation(mocker: MockerFixture) -> None:
    connection = Mock(fetchval=AsyncMock(side_effect=[False, True]), close=AsyncMock(), add_listener=AsyncMock())
    mocker.patch.object(vessel_owner, "database_saq_dsn", return_value="db")
    mocker.patch.object(vessel_owner.asyncpg, "connect", new=AsyncMock(return_value=connection))
    mocker.patch.object(vessel_owner, "_stop_proof", return_value="proof")
    app = Litestar()
    stop = Mock()
    app.state.native_request_stop = stop
    async with vessel_owner.vessel_database_owner(app):
        handler = connection.add_listener.await_args.args[1]
        handler(connection, 1, "lychd_native_stop", "unrelated")
        handler(connection, 1, "lychd_native_stop", "Ω")
        stop.assert_not_called()
        handler(connection, 1, "lychd_native_stop", "proof")
        stop.assert_called_once_with()


@pytest.mark.asyncio
async def test_native_stop_awaits_release_of_exact_generation(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LYCHD_VESSEL_MODE", "native")
    generation = "lychd-native-first"
    connection = Mock(
        fetchval=AsyncMock(side_effect=[False, generation, generation, "lychd-native-next"]),
        execute=AsyncMock(),
        close=AsyncMock(),
    )
    mocker.patch.object(vessel_owner, "database_saq_dsn", return_value="db")
    mocker.patch.object(vessel_owner.asyncpg, "connect", new=AsyncMock(return_value=connection))
    mocker.patch.object(vessel_owner, "_stop_proof", return_value="proof")
    assert await vessel_owner.stop_native_vessel()
    connection.execute.assert_awaited_once_with("SELECT pg_notify($1, $2)", "lychd_native_stop", "proof")
    connection.close.assert_awaited_once()
