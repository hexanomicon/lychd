"""`lych bind` file-set parity net (brief §8.2 Quadlet writer split, P4).

Proves the Scribe writes exactly the expected unit files into their two binding
sites -- ``.container``/``.pod`` into the Quadlet dir, ``.target`` into the
systemd user dir -- for BOTH transmutation scenarios. The expected file sets are
committed fixtures captured PRE-refactor (P1), so the QuadletContributor refactor
cannot silently add, drop, or misroute a unit file.

Regenerate with ``LYCHD_REGEN_GOLDEN=1`` after an INTENTIONAL change.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.system.services.scribe import ScribeService

if TYPE_CHECKING:
    from lychd.system.schemas import QuadletBase

GOLDEN_DIR = Path(__file__).parents[2] / "fixtures" / "golden" / "quadlets"
_REGEN = os.getenv("LYCHD_REGEN_GOLDEN") == "1"


def _transmute(*, phoenix_active: bool) -> list[QuadletBase]:
    from lychd.config.runes.registry import RuneRegistry
    from lychd.domain.animation.schemas import ConcurrencyIntent, GenericSoulstoneConfig
    from lychd.extensions.builtin.observability.phoenix.config import PhoenixSettings
    from lychd.extensions.builtin.observability.phoenix.contributor import PhoenixQuadletContributor

    # Mirror the golden fixture stone set so the two nets pin the same reality.
    soulstones = [
        GenericSoulstoneConfig(name="alpha", image="registry.example/alpha:1", groups=["logic"]),
        GenericSoulstoneConfig(name="beta", image="registry.example/beta:1", groups=["logic"]),
        GenericSoulstoneConfig(name="gamma", image="registry.example/gamma:1", groups=[]),
        GenericSoulstoneConfig(
            name="resident",
            image="registry.example/resident:1",
            groups=[],
            concurrency=ConcurrencyIntent(dedicated=False, persistent_resident=True),
        ),
    ]
    transmuter = Transmuter(
        runtime_planner=RuntimeAdapterRegistry(),
        contributors=[PhoenixQuadletContributor()],
    )
    runes = RuneRegistry([PhoenixSettings()] if phoenix_active else [])
    return transmuter.transmute_all(soulstones, runes=runes)


def _write_and_collect(manifests: list[QuadletBase], tmp_path: Path) -> dict[str, list[str]]:
    quadlet_dir = tmp_path / "containers"
    systemd_dir = tmp_path / "systemd"
    scribe = ScribeService(output_dir=quadlet_dir, systemd_dir=systemd_dir)
    scribe.generate_all(manifests)
    return {
        "quadlet": sorted(p.name for p in quadlet_dir.iterdir() if p.is_file() and not p.name.startswith(".")),
        "systemd": sorted(p.name for p in systemd_dir.iterdir() if p.is_file() and not p.name.startswith(".")),
    }


def _fileset_path() -> Path:
    return GOLDEN_DIR / "bind_fileset.json"


@pytest.mark.parametrize("scenario", ["phoenix_active", "phoenix_absent"])
def test_bind_fileset_parity(scenario: str, tmp_path: Path) -> None:
    manifests = _transmute(phoenix_active=(scenario == "phoenix_active"))
    actual = _write_and_collect(manifests, tmp_path)

    path = _fileset_path()
    existing: dict[str, dict[str, list[str]]] = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    if _REGEN:
        existing[scenario] = actual
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert scenario in existing, f"Missing bind file-set golden for '{scenario}'; regen with LYCHD_REGEN_GOLDEN=1."
    assert actual == existing[scenario]


def test_target_split_routing(tmp_path: Path) -> None:
    """§8.2 — .target files land in the systemd dir, containers/pods in the Quadlet dir."""
    manifests = _transmute(phoenix_active=True)
    result = _write_and_collect(manifests, tmp_path)
    assert "lychd.pod" in result["quadlet"]
    assert "lychd-oculus.container" in result["quadlet"]
    assert all(name.endswith((".container", ".pod")) for name in result["quadlet"])
    assert result["systemd"] == ["lychd-coven-logic.target"]
