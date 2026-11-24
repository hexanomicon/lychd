"""Exercise the desktop inference and file paths using real streams and distinct identities."""

from __future__ import annotations

import asyncio
import os
import ssl
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from lychd.system.desktop import reactor_link
from lychd.system.desktop.reactor_identity import create_identities
from lychd.system.services import native_socket_relay


async def echo(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        writer.write(await reader.readline())
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


def test_shared_mounts_require_disjoint_sources() -> None:
    sibling_mounts = b"41 1 0:28 /share/inbox /in rw\n42 1 0:28 /share/journal /out ro\n43 1 0:29 / /keys ro\n"
    reactor_link.verify_disjoint_mount_roots({41, 42, 43}, sibling_mounts)
    with pytest.raises(ValueError, match="overlap"):
        reactor_link.verify_disjoint_mount_roots({41, 42, 43}, sibling_mounts.replace(b"/share/inbox", b"/share"))
    with pytest.raises(ValueError, match="identify"):
        reactor_link.verify_disjoint_mount_roots({41, 42, 44}, sibling_mounts)


@pytest.mark.skipif(sys.platform != "linux", reason="the caged Vessel reads the Linux guest mounts")
def test_mailbox_session_is_bounded_and_shared(tmp_path: Path) -> None:
    inbox, journal = tmp_path / "inbox", tmp_path / "journal"
    inbox.mkdir()
    journal.mkdir()
    marker = inbox / ".host-session"
    for directory in (inbox, journal):
        (directory / ".host-session").write_bytes(b"a" * 64)
    assert reactor_link.mailbox_session(inbox, journal) == "a" * 64
    marker.write_bytes(b"b" * 64)
    with pytest.raises(ValueError, match="different sessions"):
        reactor_link.mailbox_session(inbox, journal)
    marker.unlink()
    os.mkfifo(marker)
    with pytest.raises(ValueError, match="no live host"):
        reactor_link.mailbox_session(inbox, journal)


@pytest.mark.asyncio
async def test_guest_only_reaches_its_bound_engine_and_authenticates_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unused_tcp_port_factory: Callable[[], int]
) -> None:
    root = await asyncio.to_thread(tmp_path.resolve, strict=True)
    create_identities(root)
    unrelated = root / "other-installation"
    create_identities(unrelated)
    host_port, client_port, link_port = unused_tcp_port_factory(), unused_tcp_port_factory(), unused_tcp_port_factory()
    projection = reactor_link.ReactorProjection(
        profile_digest="sha256:" + "d" * 64,
        binding_digest="sha256:" + "a" * 64,
        generation="sha256:" + "b" * 64,
        ports={"model": host_port},
    )
    # On one kernel the two sites need different loopback ports. Resolve only the
    # documented desktop alias to this test host; TLS and both listeners are real.
    monkeypatch.setattr(reactor_link, "_HOST_ALIASES", frozenset({"127.0.0.1"}))
    monkeypatch.setattr(reactor_link, "LINK_PORT", link_port)
    async with (
        await asyncio.start_server(echo, "127.0.0.1", host_port),
        reactor_link.expose_host_engines(
            projection, root / "host", listen="127.0.0.1", session="trial", port=link_port
        ),
    ):
        await reactor_link.verify_guest_link("127.0.0.1", projection, root / "vessel", session="trial")
        stale = projection.model_copy(update={"generation": "sha256:" + "c" * 64})
        with pytest.raises(ValueError, match="differ"):
            await reactor_link.verify_guest_link("127.0.0.1", stale, root / "vessel", session="trial")
        with pytest.raises(ssl.SSLError):
            await reactor_link.verify_guest_link("127.0.0.1", projection, unrelated / "vessel", session="trial")
        async with reactor_link.guest_engine_routes(
            {"model": client_port}, root / "vessel", host="127.0.0.1", generation=projection.link_id, port=link_port
        ):
            reader, writer = await asyncio.open_connection("127.0.0.1", client_port)
            writer.write(b"inference\n")
            await writer.drain()
            assert await asyncio.wait_for(reader.read(), 5) == b"inference\n"
            writer.close()
            await writer.wait_closed()


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Linux managed service uses an AF_UNIX engine socket",
)
@pytest.mark.asyncio
async def test_pod_relay_forwards_to_fixed_socket_and_handles_stopped_engine(
    monkeypatch: pytest.MonkeyPatch, unused_tcp_port: int
) -> None:
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as directory:
        endpoint = str(Path(directory) / "engine.sock")
        monkeypatch.setattr(native_socket_relay, "_ENGINE_SOCKET", endpoint)
        port = unused_tcp_port
        owner = asyncio.create_task(native_socket_relay.serve(port))
        try:
            async with asyncio.timeout(5):
                while True:
                    try:
                        reader, writer = await asyncio.open_connection("127.0.0.1", port)
                    except ConnectionRefusedError:
                        await asyncio.sleep(0.01)
                    else:
                        break
                assert await reader.read() == b""
                writer.close()
                await writer.wait_closed()
            async with await asyncio.start_unix_server(echo, endpoint):
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                writer.write(b"model\n")
                await writer.drain()
                assert await asyncio.wait_for(reader.read(), 5) == b"model\n"
                writer.close()
                await writer.wait_closed()
        finally:
            owner.cancel()
            await asyncio.gather(owner, return_exceptions=True)
