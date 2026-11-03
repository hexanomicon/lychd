"""Bounded research proposals, transient source projections and host-owned citations.

Source bodies belong only to the acquisition/synthesis station's local variables.
These helpers neither acquire data nor turn attributed source text into instructions.
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Literal, Self, cast
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_ai.messages import ModelRequest, UserPromptPart
from pydantic_ai.models.wrapper import WrapperModel

from lychd.compositions.reach.checkback import (
    COMPLETE_QUOTES_RULE,
    PUBLIC_TEXT_EVIDENCE_RULE,
    InputBudget,
    checkback_reserve,
    model_input_cost,
)
from lychd.compositions.reach.conversation_references import reference_payload
from lychd.compositions.reach.documents import (
    RESEARCH_PROJECTION_OMISSION,
    PublicCorpus,
    project_research_source,
    research_document_catalogue,
    research_projection_mode,
    retrieval_terms,
)
from lychd.compositions.reach.documents_workflow import DocumentsRefused
from lychd.compositions.reach.expressions import REACTIONS, ConversationExpressions, GifId, Reaction
from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    canonical_json,
)
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
MAX_RESEARCH_FOCUS_CHARS = 500
MAX_RESEARCH_ANSWER_CHARS = 8000
_WEB_REFERENCE_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_WEB_REFERENCE_ID = re.compile(r"(?<![\w:./-])[\w:./-]*web:[^\s<>\[\]()\"'`,;!?]+", re.IGNORECASE)
_WEB_URL_PROSE_SUFFIX = frozenset(".,;:!)]}>\"'`")
# Retrieval noise only: these catalogue/status words do not establish a topic.
# This approximate eligibility gate does not decide which offered source is relevant.
_WEB_METADATA_NOISE = frozenset(
    {"https", "www", "com", "jp", "web", "official", "operator", "http403", "news", "check", "may", "source", "blocked"}
)
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
    """Public acknowledgement and optional local selection focus confer no acquisition authority."""

    kind: Literal["research"]
    text: str = Field(min_length=1, max_length=MAX_RESEARCH_PLAN_CHARS, repr=False)
    focus: str | None = Field(default=None, min_length=1, max_length=MAX_RESEARCH_FOCUS_CHARS, repr=False)
    source_ids: tuple[SourceId, ...] = Field(min_length=1, max_length=MAX_RESEARCH_SOURCES)

    @field_validator("text")
    @classmethod
    def nonempty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            msg = "conversation_research_plan"
            raise ValueError(msg)
        return value

    @field_validator("focus")
    @classmethod
    def nonempty_focus(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            msg = "conversation_research_focus"
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


def _web_reference(text: str, catalogue: tuple[dict[str, str], ...]) -> bool:
    urls = {source["url"] for source in catalogue}
    lengths = {len(url) for url in urls}
    for match in _WEB_REFERENCE_URL.finditer(text):
        if match.start() and (text[match.start() - 1].isalnum() or text[match.start() - 1] == "_"):
            continue
        value = match.group()
        # A configured path may itself end in punctuation or contain parentheses.
        if value in urls:
            return True
        if any(
            value[:length] in urls and set(value[length:]) <= _WEB_URL_PROSE_SUFFIX
            for length in lengths
            if length < len(value)
        ):
            return True
    # A selector inside an unknown URL is part of that locator, not a separate reference.
    without_urls = _WEB_REFERENCE_URL.sub(" ", text)
    identities = {match.group().rstrip(".") for match in _WEB_REFERENCE_ID.finditer(without_urls)}
    return any(source["id"] in identities for source in catalogue)


def _web_catalogue_eligible(catalogue: tuple[dict[str, str], ...], request: ReachWorkerRequest) -> bool:
    """Retrieve the standing web catalogue without widening its authority or selecting a source.

    Current text and actual anchors supply approximate topic matches. Only exact
    references in the last two admitted history entries can recover an unanchored
    follow-up; older topics never keep the catalogue eligible by themselves.
    """
    current = (request.event.question,)
    if request.reply_anchor is not None:
        current += (request.reply_anchor.text,)
    if request.continuation_anchor is not None:
        current += (request.continuation_anchor.text,)
    recent = tuple(
        item.text for item in sorted(request.history, key=lambda item: (item.occurred_at, item.event_id))[-2:]
    )
    if any(_web_reference(text, catalogue) for text in (*current, *recent)):
        return True
    metadata = (
        retrieval_terms(
            " ".join(
                f"{source['id'].removeprefix('web:')} {source['title']} {urlsplit(source['url']).path}"
                for source in catalogue
            )
        )
        - _WEB_METADATA_NOISE
    )
    # Unknown locators and selector lookalikes must not qualify via token fragments.
    text = _WEB_REFERENCE_ID.sub(" ", _WEB_REFERENCE_URL.sub(" ", " ".join(current)))
    return bool(metadata & retrieval_terms(text))


def research_catalogue(
    profile: OperatorConversationProfile, corpus: PublicCorpus, request: ReachWorkerRequest | None = None
) -> tuple[dict[str, str], ...]:
    """Offer retrieved documents and an eligible standing web catalogue, never new authority."""
    if not profile.research.enabled:
        return ()
    context = tuple(item.text for item in request.history) if request is not None else ()
    if request is not None and request.reply_anchor is not None:
        context += (request.reply_anchor.text,)
    if request is not None and request.continuation_anchor is not None:
        context += (request.continuation_anchor.text,)
    documents = research_document_catalogue(
        corpus, question=request.event.question if request is not None else "", context=context
    )
    web = tuple(
        {"id": f"web:{source.id}", "title": source.title, "url": source.url} for source in profile.research.sources
    )
    return documents + (web if request is None or _web_catalogue_eligible(web, request) else ())


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


def model_research_source(full_projection: dict[str, object]) -> dict[str, object]:
    """Keep exact source evidence while leaving derived span proofs with the host projector."""
    return {key: value for key, value in full_projection.items() if key != "projection_spans"}


def _source_projection(
    source: SourceReadResult, length: int, mode: Literal["balanced", "complete_quotes"]
) -> dict[str, object]:
    """Never make an empty quotation projection available as successful citable evidence."""
    projected = project_research_source(source, length, projection_mode=mode)
    if mode == "complete_quotes" and source.status == "ok" and not cast("str", projected["text"]).strip():
        msg = "conversation_budget"
        raise DocumentsRefused(msg)
    return model_research_source(projected)


def synthesis_prompt(
    profile: OperatorConversationProfile,
    corpus: PublicCorpus,
    request: ReachWorkerRequest,
    plan: ResearchPlan,
    sources: tuple[SourceReadResult, ...],
    *,
    instructions: str,
    agent_subject_id: str | None = None,
    request_goals: tuple[str, ...] = (),
) -> str:
    """Budget exact source projections in the mode selected by the bound current question."""
    evidence_scope = {
        "version": "public-text-v1",
        "source_authority": "public_reference_text",
        "successful_read_proves": "source_bytes_obtained",
        "operator_runtime_observation": "not_supplied",
    }
    reference_hints = reference_payload(request)
    projection_mode = research_projection_mode(request.event.question)
    selected = [
        item.model_dump(mode="json")
        for item in sorted(request.history, key=lambda item: (item.occurred_at, item.event_id))
    ]
    anchor = request.reply_anchor.model_dump(mode="json") if request.reply_anchor is not None else None
    continuation = (
        request.continuation_anchor.model_dump(mode="json") if request.continuation_anchor is not None else None
    )
    for item in [
        *selected,
        *([anchor] if anchor is not None else []),
        *([continuation] if continuation is not None else []),
    ]:
        if item["subject_id"] == agent_subject_id:
            item["subject_label"] = profile.persona_name
    omitted = 0
    lengths = [len(source.text) for source in sources]
    minimum_lengths = [
        min(
            len(source.text),
            next((index + 1 for index, char in enumerate(source.text) if not char.isspace()), 0)
            + len(RESEARCH_PROJECTION_OMISSION),
        )
        for source in sources
    ]
    reserve = (
        checkback_reserve(
            profile,
            instructions,
            phase="synthesis",
            correction_phase="synthesis",
            question=request.event.question,
            runtime_claims=True,
        )
        if profile.checkback
        else InputBudget()
    )
    permitted = request.event.trigger != "command"
    expressions: dict[str, object] = {}
    if profile.expressions.enabled:
        expressions["available_expressions"] = {
            "reactions": list(REACTIONS) if permitted else [],
            "gifs": [
                {"id": item.id, "description": item.description} for item in profile.expressions.gifs if permitted
            ],
        }
    successful_ids = [source.id for source in sources if source.status == "ok"]
    web_sources = [source for source in sources if source.id.startswith("web:")]
    answer_example = bool(successful_ids) and (not web_sources or any(source.status == "ok" for source in web_sources))
    while True:
        prompt = canonical_json(
            {
                "question": request.event.question,
                "reference_hints": reference_hints,
                "request_goals": request_goals,
                "speaker_id": request.event.subject_id,
                "speaker_label": request.event.subject_label,
                "recent_messages": selected,
                "omitted_recent_messages": omitted,
                "reply_to_event_id": request.reply_to_event_id,
                "reply_anchor": anchor,
                "continuation_anchor": continuation,
                "research_plan": plan.text,
                "research_focus": plan.focus,
                "evidence_scope": evidence_scope,
                "research_sources": [
                    _source_projection(source, length, projection_mode)
                    for source, length in zip(sources, lengths, strict=True)
                ],
                "research_phase": "synthesis",
                "research_request_id": request.request_id,
                "research_evidence_rule": (
                    "Current explicit targets win. Resolve positions by anchor order; plan/focus provisional. "
                    "If all selected web reads fail, clarify. Claims need read support. Never quote omission markers or stitch gaps. "
                    "Other omissions do not invalidate complete visible quotes. "
                    + (COMPLETE_QUOTES_RULE if projection_mode == "complete_quotes" else "")
                    + PUBLIC_TEXT_EVIDENCE_RULE
                ),
                "research_output_contract": {
                    "required_keys": ["kind", "text", "citations"],
                    "answer_citation_ids": successful_ids,
                    "rule": (
                        "Answer now; no plan repeat, unasked extras or future offers. "
                        "On corrections, own the prior visible error and answer why without guessing hidden causes. "
                        "Use read text or name gaps. One JSON object. Cite only supporting status-ok IDs; "
                        "answer >=1 if answer_citation_ids nonempty; clarify may use []. "
                        "No HTTP text URLs; host links. reaction/gif_id: available_expressions only."
                    ),
                    "shape_example": {
                        "kind": "answer" if answer_example else "clarify",
                        "text": "<your source-grounded answer>" if answer_example else "<your clarification question>",
                        "citations": successful_ids[:1] if answer_example else [],
                    },
                },
                "corpus_digest": corpus.digest,
                **expressions,
            }
        )
        cost = model_input_cost(profile, instructions, prompt, phase="synthesis")
        char_excess, byte_excess, frame_excess = cost.excess(profile, reserve)
        if char_excess <= 0 and byte_excess <= 0 and frame_excess <= 0:
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
        # Estimate characters at the current exact encoding ratio; allocated budgets
        # still decrease on every pass even when source projections underfill.
        byte_reduction = (max(byte_excess, 0) * cost.input_chars + cost.payload_bytes - 1) // cost.payload_bytes
        frame_reduction = (max(frame_excess, 0) * cost.input_chars + cost.frame_bytes - 1) // cost.frame_bytes
        excess = max(char_excess, byte_reduction, frame_reduction, 1)
        reduction = (excess + len(reducible) - 1) // len(reducible)
        lengths[longest] = max(minimum_lengths[longest], lengths[longest] - max(reduction, 1))


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


def _inline_container_prefix_is_complex(line_prefix: str) -> bool:
    """Allow one plainly spaced list or quote marker, refusing ambiguous code indentation."""
    leading = line_prefix[: len(line_prefix) - len(line_prefix.lstrip(" \t"))]
    if "\t" in leading or re.match(r" {4}", leading) is not None:
        return True
    content = line_prefix[len(leading) :]
    marker = re.match(r"(?:>|[-+*]|[0-9]+[.)])([ \t]+)", content)
    if marker is None:
        return content.startswith(">")
    spacing = marker.group(1)
    nested = re.match(r"(?:>|[-+*][ \t]|[0-9]+[.)][ \t])", content[marker.end() :])
    return "\t" in spacing or re.match(r" {4}", spacing) is not None or nested is not None


def _inline_link_has_complex_container(text: str, prefix: str) -> bool:
    """Refuse ambiguous containers instead of interpreting their nested Markdown or HTML."""
    line_prefix = prefix[prefix.rfind("\n") + 1 :]
    return (
        _inline_container_prefix_is_complex(line_prefix)
        or re.search(r"<\s*/?\s*(?:pre|code)\b", text, flags=re.IGNORECASE) is not None
    )


def _inline_link_has_plain_context(text: str, start: int) -> bool:
    depth = 0
    code_marker = ""
    prefix = text[:start]
    if _inline_link_has_complex_container(text, prefix):
        return False
    for token in re.finditer(r"\\.|`+|~{3,}|\[|\]", prefix):
        value = token.group()
        if value.startswith("\\"):
            continue
        if value.startswith(("`", "~")):
            if not code_marker:
                code_marker = value
            elif code_marker == value:
                code_marker = ""
        elif not code_marker:
            depth = depth + 1 if value == "[" else max(0, depth - 1)
    return not (depth or code_marker)


def _simple_inline_link_labels(text: str) -> str:
    """Discard simple inline HTTP destinations while retaining their exact visible labels.

    Nested, escaped, image and code links remain untouched for the existing URL
    refusal. One pass cannot progressively simplify a complex nested construct.
    """
    pattern = r"(?<!!)(?<!\\)\[([^\[\]\\`\r\n]+)\]\(https?://[^\s()<>\[\]\\\"']+\)"

    def label(match: re.Match[str]) -> str:
        return match.group(1) if _inline_link_has_plain_context(text, match.start()) else match.group()

    return re.sub(pattern, label, text, flags=re.IGNORECASE)


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
    *,
    acknowledged_plan: str | None = None,
) -> ResearchAnswer:
    """Validate raw shape, render simple link labels, then fence unsupported prose and citations."""
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
    decision = decision.model_copy(update={"text": _simple_inline_link_labels(decision.text)})
    if acknowledged_plan is not None and " ".join(decision.text.split()) == " ".join(acknowledged_plan.split()):
        msg = "conversation_research_answer"
        raise ValueError(msg)
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
