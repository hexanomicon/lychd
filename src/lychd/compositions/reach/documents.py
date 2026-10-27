"""Pure verification and deterministic excerpt search over an explicit public export."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from lychd.compositions.reach.operator_wire import ReachHistoryEntry, ReachWorkerRequest
from lychd.compositions.reach.schemas import PolicyDigest, ReachPolicy, Record

MAX_DOCUMENT_BYTES = 524_288
MAX_CORPUS_BYTES = 2_097_152
MAX_HISTORY_BYTES = 16_384
MIN_EXCERPT_CHARS = 30
_REPO = "https://github.com/hexanomicon/lychd/blob/"
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
    """Refuse foreign, stale, duplicate or unbudgeted history instead of silently expanding context."""
    history = request.history
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
    context_terms = _tokens(" ".join(item.text for item in request.history))
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
