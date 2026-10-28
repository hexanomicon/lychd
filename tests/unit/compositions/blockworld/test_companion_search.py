"""Focused source, proposal and continuation boundaries for inactive Dump & Search."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from lychd.agents.router import Intent
from lychd.compositions.blockworld.companion_search import (
    MAX_DUMP_BYTES,
    SEARCH_SCOPE,
    SEARCH_SOURCE,
    CatalogueItem,
    CatalogueSnapshot,
    Dump,
    DumpSearchState,
    LiteralSearch,
    Report,
    RerankProposal,
    SearchRequest,
    decode_catalogue,
    dump_search_workflow,
    literal_search,
)

if TYPE_CHECKING:
    from lychd.agents.services import WorkflowServices

REQUEST_ID = "00000000-0000-4000-8000-000000000001"
RUN_ID = "00000000-0000-4000-8000-000000000002"


def snapshot(count: int = 1, *, total: int | None = None) -> CatalogueSnapshot:
    total = count if total is None else total
    return CatalogueSnapshot(
        source_id="test-catalogue",
        revision="fixture.1",
        total_count=total,
        truncated=total > count,
        items=tuple(
            CatalogueItem(
                id=f"fixture:castle_{index:03}",
                label=f"Castle {index}",
                characteristics=("stone walls", "small courtyard"),
                terms=("hrad",),
            )
            for index in range(count)
        ),
    )


def request(dump: CatalogueSnapshot, query: str = "castle", **changes: Any) -> SearchRequest:
    return SearchRequest.model_validate(
        {"request_id": REQUEST_ID, "binding": dump.binding.model_dump(), "query": query, **changes}
    )


class Source:
    def __init__(self, dump: CatalogueSnapshot) -> None:
        self.document = dump.model_dump_json().encode()
        self.calls = 0

    async def dump(self) -> bytes:
        self.calls += 1
        return self.document


def runtime(dump: CatalogueSnapshot, *, scopes: frozenset[str] = frozenset({SEARCH_SCOPE})) -> Any:
    source = Source(dump)
    workflow = dump_search_workflow(source, binding=dump.binding, session_id="session", principal="operator")
    intent = Intent(
        run_id=RUN_ID,
        session_id="session",
        prompt=request(dump).model_dump_json(),
        source=SEARCH_SOURCE,
        sigil_name="operator",
        sigil_scopes=frozenset({SEARCH_SCOPE}),
    )
    events: list[str] = []
    common = SimpleNamespace(
        sigil_provider=lambda: SimpleNamespace(name="operator", scopes=scopes),
        events=SimpleNamespace(emitter=Mock(return_value=SimpleNamespace(log=events.append))),
    )
    assert workflow.bind_deps is not None
    state = workflow.make_state(intent)
    deps = workflow.bind_deps(cast("WorkflowServices", common))
    return SimpleNamespace(
        source=source,
        workflow=workflow,
        intent=intent,
        state=state,
        deps=deps,
        events=events,
        context=SimpleNamespace(state=state, deps=deps),
    )


@pytest.mark.parametrize("query", ["castle", "hrad", "zámek", "CASTLES", "hrady"])
def test_castle_aliases_are_finite_literal_alternatives(query: str) -> None:
    dump = snapshot()
    result = literal_search(dump, request(dump, query))
    assert result.match_count == 1
    assert result.choices[0].id == "fixture:castle_000"
    assert result.ranking == "literal"
    assert result.binding == dump.binding


@pytest.mark.parametrize("query", [".*", "castle|tower", "[castle]", "(castle)", "castle$"])
def test_caller_regex_syntax_is_literal(query: str) -> None:
    dump = snapshot()
    assert literal_search(dump, request(dump, query)).match_count == 0


def test_dump_and_candidate_truncation_are_independent_and_explicit() -> None:
    dump = snapshot(30, total=100)
    result = literal_search(dump, request(dump, language="sk"))
    assert (result.dump_count, result.catalogue_total, result.match_count) == (30, 100, 30)
    assert result.catalogue_truncated
    assert result.candidates_truncated
    assert len(result.candidates) == 16
    assert len(result.choices) == len(result.spoken_choices) == 3
    assert result.spoken_choices[0].startswith("Možnosť 1:")
    assert "stone walls" in result.spoken_choices[0]
    assert [item.id for item in result.candidates] == sorted(item.id for item in result.candidates)


def test_empty_complete_catalogue_is_not_unavailable_or_invented_support() -> None:
    dump = snapshot(0)
    result = literal_search(dump, request(dump))
    assert result.match_count == 0
    assert result.candidates == result.choices == result.spoken_choices == ()
    assert not result.catalogue_truncated


@pytest.mark.parametrize("changes", [{"total_count": 0}, {"truncated": True}])
def test_completeness_cannot_lie(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        CatalogueSnapshot.model_validate({**snapshot().model_dump(), **changes})


def test_snapshot_rejects_duplicate_ids_and_more_than_256_items() -> None:
    dump = snapshot()
    with pytest.raises(ValidationError):
        CatalogueSnapshot.model_validate({**dump.model_dump(), "items": dump.items * 2, "total_count": 2})
    with pytest.raises(ValidationError):
        snapshot(257)


def test_bounded_strict_dump_decode() -> None:
    with pytest.raises(ValueError, match="byte limit"):
        decode_catalogue(b" " * (MAX_DUMP_BYTES + 1))
    with pytest.raises(ValueError, match="Duplicate"):
        decode_catalogue(b'{"source_id":"a","source_id":"b"}')
    with pytest.raises(ValueError, match="Non-finite"):
        decode_catalogue(b'{"total_count":NaN}')
    assert decode_catalogue(snapshot().model_dump_json().encode()).binding == snapshot().binding


@pytest.mark.parametrize("query", [" castle", "castle\n", "castle\u202e", "\x00"])
def test_query_and_display_text_reject_controls(query: str) -> None:
    with pytest.raises(ValidationError):
        request(snapshot(), query)
    with pytest.raises(ValidationError):
        CatalogueItem(id="fixture:safe", label=query, characteristics=("stone",))


def test_supplied_ids_only_ranking_is_bound_to_the_exact_candidate_packet() -> None:
    dump = snapshot(5)
    original = request(dump)
    first = literal_search(dump, original)
    proposal = RerankProposal(
        binding=dump.binding, candidate_digest=first.candidate_digest, ids=("fixture:castle_004", "fixture:castle_002")
    )
    result = literal_search(dump, request(dump, proposal=proposal))
    assert result.ranking == "supplied_proposal"
    assert [item.id for item in result.choices] == ["fixture:castle_004", "fixture:castle_002", "fixture:castle_000"]
    assert result.match_count == first.match_count
    assert result.candidate_digest == first.candidate_digest
    assert {item.id for item in result.candidates} == {item.id for item in first.candidates}


@pytest.mark.parametrize("fault", ["digest", "binding", "foreign_id", "changed_query"])
def test_stale_or_foreign_ranking_cannot_change_candidates(fault: str) -> None:
    dump = snapshot(3)
    first = literal_search(dump, request(dump))
    proposal = RerankProposal(
        binding=snapshot(2).binding if fault == "binding" else dump.binding,
        candidate_digest="sha256:" + "0" * 64 if fault == "digest" else first.candidate_digest,
        ids=("fixture:not_returned",) if fault == "foreign_id" else ("fixture:castle_002",),
    )
    with pytest.raises(ValueError, match="Ranking proposal"):
        literal_search(dump, request(dump, "hrad" if fault == "changed_query" else "castle", proposal=proposal))


def test_duplicate_ranking_ids_are_invalid() -> None:
    dump = snapshot()
    with pytest.raises(ValidationError):
        RerankProposal(
            binding=dump.binding,
            candidate_digest="sha256:" + "0" * 64,
            ids=("fixture:castle_000", "fixture:castle_000"),
        )


def test_factory_is_inactive_native_serial_pattern() -> None:
    rt = runtime(snapshot())
    assert rt.source.calls == 0
    assert rt.workflow.name == SEARCH_SOURCE
    assert rt.workflow.durable is False
    assert [node.key for node in rt.workflow.manifest.nodes] == ["dump", "literal-search", "report", "end"]
    assert [(edge.source, edge.target) for edge in rt.workflow.manifest.edges] == [
        ("dump", "literal-search"),
        ("literal-search", "report"),
        ("report", "end"),
    ]
    assert rt.workflow.validate_state is not None
    rt.workflow.validate_state(rt.intent, rt.state)


@pytest.mark.asyncio
async def test_dump_search_report_uses_one_read_and_reuses_retained_snapshot() -> None:
    rt = runtime(snapshot(5))
    assert isinstance(await Dump().run(rt.context), LiteralSearch)
    await Dump().run(rt.context)
    assert rt.source.calls == 1
    assert isinstance(await LiteralSearch().run(rt.context), Report)
    ended = await Report().run(rt.context)
    assert ended.data == rt.state.result
    assert len(rt.events) == 1
    reported = json.loads(rt.events[0])
    assert reported["match_count"] == 5
    assert reported["binding"]["digest"] == snapshot(5).binding.digest
    restored = DumpSearchState.model_validate_json(rt.state.model_dump_json())
    rt.workflow.validate_state(rt.intent, restored)


@pytest.mark.asyncio
async def test_missing_scope_refuses_before_source_read() -> None:
    rt = runtime(snapshot(), scopes=frozenset())
    with pytest.raises(ValueError, match="authority"):
        await Dump().run(rt.context)
    assert rt.source.calls == 0


@pytest.mark.asyncio
async def test_changed_dump_refuses_without_retaining_unbound_snapshot() -> None:
    rt = runtime(snapshot())
    rt.source.document = snapshot(2).model_dump_json().encode()
    with pytest.raises(ValueError, match="source closure"):
        await Dump().run(rt.context)
    assert rt.source.calls == 1
    assert rt.state.snapshot is None


@pytest.mark.asyncio
async def test_malformed_continuation_has_no_source_read() -> None:
    rt = runtime(snapshot())
    rt.state.request = request(snapshot(), "different")
    with pytest.raises(ValueError, match="checkpoint"):
        await Dump().run(rt.context)
    assert rt.source.calls == 0


@pytest.mark.parametrize("fault", ["input", "manifest", "run", "snapshot", "result"])
def test_resume_pins_manifest_input_snapshot_and_derived_result(fault: str) -> None:
    rt = runtime(snapshot(3))
    state = cast("DumpSearchState", rt.state)
    state.snapshot = snapshot(3)
    state.result = literal_search(state.snapshot, state.request)
    if fault == "input":
        state.prompt = request(snapshot(3), "hrad").model_dump_json()
    elif fault == "manifest":
        state.manifest_digest = "0" * 64
    elif fault == "run":
        state.run_id = REQUEST_ID
    elif fault == "snapshot":
        state.snapshot = snapshot(2)
    else:
        state.result = state.result.model_copy(update={"match_count": 99})
    with pytest.raises(ValueError, match=r"Search|Ranking|validation"):
        rt.workflow.validate_state(rt.intent, state)
    assert rt.source.calls == 0


@pytest.mark.parametrize("fault", ["source", "session", "binding", "malformed"])
def test_invalid_admission_never_reads_source(fault: str) -> None:
    rt = runtime(snapshot())
    changes: dict[str, Any] = {}
    if fault == "source":
        changes["source"] = "bridge"
    elif fault == "session":
        changes["session_id"] = "other"
    elif fault == "binding":
        changes["prompt"] = request(snapshot(2)).model_dump_json()
    else:
        changes["prompt"] = '{"request_id":"invalid","unknown":true}'
    intent = Intent.model_validate({**rt.intent.model_dump(), **changes})
    with pytest.raises(ValueError, match=r"Search|Ranking|validation"):
        rt.workflow.make_state(intent)
    assert rt.source.calls == 0


def test_cross_source_proposal_is_malformed_before_native_read() -> None:
    rt = runtime(snapshot())
    proposal = RerankProposal(binding=snapshot(2).binding, candidate_digest="sha256:" + "0" * 64, ids=())
    malformed = {**request(snapshot()).model_dump(mode="json"), "proposal": proposal.model_dump(mode="json")}
    intent = Intent.model_validate({**rt.intent.model_dump(), "prompt": json.dumps(malformed)})
    with pytest.raises(ValueError, match="Ranking proposal"):
        rt.workflow.make_state(intent)
    assert rt.source.calls == 0
