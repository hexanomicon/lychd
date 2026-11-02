"""Verify detached public project exports and offer bounded source metadata for research.

Project knowledge is pinned Git text, never a live checkout or execution authority.
Planning retrieves at most sixteen identities; source bodies enter only explicit reads.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from lychd.compositions.reach.operator_wire import ReachHistoryEntry, ReachWorkerRequest
from lychd.compositions.reach.research_wire import MAX_DOCUMENT_SOURCE_CHARS, SourceReadResult
from lychd.compositions.reach.schemas import PolicyDigest, ReachPolicy, Record

MAX_DOCUMENT_BYTES = 524_288
MAX_CORPUS_BYTES = 67_108_864
MAX_CORPUS_DOCUMENTS = 8192
MAX_CORPUS_MANIFEST_BYTES = 8_388_608
MAX_CORPUS_PATH_CHARS = 200
MAX_RESEARCH_CATALOGUE_DOCUMENTS = 16
LEGACY_MAX_CORPUS_BYTES = 2_097_152
LEGACY_MAX_DOCUMENTS = 32
MAX_HISTORY_BYTES = 16_384
MIN_EXCERPT_CHARS = 30
_REPO = "https://github.com/hexanomicon/lychd/blob/"
_PUBLIC_SITE = "https://hexanomicon.dev"
_RESEARCH_EXCERPT_CHARS = 4000
_RESEARCH_ANCESTOR_CHARS = 600
_RESEARCH_PROJECTION_PREAMBLE_CHARS = 400
_RESEARCH_PROJECTION_SPANS = 48
_RESEARCH_PROJECTION_QUOTE_CHARS = 40
_RESEARCH_PROJECTION_ATTRIBUTION_CHARS = 120
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


def research_document_catalogue(
    corpus: PublicCorpus, *, question: str = "", context: tuple[str, ...] = ()
) -> tuple[dict[str, str], ...]:
    """Offer at most sixteen sources by exact reference, authored section target, then lexical rank.

    Ranking is local and deterministic. Only identity, title and pinned URL leave
    this function; the model must select an offered ID before an explicit read.
    """
    exact_question = set(research_document_matches(corpus, (question,)))
    exact_context = set(research_document_matches(corpus, context))
    question_terms, context_terms = _tokens(question), _tokens(" ".join(context))
    numbered_question = _research_numbered_targets(_URL.sub(" ", question))
    kickoff = _research_kickoff(question)
    if kickoff:
        question_terms |= frozenset({"roadmap", "milestone", "milestones"})
    ranked: list[tuple[int, int, int, str, dict[str, str]]] = []
    for document, text in zip(corpus.manifest.documents, corpus.texts, strict=True):
        title = _research_title(document, text)
        source_id = f"doc:{document.path}"
        path_terms, title_terms, content_terms = _tokens(document.path), _tokens(title), _tokens(text)
        route = kickoff and document.path in {"ROADMAP.md", "docs/roadmap.md"}
        exact = 3 if source_id in exact_question else 2 if source_id in exact_context else int(route)
        section_matches = (
            len(
                numbered_question
                & frozenset(
                    target
                    for _, _, heading, anchor in _research_headings(text)
                    for target in _research_numbered_targets(f"{heading} {anchor}")
                )
            )
            if numbered_question and document.path.endswith(".md")
            else 0
        )
        score = (
            24 * len(question_terms & path_terms)
            + 12 * len(question_terms & title_terms)
            + 3 * len(question_terms & content_terms)
            + 4 * len(context_terms & path_terms)
            + 2 * len(context_terms & title_terms)
            + len(context_terms & content_terms)
        )
        if exact or section_matches or score or not (question or context):
            ranked.append(
                (
                    -exact,
                    -section_matches,
                    -score,
                    document.path,
                    {"id": source_id, "title": title, "url": document.url},
                )
            )
    # Preserve the small legacy catalogue's authored order for callers without a query.
    if question or context:
        ranked.sort(key=lambda item: item[:4])
    return tuple(item[4] for item in ranked[:MAX_RESEARCH_CATALOGUE_DOCUMENTS])


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
    terms = _tokens(query)
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


def _research_ancestor_start(
    headings: tuple[tuple[int, int, str, str], ...], selected: tuple[int, int, str, str]
) -> int:
    """Retain a nearby parent's authored heading and preamble as contiguous source context."""
    parent = next(
        (heading for heading in reversed(headings) if heading[0] < selected[0] and heading[1] < selected[1]), None
    )
    if parent is not None and selected[0] - parent[0] <= _RESEARCH_ANCESTOR_CHARS:
        return parent[0]
    return selected[0]


def _research_numbered_targets(value: str) -> frozenset[tuple[str, int]]:
    """Treat authored labels such as Week02, Week 2 and week-02 as the same target."""
    normalized = _normalized(value)
    targets: set[tuple[str, int]] = set()
    for match in re.finditer(r"\b([a-z]+)[ \t_-]*([0-9]{1,6})\b", normalized):
        targets.add((match.group(1), int(match.group(2))))
        tail = normalized[match.end() :]
        while adjacent := re.match(r"\s*/\s*([0-9]{1,6})\b", tail):
            targets.add((match.group(1), int(adjacent.group(1))))
            tail = tail[adjacent.end() :]
    return frozenset(targets)


