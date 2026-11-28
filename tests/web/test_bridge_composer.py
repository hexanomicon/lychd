"""Current Bridge composer guidance comes from admission, never retained Runs."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock

import pytest

from lychd.agents.router import Intent
from lychd.agents.workflows import (
    BRIDGE_CHAT,
    BRIDGE_CHAT_ARCHIVE,
    BRIDGE_CHAT_BOUND,
    BRIDGE_CHAT_SEMANTIC,
    BRIDGE_CHAT_WEBCRAWLER,
    BuiltinWorkflowRegistry,
    Workflow,
)
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.webcrawler.profile import parse_page_question
from lychd.interface.web.webcrawler_admission import WebcrawlerAdmissionService
from tests.webcrawler_fixtures import webcrawler_profile

if TYPE_CHECKING:
    from types import SimpleNamespace

    from tests.web.conftest import AsgiClient

_EXAMPLE = "/read-public https://example.com/page\nWhat does this page claim?"
_GUIDANCE = (
    "Enter /read-public followed by one exact public HTTPS URL, then a newline and your question. "
    "Sending this command declares the complete URL, including its path and query, public. "
    "Approval is required before page contact.\n\n" + _EXAMPLE
)


def _configure(services: SimpleNamespace, *, revision: str = "4") -> Mock:
    services.run_engine.workflows = BuiltinWorkflowRegistry(
        workflows=(BRIDGE_CHAT, BRIDGE_CHAT_BOUND, BRIDGE_CHAT_ARCHIVE, BRIDGE_CHAT_WEBCRAWLER, BRIDGE_CHAT_SEMANTIC),
        active_revisions=(("bridge_chat", revision),),
        default_name="bridge_chat",
    )
    services.run_engine.bridge_webcrawler = webcrawler_profile().model_copy(
        update={"resolver_custody_statement": "PRIVATE_CONFIGURATION_SENTINEL"}
    )
    admission = Mock(spec=WebcrawlerAdmissionService)
    services.webcrawler_admission = services.run_engine.webcrawler_admission = admission
    return admission


async def _retained_run(services: SimpleNamespace, workflow: Workflow) -> str:
    session = await services.bridge_sessions.create_session()
    run = await services.ledger.create(
        Intent(session_id=session.id, prompt="PRIVATE_DRAFT_SENTINEL", source="bridge"),
        workflow_name=workflow.name,
        pattern_manifest=workflow.manifest.snapshot(),
        queue_name="runs",
        priority=50,
    )
    await services.ledger.set_status(run.run_id, RunStatus.RUNNING)
    await services.ledger.set_status(run.run_id, RunStatus.DONE)
    await services.bridge_sessions.add_turn(
        session.id, BridgeTurn(role="agent", content="Retained earlier answer", run_id=run.run_id)
    )
    return session.id


def test_empty_webcrawler_snapshot_projects_actual_admission_default_without_effects(
    altar_client: AsgiClient, fake_services: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    admission = _configure(fake_services)
    assert fake_services.workflows.default is BRIDGE_CHAT
    forbidden: list[AsyncMock] = []
    for owner, name in (
        (fake_services.run_engine, "submit"),
        (fake_services.run_engine, "resume_consent"),
        (fake_services.ledger, "create"),
        (fake_services.consents, "park"),
        (fake_services.bridge_sessions, "create_session"),
    ):
        effect = AsyncMock(side_effect=AssertionError("A composer read cannot admit work."))
        monkeypatch.setattr(owner, name, effect)
        forbidden.append(effect)
    response = altar_client.get("/api/v1/bridge")
    assert response.status_code == 200
    payload = response.json()
    assert payload["session"] is None
    assert payload["active_runs"] == payload["pending_consents"] == []
    assert payload["composer"] == {"pattern_id": "bridge_chat", "pattern_revision": "4", "guidance": _GUIDANCE}
    assert "PRIVATE_CONFIGURATION_SENTINEL" not in response.text
    admission.assert_not_called()
    admission.declare.assert_not_called()
    for effect in forbidden:
        effect.assert_not_called()
    parsed = parse_page_question(_EXAMPLE)
    assert parsed.url == "https://example.com/page"
    assert parsed.question == "What does this page claim?"


def test_selected_snapshot_uses_current_webcrawler_despite_older_session_run(
    altar_client: AsgiClient, fake_services: SimpleNamespace
) -> None:
    _configure(fake_services)
    session_id = asyncio.run(_retained_run(fake_services, BRIDGE_CHAT))
    response = altar_client.get(f"/api/v1/bridge/sessions/{session_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["id"] == session_id
    assert payload["composer"] == {"pattern_id": "bridge_chat", "pattern_revision": "4", "guidance": _GUIDANCE}
    assert "PRIVATE_DRAFT_SENTINEL" not in payload["composer"]["guidance"]
    assert "PRIVATE_CONFIGURATION_SENTINEL" not in payload["composer"]["guidance"]


@pytest.mark.parametrize("revision", ["1", "2", "3"])
def test_older_current_revision_never_borrows_guidance_from_retained_webcrawler(
    altar_client: AsgiClient, fake_services: SimpleNamespace, revision: str
) -> None:
    _configure(fake_services, revision=revision)
    session_id = asyncio.run(_retained_run(fake_services, BRIDGE_CHAT_WEBCRAWLER))
    # Even a disagreeing read-only catalogue cannot choose the composer identity.
    fake_services.workflows = BuiltinWorkflowRegistry(workflows=(BRIDGE_CHAT_WEBCRAWLER,))
    for path in ("/api/v1/bridge", f"/api/v1/bridge/sessions/{session_id}"):
        response = altar_client.get(path)
        assert response.status_code == 200
        assert response.json()["composer"] == {
            "pattern_id": "bridge_chat",
            "pattern_revision": revision,
            "guidance": None,
        }


def test_inactive_registered_webcrawler_does_not_advertise_its_command(
    altar_client: AsgiClient, fake_services: SimpleNamespace
) -> None:
    _configure(fake_services, revision="1")
    registry = fake_services.run_engine.workflows
    assert registry.get_revision("bridge_chat", "4") is BRIDGE_CHAT_WEBCRAWLER
    assert not registry.is_active("bridge_chat", "4")
    response = altar_client.get("/api/v1/bridge")
    assert response.status_code == 200
    assert response.json()["composer"] == {"pattern_id": "bridge_chat", "pattern_revision": "1", "guidance": None}


@pytest.mark.parametrize("missing", ["profile", "engine_admission", "handler_admission"])
def test_webcrawler_identity_without_required_collaborator_has_no_guidance(
    altar_client: AsgiClient, fake_services: SimpleNamespace, missing: str
) -> None:
    _configure(fake_services)
    if missing == "profile":
        fake_services.run_engine.bridge_webcrawler = None
    elif missing == "engine_admission":
        fake_services.run_engine.webcrawler_admission = None
    else:
        fake_services.webcrawler_admission = None
    response = altar_client.get("/api/v1/bridge")
    assert response.status_code == 200
    assert response.json()["composer"] == {"pattern_id": "bridge_chat", "pattern_revision": "4", "guidance": None}


class _UnavailableRegistry(BuiltinWorkflowRegistry):
    @property
    def default(self) -> Workflow:
        message = "Default binding unavailable."
        raise RuntimeError(message)


@pytest.mark.parametrize("registry", [None, _UnavailableRegistry(workflows=(BRIDGE_CHAT,))])
def test_unavailable_admission_registry_does_not_fall_back_to_catalogue(
    altar_client: AsgiClient, fake_services: SimpleNamespace, registry: Any
) -> None:
    fake_services.run_engine.workflows = registry
    fake_services.workflows = BuiltinWorkflowRegistry(workflows=(BRIDGE_CHAT_WEBCRAWLER,))
    response = altar_client.get("/api/v1/bridge")
    assert response.status_code == 200
    assert response.json()["composer"] is None


@pytest.mark.parametrize("bound", [False, True])
def test_semantic_composer_describes_current_default_without_claiming_readiness(
    altar_client: AsgiClient,
    fake_services: SimpleNamespace,
    *,
    bound: bool,
) -> None:
    from lychd.domain.cortex.semantic_answer import SemanticAnswerBinding
    from tests.unit.domain.test_archive_semantic import MANIFEST, REFERENCE

    _configure(fake_services, revision="5")
    fake_services.run_engine.bridge_semantic = (
        SemanticAnswerBinding(manifest=MANIFEST, generation=REFERENCE, min_cosine=-0.5) if bound else None
    )
    session_id = asyncio.run(_retained_run(fake_services, BRIDGE_CHAT_ARCHIVE))
    response = altar_client.get(f"/api/v1/bridge/sessions/{session_id}")
    assert response.status_code == 200
    composer = response.json()["composer"]
    assert (composer["pattern_id"], composer["pattern_revision"]) == ("bridge_chat", "5")
    if bound:
        assert "Semantic public-note answers" in composer["guidance"]
        assert "partial" in composer["guidance"]
        assert "no tools" in composer["guidance"]
        assert "does not indicate" in composer["guidance"]
        assert "earlier conversation history" in composer["guidance"]
        assert str(REFERENCE.generation_id) not in composer["guidance"]
    else:
        assert composer["guidance"] is None
