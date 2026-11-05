"""Verify detached public project exports and offer bounded source metadata for research.

Project knowledge is pinned Git text, never a live checkout or execution authority.
Planning retrieves at most sixteen identities; source bodies enter only explicit reads.
"""

from __future__ import annotations

import json
import re
import unicodedata
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from math import log1p
from typing import Annotated, Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from lychd.compositions.reach.conversation_references import MAX_REFERENCE_SELECTIONS, REFERENCE_ORDINALS
from lychd.compositions.reach.operator_wire import MAX_HISTORY_BYTES, ReachHistoryEntry, ReachWorkerRequest
from lychd.compositions.reach.research_wire import MAX_DOCUMENT_SOURCE_CHARS, SourceReadResult
from lychd.compositions.reach.schemas import PolicyDigest, ReachPolicy, Record

MAX_DOCUMENT_BYTES = 524_288
MAX_CORPUS_BYTES = 67_108_864
MAX_CORPUS_DOCUMENTS = 8192
MAX_CORPUS_MANIFEST_BYTES = 8_388_608
MAX_CORPUS_PATH_CHARS = 200
MAX_RESEARCH_CATALOGUE_DOCUMENTS = 16
MAX_RESEARCH_SECTION_MATCH_CHARS = 320
LEGACY_MAX_CORPUS_BYTES = 2_097_152
LEGACY_MAX_DOCUMENTS = 32
MIN_EXCERPT_CHARS = 30
RESEARCH_PROJECTION_OMISSION = "\n[omitted]\n"
_REPO = "https://github.com/hexanomicon/lychd/blob/"
_PUBLIC_SITE = "https://hexanomicon.dev"
_RESEARCH_EXCERPT_CHARS = 4000
_RESEARCH_SELECTED_CONTEXT_CHARS = 600
_RESEARCH_PROJECTION_PREAMBLE_CHARS = 400
_RESEARCH_PROJECTION_SPANS = 48
_RESEARCH_PROJECTION_QUOTE_CHARS = 40
_RESEARCH_PROJECTION_ATTRIBUTION_CHARS = 120
_RESEARCH_NORMALIZED_RANKING_VERSION = 2
type _ResearchQuoteBlock = tuple[int, int, tuple[int, int] | None]
_URL = re.compile(r"https?://[^\s<>\[\]()\"']+")
_PATH = re.compile(r"(?<![A-Za-z0-9_./-])(?:doc:)?([A-Za-z0-9_./-]{1,200})(?![A-Za-z0-9_./-])")
_PUBLIC_ROOT_FILES = frozenset(
    {
        "AGENTS.md",
        "CONTRIBUTING.md",
        "Containerfile",
        "Containerfile.tests",
        "LICENSE",
        "Makefile",
        "README.md",
        "ROADMAP.md",
        "SECURITY.md",
        "THIRD_PARTY_NOTICES.md",
        "pyproject.toml",
        "uv.lock",
        "zensical.toml",
        ".containerignore",
        ".gitattributes",
        ".gitignore",
        ".markdownlint.json",
        ".nvmrc",
        ".python-version",
    }
)
_PUBLIC_SUBTREES = frozenset({"docs", "src", "tests", "scripts", "clients", "examples"})
_TEXT_SUFFIXES = frozenset(
    {
        ".md",
        ".txt",
        ".py",
        ".pyi",
        ".toml",
        ".json",
        ".yaml",
        ".yml",
        ".ini",
        ".cfg",
        ".conf",
        ".sh",
        ".bash",
        ".sql",
        ".js",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".jsx",
        ".svelte",
        ".css",
        ".html",
        ".xml",
        ".svg",
        ".kt",
        ".kts",
        ".java",
        ".gradle",
        ".properties",
        ".lock",
        ".lockfile",
        ".service",
        ".socket",
        ".timer",
        ".container",
        ".network",
        ".volume",
        ".pod",
        ".target",
        ".csv",
        ".tsv",
        ".rst",
        ".bat",
        ".jinja",
        ".j2",
        ".mako",
        ".typed",
        ".jsonl",
    }
)
_TEXT_FILENAMES = frozenset({"Containerfile", "Containerfile.tests", "Dockerfile", "Makefile", "LICENSE", "gradlew"})
_EXCLUDED_PARTS = frozenset({"node_modules", "venv", "__pycache__"})
_NAVIGATION_HEADINGS = frozenset({"contents", "table of contents", "navigation", "see also", "related links"})
_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "do",
        "does",
        "for",
        "from",
        "how",
        "i",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "what",
        "when",
        "where",
        "which",
        "with",
        "ako",
        "aj",
        "alebo",
        "bol",
        "bude",
        "co",
        "do",
        "je",
        "ked",
        "kde",
        "kto",
        "na",
        "nie",
        "o",
        "od",
        "pre",
        "pri",
        "sa",
        "si",
        "som",
        "su",
        "tak",
        "to",
        "v",
        "vo",
        "za",
        "ze",
    ]
)


def public_project_path(path: str) -> bool:
    """Close project selection to named public roots and text kinds, excluding hidden material."""
    if not 1 <= len(path) <= MAX_CORPUS_PATH_CHARS or re.fullmatch(r"[A-Za-z0-9_./-]+", path) is None:
        return False
    parts = path.split("/")
    if any(part in {"", ".", ".."} or part in _EXCLUDED_PARTS for part in parts):
        return False
    if len(parts) == 1:
        return path in _PUBLIC_ROOT_FILES
    public_subtree = parts[0] in _PUBLIC_SUBTREES or parts[:2] == [".github", "workflows"]
    if not public_subtree or any(part.startswith(".") for part in parts[1:]):
        return False
    filename = parts[-1]
    return filename in _TEXT_FILENAMES or "." + filename.rsplit(".", 1)[-1] in _TEXT_SUFFIXES


def decode_public_text(raw: bytes) -> str:
    """Require complete UTF-8 text without binary controls; do not sanitize source bytes."""
    value = raw.decode("utf-8", errors="strict")
    if any(unicodedata.category(char) in {"Cc", "Cs"} and char not in "\n\r\t" for char in value):
        msg = "corpus_text"
        raise ValueError(msg)
    return value


class CorpusDocument(Record):
    """One immutable public source binding, not a user-selected filesystem path."""

    path: str = Field(max_length=200)
    url: str = Field(max_length=360)
    sha256: PolicyDigest
    file: str = Field(pattern=r"^(?:[0-9]{3}\.md|[0-9]{4}\.txt)$")

    @model_validator(mode="after")
    def safe_path(self) -> Self:
        if not public_project_path(self.path):
            msg = "corpus_path"
            raise ValueError(msg)
        return self


class CorpusOmission(Record):
    """A candidate text path deliberately unavailable under the fixed export bounds."""

    path: str = Field(max_length=200)
    reason: Literal["document_limit", "not_text"]

    @model_validator(mode="after")
    def safe_path(self) -> Self:
        if not public_project_path(self.path):
            msg = "corpus_path"
            raise ValueError(msg)
        return self


class CorpusManifest(Record):
    """Bounded export whose URLs bind exactly to its source revision."""

    schema_version: Annotated[int, Field(ge=1, le=2)] = 1
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    documents: tuple[CorpusDocument, ...] = Field(min_length=1, max_length=MAX_CORPUS_DOCUMENTS)
    omissions: tuple[CorpusOmission, ...] = Field(default=(), max_length=MAX_CORPUS_DOCUMENTS)

    @model_validator(mode="after")
    def bindings(self) -> Self:
        if self.schema_version == 1 and (
            len(self.documents) > LEGACY_MAX_DOCUMENTS
            or self.omissions
            or any(
                re.fullmatch(r"(?:README\.md|CONTRIBUTING\.md|docs/[A-Za-z0-9_./-]+\.md)", item.path) is None
                or re.fullmatch(r"[0-9]{3}\.md", item.file) is None
                for item in self.documents
            )
        ):
            msg = "corpus_legacy"
            raise ValueError(msg)
        if len(self.documents) + len(self.omissions) > MAX_CORPUS_DOCUMENTS:
            msg = "corpus_limit"
            raise ValueError(msg)
        all_paths = [item.path for item in (*self.documents, *self.omissions)]
        if len(set(all_paths)) != len(all_paths):
            msg = "corpus_duplicate"
            raise ValueError(msg)
        for name in ("path", "file"):
            values = [getattr(document, name) for document in self.documents]
            if len(values) != len(set(values)):
                msg = "corpus_duplicate"
                raise ValueError(msg)
        if any(document.url != f"{_REPO}{self.source_revision}/{document.path}" for document in self.documents):
            msg = "corpus_url"
            raise ValueError(msg)
        return self


def parse_corpus_manifest(raw: bytes) -> CorpusManifest:
    """Parse the separately bounded manifest without widening the conversation wire."""
    if len(raw) > MAX_CORPUS_MANIFEST_BYTES:
        msg = "corpus_manifest_limit"
        raise ValueError(msg)

    def unique(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                msg = "duplicate_key"
                raise ValueError(msg)
            result[key] = value
        return result

    def invalid_constant(_value: str) -> Any:
        msg = "invalid_json"
        raise ValueError(msg)

    json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=unique, parse_constant=invalid_constant)
    return CorpusManifest.model_validate_json(raw)


