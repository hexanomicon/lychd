"""Thin CLI session over reusable bind compilation and application services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from lychd.config.settings import SettingsSnapshot
from lychd.domain.animation.services.declarations import (
    compile_animator_declarations,
)
from lychd.system.services.bind_assembly import assemble_bind_use_case
from lychd.system.services.bind_compilation import (
    compile_bind_request,
    uncaged_control_plane_secret_names,
)

if TYPE_CHECKING:
    from lychd.config.runes.registry import RuneRegistry
    from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig
    from lychd.extensions.host import AssembledExtensions
    from lychd.system.services.bind import BindPlan, BindRequest, BindUseCase
    from lychd.system.services.binding_preflight import (
        BindingPreflightReport,
        BindingPreflightService,
    )


@dataclass(frozen=True, slots=True)
class PreparedBinding:
    """Compiled request, observation, and use case exposed to Click narration."""

    request: BindRequest
    plan: BindPlan
    use_case: BindUseCase


@dataclass(frozen=True, slots=True)
class BindingCommandSession:
    """One loaded command session before host authority is refined."""

    settings_snapshot: SettingsSnapshot
    extensions: AssembledExtensions
    runes: RuneRegistry
    soulstones: tuple[SoulstoneConfig, ...]
    portals: tuple[PortalConfig, ...]
    preflight_service: BindingPreflightService
    preflight: BindingPreflightReport
    uncaged: bool

    @classmethod
    def inspect(cls, *, uncaged: bool) -> BindingCommandSession:
        """Load declared intent once and inspect prerequisites without effects."""
        from lychd.config.runes.registry import load_rune_registry
        from lychd.config.settings.root import get_settings
        from lychd.extensions.host import get_extensions
        from lychd.system.services.binding_preflight import (
            BindingPreflightService,
        )

        extensions = get_extensions()
        settings = get_settings()
        runes = load_rune_registry(extensions)
        declarations = compile_animator_declarations(
            settings=settings,
            runes=runes,
        )
        preflight_service = BindingPreflightService()
        preflight = preflight_service.inspect(
            settings,
            uncaged=uncaged,
            uncaged_control_plane_secrets=(
                uncaged_control_plane_secret_names(declarations.soulstones) if uncaged else ()
            ),
        )
        return cls(
            settings_snapshot=SettingsSnapshot.capture(settings),
            extensions=extensions,
            runes=runes,
            soulstones=declarations.soulstones,
            portals=declarations.portals,
            preflight_service=preflight_service,
            preflight=preflight,
            uncaged=uncaged,
        )

    def prepare(self) -> PreparedBinding:
        """Refine host authority and compile the complete immutable bind request."""
        settings = self.settings_snapshot.materialize()
        foundation = self.preflight.require_ready()
        request = compile_bind_request(
            settings=settings,
            extensions=self.extensions,
            runes=self.runes,
            soulstones=self.soulstones,
            portals=self.portals,
            uncaged=self.uncaged,
        )
        use_case = assemble_bind_use_case(
            foundation=foundation,
            preflight_service=self.preflight_service,
            settings_snapshot=self.settings_snapshot,
            uncaged_control_plane_secrets=(uncaged_control_plane_secret_names(self.soulstones) if self.uncaged else ()),
            uncaged=self.uncaged,
        )
        return PreparedBinding(
            request=request,
            plan=use_case.plan(request),
            use_case=use_case,
        )


__all__ = [
    "BindingCommandSession",
    "PreparedBinding",
]
