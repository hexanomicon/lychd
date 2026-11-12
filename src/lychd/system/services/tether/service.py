"""Native Tether lifecycle: durable admission, exact custody, isolated activation.

Ansible and Click call this owner; neither is an alternative VPN orchestrator.
The complete Scribe generation supplies fresh CAS, while admission and retained
runtime closure remain per network and per peer.
"""

from __future__ import annotations

import json
import os
import sys
import time
from contextlib import nullcontext, suppress
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from lychd.config.runes.registry import RuneRegistry
from lychd.domain.tether.compiler import TetherDeployment, compile_tether
from lychd.domain.tether.models import AttachmentAdmission, ImportedAttachment, OfferedPeer, TetherRune, TetherSnapshot
from lychd.system import constants
from lychd.system.schemas import QuadletBase, QuadletContainer, QuadletPod
from lychd.system.services.lifecycle.lock import LifecycleLock
from lychd.system.services.tether.custody import TetherCustody
from lychd.system.services.tether.host import TetherHost
from lychd.system.services.tether.keys import TetherKeys
from lychd.system.services.tether.models import TetherError, TetherIntent, canonical_bytes, load_intent

_RUNTIME_UNIT = "lychd-tether-runtime.service"
_RESUME_UNIT = "lychd-tether-resume.service"
_PRIVATE_FILE_MODE = 0o600
_MAX_KEY_OWNERS = 512