@dataclass(frozen=True)
class PublicCorpus:
    """Verified detached bytes; search never accesses a filesystem or network."""

    manifest: CorpusManifest
    texts: tuple[str, ...]
    digest: str


def verify_corpus(manifest: CorpusManifest, contents: tuple[bytes, ...]) -> PublicCorpus:
    """Verify complete bounded source bytes before admitting a search corpus."""
    byte_limit = LEGACY_MAX_CORPUS_BYTES if manifest.schema_version == 1 else MAX_CORPUS_BYTES
    if len(contents) != len(manifest.documents) or sum(map(len, contents)) > byte_limit:
        msg = "corpus_limit"
        raise ValueError(msg)
    texts: list[str] = []
    for document, raw in zip(manifest.documents, contents, strict=True):
        if len(raw) > MAX_DOCUMENT_BYTES or sha256(raw).hexdigest() != document.sha256:
            msg = "corpus_content"
            raise ValueError(msg)
        texts.append(decode_public_text(raw))
    manifest_value = manifest.model_dump(mode="json")
    if manifest.schema_version == 1:
        manifest_value.pop("omissions")
    canonical = json.dumps(manifest_value, sort_keys=True, separators=(",", ":"))
    return PublicCorpus(manifest, tuple(texts), sha256(canonical.encode()).hexdigest())


def _normalized(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(char))


def retrieval_terms(value: str) -> frozenset[str]:
    """Normalize lexical retrieval terms without changing the supplied source text."""
    return frozenset(
        token for token in re.findall(r"[^\W_]+", _normalized(value)) if len(token) > 1 and token not in _STOP
    )


def validate_history(policy: ReachPolicy, request: ReachWorkerRequest) -> None:
    """Bound history to its conversation and, for DMs, the sender and this bot."""
    history = (
        request.history
        + ((request.reply_anchor,) if request.reply_anchor is not None else ())
        + ((request.continuation_anchor,) if request.continuation_anchor is not None else ())
    )
    if request.reply_anchor is not None and request.reply_anchor.event_id != request.reply_to_event_id:
        msg = "history_anchor_binding"
        raise ValueError(msg)
    event = request.event
    if request.continuation_anchor is not None and event.trigger != "followup":
        msg = "history_continuation_binding"
        raise ValueError(msg)
    if event.trigger in {"reply", "followup"}:
        anchor = request.reply_anchor if event.trigger == "reply" else request.continuation_anchor
        if (
            anchor is None
            or anchor.event_id != event.related_event_id
            or anchor.subject_id != policy.agent_subject_id
            or anchor.subject_id != event.related_subject_id
            or anchor.occurred_at != event.related_occurred_at
            or (
                event.trigger == "followup"
                and (request.reply_to_event_id is not None or request.reply_anchor is not None)
            )
        ):
            msg = "history_continuation_binding"
            raise ValueError(msg)
    if not history:
        return
    if (
        len(history) > policy.context_message_limit
        or sum(len(item.text.encode("utf-8")) for item in history) > MAX_HISTORY_BYTES
    ):
        msg = "history_limit"
        raise ValueError(msg)
    seen: set[str] = set()
    for item in history:
        age = (request.event.occurred_at - item.occurred_at).total_seconds()
        if (
            item.conversation_id != request.event.conversation_id
            or (
                request.event.trigger == "message"
                and item.subject_id not in (request.event.subject_id, policy.agent_subject_id)
            )
            or item.event_id in seen
            or age < 0
            or age > policy.context_max_age_seconds
            or any(unicodedata.category(char) in {"Cc", "Cs"} and char not in "\n\r\t" for char in item.text)
        ):
            msg = "history_binding"
            raise ValueError(msg)
        seen.add(item.event_id)


def _quote(value: str, limit: int = 300) -> str:
    # Keep source text visually quoted and prevent source markdown becoming structure.
    text = " ".join(value.split()).replace("`", "'")
    return text[:limit].replace("[", "(").replace("]", ")")


def context_excerpts(history: tuple[ReachHistoryEntry, ...]) -> tuple[Literal["context", "empty"], str]:
    """Quote supplied evidence; do not claim a model-generated summary."""
    if not history:
        return "empty", "No eligible context excerpts were supplied."
    lines = ["Selected context excerpts (no AI summary):"]
    newest = sorted(history, key=lambda item: (item.occurred_at, item.event_id), reverse=True)[:3]
    lines.extend(f"> {_quote(item.text)}" for item in reversed(newest))
    return "context", "\n\n".join(lines)


def search_documents(corpus: PublicCorpus, request: ReachWorkerRequest) -> tuple[Literal["docs", "empty"], str]:
    """Return at most three lexical matches, with bounded quotes and pinned citations."""
    question_terms = retrieval_terms(request.event.question)
    context = (
        request.history
        + ((request.reply_anchor,) if request.reply_anchor is not None else ())
        + ((request.continuation_anchor,) if request.continuation_anchor is not None else ())
    )
    context_terms = retrieval_terms(" ".join(item.text for item in context))
    ranked: list[tuple[int, str, CorpusDocument, str]] = []
    for document, text in zip(corpus.manifest.documents, corpus.texts, strict=True):
        terms = retrieval_terms(text)
        score = 10 * len(question_terms & terms) + len(context_terms & terms)
        if score:
            ranked.append((-score, document.path, document, text))
    ranked.sort(key=lambda item: (item[0], item[1]))
    if not ranked:
        return "empty", "No matching public documentation excerpts found."
    lines = ["Public documentation search excerpts:"]
    for _, _, document, text in ranked[:3]:
        # Start around the earliest matching query term when possible.
        lowered = _normalized(text)
        offsets = [lowered.find(term) for term in sorted(question_terms) if term in lowered]
        start = max(0, min(offsets, default=0) - 80)
        citation = f"[{document.path}]({document.url})"
        available = 1900 - len("\n\n".join(lines)) - len(citation) - 8
        if available < MIN_EXCERPT_CHARS:
            break
        lines.append(f"{citation}\n> {_quote(text[start:], min(300, available))}")
    return "docs", "\n\n".join(lines)


def _research_heading_title(value: str) -> str:
    """Remove heading markup while retaining the authored public label."""
    value = re.sub(r"\s*\{\s*#[^}]+\}\s*$", "", value)
    value = re.sub(r"(?<!\w):[A-Za-z0-9_-]+:", "", value)
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    return " ".join(value.strip(" #*").split())[:120]


def _research_headings(text: str) -> tuple[tuple[int, int, str, str], ...]:
    """Locate ATX headings and adjacent authored anchors outside headers and fenced code."""
    headings: list[tuple[int, int, str, str]] = []
    offset = 0
    frontmatter = text.startswith(("---\n", "---\r\n"))
    fence: tuple[str, int] | None = None
    adjacent_anchor: str | None = None
    for index, line in enumerate(text.splitlines(keepends=True)):
        stripped = line.strip()
        if frontmatter:
            if index and stripped == "---":
                frontmatter = False
        elif fence is not None:
            if re.fullmatch(rf"{re.escape(fence[0])}{{{fence[1]},}}\s*", stripped):
                fence = None
        elif re.match(r"^\s{0,3}(?:`{3,}|~{3,})", line):
            marker = re.match(r"`+|~+", stripped)
            if marker is not None:
                fence = (stripped[0], len(marker.group()))
            adjacent_anchor = None
        else:
            match = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*\r?\n?$", line)
            if match is not None:
                raw_title = match.group(2)
                explicit = re.search(r"\{\s*#([A-Za-z0-9_-]+)\s*\}\s*$", raw_title)
                title = _research_heading_title(raw_title)
                anchor = (
                    explicit.group(1)
                    if explicit is not None
                    else adjacent_anchor or re.sub(r"[^\w-]", "", title.casefold().replace(" ", "-"))
                )
                headings.append((offset, len(match.group(1)), title, anchor))
                adjacent_anchor = None
            elif stripped:
                anchor_match = re.fullmatch(r"<a\s+(?:id|name)=[\"']([A-Za-z0-9_-]+)[\"']\s*>\s*</a>", stripped)
                adjacent_anchor = anchor_match.group(1) if anchor_match is not None else None
        offset += len(line)
    return tuple(headings)


def _research_title(document: CorpusDocument, text: str) -> str:
    if not document.path.endswith(".md"):
        return document.path[:120]
    return next((title for _, level, title, _ in _research_headings(text) if level == 1 and title), document.path)[:120]


def _research_kickoff(question: str) -> bool:
    return (
        re.search(
            r"\bkick(?: us)?[ -]?off\b|\bstart (?:of )?(?:the )?project\b|\bproject start\b",
            _normalized(question),
        )
        is not None
    )


def _research_unit_kind_matches(requested: str, authored: str) -> bool:
    return requested == authored or requested == authored + "s" or authored == requested + "s"


def _research_catalogue_units(question: str) -> frozenset[str]:
    """Prefer the requested overview granularity over ancillary outcome nouns."""
    named = re.findall(r"\b(?:week|chapter|section|stage)s?\b", _normalized(question))
    return frozenset(named) or retrieval_terms(question)


def _research_catalogue_subtree_body(text: str, headings: tuple[tuple[int, int, str, str], ...], index: int) -> str:
    """Observe the unit's descendant bodies without counting heading metadata as content."""
    heading = headings[index]
    start = text.find("\n", heading[0])
    if start < 0:
        return ""
    start += 1
    parts: list[str] = []
    for descendant in headings[index + 1 :]:
        parts.append(text[start : descendant[0]])
        if descendant[1] <= heading[1]:
            return "".join(parts)
        line_end = text.find("\n", descendant[0])
        start = line_end + 1 if line_end >= 0 else len(text)
    parts.append(text[start:])
    return "".join(parts)


