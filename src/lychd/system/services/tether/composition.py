"""Bootstrap-safe native assembly and closed internal preflight/closure entry."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.tether.models import CompiledTetherPlan, TetherPeerIntent
from lychd.system.constants import PATH_CACHE_ROOT, PATH_CODEX_ROOT, PATH_CRYPT_ROOT
from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator.process import SubprocessRunner
from lychd.system.services.lifecycle.lock import LifecycleLock
from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore
from lychd.system.services.tether.closure import TetherStopAdapter
from lychd.system.services.tether.custody import PreparationStore, TetherCustody
from lychd.system.services.tether.models import (
    ClosureObservation,
    EnrollRequest,
    OperationReceipt,
    PreparedInspection,
    TetherError,
    digest,
)
from lychd.system.services.tether.operations import TetherOperations
from lychd.system.services.tether.secrets import TetherSecrets

if TYPE_CHECKING:
    from lychd.cli.binding import BindingCommandSession
    from lychd.system.services.bind import BindRequest


def _binding_request(session: BindingCommandSession) -> BindRequest:
    """Compile the same complete manager-attributed request as ordinary CLI bind."""
    from lychd.system.services.bind_compilation import compile_bind_request

    return compile_bind_request(
        settings=session.settings_snapshot.materialize(),
        extensions=session.extensions,
        runes=session.runes,
        soulstones=session.soulstones,
        portals=session.portals,
    )


def _tether_plan(request: BindRequest) -> CompiledTetherPlan:
    """Require the single builtin profile admitted by complete Transmutation."""
    if len(request.tether_plans) != 1:
        msg = "Native Tether operations require exactly one manager-admitted builtin Tether profile"
        raise TetherError(msg)
    return request.tether_plans[0]


def declared_tether_plan() -> CompiledTetherPlan:
    """Compile public declared intent before preparation or binding is available."""
    from lychd.cli.binding import BindingCommandSession

    return _tether_plan(_binding_request(BindingCommandSession.inspect()))


def prepared_tether_inspection() -> PreparedInspection:
    """Read exact selected preparation metadata without requiring any Tether binding."""
    if os.geteuid() == 0:
        msg = "Tether preparation metadata belongs to the rootless operator"
        raise TetherError(msg)
    custody = TetherCustody(PATH_CODEX_ROOT, PATH_CRYPT_ROOT)
    selected = PreparationStore(custody).selected()
    receipt = preparation_service(selected.plan).attest()
    raw = custody.read("public", "peer.json")
    peer = TetherPeerIntent.model_validate_json(raw) if raw is not None else None
    if peer is not None and peer.installation_id != selected.selection.installation_id:
        msg = "Current peer belongs to another prepared installation"
        raise TetherError(msg)
    return PreparedInspection(
        installation_id=selected.selection.installation_id,
        envelope_digest=selected.plan.envelope_digest,
        preparation_digest=digest(selected.selection),
        peer_generation=peer.generation if peer else 0,
        preparation=receipt,
    )


def _tool(name: str, *locations: str) -> str:
    tool = trusted_host_tool(name, fallbacks=tuple(Path(location) for location in locations) or None)
    if tool is None:
        msg = f"A trusted {name} executable is required for native Tether operations"
        raise TetherError(msg)
    return tool


def preparation_service(plan: CompiledTetherPlan, *, podman_bin: str | None = None) -> TetherSecrets:
    """Build the mandatory bind-time identity attestor, with no creation effect.

    Bind calls ``attest`` before preview and again under LifecycleLock and
    compares the returned PreparationReceipt. It must never use exists-only
    secret checks as a substitute for this exact identity/fingerprint result.
    """
    custody = TetherCustody(PATH_CODEX_ROOT, PATH_CRYPT_ROOT)
    return TetherSecrets(
        plan,
        custody,
        SubprocessRunner(),
        podman_bin=podman_bin or _tool("podman"),
        wg_bin=_tool("wg", "/usr/bin/wg"),
        ssh_keygen_bin=_tool("ssh-keygen", "/usr/bin/ssh-keygen"),
    )


def build_tether_operations(*, for_closure: bool = False) -> TetherOperations:  # noqa: C901, PLR0915 - assemble fixed fresh/retained native authority and cold observation ports
    """Resolve fixed native authority without assembling an application listener."""
    if os.geteuid() == 0:
        msg = "Tether belongs to the rootless operator; rerun as your ordinary user"
        raise TetherError(msg)
    if for_closure:
        return _retained_operations()
    from lychd.cli.binding import BindingCommandSession
    from lychd.system.services.scribe.facade import ScribeService

    session = BindingCommandSession.inspect()
    foundation = session.preflight.require_ready()
    plan = _tether_plan(_binding_request(session))
    LifecycleReceiptStore().require_dedicated_root_identities((PATH_CODEX_ROOT, PATH_CRYPT_ROOT, PATH_CACHE_ROOT))
    custody = TetherCustody(PATH_CODEX_ROOT, PATH_CRYPT_ROOT)
    runner = SubprocessRunner()
    secrets = preparation_service(plan, podman_bin=foundation.podman_bin)

    def binding_probe() -> str:
        # Fresh full-generation compilation/inspection only. Peer operations
        # never call reconcile_all or create/rotate any Core secret.
        current = BindingCommandSession.inspect()
        current_foundation = current.preflight.require_ready()
        request = _binding_request(current)
        if _tether_plan(request) != plan:
            msg = "Tether static envelope changed after native assembly"
            raise TetherError(msg)
        current.preflight_service.attest_tether_preparation(plan, podman_bin=current_foundation.podman_bin)
        scribe = ScribeService(expected_sites=current_foundation.sites)
        owned = scribe.inspect_owned_bindings()
        expected = {*plan.transport_units, *plan.plain_unit_names}
        if not owned.receipt_present or owned.generation is None or not expected <= set(owned.runtime_units):
            msg = "The exact Tether body is not owned by the complete Scribe generation; bind first"
            raise TetherError(msg)
        preview = scribe.plan_reconcile_all(request.manifests, plain_units=dict(request.plain_units))
        if preview.mutates:
            msg = "Current bindings differ from complete declared intent; ordinary bind is required"
            raise TetherError(msg)
        return owned.generation

    def preparation_cold_probe(old_plan: CompiledTetherPlan) -> ClosureObservation:
        from lychd.system.services.deployment import DeploymentInspectionService

        scribe = ScribeService(expected_sites=foundation.sites)
        owned = scribe.inspect_owned_bindings()
        expected = {*old_plan.transport_units, *old_plan.plain_unit_names}
        observer = TetherStopAdapter(
            old_plan, runner, podman_bin=foundation.podman_bin, systemctl_bin=foundation.systemctl_bin, custody=custody
        )
        present = expected.intersection(owned.runtime_units)
        if present:
            if present != expected or owned.generation is None:
                msg = "Image replacement refuses partial Tether binding ownership"
                raise TetherError(msg)
            DeploymentInspectionService(runner=runner).observe_owned_units(owned, unit_names=frozenset(expected))
            observation = observer.observe()
            if not observation.closed:
                msg = "Image replacement requires the exact owned Tether road cold"
                raise TetherError(msg)
            return observation
        sources = (
            *(
                foundation.sites.quadlet.path / name
                for name in (
                    old_plan.pod_source,
                    f"{old_plan.wireguard_container}.container",
                    f"{old_plan.forwarder_container}.container",
                )
            ),
            *(foundation.sites.systemd_user.path / name for name in old_plan.plain_unit_names),
        )
        if any(os.path.lexists(path) for path in sources):
            msg = "Image replacement refuses unowned fixed Tether binding sources"
            raise TetherError(msg)
        return observer.observe_never_bound()

    stop = TetherStopAdapter(
        plan, runner, podman_bin=foundation.podman_bin, systemctl_bin=foundation.systemctl_bin, custody=custody
    )
    return TetherOperations(
        plan,
        custody,
        secrets,
        stop,
        runner,
        systemctl_bin=foundation.systemctl_bin,
        binding_probe=binding_probe,
        lock_factory=LifecycleLock,
        preparation_cold_probe=preparation_cold_probe,
    )


def _retained_operations() -> TetherOperations:
    """Close a receipted native installation even when current Runes drift."""
    from lychd.system.services.deployment import DeploymentInspectionService, DeploymentObservationError
    from lychd.system.services.scribe.facade import ScribeService

    custody = TetherCustody(PATH_CODEX_ROOT, PATH_CRYPT_ROOT)
    custody.attest()
    store = PreparationStore(custody)
    peer_raw = custody.read("public", "peer.json")
    if peer_raw is None:
        plan = store.selected().plan
    else:
        peer = TetherPeerIntent.model_validate_json(peer_raw)
        enrollment_raw = custody.read("operations", f"{peer.operation_id}.json")
        if enrollment_raw is None:
            msg = "Current peer has no exact historical enrollment plan authority"
            raise TetherError(msg)
        enrollment = OperationReceipt.model_validate_json(enrollment_raw)
        request = enrollment.request
        if (
            not isinstance(request, EnrollRequest)
            or request.peer != peer
            or enrollment.request_digest != digest(request)
        ):
            msg = "Current peer differs from its exact historical enrollment authority"
            raise TetherError(msg)
        plan = store.retained_enrollment_plan(peer, enrollment)
    LifecycleReceiptStore().require_dedicated_root_identities((PATH_CODEX_ROOT, PATH_CRYPT_ROOT, PATH_CACHE_ROOT))
    process = SubprocessRunner()
    podman, systemctl = _tool("podman"), _tool("systemctl")
    secrets = TetherSecrets(
        plan,
        custody,
        process,
        podman_bin=podman,
        wg_bin=trusted_host_tool("wg", fallbacks=(Path("/usr/bin/wg"),)) or "",
        ssh_keygen_bin=trusted_host_tool("ssh-keygen", fallbacks=(Path("/usr/bin/ssh-keygen"),)) or "",
    )

    def binding_probe() -> str:
        owned = ScribeService().inspect_owned_bindings()
        if (
            not owned.receipt_present
            or owned.generation is None
            or not {*plan.transport_units, *plan.plain_unit_names} <= set(owned.runtime_units)
        ):
            msg = "Retained Tether bindings are absent or no longer owned"
            raise TetherError(msg)
        try:
            DeploymentInspectionService(runner=process).observe_owned_units(
                owned, unit_names=frozenset((*plan.transport_units, *plan.plain_unit_names))
            )
            stop.require_retained_runtime_ownership(owned.generation)
        except (DeploymentObservationError, ValueError, OSError) as exc:
            msg = "Retained Tether effective units or runtime identities are no longer owned"
            raise TetherError(msg) from exc
        return owned.generation

    def desired_probe() -> str:
        from lychd.cli.binding import BindingCommandSession

        current = BindingCommandSession.inspect()
        current.preflight.require_ready()
        return _tether_plan(_binding_request(current)).envelope_digest

    stop = TetherStopAdapter(plan, process, podman_bin=podman, systemctl_bin=systemctl, custody=custody)
    return TetherOperations(
        plan,
        custody,
        secrets,
        stop,
        process,
        systemctl_bin=systemctl,
        binding_probe=binding_probe,
        lock_factory=LifecycleLock,
        desired_probe=desired_probe,
    )


def main() -> None:
    """Accept only fixed internal startup, poststart or closure operations."""
    allowed = {
        "preflight",
        "close",
        "begin-pod",
        "preflight-pod",
        "preflight-wireguard",
        "preflight-forwarder",
        "attest-pod",
        "attest-wireguard",
        "attest-forwarder",
    }
    if len(sys.argv[1:]) != 1 or sys.argv[1] not in allowed:
        msg = "Expected one fixed internal Tether lifecycle operation"
        raise TetherError(msg)
    command = sys.argv[1]
    operations = build_tether_operations(for_closure=command == "close")
    # systemd children also run while public enrollment holds LifecycleLock.
    # Their finite receipt writes use immutable identity-specific create; they
    # never reacquire the parent's lock, start units or clear a fence.
    if command == "close":
        operations.handle_closure()
    elif command == "begin-pod":
        operations.begin_pod()
    elif command == "preflight":
        operations.startup_preflight()
    elif command.startswith("preflight-"):
        operations.role_preflight(command.removeprefix("preflight-"))
    else:
        operations.attest_started(command.removeprefix("attest-"))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - fixed diagnostic suppresses settings and secret validation input
        print("Native Tether preflight or closure remains refused/incomplete", file=sys.stderr)  # noqa: T201 - fixed stderr diagnostic
        raise SystemExit(1) from None
