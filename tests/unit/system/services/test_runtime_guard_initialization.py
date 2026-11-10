"""Initialization and startup agree on the guard's private directory mode."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import Mock

import pytest

from lychd.system.services.layout import LayoutService
from lychd.system.services.lifecycle._authority import LifecycleAuthority
from lychd.system.services.lifecycle.initialization import InitializationPlanner
from lychd.system.services.lifecycle.models import LifecycleAction, LifecycleDisposition, LifecycleResourceKind
from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore
from lychd.system.services.runtime_guard import FileSoftActivationGuard


def test_layout_initialization_creates_a_guard_that_startup_accepts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    guard = tmp_path / "runtime-guard"
    monkeypatch.setattr("lychd.system.services.layout.PATH_RUNTIME_GUARD_DIR", guard)
    previous_umask = os.umask(0o022)
    try:
        result = LayoutService(paths=(guard,)).initialize()
    finally:
        os.umask(previous_umask)
    assert result.directories == (guard,)
    assert stat.S_IMODE(guard.stat().st_mode) == 0o700
    FileSoftActivationGuard(guard).assert_clear()


@pytest.mark.parametrize("existing", [False, True])
def test_init_plan_requires_private_guard_without_changing_existing_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, existing: bool
) -> None:
    crypt, codex, cache = (tmp_path / name for name in ("crypt", "codex", "cache"))
    guard = crypt / "runtime-guard"
    authority = LifecycleAuthority(
        host_layout=(guard,),
        cache_root=cache,
        codex_root=codex,
        crypt_root=crypt,
        lifecycle_receipt=codex / "receipt.json",
        lychd_toml=codex / "lychd.toml",
        postgres_root=crypt / "postgres",
        postgres_data=crypt / "postgres" / "data",
        postgres_snapshots=crypt / "snapshots",
        runes=codex / "runes",
        systemd_units=tmp_path / "quadlets",
        systemd_user_units=tmp_path / "units",
    )
    monkeypatch.setattr("lychd.system.services.lifecycle.initialization.current_authority", lambda: authority)
    receipt = Mock(spec=LifecycleReceiptStore)
    receipt.path = authority.lifecycle_receipt
    receipt.exists = False
    receipt.plan_recorded_identities.return_value = ()
    receipt.plan_dedicated_root_attestation.return_value = LifecycleAction(
        LifecycleDisposition.WOULD_CREATE,
        LifecycleResourceKind.RECEIPT,
        str(authority.lifecycle_receipt),
        "absent receipt",
    )
    if existing:
        guard.mkdir(parents=True, mode=0o755)
        guard.chmod(0o755)
    plan = InitializationPlanner(reactor_directories=(), anchor_paths=(), sample_paths=(), receipt_store=receipt).plan()
    receipt.plan_recorded_identities.assert_called_once_with()
    action = next(item for item in plan.actions if item.target == str(guard))
    assert "0700" in action.detail
    assert action.disposition is (LifecycleDisposition.BLOCKED if existing else LifecycleDisposition.WOULD_CREATE)
    if existing:
        assert stat.S_IMODE(guard.stat().st_mode) == 0o755


pytestmark = pytest.mark.usefixtures("persistent_identity_observer")
