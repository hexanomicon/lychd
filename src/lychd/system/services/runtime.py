"""Trusted implementations of the orchestration runtime actuator."""

from __future__ import annotations

import asyncio
import json
import os
import stat
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.orchestration.actuator import (
    RuntimeActuationRestoredError,
    RuntimeCancellationRestoredError,
    RuntimePreconditionError,
    TransitionIntent,
)
from lychd.system.services.lifecycle.models import LifecycleError
from lychd.system.services.systemctl_process import (
    SystemctlClientTimeoutError,
    communicate_systemctl_client,
    validate_systemctl_timeout,
    wait_systemctl_client,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

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
_JOB_POLL_SECONDS = 0.05
_JOB_SETTLE_TIMEOUT_SECONDS = 30.0
_LIST_JOBS_UNIT_COLUMN = 1


class _PublishedIntentError(RuntimeError):
    """A publication failure that happened after the inbox link became visible."""

    def __init__(self, original: Exception) -> None:
        super().__init__(str(original))
        self.original = original


@dataclass(frozen=True, slots=True)
class _ObservedRuntimeWorld:
    """Settled target reservations and running services for local Animators."""

    reserved_animators: tuple[str, ...]
    running_animators: tuple[str, ...]

    def is_exact(self, expected: tuple[str, ...]) -> bool:
        """Require both the conflict reservation and its service to converge."""
        return self.reserved_animators == expected and self.running_animators == expected


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
    """Ask systemd to execute one already-authorized Animator-target transaction."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        systemctl_bin: str,
        systemctl_timeout_s: float = 120.0,
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
        self._systemctl_timeout_s = validate_systemctl_timeout(systemctl_timeout_s)
        self._observe_systemd = observe_systemd
        self._lock_factory = lock_factory
        from lychd.system.services.runtime_topology import RuntimeTopologyAttestor
        from lychd.system.services.scribe import ScribeService

        scribe = ScribeService()
        self._topology_attestor = RuntimeTopologyAttestor(
            registry,
            systemctl_bin=systemctl_bin,
            systemctl_timeout_s=self._systemctl_timeout_s,
            owned_bindings_provider=scribe.inspect_owned_bindings,
        )

    async def apply(self, intent: TransitionIntent) -> None:
        """Apply the complete set, rejecting stale worlds and rolling back failures."""
        with self._effect_authority(intent, operation="transition"):
            await self._apply_locked(intent)

    async def _apply_locked(self, intent: TransitionIntent) -> None:
        """Observe and mutate only after the configured lifecycle authority is held."""
        try:
            if self._observe_systemd:
                await self._topology_attestor.attest(intent)
                pending = await self._pending_relevant_jobs(intent)
                if pending:
                    message = (
                        f"Transition '{intent.transition_id}' found in-flight systemd jobs before "
                        f"any effect: {', '.join(pending)}."
                    )
                    raise RuntimePreconditionError(message)
            world = await self._observe_runtime_world()
        except SystemctlClientTimeoutError as exc:
            message = (
                f"Transition '{intent.transition_id}' could not establish its systemd "
                f"pre-world before any effect: {exc}."
            )
            raise RuntimePreconditionError(message) from exc
        expected = tuple(sorted(intent.expected_active_animators))
        if not world.is_exact(expected):
            message = (
                f"Stale transition '{intent.transition_id}': expected exact runtime world {expected}, "
                f"observed target reservations {world.reserved_animators} and running services "
                f"{world.running_animators}."
            )
            raise RuntimePreconditionError(message)
        await self._execute_transaction(intent)

    async def recover(self, intent: TransitionIntent) -> None:
        """Reconcile a crashed compound transaction from its settled physical world."""
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
        """Recover one transaction while its effect authority remains exclusive."""
        if not self._observe_systemd:
            msg = "Host transition recovery requires direct systemd state observation."
            raise RuntimeError(msg)
        await self._await_relevant_jobs_quiescent(intent)
        await self._topology_attestor.attest(intent)
        world = await self._observe_runtime_world()
        expected = self._expected_world(intent)
        desired = self._desired_world(intent)
        if world.is_exact(desired):
            return
        if world.is_exact(expected):
            await self._execute_transaction(intent)
            return

        restored, _, compensation_error = await self._restore_expected(intent, observed=world)
        if restored.is_exact(expected):
            message = (
                f"Recovered partial transition '{intent.transition_id}' by restoring "
                f"its prior runtime world {expected}."
            )
            raise RuntimeActuationRestoredError(message)
        msg = (
            f"Cannot safely recover transition '{intent.transition_id}': observed partial world "
            f"{world}, compensation left {restored}, expected {expected}."
        )
        raise RuntimeError(msg) from compensation_error

    async def _execute_transaction(self, intent: TransitionIntent) -> None:
        """Fence caller cancellation through classification and exact restoration."""
        transaction_task = asyncio.create_task(self._execute_transaction_to_terminal(intent))
        try:
            await asyncio.shield(transaction_task)
        except asyncio.CancelledError as cancellation:
            # Repeated caller cancellation may not abandon a systemd-owned job.
            # Let the full classifier settle, then independently restore the
            # exact pre-world before preserving cancellation semantics.
            with suppress(Exception):
                await self._await_task_terminal(transaction_task)
            if not self._observe_systemd:
                await self._compensate_unobserved(intent)
                raise
            restoration_task = asyncio.create_task(self._compensate_after_interruption(intent))
            await self._await_task_terminal(restoration_task)
            message = f"Cancelled transition '{intent.transition_id}' restored its exact prior runtime world."
            raise RuntimeCancellationRestoredError(message) from cancellation
        else:
            return

    async def _execute_transaction_to_terminal(self, intent: TransitionIntent) -> None:
        """Run one compound request and classify the settled physical world."""
        action, units = self._physical_request(intent)
        try:
            returncode = await self._run_systemctl(action, units)
        except Exception as exc:  # subprocess creation/transport failure
            if self._observe_systemd:
                await self._settle_observed_transaction(intent, command_error=exc)
                return
            await self._compensate_unobserved(intent)
            message = f"Transition '{intent.transition_id}' could not submit its systemd transaction."
            raise RuntimeError(message) from exc

        if self._observe_systemd:
            await self._settle_observed_transaction(intent, returncode=returncode)
            return
        if returncode != 0:
            await self._compensate_unobserved(intent)
            msg = f"Transition '{intent.transition_id}' failed: systemctl returned {returncode} for {' '.join(units)}."
            raise RuntimeError(msg)
        await self._refresh_affected(intent)

    @staticmethod
    async def _await_task_terminal(task: asyncio.Task[None]) -> None:
        """Await a shielded task despite repeated cancellation requests."""
        while True:
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.cancelled():
                    raise
                continue
            else:
                return

    async def _settle_observed_transaction(
        self,
        intent: TransitionIntent,
        *,
        returncode: int | None = None,
        command_error: Exception | None = None,
    ) -> None:
        """Trust the settled world over the client return code, then compensate."""
        await self._await_relevant_jobs_quiescent(intent)
        observed = await self._observe_runtime_world()
        expected = self._expected_world(intent)
        desired = self._desired_world(intent)
        if observed.is_exact(desired):
            return
        if observed.is_exact(expected):
            message = (
                f"Transition '{intent.transition_id}' did not complete, but systemd "
                f"restored its prior runtime world {expected}."
            )
            raise RuntimeActuationRestoredError(message) from command_error

        restored, compensation_returncode, compensation_error = await self._restore_expected(
            intent,
            observed=observed,
        )
        if restored.is_exact(expected):
            detail = f" after systemctl returned {returncode}" if returncode is not None else ""
            message = f"Transition '{intent.transition_id}' failed{detail}; its prior runtime world was restored."
            raise RuntimeActuationRestoredError(message) from (command_error or compensation_error)

        cause = command_error or compensation_error
        result = f"systemctl return code {returncode}" if returncode is not None else "systemctl submission failure"
        compensation_detail = (
            f", compensation return code {compensation_returncode}" if compensation_returncode is not None else ""
        )
        msg = (
            f"Transition '{intent.transition_id}' is physically uncertain after {result}{compensation_detail}: "
            f"observed {observed}, compensation left {restored}, expected {expected}, desired {desired}."
        )
        raise RuntimeError(msg) from cause

    async def _compensate_after_interruption(self, intent: TransitionIntent) -> None:
        """Restore the exact pre-world after caller cancellation."""
        if self._observe_systemd:
            await self._await_relevant_jobs_quiescent(intent)
            observed = await self._observe_runtime_world()
            if observed.is_exact(self._expected_world(intent)):
                return
            restored, _, compensation_error = await self._restore_expected(
                intent,
                observed=observed,
            )
            if not restored.is_exact(self._expected_world(intent)):
                msg = (
                    f"Cancelled transition '{intent.transition_id}' could not restore its prior "
                    f"runtime world: observed {restored}."
                )
                raise RuntimeError(msg) from compensation_error
            return
        await self._compensate_unobserved(intent)

    async def _restore_expected(
        self,
        intent: TransitionIntent,
        *,
        observed: _ObservedRuntimeWorld,
    ) -> tuple[_ObservedRuntimeWorld, int | None, Exception | None]:
        """Submit one bounded inverse, await its jobs, and observe regardless of rc."""
        action, units = self._compensation_request(intent, observed=observed)
        returncode: int | None = None
        command_error: Exception | None = None
        try:
            returncode = await self._run_systemctl(action, units)
        except Exception as exc:  # noqa: BLE001 - final observation is authoritative
            command_error = exc
        try:
            await self._await_relevant_jobs_quiescent(intent)
        except Exception as exc:  # noqa: BLE001 - retain error but still attempt observation
            command_error = command_error or exc
        restored = await self._observe_runtime_world()
        return restored, returncode, command_error

    def _compensation_request(
        self,
        intent: TransitionIntent,
        *,
        observed: _ObservedRuntimeWorld,
    ) -> tuple[str, tuple[str, ...]]:
        """Choose the one inverse request capable of restoring this settled shape."""
        expected = self._expected_world(intent)
        expected_set = set(expected)
        extras = sorted(set(observed.reserved_animators) - expected_set)
        missing_reservations = expected_set - set(observed.reserved_animators)
        missing_services = expected_set - set(observed.running_animators)
        if extras and not missing_reservations and not missing_services:
            return (
                "stop",
                tuple(self._require_runtime_target(name) for name in extras),
            )
        if expected:
            return (
                "start",
                tuple(self._require_runtime_target(name) for name in expected),
            )
        candidates = extras or sorted(intent.launch_animators)
        return (
            "stop",
            tuple(self._require_runtime_target(name) for name in candidates),
        )

    async def _compensate_unobserved(self, intent: TransitionIntent) -> None:
        """Best-effort compensation for narrow non-observing test/development use."""
        try:
            expected = self._expected_world(intent)
            if expected:
                request = (
                    "start",
                    tuple(self._require_runtime_target(name) for name in expected),
                )
            else:
                request = (
                    "stop",
                    tuple(self._require_runtime_target(name) for name in sorted(intent.launch_animators)),
                )
            await self._run_systemctl(*request)
        finally:
            await self._refresh_affected(intent)

    async def _refresh_affected(self, intent: TransitionIntent) -> None:
        for animator_name in sorted({*intent.evict_animators, *intent.launch_animators}):
            await self._registry.refresh_capability_states_for_animator(animator_name)

    def _physical_request(self, intent: TransitionIntent) -> tuple[str, tuple[str, ...]]:
        if intent.launch_animators:
            return (
                "start",
                tuple(self._require_runtime_target(name) for name in sorted(intent.launch_animators)),
            )
        return (
            "stop",
            tuple(self._require_runtime_target(name) for name in sorted(intent.evict_animators)),
        )

    def _require_runtime_target(self, animator_name: str) -> str:
        if self._registry.get_soulstone_rune(animator_name) is None:
            msg = f"Animator '{animator_name}' is not backed by a local lifecycle-managed runtime."
            raise RuntimeError(msg)
        from lychd.system.unit_names import animator_target_unit

        return animator_target_unit(animator_name)

    async def _run_systemctl(self, action: str, unit_names: tuple[str, ...]) -> int:
        if not unit_names:
            msg = f"Systemd transaction action '{action}' requires at least one managed target."
            raise RuntimeError(msg)
        process = await asyncio.create_subprocess_exec(
            self._systemctl,
            "--user",
            action,
            "--job-mode=fail",
            *unit_names,
        )
        return await wait_systemctl_client(
            process,
            timeout_s=self._systemctl_timeout_s,
            operation=f"systemctl {action}",
        )

    async def _await_relevant_jobs_quiescent(self, intent: TransitionIntent) -> None:
        """Wait a bounded interval for a crash-surviving systemd job closure."""
        deadline = asyncio.get_running_loop().time() + _JOB_SETTLE_TIMEOUT_SECONDS
        while pending := await self._pending_relevant_jobs(intent):
            if asyncio.get_running_loop().time() >= deadline:
                msg = f"Systemd jobs did not settle for transition '{intent.transition_id}': {', '.join(pending)}."
                raise RuntimeError(msg)
            await asyncio.sleep(_JOB_POLL_SECONDS)

    async def _pending_relevant_jobs(self, intent: TransitionIntent) -> tuple[str, ...]:
        """Return in-flight jobs touching this transition's target/service closure."""
        process = await asyncio.create_subprocess_exec(
            self._systemctl,
            "--user",
            "list-jobs",
            "--no-legend",
            "--plain",
            "--no-pager",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await communicate_systemctl_client(
            process,
            timeout_s=self._systemctl_timeout_s,
            operation="systemctl list-jobs",
        )
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            suffix = f": {detail}" if detail else ""
            msg = f"Cannot observe systemd jobs; systemctl returned {process.returncode}{suffix}"
            raise RuntimeError(msg)
        relevant = self._relevant_units(intent)
        pending: set[str] = set()
        for raw_line in stdout.decode("utf-8", errors="replace").splitlines():
            columns = raw_line.split()
            if len(columns) > _LIST_JOBS_UNIT_COLUMN and columns[_LIST_JOBS_UNIT_COLUMN] in relevant:
                pending.add(columns[_LIST_JOBS_UNIT_COLUMN])
        return tuple(sorted(pending))

    @staticmethod
    def _relevant_units(intent: TransitionIntent) -> frozenset[str]:
        from lychd.system.unit_names import animator_service_unit, animator_target_unit

        names = {
            *intent.expected_active_animators,
            *intent.evict_animators,
            *intent.launch_animators,
        }
        return frozenset(
            {
                *(animator_target_unit(name) for name in names),
                *(animator_service_unit(name) for name in names),
            }
        )

    async def _observe_runtime_world(self) -> _ObservedRuntimeWorld:
        if self._observe_systemd:
            reserved: list[str] = []
            running: list[str] = []
            from lychd.system.unit_names import animator_service_unit, animator_target_unit

            for soulstone in sorted(self._registry.list_soulstone_runes(), key=lambda item: item.name):
                animator_name = soulstone.name
                target_active = await self._unit_is_active(animator_target_unit(animator_name))
                service_active = await self._unit_is_active(animator_service_unit(animator_name))
                if target_active:
                    reserved.append(animator_name)
                if service_active:
                    running.append(animator_name)
            return _ObservedRuntimeWorld(tuple(reserved), tuple(running))
        active = tuple(
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
        return _ObservedRuntimeWorld(active, active)

    async def _active_animators(self) -> tuple[str, ...]:
        """Compatibility view of exact active target reservations."""
        return (await self._observe_runtime_world()).reserved_animators

    async def _unit_is_active(self, unit_name: str) -> bool:
        process = await asyncio.create_subprocess_exec(
            self._systemctl,
            "--user",
            "is-active",
            "--quiet",
            unit_name,
        )
        returncode = await wait_systemctl_client(
            process,
            timeout_s=self._systemctl_timeout_s,
            operation=f"systemctl is-active {unit_name}",
        )
        if returncode == 0:
            return True
        if returncode in {3, 4}:
            return False
        msg = f"Cannot observe systemd state: systemctl returned {returncode} for {unit_name}"
        raise RuntimeError(msg)

    @staticmethod
    def _expected_world(intent: TransitionIntent) -> tuple[str, ...]:
        return tuple(sorted(intent.expected_active_animators))

    @staticmethod
    def _desired_world(intent: TransitionIntent) -> tuple[str, ...]:
        return tuple(
            sorted((set(intent.expected_active_animators) - set(intent.evict_animators)) | set(intent.launch_animators))
        )


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
        if self._resolve_terminal(terminal, intent.transition_id):
            return
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
            if self._resolve_terminal(terminal, transition_id):
                return
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

    @staticmethod
    def _resolve_terminal(status: str | None, transition_id: str) -> bool:
        """Return completion, raise typed terminal failures, or report no terminal."""
        if status is None:
            return False
        if status == "completed":
            return True
        if status == "declined":
            msg = f"Host Reactor declined transition '{transition_id}' before applying effects."
            raise RuntimePreconditionError(msg)
        if status == "restored":
            msg = f"Host Reactor failed transition '{transition_id}' but restored its prior runtime world."
            raise RuntimeActuationRestoredError(msg)
        if status == "contained":
            msg = f"Host Reactor contained physically uncertain transition '{transition_id}'."
            raise RuntimeError(msg)
        msg = f"Host Reactor rejected transition '{transition_id}'."
        raise RuntimeError(msg)

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
        restored = self._journal_dir / f"{transition_id}.restored.json"
        contained = self._journal_dir / f"{transition_id}.contained.json"
        if os.path.lexists(completed):
            return "completed"
        if os.path.lexists(rejected):
            return "rejected"
        if os.path.lexists(declined):
            return "declined"
        if os.path.lexists(restored):
            return "restored"
        if os.path.lexists(contained):
            return "contained"
        return None


async def wait_for_host_reactor_idle(settings: SwitchingSettings) -> None:
    """Fence app startup against a transition left pending by an earlier process."""
    if settings.actuator != "host-reactor":
        return
    deadline = asyncio.get_running_loop().time() + settings.reactor_ack_timeout_s
    inbox = settings.host_reactor_dir
    journal = settings.host_reactor_journal_dir
    await asyncio.to_thread(_validate_reactor_boundaries, inbox, journal)
    while any(inbox.glob("*.json")) or any(journal.glob("*.processing.json")) or any(journal.glob("*.contained.json")):
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
            systemctl_timeout_s=settings.systemctl_timeout_s,
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
