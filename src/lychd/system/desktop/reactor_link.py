"""Private inference route between a container's loopback and registered desktop Animators."""

from __future__ import annotations

import asyncio
import os
import re
import ssl
import stat
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from functools import partial
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lychd.config.settings.orchestration import SwitchingSettings

from pydantic import BaseModel, ConfigDict, Field

from lychd.system.services.native_socket_relay import relay_stream

GUEST_ROOT = Path("/run/lychd/desktop-reactor")
SERVER_NAME = "reactor.lychd.local"
LINK_PORT = 17134
_HOST_ALIASES = frozenset({"host.docker.internal", "host.containers.internal"})
_MAX_STREAMS = 128
_SESSION_HEX_LENGTH = 64


class ReactorProjection(BaseModel):
    """Host-generated facts shared read-only with a single Vessel installation."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    binding_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    generation: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    profile_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ports: dict[str, int]

    @property
    def link_id(self) -> str:
        return f"{self.generation}/{self.profile_digest}"


def read_guest_projection() -> ReactorProjection:
    return ReactorProjection.model_validate_json((GUEST_ROOT / "projection.json").read_bytes())


def guest_host() -> str | None:
    """Only the opt-in Linux Vessel overlay sets this provider alias."""
    host = os.environ.get("LYCHD_DESKTOP_REACTOR_HOST")
    if host is not None and host not in _HOST_ALIASES:
        msg = "Desktop Reactor host must be the Docker or Podman host alias."
        raise ValueError(msg)
    return host


def verify_guest_mounts(inbox: Path, journal: Path) -> None:
    """Require three distinct mount roots and the kernel's read-only flag on both host publications."""
    from lychd.system.path_safety import path_has_symlink_component
    from lychd.system.services.lifecycle.mount_identity import mount_id_for_fd

    ids: set[int] = set()
    sources: set[tuple[int, int]] = set()
    for directory, readonly in ((inbox, False), (journal, True), (GUEST_ROOT, True)):
        if path_has_symlink_component(directory) is not None:
            msg = f"Redirected desktop Reactor mount: {directory}"
            raise ValueError(msg)
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            parent = os.open(directory.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                mount = mount_id_for_fd(fd)
                if mount in ids or mount == mount_id_for_fd(parent):
                    msg = f"Missing dedicated desktop Reactor mount: {directory}"
                    raise ValueError(msg)
                identity = os.fstat(fd)
                source = (identity.st_dev, identity.st_ino)
                if source in sources:
                    message = "Reactor mount roots alias each other."
                    raise ValueError(message)
                ids.add(mount)
                sources.add(source)
            finally:
                os.close(parent)
            if bool(os.fstatvfs(fd).f_flag & os.ST_RDONLY) != readonly:
                msg = f"Incorrect write access on desktop Reactor mount: {directory}"
                raise ValueError(msg)
        finally:
            os.close(fd)
    verify_disjoint_mount_roots(ids, Path("/proc/self/mountinfo").read_bytes())


def verify_disjoint_mount_roots(ids: set[int], mountinfo: bytes) -> None:
    """Require each directory to originate from an independent area in Linux mountinfo."""
    roots: dict[int, tuple[bytes, PurePosixPath]] = {}
    for line in mountinfo.splitlines():
        mount_id, _, device, root, _ = line.split(b" ", 4)
        if (number := int(mount_id)) in ids:
            # Linux escapes whitespace and backslashes within each field. Literal
            # slashes retain their meaning as pathname component separators.
            roots[number] = (device, PurePosixPath(os.fsdecode(root)))
    if roots.keys() != ids:
        message = "Cannot identify the source of each desktop Reactor mount."
        raise ValueError(message)
    for number, (device, path) in roots.items():
        if any(
            other != number and fs == device and path.is_relative_to(parent) for other, (fs, parent) in roots.items()
        ):
            message = "Desktop Reactor mount sources overlap."
            raise ValueError(message)


def mailbox_session(inbox: Path, journal: Path) -> str:
    """Bind this pair of mounted directories to the authenticated live consumer."""

    def read_marker(directory: Path) -> bytes:
        fd = os.open(directory / ".host-session", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            if stat.S_ISREG(os.fstat(fd).st_mode):
                marker = os.read(fd, _SESSION_HEX_LENGTH + 1)
                if re.fullmatch(rb"[0-9a-f]{64}", marker):
                    return marker
            message = "Desktop Reactor mailbox has no live host identity."
            raise ValueError(message)
        finally:
            os.close(fd)

    identity = read_marker(journal)
    if read_marker(inbox) != identity:
        message = "Desktop Reactor inbox and journal belong to different sessions."
        raise ValueError(message)
    return identity.decode("ascii")


async def verify_guest_link(host: str, projection: ReactorProjection, credentials: Path, *, session: str) -> None:
    """Prove that the authenticated host has this binding generation before requesting a switch."""
    if host not in _HOST_ALIASES:
        msg = "Unknown desktop host alias."
        raise ValueError(msg)
    async with asyncio.timeout(5):
        reader, writer = await asyncio.open_connection(
            host, LINK_PORT, ssl=link_context(credentials, server=False), server_hostname=SERVER_NAME
        )
        try:
            writer.write(b"?\n")
            await writer.drain()
            if await reader.readline() != f"{projection.link_id} {session}\n".encode("ascii"):
                msg = "Desktop Reactor and Vessel configurations differ. Prepare a fresh projection."
                raise ValueError(msg)
        finally:
            writer.close()
            await writer.wait_closed()


def link_context(directory: Path, *, server: bool) -> ssl.SSLContext:
    """Trust only this installation's CA and require both peers to authenticate."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if server else ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=directory / "ca.pem")
    context.load_cert_chain(directory / "identity.pem", directory / "identity.key")
    return context


class _Connections:
    def __init__(self) -> None:
        self.tasks: set[asyncio.Task[None]] = set()

    def accept(
        self,
        callback: Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]],
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        if len(self.tasks) >= _MAX_STREAMS:
            writer.close()
            return

        async def connection() -> None:
            try:
                await callback(reader, writer)
            except (ValueError, OSError, TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
                pass
            finally:
                writer.close()

        task = asyncio.create_task(connection())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def close(self) -> None:
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)


@asynccontextmanager
async def expose_host_engines(
    projection: ReactorProjection, credentials: Path, *, listen: str, session: str, port: int = LINK_PORT
) -> AsyncGenerator[None]:
    """Map a mutually authenticated Animator ID to a loopback listener held by the live actuator."""
    connections = _Connections()

    async def forward(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        name = (await asyncio.wait_for(reader.readuntil(b"\n"), 5))[:-1].decode("ascii")
        if name == "?":
            writer.write(f"{projection.link_id} {session}\n".encode("ascii"))
            await writer.drain()
        else:
            generation, _, animator = name.partition(" ")
            if generation == projection.link_id and animator in projection.ports:
                await relay_stream(
                    reader, writer, lambda: asyncio.open_connection("127.0.0.1", projection.ports[animator])
                )

    try:
        async with await asyncio.start_server(
            partial(connections.accept, forward),
            listen,
            port,
            ssl=link_context(credentials, server=True),
            ssl_handshake_timeout=5,
            limit=512,
        ):
            yield
    finally:
        await connections.close()


@asynccontextmanager
async def guest_engine_routes(
    routes: dict[str, int], credentials: Path, *, host: str, generation: str, port: int = LINK_PORT
) -> AsyncGenerator[None]:
    """Reserve a local listener per registered engine and send only its fixed ID upstream."""
    if host not in _HOST_ALIASES:
        msg = "Desktop Reactor host must be the Docker or Podman host alias."
        raise ValueError(msg)
    context = link_context(credentials, server=False)
    connections = _Connections()

    async def forward(name: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        async def connect() -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
            remote, stream = await asyncio.open_connection(host, port, ssl=context, server_hostname=SERVER_NAME)
            try:
                stream.write(f"{generation} {name}\n".encode("ascii"))
                await stream.drain()
            except BaseException:
                stream.close()
                with suppress(OSError):
                    await stream.wait_closed()
                raise
            return remote, stream

        await relay_stream(reader, writer, connect)

    async with AsyncExitStack() as stack:
        stack.push_async_callback(connections.close)
        for name, local_port in routes.items():
            listener = await asyncio.start_server(
                partial(connections.accept, partial(forward, name)), "127.0.0.1", local_port
            )
            await stack.enter_async_context(listener)
        yield


@asynccontextmanager
async def desktop_guest_inference(settings: SwitchingSettings) -> AsyncGenerator[None]:
    """Install scoped model routes only for the explicitly mounted guest profile."""
    host = guest_host()
    if host is None:
        yield
        return
    if settings.actuator != "host-reactor":
        message = "The desktop guest requires host-reactor switching."
        raise ValueError(message)
    verify_guest_mounts(settings.host_reactor_dir, settings.host_reactor_journal_dir)
    projection = read_guest_projection()
    session = mailbox_session(settings.host_reactor_dir, settings.host_reactor_journal_dir)
    await verify_guest_link(host, projection, GUEST_ROOT, session=session)
    async with guest_engine_routes(projection.ports, GUEST_ROOT, host=host, generation=projection.link_id):
        yield
