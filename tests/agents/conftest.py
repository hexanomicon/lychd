"""Offline test floor for the agent/graph suite (A5 §10).

The module-level side effect below forbids every real model request across the
whole suite: no test may call out to a soulstone. All agent behaviour is driven
by `TestModel`/`FunctionModel` (Part 2.1 / 5.A, adopted verbatim from adw-kit).
"""

from __future__ import annotations

import pydantic_ai.models
import pytest

# NO test in this package may reach a real model — enforced process-wide.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False

from lychd.agents.services import WorkflowServices, default_sigil  # noqa: E402
from lychd.agents.the_first_one import default_forge  # noqa: E402
from lychd.domain.cortex.context import ContextOrchestrator  # noqa: E402
from lychd.domain.web.fragments import build_fragment_registry  # noqa: E402
from tests.agents.fakes import (  # noqa: E402
    FakeConsents,
    FakeDispatcher,
    FakeEvents,
    FakeOrchestrator,
    FakeRegistry,
    FakeTurns,
)


@pytest.fixture
def fake_events() -> FakeEvents:
    return FakeEvents()


@pytest.fixture
def fake_turns() -> FakeTurns:
    return FakeTurns()


@pytest.fixture
def fake_consents() -> FakeConsents:
    return FakeConsents()


@pytest.fixture
def fake_orchestrator() -> FakeOrchestrator:
    return FakeOrchestrator()


def make_services(
    *,
    model: object,
    events: FakeEvents,
    turns: FakeTurns,
    consents: FakeConsents,
    orchestrator: FakeOrchestrator,
    toolsets: tuple[object, ...] = (),
) -> WorkflowServices:
    """Assemble `WorkflowServices` from fakes + a real forge/context/fragments.

    The dispatcher hands back a grant carrying `model` (a TestModel) and
    `toolsets`; `context` and `fragments` are the real collaborators.
    """
    return WorkflowServices(
        dispatcher=FakeDispatcher(model=model, toolsets=toolsets),
        orchestrator=orchestrator,
        context=ContextOrchestrator(registry=FakeRegistry()),
        fragments=build_fragment_registry(),
        turns=turns,
        consents=consents,
        events=events,
        forge=default_forge(),
        sigil_provider=default_sigil,
    )
