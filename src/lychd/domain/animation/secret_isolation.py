"""Pure credential-name admission shared by Rune hydration and transmutation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig

__all__ = ["validate_secret_declarations"]


def validate_secret_declarations(
    *,
    core_secret_names: tuple[str, ...],
    soulstones: Sequence[SoulstoneConfig],
    portals: Sequence[PortalConfig],
) -> tuple[frozenset[str], dict[str, int]]:
    """Reject declaration aliases and return privileged names plus control-owner indices.

    Runtime planners may mount only their own Soulstone's control documents;
    transmutation checks those later contributions against the returned scopes.
    Declaration data secrets cannot alias any control document, regardless of
    Rune ordering. No secret values or host state enter this policy.
    """
    if len(set(core_secret_names)) != len(core_secret_names):
        msg = "Core credentials must use distinct names"
        raise ValueError(msg)
    portal_secrets = {portal.api_key_secret_name for portal in portals if portal.api_key_secret_name is not None}
    core_aliases = sorted(portal_secrets.intersection(core_secret_names))
    if core_aliases:
        msg = f"Portal API secret(s) {', '.join(core_aliases)} cannot alias core application or database secrets"
        raise ValueError(msg)
    privileged = frozenset((*core_secret_names, *portal_secrets))

    control_plane_owners: dict[str, int] = {}
    for stone_index, stone in enumerate(soulstones):
        for secret_name in stone.control_plane_secret_names:
            previous = control_plane_owners.get(secret_name)
            if previous is not None:
                msg = (
                    f"Soulstones '{soulstones[previous].name}' and '{stone.name}' cannot share "
                    f"control-plane secret '{secret_name}'"
                )
                raise ValueError(msg)
            control_plane_owners[secret_name] = stone_index

    for stone in soulstones:
        rune_secrets = {*stone.secret_env_files.values(), *stone.control_plane_secret_names}
        aliases = sorted(rune_secrets.intersection(privileged))
        if aliases:
            msg = (
                f"Soulstone '{stone.name}' secret(s) {', '.join(aliases)} must be distinct from core and Portal secrets"
            )
            raise ValueError(msg)
        control_aliases = sorted(set(stone.secret_env_files.values()).intersection(control_plane_owners))
        if control_aliases:
            msg = (
                f"Soulstone '{stone.name}' data-plane secret(s) {', '.join(control_aliases)} cannot alias "
                "a Soulstone control-plane secret"
            )
            raise ValueError(msg)

    return privileged, control_plane_owners
