"""Quadlet contributor for the external Arize Phoenix Eye."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.domain.animation.transmute import QuadletContribution
from lychd.extensions.builtin.observability.phoenix.config import (
    CONTAINER_PHOENIX_OTLP_PORT,
    CONTAINER_PHOENIX_UI_PORT,
    PhoenixSettings,
)
from lychd.system.constants import CONTAINER_POSTGRES_PORT
from lychd.system.schemas import QuadletContainer

if TYPE_CHECKING:
    from lychd.domain.animation.transmute import TransmutationContext


class PhoenixQuadletContributor:
    """Contribute the Phoenix Eye container and pod ports when selected."""

    def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
        """Emit the Phoenix Eye container/ports, or an empty contribution if absent."""
        phoenix = ctx.runes.one_or_none(PhoenixSettings)  # >1 raises loudly (kept semantics)
        if phoenix is None:
            return QuadletContribution()
        database = ctx.settings.server.database
        return QuadletContribution(
            containers=(
                QuadletContainer(
                    description="External Eye (Arize Phoenix)",
                    image=phoenix.quadlet.image,
                    container_name=phoenix.service_name,
                    pod="lychd.pod",
                    env_vars={
                        "PHOENIX_PORT": str(CONTAINER_PHOENIX_UI_PORT),
                        "PHOENIX_POSTGRES_HOST": "localhost",
                        "PHOENIX_POSTGRES_PORT": str(CONTAINER_POSTGRES_PORT),
                        "PHOENIX_POSTGRES_USER": database.phoenix_user,
                        "PHOENIX_POSTGRES_DB": "phoenix",
                    },
                    secrets=[f"{database.phoenix_password_secret},type=env,target=PHOENIX_POSTGRES_PASSWORD"],
                    wants=["lychd-migrate.service"],
                    requires=["lychd-migrate.service"],
                    after=["lychd-migrate.service"],
                ),
            ),
            pod_ports=(
                f"{phoenix.ui_port}:{CONTAINER_PHOENIX_UI_PORT}",
                f"{phoenix.otlp_port}:{CONTAINER_PHOENIX_OTLP_PORT}",
            ),
        )
