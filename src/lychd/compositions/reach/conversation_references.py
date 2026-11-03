"""Conservative observations of positional references in the actual admitted anchor.

``anchor-order-v2`` accepts ASCII first through twelfth, with up to three distinct
coordinated ordinals followed by one unit. Units are the regular singular/plural
forms below. One top-level numbered list (starting at 1, consecutive or repeated
Markdown 1 markers), or one sibling ATX/bold heading sequence, supplies 2-12
unique same-unit numeric labels. Printed label values never determine position.
One separate English form observes ``what comes after [that/the/our/this]
first/opening [project] week/day/month/year`` when the anchor explicitly names
``our/the opening/first [project] <period>, <label>`` and then
``the next <same period> is <same-unit label>``. Optional parenthesized ASCII
dunder aliases are observed literally. This relation never becomes a selector.

Ambiguity, nested/competing structures, quoted/code lists, fence-bearing anchors
and visible truncation yield no observation. These hints identify text referents,
never goals, source truth or instructions. All offsets are Python character
offsets in unchanged text.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal

from lychd.compositions.reach.operator_model_wire import canonical_json
from lychd.compositions.reach.operator_wire import ReachHistoryEntry, ReachWorkerRequest

REFERENCE_PARSER_VERSION = "anchor-order-v2"
MAX_REFERENCE_ITEMS = 12
MAX_REFERENCE_SELECTIONS = 3
_MIN_REFERENCE_ITEMS = 2
_ANCHOR_LIMIT = 2000
_MAX_LABEL_DIGITS = 6
_SUCCESSOR_POSITION = 2
REFERENCE_ORDINALS = (
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "tenth",
    "eleventh",
    "twelfth",
)
_UNITS = ("week", "day", "month", "year", "chapter", "section", "stage", "step", "phase", "item", "interval", "part")
_ORDINAL = "|".join(REFERENCE_ORDINALS)
_UNIT = "|".join(_UNITS)
_LABEL = re.compile(rf"\b(?P<unit>{_UNIT})[ \t_-]*(?P<number>[0-9]{{1,{_MAX_LABEL_DIGITS}}})\b", re.IGNORECASE)
_EXPLICIT_LABEL = re.compile(rf"\b(?:{_UNIT})[ \t_-]*[0-9]", re.IGNORECASE)
_COORDINATION = rf"(?:{_ORDINAL})(?:[ \t]*(?:,[ \t]*(?:and[ \t]+)?|and[ \t]+)(?:the[ \t]+)?(?:{_ORDINAL}))*"
_REQUEST = re.compile(rf"\b(?P<ordinals>{_COORDINATION})[ \t]+(?P<unit>(?:{_UNIT})s?)\b", re.IGNORECASE)
_TRUNCATION = re.compile(
    r"\.\.\.|\N{HORIZONTAL ELLIPSIS}|\[(?:truncated|omitted|continued)[^]]*\]|"
    r"\b(?:part|message)[ \t]+[0-9]+[ \t]*(?:/|of)[ \t]*[0-9]+\b|"
    r"^[ \t]*[\[(]?[0-9]+/[0-9]+[\])]?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
_PERIOD = "week|day|month|year"
_SUCCESSOR_QUESTION = re.compile(
    rf"\bwhat[ \t]+comes[ \t]+after[ \t]+(?:(?:that|the|our|this)[ \t]+)?"
    rf"(?:first|opening)[ \t]+(?:project[ \t]+)?(?P<period>{_PERIOD})\b",
    re.IGNORECASE,
)
_RELATION_LABEL = rf"(?P<label>(?P<label_unit>{_UNIT})[ \t_-]*(?P<number>[0-9]{{1,{_MAX_LABEL_DIGITS}}}))\b"
_RELATION_ALIAS = r"(?:[ \t]*\((?P<alias>__[A-Za-z_][A-Za-z0-9_]{0,60}__)\))?"
_OPENING_PERIOD = re.compile(
    rf"\b(?:our|the)[ \t]+(?:opening|first)[ \t]+(?:project[ \t]+)?(?P<period>{_PERIOD})"
    rf"[ \t]*,[ \t]*{_RELATION_LABEL}{_RELATION_ALIAS}",
    re.IGNORECASE,
)
_NEXT_PERIOD = re.compile(
    rf"\bthe[ \t]+next[ \t]+(?P<period>{_PERIOD})[ \t]+is[ \t]+{_RELATION_LABEL}{_RELATION_ALIAS}",
    re.IGNORECASE,
)
_RELATION_UNCERTAINTY = re.compile(
    r"\b(?:not|no|never|false|instead|rather|if|unless|whether|might|may|could|would|perhaps|possibly|hypothetical|suppose|imagine|denied|rejected|example)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, kw_only=True)
class ReferenceHint:
    """A bounded observed label bound to literal question and anchor spans."""

    origin: Literal["reply_anchor", "continuation_anchor"]
    relation: Literal["position", "opening_successor"]
    parser_version: str
    anchor_event_id: str
    anchor_digest: str
    scope_start: int
    scope_end: int
    position: int
    unit: str
    label_unit: str
    label: str
    aliases: tuple[str, ...]
    question_start: int
    question_end: int
    anchor_start: int
    anchor_end: int


@dataclass(frozen=True)
class _Item:
    start: int
    end: int
    label_start: int
    label_end: int
    unit: str
    number: int
    aliases: tuple[str, ...]
    kind: str
    level: int
    marker: int


def _anchor(
    request: ReachWorkerRequest,
) -> tuple[Literal["reply_anchor", "continuation_anchor"], ReachHistoryEntry] | None:
    if request.reply_anchor is not None:
        if request.continuation_anchor is not None or request.reply_to_event_id != request.reply_anchor.event_id:
            return None
        return "reply_anchor", request.reply_anchor
    if request.reply_to_event_id is not None or request.continuation_anchor is None:
        return None
    return "continuation_anchor", request.continuation_anchor


def _question_positions(question: str) -> tuple[str, tuple[tuple[int, int, int], ...]] | None:
    # Quoted or relational ordinal expressions are outside this grammar.
    if re.search(
        r"[`\"'\N{LEFT DOUBLE QUOTATION MARK}\N{RIGHT DOUBLE QUOTATION MARK}\n]|\b(?:after|before|between|following|next|last|previous|either|or|not)\b",
        question,
        re.IGNORECASE,
    ):
        return None
    matches = list(_REQUEST.finditer(question))
    if len(matches) != 1 or not matches[0].group().isascii():
        return None
    match = matches[0]
    ordinals = tuple(re.finditer(rf"\b(?:{_ORDINAL})\b", match.group("ordinals"), re.IGNORECASE))
    all_ordinals = tuple(re.finditer(rf"\b(?:{_ORDINAL})\b", question, re.IGNORECASE))
    if len(ordinals) != len(all_ordinals) or not 1 <= len(ordinals) <= MAX_REFERENCE_SELECTIONS:
        return None
    positions = tuple(
        (
            REFERENCE_ORDINALS.index(item.group().casefold()) + 1,
            match.start("ordinals") + item.start(),
            match.start("ordinals") + item.end(),
        )
        for item in ordinals
    )
    if len({item[0] for item in positions}) != len(positions):
        return None
    return match.group("unit").casefold().removesuffix("s"), positions


def _line_item(line: str, offset: int) -> _Item | None:
    numbered = re.match(r"^(?P<marker>[0-9]{1,2})[.)][ \t]+(?P<title>.+)", line)
    heading = re.match(r"^(?P<level>#{1,6})[ \t]+(?P<title>.+)", line)
    bold = re.match(r"^\*\*(?P<title>[^\n]+?)\*\*(?:[ \t]*[:\N{EM DASH}\N{EN DASH}-]?[ \t]*[^\n]*)?\r?\n?$", line)
    structure = numbered or heading or bold
    if structure is None:
        return None
    title = structure.group("title")
    # Presentation markers may surround the label, but other prose may not precede it.
    labels = list(_LABEL.finditer(title))
    if len(labels) != 1 or title[: labels[0].start()].strip(" *`_"):
        return None
    label = labels[0]
    aliases = tuple(dict.fromkeys(re.findall(r"`([^`\n]{1,80})`|\{#([A-Za-z0-9_-]{1,80})\}", title)))
    observed_aliases = tuple(left or right for left, right in aliases)
    return _Item(
        start=offset,
        end=offset + len(line),
        label_start=offset + structure.start("title") + label.start(),
        label_end=offset + structure.start("title") + label.end(),
        unit=label.group("unit").casefold(),
        number=int(label.group("number")),
        aliases=observed_aliases[:MAX_REFERENCE_SELECTIONS],
        kind="numbered" if numbered is not None else "heading" if heading is not None else "bold",
        level=len(heading.group("level")) if heading is not None else 0,
        marker=int(numbered.group("marker")) if numbered is not None else 0,
    )


def _sequence_lines(text: str) -> tuple[_Item, ...] | None:
    items: list[_Item] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith(">"):
            if _LABEL.search(line) is not None:
                return None
        else:
            item = _line_item(line, offset)
            container = re.match(r"^\s*(?:[0-9]+[.)]|[-+*])[ \t]+", line)
            if item is None and (container is not None or _line_item(line.lstrip(), offset) is not None):
                return None
            if item is not None:
                items.append(item)
        offset += len(line)
    return tuple(items)


def _heading_interrupts(line: str, item: _Item) -> bool:
    if _line_item(line, 0) is not None:
        return False
    heading = re.match(r"^(#{1,6})[ \t]+", line)
    if heading is not None:
        return item.kind == "bold" or len(heading.group(1)) <= item.level
    return item.kind == "bold" and re.fullmatch(r"\*\*[^*\r\n]+\*\*[ \t]*:?[ \t]*", line) is not None


def _uninterrupted_scope(text: str, items: tuple[_Item, ...]) -> bool:
    lines = text[items[0].end : items[-1].start].splitlines()
    if items[0].kind == "numbered":
        markers = tuple(item.marker for item in items)
        return markers in (tuple(range(1, len(items) + 1)), (1,) * len(items)) and not any(
            line and not line[0].isspace() and _line_item(line, 0) is None for line in lines
        )
    # A different parent or sibling heading interrupts the one sequence scope.
    return not any(_heading_interrupts(line, items[0]) for line in lines)


def _sequence(text: str) -> tuple[_Item, ...] | None:
    if (
        not text
        or len(text) >= _ANCHOR_LIMIT
        or _TRUNCATION.search(text) is not None
        or re.search(r"`{3,}|~{3,}|<\s*/?\s*(?:pre|code)\b", text, re.IGNORECASE) is not None
        or any(not match.group("unit").isascii() for match in _LABEL.finditer(text))
    ):
        return None
    items = _sequence_lines(text)
    if items is None or not _MIN_REFERENCE_ITEMS <= len(items) <= MAX_REFERENCE_ITEMS:
        return None
    if len({(item.kind, item.level, item.unit) for item in items}) != 1 or len({item.number for item in items}) != len(
        items
    ):
        return None
    return items if _uninterrupted_scope(text, items) else None


def _positional_references(request: ReachWorkerRequest) -> tuple[ReferenceHint, ...]:
    selected_anchor = _anchor(request)
    positions = _question_positions(request.event.question)
    if selected_anchor is None or positions is None:
        return ()
    origin, anchor = selected_anchor
    items = _sequence(anchor.text)
    unit, selected = positions
    if items is None or items[0].unit != unit or any(position > len(items) for position, _, _ in selected):
        return ()
    # Current literal numeric targets already have their own selector precedence.
    # Abstaining also handles ranges/coordinations and overlong digits without
    # partial parsing or an unbounded integer conversion.
    if _EXPLICIT_LABEL.search(request.event.question) is not None:
        return ()
    digest = sha256(anchor.text.encode("utf-8")).hexdigest()
    return tuple(
        ReferenceHint(
            origin=origin,
            relation="position",
            parser_version=REFERENCE_PARSER_VERSION,
            anchor_event_id=anchor.event_id,
            anchor_digest=digest,
            scope_start=items[0].start,
            scope_end=items[-1].end,
            position=position,
            unit=unit,
            label_unit=unit,
            label=anchor.text[items[position - 1].label_start : items[position - 1].label_end],
            aliases=items[position - 1].aliases,
            question_start=start,
            question_end=end,
            anchor_start=items[position - 1].label_start,
            anchor_end=items[position - 1].label_end,
        )
        for position, start, end in selected
    )


def _successor_question(question: str) -> re.Match[str] | None:
    if (
        re.search(
            r"[`\"'\N{LEFT SINGLE QUOTATION MARK}\N{RIGHT SINGLE QUOTATION MARK}\N{LEFT DOUBLE QUOTATION MARK}\N{RIGHT DOUBLE QUOTATION MARK}\n]|\b(?:before|between|or|following)\b",
            question,
            re.IGNORECASE,
        )
        or _EXPLICIT_LABEL.search(question) is not None
        or _RELATION_UNCERTAINTY.search(question) is not None
    ):
        return None
    matches = list(_SUCCESSOR_QUESTION.finditer(question))
    if len(matches) != 1 or not matches[0].group().isascii():
        return None
    match = matches[0]
    references = re.finditer(rf"\b(?:{_ORDINAL}|opening|after|next)\b", question, re.IGNORECASE)
    return match if all(match.start() <= item.start() < item.end() <= match.end() for item in references) else None


def _successor_pair(text: str) -> tuple[re.Match[str], re.Match[str]] | None:
    if (
        not text
        or len(text) >= _ANCHOR_LIMIT
        or _TRUNCATION.search(text) is not None
        or _RELATION_UNCERTAINTY.search(text) is not None
        or re.search(
            r"[`\"'\N{LEFT SINGLE QUOTATION MARK}\N{RIGHT SINGLE QUOTATION MARK}\N{LEFT DOUBLE QUOTATION MARK}\N{RIGHT DOUBLE QUOTATION MARK}]|~{3,}|<\s*/?\s*(?:pre|code)\b|(?m:^[ \t]*(?:>|#|[-+*][ \t]|[0-9]+[.)][ \t]))",
            text,
            re.IGNORECASE,
        )
        is not None
    ):
        return None
    openings, following = list(_OPENING_PERIOD.finditer(text)), list(_NEXT_PERIOD.finditer(text))
    if len(openings) != 1 or len(following) != 1:
        return None
    opening, target = openings[0], following[0]
    if not opening.group().isascii() or not target.group().isascii() or opening.end() > target.start():
        return None
    labels = list(_LABEL.finditer(text))
    if (
        len(labels) != _SUCCESSOR_POSITION
        or len(list(_EXPLICIT_LABEL.finditer(text))) != _SUCCESSOR_POSITION
        or [item.span() for item in labels] != [opening.span("label"), target.span("label")]
    ):
        return None
    if (
        opening.group("period").casefold() != target.group("period").casefold()
        or opening.group("label_unit").casefold() != target.group("label_unit").casefold()
        or int(opening.group("number")) == int(target.group("number"))
        or (opening.group("alias") is not None and opening.group("alias") == target.group("alias"))
    ):
        return None
    period_mentions = re.findall(
        rf"\b(?:opening|first|next)[ \t]+(?:project[ \t]+)?(?:{_PERIOD})\b", text, re.IGNORECASE
    )
    return (opening, target) if len(period_mentions) == _SUCCESSOR_POSITION else None


def opening_successor(request: ReachWorkerRequest) -> ReferenceHint | None:
    """Observe only an explicit opening-to-next relation in the actual anchor.

    ``unit`` is the literal period unit; ``label_unit`` is independently observed
    on both printed labels. Their relationship is text, never a unit translation.
    """
    selected_anchor, question = _anchor(request), _successor_question(request.event.question)
    if selected_anchor is None or question is None:
        return None
    origin, anchor = selected_anchor
    pair = _successor_pair(anchor.text)
    if pair is None or pair[0].group("period").casefold() != question.group("period").casefold():
        return None
    opening, target = pair
    return ReferenceHint(
        origin=origin,
        relation="opening_successor",
        parser_version=REFERENCE_PARSER_VERSION,
        anchor_event_id=anchor.event_id,
        anchor_digest=sha256(anchor.text.encode("utf-8")).hexdigest(),
        scope_start=opening.start(),
        scope_end=target.end(),
        position=_SUCCESSOR_POSITION,
        unit=question.group("period").casefold(),
        label_unit=target.group("label_unit").casefold(),
        label=target.group("label"),
        aliases=(target.group("alias"),) if target.group("alias") is not None else (),
        question_start=question.start(),
        question_end=question.end(),
        anchor_start=target.start("label"),
        anchor_end=target.end("label"),
    )


def anchor_references(request: ReachWorkerRequest) -> tuple[ReferenceHint, ...]:
    """Observe one bounded positional or explicit successor relation, or abstain."""
    positional = _positional_references(request)
    if positional:
        return positional
    successor = opening_successor(request)
    return (successor,) if successor is not None else ()


def reference_payload(request: ReachWorkerRequest) -> list[dict[str, object]]:
    """Serialize the exact immutable hints as JSON-ready attributed observations."""
    values: list[dict[str, object]] = []
    for hint in anchor_references(request):
        value = asdict(hint)
        value["aliases"] = list(hint.aliases)
        values.append(value)
    return values


def reference_selectors(request: ReachWorkerRequest) -> tuple[str, ...]:
    """Supply only the observed labels to the bounded local section-selector seam."""
    return tuple(hint.label for hint in anchor_references(request) if hint.relation == "position")


def reference_digest(request: ReachWorkerRequest) -> str:
    """Bind exact hint values without storing anchor or question bodies in a trace."""
    return sha256(canonical_json(reference_payload(request)).encode("utf-8")).hexdigest()
