from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from lychd.system.operator import composition
from lychd.system.operator.inventory import OperatorPaths
from lychd.system.operator.models import OperatorAction, VesselAuthority
from tests.unit.system.operator.test_active_stop import _World  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_composition_is_lazy_until_an_active_native_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    world = _World()
    paths = OperatorPaths(
        *(
            tmp_path / name
            for name in ("codex", "config", "receipt", "runes", "quadlet", "units", "storage", "snapshots")
        )
    )

    def trusted_tool(name: str) -> str:
        return f"/trusted/{name}"

    def inventory(**_kwargs: Any) -> _World:
        return world

    monkeypatch.setattr(composition, "trusted_host_tool", trusted_tool)
    monkeypatch.setattr(composition, "OperatorInventoryService", inventory)
    monkeypatch.setattr("lychd.system.services.lifecycle.lock.LifecycleLock", world.lock)
    original_import = builtins.__import__

    def bootstrap_import(name: str, *args: Any, **kwargs: Any) -> Any:
        assert name not in {
            "lychd.app",
            "lychd.system.operator.admission_client",
            "lychd.system.operator.stop_evidence",
        }
        assert not name.startswith("dbus_fast")
        return original_import(name, *args, **kwargs)

    with monkeypatch.context() as bootstrap:
        bootstrap.setattr(builtins, "__import__", bootstrap_import)
        services = composition.build_operator_services(runner=world, paths=paths)
    assert not world.admissions
    assert not world.reference_events
    assert not world.calls

    class AdmissionClient:
        def admit(self, generation: str) -> None:
            world.admit(generation)

    monkeypatch.setattr("lychd.system.operator.admission_client.StopAdmissionClient", AdmissionClient)
    monkeypatch.setattr("lychd.system.operator.stop_evidence.hold_native_exit", world.reference)

    result = services.control.execute(OperatorAction.STOP)

    assert result.authority is VesselAuthority.VESSEL
    assert world.admissions == ["a" * 64]
    assert world.reference_events == ["acquired", "released"]
    assert world.stops == [("lychd-uncaged-vessel.service",), ("lychd-qwen.service", "lychd-phylactery.service")]
    assert not world.locked