def _research_catalogue_children(
    text: str,
    headings: tuple[tuple[int, int, str, str], ...],
    parent: tuple[int, int, str, str],
    units: frozenset[str],
) -> tuple[tuple[int, int, str, str], ...]:
    """Observe substantive numbered units in one descendant branch of the named parent."""
    selected: list[tuple[int, int, str, str]] = []
    identities: list[frozenset[tuple[str, int, int]]] = []
    owners: set[int] = set()
    stack = [parent]
    first = headings.index(parent) + 1
    for index, heading in enumerate(headings[first:], start=first):
        if heading[1] <= parent[1]:
            break
        while stack[-1][1] >= heading[1]:
            stack.pop()
        targets = frozenset(
            target
            for target in _research_numbered_targets(f"{heading[2]} {heading[3]}")
            if target[1] == target[2] and any(_research_unit_kind_matches(unit, target[0]) for unit in units)
        )
        body = _research_catalogue_subtree_body(text, headings, index)
        substantive = (
            bool(body.strip()) and not _research_link_only(body) and heading[2].casefold() not in _NAVIGATION_HEADINGS
        )
        if targets and substantive:
            if len({target[1] for target in targets}) != 1:
                return ()
            selected.append(heading)
            identities.append(targets)
            owners.add(stack[-1][0])
        stack.append(heading)
    all_targets = [min(identity) for identity in identities]
    kinds = {target[0] for target in all_targets}
    numbers = [target[1] for target in all_targets]
    one_kind = all(_research_unit_kind_matches(first, second) for first in kinds for second in kinds)
    if len(owners) != 1 or not one_kind or len(set(numbers)) != len(numbers):
        return ()
    return tuple(selected)


def _research_catalogue_parents(
    text: str, headings: tuple[tuple[int, int, str, str], ...], question: str, units: frozenset[str]
) -> tuple[tuple[int, int, str, str], ...]:
    """Resolve name ambiguity only among non-navigation parents with matching authored units."""
    normalized = " ".join(re.findall(r"[^\W_]+", _normalized(question)))
    candidates: list[tuple[int, int, str, str]] = []
    for index, heading in enumerate(headings):
        if heading[2].casefold() in _NAVIGATION_HEADINGS or not any(
            re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized)
            for phrase in _research_heading_names(heading[2])
        ):
            continue
        end = headings[index + 1][0] if index + 1 < len(headings) else len(text)
        if _research_link_only(text[heading[0] : end].partition("\n")[2]):
            continue
        if _research_catalogue_children(text, headings, heading, units):
            candidates.append(heading)
    return tuple(candidates)


