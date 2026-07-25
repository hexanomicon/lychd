"""Lifecycle planning and cleanup for exact Scribe-owned bindings."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator.process import (
    ProcessInvocationError,
    ProcessResult,
    ProcessRunner,
    SubprocessRunner,
)
from lychd.system.services.lifecycle.models import (
    LifecycleAction,
    LifecycleDisposition,
    LifecycleError,
    LifecyclePlan,
    LifecycleResourceKind,
)

if TYPE_CHECKING:
    from lychd.system.services.scribe import OwnedBindings, ScribeService

_SYSTEMCTL_PROBE_TIMEOUT_SECONDS = 3.0
_SYSTEMCTL_RELOAD_TIMEOUT_SECONDS = 30.0
_SYSTEMCTL_NOT_FOUND_EXIT = 4


class BindingLifecycleService:
    """Plan and remove exact Scribe-owned bindings while the units are inert."""

    def __init__(
        self,
        scribe: ScribeService,
        *,
        runner: ProcessRunner | None = None,
        systemctl_bin: str | None = None,
    ) -> None:
        """Bind lifecycle inspection to one Scribe and bounded process port."""
        self._scribe = scribe
        self._runner = runner or SubprocessRunner()
        self._systemctl = systemctl_bin if systemctl_bin is not None else trusted_host_tool("systemctl")
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
            disposition = LifecycleDisposition.WOULD_REMOVE if os.path.lexists(path) else LifecycleDisposition.PRESERVE
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
            owned.receipt_present != self._planned_receipt_present or owned.generation != self._planned_generation
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
            reload_result = self._runner.run(
                (self._systemctl, "--user", "daemon-reload"),
                timeout_s=_SYSTEMCTL_RELOAD_TIMEOUT_SECONDS,
            )
        except ProcessInvocationError as exc:
            msg = "Owned binding sources were removed, but systemd daemon-reload failed; rerun destroy."
            raise LifecycleError(msg) from exc
        if reload_result.returncode != 0:
            detail = reload_result.stderr.strip() or f"exit {reload_result.returncode}"
            msg = f"Owned binding sources were removed, but systemd daemon-reload failed ({detail}); rerun destroy."
            raise LifecycleError(msg)

        post_reload = self._scribe.inspect_owned_bindings()
        if (
            not post_reload.receipt_present
            or post_reload.quadlet_sources != owned.quadlet_sources
            or post_reload.systemd_sources != owned.systemd_sources
            or post_reload.runtime_units != owned.runtime_units
        ):
            msg = "Scribe authority changed during daemon reload; deletion must remain blocked."
            raise LifecycleError(msg)
        if post_reload.generation is None:
            msg = "Scribe authority lost its generation during daemon reload."
            raise LifecycleError(msg)
        LifecyclePlan(actions=tuple(self._post_reload_unit_actions(post_reload))).require_executable()
        self._scribe.release_owned_binding_authority(
            expected_generation=post_reload.generation,
        )

    def _unit_actions(self, owned: OwnedBindings) -> list[LifecycleAction]:
        """Return inert/enabled blockers for exact receipt-derived runtime units."""
        if self._systemctl is None:
            return []
        actions: list[LifecycleAction] = []
        for unit in owned.runtime_units:
            active_result = self._run_systemctl("is-active", "--quiet", unit)
            if active_result is None:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.BLOCKED,
                        LifecycleResourceKind.UNIT,
                        unit,
                        "systemd activity check could not be executed",
                    )
                )
                continue
            active = active_result.returncode
            if active == 0:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.BLOCKED,
                        LifecycleResourceKind.UNIT,
                        unit,
                        "unit is active; stop it before destroy",
                    )
                )
                continue
            if active not in {3, _SYSTEMCTL_NOT_FOUND_EXIT}:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.BLOCKED,
                        LifecycleResourceKind.UNIT,
                        unit,
                        f"systemd activity check failed with exit {active}",
                    )
                )
                continue
            enabled_result = self._run_systemctl("is-enabled", "--quiet", unit)
            if enabled_result is None:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.BLOCKED,
                        LifecycleResourceKind.UNIT,
                        unit,
                        "systemd enablement check could not be executed",
                    )
                )
                continue
            enabled = enabled_result.returncode
            if enabled == 0:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.BLOCKED,
                        LifecycleResourceKind.UNIT,
                        unit,
                        "unit is enabled; disable it before destroy",
                    )
                )
                continue
            if enabled not in {1, _SYSTEMCTL_NOT_FOUND_EXIT}:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.BLOCKED,
                        LifecycleResourceKind.UNIT,
                        unit,
                        f"systemd enablement check failed with exit {enabled}",
                    )
                )
                continue
            actions.append(
                LifecycleAction(
                    LifecycleDisposition.PRESERVE,
                    LifecycleResourceKind.UNIT,
                    unit,
                    (
                        "runtime unit is not found"
                        if _SYSTEMCTL_NOT_FOUND_EXIT in (active, enabled)
                        else "runtime unit is inactive and disabled"
                    ),
                )
            )
        return actions

    def _post_reload_unit_actions(self, owned: OwnedBindings) -> list[LifecycleAction]:
        """Reverify the prior exact unit set after the manager accepts removal."""
        actions: list[LifecycleAction] = []
        for unit in owned.runtime_units:
            result = self._run_systemctl(
                "show",
                unit,
                "--property=LoadState",
                "--property=ActiveState",
                "--property=UnitFileState",
            )
            if result is None:
                detail = "post-reload systemd state check could not be executed"
            elif result.returncode != 0:
                error = result.stderr.strip() or f"exit {result.returncode}"
                detail = f"post-reload systemd state check failed: {error}"
            else:
                fields = self._parse_show(result.stdout)
                load_state = fields.get("LoadState")
                active_state = fields.get("ActiveState")
                unit_file_state = fields.get("UnitFileState")
                if load_state == "not-found" and active_state == "inactive":
                    actions.append(
                        LifecycleAction(
                            LifecycleDisposition.PRESERVE,
                            LifecycleResourceKind.UNIT,
                            unit,
                            "runtime unit is stably inactive and not found after daemon reload",
                        )
                    )
                    continue
                if load_state == "loaded" and active_state == "inactive" and unit_file_state == "disabled":
                    actions.append(
                        LifecycleAction(
                            LifecycleDisposition.PRESERVE,
                            LifecycleResourceKind.UNIT,
                            unit,
                            "runtime unit is stably inactive and disabled after daemon reload",
                        )
                    )
                    continue
                detail = (
                    "post-reload unit is not stably inactive and disabled/not-found "
                    f"(load={load_state or 'unknown'}, active={active_state or 'unknown'}, "
                    f"unit-file={unit_file_state or 'unknown'})"
                )
            actions.append(
                LifecycleAction(
                    LifecycleDisposition.BLOCKED,
                    LifecycleResourceKind.UNIT,
                    unit,
                    detail,
                )
            )
        return actions

    def _run_systemctl(self, *arguments: str) -> ProcessResult | None:
        """Run one bounded exact-unit probe and retain invocation failure as unknown."""
        if self._systemctl is None:
            return None
        try:
            result = self._runner.run(
                (self._systemctl, "--user", *arguments),
                timeout_s=_SYSTEMCTL_PROBE_TIMEOUT_SECONDS,
            )
        except ProcessInvocationError:
            return None
        return result

    @staticmethod
    def _parse_show(content: str) -> dict[str, str]:
        """Parse the exact properties requested from ``systemctl show``."""
        fields: dict[str, str] = {}
        for line in content.splitlines():
            key, separator, value = line.partition("=")
            if separator and key not in fields:
                fields[key] = value
        return fields
