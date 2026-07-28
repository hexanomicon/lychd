"""Host-side consumer for the caged Vessel's typed transition outbox."""

from __future__ import annotations

import json
import os
import re
import stat
from typing import TYPE_CHECKING, Literal, Protocol
from uuid import uuid4

import structlog

from lychd.domain.animation.capabilities import CapabilityPhase, CapabilityState
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.orchestration.actuator import (
    RuntimeActuationRestoredError,
    RuntimeCancellationRestoredError,
    RuntimePreconditionError,
    TransitionIntent,
    build_compensation_intent,
    capability_config_generation,
)
from lychd.domain.orchestration.policies import SwitchPolicy, resolve_switch_policy
from lychd.system.constants import PATH_REACTOR_INBOX_DIR, PATH_REACTOR_JOURNAL_DIR
from lychd.system.schemas import systemd_environment_assignment
from lychd.system.services.runtime import SystemdRuntimeActuator

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager
    from pathlib import Path

    from lychd.domain.animation.capabilities import CapabilitySpec
    from lychd.domain.animation.protocols import CapabilityRegistry
    from lychd.domain.animation.schemas import SoulstoneConfig

logger = structlog.get_logger()
_DIRECTORY_MODE = 0o700
_INTENT_MODE = 0o600
_MAX_INTENT_BYTES = 64 * 1024
_MAX_REJECTION_DETAIL = 2048
_PENDING_NAME = re.compile(r"^(?P<transition_id>[0-9a-f]{32})\.json$")

__all__ = ["HostReactor", "render_reactor_path_unit", "render_reactor_service_unit"]


class _RecoverableRuntimeActuator(Protocol):
    """Narrow host effect port required by the crash-recovering Reactor."""

    async def apply(self, intent: TransitionIntent) -> None:
        """Apply one fresh transition."""
        ...

    async def recover(self, intent: TransitionIntent) -> None:
        """Resume one claimed transition from observed host state."""
        ...


class _ExpectedStateView:
    """Policy view projected from the intent's claimed pre-transition world."""

    def __init__(self, registry: CapabilityRegistry, expected_active: set[str]) -> None:
        self._registry = registry
        self._expected_active = expected_active
        self._specs = {spec.key: spec for spec in registry.list_capabilities()}

    def list_capabilities(self) -> list[CapabilitySpec]:
        return list(self._specs.values())

    def get_capability_state(self, key: str, /) -> CapabilityState | None:
        spec = self._specs.get(key)
        if spec is None:
            return None
        phase = CapabilityPhase.WARM if spec.animator_name in self._expected_active else CapabilityPhase.COLD
        return CapabilityState(
            capability_key=key,
            is_dynamic=spec.is_dynamic,
            phase=phase,
            health="intent-projection",
        )

    def get_soulstone_rune(self, name: str, /) -> SoulstoneConfig | None:
        return self._registry.get_soulstone_rune(name)


def render_reactor_service_unit(*, executable: Path, environment: dict[str, str]) -> str:
    """Render the host-only oneshot consumer unit with deterministic environment."""
    lines = [
        "[Unit]",
        "Description=LychD Host Reactor",
        "Documentation=man:systemd.service(5)",
        "",
        "[Service]",
        "Type=oneshot",
        f"ExecStart={executable} reactor consume",
        *(f"Environment={systemd_environment_assignment(key, value)}" for key, value in sorted(environment.items())),
        "Restart=on-failure",
        "RestartSec=1s",
        "",
    ]
    return "\n".join(lines)