def _research_section_match(text: str, question: str) -> tuple[int, str]:
    """Describe matching authored structure only; never quote source bodies or infer a schedule."""
    headings = _research_headings(text)
    units = _research_catalogue_units(question)
    parents = _research_catalogue_parents(text, headings, question, units)
    parent = _research_named_heading(text, parents, question)
    if parent is None:
        return 0, ""
    heading_end = text.find("\n", parent[0])
    heading_end = heading_end if heading_end >= 0 else len(text)
    if heading_end - parent[0] > MAX_RESEARCH_SECTION_MATCH_CHARS:
        return 0, ""
    children = _research_catalogue_children(text, headings, parent, units)
    if not children:
        return 0, ""
    description = f"Parent heading (excerpt): {parent[2]}; matching sections: {len(children)}; examples (sample): "
    if len(description) > MAX_RESEARCH_SECTION_MATCH_CHARS:
        return 0, ""
    samples = sorted({0, len(children) // 2, len(children) - 1})
    for index in samples:
        child = children[index]
        label = child[2]
        anchored = f"{label} [#{child[3]}]"
        label = anchored if len(description) + len(anchored) <= MAX_RESEARCH_SECTION_MATCH_CHARS else label
        addition = (" | " if index != samples[0] else "") + label
        if len(description) + len(addition) > MAX_RESEARCH_SECTION_MATCH_CHARS:
            break
        description += addition
    return len(children), description


def _research_ranking_fields(
    document: CorpusDocument, text: str
) -> tuple[frozenset[str], frozenset[str], Counter[str]]:
    """Keep authored title credit distinct from a fallback display label."""
    title = (
        next((title for _, level, title, _ in _research_headings(text) if level == 1 and title), "")
        if document.path.endswith(".md")
        else ""
    )
    body = Counter(
        token for token in re.findall(r"[^\W_]+", _normalized(text)) if len(token) > 1 and token not in _STOP
    )
    return retrieval_terms(document.path), retrieval_terms(title), body


def _research_normalized_scores(
    corpus: PublicCorpus, question_terms: frozenset[str], context_terms: frozenset[str]
) -> tuple[float, ...]:
    """Compute version 2 lexical scores from this immutable corpus, without retained state.

    Document frequency discounts ubiquitous terms; saturating field frequency and
    body-length normalization keep repetition from dominating relevance. A path
    used as a fallback label receives no independent authored-title credit.
    Two passes retain only query-term statistics, not a second corpus-sized index.
    """
    document_count = len(corpus.manifest.documents)
    if not document_count:
        return ()
    query_terms = question_terms | context_terms
    frequencies: Counter[str] = Counter()
    total_length = 0
    for document, text in zip(corpus.manifest.documents, corpus.texts, strict=True):
        path_terms, title_terms, body = _research_ranking_fields(document, text)
        total_length += body.total()
        frequencies.update((path_terms | title_terms | body.keys()) & query_terms)
    mean_length = total_length / document_count or 1.0
    # Sorted accumulation makes equal scores independent of process hash order.
    terms = tuple(sorted(query_terms))
    weights = {term: 1.0 if term in question_terms else 0.25 for term in terms}
    inverse_frequency = {
        term: log1p((document_count - frequencies[term] + 0.5) / (frequencies[term] + 0.5)) for term in terms
    }
    scores: list[float] = []
    for document, text in zip(corpus.manifest.documents, corpus.texts, strict=True):
        path_terms, title_terms, body = _research_ranking_fields(document, text)
        normalizer = 0.25 + 0.75 * body.total() / mean_length
        score = 0.0
        for term in terms:
            frequency = 8 * (term in path_terms) + 4 * (term in title_terms) + body[term] / normalizer
            score += weights[term] * inverse_frequency[term] * frequency / (1 + frequency)
        scores.append(score)
    return tuple(scores)


def research_document_catalogue(
    corpus: PublicCorpus,
    *,
    question: str = "",
    context: tuple[str, ...] = (),
    ranking_version: Literal[1, 2] = 1,
) -> tuple[dict[str, str], ...]:
    """Rank exact references and numeric targets before matching authored unit structure and lexical terms.

    Optional section_match is bounded, sampled heading metadata, never read body
    evidence. Source selection and the delivered-plan acquisition gate remain separate.
    Version 1 preserves the original lexical score; version 2 normalizes frequency
    and length without changing stronger selection tiers or no-query authored order.
    """
    if type(ranking_version) is not int or ranking_version not in (1, 2):
        msg = "research_ranking_version"
        raise ValueError(msg)
    exact_question = set(research_document_matches(corpus, (question,)))
    exact_context = set(research_document_matches(corpus, context))
    question_terms, context_terms = retrieval_terms(question), retrieval_terms(" ".join(context))
    numbered_question = _research_numbered_targets(_URL.sub(" ", question))
    kickoff = _research_kickoff(question)
    if kickoff:
        question_terms |= frozenset({"roadmap", "milestone", "milestones"})
    normalized_scores = (
        _research_normalized_scores(corpus, question_terms, context_terms)
        if ranking_version == _RESEARCH_NORMALIZED_RANKING_VERSION and (question or context)
        else ()
    )
    ranked: list[tuple[int, int, int, float, str, dict[str, str]]] = []
    for index, (document, text) in enumerate(zip(corpus.manifest.documents, corpus.texts, strict=True)):
        title = _research_title(document, text)
        source_id = f"doc:{document.path}"
        route = kickoff and document.path in {"ROADMAP.md", "docs/roadmap.md"}
        exact = 3 if source_id in exact_question else 2 if source_id in exact_context else int(route)
        section_matches = (
            len(
                _research_numbered_matches(
                    numbered_question,
                    frozenset(
                        target
                        for _, _, heading, anchor in _research_headings(text)
                        for target in _research_numbered_targets(f"{heading} {anchor}")
                    ),
                )
            )
            if numbered_question and document.path.endswith(".md")
            else 0
        )
        structural_matches, section_match = (
            _research_section_match(text, question) if question and document.path.endswith(".md") else (0, "")
        )
        if normalized_scores:
            score = normalized_scores[index]
        else:
            path_terms, title_terms, content_terms = (
                retrieval_terms(document.path),
                retrieval_terms(title),
                retrieval_terms(text),
            )
            score = (
                24 * len(question_terms & path_terms)
                + 12 * len(question_terms & title_terms)
                + 3 * len(question_terms & content_terms)
                + 4 * len(context_terms & path_terms)
                + 2 * len(context_terms & title_terms)
                + len(context_terms & content_terms)
            )
        metadata = {"id": source_id, "title": title, "url": document.url}
        if section_match:
            metadata["section_match"] = section_match
        if exact or section_matches or structural_matches or score or not (question or context):
            ranked.append(
                (
                    -exact,
                    -section_matches,
                    -structural_matches,
                    -score,
                    document.path,
                    metadata,
                )
            )
    # Preserve the small legacy catalogue's authored order for callers without a query.
    if question or context:
        ranked.sort(key=lambda item: item[:5])
    return tuple(item[5] for item in ranked[:MAX_RESEARCH_CATALOGUE_DOCUMENTS])


def _research_site_url(path: str) -> str | None:
    if not path.startswith("docs/") or not path.endswith(".md"):
        return None
    route = path.removeprefix("docs/")
    if route.endswith("/index.md") or route == "index.md":
        route = route.removesuffix("index.md")
    else:
        route = route.removesuffix(".md") + "/"
    return f"{_PUBLIC_SITE}/{route}"


def _research_urls(texts: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(match.group().rstrip(".,;:!") for text in texts for match in _URL.finditer(text))


def _research_url_matches(document: CorpusDocument, value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if parsed.query or "\\" in value or any(ord(char) < ord("!") for char in value):
        return False
    locator = value.split("#", 1)[0]
    return locator in (document.url, _research_site_url(document.path))


def research_document_matches(corpus: PublicCorpus, texts: tuple[str, ...]) -> tuple[str, ...]:
    """Resolve at most sixteen exact public URLs or known project paths, without fetching."""
    result: list[str] = []
    by_path = {document.path: document for document in corpus.manifest.documents}
    by_url = {
        locator: document
        for document in corpus.manifest.documents
        for locator in (document.url, _research_site_url(document.path))
        if locator is not None
    }
    for text in texts:
        references = [
            (match.start(), by_url.get(match.group().rstrip(".,;:!").split("#", 1)[0])) for match in _URL.finditer(text)
        ]
        # Remove URLs before path matching: an unpinned URL is not an exact path reference.
        references.extend(
            (match.start(), by_path.get(match.group(1).rstrip(".")))
            for match in _PATH.finditer(_URL.sub(lambda match: " " * len(match.group()), text))
        )
        for _, document in sorted(references, key=lambda item: item[0]):
            if document is None:
                continue
            source_id = f"doc:{document.path}"
            if source_id not in result:
                result.append(source_id)
            if len(result) == MAX_RESEARCH_CATALOGUE_DOCUMENTS:
                return tuple(result)
    return tuple(result)


def _research_source_start(text: str, path: str, question: str) -> int:
    """Prefer an explicitly named symbol's declaration, then the strongest lexical window."""
    query = _URL.sub(" ", question).replace(path, " ")
    identifiers = {
        match.group()
        for match in re.finditer(r"\b[A-Za-z_][A-Za-z0-9_]*\b", query)
        if "_" in match.group() or any(char.isupper() for char in match.group()[1:])
    }
    for identifier in sorted(identifiers, key=lambda value: (-len(value), value)):
        symbol = re.escape(identifier)
        declaration = re.search(
            rf"(?m)^[ \t]*(?:(?:export[ \t]+)?(?:default[ \t]+)?(?:async[ \t]+)?(?:def|class|function|interface|type|const|let|val|fun)[ \t]+{symbol}\b|{symbol}[ \t]*(?::[^=\n]+)?=)",
            text,
        )
        occurrence = declaration or re.search(rf"\b{symbol}\b", text)
        if occurrence is not None:
            return max(0, occurrence.start() - 300)
    terms = retrieval_terms(query)
    hits = [
        (match.start(), _normalized(match.group()))
        for match in re.finditer(r"(?<!\w)[^\W_]+(?!\w)", text)
        if _normalized(match.group()) in terms
    ]
    counts: dict[str, int] = {}
    right = 0
    best_score, best_start = 0, 0
    for offset, term in hits:
        while right < len(hits) and hits[right][0] < offset + _RESEARCH_EXCERPT_CHARS - 300:
            selected = hits[right][1]
            counts[selected] = counts.get(selected, 0) + 1
            right += 1
        if len(counts) > best_score:
            best_score, best_start = len(counts), max(0, offset - 300)
        counts[term] -= 1
        if not counts[term]:
            del counts[term]
    return best_start


def _research_link_only(body: str) -> bool:
    """Recognize link lists and their anchor markup without relying on a navigation title."""
    without_links = re.sub(r"\[[^]\n]+\]\([^\n)]+\)", "", body)
    without_links = re.sub(r"<a\b[^>\n]*>\s*</a>", "", without_links)
    without_links = re.sub(r"(?m)^\s*\d+[.)]\s+", "", without_links)
    return without_links != body and re.search(r"\w", without_links) is None


def _research_ranked_heading(
    text: str, headings: tuple[tuple[int, int, str, str], ...], terms: frozenset[str], *, kickoff: bool, query: str
) -> tuple[int, int, str, str] | None:
    """Rank substantive headings by opening intent, then ordinary lexical overlap."""
    ranked: list[tuple[int, int, int, tuple[int, int, str, str]]] = []
    for index, heading in enumerate(headings):
        body_end = headings[index + 1][0] if index + 1 < len(headings) else len(text)
        body = text[heading[0] : body_end].partition("\n")[2]
        if heading[2].casefold() in _NAVIGATION_HEADINGS or _research_link_only(body):
            continue
        heading_terms = _research_heading_terms(heading[2], query)
        kickoff_rank = 0
        if kickoff:
            if heading_terms & {"welcome", "onboarding", "kickoff"} or {"getting", "started"} <= heading_terms:
                kickoff_rank = 2
            elif "formation" in heading_terms:
                kickoff_rank = 1
        overlap = len(terms & heading_terms)
        if kickoff_rank or overlap:
            ranked.append((-kickoff_rank, -overlap, heading[0], heading))
    return min(ranked, key=lambda item: item[:3])[3] if ranked else None


def _research_heading_names(value: str) -> tuple[str, ...]:
    """Keep authored title segments while ignoring code literals and numeric decorations."""
    title = re.sub(r"`+[^`]+`+|(?<!\w)_[A-Za-z0-9_]+(?!\w)", " ", value)
    title = re.sub(r"\(\s*[0-9]+(?:\s*[-\N{EN DASH}\N{EM DASH}]\s*[0-9]+)?\s*\)", " ", title)
    parts = [title, *re.split(r"[\N{MIDDLE DOT}|]|\s[-\N{EN DASH}\N{EM DASH}]\s|:\s+", title)]
    return tuple(
        phrase
        for part in parts
        if (phrase := " ".join(re.findall(r"[^\W_]+", _normalized(part)))) and re.search(r"[^\W\d_]", phrase)
    )


def _research_named_heading(
    text: str, headings: tuple[tuple[int, int, str, str], ...], query: str
) -> tuple[int, int, str, str] | None:
    """Recognize one whole authored heading phrase, rather than an incidental shared word."""
    normalized = " ".join(re.findall(r"[^\W_]+", _normalized(query)))
    matches: list[tuple[int, int, str, str]] = []
    for index, heading in enumerate(headings):
        end = headings[index + 1][0] if index + 1 < len(headings) else len(text)
        if (
            heading[2].casefold() not in _NAVIGATION_HEADINGS
            and not _research_link_only(text[heading[0] : end].partition("\n")[2])
            and any(
                re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized)
                for phrase in _research_heading_names(heading[2])
            )
        ):
            matches.append(heading)
    return matches[0] if len(matches) == 1 else None


def _research_ancestor_start(
    text: str,
    headings: tuple[tuple[int, int, str, str], ...],
    selected: tuple[int, int, str, str],
    *,
    end: int,
    limit: int,
) -> int | None:
    """Retain the owning section while reserving a bounded opening of the selected child.

    A document title alone adds no section ownership. Refuse a child whose owner
    cannot accompany its opening inside the existing contiguous read budget.
    """
    parent = next(
        (heading for heading in reversed(headings) if heading[0] < selected[0] and heading[1] < selected[1]), None
    )
    if parent is None or parent[1] == 1:
        return selected[0]
    heading_end = text.find("\n", selected[0], end)
    body_start = heading_end + 1 if heading_end >= 0 else end
    body = re.search(r"\S", text[body_start:end])
    body_end = body_start + (body.start() if body is not None else 0) + MIN_EXCERPT_CHARS
    opening_end = min(end, max(selected[0] + _RESEARCH_SELECTED_CONTEXT_CHARS, body_end))
    return parent[0] if opening_end - parent[0] <= limit else None


def _research_numbered_targets(value: str) -> frozenset[tuple[str, int, int]]:
    """Resolve numbered labels, coordinated lists and bounded ranges without expanding integers."""
    normalized = _normalized(value)
    targets: set[tuple[str, int, int]] = set()
    consumed_until = 0
    for match in re.finditer(r"\b([a-z]+)[ \t_-]*([0-9]{1,6})\b", normalized):
        if match.start() < consumed_until:
            continue
        label, first = match.group(1), int(match.group(2))
        tail = normalized[match.end() :]
        interval = re.match(r"[ \t]*(?:[-\N{EN DASH}]|to|through)[ \t]*(?:([a-z]+)[ \t_-]*)?([0-9]{1,6})\b", tail)
        if interval is not None and (
            interval.group(1) is None or _research_unit_kind_matches(label, interval.group(1))
        ):
            last = int(interval.group(2))
            consumed_until = match.end() + interval.end()
            if first <= last:
                targets.add((label, first, last))
            continue
        targets.add((label, first, first))
        while adjacent := re.match(r"\s*(?:/|,(?:\s*and)?|and)\s*([0-9]{1,6})\b", tail):
            number = int(adjacent.group(1))
            targets.add((label, number, number))
            tail = tail[adjacent.end() :]
    return frozenset(targets)


def _research_numbered_matches(
    requested: frozenset[tuple[str, int, int]], authored: frozenset[tuple[str, int, int]]
) -> frozenset[tuple[str, int, int]]:
    """Match requested intervals only against available labels, allowing regular plurals."""
    return frozenset(
        target
        for target in authored
        if any(
            _research_unit_kind_matches(label, target[0]) and first <= target[1] and target[2] <= last
            for label, first, last in requested
        )
    )


def _research_ordinal_scope(
    headings: tuple[tuple[int, int, str, str], ...],
    available: tuple[tuple[int, int, str, str], ...],
    query: str,
    excluded: frozenset[str],
) -> tuple[tuple[int, int, str, str], ...] | None:
    """Use a unique named parent branch; unrelated named branches cannot establish ordinal scope."""
    terms = retrieval_terms(query) - excluded
    named: list[tuple[int, int, tuple[tuple[int, int, str, str], ...]]] = []
    names: dict[int, frozenset[str]] = {}
    boundary = max((heading[0] for heading in headings), default=-1) + 1
    deepest = max((heading[1] for heading in available), default=0)
    positions = [heading[0] for heading in available]
    ends: dict[int, int] = {}
    stack: list[tuple[int, int, str, str]] = []
    for heading in headings:
        while stack and stack[-1][1] >= heading[1]:
            ends[stack.pop()[0]] = heading[0]
        stack.append(heading)
    for parent in headings:
        if parent[1] >= deepest:
            continue
        name = _research_heading_terms(parent[2], query) - excluded
        if not terms & name:
            continue
        end = ends.get(parent[0], boundary)
        children = available[bisect_right(positions, parent[0]) : bisect_left(positions, end)]
        named.append((parent[0], end, children))
        names[parent[0]] = name
    if not named:
        return available
    specific: list[tuple[int, int, tuple[tuple[int, int, str, str], ...]]] = []
    for parent in named:
        if specific and specific[-1][0] < parent[0] < specific[-1][1]:
            if not terms & (names[parent[0]] - names[specific[-1][0]]):
                continue
            specific.pop()
        specific.append(parent)
    return specific[0][2] if len(specific) == 1 and specific[0][2] else None


def _research_ordinal_sections(
    headings: tuple[tuple[int, int, str, str], ...], query: str
) -> tuple[tuple[int, int, str, str], ...] | Literal["scope", "relative"]:
    """Resolve authored ordinals, distinguishing rejected named scope from an unanchored relative request."""
    ordinals = {"opening": 0, "first": 0, "second": 1, "third": 2}
    words = "|".join((*ordinals, "following"))
    requests = [
        (re.findall(rf"\b(?:{words})\b", match.group(1)), match.group(2))
        for match in re.finditer(
            rf"\b((?:{words})(?:\s*(?:,\s*(?:and\s+)?|and\s+)(?:{words}))*)\s+([a-z]+)\b",
            _normalized(query),
        )
    ]
    selected: set[tuple[int, int, str, str]] = set()
    unanchored = False
    for requested, unit in requests:
        available = tuple(
            heading
            for heading in headings
            if any(
                first == last and (label == unit or label + "s" == unit or label == unit + "s")
                for label, first, last in _research_numbered_targets(f"{heading[2]} {heading[3]}")
            )
        )
        scoped = _research_ordinal_scope(
            headings,
            available,
            query,
            frozenset((*ordinals, "following", "compare", "explain", "read", unit, unit + "s", unit.removesuffix("s"))),
        )
        if scoped is None:
            return "scope"
        available = scoped
        opening = any(
            {"opening", "first"} & set(other) and (label == unit or label + "s" == unit or label == unit + "s")
            for other, label in requests
        )
        positions = {ordinals[word] for word in requested if word in ordinals}
        if "following" in requested and opening:
            positions.add(1)
        elif "following" in requested and available:
            unanchored = True
        for relation in re.finditer(
            rf"\b(after|before)\s+(?:(?:that|the|this)\s+)?({'|'.join(ordinals)})\s+{re.escape(unit)}\b",
            _normalized(query),
        ):
            anchor = ordinals[relation.group(2)]
            adjacent = anchor + (1 if relation.group(1) == "after" else -1)
            if not (0 <= anchor < len(available) and 0 <= adjacent < len(available)):
                continue
            parents = {
                next(
                    (parent[0] for parent in reversed(headings) if parent[0] < heading[0] and parent[1] < heading[1]),
                    None,
                )
                for heading in (available[anchor], available[adjacent])
            }
            if len(parents) == 1:
                positions.add(adjacent)
        selected.update(available[position] for position in positions if position < len(available))
    if unanchored and not selected:
        return "relative"
    return tuple(heading for heading in headings if heading in selected)


def _research_section_query(document: CorpusDocument, question: str) -> str:
    query = _URL.sub(" ", question)
    return re.sub(rf"(?i)(?:doc:)?{re.escape(document.path)}", " ", query)


def _research_literal_targets(value: str, query: str) -> frozenset[str]:
    """Recognize authored code literals only when the query explicitly names their exact token."""
    return frozenset(
        symbol
        for match in re.finditer(r"`+[^`]+`+|(?<!\w)_[A-Za-z0-9_]+(?!\w)", value)
        if (symbol := match.group().strip("`"))
        and ("_" in symbol or f"`{symbol}`" in query)
        and re.search(rf"(?<!\w){re.escape(symbol)}(?!\w)", query) is not None
    )


def _research_heading_terms(value: str, query: str) -> frozenset[str]:
    """Do not interpret an inline code identifier as an ordinary language heading."""
    targets = _research_literal_targets(value, query)

    def literal(match: re.Match[str]) -> str:
        symbol = match.group().strip("`")
        return symbol if symbol in targets else " "

    return retrieval_terms(re.sub(r"`+[^`]+`+|(?<!\w)_[A-Za-z0-9_]+(?!\w)", literal, value))


def _research_opening_outlook(
    text: str,
    headings: tuple[tuple[int, int, str, str], ...],
    selected: tuple[tuple[int, int, str, str], ...],
    query: str,
) -> tuple[tuple[int, int, str, str], ...] | None:
    """Keep one following authored unit as outlook context for a selected opening unit."""
    normalized = _normalized(query)
    if (
        len(selected) != 1
        or re.search(r"\b(?:what lies ahead|what comes next|upcoming (?:stages|timeline))\b", normalized) is None
        or (re.search(r"\b(?:opening|first)\b", normalized) is None and not _research_kickoff(query))
    ):
        return selected
    parents: dict[int, tuple[int, int, str, str] | None] = {}
    stack: list[tuple[int, int, str, str]] = []
    for heading in headings:
        while stack and stack[-1][1] >= heading[1]:
            stack.pop()
        parents[heading[0]] = stack[-1] if stack else None
        stack.append(heading)
    owner: tuple[int, int, str, str] | None = next(iter(selected))
    while owner is not None:
        labels = {label for label, first, last in _research_numbered_targets(f"{owner[2]} {owner[3]}") if first == last}
        pairs: set[tuple[tuple[int, int, str, str], tuple[int, int, str, str]]] = set()
        for unit in labels:
            siblings = tuple(
                heading
                for heading in headings
                if parents[heading[0]] == parents[owner[0]]
                and any(
                    first == last and (label == unit or label + "s" == unit or label == unit + "s")
                    for label, first, last in _research_numbered_targets(f"{heading[2]} {heading[3]}")
                )
            )
            if len(siblings) > 1 and next(iter(siblings)) == owner:
                pairs.add((owner, siblings[1]))
        if pairs:
            if len(pairs) != 1:
                return None
            opening, following = next(iter(pairs))
            end = next(
                (heading[0] for heading in headings if heading[0] > following[0] and heading[1] <= following[1]),
                len(text),
            )
            if min(end, following[0] + _RESEARCH_SELECTED_CONTEXT_CHARS) - opening[0] > MAX_DOCUMENT_SOURCE_CHARS:
                return None
            return opening, following
        owner = parents[owner[0]]
    return selected


def _research_reference_sections(
    headings: tuple[tuple[int, int, str, str], ...], query: str, reference_labels: tuple[str, ...]
) -> tuple[tuple[int, int, str, str], ...] | None:
    """Select observed labels only when one sibling branch contains every label exactly once."""
    if not 1 <= len(reference_labels) <= MAX_REFERENCE_SELECTIONS or any(
        re.fullmatch(r"[A-Za-z]{2,24}[ \t_-]*[0-9]{1,6}", label) is None for label in reference_labels
    ):
        return None
    targets = _research_numbered_targets(" ".join(reference_labels))
    if len(targets) != len(reference_labels) or len({label for label, _, _ in targets}) != 1:
        return None
    available = tuple(
        heading
        for heading in headings
        if _research_numbered_matches(targets, _research_numbered_targets(f"{heading[2]} {heading[3]}"))
    )
    excluded = frozenset((*REFERENCE_ORDINALS, "compare", "explain", "read")) | frozenset(
        label + suffix for label, _, _ in targets for suffix in ("", "s")
    )
    selected = _research_ordinal_scope(headings, available, query, excluded)
    if selected is None or len(selected) != len(targets):
        return None
    matched = tuple(
        _research_numbered_matches(targets, _research_numbered_targets(f"{heading[2]} {heading[3]}"))
        for heading in selected
    )
    if any(len(item) != 1 for item in matched) or {target for item in matched for target in item} != set(targets):
        return None
    parents = {
        (
            heading[1],
            next(
                (parent[0] for parent in reversed(headings) if parent[0] < heading[0] and parent[1] < heading[1]), None
            ),
        )
        for heading in selected
    }
    return selected if len(parents) == 1 else None


def _research_explicit_sections(
    document: CorpusDocument,
    headings: tuple[tuple[int, int, str, str], ...],
    question: str,
    query: str,
) -> tuple[tuple[tuple[int, int, str, str], ...], bool]:
    """Find literal current-question targets and retain unmatched explicit-target precedence."""
    fragments = {
        urlsplit(value).fragment
        for value in _research_urls((question,))
        if _research_url_matches(document, value) and urlsplit(value).fragment
    }
    fragments.update(re.findall(r"(?<!\w)#([A-Za-z0-9_-]+)", query))
    explicit = tuple(
        heading
        for heading in headings
        if heading[3] in fragments or re.sub(r"[^\w-]", "", heading[2].casefold().replace(" ", "-")) in fragments
    )
    if explicit:
        return explicit, True
    numbered = _research_numbered_targets(query)
    selected = tuple(
        heading
        for heading in headings
        if _research_numbered_matches(numbered, _research_numbered_targets(f"{heading[2]} {heading[3]}"))
    )
    if selected:
        return selected, True
    literal = tuple(heading for heading in headings if _research_literal_targets(heading[2], query))
    has_current_target = bool(
        literal
        or fragments
        or numbered
        or "`" in query
        or re.search(r"\b[A-Za-z]{2,24}[ \t_-]*[0-9]", query) is not None
    )
    return literal, has_current_target


def _research_section_selection(
    text: str,
    document: CorpusDocument,
    headings: tuple[tuple[int, int, str, str], ...],
    question: str,
    reference_labels: tuple[str, ...] = (),
) -> tuple[tuple[tuple[int, int, str, str], ...], bool, Literal["scope", "relative"] | None]:
    """Prefer literal question targets, then observed anchor labels, before generic ordinal inference."""
    query = _research_section_query(document, question)
    explicit, has_current_target = _research_explicit_sections(document, headings, question, query)
    if explicit:
        return explicit, True, None
    if reference_labels:
        # An unmatched explicit current target cannot be replaced by an anchor observation.
        references = None if has_current_target else _research_reference_sections(headings, query, reference_labels)
        return (references, True, None) if references is not None else ((), False, "scope")
    ordinal = _research_ordinal_sections(headings, query)
    if isinstance(ordinal, str):
        return (), False, ordinal
    if ordinal:
        outlook = _research_opening_outlook(text, headings, ordinal, query)
        return (outlook, True, None) if outlook is not None else ((), False, "scope")
    named = _research_named_heading(text, headings, query)
    if named is not None:
        return (named,), False, None
    terms = retrieval_terms(query)
    heading: tuple[int, int, str, str] | None = None
    if _research_overview(query):
        parents = [
            heading
            for index, heading in enumerate(headings[:-1])
            if heading[2].casefold() not in _NAVIGATION_HEADINGS
            and terms & _research_heading_terms(heading[2], query)
            and headings[index + 1][1] > heading[1]
        ]
        if parents:
            heading = min(parents, key=lambda item: (-len(terms & _research_heading_terms(item[2], query)), item[0]))
    if heading is None:
        heading = _research_ranked_heading(text, headings, terms, kickoff=_research_kickoff(query), query=query)
    selected = (heading,) if heading is not None else ()
    outlook = _research_opening_outlook(text, headings, selected, query)
    return (outlook, len(outlook) > len(selected), None) if outlook is not None else ((), False, "scope")


def _research_overview(question: str) -> bool:
    """Recognize multi-section intent, allowing at most two words to qualify a singular unit."""
    return (
        re.search(
            r"\b(?:overview|weekly|weeks|chapters|sections|stages)\b|\b(?:per|each|every)\s+(?:[^\W\d_]+[ \t]+){0,2}(?:week|chapter|section|stage)\b",
            _normalized(question),
        )
        is not None
    )


def _research_focused_selection(
    text: str,
    document: CorpusDocument,
    headings: tuple[tuple[int, int, str, str], ...],
    question: str,
    focus: str,
    reference_labels: tuple[str, ...],
) -> tuple[tuple[tuple[int, int, str, str], ...], bool, Literal["scope", "relative"] | None, str]:
    """Resolve focus only after current explicit and uniquely authored named targets."""
    selected_headings, explicit, unresolved = _research_section_selection(
        text, document, headings, question, reference_labels
    )
    if unresolved == "scope":
        return selected_headings, explicit, unresolved, question
    query = question
    named = _research_named_heading(text, headings, _research_section_query(document, question))
    if focus and (not selected_headings or (not explicit and named is None)):
        focused, focused_explicit, focus_unresolved = _research_section_selection(text, document, headings, focus)
        focused_name = _research_named_heading(text, headings, _research_section_query(document, focus))
        focus_terms = retrieval_terms(_research_section_query(document, focus))
        focus_parents = [
            heading
            for index, heading in enumerate(headings[:-1])
            if headings[index + 1][1] > heading[1] and focus_terms & _research_heading_terms(heading[2], focus)
        ]
        resolved_parent = _research_overview(focus) and len(focus_parents) == 1 and focused == (focus_parents[0],)
        if not selected_headings or (focused and (focused_explicit or focused_name is not None or resolved_parent)):
            selected_headings, explicit = focused, focused_explicit
            unresolved = focus_unresolved or unresolved
            query = focus
    return selected_headings, explicit, unresolved, query


def _research_excerpt(
    text: str,
    document: CorpusDocument,
    question: str,
    focus: str,
    reference_labels: tuple[str, ...] = (),
    projection_mode: Literal["balanced", "complete_quotes"] | None = None,
) -> tuple[int, str] | None:
    """Select bounded contiguous evidence with its section owner, or refuse incomplete lineage."""
    if not document.path.endswith(".md"):
        query = question if retrieval_terms(_research_section_query(document, question)) else focus
        start = _research_source_start(text, document.path, query)
        return start, text[start : start + _RESEARCH_EXCERPT_CHARS]
    headings = _research_headings(text)
    selected_headings, explicit, unresolved, query = _research_focused_selection(
        text, document, headings, question, focus, reference_labels
    )
    if unresolved == "scope":
        return None
    if not selected_headings and unresolved is not None:
        return None
    selected = selected_headings[0] if selected_headings else None
    terms = retrieval_terms(_research_section_query(document, query))
    start = selected[0] if selected is not None else 0
    end = len(text)
    limit = _RESEARCH_EXCERPT_CHARS
    if selected is not None and (
        len(selected_headings) > 1
        or _research_overview(query)
        or (projection_mode if projection_mode is not None else research_projection_mode(question)) == "complete_quotes"
    ):
        limit = MAX_DOCUMENT_SOURCE_CHARS
    if selected_headings:
        last = selected_headings[-1]
        end = next(
            (offset for offset, level, _, _ in headings if offset > last[0] and level <= last[1]),
            end,
        )
        if not explicit:
            ancestor = _research_ancestor_start(text, headings, selected_headings[0], end=end, limit=limit)
            if ancestor is None:
                return None
            start = ancestor
    matches = (
        match.start() for match in re.finditer(r"[^\W_]+", text[start:end]) if _normalized(match.group()) in terms
    )
    relevant = next(matches, None)
    if relevant is not None and selected is None:
        start = max(start, start + relevant - 300)
    return start, text[start : min(end, start + limit)]


def read_research_document(
    corpus: PublicCorpus,
    source_id: str,
    *,
    question: str,
    focus: str = "",
    reference_labels: tuple[str, ...] = (),
    projection_mode: Literal["balanced", "complete_quotes"] | None = None,
) -> SourceReadResult:
    """Read an admitted identity with exact provenance and optional observed anchor-label selection.

    Literal question targets retain precedence. Observations resolve only a unique
    sibling section scope; they grant no additional source identity or size budget.
    Explicit quotation requests share the existing 16k selected Markdown scope
    ceiling; ordinary reads and non-Markdown evidence retain their 4k ceiling.
    """
    if projection_mode not in {None, "balanced", "complete_quotes"}:
        msg = "research_projection_mode"
        raise ValueError(msg)
    for document, text in zip(corpus.manifest.documents, corpus.texts, strict=True):
        if source_id != f"doc:{document.path}":
            continue
        title = _research_title(document, text)
        selection = _research_excerpt(text, document, question, focus, reference_labels, projection_mode)
        if selection is None:
            return SourceReadResult(
                id=source_id,
                title=title,
                url=document.url,
                status="refused",
                reason="research_document_context",
            )
        start, excerpt = selection
        if not excerpt.strip():
            return SourceReadResult(
                id=source_id,
                title=title,
                url=document.url,
                status="refused",
                reason="research_document_empty",
            )
        return SourceReadResult(
            id=source_id,
            title=title,
            url=document.url,
            status="ok",
            text=excerpt,
            source_digest=sha256(text.encode("utf-8")).hexdigest(),
            text_digest=sha256(excerpt.encode("utf-8")).hexdigest(),
            source_chars=len(text),
            excerpt_start=start,
            truncated=start > 0 or start + len(excerpt) < len(text),
        )
    safe_id = source_id if re.fullmatch(r"doc:[A-Za-z0-9_./-]{1,200}", source_id) else "doc:unknown"
    return SourceReadResult(
        id=safe_id,
        title="Unknown public document",
        url=f"{_PUBLIC_SITE}/",
        status="refused",
        reason="research_document_unknown",
    )


def _research_projection_sections(text: str) -> tuple[tuple[int, int], ...]:
    """Find sibling sections under the selected parent, keeping nested subsections together."""
    headings = _research_headings(text)
    if not headings:
        return ()
    root_level = headings[0][1]
    siblings = [heading for heading in headings if heading[1] == root_level]
    if len(siblings) <= 1:
        child_level = min((heading[1] for heading in headings if heading[1] > root_level), default=root_level)
        siblings = [heading for heading in headings if heading[1] == child_level]
    if len(siblings) <= 1:
        return ()
    starts = [heading[0] for heading in siblings]
    return tuple(zip(starts, [*starts[1:], len(text)], strict=True))


def _research_projection_lines(text: str, start: int, end: int) -> tuple[tuple[int, str], ...]:
    """Replace fenced lines with paragraph boundaries without changing source offsets."""
    result: list[tuple[int, str]] = []
    fence: tuple[str, int] | None = None
    offset = start
    for line in text[start:end].splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence is not None:
            result.append((offset, ""))
            if re.fullmatch(rf"{re.escape(fence[0])}{{{fence[1]},}}\s*", line.strip()):
                fence = None
        elif marker is not None:
            result.append((offset, ""))
            fence = (marker.group(1)[0], len(marker.group(1)))
        else:
            result.append((offset, line))
        offset += len(line)
    return tuple(result)


def _research_quote_attribution(line: str, offset: int) -> tuple[int, int] | None:
    if re.match(r"^ {0,3}>\s*(?:\N{EM DASH}|\N{EN DASH}|-)\s+", line) is None:
        return None
    destination = re.search(r"\]\(", line)
    return offset, offset + (destination.start() + 1 if destination is not None else len(line))


def _research_quote_narrative(text: str, start: int, end: int) -> tuple[int, tuple[int, int] | None, int, int] | None:
    """Locate the first narrative paragraph after a blockquote outside fenced code."""
    quote_start: int | None = None
    paragraph_start: int | None = None
    paragraph_end = start
    attribution: tuple[int, int] | None = None
    separated = False
    for offset, line in _research_projection_lines(text, start, end):
        stripped = line.strip()
        boundary = not stripped or re.match(r"^ {0,3}(?:>|#{1,6}\s|<a\s)", line) is not None
        if paragraph_start is not None:
            if quote_start is not None and boundary:
                return quote_start, attribution, paragraph_start, paragraph_end
            paragraph_end = offset + len(line)
        elif re.fullmatch(r" {0,3}>[ \t]*(?:\r?\n)?", line):
            separated = quote_start is not None
        elif re.match(r"^ {0,3}>", line):
            if quote_start is None:
                quote_start = offset
            attribution = _research_quote_attribution(line, offset)
            separated = False
        elif quote_start is not None and boundary:
            separated = True
        elif quote_start is not None and separated:
            paragraph_start = offset
            paragraph_end = offset + len(line)
    if quote_start is not None and paragraph_start is not None:
        return quote_start, attribution, paragraph_start, paragraph_end
    return None


def _research_section_spans(text: str, start: int, end: int, length: int) -> list[dict[str, int]]:
    """Keep quote, attribution and meaning prefixes when a long quote consumes the share."""
    narrative = _research_quote_narrative(text, start, end)
    if narrative is not None and narrative[2] >= start + length:
        quote_start, attribution, paragraph_start, paragraph_end = narrative
        opening_minimum = quote_start - start + _RESEARCH_PROJECTION_QUOTE_CHARS
        if attribution is not None:
            opening_minimum = min(opening_minimum, attribution[0] - start)
        remaining = max(0, length - opening_minimum)
        attribution_length = (
            min(attribution[1] - attribution[0], _RESEARCH_PROJECTION_ATTRIBUTION_CHARS, remaining // 3)
            if attribution is not None
            else 0
        )
        narrative_length = min(paragraph_end - paragraph_start, length // 2, remaining - attribution_length)
        if narrative_length:
            opening_end = start + length - narrative_length - attribution_length
            if attribution is not None:
                opening_end = min(opening_end, attribution[0])
            spans = [{"start": start, "end": opening_end}]
            if attribution is not None and attribution_length:
                spans.append({"start": attribution[0], "end": attribution[0] + attribution_length})
            spans.append({"start": paragraph_start, "end": paragraph_start + narrative_length})
            return spans
    return [{"start": start, "end": start + length}]


def _research_projection_spans(source: SourceReadResult, length: int) -> list[dict[str, int]]:
    text = source.text
    if not text or not length:
        return []
    if len(text) <= length or not source.id.endswith(".md"):
        return [{"start": 0, "end": min(length, len(text))}]
    sections = _research_projection_sections(text)
    if not sections:
        return [{"start": 0, "end": min(length, len(text))}]
    preamble = min(sections[0][0], _RESEARCH_PROJECTION_PREAMBLE_CHARS, length // 5)
    limit = (_RESEARCH_PROJECTION_SPANS - bool(preamble)) // 3
    if len(sections) > limit:
        sections = tuple(sections[index * (len(sections) - 1) // (limit - 1)] for index in range(limit))
    separators = 2 * (3 * len(sections) + bool(preamble) - 1)
    available = length - preamble - separators
    if available < len(sections):
        return [{"start": 0, "end": min(length, len(text))}]
    share, remainder = divmod(available, len(sections))
    sizes = [min(end - start, share + (index < remainder)) for index, (start, end) in enumerate(sections)]
    remaining = available - sum(sizes)
    for index, (start, end) in enumerate(sections):
        extra = min(end - start - sizes[index], remaining)
        sizes[index] += extra
        remaining -= extra
    spans = [{"start": 0, "end": preamble}] if preamble else []
    for (start, end), size in zip(sections, sizes, strict=True):
        spans.extend(_research_section_spans(text, start, end, size))
    return spans


def render_research_projection(text: str, spans: list[dict[str, int]]) -> str:
    """Reconstruct exact ordered source spans, explicitly marking every omitted interval.

    An empty span list offers no text. Markers are synthetic evidence boundaries,
    never part of a source span or an exact quotation.
    """
    if not spans:
        return ""
    parts: list[str] = []
    cursor = 0
    for span in spans:
        start, end = span["start"], span["end"]
        if not cursor <= start < end <= len(text):
            msg = "research_projection_spans"
            raise ValueError(msg)
        if cursor < start:
            parts.append(RESEARCH_PROJECTION_OMISSION)
        parts.append(text[start:end])
        cursor = end
    if cursor < len(text):
        parts.append(RESEARCH_PROJECTION_OMISSION)
    return "".join(parts)


def research_projection_mode(question: str) -> Literal["balanced", "complete_quotes"]:
    """Preserve requested quotations unless the question explicitly asks to abbreviate them."""
    query = _normalized(question).replace("\N{RIGHT SINGLE QUOTATION MARK}", "'")
    noun = r"(?:quotes?|quotations?)"
    if re.search(rf"\b{noun}\b", query) is None:
        return "balanced"
    shortened = (
        rf"\b(?:shorten|summari[sz]e|abbreviate|trim)\s+(?:(?:the|these|those|your|all|long)\s+)*{noun}\b|"
        rf"\b{noun}\s+(?:excerpts?|fragments?|openings?|summaries)\b|"
        rf"\b(?:excerpts?|fragments?|openings?|summaries)\s+(?:of\s+)?(?:the\s+)?{noun}\b"
    )
    for match in re.finditer(shortened, query):
        prefix = query[max(0, match.start() - 40) : match.start()]
        if re.search(r"\b(?:no|not|never|don't|dont|without)(?:\s+\w+){0,2}\s*$", prefix) is None:
            return "balanced"
    return "complete_quotes"


def _research_merge_spans(text: str, spans: list[dict[str, int]]) -> list[dict[str, int]]:
    merged: list[dict[str, int]] = []
    for span in sorted(spans, key=lambda item: (item["start"], item["end"])):
        if merged and (span["start"] <= merged[-1]["end"] or text[merged[-1]["end"] : span["start"]].isspace()):
            merged[-1]["end"] = max(merged[-1]["end"], span["end"])
        else:
            merged.append(dict(span))
    return merged


def _research_quote_line_kind(line: str) -> Literal["quote", "blank", "boundary", "continuation"]:
    if not line:
        return "boundary"
    if not line.strip():
        return "blank"
    if re.match(r"^ {0,3}>", line):
        return "quote"
    if re.match(r"^ {0,3}(?:#{1,6}\s|[-*_]{3,}\s*$|(?:[-+*]|[0-9]+[.)])\s)", line):
        return "boundary"
    return "continuation"


def _research_consume_quote(
    lines: tuple[tuple[int, str], ...], opening: int
) -> tuple[int, int, tuple[int, int] | None, bool]:
    offset, line = lines[opening]
    closing = offset + len(line)
    attribution = _research_quote_attribution(line, offset)
    separated = False
    for index in range(opening + 1, len(lines)):
        offset, line = lines[index]
        kind = _research_quote_line_kind(line)
        if kind == "quote":
            closing, attribution = offset + len(line), _research_quote_attribution(line, offset)
            separated = False
        elif kind == "blank":
            separated = True
        elif kind == "boundary" or separated:
            return index, closing, attribution, True
        else:
            # Unmarked paragraph continuation remains inside the quotation.
            closing, attribution = offset + len(line), None
    return len(lines), closing, attribution, False


def _research_complete_blocks(
    text: str, start: int, end: int, *, complete_start: bool, complete_end: bool
) -> tuple[tuple[_ResearchQuoteBlock, ...], bool]:
    """Observe explicit quote paragraphs and lazy continuations outside fences.

    Headings, simple list/thematic starts and blank-separated prose delimit this
    conservative subset. Unknown acquisition edges are omitted, not repaired.
    """
    blocks: list[_ResearchQuoteBlock] = []
    lines = _research_projection_lines(text, start, end)
    cursor, bounded, all_bounded = 0, complete_start, True
    while cursor < len(lines):
        offset, line = lines[cursor]
        kind = _research_quote_line_kind(line)
        if kind != "quote":
            bounded = bounded or kind == "boundary"
            cursor += 1
            continue
        cursor, closing, attribution, observed_end = _research_consume_quote(lines, cursor)
        body_end = attribution[0] if attribution else closing
        complete = bounded and (observed_end or complete_end)
        if complete and body_end > offset:
            blocks.append((offset, body_end, attribution))
        all_bounded = all_bounded and complete
        bounded = observed_end
    return tuple(blocks), all_bounded


def _research_narrative_span(text: str, start: int, end: int) -> tuple[int, int] | None:
    opening: int | None = None
    closing = start
    for offset, line in _research_projection_lines(text, start, end):
        if not line.strip() or re.match(r"^ {0,3}(?:>|#{1,6}\s|<a\s)", line):
            if opening is not None:
                break
        else:
            if opening is None:
                opening = offset
            closing = offset + len(line)
    return (opening, closing) if opening is not None else None


def _research_quote_header_end(text: str, start: int, end: int) -> int:
    """Keep a complete section heading/preamble without importing fenced quote decoys."""
    closing = start
    for offset, line in _research_projection_lines(text, start, end):
        if (
            not line.strip()
            or re.match(r"^ {0,3}>", line)
            or offset + len(line) - start > _RESEARCH_PROJECTION_PREAMBLE_CHARS
        ):
            break
        closing = offset + len(line)
    return closing


def _research_complete_attribution_spans(
    text: str, attribution: tuple[int, int], end: int
) -> list[dict[str, int]] | None:
    """Keep all authored attribution words, including text following a simple link."""
    start, prefix_end = attribution
    line_end = text.find("\n", start, end)
    line_end = line_end + 1 if line_end >= 0 else end
    spans = [{"start": start, "end": prefix_end}]
    if prefix_end < line_end:
        destination = re.match(r"\([^()\r\n]*\)", text[prefix_end:line_end])
        if destination is None:
            return None
        suffix = prefix_end + destination.end()
        if text[suffix:line_end].strip():
            spans.append({"start": suffix, "end": line_end})
    return spans


def _research_quote_edges_bounded(source: SourceReadResult) -> bool:
    """Establish quote boundaries from observed context and actual source endpoints."""
    _, bounded = _research_complete_blocks(
        source.text,
        0,
        len(source.text),
        complete_start=source.excerpt_start == 0,
        complete_end=source.excerpt_start + len(source.text) == source.source_chars,
    )
    return bounded


def _research_admit_quote_spans(
    text: str, length: int, spans: list[dict[str, int]], additions: list[dict[str, int]]
) -> bool:
    candidate = _research_merge_spans(text, [*spans, *additions])
    if len(candidate) > _RESEARCH_PROJECTION_SPANS or len(render_research_projection(text, candidate)) > length:
        return False
    spans[:] = candidate
    return True


def _research_section_quote_units(
    source: SourceReadResult, start: int, end: int
) -> list[tuple[list[dict[str, int]], tuple[int, int] | None]]:
    """Pair each complete quotation/attribution atom with its following explanation."""
    text = source.text
    blocks, _ = _research_complete_blocks(
        text,
        start,
        end,
        complete_start=start > 0 or source.excerpt_start == 0,
        complete_end=end < len(text) or source.excerpt_start + len(text) == source.source_chars,
    )
    if not blocks:
        return []
    heading_starts = [offset for offset, _, _, _ in _research_headings(text) if start <= offset < end]
    units: list[tuple[list[dict[str, int]], tuple[int, int] | None]] = []
    for index, (opening, closing, attribution) in enumerate(blocks):
        attribution_spans = _research_complete_attribution_spans(text, attribution, end) if attribution else []
        if attribution_spans is None:
            continue
        additions = [{"start": opening, "end": closing}]
        position = bisect_right(heading_starts, opening)
        owner = heading_starts[position - 1] if position else start
        header_end = _research_quote_header_end(text, owner, opening)
        if owner < header_end:
            additions.append({"start": owner, "end": header_end})
        additions.extend(attribution_spans)
        after = closing
        if attribution is not None:
            line_end = text.find("\n", attribution[1], end)
            after = line_end + 1 if line_end >= 0 else end
        boundary = blocks[index + 1][0] if index + 1 < len(blocks) else end
        units.append((additions, _research_narrative_span(text, after, boundary)))
    return units


def _research_fill_quote_narratives(
    text: str, length: int, spans: list[dict[str, int]], narratives: list[tuple[int, int]]
) -> None:
    """Offer every first complete sentence before longer explanatory paragraphs."""
    for start, end in narratives:
        sentence = re.search(r"[.!?](?=\s|$)", text[start:end])
        first_end = start + sentence.end() if sentence is not None else end
        _research_admit_quote_spans(text, length, spans, [{"start": start, "end": first_end}])
    for start, end in narratives:
        _research_admit_quote_spans(text, length, spans, [{"start": start, "end": end}])


def _research_nonquote_prefix(text: str, length: int) -> list[dict[str, int]]:
    """Retain bounded non-quotation context without importing a partial quote."""
    first_quote = next(
        (offset for offset, line in _research_projection_lines(text, 0, len(text)) if re.match(r"^ {0,3}>", line)),
        len(text),
    )
    prefix = min(_research_quote_header_end(text, 0, first_quote), max(0, length - len(RESEARCH_PROJECTION_OMISSION)))
    return [{"start": 0, "end": prefix}] if prefix else []


def _research_complete_quote_spans(source: SourceReadResult, length: int) -> list[dict[str, int]]:
    """Pack whole quotation units before purpose/context; every gap remains explicit."""
    text = source.text
    if not text or not length:
        return []
    if len(text) <= length and _research_quote_edges_bounded(source):
        return [{"start": 0, "end": len(text)}]
    sections = _research_projection_sections(text) or ((0, len(text)),)
    if sections[0][0]:
        sections = ((0, sections[0][0]), *sections)
    spans: list[dict[str, int]] = []
    narratives: list[tuple[int, int]] = []
    for start, end in sections:
        for additions, narrative in _research_section_quote_units(source, start, end):
            if _research_admit_quote_spans(text, length, spans, additions) and narrative is not None:
                narratives.append(narrative)
    _research_fill_quote_narratives(text, length, spans, narratives)
    return spans or _research_nonquote_prefix(text, length)


def project_research_source(
    source: SourceReadResult,
    length: int,
    *,
    projection_mode: Literal["balanced", "complete_quotes"] = "balanced",
) -> dict[str, object]:
    """Budget exact spans and omissions, optionally preserving requested quotation units atomically."""
    if length < 0:
        msg = "research_projection_length"
        raise ValueError(msg)
    if projection_mode not in ("balanced", "complete_quotes"):
        msg = "research_projection_mode"
        raise ValueError(msg)
    allocation = length
    for _ in range(_RESEARCH_PROJECTION_SPANS + 1):
        spans = (
            _research_complete_quote_spans(source, allocation)
            if projection_mode == "complete_quotes" and source.id.endswith(".md")
            else _research_projection_spans(source, allocation)
        )
        text = render_research_projection(source.text, spans)
        excess = len(text) - length
        if excess <= 0:
            break
        allocation = max(0, allocation - excess)
    else:
        # The finite retry bound cannot leave an over-budget projection behind.
        prefix = (
            max(0, min(len(source.text), length - len(RESEARCH_PROJECTION_OMISSION)))
            if projection_mode == "balanced"
            else 0
        )
        spans = [{"start": 0, "end": prefix}] if prefix else []
        text = render_research_projection(source.text, spans)
    return {
        **source.model_dump(mode="json"),
        "text": text,
        "projection_budget": length,
        "projection_mode": projection_mode,
        "projection_digest": sha256(text.encode("utf-8")).hexdigest(),
        "projection_truncated": sum(span["end"] - span["start"] for span in spans) < len(source.text),
        "projection_spans": spans,
    }
