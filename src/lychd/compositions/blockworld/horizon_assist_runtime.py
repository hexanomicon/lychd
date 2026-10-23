"""Explicit process-local Run assembly for the experimental assist CLI.

This is local delivery, not SAQ, a production startup, or restart recovery.
Physical game I/O belongs to the supplied system-layer control session.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, cast

from lychd.agents.router import Intent
from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.compositions.blockworld.horizon_assist import AssistRequest, HorizonAssistService, horizon_assist_workflow
from lychd.compositions.blockworld.horizon_behaviors import (
    BehaviorTick,
    HorizonBehaviorService,
    horizon_behavior_workflows,
)
from lychd.compositions.blockworld.horizon_build import BuildStep, HorizonBuildService, horizon_build_workflow
from lychd.compositions.blockworld.local_runtime import (
    LocalJob as LocalJob,  # noqa: PLC0414 - retain the established public import
)
from lychd.compositions.blockworld.local_runtime import (
    LocalRunQueue,
    RefuseHostTransitions,
)
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import SettingsSnapshot
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.cancellation import RunEffectLifecycle
from lychd.domain.cortex.substrate import get_run_substrate, reset_run_substrate, set_run_substrate
from lychd.interface.web.altar_services import AltarServices, build_altar_services


class BehaviorAdmissionRefused(ValueError):  # noqa: N818 - names the exact pre-admission refusal boundary
    """A tick failed authority validation before native Run admission began."""


class BuildAdmissionRefused(BehaviorAdmissionRefused):
    """A cell failed validation before any native Run submission began."""


class LocalControl(RunEffectLifecycle, Protocol):
    async def aclose(self) -> None: ...


# Preserve the established public queue name for Horizon callers.
LocalAssistQueue = LocalRunQueue


class LocalAssistRunner:
    """One explicit assembly; each request goes through RunEngine and perform_run."""

    def __init__(
        self,
        assist: HorizonAssistService,
        control: LocalControl,
        *,
        behaviors: HorizonBehaviorService | None = None,
        builds: HorizonBuildService | None = None,
    ) -> None:
        """Retain already constructed session collaborators, without startup."""
        self.assist = assist
        self.control = control
        if behaviors is not None and behaviors.assist is not assist:
            msg = "Behavior and operator commands must share one assist service."
            raise ValueError(msg)
        self.behaviors = behaviors
        if builds is not None and (builds.assist is not assist or builds.control is not cast("object", control)):
            msg = "Build, behavior and operator commands must share one assist/control session."
            raise ValueError(msg)
        self.builds = builds
        self.queue = LocalAssistQueue()
        self.services: AltarServices | None = None
        self.active_run: str | None = None

    async def open(self) -> None:
        """Publish a fresh memory assembly only when no other substrate exists."""
        try:
            get_run_substrate()
        except RuntimeError:
            pass
        else:
            msg = "Local assist requires an unpublished process Run substrate."
            raise RuntimeError(msg)
        workflow = horizon_assist_workflow(self.assist)
        workflows = (workflow,) if self.behaviors is None else (workflow, *horizon_behavior_workflows(self.behaviors))
        if self.builds is not None:
            workflows = (*workflows, horizon_build_workflow(self.builds))
        settings = SettingsSnapshot(
            payload='{"server":{"database":{"profile":"memory"}},"extensions":{"builtins":[],"crypt":[]}}'
        ).materialize()
        services = build_altar_services(
            queues={"runs": self.queue, "rites": self.queue},
            runes=RuneRegistry(()),
            settings=settings,
            workflows=BuiltinWorkflowRegistry(
                workflows=workflows,
                default_name=workflow.name,
                route_precedence=tuple(item.name for item in workflows[1:]),
            ),
            profile="memory",
            runtime_actuator=RefuseHostTransitions(),
            soft_activation_guard=RefuseHostTransitions(),
        )
        services.substrate.effects = self.control
        services.run_engine.effects = self.control
        services.registry.ensure_loaded()
        self.services = services
        set_run_substrate(services.substrate)

    async def submit(self, request: AssistRequest) -> str:
        """Admit one typed action with a stable request identity and session fence."""
        services = self.services
        if services is None:
            msg = "Local assist runner is closed."
            raise RuntimeError(msg)
        principal = Sigil(name=self.assist.policy.principal, scopes=frozenset({"horizon:assist"}))
        handle = await services.run_engine.submit(
            Intent(
                session_id=self.assist.policy.session_id,
                prompt=request.model_dump_json(),
                source="horizon.assist",
                sigil_name=principal.name,
                sigil_scopes=principal.scopes,
            ),
            idempotency_key=f"horizon-assist:{self.assist.policy.session_id}:{request.request_id}",
            exclusive_session=True,
        )
        self.active_run = handle.run_id
        return handle.run_id

    async def submit_behavior(self, tick: BehaviorTick) -> str:
        """Admit one retained finite tick through the same native engine and session."""
        services, behaviors = self.services, self.behaviors
        if services is None or behaviors is None:
            msg = "Local behavior runner is closed or unconfigured."
            raise RuntimeError(msg)
        principal = Sigil(name=self.assist.policy.principal, scopes=frozenset({"horizon:assist"}))
        try:
            behaviors.validate(tick, principal)
        except ValueError as exc:
            raise BehaviorAdmissionRefused(str(exc)) from exc
        handle = await services.run_engine.submit(
            Intent(
                session_id=self.assist.policy.session_id,
                prompt=tick.model_dump_json(),
                source=f"horizon.{tick.kind}_tick",
                sigil_name=principal.name,
                sigil_scopes=principal.scopes,
            ),
            idempotency_key=f"horizon-behavior:{self.assist.policy.session_id}:{tick.request_id}",
            exclusive_session=True,
        )
        self.active_run = handle.run_id
        return handle.run_id

    async def submit_build(self, step: BuildStep) -> str:
        """Admit one exact plan cell with the native engine's exclusive session."""
        services, builds = self.services, self.builds
        if services is None or builds is None:
            msg = "Local build runner is closed or unconfigured."
            raise RuntimeError(msg)
        principal = Sigil(name=self.assist.policy.principal, scopes=frozenset({"horizon:assist"}))
        try:
            builds.validate(step, principal)
        except ValueError as exc:
            raise BuildAdmissionRefused(str(exc)) from exc
        handle = await services.run_engine.submit(
            Intent(
                session_id=self.assist.policy.session_id,
                prompt=step.model_dump_json(),
                source="horizon.build_step",
                sigil_name=principal.name,
                sigil_scopes=principal.scopes,
            ),
            idempotency_key=f"horizon-build:{self.assist.policy.session_id}:{step.request_id}",
            exclusive_session=True,
        )
        self.active_run = handle.run_id
        return handle.run_id

    async def wait(self, run_id: str) -> dict[str, Any]:
        """Wait for this process's exact local delivery and persisted event chain."""
        services = self.services
        if services is None:
            msg = "Local assist runner is closed."
            raise RuntimeError(msg)
        jobs = [job for job in self.queue.jobs.values() if job.run_id == run_id]
        if len(jobs) != 1 or jobs[0].task is None:
            msg = "Expected one exact local delivery."
            raise RuntimeError(msg)
        result = await asyncio.shield(jobs[0].task)
        await services.bus.wait_persisted(run_id)
        if self.active_run == run_id:
            self.active_run = None
        return result

    async def cancel(self) -> None:
        """Priority stop path, independent of parsing or any awaited game reply."""
        if self.services is not None and self.active_run is not None:
            await self.services.run_engine.cancel(self.active_run)
            self.active_run = None

    async def aclose(self) -> None:
        """Fence/contain before task drainage and service withdrawal."""
        try:
            await self.cancel()
            await self.control.aclose()
        finally:
            await self.queue.close()
            if self.services is not None:
                reset_run_substrate()
                await self.services.aclose()
                self.services = None
