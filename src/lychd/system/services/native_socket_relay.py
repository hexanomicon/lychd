"""Expose one managed native engine's private Unix socket on the Vessel pod's loopback."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress

_MAX_PORT = 65535
_ENGINE_SOCKET = "/run/lychd-native-engine/server.sock"
StreamPair = tuple[asyncio.StreamReader, asyncio.StreamWriter]
OpenUpstream = Callable[[], Awaitable[StreamPair]]


async def _copy(source: asyncio.StreamReader, destination: asyncio.StreamWriter) -> None:
    while chunk := await source.read(64 * 1024):
        destination.write(chunk)
        await destination.drain()
    if destination.can_write_eof():
        destination.write_eof()


async def relay_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, connect: OpenUpstream) -> None:
    """Bridge one connection to its configured peer and release both streams on disconnect."""
    upstream: asyncio.StreamWriter | None = None
    try:
        peer, upstream = await asyncio.wait_for(connect(), timeout=5)
        async with asyncio.TaskGroup() as group:
            uploads = group.create_task(_copy(reader, upstream))
            try:
                await _copy(peer, writer)
            finally:
                uploads.cancel()
    except* (OSError, TimeoutError, EOFError, ValueError):
        pass
    finally:
        for stream in (upstream, writer):
            if stream is not None:
                stream.close()
                with suppress(OSError, TimeoutError):
                    await asyncio.wait_for(stream.wait_closed(), timeout=2)


async def serve(port: int) -> None:
    """Listen only inside the pod, with a fixed socket mounted by the bound unit."""
    if not 1 <= port <= _MAX_PORT:
        msg = "Invalid native engine relay port."
        raise ValueError(msg)

    async def forward(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await relay_stream(reader, writer, lambda: asyncio.open_unix_connection(_ENGINE_SOCKET))

    async with await asyncio.start_server(forward, "127.0.0.1", port) as server:
        await server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", type=int)
    asyncio.run(serve(parser.parse_args().port))
