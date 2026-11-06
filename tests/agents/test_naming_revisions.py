"""Named execution cannot fall through an older worker's unnamed Bridge manifest."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from pydantic import ConfigDict, create_model

from lychd.agents.router import Intent
from lychd.agents.workflows import (
    BRIDGE_CHAT,
    BRIDGE_CHAT_ARCHIVE,
    BRIDGE_CHAT_BOUND,
    BRIDGE_CHAT_SCOUT,
    BRIDGE_CHAT_SEMANTIC,
    BuiltinWorkflowRegistry,
    builtin_workflow_registry,
    resolve_named_workflow,
    resolve_pinned_workflow,
)
from lychd.domain.cortex.semantic_answer import SemanticAnswerBinding
from lychd.domain.naming import NamingSnapshot
from tests.scout_fixtures import PROMPT, scout_binding
from tests.unit.domain.test_archive_semantic import MANIFEST, PROFILE, REFERENCE

if TYPE_CHECKING:
    from lychd.agents.workflows.base import Workflow

_PROFILES = (BRIDGE_CHAT, BRIDGE_CHAT_BOUND, BRIDGE_CHAT_ARCHIVE, BRIDGE_CHAT_SCOUT, BRIDGE_CHAT_SEMANTIC)


def _naming() -> NamingSnapshot:
    return NamingSnapshot(
        magus_name="Zenith Runeweaver",
        primus_name="Aster Shadowdancer",
        magus_origin="manual",
        primus_origin="self_chosen",
        revision=1,
    )


def _intent(workflow: Workflow) -> Intent:
    revision = workflow.manifest.revision
    return Intent(
        session_id="session",
        run_id=str(UUID(int=1)),
        priority=70,
        prompt=PROMPT if revision == "4" else "hello",
        admitted_capability_key=None if revision == "1" else "chat:test",
        admitted_archive=PROFILE if revision == "3" else None,
        admitted_scout=scout_binding() if revision == "4" else None,
        admitted_semantic=SemanticAnswerBinding(manifest=MANIFEST, generation=REFERENCE, min_cosine=-0.5)
        if revision == "5"
        else None,
    )


@pytest.mark.parametrize("base", _PROFILES, ids=["1", "2", "3", "4", "5"])
def test_named_manifest_is_refused_by_old_registry_and_legacy_manifest_still_resolves(base: Workflow) -> None:
    current = builtin_workflow_registry()
    older = BuiltinWorkflowRegistry(workflows=(base,))
    legacy_snapshot = base.manifest.snapshot()
    named = resolve_named_workflow(current, base)
    named_snapshot = named.manifest.snapshot()
    assert named.manifest.revision == f"{base.manifest.revision}-naming1"
    assert named.manifest.implementation_revision != base.manifest.implementation_revision
    assert named.manifest.checkpoint_schema != base.manifest.checkpoint_schema
    assert base.manifest.snapshot() == legacy_snapshot
    assert resolve_pinned_workflow(older, workflow_name=base.name, snapshot=named_snapshot) is None
    assert resolve_pinned_workflow(current, workflow_name=base.name, snapshot=named_snapshot) is named
    assert resolve_pinned_workflow(current, workflow_name=base.name, snapshot=legacy_snapshot) is base
    assert not current.is_active(base.name, named.manifest.revision)
    assert not named.trigger.match(_intent(base))
    with pytest.raises(ValueError, match="cannot execute retained Bridge naming"):
        resolve_named_workflow(older, base)


@pytest.mark.parametrize("base", _PROFILES, ids=["1", "2", "3", "4", "5"])
def test_named_and_legacy_checkpoints_cannot_substitute_for_each_other(base: Workflow) -> None:
    named = resolve_named_workflow(builtin_workflow_registry(), base)
    legacy_intent = _intent(base)
    intent = legacy_intent.model_copy(update={"admitted_naming": _naming()})
    state = named.make_state(intent)
    restored = type(state).model_validate_json(state.model_dump_json())
    assert named.validate_state is not None
    named.validate_state(intent, restored)
    assert base.validate_state is not None
    with pytest.raises(ValueError, match=r"Legacy Bridge revision|checkpoint does not match"):
        base.validate_state(intent, restored)
    with pytest.raises(ValueError, match="Legacy Bridge revision"):
        base.make_state(intent)
    with pytest.raises(ValueError, match="requires its admitted naming snapshot"):
        named.make_state(legacy_intent)
    with pytest.raises(ValueError, match="requires its admitted naming snapshot"):
        named.validate_state(legacy_intent, restored)
    with pytest.raises(ValueError, match="does not match its admitted naming snapshot"):
        named.validate_state(intent, restored.model_copy(update={"naming": None}))


@pytest.mark.parametrize("base", _PROFILES, ids=["1", "2", "3", "4", "5"])
def test_unnamed_checkpoints_remain_compatible_with_strict_legacy_field_set(base: Workflow) -> None:
    intent = _intent(base)
    state = base.make_state(intent)
    assert "naming" not in state.model_dump()
    assert "naming" not in json.loads(state.model_dump_json())
    # The pre-naming schema has the same original fields and rejects unknown ones.
    legacy_fields: dict[str, Any] = {
        key: (field.annotation or Any, field) for key, field in type(state).model_fields.items() if key != "naming"
    }
    legacy_schema = create_model(
        "LegacyCheckpoint",
        __config__=ConfigDict(extra="forbid"),
        **legacy_fields,
    )
    legacy_schema.model_validate_json(state.model_dump_json())
    assert base.validate_state is not None
    base.validate_state(intent, type(state).model_validate_json(state.model_dump_json()))
