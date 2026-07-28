"""Trusted implementations of the orchestration runtime actuator."""

from __future__ import annotations

import asyncio
import json
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.orchestration.actuator import RuntimePreconditionError, TransitionIntent
from lychd.system.services.lifecycle.models import LifecycleError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterator
    from contextlib import AbstractContextManager
    from typing import Any

    from lychd.config.settings.orchestration import SwitchingSettings
    from lychd.domain.animation.protocols import CapabilityRegistry

__all__ = [
    "HostReactorRuntimeActuator",
    "SystemdRuntimeActuator",
    "build_runtime_actuator",
    "wait_for_host_reactor_idle",
]

_REACTOR_DIRECTORY_MODE = 0o700
_ACK_POLL_SECONDS = 0.1


class _PublishedIntentError(RuntimeError):
    """A publication failure that happened after the inbox link became visible."""

    def __init__(self, original: Exception) -> None:
        super().__init__(str(original))
        self.original = original


def _validate_reactor_directory(path: Path, *, label: str) -> None:
    """Require one owner-only, non-symlink Reactor boundary directory."""
    if path.is_symlink() or not path.is_dir():
        msg = f"Host Reactor {label} directory does not exist safely: {path}"
        raise RuntimeError(msg)
    metadata = path.stat()
    mode = stat.S_IMODE(metadata.st_mode)
    if mode != _REACTOR_DIRECTORY_MODE or metadata.st_uid != os.getuid():
        msg = f"Host Reactor {label} directory must be owned by uid {os.getuid()} with mode 0o700: {path}"
        raise RuntimeError(msg)


def _validate_reactor_boundaries(intents_dir: Path, journal_dir: Path) -> None:
    """Validate the paired writable-inbox/read-only-journal trust boundary."""
    _validate_reactor_directory(intents_dir, label="intent")
    _validate_reactor_directory(journal_dir, label="journal")


