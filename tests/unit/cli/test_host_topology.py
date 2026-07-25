from __future__ import annotations

from pathlib import Path

import pytest

from lychd.cli.host_topology import HostTier, HostTopology
from lychd.system.services import lifecycle


def test_topology_uses_the_planners_patchable_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_root = tmp_path / "config" / "lychd"
    data_root = tmp_path / "share" / "lychd"
    cache_root = tmp_path / "cache" / "lychd"
    quadlets = tmp_path / "config" / "containers" / "systemd"
    user_units = tmp_path / "config" / "systemd" / "user"
    monkeypatch.setattr(lifecycle, "PATH_CODEX_ROOT", config_root)
    monkeypatch.setattr(lifecycle, "PATH_CRYPT_ROOT", data_root)
    monkeypatch.setattr(lifecycle, "PATH_CACHE_ROOT", cache_root)
    monkeypatch.setattr(lifecycle, "PATH_SYSTEMD_UNITS_DIR", quadlets)
    monkeypatch.setattr(lifecycle, "PATH_SYSTEMD_USER_UNITS_DIR", user_units)

    topology = HostTopology.current()

    assert topology.root(HostTier.CODEX) == config_root.parent
    assert topology.root(HostTier.CRYPT) == data_root.parent
    assert topology.root(HostTier.FORGE) == cache_root.parent
    assert topology.tier_for(data_root / "postgres") is HostTier.CRYPT
    assert topology.tier_for(tmp_path / "elsewhere") is HostTier.HOST
    assert topology.shared_anchors == frozenset(
        {
            config_root.parent,
            data_root.parent,
            cache_root.parent,
            quadlets.parent,
            quadlets,
            user_units.parent,
            user_units,
        }
    )
    assert topology.routine_anchors == frozenset(
        {
            quadlets.parent,
            user_units.parent,
        }
    )
