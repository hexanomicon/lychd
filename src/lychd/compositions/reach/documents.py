"""Pure verification and deterministic excerpt search over an explicit public export."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from lychd.compositions.reach.operator_wire import ReachHistoryEntry, ReachWorkerRequest
from lychd.compositions.reach.research_wire import SourceReadResult
from lychd.compositions.reach.schemas import PolicyDigest, ReachPolicy, Record

MAX_DOCUMENT_BYTES = 524_288
MAX_CORPUS_BYTES = 2_097_152
MAX_HISTORY_BYTES = 16_384
MIN_EXCERPT_CHARS = 30
_REPO = "https://github.com/hexanomicon/lychd/blob/"
_PUBLIC_SITE = "https://hexanomicon.dev"
_RESEARCH_EXCERPT_CHARS = 4000
_URL = re.compile(r"https?://[^\s<>\[\]()\"']+")
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


class CorpusDocument(Record):
    """One immutable public source binding, not a user-selected filesystem path."""

    path: str = Field(pattern=r"^(?:README\.md|CONTRIBUTING\.md|docs/[A-Za-z0-9_./-]+\.md)$", max_length=200)
    url: str = Field(max_length=360)
    sha256: PolicyDigest
    file: str = Field(pattern=r"^[0-9]{3}\.md$")

    @model_validator(mode="after")
    def safe_path(self) -> Self:
        if any(part in {"", ".", ".."} for part in self.path.split("/")):
            msg = "corpus_path"
            raise ValueError(msg)
        return self


class CorpusManifest(Record):
    """Bounded export whose URLs bind exactly to its source revision."""

    schema_version: Annotated[int, Field(ge=1, le=1)] = 1
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    documents: tuple[CorpusDocument, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def bindings(self) -> Self:
        for name in ("path", "file"):
            values = [getattr(document, name) for document in self.documents]
            if len(values) != len(set(values)):
                msg = "corpus_duplicate"
                raise ValueError(msg)
        if any(document.url != f"{_REPO}{self.source_revision}/{document.path}" for document in self.documents):
            msg = "corpus_url"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class PublicCorpus:
    """Verified detached bytes; search never accesses a filesystem or network."""

    manifest: CorpusManifest
    texts: tuple[str, ...]
    digest: str


def verify_corpus(manifest: CorpusManifest, contents: tuple[bytes, ...]) -> PublicCorpus:
    """Verify complete bounded source bytes before admitting a search corpus."""
    if len(contents) != len(manifest.documents) or sum(map(len, contents)) > MAX_CORPUS_BYTES:
        msg = "corpus_limit"
        raise ValueError(msg)
    texts: list[str] = []
    for document, raw in zip(manifest.documents, contents, strict=True):
        if len(raw) > MAX_DOCUMENT_BYTES or sha256(raw).hexdigest() != document.sha256:
            msg = "corpus_content"
            raise ValueError(msg)
        value = raw.decode("utf-8", errors="strict")
        if any(unicodedata.category(char) in {"Cc", "Cs"} and char not in "\n\r\t" for char in value):
            msg = "corpus_text"
            raise ValueError(msg)
        texts.append(value)
    canonical = json.dumps(manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return PublicCorpus(manifest, tuple(texts), sha256(canonical.encode()).hexdigest())


def _normalized(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(char))


def _tokens(value: str) -> frozenset[str]:
    return frozenset(
        token for token in re.findall(r"[^\W_]+", _normalized(value)) if len(token) > 1 and token not in _STOP
    )


def validate_history(policy: ReachPolicy, request: ReachWorkerRequest) -> None:
    """Bound history to its conversation and, for DMs, the sender and this bot."""
    history = request.history + ((request.reply_anchor,) if request.reply_anchor is not None else ())
    if request.reply_anchor is not None and request.reply_anchor.event_id != request.reply_to_event_id:
        msg = "history_anchor_binding"
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
    question_terms = _tokens(request.event.question)
    context = request.history + ((request.reply_anchor,) if request.reply_anchor is not None else ())
    context_terms = _tokens(" ".join(item.text for item in context))
    ranked: list[tuple[int, str, CorpusDocument, str]] = []
    for document, text in zip(corpus.manifest.documents, corpus.texts, strict=True):
        terms = _tokens(text)
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
    return " ".join(value.strip(" #*_`").split())[:120]


def _research_headings(text: str) -> tuple[tuple[int, int, str, str], ...]:
    """Locate ATX headings outside the YAML header and fenced quotations."""
    headings: list[tuple[int, int, str, str]] = []
    offset = 0
    frontmatter = text.startswith(("---\n", "---\r\n"))
    fence: str | None = None
    for index, line in enumerate(text.splitlines(keepends=True)):
        stripped = line.strip()
        if frontmatter:
            if index and stripped == "---":
                frontmatter = False
        elif fence is not None:
            if re.fullmatch(rf"{re.escape(fence)}{{3,}}\s*", stripped):
                fence = None
        elif re.match(r"^\s{0,3}(?:`{3,}|~{3,})", line):
            fence = stripped[0]
        else:
            match = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*\r?\n?$", line)
            if match is not None:
                raw_title = match.group(2)
                explicit = re.search(r"\{\s*#([A-Za-z0-9_-]+)\s*\}\s*$", raw_title)
                title = _research_heading_title(raw_title)
                anchor = (
                    explicit.group(1)
                    if explicit is not None
                    else re.sub(r"[^\w-]", "", title.casefold().replace(" ", "-"))
                )
                headings.append((offset, len(match.group(1)), title, anchor))
        offset += len(line)
    return tuple(headings)


def research_document_catalogue(corpus: PublicCorpus) -> tuple[dict[str, str], ...]:
    """Name only verified manifest sources; this catalogue performs no acquisition."""
    result: list[dict[str, str]] = []
    for document, text in zip(corpus.manifest.documents, corpus.texts, strict=True):
        title = next((title for _, level, title, _ in _research_headings(text) if level == 1 and title), document.path)
        result.append({"id": f"doc:{document.path}", "title": title[:120], "url": document.url})
    return tuple(result)


def _research_site_url(path: str) -> str | None:
    if not path.startswith("docs/"):
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
    """Resolve exact public-site or revision-pinned locators to local IDs, without fetching."""
    result: list[str] = []
    for value in _research_urls(texts):
        for document in corpus.manifest.documents:
            source_id = f"doc:{document.path}"
            if _research_url_matches(document, value) and source_id not in result:
                result.append(source_id)
    return tuple(result)


def _research_excerpt(text: str, document: CorpusDocument, question: str) -> tuple[int, str]:
    headings = _research_headings(text)
    terms = _tokens(_URL.sub(" ", question))
    fragments = {
        urlsplit(value).fragment
        for value in _research_urls((question,))
        if _research_url_matches(document, value) and urlsplit(value).fragment
    }
    selected: tuple[int, int, str, str] | None = None
    if fragments:
        selected = next((heading for heading in headings if heading[3] in fragments), None)
    if selected is None:
        ranked = [
            (-len(terms & _tokens(heading[2])), heading[0], heading)
            for heading in headings
            if heading[2].casefold() not in _NAVIGATION_HEADINGS and terms & _tokens(heading[2])
        ]
        if ranked:
            selected = min(ranked, key=lambda item: (item[0], item[1]))[2]
    start = selected[0] if selected is not None else 0
    end = len(text)
    if selected is not None:
        end = next((offset for offset, level, _, _ in headings if offset > start and level <= selected[1]), end)
    matches = (
        match.start() for match in re.finditer(r"[^\W_]+", text[start:end]) if _normalized(match.group()) in terms
    )
    relevant = next(matches, None)
    if relevant is not None and (selected is None or relevant > _RESEARCH_EXCERPT_CHARS - 300):
        start = max(start, start + relevant - 300)
    return start, text[start : min(end, start + _RESEARCH_EXCERPT_CHARS)]


def read_research_document(corpus: PublicCorpus, source_id: str, *, question: str) -> SourceReadResult:
    """Read one exact manifest member and bind its bounded excerpt to the complete source bytes."""
    for document, text in zip(corpus.manifest.documents, corpus.texts, strict=True):
        if source_id != f"doc:{document.path}":
            continue
        title = next((title for _, level, title, _ in _research_headings(text) if level == 1 and title), document.path)[
            :120
        ]
        start, excerpt = _research_excerpt(text, document, question)
        if not excerpt.strip():
            return SourceReadResult(
                id=source_id, title=title, url=document.url, status="refused", reason="research_document_empty"
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