def render_reactor_path_unit(*, inbox_dir: Path, journal_dir: Path | None = None) -> str:
    """Render triggers for new intents and crash-surviving processing records."""
    resolved_journal = journal_dir or inbox_dir.parent / "journal"
    return "\n".join(
        [
            "[Unit]",
            "Description=Watch LychD Host Reactor transition work",
            "",
            "[Path]",
            f"PathExistsGlob={inbox_dir}/*.json",
            f"PathExistsGlob={resolved_journal}/*.processing.json",
            "Unit=lychd-reactor.service",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )


class HostReactor:
    """Validate, claim, apply, and journal one-way transition intents on the host.

    The inbox and journal are sibling host-owned directories. An intent is moved
    out of the Vessel-writable inbox before execution. The journal is mounted
    read-only into the Vessel so terminal records can close its completion fence;
    it is never a Vessel-writable reply or command protocol.
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        inbox_dir: Path = PATH_REACTOR_INBOX_DIR,
        journal_dir: Path = PATH_REACTOR_JOURNAL_DIR,
        actuator: _RecoverableRuntimeActuator | None = None,
        policy: SwitchPolicy | None = None,
        systemctl_bin: str | None = None,
        systemctl_timeout_s: float = 120.0,
        lock_factory: Callable[[], AbstractContextManager[object]] | None = None,
    ) -> None:
        """Bind the consumer to host-owned registry truth and directories."""
        if actuator is None:
            if systemctl_bin is None:
                msg = "Host Reactor requires an injected actuator or attested systemctl executable."
                raise ValueError(msg)
            actuator = SystemdRuntimeActuator(
                registry,
                systemctl_bin=systemctl_bin,
                systemctl_timeout_s=systemctl_timeout_s,
                observe_systemd=True,
            )
        if lock_factory is None:
            from lychd.system.services.lifecycle.lock import LifecycleLock

            lock_factory = LifecycleLock
        self._registry = registry
        self._inbox_dir = inbox_dir
        self._journal_dir = journal_dir
        self._actuator = actuator
        self._policy = policy or resolve_switch_policy("declared-conflicts")
        self._lock_factory = lock_factory

    async def consume_all(self) -> int:
        """Consume every claimed/pending intent once; raise after journaling failures."""
        with self._lock_factory():
            return await self._consume_all_locked()

    async def _consume_all_locked(self) -> int:
        """Consume all work while excluding every peer lifecycle mutation."""
        self._validate_directory(self._inbox_dir, label="inbox")
        self._validate_directory(self._journal_dir, label="journal")
        self._require_no_containment()

        processed, errors, mutation_fenced = await self._recover_claimed_batch()
        if not mutation_fenced:
            pending_processed, pending_errors = await self._consume_pending_batch()
            processed += pending_processed
            errors.extend(pending_errors)

        if errors:
            detail = "; ".join(errors)
            msg = f"Host Reactor did not apply transition intent(s): {detail}"
            raise RuntimeError(msg)
        return processed

    def _require_no_containment(self) -> None:
        """Refuse every host effect while a durable containment latch exists."""
        contained = sorted(self._journal_dir.glob("*.contained.json"))
        if contained:
            names = ", ".join(path.name for path in contained)
            msg = f"Host Reactor containment is active; refusing new physical work: {names}"
            raise RuntimeError(msg)

    async def _recover_claimed_batch(self) -> tuple[int, list[str], bool]:
        """Recover old claims first and stop at the first unresolved world."""
        processed = 0
        errors: list[str] = []
        for claimed in sorted(self._journal_dir.glob("*.processing.json")):
            error = await self._consume_existing_claim(claimed)
            if error is None:
                processed += 1
                continue
            errors.append(error)
            if os.path.lexists(claimed):
                return processed, errors, True
        return processed, errors, False

    async def _consume_pending_batch(self) -> tuple[int, list[str]]:
        """Consume fresh work until the first host-global mutation fence."""
        processed = 0
        errors: list[str] = []
        for pending in sorted(self._inbox_dir.glob("*.json")):
            did_process, error = await self._consume_pending(pending)
            if did_process:
                processed += 1
            if error is not None:
                errors.append(error)
            if self._mutation_fence_exists():
                break
        return processed, errors

    def _mutation_fence_exists(self) -> bool:
        """Return whether this batch has reached unresolved physical state."""
        return any(self._journal_dir.glob("*.processing.json")) or any(self._journal_dir.glob("*.contained.json"))

    async def _consume_existing_claim(self, claimed: Path) -> str | None:
        try:
            await self._apply_claimed(claimed, recover=True)
        except Exception as exc:  # noqa: BLE001 - journal then report all failures
            # A reclaimed record may represent a transaction already accepted
            # by systemd before the Reactor crashed. No generic exception proves
            # the old or desired world, so keep ``.processing`` as a durable
            # startup fence until recovery reaches a classified terminal world.
            return f"{claimed.name}: {exc}"
        return None

    async def _consume_pending(self, pending: Path) -> tuple[bool, str | None]:
        claimed: Path | None = None
        try:
            transition_id = self._transition_id_from_pending(pending)
            if self._already_journaled(transition_id):
                self._discard_path(pending)
                self._fsync_directory(self._inbox_dir)
                return False, None
            claimed = self._journal_dir / f"{transition_id}.processing.json"
            if os.path.lexists(claimed):
                self._discard_path(pending)
                self._fsync_directory(self._inbox_dir)
                return False, None
            # The host claims before reading. The Vessel cannot rename or
            # replace the journal path after this boundary.
            pending.replace(claimed)
            self._fsync_directory(self._inbox_dir)
            self._fsync_directory(self._journal_dir)
            await self._apply_claimed(claimed)
        except Exception as exc:  # noqa: BLE001 - malformed input must leave the live inbox
            if claimed is None:
                self._reject_pending(pending, reason=str(exc))
            # Once claimed, _apply_claimed owns every safe terminal
            # classification. If it leaves .processing behind, the effect
            # boundary is uncertain and must remain a durable batch fence.
            return False, f"{pending.name}: {exc}"
        return True, None

    async def _apply_claimed(self, claimed: Path, *, recover: bool = False) -> None:
        resolved = self._read_claimed_intent(claimed, recover=recover)
        observed_generation = capability_config_generation(self._registry)
        self._validate_claimed_preconditions(
            claimed,
            resolved,
            observed_generation=observed_generation,
            recover=recover,
        )
        await self._actuate_claimed(claimed, resolved, recover=recover)
        self._finish(claimed, status="completed")
        logger.info("host_transition_completed", transition_id=resolved.transition_id)

    def _read_claimed_intent(self, claimed: Path, *, recover: bool) -> TransitionIntent:
        """Read a claim, rejecting malformed fresh work before any effect."""
        try:
            return self._read_intent(claimed, claimed=True)
        except Exception as exc:
            if not recover:
                self._reject_claimed(claimed, reason=str(exc))
            raise

    def _validate_claimed_preconditions(
        self,
        claimed: Path,
        intent: TransitionIntent,
        *,
        observed_generation: str,
        recover: bool,
    ) -> None:
        """Classify declaration and policy failures before host actuation."""
        try:
            self._validate_preconditions(intent, observed_generation=observed_generation)
        except Exception as exc:
            if recover:
                msg = (
                    f"Cannot revalidate crash-reclaimed transition '{intent.transition_id}' "
                    f"without physical recovery: {exc}"
                )
                raise RuntimeError(msg) from exc
            self._finish(claimed, status="declined")
            if isinstance(exc, RuntimePreconditionError):
                raise
            raise RuntimePreconditionError(str(exc)) from exc

    async def _actuate_claimed(
        self,
        claimed: Path,
        intent: TransitionIntent,
        *,
        recover: bool,
    ) -> None:
        """Apply or recover one validated claim and journal its outcome."""
        try:
            # Only a crash-reclaimed processing record needs physical recovery.
            # A newly published compensation is a fresh inverse transaction and
            # must pass the actuator's normal exact-preworld admission path.
            if recover:
                await self._actuator.recover(intent)
            else:
                await self._actuator.apply(intent)
        except RuntimePreconditionError:
            if recover:
                raise
            self._finish(claimed, status="declined")
            raise
        except (RuntimeActuationRestoredError, RuntimeCancellationRestoredError):
            self._finish(claimed, status="restored")
            raise
        except Exception:
            if recover:
                raise
            # Validation failures are declined/rejected before effects. An
            # actuator failure is different: unless it proves restoration, the
            # host must leave a durable containment marker across app restarts.
            self._finish(claimed, status="contained")
            raise

    def _validate_preconditions(self, intent: TransitionIntent, *, observed_generation: str) -> None:
        """Validate generation and host authorization before any physical effect."""
        if intent.config_generation != observed_generation:
            msg = f"stale config generation {intent.config_generation}; host observes {observed_generation}"
            raise RuntimePreconditionError(msg)
        if intent.operation == "compensation":
            self._validate_compensation(intent, observed_generation=observed_generation)
        else:
            self._validate_policy(intent)

    def _read_intent(
        self,
        path: Path,
        *,
        claimed: bool = False,
        terminal_status: Literal["completed", "contained", "declined", "rejected", "restored"] | None = None,
    ) -> TransitionIntent:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError as exc:
            msg = "intent must be an available, non-symlink regular file"
            raise RuntimeError(msg) from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                msg = "intent must be a regular file"
                raise RuntimeError(msg)
            if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != _INTENT_MODE:
                msg = "intent must be owner-only (0600) and owned by the Reactor uid"
                raise RuntimeError(msg)
            if metadata.st_size > _MAX_INTENT_BYTES:
                msg = f"intent exceeds {_MAX_INTENT_BYTES} bytes"
                raise RuntimeError(msg)
            payload = bytearray()
            while len(payload) <= _MAX_INTENT_BYTES:
                chunk = os.read(descriptor, min(8192, _MAX_INTENT_BYTES + 1 - len(payload)))
                if not chunk:
                    break
                payload.extend(chunk)
            if len(payload) > _MAX_INTENT_BYTES:
                msg = f"intent exceeds {_MAX_INTENT_BYTES} bytes"
                raise RuntimeError(msg)
        finally:
            os.close(descriptor)
        intent = TransitionIntent.model_validate_json(payload)
        expected_name = self._expected_intent_name(
            intent.transition_id,
            claimed=claimed,
            terminal_status=terminal_status,
        )
        if path.name != expected_name:
            msg = "intent filename does not match transition_id"
            raise RuntimeError(msg)
        return intent

    @staticmethod
    def _expected_intent_name(
        transition_id: str,
        *,
        claimed: bool,
        terminal_status: Literal["completed", "contained", "declined", "rejected", "restored"] | None,
    ) -> str:
        """Return the only legal filename for one intent lifecycle position."""
        if claimed and terminal_status is not None:
            msg = "intent read cannot be both processing and terminal"
            raise RuntimeError(msg)
        if terminal_status is not None:
            return f"{transition_id}.{terminal_status}.json"
        if claimed:
            return f"{transition_id}.processing.json"
        return f"{transition_id}.json"

    def _validate_policy(self, intent: TransitionIntent) -> None:
        """Recompute the allowlisted plan; syntax alone never grants host effects."""
        self._validate_known_animators(intent)
        target = self._resolve_policy_target(intent)
        view = _ExpectedStateView(self._registry, set(intent.expected_active_animators))
        decision = self._policy.solve(target, view, LeaseLedger())
        expected_evict = tuple(sorted(decision.evict_animator_names))
        expected_launch = tuple(sorted(decision.launch_animator_names))
        if (
            tuple(sorted(intent.evict_animators)) != expected_evict
            or tuple(sorted(intent.launch_animators)) != expected_launch
        ):
            msg = (
                f"transition violates policy '{self._policy.name}': expected evict={expected_evict}, "
                f"launch={expected_launch}"
            )
            raise RuntimeError(msg)

    def _resolve_policy_target(self, intent: TransitionIntent) -> CapabilitySpec:
        """Resolve the exact target, with an unambiguous legacy-journal fallback."""
        specs = self._registry.list_capabilities()
        if intent.target_capability_key is None:
            legacy = sorted(
                (spec for spec in specs if spec.animator_name == intent.target_animator),
                key=lambda spec: spec.key,
            )
            if len(legacy) == 1:
                return legacy[0]
            if len(legacy) > 1:
                msg = (
                    "legacy transition omits target_capability_key, but target animator "
                    f"'{intent.target_animator}' has multiple configured capabilities"
                )
                raise RuntimeError(msg)
            msg = f"target animator has no configured capability: {intent.target_animator}"
            raise RuntimeError(msg)

        target = next(
            (spec for spec in specs if spec.key == intent.target_capability_key),
            None,
        )
        if target is None:
            msg = f"target capability is not configured: {intent.target_capability_key}"
            raise RuntimeError(msg)
        if target.animator_name != intent.target_animator:
            msg = (
                f"target capability '{target.key}' belongs to animator "
                f"'{target.animator_name}', not '{intent.target_animator}'"
            )
            raise RuntimeError(msg)
        return target

    def _validate_compensation(self, intent: TransitionIntent, *, observed_generation: str) -> None:
        """Authorize only the exact inverse of a current completed forward intent."""
        self._validate_known_animators(intent)
        rollback_of = intent.rollback_of
        if rollback_of is None:  # Pydantic enforces this; retain a local fail-closed guard.
            msg = "compensation transition is missing rollback_of"
            raise RuntimeError(msg)
        original_path = self._journal_dir / f"{rollback_of}.completed.json"
        original = self._read_intent(original_path, terminal_status="completed")
        if original.operation != "forward":
            msg = "compensation may reference only a completed forward transition"
            raise RuntimeError(msg)
        if original.config_generation != observed_generation:
            msg = "compensation references a completed transition from a stale config generation"
            raise RuntimeError(msg)
        expected = build_compensation_intent(original)
        actual_effect = intent.model_dump(mode="json", exclude={"transition_id"})
        expected_effect = expected.model_dump(mode="json", exclude={"transition_id"})
        if actual_effect != expected_effect:
            msg = "compensation does not exactly invert the completed forward transition"
            raise RuntimeError(msg)

    def _validate_known_animators(self, intent: TransitionIntent) -> None:
        """Reject every effect identity outside the locally configured registry."""
        referenced = {
            intent.target_animator,
            *intent.evict_animators,
            *intent.launch_animators,
            *intent.expected_active_animators,
        }
        unknown = sorted(name for name in referenced if self._registry.get_soulstone_rune(name) is None)
        if unknown:
            msg = f"transition references non-local or unknown animators: {unknown}"
            raise RuntimeError(msg)

    @staticmethod
    def _transition_id_from_pending(path: Path) -> str:
        match = _PENDING_NAME.fullmatch(path.name)
        if match is None:
            msg = "intent filename must be <32 lowercase hex>.json"
            raise RuntimeError(msg)
        try:
            metadata = path.lstat()
        except OSError as exc:
            msg = "intent disappeared before it could be claimed"
            raise RuntimeError(msg) from exc
        if not stat.S_ISREG(metadata.st_mode):
            msg = "intent must be a regular file"
            raise RuntimeError(msg)
        return match.group("transition_id")

    def _already_journaled(self, transition_id: str) -> bool:
        return any(
            (self._journal_dir / f"{transition_id}.{status}.json").exists()
            for status in ("processing", "completed", "contained", "declined", "rejected", "restored")
        )

    def _finish(self, claimed: Path, *, status: str) -> None:
        transition_id = claimed.name.removesuffix(".processing.json")
        target = self._journal_dir / f"{transition_id}.{status}.json"
        if target.exists():
            msg = f"journal record already exists: {target.name}"
            raise RuntimeError(msg)
        claimed.replace(target)
        self._fsync_directory(self._journal_dir)

    def _reject_pending(self, pending: Path, *, reason: str) -> None:
        if not os.path.lexists(pending):
            return
        self._discard_path(pending)
        self._fsync_directory(self._inbox_dir)
        self._write_rejection(f"invalid-{uuid4().hex}", reason=reason)

    def _reject_claimed(self, claimed: Path, *, reason: str) -> None:
        transition_id = claimed.name.removesuffix(".processing.json")
        self._discard_path(claimed)
        self._fsync_directory(self._journal_dir)
        marker_id = transition_id if re.fullmatch(r"[0-9a-f]{32}", transition_id) else f"invalid-{uuid4().hex}"
        self._write_rejection(marker_id, reason=reason)

    @staticmethod
    def _discard_path(path: Path) -> None:
        try:
            path.unlink()
        except IsADirectoryError:
            path.rmdir()

    def _write_rejection(self, marker_id: str, *, reason: str) -> None:
        target = self._journal_dir / f"{marker_id}.rejected.json"
        if os.path.lexists(target):
            return
        temporary = self._journal_dir / f".{marker_id}.{uuid4().hex}.tmp"
        payload = (
            json.dumps(
                {"status": "rejected", "reason": reason[:_MAX_REJECTION_DETAIL]},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            + b"\n"
        )
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _INTENT_MODE)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        self._fsync_directory(self._journal_dir)

    @staticmethod
    def _validate_directory(path: Path, *, label: str) -> None:
        if path.is_symlink() or not path.is_dir():
            msg = f"Host Reactor {label} is not a real directory: {path}"
            raise RuntimeError(msg)
        metadata = path.stat()
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != _DIRECTORY_MODE:
            msg = f"Host Reactor {label} must be owned by uid {os.getuid()} with mode 0o700: {path}"
            raise RuntimeError(msg)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
