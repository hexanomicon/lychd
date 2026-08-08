"""Conformance receipt for the complete private Crypt-to-Dispatcher seam."""

from __future__ import annotations

import asyncio
from pathlib import Path
from textwrap import dedent

from pydantic_ai.models.test import TestModel

from lychd.config.runes.registry import load_rune_registry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.schemas import CapabilityFamily
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.declarations import compile_animator_declarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger
from lychd.extensions.host import AssembledExtensions
from lychd.extensions.manager import ExtensionManager
from lychd.system.schemas import QuadletContainer

_EXTENSION_ID = "adversarial/vertical"
_MODEL_ID = "crypt-cipher-model"
_CAPABILITY_KEY = f"crypt-stone:chat:{_MODEL_ID}"

_REGISTER_SOURCE = dedent(
    """
    from datetime import UTC, datetime
    from pathlib import Path
    from typing import ClassVar

    from pydantic_ai.models.test import TestModel

    from lychd.domain.animation.capabilities import (
        ActivationResult,
        CapabilityPhase,
        CapabilitySpec,
        CapabilityState,
        SourceKind,
    )
    from lychd.domain.animation.connectors import Connector, ModelConnector
    from lychd.domain.animation.links import Link
    from lychd.domain.animation.schemas import CapabilityFamily, SoulstoneConfig
    from lychd.domain.animation.services.adapters.contracts import RuntimePlan, SoulstoneDefinition
    from lychd.domain.animation.services.adapters.surfaces import SoulstoneAnimator


    class AdversarialCryptRune(SoulstoneConfig):
        path_fragment: ClassVar[Path] = Path("crypt-adversarial")

        capability_model_id: str
        crypt_seal: str
        extra_modality: str


    class AdversarialConnector(Connector, ModelConnector):
        def __init__(self, model_id):
            self._model_id = model_id
            self._link = Link(up=True)
            self._model = TestModel()

        @property
        def kind(self):
            return "crypt-conformance"

        @property
        def link(self):
            return self._link

        @property
        def base_url(self):
            return "crypt://adversarial"

        def list_models(self):
            return ()

        def get_model(self, *, model_id=None):
            if model_id != self._model_id:
                raise ValueError(f"unexpected model request: {model_id}")
            return self._model


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

        def build_capability_specs(self, soulstone):
            if not isinstance(soulstone, AdversarialCryptRune):
                return []
            return [
                CapabilitySpec(
                    key=f"{soulstone.name}:chat:{soulstone.capability_model_id}",
                    animator_name=soulstone.name,
                    runtime=self.runtime,
                    source_kind=SourceKind.SOULSTONE,
                    family=CapabilityFamily.CHAT,
                    model_id=soulstone.capability_model_id,
                    modalities_in=["text", soulstone.extra_modality],
                    modalities_out=["text"],
                    supports_tools=True,
                    supports_streaming=False,
                    concurrency=soulstone.concurrency,
                    metadata={"crypt_seal": soulstone.crypt_seal},
                )
            ]

        async def probe_capability_states(self, animator, specs):
            return [
                CapabilityState(
                    capability_key=spec.key,
                    is_dynamic=spec.is_dynamic,
                    phase=CapabilityPhase.WARM,
                    health="crypt-ready",
                    active_model_id=spec.model_id,
                    loaded_model_ids=[spec.model_id],
                    checked_at=datetime.now(UTC),
                    metadata={"observer": animator.connector.kind},
                )
                for spec in specs
            ]

        async def activate_capability(self, animator, spec):
            return ActivationResult(
                accepted=False,
                phase=CapabilityPhase.WARM,
                reason=f"{animator.name}:{spec.model_id} is already warm",
            )

        def control_plane(self, animator):
            return None


    def register(context):
        context.soulstones.add(
            SoulstoneDefinition(
                rune_schema=AdversarialCryptRune,
                runtime_adapter=AdversarialRuntimeAdapter(),
            )
        )
    """
).lstrip()


def test_external_crypt_contributes_rune_adapter_capability_to_dispatcher(tmp_path: Path) -> None:
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

    context = ExtensionManager(
        builtins=[],
        crypt=[_EXTENSION_ID],
        crypt_root=crypt_extensions,
    ).assemble()
    extensions = AssembledExtensions(context=context, active_ids=(_EXTENSION_ID,))

    assert len(extensions.soulstone_definitions) == 1
    definition = extensions.soulstone_definitions[0]
    assert context.soulstones.registrations[0].provider_id == "crypt:adversarial/vertical"
    assert definition.rune_schema in extensions.rune_schemas
    assert extensions.runtime_adapters == (definition.runtime_adapter,)
    assert definition.rune_schema.__module__.startswith("lychd_crypt_extension_")
    assert type(definition.runtime_adapter).__module__ == definition.rune_schema.__module__

    runes = load_rune_registry(extensions, runes_dir)
    loaded_rune = runes.one(definition.rune_schema)
    assert loaded_rune.source_file == rune_file
    assert loaded_rune.model_dump()["crypt_seal"] == "registered-outside-core"
    assert definition.runtime_adapter.plan(loaded_rune).exec_args == [
        "crypt-runtime",
        "--model",
        _MODEL_ID,
    ]

    settings = get_settings()
    manifests = Transmuter(
        settings=settings,
        runtime_planner=RuntimeAdapterRegistry(adapters=extensions.runtime_adapters),
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
        runtime_adapters=extensions.runtime_adapters,
    )
    registry.ensure_loaded()
    leases = LeaseLedger()
    dispatcher = Dispatcher(registry=registry, leases=leases)

    resolved = dispatcher.resolve_intent("chat")
    assert resolved.key == _CAPABILITY_KEY
    assert resolved.metadata == {"crypt_seal": "registered-outside-core"}

    async def prove_dispatch() -> None:
        async with dispatcher.lease_grant(
            family=CapabilityFamily.CHAT,
            model_name=_MODEL_ID,
            run_id="crypt-conformance",
            require_modalities=("ciphertext",),
            requires_tools=True,
        ) as grant:
            assert grant.key == _CAPABILITY_KEY
            assert grant.state.health == "crypt-ready"
            assert grant.state.metadata == {"observer": "crypt-conformance"}
            assert not hasattr(grant, "animator")
            assert isinstance(grant.model, TestModel)
            assert [(row.capability_key, row.holder) for row in leases.active()] == [
                (_CAPABILITY_KEY, "run:crypt-conformance")
            ]

    asyncio.run(prove_dispatch())
    assert leases.active() == []
