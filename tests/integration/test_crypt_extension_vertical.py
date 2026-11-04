"""Conformance receipt for the complete private Crypt-to-Dispatcher seam."""

from __future__ import annotations

import asyncio
from pathlib import Path
from textwrap import dedent
from typing import cast
from unittest.mock import Mock

import httpx2
import pytest
import respx
from pydantic_ai.models.test import TestModel

from lychd.config.runes.registry import load_rune_registry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.schemas import CapabilityFamily, SoulstoneConfig
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.declarations import compile_animator_declarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.orchestration.actuator import RuntimeActuator
from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.policies import DeclaredConflictPolicy
from lychd.domain.web.schemas import build_nexus_board
from lychd.extensions.host import AssembledExtensions
from lychd.extensions.manager import ExtensionManager
from lychd.system.schemas import QuadletContainer
from tests.runtime_guards import InertSoftActivationGuard

pytestmark = pytest.mark.httpx2(assert_all_called=False)


_EXTENSION_ID = "adversarial/vertical"
_MODEL_ID = "crypt-cipher-model"
_CAPABILITY_KEY = f"crypt-stone:chat:{_MODEL_ID}"

_REGISTER_SOURCE = dedent(
    """
    from datetime import UTC, datetime
    from pathlib import Path
    from typing import ClassVar

    from pydantic_ai.models.test import TestModel
    from pydantic_ai.toolsets import FunctionToolset

    from lychd.agents.workflows.nodes import CONSENT_EFFECT_ID_KEY, CONSENT_EFFECT_REVISION_KEY
    from lychd.domain.animation.capabilities import (
        ActivationResult,
        CapabilityPhase,
        CapabilitySpec,
        CapabilityState,
        SourceKind,
    )
    from lychd.domain.animation.connectors import Connector, ModelConnector, ToolConnector
    from lychd.domain.animation.links import Link
    from lychd.domain.animation.schemas import CapabilityFamily, SoulstoneConfig
    from lychd.domain.animation.services.adapters.contracts import RuntimePlan, SoulstoneDefinition
    from lychd.domain.animation.services.adapters.surfaces import SoulstoneAnimator


    class AdversarialCryptRune(SoulstoneConfig):
        path_fragment: ClassVar[Path] = Path("crypt-adversarial")

        capability_model_id: str
        crypt_seal: str
        extra_modality: str


    async def reveal_ciphertext(ciphertext: str):
        return ciphertext


    class AdversarialConnector(Connector, ModelConnector, ToolConnector):
        def __init__(self, model_id):
            self._model_id = model_id
            self._link = Link(up=True)
            self._model = TestModel()
            self._toolset = FunctionToolset(id="crypt-adversarial-tools")
            self._toolset.add_function(
                reveal_ciphertext,
                requires_approval=True,
                metadata={
                    CONSENT_EFFECT_ID_KEY: "crypt.reveal-ciphertext",
                    CONSENT_EFFECT_REVISION_KEY: "v1",
                },
            )

        @property
        def link(self):
            return self._link

        @property
        def base_url(self):
            return "crypt://adversarial"

        def get_model(self, *, model_id=None):
            if model_id != self._model_id:
                raise ValueError(f"unexpected model request: {model_id}")
            return self._model

        def get_toolsets(self):
            return (self._toolset,)


    class AdversarialRuntimeAdapter:
        runtime: ClassVar[str] = "crypt-adversarial"

        def plan(self, soulstone):
            return RuntimePlan(
                exec_args=["crypt-runtime", "--model", soulstone.capability_model_id],
            )

        def build_runtime(self, soulstone):
            if not isinstance(soulstone, AdversarialCryptRune):
                return None
            return SoulstoneAnimator(
                rune=soulstone,
                connector=AdversarialConnector(soulstone.capability_model_id),
            )

        def build_capability_specs(self, animator):
            soulstone = animator.rune
            if not isinstance(soulstone, AdversarialCryptRune):
                return []
            return [
                CapabilitySpec(
                    key=f"{soulstone.name}:chat:{soulstone.capability_model_id}",
                    animator_name=soulstone.name,
                    runtime=self.runtime,
                    registrant_id="core",
                    source_kind=SourceKind.SOULSTONE,
                    family=CapabilityFamily.CHAT,
                    model_id=soulstone.capability_model_id,
                    modalities_in=["text", soulstone.extra_modality],
                    supports_tools=True,
                    concurrency=soulstone.concurrency,
                )
            ]

        async def probe_capability_states(self, animator, specs):
            return [
                CapabilityState(
                    capability_key=spec.key,
                    phase=CapabilityPhase.WARM,
                    health="crypt-ready",
                    checked_at=datetime.now(UTC),
                )
                for spec in specs
            ]

        async def activate_capability(self, animator, spec):
            return ActivationResult(
                accepted=False,
                reason=f"{animator.name}:{spec.model_id} is already warm",
            )

    def register(context):
        context.soulstones.add(
            SoulstoneDefinition(
                rune_schema=AdversarialCryptRune,
                runtime_adapter=AdversarialRuntimeAdapter(),
            )
        )
    """
).lstrip()


