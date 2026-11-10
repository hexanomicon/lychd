"""No-follow, descriptor-bound, durable custody for fixed Tether leaves.

Creation records are written only after absent-only creation. An interrupted
creation without its receipt refuses subsequent adoption.
"""

from __future__ import annotations

import json
import os
import stat
from contextlib import contextmanager, suppress
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from lychd.domain.tether.models import CompiledTetherPlan, TetherPeerIntent, validate_peer
from lychd.system.services.tether.models import (
    EnrollRequest,
    ImagePreparationBundle,
    InitialPreparationBundle,
    OperationReceipt,
    PreparationReceipt,
    PreparationSelection,
    PrepareImageRequest,
    SelectedPreparation,
    TetherError,
    digest,
    require_image_only_change,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from pydantic import BaseModel

_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_MAX_BYTES = 131072
_DIRS = ("public", "wireguard", "forwarder", "private", "operations", "revocations", "generations")


class TetherCustody:
    """Use only compiler-fixed roles beneath init-attested dedicated roots."""

    def __init__(self, codex_root: Path, crypt_root: Path) -> None:
        """Bind fixed native roles to trusted custody and process dependencies."""
        self.codex_root = codex_root
        self.crypt_root = crypt_root
        self.directories = {
            "public": codex_root / "tether",
            "wireguard": codex_root / "tether/wireguard",
            "forwarder": codex_root / "tether/forwarder",
            "private": crypt_root / "tether",
            "operations": crypt_root / "tether/operations",
            "revocations": crypt_root / "tether/revocations",
            "generations": crypt_root / "tether/generations",
        }

    @contextmanager
    def _directory(self, path: Path) -> Generator[int]:
        if not path.is_absolute() or ".." in path.parts:
            msg = "Tether custody requires canonical absolute roots"
            raise TetherError(msg)
        descriptor = os.open("/", _FLAGS)
        try:
            for part in path.parts[1:]:
                child = os.open(part, _FLAGS, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            metadata = os.fstat(descriptor)
            if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != (
                0o755 if path in (self.directories["wireguard"], self.directories["forwarder"]) else 0o700
            ):
                msg = "Tether custody directory must be operator-owned mode 0700"
                raise TetherError(msg)
            yield descriptor
        finally:
            os.close(descriptor)

    @staticmethod
    def _identity(descriptor: int) -> list[int]:
        metadata = os.fstat(descriptor)
        return [metadata.st_dev, metadata.st_ino]

    def initialize(self) -> None:
        """Create absent leaves once; existing leaves require exact creation receipt."""
        if os.path.lexists(self.directories["private"]):
            self.attest()
            return
        if os.path.lexists(self.directories["public"]):
            msg = "Unreceipted Tether public custody exists; refusing adoption"
            raise TetherError(msg)
        identities: dict[str, list[int]] = {}
        for role in _DIRS:
            path = self.directories[role]
            with self._directory(path.parent) as parent:
                mode = 0o755 if role in {"wireguard", "forwarder"} else 0o700
                os.mkdir(path.name, mode, dir_fd=parent)
                child = os.open(path.name, _FLAGS, dir_fd=parent)
                try:
                    os.fchmod(child, mode)
                    os.fsync(child)
                finally:
                    os.close(child)
                os.fsync(parent)
            with self._directory(path) as descriptor:
                os.fchmod(descriptor, 0o755 if role in {"wireguard", "forwarder"} else 0o700)
                identities[role] = self._identity(descriptor)
        for role, path in (("codex", self.codex_root), ("crypt", self.crypt_root)):
            with self._directory(path) as descriptor:
                os.fchmod(descriptor, 0o755 if role in {"wireguard", "forwarder"} else 0o700)
                identities[role] = self._identity(descriptor)
        self._write("private", ".custody.json", json.dumps(identities).encode(), immutable=True)
        self.attest()

    def attest(self) -> None:
        """Refuse replaced directories even when their names and modes match."""
        raw = self._read("private", ".custody.json")
        if raw is None:
            msg = "Tether creation receipt is absent; preserve uncertain custody"
            raise TetherError(msg)
        expected = cast("dict[str, list[int]]", json.loads(raw))
        paths = {**self.directories, "codex": self.codex_root, "crypt": self.crypt_root}
        if set(expected) != set(paths):
            msg = "Tether custody receipt has an unknown or missing role"
            raise TetherError(msg)
        for role, path in paths.items():
            with self._directory(path) as descriptor:
                if expected[role] != self._identity(descriptor):
                    msg = "Tether custody identity changed"
                    raise TetherError(msg)

    @staticmethod
    def _name(name: str) -> None:
        if not name or name in {".", ".."} or "/" in name or "\x00" in name:
            msg = "Invalid internal Tether record name"
            raise TetherError(msg)

    def _read(self, role: str, name: str) -> bytes | None:
        self._name(name)
        with self._directory(self.directories[role]) as parent:
            try:
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            except FileNotFoundError:
                return None
            try:
                metadata = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) != (0o644 if role in {"wireguard", "forwarder"} else 0o600)
                    or metadata.st_nlink != 1
                ):
                    msg = "Unsafe Tether record metadata"
                    raise TetherError(msg)
                content = os.read(descriptor, _MAX_BYTES + 1)
                if len(content) > _MAX_BYTES:
                    msg = "Oversized Tether record"
                    raise TetherError(msg)
                return content
            finally:
                os.close(descriptor)

    def read(self, role: str, name: str) -> bytes | None:
        """Read bounded bytes after full custody revalidation."""
        self.attest()
        return self._read(role, name)

    def write(self, role: str, name: str, value: BaseModel, *, immutable: bool = False) -> None:
        """Publish one typed record, durably and atomically."""
        self.publish(role, name, value.model_dump_json().encode(), immutable=immutable)

    def publish(self, role: str, name: str, content: bytes, *, immutable: bool = False) -> None:
        """Publish a compiler-owned public projection or typed journal record."""
        self.attest()
        self._write(role, name, content, immutable=immutable)

    def _write(self, role: str, name: str, content: bytes, *, immutable: bool) -> None:
        self._name(name)
        if len(content) > _MAX_BYTES:
            msg = "Oversized Tether publication"
            raise TetherError(msg)
        previous = self._read(role, name)
        if previous is not None and immutable:
            if previous != content:
                msg = "Immutable Tether evidence disagrees with retry"
                raise TetherError(msg)
            return
        temporary = f".staging-{uuid4()}"
        with self._directory(self.directories[role]) as parent:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o644 if role in {"wireguard", "forwarder"} else 0o600,
                dir_fd=parent,
            )
            try:
                os.fchmod(descriptor, 0o644 if role in {"wireguard", "forwarder"} else 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                if immutable:
                    os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                    os.unlink(temporary, dir_fd=parent)
                else:
                    os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                with suppress(FileNotFoundError):
                    os.unlink(temporary, dir_fd=parent)

    def names(self, role: str) -> tuple[str, ...]:
        """List names only through the fixed attested directory descriptor."""
        self.attest()
        with self._directory(self.directories[role]) as parent:
            return tuple(sorted(os.listdir(parent)))  # noqa: PTH208 - descriptor-bound inventory must not reopen a pathname

    def select_preparation(self, expected: bytes | None, selection: PreparationSelection) -> None:
        """Durably CAS the fixed selector while the native owner holds LifecycleLock."""
        self.attest()
        if self._read("private", "current-preparation.json") != expected:
            msg = "Preparation selector changed before its exact atomic commit"
            raise TetherError(msg)
        self._write("private", "current-preparation.json", selection.model_dump_json().encode(), immutable=False)

    def clear_latch(self, expected: bytes) -> None:
        """Remove only the active latch after exact cold reenrollment validation."""
        self.attest()
        if self._read("private", "closed.json") != expected:
            msg = "Closure latch changed before cold reenrollment"
            raise TetherError(msg)
        with self._directory(self.directories["private"]) as parent:
            os.unlink("closed.json", dir_fd=parent)
            os.fsync(parent)


class PreparationStore:
    """Resolve the selected preparation and its immutable image-only ancestry."""

    _SELECTOR = "current-preparation.json"
    _BUNDLE_PREFIX = "image-preparation-"

    def __init__(self, custody: TetherCustody) -> None:
        """Use the same fixed, attested private leaf as native operation evidence."""
        self.custody = custody

    def _legacy(self) -> SelectedPreparation:
        plan_raw = self.custody.read("private", "plan.json")
        receipt_raw = self.custody.read("private", "preparation.json")
        if plan_raw is None or receipt_raw is None:
            msg = "Tether has no complete original preparation authority"
            raise TetherError(msg)
        plan = CompiledTetherPlan.model_validate_json(plan_raw)
        receipt = PreparationReceipt.model_validate_json(receipt_raw)
        self._require_pair(plan, receipt)
        bundle = InitialPreparationBundle(plan=plan, preparation=receipt)
        selection = PreparationSelection(
            installation_id=receipt.installation_id, operation_id=receipt.operation_id, bundle_digest=digest(bundle)
        )
        return SelectedPreparation(selection=selection, plan=plan, preparation=receipt)

    @staticmethod
    def _require_pair(plan: CompiledTetherPlan, receipt: PreparationReceipt) -> None:
        if receipt.installation_id != plan.envelope.installation_id or receipt.envelope_digest != plan.envelope_digest:
            msg = "Preparation does not match its exact retained envelope"
            raise TetherError(msg)
        if any(
            (reference.purpose, reference.name) != (identity.purpose, identity.name)
            for reference, identity in zip(plan.secret_requirements, receipt.secrets, strict=True)
        ):
            msg = "Preparation secret roles differ from their retained references"
            raise TetherError(msg)

    def _require_request(self, selection: PreparationSelection, bundle: ImagePreparationBundle) -> None:
        raw = self.custody.read("operations", f"{selection.operation_id}.json")
        if raw is None:
            msg = "Image preparation bundle lacks its exact native request journal"
            raise TetherError(msg)
        receipt = OperationReceipt.model_validate_json(raw)
        request = receipt.request
        if (
            not isinstance(request, PrepareImageRequest)
            or receipt.request_digest != digest(request)
            or bundle.request_digest != receipt.request_digest
            or request.operation_id != selection.operation_id
            or request.installation_id != selection.installation_id
            or request.envelope_digest != bundle.plan.envelope_digest
            or request.intent_digest != bundle.plan.envelope_digest
            or request.expected_preparation_digest != digest(bundle.parent_selection)
            or "image-cold-proven" not in receipt.stages
        ):
            msg = "Image preparation bundle differs from its correlated native request"
            raise TetherError(msg)

    def _require_consistent_completions(self, states: list[SelectedPreparation]) -> None:
        selected_operations = {state.selection.operation_id for state in states}
        for name in self.custody.names("private"):
            if not name.startswith(self._BUNDLE_PREFIX) or not name.endswith(".json"):
                continue
            operation_id = UUID(name.removeprefix(self._BUNDLE_PREFIX).removesuffix(".json"))
            if operation_id in selected_operations:
                continue
            raw = self.custody.read("operations", f"{operation_id}.json")
            if raw is None:
                continue
            receipt = OperationReceipt.model_validate_json(raw)
            if receipt.request_digest != digest(receipt.request) or not isinstance(
                receipt.request, PrepareImageRequest
            ):
                msg = "Unselected transition evidence has inconsistent operation identity"
                raise TetherError(msg)
            if receipt.complete or "image-selected" in receipt.stages:
                msg = "Completed image preparation is outside current selected ancestry"
                raise TetherError(msg)

    def history(self) -> tuple[SelectedPreparation, ...]:  # noqa: C901 - validate every immutable ancestry and commit predicate
        """Validate the entire selected ancestry; unselected bundles confer no authority."""
        raw = self.custody.read("private", self._SELECTOR)
        if raw is None:
            if any(name.startswith(self._BUNDLE_PREFIX) for name in self.custody.names("private")):
                msg = "Preparation selector is absent while transition evidence exists; preserve and reconcile"
                raise TetherError(msg)
            return (self._legacy(),)
        selection = PreparationSelection.model_validate_json(raw)
        states: list[SelectedPreparation] = []
        seen: set[str] = set()
        while True:
            identity = digest(selection)
            if identity in seen:
                msg = "Preparation ancestry contains a repeated selector"
                raise TetherError(msg)
            seen.add(identity)
            if selection.parent_preparation_digest is None:
                legacy = self._legacy()
                if selection != legacy.selection:
                    msg = "Initial preparation selector differs from immutable original evidence"
                    raise TetherError(msg)
                states.append(legacy)
                break
            bundle_raw = self.custody.read("private", f"{self._BUNDLE_PREFIX}{selection.operation_id}.json")
            if bundle_raw is None:
                msg = "Selected preparation bundle is absent"
                raise TetherError(msg)
            bundle = ImagePreparationBundle.model_validate_json(bundle_raw)
            self._require_pair(bundle.plan, bundle.preparation)
            if (
                digest(bundle) != selection.bundle_digest
                or bundle.preparation.operation_id != selection.operation_id
                or bundle.preparation.installation_id != selection.installation_id
                or bundle.parent_selection.installation_id != selection.installation_id
                or digest(bundle.parent_selection) != selection.parent_preparation_digest
            ):
                msg = "Preparation selector or ancestry link differs from its immutable bundle"
                raise TetherError(msg)
            self._require_request(selection, bundle)
            states.append(SelectedPreparation(selection=selection, plan=bundle.plan, preparation=bundle.preparation))
            selection = bundle.parent_selection
        self._require_consistent_completions(states)
        for child, parent in pairwise(states):
            require_image_only_change(parent.plan, child.plan)
            if child.preparation.secrets != parent.preparation.secrets:
                msg = "Image preparation changed immutable server secret identities"
                raise TetherError(msg)
        return tuple(states)

    def selected(self) -> SelectedPreparation:
        """Return the fully validated selected preparation without any write."""
        return self.history()[0]

    def historical_plan(self, envelope_digest: str) -> CompiledTetherPlan:
        """Resolve only an envelope admitted by the selected immutable ancestry."""
        for state in self.history():
            if state.plan.envelope_digest == envelope_digest:
                return state.plan
        msg = "Retained envelope is not in the selected image-only ancestry"
        raise TetherError(msg)

    def retained_enrollment_plan(  # noqa: C901 - finite closure-only correlation and immutable plan-data validation
        self, peer: TetherPeerIntent, enrollment: OperationReceipt
    ) -> CompiledTetherPlan:
        """Resolve plan data only for an already owned peer, never preparation or startup."""
        request = enrollment.request
        generation = self.custody.read("generations", f"{peer.generation}.json")
        if (
            not isinstance(request, EnrollRequest)
            or request.peer != peer
            or request.installation_id != peer.installation_id
            or request.operation_id != peer.operation_id
            or request.expected_generation != peer.generation - 1
            or request.intent_digest != digest(peer)
            or enrollment.request_digest != digest(request)
            or enrollment.binding_generation is None
            or generation is None
            or TetherPeerIntent.model_validate_json(generation) != peer
        ):
            msg = "Retained closure plan lacks exact immutable peer and enrollment authority"
            raise TetherError(msg)
        matches: list[CompiledTetherPlan] = []
        legacy = self.custody.read("private", "plan.json")
        if legacy is not None:
            try:
                candidate = CompiledTetherPlan.model_validate_json(legacy)
            except ValueError:
                candidate = None
            if candidate is not None and candidate.envelope_digest == request.envelope_digest:
                matches.append(candidate)
        for name in self.custody.names("private"):
            if not name.startswith(self._BUNDLE_PREFIX) or not name.endswith(".json"):
                continue
            try:
                UUID(name.removeprefix(self._BUNDLE_PREFIX).removesuffix(".json"))
                raw = self.custody.read("private", name)
                body: object = json.loads(raw) if raw is not None else None
                if not isinstance(body, dict):
                    continue
                fields = cast("dict[str, object]", body)
                candidate = CompiledTetherPlan.model_validate(fields.get("plan"))
            except (ValueError, TypeError, OSError, TetherError):
                continue
            if candidate.envelope_digest == request.envelope_digest:
                matches.append(candidate)
        if not matches or any(candidate != matches[0] for candidate in matches):
            msg = "Exact enrolled envelope plan data is absent or conflicting"
            raise TetherError(msg)
        plan = matches[0]
        validate_peer(plan, peer)
        return plan

    def require_lineage(self, old_digest: str, new_digest: str) -> None:
        """Refuse to relabel historical evidence as an unrelated deployment envelope."""
        states = self.history()
        new_positions = [index for index, state in enumerate(states) if state.plan.envelope_digest == new_digest]
        old_positions = [index for index, state in enumerate(states) if state.plan.envelope_digest == old_digest]
        if (
            not new_positions
            or not old_positions
            or not any(old >= new for old in old_positions for new in new_positions)
        ):
            msg = "Historical envelope lacks the exact admitted image-only transition lineage"
            raise TetherError(msg)

    def require_replacement_ancestry(self, old_digest: str) -> None:
        """Require an actual selected replacement after the historical envelope."""
        if not any(state.plan.envelope_digest == old_digest for state in self.history()[1:]):
            msg = "Historical envelope has no committed image replacement in selected ancestry"
            raise TetherError(msg)

    def commit(
        self,
        request: PrepareImageRequest,
        parent: SelectedPreparation,
        preparation: PreparationReceipt,
        plan: CompiledTetherPlan,
    ) -> PreparationReceipt:
        """Select one immutable bundle under the existing lifecycle lock and exact CAS."""
        current = self.selected()
        if digest(current.selection) != request.expected_preparation_digest or current != parent:
            msg = "Selected preparation changed before image transition commit"
            raise TetherError(msg)
        require_image_only_change(parent.plan, plan)
        self._require_pair(plan, preparation)
        if preparation.operation_id != request.operation_id or preparation.secrets != parent.preparation.secrets:
            msg = "Image replacement must preserve exact original server secret identities"
            raise TetherError(msg)
        raw = self.custody.read("private", self._SELECTOR)
        if raw is None:
            self.custody.select_preparation(None, parent.selection)
            raw = parent.selection.model_dump_json().encode()
        bundle = ImagePreparationBundle(
            parent_selection=parent.selection, request_digest=digest(request), plan=plan, preparation=preparation
        )
        selection = PreparationSelection(
            installation_id=preparation.installation_id,
            operation_id=request.operation_id,
            bundle_digest=digest(bundle),
            parent_preparation_digest=digest(parent.selection),
        )
        self.custody.write("private", f"{self._BUNDLE_PREFIX}{request.operation_id}.json", bundle, immutable=True)
        self.custody.select_preparation(raw, selection)
        return self.selected().preparation