class SystemdRuntimeActuator:
    """Translate animator identities to allowlisted registry-owned systemd units."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        systemctl_bin: str,
        observe_systemd: bool = False,
        lock_factory: Callable[[], AbstractContextManager[object]] | None = None,
    ) -> None:
        """Initialize against registry truth and an injected attested executable.

        The in-process orchestrator normally compares against probed capability
        state.  The host Reactor cannot reach pod-internal model endpoints, so it
        must compare the intent's expected world against systemd's unit state.
        """
        if not Path(systemctl_bin).is_absolute():
            msg = "Systemd runtime actuation requires an absolute attested systemctl path."
            raise ValueError(msg)
        self._registry = registry
        self._systemctl = systemctl_bin
        self._observe_systemd = observe_systemd
        self._lock_factory = lock_factory

    async def apply(self, intent: TransitionIntent) -> None:
        """Apply the complete set, rejecting stale worlds and rolling back failures."""
        with self._effect_authority(intent, operation="transition"):
            await self._apply_locked(intent)

    async def _apply_locked(self, intent: TransitionIntent) -> None:
        """Observe and mutate only after the configured lifecycle authority is held."""
        observed = await self._active_animators()
        expected = tuple(sorted(intent.expected_active_animators))
        if observed != expected:
            message = f"Stale transition '{intent.transition_id}': expected active {expected}, observed {observed}."
            raise RuntimePreconditionError(message)
        await self._apply_from_prefix(intent, prefix_length=0)

    async def recover(self, intent: TransitionIntent) -> None:
        """Resume a crashed transition only from an exact physical action prefix."""
        with self._effect_authority(intent, operation="recovery"):
            await self._recover_locked(intent)

    @contextmanager
    def _effect_authority(
        self,
        intent: TransitionIntent,
        *,
        operation: str,
    ) -> Iterator[None]:
        """Map only pre-entry lock refusal to verified no-effect rejection."""
        if self._lock_factory is None:
            yield
            return
        entered = False
        try:
            with self._lock_factory():
                entered = True
                yield
        except LifecycleError as exc:
            if entered:
                raise
            message = f"Direct systemd {operation} '{intent.transition_id}' could not acquire lifecycle authority."
            raise RuntimePreconditionError(message) from exc

    async def _recover_locked(self, intent: TransitionIntent) -> None:
        """Recover one transition while its effect authority remains exclusive."""
        if not self._observe_systemd:
            msg = "Host transition recovery requires direct systemd state observation."
            raise RuntimeError(msg)
        observed = await self._active_animators()
        legal_prefixes = self._legal_prefix_states(intent)
        try:
            prefix_length = legal_prefixes.index(observed)
        except ValueError as exc:
            msg = (
                f"Cannot safely recover transition '{intent.transition_id}': observed active "
                f"{observed} is not a legal action prefix."
            )
            raise RuntimeError(msg) from exc
        await self._apply_from_prefix(intent, prefix_length=prefix_length)

    @staticmethod
    def _legal_prefix_states(intent: TransitionIntent) -> tuple[tuple[str, ...], ...]:
        """Project every state reachable by the intent's ordered action prefixes."""
        active = set(intent.expected_active_animators)
        states: list[tuple[str, ...]] = [tuple(sorted(active))]
        for animator_name in intent.evict_animators:
            active.remove(animator_name)
            states.append(tuple(sorted(active)))
        for animator_name in intent.launch_animators:
            active.add(animator_name)
            states.append(tuple(sorted(active)))
        return tuple(states)

    async def _apply_from_prefix(self, intent: TransitionIntent, *, prefix_length: int) -> None:
        """Apply the uncompleted suffix, compensating the entire prefix on failure."""
        evict_count = min(prefix_length, len(intent.evict_animators))
        launch_count = max(0, prefix_length - len(intent.evict_animators))
        stopped = list(intent.evict_animators[:evict_count])
        started = list(intent.launch_animators[:launch_count])

        try:
            for animator_name in intent.evict_animators[evict_count:]:
                await self._run_recorded_effect(self._stop, animator_name, stopped)
            for animator_name in intent.launch_animators[launch_count:]:
                await self._run_recorded_effect(self._start, animator_name, started)
        except (Exception, asyncio.CancelledError) as exc:
            # Cancellation is an operational interruption too. Run compensation
            # in its own shielded task so shutdown cannot strand a half-applied
            # physical world merely because CancelledError is a BaseException.
            rollback_task = asyncio.create_task(self._rollback(stopped=stopped, started=started))
            rollback_errors = await asyncio.shield(rollback_task)
            if isinstance(exc, asyncio.CancelledError):
                raise
            detail = f" Rollback errors: {'; '.join(rollback_errors)}" if rollback_errors else ""
            message = f"Transition '{intent.transition_id}' failed and was rolled back.{detail}"
            raise RuntimeError(message) from exc

    @staticmethod
    async def _run_recorded_effect(
        operation: Callable[[str], Coroutine[Any, Any, None]],
        animator_name: str,
        completed: list[str],
    ) -> None:
        """Finish one systemd effect under cancellation, then record it exactly once."""
        effect_task = asyncio.create_task(operation(animator_name))
        try:
            await asyncio.shield(effect_task)
        except asyncio.CancelledError:
            await asyncio.shield(effect_task)
            completed.append(animator_name)
            raise
        completed.append(animator_name)

    async def _rollback(self, *, stopped: list[str], started: list[str]) -> list[str]:
        """Best-effort reverse completed effects; return every rollback error."""
        errors: list[str] = []
        for animator_name in reversed(started):
            try:
                await self._stop(animator_name)
            except Exception as exc:  # noqa: BLE001 - collect all compensating failures
                errors.append(f"stop {animator_name}: {exc}")
        for animator_name in reversed(stopped):
            try:
                await self._start(animator_name)
            except Exception as exc:  # noqa: BLE001 - collect all compensating failures
                errors.append(f"restart {animator_name}: {exc}")
        return errors

    async def _start(self, animator_name: str) -> None:
        unit_name = self._require_runtime_unit(animator_name)
        await self._run_systemctl("start", unit_name, failure_prefix="Physical manifestation failed")
        if not self._observe_systemd:
            await self._registry.refresh_capability_states_for_animator(animator_name)

    async def _stop(self, animator_name: str) -> None:
        unit_name = self._runtime_unit(animator_name)
        if unit_name is None:
            return

        await self._run_systemctl("stop", unit_name, failure_prefix="Eviction failed")
        if not self._observe_systemd:
            await self._registry.refresh_capability_states_for_animator(animator_name)

    def _require_runtime_unit(self, animator_name: str) -> str:
        unit_name = self._runtime_unit(animator_name)
        if unit_name is None:
            msg = f"Animator '{animator_name}' is not backed by a local lifecycle-managed runtime."
            raise RuntimeError(msg)
        return unit_name

    async def _run_systemctl(self, action: str, unit_name: str, *, failure_prefix: str) -> None:
        process = await asyncio.create_subprocess_exec(
            self._systemctl,
            "--user",
            action,
            unit_name,
        )
        await process.wait()
        if process.returncode != 0:
            msg = f"{failure_prefix}: systemctl returned {process.returncode} for {unit_name}"
            raise RuntimeError(msg)

    def _runtime_unit(self, animator_name: str) -> str | None:
        soulstone = self._registry.get_soulstone_rune(animator_name)
        if soulstone is None:
            return None
        return f"{soulstone.service_name}.service"

    async def _active_animators(self) -> tuple[str, ...]:
        if self._observe_systemd:
            active: list[str] = []
            names = sorted({spec.animator_name for spec in self._registry.list_capabilities()})
            for animator_name in names:
                unit_name = self._runtime_unit(animator_name)
                if unit_name is not None and await self._unit_is_active(unit_name):
                    active.append(animator_name)
            return tuple(active)
        return tuple(
            sorted(
                {
                    spec.animator_name
                    for spec in self._registry.list_capabilities()
                    if self._registry.get_soulstone_rune(spec.animator_name) is not None
                    and (state := self._registry.get_capability_state(spec.key)) is not None
                    and state.runtime_started
                }
            )
        )

    async def _unit_is_active(self, unit_name: str) -> bool:
        process = await asyncio.create_subprocess_exec(
            self._systemctl,
            "--user",
            "is-active",
            "--quiet",
            unit_name,
        )
        await process.wait()
        if process.returncode == 0:
            return True
        if process.returncode in {3, 4}:
            return False
        msg = f"Cannot observe systemd state: systemctl returned {process.returncode} for {unit_name}"
        raise RuntimeError(msg)