def _research_section_query(document: CorpusDocument, question: str) -> str:
    query = _URL.sub(" ", question)
    return re.sub(rf"(?i)(?:doc:)?{re.escape(document.path)}", " ", query)


def _research_heading_terms(value: str, query: str) -> frozenset[str]:
    """Do not interpret an inline code identifier as an ordinary language heading."""

    def literal(match: re.Match[str]) -> str:
        symbol = match.group().strip("`")
        return symbol if symbol in query and ("_" in symbol or f"`{symbol}`" in query) else " "

    return _tokens(re.sub(r"`+[^`]+`+|(?<!\w)_[A-Za-z0-9_]+(?!\w)", literal, value))


def _research_section_selection(
    text: str, document: CorpusDocument, headings: tuple[tuple[int, int, str, str], ...], question: str
) -> tuple[tuple[tuple[int, int, str, str], ...], bool]:
    """Resolve exact fragments and numbered targets before ordinary heading language."""
    fragments = {
        urlsplit(value).fragment
        for value in _research_urls((question,))
        if _research_url_matches(document, value) and urlsplit(value).fragment
    }
    query = _research_section_query(document, question)
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
        heading for heading in headings if numbered & _research_numbered_targets(f"{heading[2]} {heading[3]}")
    )
    if selected:
        return selected, True
    terms = _tokens(query)
    if _research_overview(query):
        parents = [
            heading
            for index, heading in enumerate(headings[:-1])
            if heading[2].casefold() not in _NAVIGATION_HEADINGS
            and terms & _research_heading_terms(heading[2], query)
            and headings[index + 1][1] > heading[1]
        ]
        if parents:
            return (
                min(
                    parents, key=lambda heading: (-len(terms & _research_heading_terms(heading[2], query)), heading[0])
                ),
            ), False
    heading = _research_ranked_heading(text, headings, terms, kickoff=_research_kickoff(query), query=query)
    return ((heading,) if heading is not None else ()), False


def _research_overview(question: str) -> bool:
    return (
        re.search(
            r"\b(?:overview|weekly|weeks|chapters|sections|stages)\b|\b(?:per|each|every)\s+(?:week|chapter|section|stage)\b",
            _normalized(question),
        )
        is not None
    )


def _research_excerpt(text: str, document: CorpusDocument, question: str, focus: str) -> tuple[int, str]:
    """Select a bounded contiguous section; the current request takes precedence over prior focus."""
    if not document.path.endswith(".md"):
        query = question if _tokens(_research_section_query(document, question)) else focus
        start = _research_source_start(text, document.path, query)
        return start, text[start : start + _RESEARCH_EXCERPT_CHARS]
    headings = _research_headings(text)
    selected_headings, explicit = _research_section_selection(text, document, headings, question)
    query = question
    if not selected_headings and focus:
        selected_headings, explicit = _research_section_selection(text, document, headings, focus)
        query = focus
    selected = selected_headings[0] if selected_headings else None
    terms = _tokens(_research_section_query(document, query))
    kickoff = _research_kickoff(query)
    start = selected[0] if selected is not None else 0
    end = len(text)
    if selected is not None:
        last = selected_headings[-1]
        end = next((offset for offset, level, _, _ in headings if offset > last[0] and level <= last[1]), end)
        if not explicit and kickoff:
            start = _research_ancestor_start(headings, selected)
    limit = _RESEARCH_EXCERPT_CHARS
    if selected is not None and (len(selected_headings) > 1 or _research_overview(query)):
        limit = MAX_DOCUMENT_SOURCE_CHARS
    matches = (
        match.start() for match in re.finditer(r"[^\W_]+", text[start:end]) if _normalized(match.group()) in terms
    )
    relevant = next(matches, None)
    if relevant is not None and (selected is None or (not explicit and relevant > limit - 300)):
        start = max(start, start + relevant - 300)
    return start, text[start : min(end, start + limit)]


def read_research_document(corpus: PublicCorpus, source_id: str, *, question: str, focus: str = "") -> SourceReadResult:
    """Bind an exact local read to complete bytes, using acknowledged focus for elliptical requests."""
    for document, text in zip(corpus.manifest.documents, corpus.texts, strict=True):
        if source_id != f"doc:{document.path}":
            continue
        title = _research_title(document, text)
        start, excerpt = _research_excerpt(text, document, question, focus)
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
    if len(text) <= length or len(text) <= _RESEARCH_EXCERPT_CHARS or not source.id.endswith(".md"):
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


def project_research_source(source: SourceReadResult, length: int) -> dict[str, object]:
    """Project exact source spans within a character budget, balancing Markdown siblings and meanings.

    Offsets are relative to the admitted excerpt. Only the separators between spans
    are synthetic; the digest binds the exact text offered to synthesis.
    """
    if length < 0:
        msg = "research_projection_length"
        raise ValueError(msg)
    spans = _research_projection_spans(source, length)
    text = "\n\n".join(source.text[span["start"] : span["end"]] for span in spans)
    return {
        **source.model_dump(mode="json"),
        "text": text,
        "projection_budget": length,
        "projection_digest": sha256(text.encode("utf-8")).hexdigest(),
        "projection_truncated": sum(span["end"] - span["start"] for span in spans) < len(source.text),
        "projection_spans": spans,
    }