class NativeState(BaseModel):
    """Public durable authority; no key bytes, passwords, tokens, or tmpfs identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1] = 1
    intent: TetherIntent
    topology: TetherRune | None = None
    key_owners: dict[str, str] = Field(default_factory=dict, max_length=_MAX_KEY_OWNERS)
    snapshot: TetherSnapshot
    image: dict[str, str]
    active: tuple[str, ...] = ()
    incarnations: dict[str, dict[str, Any]] = Field(default_factory=dict)
    pods: dict[str, dict[str, Any]] = Field(default_factory=dict)
    launches: dict[str, dict[str, Any]] = Field(default_factory=dict)
    revocations: dict[str, dict[str, Any]] = Field(default_factory=dict)


class NativeTetherService:
    """Run rootless under the same lifecycle lock as init, bind and the Reactor."""

    def __init__(
        self,
        *,
        custody: TetherCustody | None = None,
        host: TetherHost | None = None,
        runtime_root: Path | None = None,
    ) -> None:
        """Bind fixed production paths or explicit isolated test ports."""
        if os.geteuid() == 0:
            msg = "Tether requires the ordinary LychD runtime user"
            raise TetherError(msg)
        self.custody = custody or TetherCustody(constants.PATH_TETHER_STATE_DIR)
        self.host = host or TetherHost()
        self.runtime_root = runtime_root or constants.PATH_TETHER_RUNTIME_DIR

    def _declared(self) -> tuple[Any, Any, Any, TetherRune]:
        from lychd.config.runes.registry import load_rune_registry
        from lychd.config.settings.root import get_settings
        from lychd.extensions.host import get_extensions
        from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore

        receipt = LifecycleReceiptStore()
        receipt.require_dedicated_root_identities(
            (constants.PATH_CODEX_ROOT, constants.PATH_CRYPT_ROOT, constants.PATH_CACHE_ROOT)
        )
        settings = get_settings()
        extensions = get_extensions()
        if "tether" not in settings.extensions.builtins:
            msg = "Select Tether during original initialization before preparing it"
            raise TetherError(msg)
        runes = load_rune_registry(extensions)
        rune = runes.one(TetherRune)
        # Original configuration remains the immutable installation admission.
        # A changed deployment is a new explicit campaign, never silent adoption.
        receipt.read_original_file(constants.PATH_LYCHD_TOML, expected_mode=0o600, max_bytes=1048576)
        return settings, extensions, runes, rune

    def _load_retained(self) -> NativeState:
        """Retain denial authority when current images or credentials are unavailable."""
        from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore

        self.custody.attest()
        raw = self.custody.read("state.json")
        if raw is None:
            msg = "Tether has not been prepared"
            raise FileNotFoundError(msg)
        LifecycleReceiptStore().require_dedicated_root_identities(
            (constants.PATH_CODEX_ROOT, constants.PATH_CRYPT_ROOT, constants.PATH_CACHE_ROOT)
        )
        return NativeState.model_validate_json(canonical_bytes(raw))

    def _load(self) -> NativeState:
        state = self._load_retained()
        settings, _extensions, _runes, rune = self._declared()
        # Loader source provenance is not serialized into the public preparation intent.
        if canonical_bytes(rune) != canonical_bytes(state.intent.rune) or settings.server.port != state.intent.web_port:
            msg = "Tether topology differs from its admitted preparation"
            raise TetherError(msg)
        if self.host.image(rune.quadlet.image) != state.image:
            msg = "The prepared Tether image was replaced"
            raise TetherError(msg)
        self.effective_rune(state)
        return state

    @staticmethod
    def _key_assignments(rune: TetherRune, peers: tuple[OfferedPeer, ...]) -> tuple[tuple[str, str], ...]:
        assignments: list[tuple[str, str]] = []
        if rune.offered:
            assignments.append((rune.offered.private_key_ref, "offered:wireguard"))
        for attachment in rune.attachments:
            assignments.append((attachment.private_key_ref, f"attachment:{attachment.id}:wireguard"))
            if attachment.preshared_key_ref:
                assignments.append((attachment.preshared_key_ref, f"attachment:{attachment.id}:preshared"))
        for peer in peers:
            if peer.preshared_key_ref:
                assignments.append((peer.preshared_key_ref, f"peer:{peer.id}:preshared"))
            if peer.owner_access:
                assignments.append((peer.owner_access.ssh_host_key_ref, f"peer:{peer.id}:ssh-host"))
        return tuple(assignments)

    @staticmethod
    def _key_ownership(state: NativeState, rune: TetherRune, peers: tuple[OfferedPeer, ...]) -> dict[str, str]:
        """Retain original and retired reference ownership across managed updates."""
        owners = dict(state.key_owners)
        configurations = (
            (state.intent.rune, state.intent.offered_peers),
            (state.topology or state.intent.rune, state.snapshot.offered_peers),
            (rune, peers),
        )
        for definition, admitted_peers in configurations:
            for reference, owner in NativeTetherService._key_assignments(definition, admitted_peers):
                if reference in owners and owners[reference] != owner:
                    message = "Tether key reference belongs to another road or credential purpose"
                    raise TetherError(message)
                owners[reference] = owner
        if len(owners) > _MAX_KEY_OWNERS:
            message = "Tether historical key reference capacity is exhausted"
            raise TetherError(message)
        return owners

    @staticmethod
    def effective_rune(state: NativeState) -> TetherRune:
        """Resolve managed roads without changing the immutable installation envelope."""
        rune = state.topology or state.intent.rune
        if rune.model_dump(exclude={"attachments"}) != state.intent.rune.model_dump(exclude={"attachments"}):
            message = "Managed Tether topology may change only imported attachments"
            raise TetherError(message)
        NativeTetherService._key_ownership(state, rune, state.snapshot.offered_peers)
        return rune

    @staticmethod
    def _effective_registry(state: NativeState, runes: RuneRegistry) -> RuneRegistry:
        """Overlay exactly one Tether definition while preserving every other Rune."""
        runes.one(TetherRune)
        effective = NativeTetherService.effective_rune(state)
        return RuneRegistry(tuple(effective if isinstance(row, TetherRune) else row for row in runes.all()))

    def _save(self, state: NativeState) -> bool:
        return self.custody.write("state.json", state.model_dump(mode="json", by_alias=True))

    def _empty_preparation(self) -> bool:
        if not os.path.lexists(self.custody.root):
            return True
        self.custody.attest()
        if self.custody.read("state.json") is not None:
            return False
        if set(self.custody.known_paths()) != {self.custody.root, self.custody.root / ".custody.json"}:
            message = "Tether state is absent but retained material remains; preserve uncertain custody"
            raise TetherError(message)
        return True

    def preparation_status(self) -> dict[str, Any]:
        """Distinguish missing admission from explicit imports and replaced credentials."""
        if self._empty_preparation():
            paths = self.custody.known_paths() if os.path.lexists(self.custody.root) else ()
            return {
                "state": "absent",
                "missing_secrets": [],
                "required_secrets": [],
                "owned_secrets": [],
                "known_paths": [str(path) for path in paths],
            }
        state = self._load()
        deployment = self._projection(state)
        keys = self._keys(state)
        observation = keys.observe()
        owned = set(observation.identities)
        local = self._local_references(state)
        missing: list[str] = []
        retry_prepare = False
        for reference in deployment.required_secrets:
            phase = observation.preparation_state(reference)
            if phase == "ready":
                if reference not in owned:
                    message = "Ready Tether credential lacks current owned backend evidence"
                    raise TetherError(message)
            elif reference in local:
                retry_prepare = True
            elif phase == "pending":
                message = "Retry native import-key to reconcile the pending client-key operation"
                raise TetherError(message)
            else:
                missing.append(reference)
        return {
            "state": "absent" if retry_prepare else "waiting_keys" if missing else "prepared",
            "missing_secrets": sorted(missing),
            "required_secrets": list(deployment.required_secrets),
            "owned_secrets": sorted(owned),
            "known_paths": [str(path) for path in self.custody.known_paths()],
        }

    def _keys(self, state: NativeState) -> TetherKeys:
        return TetherKeys(self.custody, state.snapshot.installation_epoch, runner=self.host.runner)

    @staticmethod
    def _local_references(state: NativeState) -> dict[str, Literal["wireguard", "ssh-host"]]:
        result: dict[str, Literal["wireguard", "ssh-host"]] = {}
        if state.intent.rune.offered:
            result[state.intent.rune.offered.private_key_ref] = "wireguard"
        for peer in state.snapshot.offered_peers:
            if peer.owner_access:
                result[peer.owner_access.ssh_host_key_ref] = "ssh-host"
        return result

    @staticmethod
    def _references(state: NativeState) -> dict[str, str]:
        rune = NativeTetherService.effective_rune(state)
        return {
            reference: owner.rsplit(":", 1)[1]
            for reference, owner in NativeTetherService._key_assignments(rune, state.snapshot.offered_peers)
        }

    def _attest_keys(self, state: NativeState, deployment: TetherDeployment) -> None:
        self._keys(state).attest_many(deployment.required_secrets)

    def _projection(self, state: NativeState) -> TetherDeployment:
        return compile_tether(
            rune=self.effective_rune(state),
            snapshot=state.snapshot,
            runtime_root=self.runtime_root,
            config_root=self.custody.root / "runtime",
            core_web_port=state.intent.web_port,
            consumer_uid=os.getuid(),
            forbidden_backend_addresses=self.host.host_addresses(),
        )

    def _retained_projection(self, state: NativeState) -> TetherDeployment:
        """Reconstruct withdrawal targets only; this grants no startup authority."""
        return compile_tether(
            rune=self.effective_rune(state),
            snapshot=state.snapshot,
            runtime_root=self.runtime_root,
            config_root=self.custody.root / "runtime",
            core_web_port=state.intent.web_port,
            consumer_uid=os.getuid(),
            forbidden_backend_addresses=(),
        )

    def projection(self) -> TetherDeployment:
        """Return current pure projection after persistent image and key attestation."""
        state = self._load()
        deployment = self._projection(state)
        self._attest_keys(state, deployment)
        return deployment

    def binding_context(self, state_override: NativeState | None = None) -> dict[str, Any]:
        """Supply explicit current authority to the pure complete bind compiler."""
        state = state_override or self._load()
        self._attest_keys(state, self._projection(state))
        return {
            "tether_snapshot": state.snapshot,
            "tether_runtime_root": self.runtime_root,
            "tether_config_root": self.custody.root / "runtime",
            "tether_consumer_uid": os.getuid(),
            "tether_forbidden_backend_addresses": self.host.host_addresses(),
        }

    def bind_request(self, state_override: NativeState | None = None) -> Any:
        """Compile the same complete body as ordinary bind, including boot helpers."""
        from lychd.domain.animation.services.declarations import compile_animator_declarations
        from lychd.system.services.bind_compilation import compile_bind_request

        settings, extensions, runes, _rune = self._declared()
        state = state_override or self._load()
        runes = self._effective_registry(state, runes)
        declarations = compile_animator_declarations(settings=settings, runes=runes)
        request = compile_bind_request(
            settings=settings,
            extensions=extensions,
            runes=runes,
            soulstones=declarations.soulstones,
            portals=declarations.portals,
            **self.binding_context(state),
        )
        executable = Path(sys.prefix) / "bin/lychd"
        from lychd.system.schemas import systemd_environment_assignment, systemd_executable_token

        command = systemd_executable_token(executable)
        environment = "\n".join(
            "Environment=" + systemd_environment_assignment(key, str(value))
            for key, value in {
                "HOME": Path.home(),
                "XDG_CONFIG_HOME": constants.PATH_XDG_CONFIG_HOME,
                "XDG_DATA_HOME": constants.PATH_XDG_DATA_HOME,
                "XDG_CACHE_HOME": constants.PATH_XDG_CACHE_HOME,
            }.items()
        )
        plain = request.plain_unit_mapping()
        plain[_RUNTIME_UNIT] = (
            "[Unit]\nDescription=Prepare private boot-local Tether paths\n"
            "[Service]\nType=oneshot\nRemainAfterExit=no\n" + environment + "\n"
            f"ExecStart={command} tether runtime-dir\nTimeoutStartSec=45\n"
        )
        plain[_RESUME_UNIT] = (
            "[Unit]\nDescription=Resume explicitly activated Tether networks\n"
            "After=lychd-vessel.service\nRequires=lychd-vessel.service\n"
            "[Service]\nType=oneshot\nRemainAfterExit=no\n" + environment + "\n"
            f"ExecStart={command} tether resume\nTimeoutStartSec=120\n"
        )
        manifests: list[QuadletBase] = []
        for manifest in request.manifests:
            prepared_manifest = manifest
            if isinstance(manifest, QuadletContainer) and (
                manifest.tether_role is not None or manifest.container_name == "lychd-vessel"
            ):
                updates: dict[str, Any] = {
                    "requires": [*manifest.requires, _RUNTIME_UNIT],
                    "after": [*manifest.after, _RUNTIME_UNIT],
                }
                if manifest.container_name == "lychd-vessel":
                    updates["wants"] = [*manifest.wants, _RESUME_UNIT]
                prepared_manifest = manifest.model_copy(update=updates)
            manifests.append(prepared_manifest)
        return replace(request, manifests=tuple(manifests), plain_units=tuple(sorted(plain.items())))

    def attest_bind_request(self, request: Any) -> None:
        """Recheck full public intent and exact private-key identities under bind's lock."""
        fresh = self.bind_request()
        if (
            tuple(row.model_dump(mode="json") for row in request.manifests)
            != tuple(row.model_dump(mode="json") for row in fresh.manifests)
            or request.plain_units != fresh.plain_units
            or request.required_secret_names != fresh.required_secret_names
            or request.secret_names != fresh.secret_names
        ):
            msg = "Tether binding admission changed before commit"
            raise TetherError(msg)

    def prepare(self, intent_path: Path, *, dry_run: bool = False) -> dict[str, Any]:
        """Create absent-only custody and local server keys; import client keys separately."""
        intent = load_intent(intent_path)
        with nullcontext() if dry_run else LifecycleLock():
            settings, _extensions, _runes, rune = self._declared()
            if canonical_bytes(rune) != canonical_bytes(intent.rune) or settings.server.port != intent.web_port:
                msg = "Preparation intent differs from original initialization"
                raise TetherError(msg)
            if not self._empty_preparation():
                state = self._load()
                if state.intent != intent:
                    msg = "Existing Tether preparation has different intent"
                    raise TetherError(msg)
                changed = False
            else:
                state = NativeState(
                    intent=intent,
                    snapshot=TetherSnapshot(
                        installation_epoch=uuid4().hex,
                        offered_peers=intent.offered_peers,
                        attachments=intent.attachments,
                    ),
                    image=self.host.image(intent.rune.quadlet.image),
                )
                self._projection(state)
                if dry_run:
                    return {"state": "absent", "changed": True, "dry_run": True}
                changed = self.custody.initialize()
                changed = self._save(state) or changed
            if dry_run:
                return {"state": "prepared", "changed": False, "dry_run": True}
            keys = self._keys(state)
            local_references = self._local_references(state)
            for reference, purpose in local_references.items():
                keys.ensure(reference, purpose)
            self._materialize(state)
            public_keys = [
                {key: value[key] for key in ("reference", "purpose", "public_key", "fingerprint")}
                for value in keys.attest_many(sorted(local_references)).values()
            ]
            return {
                "state": "prepared",
                "changed": changed,
                "installation_epoch": state.snapshot.installation_epoch,
                "public_keys": public_keys,
            }

    def _materialize(self, state: NativeState) -> None:
        deployment = self._projection(state)
        self.custody.directory("runtime", public=True)
        for config in deployment.runtime_configs:
            self.custody.directory("runtime/" + config.name, public=True)
            self.custody.publish(Path("runtime") / config.name / "config.json", config.payload, public=True)
            fence = {**config.fences, "enabled": config.network_id in state.active}
            self.custody.publish(Path("runtime") / config.name / "fences.json", fence, public=True)

    def runtime_dir(self) -> dict[str, Any]:
        """Recreate only boot-local, private paths before a bind-mounted consumer starts."""
        state = self._load()
        deployment = self._projection(state)
        self.host.runtime_directories(
            self.runtime_root, tuple(network.runtime_directory for network in deployment.networks)
        )
        # Runtime catalog is rebuilt from fresh observation, never restored from disk.
        if not os.path.lexists(self.runtime_root / "catalog.json"):
            self._catalog(state, ())
        return {"state": "prepared", "changed": False}

    def _bound(self, request: Any) -> dict[str, dict[str, str]]:
        from lychd.system.services.deployment import DeploymentInspectionService
        from lychd.system.services.scribe.facade import ScribeService

        scribe = ScribeService()
        owned = scribe.inspect_owned_bindings()
        if (
            not owned.receipt_present
            or scribe.plan_reconcile_all(request.manifests, plain_units=request.plain_unit_mapping()).mutates
        ):
            msg = "Current complete bindings differ; run native Tether bind"
            raise TetherError(msg)
        names = frozenset(
            unit for network in request.tether.networks for unit in (*network.unit_names, network.pod_unit)
        )
        return DeploymentInspectionService().observe_owned_units(
            owned, unit_names=names | frozenset({_RUNTIME_UNIT, _RESUME_UNIT, "lychd-vessel.service"})
        )

    def _bind(self, state: NativeState) -> dict[str, Any]:
        from lychd.config.settings import SettingsSnapshot
        from lychd.system.services.bind import BindUseCase
        from lychd.system.services.binding_preflight import BindingPreflightService
        from lychd.system.services.scribe.facade import ScribeService
        from lychd.system.services.secrets import PodmanSecretStore
        from lychd.system.services.systemd import SystemdUserManager

        settings, _extensions, _runes, _rune = self._declared()
        snapshot = SettingsSnapshot.capture(settings)
        preflight = BindingPreflightService()
        foundation = preflight.inspect(settings).require_ready()
        request = self.bind_request()
        self._materialize(state)
        self.host.runtime_directories(
            self.runtime_root, tuple(network.runtime_directory for network in request.tether.networks)
        )
        use_case = BindUseCase(
            scribe=ScribeService(expected_sites=foundation.sites),
            secrets=PodmanSecretStore(foundation.podman_bin),
            systemd_factory=lambda: SystemdUserManager(systemctl_bin=foundation.systemctl_bin),
            foundation=foundation,
            foundation_probe=lambda: preflight.inspect(snapshot.materialize()).require_ready(),
            lock_factory=nullcontext,
            request_attestor=self.attest_bind_request,
        )
        plan = use_case.plan(request)
        self._attest_keys(state, request.tether)
        if not plan.bindings.mutates and not plan.missing_core_secrets:
            return {"state": "bound", "changed": False}
        use_case.apply(request, plan)
        return {"state": "bound", "changed": True}

    def bind(self, *, dry_run: bool = False) -> dict[str, Any]:
        """Materialize public projections and one complete, CAS-checked Scribe generation."""
        with nullcontext() if dry_run else LifecycleLock():
            state = self._load()
            if dry_run:
                from lychd.system.services.scribe.facade import ScribeService

                request = self.bind_request()
                plan = ScribeService().plan_reconcile_all(request.manifests, plain_units=request.plain_unit_mapping())
                return {"state": "prepared", "changed": plan.mutates, "dry_run": True}
            return self._bind(state)

    def _catalog(self, state: NativeState, routes: tuple[Any, ...]) -> None:
        import stat

        path = self.runtime_root / "catalog.json"
        payload = (
            json.dumps(
                {
                    "schema": "lychd.tether.catalog",
                    "version": 1,
                    "installation_epoch": state.snapshot.installation_epoch,
                    "routes": [route.model_dump(mode="json") for route in routes],
                },
                sort_keys=True,
            )
            + "\n"
        ).encode()
        if not self.runtime_root.exists():
            return
        descriptor = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        temporary = ".catalog-" + uuid4().hex
        try:
            if os.path.lexists(path):
                current = os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
                if (
                    not stat.S_ISREG(current.st_mode)
                    or current.st_uid != os.getuid()
                    or current.st_nlink != 1
                    or stat.S_IMODE(current.st_mode) != _PRIVATE_FILE_MODE
                ):
                    msg = "Unsafe boot-local route catalog"
                    raise TetherError(msg)
                source = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
                try:
                    pinned = os.fstat(source)
                    if (pinned.st_dev, pinned.st_ino) != (current.st_dev, current.st_ino):
                        msg = "Boot-local route catalog changed during observation"
                        raise TetherError(msg)
                    if os.read(source, len(payload) + 1) == payload:
                        return
                finally:
                    os.close(source)
            target = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=descriptor)
            try:
                with os.fdopen(target, "wb", closefd=False) as output:
                    output.write(payload)
                    output.flush()
                    os.fsync(target)
            finally:
                os.close(target)
            os.replace(temporary, path.name, src_dir_fd=descriptor, dst_dir_fd=descriptor)
            os.fsync(descriptor)
        finally:
            with suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=descriptor)
            os.close(descriptor)

    def _require_core(self) -> None:
        """Bind the ordinary Core's actual image and process to its owned invocation."""
        settings, _extensions, _runes, _rune = self._declared()
        self.host.require_core(settings.server.web.image)

    @staticmethod
    def _pod_name(config: Any) -> str:
        return "-".join(config.name.split("-")[:3])

    def _require_pending(self, pending: dict[str, Any] | None, config: Any) -> dict[str, Any]:
        if (
            pending is None
            or pending.get("boot_id") != Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            or pending.get("policy_digest") != config.payload["policy_digest"]
            or pending.get("network_id") != config.network_id
            or self.host.unit_incarnation(config.name + ".service")["InvocationID"]
            == pending.get("previous_invocation_id")
        ):
            message = "The pending Tether launch lacks exact current invocation authority"
            raise TetherError(message)
        return pending

    def _retain_role(self, state: NativeState, config: Any) -> NativeState:
        """Seal role and Pod together before clearing recoverable launch authority."""
        identity = self.host.capture(config, state.image)
        pod = self.host.capture_pod(self._pod_name(config))
        old = state.incarnations.get(config.name)
        previous_pod = state.pods.get(config.network_id)
        pending = state.launches.get(config.name)
        if identity["pod_id"] != pod["pod_id"] or identity["netns"] != pod["netns"]:
            message = "Tether role does not inhabit its exact owned Pod namespace"
            raise TetherError(message)
        if pending is not None or old is None:
            pending = self._require_pending(pending, config)
        if (
            old is not None
            and identity["container_id"] != old["container_id"]
            and (not self.host.cgroup_empty(old["cgroup"]) or identity["invocation_id"] == old["invocation_id"])
        ):
            message = "A previous Tether incarnation is still live or replacement lacks a new owned invocation"
            raise TetherError(message)
        if previous_pod is None:
            pending = self._require_pending(pending, config)
            if pod["invocation_id"] == pending.get("previous_pod_invocation_id"):
                message = "The pending launch did not create a new owned Pod invocation"
                raise TetherError(message)
        elif pod["pod_id"] != previous_pod["pod_id"]:
            self._require_pending(pending, config)
            if (
                not self.host.cgroup_empty(previous_pod["infra_cgroup"])
                or pod["invocation_id"] == previous_pod["invocation_id"]
            ):
                message = "A replaced Tether Pod still has a live previous incarnation"
                raise TetherError(message)
        return state.model_copy(
            update={
                "incarnations": {**state.incarnations, config.name: identity},
                "pods": {**state.pods, config.network_id: pod},
                "launches": {name: value for name, value in state.launches.items() if name != config.name},
            }
        )

    def _preflight_role(self, state: NativeState, config: Any) -> None:
        retained = state.incarnations.get(config.name)
        if self.host.exists("container", config.name):
            row = self.host.row("container", config.name)
            if row.get("State", {}).get("Running") is True:
                self._retain_role(state, config)
            elif retained is None or row.get("Id") != retained["container_id"]:
                message = "An existing stopped Tether container has no retained authority"
                raise TetherError(message)
        elif retained is not None and not self.host.cgroup_empty(retained["cgroup"]):
            message = "Previous Tether role closure is uncertain"
            raise TetherError(message)

    def _preflight_activation(
        self, state: NativeState, deployment: TetherDeployment, selected: tuple[str, ...]
    ) -> None:
        """Prove existing names before enabling any role's durable fence."""
        for network in deployment.networks:
            if network.id not in selected:
                continue
            pod_name = network.pod_unit.removesuffix("-pod.service")
            previous = state.pods.get(network.id)
            if self.host.exists("pod", pod_name):
                row = self.host.row("pod", pod_name)
                if previous is None or row.get("Id") != previous["pod_id"]:
                    wg = next(
                        item
                        for item in deployment.runtime_configs
                        if item.network_id == network.id and item.role == "wireguard"
                    )
                    self._require_pending(state.launches.get(wg.name), wg)
                    self._retain_role(state, wg)
            elif previous is not None and not self.host.cgroup_empty(previous["infra_cgroup"]):
                message = "Previous Tether Pod closure is uncertain"
                raise TetherError(message)
            for config in (item for item in deployment.runtime_configs if item.network_id == network.id):
                self._preflight_role(state, config)

    def _start_role(self, state: NativeState, config: Any) -> tuple[NativeState, bool]:
        """Recover only a manager-proven launch; start stopped owned containers too."""
        changed = False
        exists = self.host.exists("container", config.name)
        retained = state.incarnations.get(config.name)
        if exists:
            row = self.host.row("container", config.name)
            if row.get("State", {}).get("Running") is True:
                state = self._retain_role(state, config)
                self._save(state)
                return state, False
            if retained is None or row.get("Id") != retained["container_id"]:
                message = "A stopped Tether container has no exact retained authority"
                raise TetherError(message)
        if retained is not None and not self.host.cgroup_empty(retained["cgroup"]):
            message = "The previous Tether incarnation still has descendants"
            raise TetherError(message)
        unit = self.host.unit_incarnation(config.name + ".service")
        launch = {
            "previous_invocation_id": unit["InvocationID"],
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "policy_digest": config.payload["policy_digest"],
            "network_id": config.network_id,
            "previous_pod_invocation_id": self.host.unit_incarnation(self._pod_name(config) + "-pod.service")[
                "InvocationID"
            ],
        }
        state = state.model_copy(update={"launches": {**state.launches, config.name: launch}})
        self._save(state)
        try:
            self.host.command("systemctl", "--user", "start", config.name + ".service")
            changed = True
        finally:
            if self.host.exists("container", config.name):
                state = self._retain_role(state, config)
                self._save(state)
        return state, changed

    def _await_policy(self, config: Any, seconds: float = 15.0) -> None:
        deadline = time.monotonic() + seconds
        while True:
            try:
                self.host.observe(config)
            except TetherError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.1)
            else:
                return

    def _activate_network(
        self, state: NativeState, deployment: TetherDeployment, network: Any
    ) -> tuple[NativeState, bool]:
        pod_name = network.pod_unit.removesuffix("-pod.service")
        previous = state.pods.get(network.id)
        if self.host.exists("pod", pod_name):
            pod = self.host.row("pod", pod_name)
            if previous is None or pod.get("Id") != previous["pod_id"]:
                wg = next(
                    item
                    for item in deployment.runtime_configs
                    if item.network_id == network.id and item.role == "wireguard"
                )
                # This proves pending boot/policy and old infra closure before adoption.
                self._require_pending(state.launches.get(wg.name), wg)
                state = self._retain_role(state, wg)
                self._save(state)
        elif previous is not None and not self.host.cgroup_empty(previous["infra_cgroup"]):
            message = "The previous Tether Pod still has live descendants"
            raise TetherError(message)
        changed = False
        for config in (item for item in deployment.runtime_configs if item.network_id == network.id):
            state, role_changed = self._start_role(state, config)
            changed = role_changed or changed
            self._await_policy(config)
        return state, changed

    def _activate(self, state: NativeState, selected: tuple[str, ...]) -> dict[str, Any]:
        """Reconcile selected incarnations without restarting unrelated networks."""
        self._require_core()
        if any(row.get("status") != "complete" for row in state.revocations.values()):
            message = "Finish pending revocation before activating networks"
            raise TetherError(message)
        deployment = self._projection(state)
        self._attest_keys(state, deployment)
        self._bound(self.bind_request())
        self.host.runtime_directories(
            self.runtime_root, tuple(network.runtime_directory for network in deployment.networks)
        )
        if not set(selected) <= {network.id for network in deployment.networks}:
            message = "Activation refers to a disabled or undeclared network"
            raise TetherError(message)
        self._preflight_activation(state, deployment, selected)
        updated = state.model_copy(update={"active": tuple(sorted(set(state.active) | set(selected)))})
        self._save(updated)
        self._materialize(updated)
        changed = state.active != updated.active
        for network in deployment.networks:
            if network.id in selected:
                updated, network_changed = self._activate_network(updated, deployment, network)
                changed = network_changed or changed
        for config in deployment.runtime_configs:
            if config.network_id in updated.active:
                self.host.observe(config)
        routes = tuple(route for route in deployment.routes if route.selection.attachment_id in updated.active)
        self._catalog(updated, routes)
        return {"state": "active", "changed": changed}

    def activate(self, *, dry_run: bool = False) -> dict[str, Any]:
        """Activate only admitted networks after the ordinary Core bootstrap."""
        with nullcontext() if dry_run else LifecycleLock():
            state = self._load()
            deployment = self._projection(state)
            selected = tuple(network.id for network in deployment.networks)
            if dry_run:
                self._attest_keys(state, deployment)
                self._bound(self.bind_request())
                return {"state": "bound", "changed": state.active != tuple(sorted(selected)), "dry_run": True}
            return self._activate(state, selected)

    def resume(self) -> dict[str, Any]:
        """Boot helper: revive previously granted networks; initial Core start grants none."""
        state = self._load()
        if not state.active:
            return {"state": "bound", "changed": False}
        with LifecycleLock():
            state = self._load()
            return self._activate(state, state.active)

    def inspect(self) -> dict[str, Any]:
        """Report effective ownership and live acknowledgements without secret values."""
        state = self._load()
        deployment = self._projection(state)
        self._attest_keys(state, deployment)
        bound = False
        try:
            self._bound(self.bind_request())
            bound = True
        except TetherError:
            pass
        networks: list[dict[str, Any]] = []
        active: set[str] = set()
        for network in deployment.networks:
            observed = bound and network.id in state.active
            if observed:
                for config in (item for item in deployment.runtime_configs if item.network_id == network.id):
                    retained = state.incarnations.get(config.name)
                    if retained is None or self.host.capture(config, state.image) != retained:
                        observed = False
                        break
                    self.host.observe(config)
            if observed:
                active.add(network.id)
            networks.append(
                {
                    "id": network.id,
                    "generation": network.generation,
                    "policy_digest": network.policy_digest,
                    "unit_names": [network.pod_unit, *network.unit_names],
                    "active": observed,
                }
            )
        return {
            "schema": "lychd.tether.inspection",
            "version": 1,
            "state": "active"
            if bound and len(active) == len(deployment.networks)
            else "bound"
            if bound
            else "prepared",
            "installation_epoch": state.snapshot.installation_epoch,
            "image": state.intent.rune.quadlet.image,
            "required_secrets": list(deployment.required_secrets),
            "owned_secrets": list(self._keys(state).owned_references()),
            "unit_names": [unit for network in deployment.networks for unit in (network.pod_unit, *network.unit_names)],
            "known_paths": [str(path) for path in self.custody.known_paths()],
            "networks": networks,
            "routes": [
                route.model_dump(mode="json") for route in deployment.routes if route.selection.attachment_id in active
            ],
        }

    def import_key(self, secret_ref: str, path: Path, *, dry_run: bool = False) -> dict[str, Any]:
        """Import one declared client key from a private file; never replace a key."""
        with nullcontext() if dry_run else LifecycleLock():
            state = self._load()
            purpose = self._references(state).get(secret_ref)
            if purpose not in {"wireguard", "preshared"}:
                msg = "Only a declared WireGuard client or preshared key can be imported"
                raise TetherError(msg)
            if dry_run:
                return {"state": "prepared", "changed": False, "dry_run": True}
            admitted_purpose = cast("Literal['wireguard', 'preshared']", purpose)
            identity = self._keys(state).import_key(secret_ref, path, admitted_purpose)
            return {"state": "prepared", "reference": identity["reference"], "public_key": identity["public_key"]}

    def _preflight_hot_peer(
        self, before: NativeState, after: NativeState, peer: OfferedPeer, previous: OfferedPeer | None
    ) -> None:
        """Allow only additive peers under an unchanged live offered namespace policy."""
        if previous is not None:
            message = "Stop the offered network before rotating an existing peer"
            raise TetherError(message)
        old, new = self._projection(before), self._projection(after)
        old_pods = tuple(row.model_dump(mode="json") for row in old.manifests if isinstance(row, QuadletPod))
        new_pods = tuple(row.model_dump(mode="json") for row in new.manifests if isinstance(row, QuadletPod))
        if old_pods != new_pods:
            message = "Stop the offered network before changing its Pod policy"
            raise TetherError(message)
        self._require_core()
        self._bound(self.bind_request(state_override=before))
        generated = peer.owner_access.ssh_host_key_ref if peer.owner_access else None
        keys = self._keys(after)
        keys.attest_many(reference for reference in new.required_secrets if reference != generated)

    def enroll(self, peer: OfferedPeer, *, dry_run: bool = False) -> dict[str, Any]:
        """Admit the next peer generation without disturbing unrelated attachments."""
        with nullcontext() if dry_run else LifecycleLock():
            state = self._load()
            offered = state.intent.rune.offered
            if offered is None:
                msg = "Peer admission requires an offered network"
                raise TetherError(msg)
            if any(row.get("status") != "complete" for row in state.revocations.values()):
                msg = "Finish pending revocation before changing admission"
                raise TetherError(msg)
            previous = next((row for row in state.snapshot.offered_peers if row.id == peer.id), None)
            if previous == peer:
                if offered.id in state.active and not dry_run:
                    rebound = self._bind(state)
                    resumed = self._activate(state, (offered.id,))
                    return {"state": "enrolled", "changed": rebound["changed"] or resumed["changed"]}
                return {"state": "enrolled", "changed": False}
            if not peer.enabled or peer.generation != (previous.generation + 1 if previous else 1):
                msg = "Peer admission requires the next exact enabled generation"
                raise TetherError(msg)
            peers = (*tuple(row for row in state.snapshot.offered_peers if row.id != peer.id), peer)
            snapshot = TetherSnapshot.model_validate({**state.snapshot.model_dump(), "offered_peers": peers})
            owners = self._key_ownership(state, self.effective_rune(state), peers)
            updated = state.model_copy(update={"snapshot": snapshot, "key_owners": owners})
            self._projection(updated)
            hot = offered.id in state.active
            if hot:
                self._preflight_hot_peer(state, updated, peer, previous)
            if dry_run:
                return {"state": "enrolled", "changed": True, "dry_run": True}
            # Reserve reference ownership without granting the peer before key creation.
            # An interrupted ensure must not free its new reference for another peer.
            self._save(state.model_copy(update={"key_owners": owners}))
            if peer.owner_access:
                self._keys(updated).ensure(peer.owner_access.ssh_host_key_ref, "ssh-host")
            self._save(updated)
            if hot:
                self._bind(updated)
                self._activate(updated, (offered.id,))
            else:
                self._materialize(updated)
            return {"state": "enrolled", "changed": True}

    def _validate_registered_topology(self, state: NativeState) -> TetherDeployment:
        """Compile every staged definition without authorizing any runtime effect."""
        rune = self.effective_rune(state)
        generations = {row.attachment_id: row.generation for row in state.snapshot.attachments}
        admissions = tuple(
            AttachmentAdmission(attachment_id=row.id, generation=generations.get(row.id, 1)) for row in rune.attachments
        )
        validation = state.model_copy(
            update={"snapshot": state.snapshot.model_copy(update={"attachments": admissions})}
        )
        return self._projection(validation)

    def _require_attachment_closed(self, state: NativeState, attachment_id: str, deployment: TetherDeployment) -> None:
        """Require a retired admitted generation and no current runtime or pending launch."""
        admission = next((row for row in state.snapshot.attachments if row.attachment_id == attachment_id), None)
        if admission is not None:
            journal = state.revocations.get(f"{attachment_id}:@:{admission.generation}")
            if admission.enabled or journal is None or journal.get("status") != "complete":
                message = "Revoke and reconcile the exact attachment generation before changing its definition"
                raise TetherError(message)
        names = {row.name for row in deployment.runtime_configs if row.network_id == attachment_id}
        if (
            attachment_id in state.active
            or attachment_id in state.pods
            or names.intersection(state.incarnations)
            or any(row.get("network_id") == attachment_id for row in state.launches.values())
        ):
            message = "Attachment replacement has retained runtime authority"
            raise TetherError(message)
        network = next(row for row in deployment.networks if row.id == attachment_id)
        if self.host.exists("pod", network.pod_unit.removesuffix("-pod.service")) or any(
            self.host.exists("container", name) for name in names
        ):
            message = "Attachment registration refuses an existing runtime incarnation"
            raise TetherError(message)

    def register_attachment(self, attachment: ImportedAttachment, *, dry_run: bool = False) -> dict[str, Any]:
        """Stage one closed public road definition without admitting or starting it."""
        attachment = ImportedAttachment.model_validate_json(attachment.model_dump_json())
        with nullcontext() if dry_run else LifecycleLock():
            state = self._load()
            rune = self.effective_rune(state)
            previous = next((row for row in rune.attachments if row.id == attachment.id), None)
            if previous == attachment:
                return {"state": "registered", "changed": False, "attachment_id": attachment.id}
            attachments = (*tuple(row for row in rune.attachments if row.id != attachment.id), attachment)
            topology = TetherRune.model_validate({**rune.model_dump(), "attachments": attachments})
            owners = self._key_ownership(state, topology, state.snapshot.offered_peers)
            updated = state.model_copy(update={"topology": topology, "key_owners": owners})
            deployment = self._validate_registered_topology(updated)
            self._require_attachment_closed(state, attachment.id, deployment)
            if dry_run:
                return {"state": "registered", "changed": True, "attachment_id": attachment.id, "dry_run": True}
            self._save(updated)
            return {"state": "registered", "changed": True, "attachment_id": attachment.id}

    def admit(self, attachment_id: str, generation: int, *, dry_run: bool = False) -> dict[str, Any]:
        """Admit a declared attachment generation; bind and activation remain explicit."""
        with nullcontext() if dry_run else LifecycleLock():
            state = self._load()
            if type(generation) is not int or generation < 1:
                msg = "Attachment generation must be a positive integer"
                raise TetherError(msg)
            if not any(row.id == attachment_id for row in self.effective_rune(state).attachments):
                msg = "Attachment is not registered in managed Tether topology"
                raise TetherError(msg)
            if any(row.get("status") != "complete" for row in state.revocations.values()):
                msg = "Finish pending revocation before changing admission"
                raise TetherError(msg)
            previous = next((row for row in state.snapshot.attachments if row.attachment_id == attachment_id), None)
            if previous is not None and previous.enabled and previous.generation == generation:
                return {"state": "admitted", "changed": False}
            if attachment_id in state.active or (previous is not None and previous.enabled):
                msg = "Revoke the current attachment before changing its generation"
                raise TetherError(msg)
            if generation != (previous.generation + 1 if previous else 1):
                msg = "Attachment admission requires the next exact generation"
                raise TetherError(msg)
            admission = AttachmentAdmission(attachment_id=attachment_id, generation=generation)
            attachments = (
                *tuple(row for row in state.snapshot.attachments if row.attachment_id != attachment_id),
                admission,
            )
            snapshot = TetherSnapshot.model_validate({**state.snapshot.model_dump(), "attachments": attachments})
            updated = state.model_copy(update={"snapshot": snapshot})
            self._projection(updated)
            if dry_run:
                return {"state": "admitted", "changed": True, "dry_run": True}
            self._save(updated)
            self._materialize(updated)
            return {"state": "admitted", "changed": True}

    @staticmethod
    def _revocation_complete(state: NativeState, journal: dict[str, Any]) -> bool:
        """Distinguish a completed withdrawal from a later offered-network regrant."""
        if journal.get("status") != "complete":
            return False
        offered = state.intent.rune.offered
        offered_regranted = (
            journal["peer_id"] is None
            and offered is not None
            and offered.id == journal["network_id"]
            and (offered.id in state.active or any(peer.enabled for peer in state.snapshot.offered_peers))
        )
        return not offered_regranted

    @staticmethod
    def _withdraw_peer(state: NativeState, network_id: str, peer_id: str, generation: str) -> TetherSnapshot:
        """Validate exact peer generation and retain its disabled tombstone."""
        offered = state.intent.rune.offered
        if offered is None or offered.id != network_id:
            message = "Peer revocation requires the offered network"
            raise TetherError(message)
        peer = next((row for row in state.snapshot.offered_peers if row.id == peer_id), None)
        if peer is None or str(peer.generation) != generation:
            message = "Peer generation is stale or absent"
            raise TetherError(message)
        peers = tuple(
            row.model_copy(update={"enabled": False}) if row.id == peer_id else row
            for row in state.snapshot.offered_peers
        )
        return TetherSnapshot.model_validate({**state.snapshot.model_dump(), "offered_peers": peers})

    @staticmethod
    def _withdraw_network(state: NativeState, network_id: str) -> TetherSnapshot:
        """Disable exactly the selected offered network or imported attachment."""
        offered = state.intent.rune.offered
        values = state.snapshot.model_dump()
        if offered is not None and offered.id == network_id:
            values["offered_peers"] = tuple(
                row.model_copy(update={"enabled": False}) for row in state.snapshot.offered_peers
            )
        else:
            values["attachments"] = tuple(
                row.model_copy(update={"enabled": False}) if row.attachment_id == network_id else row
                for row in state.snapshot.attachments
            )
        return TetherSnapshot.model_validate(values)

    def _begin_revocation(
        self, state: NativeState, operation: str, network_id: str, peer_id: str | None, generation: str
    ) -> NativeState:
        """Build a validated withdrawal and its durable recovery material without effects."""
        deployment = self._retained_projection(state)
        network = next((row for row in deployment.networks if row.id == network_id), None)
        if network is None:
            message = "Unknown or retired Tether network generation"
            raise TetherError(message)
        active = state.active
        if peer_id is not None:
            snapshot = self._withdraw_peer(state, network_id, peer_id, generation)
        else:
            if str(network.generation) != generation:
                message = "Network generation is stale"
                raise TetherError(message)
            snapshot = self._withdraw_network(state, network_id)
            active = tuple(row for row in active if row != network_id)
        offered = state.intent.rune.offered
        previous = state.snapshot.model_copy(
            update={
                "offered_peers": state.snapshot.offered_peers if offered and offered.id == network_id else (),
                "attachments": tuple(row for row in state.snapshot.attachments if row.attachment_id == network_id),
            }
        )
        target_names = {
            row.name
            for row in deployment.runtime_configs
            if row.network_id == network_id
            and (peer_id is None or row.role != "owner-ssh" or row.payload.get("peer_id") == peer_id)
        }
        retained = {name: value for name, value in state.incarnations.items() if name in target_names}
        journals = {
            key: row
            for key, row in state.revocations.items()
            if row["network_id"] != network_id or row["peer_id"] != peer_id or row["status"] != "complete"
        }
        journal = {
            "status": "pending",
            "network_id": network_id,
            "peer_id": peer_id,
            "generation": generation,
            "previous_snapshot": previous.model_dump(mode="json"),
            "previous_active": [network_id] if network_id in state.active else [],
            "incarnations": retained,
            "launches": {name: value for name, value in state.launches.items() if name in target_names},
            "pod": state.pods.get(network_id),
            "closed": [],
        }
        return state.model_copy(
            update={"snapshot": snapshot, "active": active, "revocations": {**journals, operation: journal}}
        )

    @staticmethod
    def _revocation_before(state: NativeState, journal: dict[str, Any]) -> NativeState:
        """Recover the old projection even when its imported attachment is now disabled."""
        snapshot = TetherSnapshot.model_validate_json(canonical_bytes(journal["previous_snapshot"]))
        return state.model_copy(
            update={
                "snapshot": snapshot,
                "active": tuple(journal["previous_active"]),
                "incarnations": journal["incarnations"],
            }
        )

    def _revocation_fence(self, state: NativeState, configs: tuple[Any, ...]) -> bool:
        """Publish every target fence and withdraw catalog rows, attempting each independently."""
        failed = False
        for config in configs:
            fence: dict[str, object] = {
                **config.fences,
                "enabled": config.network_id in state.active,
                "peers": [
                    {"id": row.id, "generation": row.generation, "enabled": row.enabled}
                    for row in state.snapshot.offered_peers
                ],
            }
            try:
                self.custody.publish(Path("runtime") / config.name / "fences.json", fence, public=True)
            except (OSError, TetherError):
                failed = True
        try:
            current = self._retained_projection(state)
            self._catalog(state, tuple(row for row in current.routes if row.selection.attachment_id in state.active))
        except (OSError, TetherError):
            failed = True
        return failed

    def _stop_revoked_role(self, config: Any, retained: dict[str, Any] | None) -> None:
        """Refuse foreign incarnations; exact retained units close even after container exit."""
        if retained is not None:
            self.host.stop(retained)
        else:
            self.host.stop_unretained(config.name)

    def _revocation_close_roles(
        self, state: NativeState, operation: str, configs: tuple[Any, ...]
    ) -> tuple[NativeState, bool]:
        """Close target role cgroups and checkpoint each outcome for independent retries."""
        journal: dict[str, Any] = state.revocations[operation]
        peer_id = journal["peer_id"]
        incarnations = dict(state.incarnations)
        launches = dict(state.launches)
        closed = set(journal["closed"])
        failed = False
        for config in reversed(configs):
            must_stop = peer_id is None or (config.role == "owner-ssh" and config.payload.get("peer_id") == peer_id)
            if not must_stop:
                continue
            try:
                self._stop_revoked_role(config, journal["incarnations"].get(config.name))
                incarnations.pop(config.name, None)
                launches.pop(config.name, None)
                closed.add(config.name)
            except (OSError, TetherError):
                failed = True
            journal = {**journal, "closed": sorted(closed)}
            state = state.model_copy(
                update={
                    "incarnations": dict(incarnations),
                    "launches": dict(launches),
                    "revocations": {**state.revocations, operation: journal},
                }
            )
            self._save(state)
        return state, failed

    def _recover_revocation_pod(self, state: NativeState, journal: dict[str, Any]) -> dict[str, Any] | None:
        """Recover only the owned Pod invocation created by a journaled failed launch."""
        before = self._revocation_before(state, journal)
        config = next(
            row
            for row in self._retained_projection(before).runtime_configs
            if row.network_id == journal["network_id"] and row.role == "wireguard"
        )
        pod_name = self._pod_name(config)
        if not self.host.exists("pod", pod_name):
            return None
        pending = journal.get("launches", {}).get(config.name)
        if (
            pending is None
            or pending.get("boot_id") != Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            or pending.get("policy_digest") != config.payload["policy_digest"]
            or pending.get("network_id") != config.network_id
            or not isinstance(pending.get("previous_pod_invocation_id"), str)
        ):
            message = "Unretained Tether Pod lacks exact pending-launch authority"
            raise TetherError(message)
        pod = self.host.capture_pod(pod_name)
        if pod["invocation_id"] == pending.get("previous_pod_invocation_id"):
            message = "Pending Tether launch did not create the observed Pod invocation"
            raise TetherError(message)
        return pod

    def _revocation_close_pod(self, state: NativeState, operation: str) -> tuple[NativeState, bool]:
        """Retire only the selected whole-network Pod after attempting all role closures."""
        journal: dict[str, Any] = state.revocations[operation]
        if journal["peer_id"] is not None:
            return state, False
        try:
            if journal.get("pod") is None:
                recovered = self._recover_revocation_pod(state, journal)
                if recovered is None:
                    return state, False
                journal = {**journal, "pod": recovered}
                state = state.model_copy(update={"revocations": {**state.revocations, operation: journal}})
                self._save(state)
            self.host.stop_pod(journal["pod"])
            pods = dict(state.pods)
            pods.pop(journal["network_id"], None)
            state = state.model_copy(update={"pods": pods})
            self._save(state)
        except (OSError, TetherError):
            return state, True
        return state, False

    @staticmethod
    def _require_peer_closed(config: Any, observed: dict[str, Any], peer: OfferedPeer) -> None:
        """Require WireGuard removal and zero established streams for this peer."""
        if config.role == "wireguard" and peer.public_key in observed.get("peer_public_keys", [peer.public_key]):
            message = "WireGuard peer closure remains incomplete"
            raise TetherError(message)
        if config.role == "offered-relay" and observed.get("streams", {}).get(peer.id, 0) != 0:
            message = "Offered peer streams remain active"
            raise TetherError(message)

    def _revocation_acknowledge(self, state: NativeState, before: NativeState, operation: str) -> None:
        """Prove peer closure from retained authority without depending on fresh grants."""
        journal = state.revocations[operation]
        peer_id, network_id = journal["peer_id"], journal["network_id"]
        if peer_id is None or network_id not in state.active:
            return
        peer = next(row for row in before.snapshot.offered_peers if row.id == peer_id)
        for config in self._retained_projection(state).runtime_configs:
            if config.network_id != network_id or config.role == "owner-ssh":
                continue
            retained = before.incarnations.get(config.name)
            if retained is None or self.host.capture(config, before.image) != retained:
                message = "Peer closure requires its exact retained network incarnation"
                raise TetherError(message)
            deadline = time.monotonic() + 5
            while True:
                try:
                    self._observe_revoked_peer(config, peer)
                    break
                except TetherError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.1)

    def revoke(
        self, network_id: str, peer_id: str | None, expected_generation: str, *, dry_run: bool = False
    ) -> dict[str, Any]:
        """Journal withdrawal, attempt independent closure phases, and retain failed work."""
        with nullcontext() if dry_run else LifecycleLock():
            state = self._load_retained()
            operation = f"{network_id}:{peer_id or '@'}:{expected_generation}"
            journal = state.revocations.get(operation)
            if journal is not None and self._revocation_complete(state, journal):
                return {"state": "revoked", "changed": False, "physical_closure": True, "bindings_reconciled": True}
            if journal is not None and journal.get("status") == "closed":
                if dry_run:
                    return {"state": "revoked", "changed": True, "dry_run": True}
                reconciled = self._reconcile_revocation(state, operation)
                return {
                    "state": "revoked",
                    "changed": reconciled,
                    "physical_closure": True,
                    "bindings_reconciled": reconciled,
                }
            recovering = journal is not None and journal.get("status") != "complete"
            updated = (
                state
                if recovering
                else self._begin_revocation(state, operation, network_id, peer_id, expected_generation)
            )
            before = self._revocation_before(updated, updated.revocations[operation])
            if dry_run:
                return {"state": "revoked", "changed": True, "dry_run": True}
            self._save(updated)
            configs = tuple(
                row for row in self._retained_projection(before).runtime_configs if row.network_id == network_id
            )
            fence_failed = self._revocation_fence(updated, configs)
            updated, roles_failed = self._revocation_close_roles(updated, operation, configs)
            updated, pod_failed = self._revocation_close_pod(updated, operation)
            failed = fence_failed or roles_failed or pod_failed
            if not failed:
                try:
                    self._revocation_acknowledge(updated, before, operation)
                except (OSError, TetherError):
                    failed = True
            if failed:
                message = "Tether revocation remains pending; retry the same target and generation"
                raise TetherError(message)
            reconciled = self._reconcile_revocation(updated, operation)
            return {"state": "revoked", "changed": True, "physical_closure": True, "bindings_reconciled": reconciled}

    def _observe_revoked_peer(self, config: Any, peer: OfferedPeer) -> None:
        """Observe the custody-owned published policy during independent pending withdrawals."""
        payload = self.custody.read(f"runtime/{config.name}/config.json")
        keys = ("role", "network_id", "installation_epoch", "generation")
        if payload is None or any(payload.get(key) != config.payload[key] for key in keys):
            message = "Peer closure lacks an owned current role configuration"
            raise TetherError(message)
        published = replace(config, payload=payload)
        self._require_peer_closed(published, self.host.observe(published), peer)

    def _reconcile_revocation(self, state: NativeState, operation: str) -> bool:
        """Persist physical closure before attempting strict complete-fileset reconciliation."""
        previous = state.revocations[operation]
        journal = {
            "status": "closed",
            "bindings_pending": True,
            "network_id": previous["network_id"],
            "peer_id": previous["peer_id"],
            "generation": previous["generation"],
        }
        state = state.model_copy(update={"revocations": {**state.revocations, operation: journal}})
        self._save(state)
        try:
            self._bind(state)
        except (OSError, RuntimeError, ValueError):
            return False
        journal = {**journal, "status": "complete", "bindings_pending": False}
        state = state.model_copy(update={"revocations": {**state.revocations, operation: journal}})
        self._save(state)
        return True