class HostReactorRuntimeActuator:
    """Publish one typed transition and await its host-owned terminal journal."""

    def __init__(self, intents_dir: Path, journal_dir: Path, *, ack_timeout_s: float) -> None:
        """Bind the gateway to its writable inbox and read-only host journal."""
        if ack_timeout_s <= 0:
            msg = "Host Reactor acknowledgement timeout must be positive."
            raise ValueError(msg)
        self._intents_dir = intents_dir
        self._journal_dir = journal_dir
        self._ack_timeout_s = ack_timeout_s

    async def apply(self, intent: TransitionIntent) -> None:
        """Durably publish, then hold the manager barrier through host completion."""
        await asyncio.to_thread(_validate_reactor_boundaries, self._intents_dir, self._journal_dir)
        terminal = self._terminal_status(intent.transition_id)
        if terminal == "completed":
            return
        if terminal == "rejected":
            msg = f"Host Reactor rejected transition '{intent.transition_id}'."
            raise RuntimeError(msg)
        if terminal == "declined":
            msg = f"Host Reactor declined transition '{intent.transition_id}' before applying effects."
            raise RuntimePreconditionError(msg)
        publish_task = asyncio.create_task(asyncio.to_thread(self._write_atomic, intent))
        publication_exposed = False
        try:
            await asyncio.shield(publish_task)
            publication_exposed = True
            await self._await_terminal(intent.transition_id)
        except asyncio.CancelledError:
            # A caller cancellation must not reopen admission while an already
            # claimed host effect can still land. First let any in-flight atomic
            # publication settle, then remove an unclaimed delivery; otherwise
            # shield until the host records a terminal outcome.
            try:
                await asyncio.shield(publish_task)
                publication_exposed = True
            except _PublishedIntentError:
                publication_exposed = True
            except (OSError, RuntimeError):  # failed before exposing an inbox link
                pass
            fence = asyncio.create_task(
                self._cancel_or_wait(intent.transition_id, require_terminal=publication_exposed)
            )
            await asyncio.shield(fence)
            raise
        except _PublishedIntentError as exc:
            fence = asyncio.create_task(self._cancel_or_wait(intent.transition_id, require_terminal=True))
            await asyncio.shield(fence)
            raise exc.original from exc
        except (OSError, RuntimeError):
            # ``link()`` is the publication point. A later chmod/fsync/cleanup
            # failure may therefore coexist with a live delivery; fence that
            # delivery before exposing the original publication error.
            fence = asyncio.create_task(self._cancel_or_wait(intent.transition_id, require_terminal=False))
            await asyncio.shield(fence)
            raise

    def _write_atomic(self, intent: TransitionIntent) -> None:
        _validate_reactor_boundaries(self._intents_dir, self._journal_dir)
        target = self._intents_dir / f"{intent.transition_id}.json"
        temporary = self._intents_dir / f".{intent.transition_id}.tmp"
        payload = json.dumps(intent.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        published = False
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            # Publish without overwriting an existing transition identity.
            os.link(temporary, target)
            published = True
            temporary.unlink()
            directory_fd = os.open(self._intents_dir, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException as exc:
            temporary.unlink(missing_ok=True)
            if published and isinstance(exc, Exception):
                raise _PublishedIntentError(exc) from exc
            raise

    async def _await_terminal(self, transition_id: str) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._ack_timeout_s
        timeout_handled = False
        while True:
            terminal = self._terminal_status(transition_id)
            if terminal == "completed":
                return
            if terminal == "rejected":
                msg = f"Host Reactor rejected transition '{transition_id}'."
                raise RuntimeError(msg)
            if terminal == "declined":
                msg = f"Host Reactor declined transition '{transition_id}' before applying effects."
                raise RuntimePreconditionError(msg)
            if not timeout_handled and loop.time() >= deadline:
                if await asyncio.to_thread(self._cancel_pending, transition_id):
                    msg = f"Host Reactor did not claim transition '{transition_id}' within {self._ack_timeout_s:g}s."
                    raise TimeoutError(msg)
                processing = self._journal_dir / f"{transition_id}.processing.json"
                # Recheck the terminal rename before ruling the delivery lost.
                if not os.path.lexists(processing) and self._terminal_status(transition_id) is None:
                    msg = f"Host Reactor transition '{transition_id}' disappeared without a terminal journal."
                    raise RuntimeError(msg)
                timeout_handled = True
            await asyncio.sleep(_ACK_POLL_SECONDS)

    async def _cancel_or_wait(self, transition_id: str, *, require_terminal: bool = False) -> None:
        if await asyncio.to_thread(self._cancel_pending, transition_id):
            return
        if self._terminal_status(transition_id) is not None:
            return
        processing = self._journal_dir / f"{transition_id}.processing.json"
        if not require_terminal and not os.path.lexists(processing):
            return
        while True:
            if self._terminal_status(transition_id) is not None:
                return
            await asyncio.sleep(_ACK_POLL_SECONDS)

    def _cancel_pending(self, transition_id: str) -> bool:
        pending = self._intents_dir / f"{transition_id}.json"
        try:
            pending.unlink()
        except FileNotFoundError:
            return False
        directory_fd = os.open(self._intents_dir, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return True

    def _terminal_status(self, transition_id: str) -> str | None:
        completed = self._journal_dir / f"{transition_id}.completed.json"
        rejected = self._journal_dir / f"{transition_id}.rejected.json"
        declined = self._journal_dir / f"{transition_id}.declined.json"
        if os.path.lexists(completed):
            return "completed"
        if os.path.lexists(rejected):
            return "rejected"
        if os.path.lexists(declined):
            return "declined"
        return None


async def wait_for_host_reactor_idle(settings: SwitchingSettings) -> None:
    """Fence app startup against a transition left pending by an earlier process."""
    if settings.actuator != "host-reactor":
        return
    deadline = asyncio.get_running_loop().time() + settings.reactor_ack_timeout_s
    inbox = settings.host_reactor_dir
    journal = settings.host_reactor_journal_dir
    await asyncio.to_thread(_validate_reactor_boundaries, inbox, journal)
    while any(inbox.glob("*.json")) or any(journal.glob("*.processing.json")):
        if asyncio.get_running_loop().time() >= deadline:
            msg = "Host Reactor still has unfinished transition work; refusing to open run admission."
            raise RuntimeError(msg)
        await asyncio.sleep(_ACK_POLL_SECONDS)


def build_runtime_actuator(
    settings: SwitchingSettings,
    registry: CapabilityRegistry,
    *,
    systemctl_bin: str | None = None,
    lock_factory: Callable[[], AbstractContextManager[object]] | None = None,
) -> SystemdRuntimeActuator | HostReactorRuntimeActuator:
    """Select the configured trusted effect owner at the composition boundary."""
    if settings.actuator == "systemd":
        if systemctl_bin is None:
            message = "Direct systemd actuation requires an injected attested systemctl executable."
            raise RuntimeError(message)
        if lock_factory is None:
            from lychd.system.services.lifecycle.lock import LifecycleLock

            lock_factory = LifecycleLock
        return SystemdRuntimeActuator(
            registry,
            systemctl_bin=systemctl_bin,
            observe_systemd=True,
            lock_factory=lock_factory,
        )
    if settings.actuator == "host-reactor":
        return HostReactorRuntimeActuator(
            settings.host_reactor_dir,
            settings.host_reactor_journal_dir,
            ack_timeout_s=settings.reactor_ack_timeout_s,
        )
    message = f"Unknown runtime actuator: {settings.actuator}"
    raise ValueError(message)
