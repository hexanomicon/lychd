"""Versioned, read-only deployment assessment owned by the host lifecycle boundary.

This deliberately narrow profile admits fresh, model-free container installations. It
never migrates settings, rebases creation evidence, adopts foreign material, or
performs a lifecycle effect. Controller source admission establishes which installed
CLI is invoked; the assessment checks its exact generated Reactor binding.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from lychd.config.settings import SettingsSnapshot, get_settings
from lychd.system import constants
from lychd.system.binding_sites import inspect_binding_site
from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator import OperatorTarget, build_operator_services
from lychd.system.operator.process import ProcessRunner, SubprocessRunner
from lychd.system.path_safety import path_has_symlink_component
from lychd.system.schemas import QuadletContainer, QuadletPod
from lychd.system.services.lifecycle.models import LifecycleError
from lychd.system.services.lifecycle.paths import digest_file
from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore
from lychd.system.services.scribe import ScribeService
from lychd.system.services.scribe.naming import runtime_unit_for_source
from lychd.system.services.scribe.storage import capture_path_state

if TYPE_CHECKING:
    from lychd.config.settings import Settings
    from lychd.system.schemas import QuadletBase
    from lychd.system.services.scribe.models import OwnedBindings

SCHEMA = "lychd.deployment"
VERSION = 1
_REVISION = re.compile(r"[0-9a-f]{40}")
_IMAGE_ID = re.compile(r"(?:sha256:)?([0-9a-f]{64})")
_COMMON_PROPERTIES = (
    "Id",
    "LoadState",
    "ActiveState",
    "SubState",
    "Job",
    "FragmentPath",
    "SourcePath",
    "DropInPaths",
    "NeedDaemonReload",
)
_SERVICE_PROPERTIES = ("MainPID", "ControlPID", "Result", "ExecMainStatus")
_MAX_CONFIG_BYTES = 1024 * 1024
_MAX_TREE_ENTRIES = 4096
_MAX_OBSERVATION_BYTES = 1024 * 1024
_CONFIG_MODE = 0o600


@dataclass(frozen=True, slots=True)
class DeploymentRequest:
    """Exact campaign identity; image references are derived rather than supplied."""

    revision: str
    image_id: str | None = None
    verify: bool = False

    def __post_init__(self) -> None:
        """Reject unpinned campaign identities before host inspection."""
        if _REVISION.fullmatch(self.revision) is None:
            msg = "deployment revision must be exactly 40 lowercase hexadecimal characters"
            raise ValueError(msg)
        if self.image_id is not None:
            match = _IMAGE_ID.fullmatch(self.image_id)
            if match is None:
                msg = "deployment image ID must be exactly 64 lowercase hexadecimal characters"
                raise ValueError(msg)
            object.__setattr__(self, "image_id", match.group(1))

    @property
    def image_ref(self) -> str:
        return f"localhost/lychd:{self.revision}"


@dataclass(slots=True)
class DeploymentReport:
    """Secret-free observation, with an explicit refusal rather than inferred authority."""

    request: DeploymentRequest
    state: str = "unknown"
    reasons: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    checks: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        actions = {"absent": "init", "initialized": "bind", "bound_inactive": "start", "running": "observe"}
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "profile": "empty-extensions-container",
            "revision": self.request.revision,
            "image_ref": self.request.image_ref,
            "state": self.state,
            "next_action": actions.get(self.state, "refuse"),
            "reasons": self.reasons,
            "facts": self.facts,
            "checks": self.checks,
            "ok": self.state == "running"
            and (not self.request.verify or (bool(self.checks) and all(check["ok"] for check in self.checks))),
        }


class DeploymentObservationError(RuntimeError):
    """A bounded host observation could not establish its declared facts."""


class DeploymentInspectionService:
    """Compose existing ownership services into one conservative deployment decision."""

    def __init__(self, *, runner: ProcessRunner | None = None) -> None:
        """Reuse native ownership and process adapters without application assembly."""
        self.runner = runner or SubprocessRunner()
        self.receipt = LifecycleReceiptStore()
        self.scribe = ScribeService()
        self.operator = build_operator_services(runner=self.runner)

    def run(self, tool: str, *arguments: str) -> str:
        executable = trusted_host_tool(tool)
        if executable is None:
            msg = f"tool_unavailable:{tool}"
            raise DeploymentObservationError(msg)
        result = self.runner.run((executable, *arguments), timeout_s=20.0)
        if result.returncode != 0:
            msg = f"observation_failed:{tool}"
            raise DeploymentObservationError(msg)
        if len(result.stdout.encode(errors="replace")) > _MAX_OBSERVATION_BYTES:
            message = "observation_output_limit"
            raise DeploymentObservationError(message)
        return result.stdout

    def inspect(self, request: DeploymentRequest) -> DeploymentReport:  # noqa: C901, PLR0911, PLR0912, PLR0915 - each conservative admission refusal remains explicit
        """Return typed refusals; operational failures are handled by the JSON adapter."""
        report = DeploymentReport(request)
        if os.geteuid() == 0:
            report.reasons.append("ordinary_runtime_user_required")
            return report
        bindings = self.scribe.inspect_owned_bindings()
        units = self._unit_names(bindings)
        observed = {name: self.observe_unit(name) for name in units}
        footprint = self._footprint(bindings)
        report.facts.update(units=observed, footprint=footprint, cli=str(Path(sys.prefix) / "bin" / "lychd"))
        material = (
            any(os.path.lexists(root) for root in self._roots()) or bindings.receipt_present or any(footprint.values())
        )
        if not material and all(self.unit_quiescent(value, absent=True) for value in observed.values()):
            report.state = "absent"
            return report
        if not self.receipt.exists:
            report.reasons.append("material_without_initialization_authority")
            return report
        settings = self._configuration(request)
        report.facts["configuration"] = {"state": "original", "image": settings.server.web.image}
        inventory = self.operator.inventory.inspect(OperatorTarget.SYSTEM)
        if inventory.warnings:
            report.reasons.append("inventory_warnings")
            return report
        report.facts["inventory"] = inventory.as_dict()
        manifests, plain_units = self.desired_bindings(settings)
        expected_names = self._runtime_names(manifests, plain_units)
        if any(name not in expected_names for name, value in observed.items() if value["LoadState"] != "not-found"):
            report.reasons.append("foreign_runtime_unit")
            return report
        if footprint["foreign_sources"]:
            report.reasons.append("foreign_binding_source")
            return report
        self._require_original_files()
        self._require_known_tree(bound=bindings.receipt_present)
        image = self._image(request)
        report.facts["image"] = image
        if image["revision"] != request.revision:
            report.state = "foreign_revision"
            report.reasons.append("image_revision_mismatch")
            return report
        if request.image_id is not None and image["id"] != request.image_id:
            report.reasons.append("admitted_image_id_mismatch")
            return report
        expected_containers = {
            manifest.container_name for manifest in manifests if isinstance(manifest, QuadletContainer)
        }
        expected_pods = {manifest.pod_name for manifest in manifests if isinstance(manifest, QuadletPod)}
        if (
            set(footprint["secrets"]) - set(settings.server.privileged_secret_names)
            or set(footprint["pods"]) - expected_pods
            or set(footprint["containers"]) - expected_containers
        ):
            report.reasons.append("foreign_runtime_material")
            return report
        if not bindings.receipt_present:
            if footprint["containers"] or footprint["pods"] or footprint["secrets"]:
                report.reasons.append("runtime_material_without_binding_authority")
            elif any(not self.unit_quiescent(value, absent=True) for value in observed.values()):
                report.reasons.append("runtime_units_without_binding_authority")
            elif not self._data_empty():
                report.reasons.append("unbound_database_not_empty")
            else:
                report.state = "initialized"
            return report
        if set(bindings.runtime_units) != expected_names:
            report.reasons.append("unsupported_owned_unit_set")
            return report
        self._require_effective_bindings(bindings, observed)
        reactor = next((path for path in bindings.systemd_sources if path.name == "lychd-reactor.service"), None)
        if reactor is None or self._source_bytes(reactor) != plain_units["lychd-reactor.service"].encode():
            report.state = "foreign_revision"
            report.reasons.append("reactor_cli_binding_mismatch")
            return report
        plan = self.scribe.plan_reconcile_all(manifests, plain_units=plain_units)
        if plan.mutates:
            report.reasons.append("bindings_differ_from_declared_generation")
            return report
        report.facts["binding_generation"] = bindings.generation
        active_units = self._active_names(manifests, plain_units)
        owned_states = {name: observed[name] for name in expected_names}
        if all(self.unit_quiescent(value) for value in owned_states.values()) and not footprint["running_containers"]:
            report.state = "bound_inactive"
        elif all(self.unit_active(owned_states[name]) for name in active_units) and all(
            self.unit_quiescent(value) for name, value in owned_states.items() if name not in active_units
        ):
            running_image = (
                self.run("podman", "container", "inspect", "lychd-vessel", "--format", "{{.Image}}")
                .strip()
                .removeprefix("sha256:")
            )
            if running_image != image["id"]:
                report.reasons.append("running_image_identity_mismatch")
            else:
                report.state = "running"
        else:
            report.reasons.append("mixed_transitional_or_unknown_units")
        if request.verify:
            if report.state != "running":
                report.checks.append({"name": "deployment.running", "ok": False, "detail": report.state})
            else:
                from lychd.system.services.deployment_acceptance import verify_deployment

                report.checks = verify_deployment(
                    self, settings=settings, request=request, units=owned_states, image=image, active_units=active_units
                )
        return report

    @staticmethod
    def _roots() -> tuple[Path, ...]:
        return constants.PATH_CODEX_ROOT, constants.PATH_CRYPT_ROOT, constants.PATH_CACHE_ROOT

    def _configuration(self, request: DeploymentRequest) -> Settings:
        self._require_original_files()
        state = capture_path_state(constants.PATH_LYCHD_TOML)
        if (
            state is None
            or state.content is None
            or len(state.content) > _MAX_CONFIG_BYTES
            or stat.S_IMODE(state.mode) != _CONFIG_MODE
        ):
            msg = "configuration_not_private_regular_file"
            raise DeploymentObservationError(msg)
        import hashlib

        recorded = next(entry for entry in self.receipt.load().files if Path(entry.path) == constants.PATH_LYCHD_TOML)
        if (state.device, state.inode, state.user_id) != (
            recorded.device,
            recorded.inode,
            os.getuid(),
        ) or "sha256:" + hashlib.sha256(state.content).hexdigest() != recorded.digest:
            message = "configuration_changed_during_observation"
            raise DeploymentObservationError(message)
        document = tomllib.loads(state.content.decode())
        declared = SettingsSnapshot(payload=json.dumps(document)).materialize()
        baseline = SettingsSnapshot(payload="{}").materialize()
        baseline.server.web.image = request.image_ref
        if declared.model_dump(mode="json", exclude_none=True) != baseline.model_dump(mode="json", exclude_none=True):
            msg = "configuration_outside_deployment_profile"
            raise DeploymentObservationError(msg)
        if SettingsSnapshot.capture(get_settings()).payload != SettingsSnapshot.capture(declared).payload:
            msg = "effective_configuration_differs"
            raise DeploymentObservationError(msg)
        return declared

    def _require_original_files(self) -> None:
        receipt = self.receipt.load()
        self.receipt.require_dedicated_root_identities(self._roots())
        if not any(Path(entry.path) == constants.PATH_LYCHD_TOML for entry in receipt.files):
            msg = "configuration_without_creation_evidence"
            raise DeploymentObservationError(msg)
        for entry in receipt.files:
            path = Path(entry.path)
            if path_has_symlink_component(path):
                msg = "created_file_symlink"
                raise DeploymentObservationError(msg)
            metadata = path.lstat()
            expected_mode = (
                0o755
                if path == constants.PATH_POSTGRES_ROOT_DIR / "init_db.sh"
                else 0o644
                if path == constants.PATH_POSTGRES_ROOT_DIR / "pg_hba_v1.conf"
                else _CONFIG_MODE
            )
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_size > _MAX_CONFIG_BYTES
                or stat.S_IMODE(metadata.st_mode) != expected_mode
            ):
                message = "created_file_shape_or_mode_changed"
                raise DeploymentObservationError(message)
            if (metadata.st_dev, metadata.st_ino, metadata.st_uid) != (entry.device, entry.inode, os.getuid()):
                msg = "created_file_identity_changed"
                raise DeploymentObservationError(msg)
            if digest_file(path, expected=metadata) != entry.digest:
                msg = "created_file_digest_changed"
                raise DeploymentObservationError(msg)

    def _require_known_tree(self, *, bound: bool) -> None:
        receipt = self.receipt.load()
        known = {
            self.receipt.path,
            *(Path(entry.path) for entry in receipt.files),
            *(Path(entry.path) for entry in receipt.directories),
            *self._roots(),
        }
        known.update(Path(entry.path) for entry in receipt.subvolumes)
        count = 0
        pending = list(self._roots())
        while pending:
            directory = pending.pop()
            if directory == constants.PATH_POSTGRESS_DATA_DIR:
                continue
            # Runtime-generated records stay in their source-owned dedicated roots.
            if bound and directory in {
                constants.PATH_RUNTIME_GUARD_DIR,
                constants.PATH_LAB_DIR,
                constants.PATH_TRIGGERS_DIR,
            }:
                continue
            for path in directory.iterdir():
                count += 1
                if count > _MAX_TREE_ENTRIES or path not in known or path.is_symlink():
                    msg = "foreign_or_unbounded_installation_tree"
                    raise DeploymentObservationError(msg)
                if path.is_dir():
                    pending.append(path)

    @staticmethod
    def desired_bindings(settings: Settings) -> tuple[list[QuadletBase], dict[str, str]]:
        """Project the canonical complete bind compiler without a second recipe."""
        from lychd.config.runes.registry import RuneRegistry
        from lychd.extensions.host import assemble_extensions
        from lychd.system.services.bind_compilation import compile_bind_request

        request = compile_bind_request(
            settings=settings,
            extensions=assemble_extensions(settings),
            runes=RuneRegistry(()),
            soulstones=(),
            portals=(),
        )
        return list(request.manifests), request.plain_unit_mapping()

    @staticmethod
    def _require_effective_bindings(bindings: OwnedBindings, observed: dict[str, dict[str, str]]) -> None:
        """Refuse overrides and shadows before an inactive body can be started."""
        for source in (*bindings.systemd_sources, *bindings.quadlet_sources):
            name = runtime_unit_for_source(source.name)
            if name not in observed:
                msg = "effective_binding_unit_missing"
                raise DeploymentObservationError(msg)
            unit = observed[name]
            if unit["LoadState"] != "loaded" or unit["DropInPaths"] or unit["NeedDaemonReload"] != "no":
                msg = "effective_binding_override_or_reload"
                raise DeploymentObservationError(msg)
            if source in bindings.systemd_sources:
                valid = (
                    unit["FragmentPath"] == str(source)
                    and unit["SourcePath"] == ""
                    and not path_has_symlink_component(source)
                )
            else:
                fragment = constants.PATH_SYSTEMD_USER_GENERATOR_DIR / name
                valid = (
                    unit["SourcePath"] == str(source)
                    and unit["FragmentPath"] == str(fragment)
                    and not path_has_symlink_component(fragment)
                    and inspect_binding_site(fragment.parent, current_uid=os.getuid()).prepared
                )
                if valid:
                    metadata = fragment.lstat()
                    valid = (
                        stat.S_ISREG(metadata.st_mode)
                        and metadata.st_uid == os.getuid()
                        and metadata.st_nlink == 1
                        and not metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                    )

            if not valid:
                msg = "effective_binding_definition_mismatch"
                raise DeploymentObservationError(msg)

    @staticmethod
    def _runtime_names(manifests: list[QuadletBase], plain: dict[str, str]) -> set[str]:
        sources = [*plain]
        for manifest in manifests:
            if isinstance(manifest, QuadletContainer):
                sources.append(f"{manifest.container_name}.container")
            elif isinstance(manifest, QuadletPod):
                sources.append(f"{manifest.pod_name}.pod")
        return {runtime_unit_for_source(name) for name in sources}

    @staticmethod
    def _active_names(manifests: list[QuadletBase], plain: dict[str, str]) -> set[str]:
        names = {name for name in plain if name.endswith(".path")}
        for manifest in manifests:
            if isinstance(manifest, QuadletPod):
                names.add(runtime_unit_for_source(f"{manifest.pod_name}.pod"))
            elif isinstance(manifest, QuadletContainer) and manifest.service_type != "oneshot":
                names.add(f"{manifest.container_name}.service")
        return names

    def _unit_names(self, bindings: OwnedBindings) -> set[str]:
        baseline = SettingsSnapshot(payload="{}").materialize()
        manifests, plain = self.desired_bindings(baseline)
        names = self._runtime_names(manifests, plain) | set(bindings.runtime_units) | {"lychd-uncaged-vessel.service"}
        for line in self.run(
            "systemctl", "--user", "list-units", "--all", "--plain", "--no-legend", "lychd*"
        ).splitlines():
            fields = line.split()
            if fields:
                names.add(fields[0])
        return names

    def observe_unit(self, name: str) -> dict[str, str]:
        """Read exactly the properties applicable to the named unit type."""
        properties = (*_COMMON_PROPERTIES, *(_SERVICE_PROPERTIES if name.endswith(".service") else ()))
        content = self.run("systemctl", "--user", "show", name, *(f"--property={key}" for key in properties))
        fields: dict[str, str] = {}
        for line in content.splitlines():
            key, separator, value = line.partition("=")
            if not separator or key in fields:
                msg = "malformed_unit_properties"
                raise DeploymentObservationError(msg)
            fields[key] = value
        if set(fields) != set(properties) or fields["Id"] != name:
            msg = "incomplete_or_wrong_unit_properties"
            raise DeploymentObservationError(msg)
        # Non-service units own no process; service-specific properties do not
        # exist on path units and must not be guessed from missing replies.
        if not name.endswith(".service"):
            fields.update(MainPID="0", ControlPID="0", Result="", ExecMainStatus="")
        return fields

    @staticmethod
    def unit_quiescent(value: dict[str, str], *, absent: bool = False) -> bool:
        return (
            value["LoadState"] in ({"not-found"} if absent else {"loaded", "not-found"})
            and value["ActiveState"] == "inactive"
            and value["SubState"] == "dead"
            and value["MainPID"] == value["ControlPID"] == "0"
            and value["Job"] in {"", "0"}
        )

    @staticmethod
    def unit_active(value: dict[str, str]) -> bool:
        return (
            value["LoadState"] == "loaded"
            and value["ActiveState"] == "active"
            and value["SubState"]
            in ({"waiting", "running"} if value["Id"].endswith(".path") else {"running", "exited"})
            and value["MainPID"].isascii()
            and value["MainPID"].isdecimal()
            and (value["Id"].endswith(".path") or value["SubState"] != "running" or value["MainPID"] != "0")
            and value["ControlPID"] == "0"
            and value["Job"] in {"", "0"}
        )

    def _footprint(self, bindings: OwnedBindings) -> dict[str, list[str]]:
        owned = {*bindings.quadlet_sources, *bindings.systemd_sources}
        foreign = [
            str(path)
            for directory in (constants.PATH_SYSTEMD_UNITS_DIR, constants.PATH_SYSTEMD_USER_UNITS_DIR)
            if directory.is_dir()
            for path in directory.glob("lychd*")
            if path not in owned
        ]
        commands = {
            "secrets": ("secret", "ls", "--format", "{{.Name}}"),
            "containers": ("ps", "--all", "--format", "{{.Names}}"),
            "running_containers": ("ps", "--format", "{{.Names}}"),
            "pods": ("pod", "ps", "--format", "{{.Name}}"),
        }
        found = {
            key: [line for line in self.run("podman", *argv).splitlines() if line.startswith("lychd")]
            for key, argv in commands.items()
        }
        found["foreign_sources"] = foreign
        return found

    def _image(self, request: DeploymentRequest) -> dict[str, str]:
        payload: object = json.loads(self.run("podman", "image", "inspect", request.image_ref))
        if not isinstance(payload, list):
            msg = "malformed_image_identity"
            raise DeploymentObservationError(msg)
        entries = cast("list[object]", payload)
        if len(entries) != 1 or not isinstance(entries[0], dict):
            msg = "malformed_image_identity"
            raise DeploymentObservationError(msg)
        value = cast("dict[str, object]", entries[0])
        identifier = value.get("Id")
        raw_labels = value.get("Labels")
        match = _IMAGE_ID.fullmatch(identifier) if isinstance(identifier, str) else None
        if match is None or not isinstance(raw_labels, dict):
            msg = "missing_image_identity"
            raise DeploymentObservationError(msg)
        labels = cast("dict[str, object]", raw_labels)
        revision = labels.get("org.opencontainers.image.revision", "")
        return {
            "id": match.group(1),
            "revision": revision if isinstance(revision, str) and _REVISION.fullmatch(revision) is not None else "",
            "reference": request.image_ref,
        }

    def _data_empty(self) -> bool:
        if not os.path.lexists(constants.PATH_POSTGRESS_DATA_DIR):
            return True
        return not self.run("podman", "unshare", "/usr/bin/ls", "-A", str(constants.PATH_POSTGRESS_DATA_DIR)).strip()

    @staticmethod
    def _source_bytes(path: Path) -> bytes:
        state = capture_path_state(path)
        if state is None or state.content is None:
            msg = "binding_source_unavailable"
            raise DeploymentObservationError(msg)
        return state.content


def inspect_deployment(request: DeploymentRequest) -> DeploymentReport:
    """Bootstrap-safe composition point used only by the optional status projection."""
    try:
        return DeploymentInspectionService().inspect(request)
    except (LifecycleError, OSError, ValueError) as error:
        # Never render validation input, file contents, or untrusted tool stderr.
        msg = "ownership_or_configuration_unavailable"
        raise DeploymentObservationError(msg) from error