def test_external_crypt_contributes_rune_adapter_capability_to_dispatcher(
    tmp_path: Path,
    httpx2_mock: respx.MockRouter,
) -> None:
    httpx2_mock.route(host="localhost").mock(
        side_effect=httpx2.ConnectError("local builtin runtime intentionally unavailable")
    )
    crypt_extensions = tmp_path / "crypt" / "extensions"
    register_file = crypt_extensions / "adversarial" / "vertical" / "register.py"
    register_file.parent.mkdir(parents=True)
    register_file.write_text(_REGISTER_SOURCE, encoding="utf-8")

    runes_dir = tmp_path / "runes"
    rune_file = runes_dir / "animator" / "soulstones" / "crypt-adversarial" / "main.toml"
    rune_file.parent.mkdir(parents=True)
    rune_file.write_text(
        dedent(
            f"""
            name = "crypt-stone"
            runtime = "crypt-adversarial"
            capability_model_id = "{_MODEL_ID}"
            crypt_seal = "registered-outside-core"
            extra_modality = "ciphertext"

            [quadlet]
            image = "localhost/crypt-conformance:latest"
            """
        ).lstrip(),
        encoding="utf-8",
    )

    builtin_rune = runes_dir / "animator" / "soulstones" / "vllm" / "main.toml"
    builtin_rune.parent.mkdir(parents=True)
    builtin_rune.write_text('name = "builtin-stone"\nmodel_path = "/models/builtin-model.gguf"\n', encoding="utf-8")

    context = ExtensionManager(
        builtins=["animator/vllm"],
        crypt=[_EXTENSION_ID],
        crypt_root=crypt_extensions,
    ).assemble()
    extensions = AssembledExtensions(context=context)

    rune_schema = next(schema for schema in extensions.rune_schemas if schema.__name__ == "AdversarialCryptRune")
    runtime_adapter = next(adapter for adapter in extensions.runtime_adapters if adapter.runtime == "crypt-adversarial")
    assert {item.registrant_id for item in extensions.soulstone_registrations} == {
        "builtin:animator/vllm",
        f"crypt:{_EXTENSION_ID}",
    }
    assert {item.registrant_id for item in extensions.portal_registrations} == {"builtin:animator"}

    runes = load_rune_registry(extensions, runes_dir)
    loaded_rune = cast("SoulstoneConfig", runes.one(rune_schema))
    assert loaded_rune.source_file == rune_file
    assert loaded_rune.model_dump()["crypt_seal"] == "registered-outside-core"
    assert runtime_adapter.plan(loaded_rune).exec_args == [
        "crypt-runtime",
        "--model",
        _MODEL_ID,
    ]

    settings = get_settings()
    manifests = Transmuter(
        settings=settings,
        runtime_planner=RuntimeAdapterRegistry(soulstone_registrations=extensions.soulstone_registrations),
    ).transmute_all([loaded_rune])
    physical = next(
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-crypt-stone"
    )
    assert physical.exec == f"crypt-runtime --model {_MODEL_ID}"

    registry = AnimatorRegistry(
        declarations=compile_animator_declarations(
            settings=settings,
            runes=runes,
            core_reserved_ports={},
        ),
        soulstone_registrations=extensions.soulstone_registrations,
        portal_registrations=extensions.portal_registrations,
    )
    registry.ensure_loaded()
    leases = LeaseLedger()
    _assert_attribution_projection(registry, leases)
    dispatcher = Dispatcher(registry=registry, leases=leases)

    async def prove_dispatch() -> None:
        async with dispatcher.lease_grant(
            family=CapabilityFamily.CHAT,
            model_name=_MODEL_ID,
            run_id="crypt-conformance",
            require_modalities=("ciphertext",),
            requires_tools=True,
        ) as grant:
            assert grant.spec.key == _CAPABILITY_KEY
            assert grant.spec.registrant_id == f"crypt:{_EXTENSION_ID}"
            assert grant.spec == registry.get_capability(_CAPABILITY_KEY)
            assert grant.state.health == "crypt-ready"
            assert isinstance(grant.model, TestModel)
            assert [toolset.id for toolset in grant.toolsets] == ["crypt-adversarial-tools"]
            assert [(row.capability_key, row.holder) for row in leases.active()] == [
                (_CAPABILITY_KEY, "run:crypt-conformance")
            ]

    asyncio.run(prove_dispatch())
    assert leases.active() == []


def _assert_attribution_projection(registry: AnimatorRegistry, leases: LeaseLedger) -> None:
    capabilities = registry.list_capabilities()
    by_key = {spec.key: spec for spec in capabilities}
    crypt_spec = by_key[_CAPABILITY_KEY]
    assert crypt_spec.registrant_id == f"crypt:{_EXTENSION_ID}"
    assert by_key["builtin-stone:chat:builtin-model"].registrant_id == "builtin:animator/vllm"
    capabilities.clear()
    detached = crypt_spec.model_dump()
    detached["registrant_id"] = "core"
    assert registry.get_capability(_CAPABILITY_KEY) == crypt_spec
    assert len(registry.list_capabilities()) == 2
    orchestrator = OrchestratorManager(
        Mock(),
        registry,
        leases=leases,
        policy=DeclaredConflictPolicy(),
        arbiter=TransitionArbiter(),
        actuator=Mock(spec=RuntimeActuator),
        switching=get_settings().orchestration.switching,
        soft_activation_guard=InertSoftActivationGuard(),
    )
    statuses = {row["capability_key"]: row for row in orchestrator.list_capability_statuses()}
    assert statuses[_CAPABILITY_KEY]["registrant_id"] == f"crypt:{_EXTENSION_ID}"
    board = build_nexus_board(orchestrator, registry)
    rows = {row.capability_key: row for _, group in board.covens for row in group}
    assert rows[_CAPABILITY_KEY].registrant_id == f"crypt:{_EXTENSION_ID}"
    assert rows["builtin-stone:chat:builtin-model"].registrant_id == "builtin:animator/vllm"
