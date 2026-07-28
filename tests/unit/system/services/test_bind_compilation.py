"""Single-snapshot contracts for pure bind request compilation."""

import pytest

from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import Settings, get_settings
from lychd.config.settings.server import ServerSettings
from lychd.domain.animation.conflicts import ConflictTopologyError
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.extensions.host import assemble_extensions
from lychd.system.constants import CONTAINER_LYCHD_PORT
from lychd.system.schemas import QuadletPod
from lychd.system.services.bind_compilation import compile_bind_request


def test_compile_uses_only_its_injected_settings_snapshot() -> None:
    """Quadlets, units, and core secrets derive from the same explicit Settings."""
    global_port = get_settings().server.port
    injected_port = global_port + 1000
    settings = Settings(server=ServerSettings(port=injected_port))

    request = compile_bind_request(
        settings=settings,
        extensions=assemble_extensions(settings),
        runes=RuneRegistry(()),
        soulstones=(),
        portals=(),
        uncaged=False,
    )

    pod = next(manifest for manifest in request.manifests if isinstance(manifest, QuadletPod))
    assert f"127.0.0.1:{injected_port}:{CONTAINER_LYCHD_PORT}" in pod.publish_ports
    assert f"127.0.0.1:{global_port}:{CONTAINER_LYCHD_PORT}" not in pod.publish_ports
    assert tuple(secret.name for secret in request.core_secrets) == tuple(
        sorted(
            (
                settings.server.database.password_secret,
                settings.server.web.secret_key_secret,
            )
        )
    )


def test_bind_rejects_a_soulstone_without_an_advertised_capability() -> None:
    """An unadvertised local service cannot enter capability-derived runtime truth."""
    settings = get_settings()
    stone = GenericSoulstoneConfig(
        name="crawler-sidecar",
        image="example/crawler:latest",
        runtime="crawler",
    )

    with pytest.raises(
        ConflictTopologyError,
        match=r"at least one capability.*crawler-sidecar",
    ):
        compile_bind_request(
            settings=settings,
            extensions=assemble_extensions(settings),
            runes=RuneRegistry(()),
            soulstones=(stone,),
            portals=(),
            uncaged=False,
        )
