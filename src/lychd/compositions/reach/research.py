"""Bounded research proposals, transient source projections and host-owned citations.

Source bodies belong only to the acquisition/synthesis station's local variables.
These helpers neither acquire data nor turn attributed source text into instructions.
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from copy import deepcopy
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal, Self, cast

from pydantic import Field, field_validator, model_validator
from pydantic_ai.messages import ModelRequest, UserPromptPart
from pydantic_ai.models.wrapper import WrapperModel

from lychd.compositions.reach.documents import PublicCorpus, research_document_catalogue
from lychd.compositions.reach.documents_workflow import DocumentsRefused
from lychd.compositions.reach.expressions import REACTIONS, ConversationExpressions, GifId, Reaction
from lychd.compositions.reach.operator_model_wire import OperatorConversationProfile, canonical_json
from lychd.compositions.reach.operator_wire import ReachWorkerRequest, strict_json
from lychd.compositions.reach.research_wire import (
    OperatorResearchRequest,
    OperatorResearchResponse,
    SourceId,
    SourceReadResult,
)
from lychd.compositions.reach.schemas import Record

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from pydantic_ai import RunContext
    from pydantic_ai.messages import ModelMessage, ModelResponse
    from pydantic_ai.models import Model, ModelRequestParameters, StreamedResponse
    from pydantic_ai.settings import ModelSettings
    from pydantic_ai.usage import RequestUsage

MAX_RESEARCH_SOURCES = 4
MAX_RESEARCH_WEB_SOURCES = 2
MAX_RESEARCH_DOCUMENT_SOURCES = 3
MAX_RESEARCH_PLAN_CHARS = 500
MAX_RESEARCH_ANSWER_CHARS = 8000
TRANSIENT_RESEARCH_QUERY = "Form the admitted research answer from the transient source envelope."
UNVERIFIED_WEB_NOTICE = (
    "I couldn't verify the selected web evidence. Please provide a readable source or an excerpt "
    "before I make claims that depend on it."
)


class ResearchSynthesisModel(WrapperModel):
    """Attach source JSON only to detached outbound messages, never cached Agent history."""

    def __init__(self, wrapped: Model, prompt: str, *, authorize: Callable[[], None]) -> None:
        """Bind one local source projection and its current consumption check."""
        super().__init__(wrapped)
        self._prompt = prompt
        self._authorize = authorize

    def _outbound(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        detached = deepcopy(messages)
        prompts = [
            part
            for message in detached
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, UserPromptPart) and part.content == TRANSIENT_RESEARCH_QUERY
        ]
        if len(prompts) != 1:
            msg = "conversation_research_projection"
            raise DocumentsRefused(msg)
        prompts[0].content = self._prompt
        self._authorize()
        return detached

    def prepare_messages(
        self, messages: list[ModelMessage], model_request_parameters: ModelRequestParameters | None = None
    ) -> list[ModelMessage]:
        return self.wrapped.prepare_messages(deepcopy(messages), model_request_parameters)

    async def count_tokens(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> RequestUsage:
        return await self.wrapped.count_tokens(self._outbound(messages), model_settings, model_request_parameters)

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        return await self.wrapped.request(self._outbound(messages), model_settings, model_request_parameters)

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncGenerator[StreamedResponse]:
        async with self.wrapped.request_stream(
            self._outbound(messages), model_settings, model_request_parameters, run_context
        ) as response:
            yield response


class ResearchPlan(Record):
    """A bounded interpreted plan selects offered identities, never new locators."""

    kind: Literal["research"]
    text: str = Field(min_length=1, max_length=MAX_RESEARCH_PLAN_CHARS, repr=False)
    source_ids: tuple[SourceId, ...] = Field(min_length=1, max_length=MAX_RESEARCH_SOURCES)

    @field_validator("text")
    @classmethod
    def nonempty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            msg = "conversation_research_plan"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def bounded_selection(self) -> Self:
        if (
            len(set(self.source_ids)) != len(self.source_ids)
            or sum(item.startswith("web:") for item in self.source_ids) > MAX_RESEARCH_WEB_SOURCES
            or sum(item.startswith("doc:") for item in self.source_ids) > MAX_RESEARCH_DOCUMENT_SOURCES
        ):
            msg = "conversation_research_sources"
            raise ValueError(msg)
        return self


def research_catalogue(profile: OperatorConversationProfile, corpus: PublicCorpus) -> tuple[dict[str, str], ...]:
    """Expose only pinned public document metadata and operator-approved public URLs."""
    if not profile.research.enabled:
        return ()
    return research_document_catalogue(corpus) + tuple(
        {"id": f"web:{source.id}", "title": source.title, "url": source.url} for source in profile.research.sources
    )


def parse_research_plan(output: str, catalogue: tuple[dict[str, str], ...]) -> ResearchPlan | None:
    """Recognize research without widening the ordinary conversation JSON grammar."""
    parsed = strict_json(output.encode("utf-8"))
    value = cast("dict[str, Any]", parsed) if isinstance(parsed, dict) else None
    if value is None or value.get("kind") != "research":
        return None
    # JSON validation admits arrays as typed tuples while retaining strict scalar checks.
    plan = ResearchPlan.model_validate_json(canonical_json(value))
    if not set(plan.source_ids) <= {item["id"] for item in catalogue}:
        msg = "conversation_research_sources"
        raise ValueError(msg)
    return plan


def validate_research_response(
    request: OperatorResearchRequest,
    response: OperatorResearchResponse,
    catalogue: tuple[dict[str, str], ...],
) -> tuple[SourceReadResult, ...]:
    """Require the acknowledged occurrence and exactly the requested catalogue bindings."""
    response = OperatorResearchResponse.model_validate_json(response.model_dump_json())
    known = {item["id"]: item for item in catalogue}
    expected = {f"web:{item}" for item in request.source_ids}
    if (
        response.call_id != request.call_id
        or response.request_id != request.request_id
        or response.binding_digest != request.binding_digest
        or response.status != "ok"
        or response.reason is not None
        or len(response.sources) != len(expected)
        or {source.id for source in response.sources} != expected
    ):
        msg = "conversation_research_response"
        raise DocumentsRefused(msg)
    for source in response.sources:
        entry = known.get(source.id)
        if (
            entry is None
            or source.title != entry["title"]
            or source.url != entry["url"]
            or (source.status == "ok" and source.reason is not None)
            or (source.status != "ok" and source.reason is None)
            or (source.status == "ok" and source.excerpt_start + len(source.text) > source.source_chars)
        ):
            msg = "conversation_research_source"
            raise DocumentsRefused(msg)
    return response.sources


def _project_source(source: SourceReadResult, length: int) -> dict[str, object]:
    text = source.text[:length]
    return {
        **source.model_dump(mode="json"),
        "text": text,
        "projection_digest": sha256(text.encode("utf-8")).hexdigest(),
        "projection_truncated": len(text) < len(source.text),
    }


def synthesis_prompt(
    profile: OperatorConversationProfile,
    corpus: PublicCorpus,
    request: ReachWorkerRequest,
    plan: ResearchPlan,
    sources: tuple[SourceReadResult, ...],
    *,
    instructions: str,
    agent_subject_id: str | None = None,
) -> str:
    """Trim oldest history, then source projections; preserve original evidence digests."""
    selected = [
        item.model_dump(mode="json")
        for item in sorted(request.history, key=lambda item: (item.occurred_at, item.event_id))
    ]
    anchor = request.reply_anchor.model_dump(mode="json") if request.reply_anchor is not None else None
    for item in [*selected, *([anchor] if anchor is not None else [])]:
        if item["subject_id"] == agent_subject_id:
            item["subject_label"] = profile.persona_name
    omitted = 0
    lengths = [len(source.text) for source in sources]
    minimum_lengths = [
        next((index + 1 for index, char in enumerate(source.text) if not char.isspace()), 0) for source in sources
    ]
    budget = min(profile.max_input_chars, profile.max_context * 3)
    permitted = request.event.trigger != "command"
    expressions: dict[str, object] = {}
    if profile.expressions.enabled:
        expressions["available_expressions"] = {
            "reactions": list(REACTIONS) if permitted else [],
            "gifs": [
                {"id": item.id, "description": item.description} for item in profile.expressions.gifs if permitted
            ],
        }
    while True:
        prompt = canonical_json(
            {
                "question": request.event.question,
                "speaker_id": request.event.subject_id,
                "speaker_label": request.event.subject_label,
                "recent_messages": selected,
                "omitted_recent_messages": omitted,
                "reply_to_event_id": request.reply_to_event_id,
                "reply_anchor": anchor,
                "research_plan": plan.text,
                "research_sources": [
                    _project_source(source, length) for source, length in zip(sources, lengths, strict=True)
                ],
                "research_phase": "synthesis",
                "research_request_id": request.request_id,
                "research_evidence_rule": (
                    "If selected web sources exist and none has status ok, choose clarify. "
                    "Do not make claims that depend on unread web evidence, even when a local document was read."
                ),
                "corpus_digest": corpus.digest,
                **expressions,
            }
        )
        excess = len(instructions) + len(prompt) - budget
        if excess <= 0:
            return prompt
        if selected:
            selected.pop(0)
            omitted += 1
            continue
        reducible = [index for index, length in enumerate(lengths) if length > minimum_lengths[index]]
        if not reducible:
            msg = "conversation_budget"
            raise DocumentsRefused(msg)
        longest = max(reducible, key=lengths.__getitem__)
        lengths[longest] = max(minimum_lengths[longest], lengths[longest] - max(excess, 1))


class _ResearchDecision(Record):
    kind: Literal["answer", "clarify"]
    text: str = Field(min_length=1, max_length=MAX_RESEARCH_ANSWER_CHARS, repr=False)
    citations: tuple[SourceId, ...] = Field(default=(), max_length=MAX_RESEARCH_SOURCES)
    reaction: Reaction | None = None
    gif_id: GifId | None = None

    def validate_adoption(self) -> None:
        """Reject prose and selections that cannot be adopted after evidence admission."""
        if (
            not self.text.strip()
            or re.search(r"https?://", self.text, flags=re.IGNORECASE)
            or len(self.citations) != len(set(self.citations))
            or (self.kind != "answer" and (self.reaction is not None or self.gif_id is not None))
        ):
            msg = "conversation_research_answer"
            raise ValueError(msg)


class ResearchAnswer(Record):
    status: Literal["conversation", "clarify"]
    text: str = Field(min_length=1, max_length=MAX_RESEARCH_ANSWER_CHARS, repr=False)
    reaction: Reaction | None = None
    gif_id: GifId | None = None


def _label(title: str) -> str:
    return re.sub(r"([\\\[\]()*_`])", r"\\\1", " ".join(title.split()))


def _unavailable_notices(sources: tuple[SourceReadResult, ...]) -> list[str]:
    return [
        f"Unavailable source: {_label(source.title)} ({source.reason or source.status})."
        for source in sources
        if source.status != "ok"
    ]


def parse_research_answer(
    output: str,
    sources: tuple[SourceReadResult, ...],
    expressions: ConversationExpressions | None = None,
) -> ResearchAnswer:
    """Fence missing web evidence before adopting model prose, then resolve admitted citations."""
    value = strict_json(output.encode("utf-8"))
    decision = _ResearchDecision.model_validate_json(canonical_json(value))
    if len({source.id for source in sources}) != len(sources):
        msg = "conversation_research_citations"
        raise ValueError(msg)
    web_sources = tuple(source for source in sources if source.id.startswith("web:"))
    if web_sources and not any(source.status == "ok" for source in web_sources):
        return ResearchAnswer(
            status="clarify", text="\n\n".join([UNVERIFIED_WEB_NOTICE, *_unavailable_notices(sources)])
        )
    decision.validate_adoption()
    (expressions or ConversationExpressions()).validate_selection(decision.reaction, decision.gif_id)
    admitted = {source.id: source for source in sources if source.status == "ok"}
    if not set(decision.citations) <= admitted.keys() or (
        decision.kind == "answer" and admitted and not decision.citations
    ):
        msg = "conversation_research_citations"
        raise ValueError(msg)
    lines = [decision.text.strip()]
    if decision.citations:
        lines.append(
            "Sources: "
            + ", ".join(f"[{_label(admitted[item].title)}]({admitted[item].url})" for item in decision.citations)
        )
    lines.extend(_unavailable_notices(sources))
    text = "\n\n".join(lines)
    if len(text) > MAX_RESEARCH_ANSWER_CHARS:
        msg = "conversation_research_answer"
        raise ValueError(msg)
    return ResearchAnswer(
        status="conversation" if decision.kind == "answer" else "clarify",
        text=text,
        reaction=decision.reaction,
        gif_id=decision.gif_id,
    )
