"""Explicit host-operator retrieval of the dedicated local HTTP credential."""

from __future__ import annotations

import os
from dataclasses import dataclass

from pydantic import SecretStr

from lychd.config.settings.root import get_settings
from lychd.config.settings.server import validate_local_access_password
from lychd.system.host_tools import trusted_host_tool
from lychd.system.services.secrets import PodmanSecretStore, PodmanSecretStoreError


@dataclass(frozen=True)
class LocalAccess:
    """Configured loopback address and deliberately masked operator credential."""

    url: str
    password: SecretStr
    username: str = "magus"


def load_local_access() -> LocalAccess:
    """Read only the named local credential, without starting application services."""
    if os.geteuid() == 0:
        msg = "Local access belongs to the rootless operator; rerun as your ordinary user."
        raise ValueError(msg)
    settings = get_settings()
    password = settings.server.web.access_password
    if password is None:
        podman = trusted_host_tool("podman")
        if podman is None:
            msg = "A trusted Podman executable is required to read the local access credential."
            raise ValueError(msg)
        try:
            password = PodmanSecretStore(podman).read(settings.server.web.access_password_secret)
        except PodmanSecretStoreError:
            msg = "The local access credential is unavailable; bind the installation before opening the Altar."
            raise ValueError(msg) from None
    return LocalAccess(
        url=f"http://127.0.0.1:{settings.server.port}/",
        password=validate_local_access_password(password),
    )
