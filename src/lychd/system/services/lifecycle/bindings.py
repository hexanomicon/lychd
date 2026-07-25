"""Lifecycle planning and cleanup for exact Scribe-owned bindings."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from lychd.system.services.lifecycle.models import (
    LifecycleAction,
    LifecycleDisposition,
    LifecycleError,
    LifecyclePlan,
    LifecycleResourceKind,
)

if TYPE_CHECKING:
    from lychd.system.services.scribe import OwnedBindings, ScribeService


class BindingLifecycleService:
    """Plan and remove exact Scribe-owned bindings while the units are inert."""

    def __init__(self, scribe: ScribeService, *, systemctl_bin: str | None = None) -> None:
        """Bind lifecycle inspection to one Scribe and optional systemctl path."""
        self._scribe = scribe
        self._systemctl = systemctl_bin if systemctl_bin is not None else shutil.which("systemctl")
        self._planned = False
        self._planned_generation: str | None = None
        self._planned_receipt_present = False

    def plan_destroy(self) -> LifecyclePlan:
        """Inspect exact binding sources and require every runtime unit inert."""
        owned = self._scribe.inspect_owned_bindings()
        self._planned = True
        self._planned_generation = owned.generation
        self._planned_receipt_present = owned.receipt_present
        return self._plan_owned(owned)

    def _plan_owned(self, owned: OwnedBindings) -> LifecyclePlan:
        """Build one plan from an immutable Scribe ownership snapshot."""
        if not owned.receipt_present:
            return LifecyclePlan()
        actions: list[LifecycleAction] = []
        for path in (*owned.quadlet_sources, *owned.systemd_sources):
            disposition = (
                LifecycleDisposition.WOULD_REMOVE
                if os.path.lexists(path)
                else LifecycleDisposition.PRESERVE
            )
            detail = (
                "exact source recorded by the Scribe ownership receipt"
                if disposition is LifecycleDisposition.WOULD_REMOVE
                else "owned binding source is already absent"
            )
            actions.append(
                LifecycleAction(
                    disposition,
                    LifecycleResourceKind.FILE,
                    str(path),
                    detail,
                )
            )

        if self._systemctl is None:
            actions.append(
                LifecycleAction(
                    LifecycleDisposition.BLOCKED,
                    LifecycleResourceKind.UNIT,
                    "systemctl --user",
                    "cannot verify that recorded runtime units are inactive",
                )
            )
        else:
            actions.extend(self._unit_actions(owned))

        actions.append(
            LifecycleAction(
                LifecycleDisposition.WOULD_REMOVE,
                LifecycleResourceKind.RECEIPT,
                str(self._scribe.ownership_path),
                "remove empty Scribe authority after daemon reload",
            )
        )
        return LifecyclePlan.combine(LifecyclePlan(actions=tuple(actions)))

    def destroy(self) -> None:
        """Remove exact inert binding sources and reload the user manager once."""
        owned = self._scribe.inspect_owned_bindings()
        if self._planned and (
            owned.receipt_present != self._planned_receipt_present
            or owned.generation != self._planned_generation
        ):
            msg = "Scribe ownership changed after destruction was planned; rerun destroy."
            raise LifecycleError(msg)
        plan = self._plan_owned(owned)
        plan.require_executable()
        if not owned.receipt_present:
            return
        self._scribe.clear_owned_bindings(expected_generation=owned.generation)
        if self._systemctl is None:
            msg = "systemctl disappeared before binding destruction."
            raise LifecycleError(msg)
        try:
            subprocess.run([self._systemctl, "--user", "daemon-reload"], check=True)  # noqa: S603
        except (OSError, subprocess.CalledProcessError) as exc:
            msg = "Owned binding sources were removed, but systemd daemon-reload failed; rerun destroy."
            raise LifecycleError(msg) from exc
        self._scribe.remove_empty_ownership_receipt()

    def _unit_actions(self, owned: OwnedBindings) -> list[LifecycleAction]:
        """Return inert/enabled blockers for exact receipt-derived runtime units."""
        if self._systemctl is None:
            return []
        actions: list[LifecycleAction] = []
        for unit in owned.runtime_units:
            active = subprocess.run(  # noqa: S603
                [self._systemctl, "--user", "is-active", "--quiet", unit],
                check=False,
                capture_output=True,
            )
            if active.returncode == 0:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.BLOCKED,
                        LifecycleResourceKind.UNIT,
                        unit,
                        "unit is active; stop it before destroy",
                    )
                )
                continue
            if active.returncode not in {3, 4}:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.BLOCKED,
                        LifecycleResourceKind.UNIT,
                        unit,
                        f"systemd activity check failed with exit {active.returncode}",
                    )
                )
                continue
            enabled = subprocess.run(  # noqa: S603
                [self._systemctl, "--user", "is-enabled", "--quiet", unit],
                check=False,
                capture_output=True,
            )
            if enabled.returncode == 0:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.BLOCKED,
                        LifecycleResourceKind.UNIT,
                        unit,
                        "unit is enabled; disable it before destroy",
                    )
                )
                continue
            if enabled.returncode != 1:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.BLOCKED,
                        LifecycleResourceKind.UNIT,
                        unit,
                        f"systemd enablement check failed with exit {enabled.returncode}",
                    )
                )
                continue
            actions.append(
                LifecycleAction(
                    LifecycleDisposition.PRESERVE,
                    LifecycleResourceKind.UNIT,
                    unit,
                    "runtime unit is inactive and disabled",
                )
            )
        return actions
