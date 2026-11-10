"""Static Tether Rune, separate from native public peer generations."""

from ipaddress import IPv4Address, IPv4Interface
from pathlib import Path
from typing import ClassVar
from uuid import UUID

from pydantic import Field

from lychd.config import QuadletConfig
from lychd.config.runes import RuneConfig
from lychd.domain.tether.models import TetherEnvelope, TetherSecretReference


class TetherSettings(RuneConfig):
    """Declare one immutable service envelope; Settings owns the Altar port."""

    path_fragment: ClassVar[Path] = Path("tether")
    installation_id: UUID
    interface: str
    server_address: str
    udp_bind_address: str
    udp_port: int = Field(ge=1024, le=65535, strict=True)
    advertised_endpoint: str
    quadlet: QuadletConfig
    wireguard_secret: TetherSecretReference
    ssh_host_secret: TetherSecretReference
    ssh_port: int = Field(default=2222, ge=1024, le=65535, strict=True)

    def envelope(self, *, altar_port: int) -> TetherEnvelope:
        """Validate complete static intent against the receiving Settings snapshot."""
        return TetherEnvelope(
            installation_id=self.installation_id,
            interface=self.interface,
            server_address=IPv4Interface(self.server_address),
            udp_bind_address=IPv4Address(self.udp_bind_address),
            udp_port=self.udp_port,
            advertised_endpoint=self.advertised_endpoint,
            image=self.quadlet.image,
            wireguard_secret=self.wireguard_secret,
            ssh_host_secret=self.ssh_host_secret,
            ssh_port=self.ssh_port,
            altar_port=altar_port,
        )
