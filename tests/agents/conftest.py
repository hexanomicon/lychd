"""Agent/graph fixtures under the repository-wide offline model-request guard."""

from __future__ import annotations

import pytest

from lychd.agents.services import WorkflowServices, default_sigil
from lychd.agents.the_first_one import default_forge
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.web.fragments import build_fragment_registry
from tests.agents.fakes import (
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
    """Assemble `WorkflowServices` from fakes + the real agent/context/fragments.

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
