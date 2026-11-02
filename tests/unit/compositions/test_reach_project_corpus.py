"""Pinned project text remains bounded knowledge, with offered-ID and source-byte custody."""

from __future__ import annotations

from hashlib import sha256
from itertools import pairwise
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError
from scripts.reach_worker import load_corpus

from lychd.compositions.reach.documents import (
    MAX_DOCUMENT_BYTES,
    MAX_RESEARCH_CATALOGUE_DOCUMENTS,
    CorpusDocument,
    CorpusManifest,
    CorpusOmission,
    PublicCorpus,
    project_research_source,
    public_project_path,
    read_research_document,
    research_document_catalogue,
    research_document_matches,
    verify_corpus,
)
from lychd.compositions.reach.research import parse_research_plan
from tests.unit.compositions.test_reach_documents import REVISION


def project_corpus(*sources: tuple[str, str]) -> PublicCorpus:
    raw = tuple(text.encode("utf-8") for _, text in sources)
    manifest = CorpusManifest(
        schema_version=2,
        source_revision=REVISION,
        documents=tuple(
            CorpusDocument(
                path=path,
                url=f"https://github.com/hexanomicon/lychd/blob/{REVISION}/{path}",
                sha256=sha256(content).hexdigest(),
                file=f"{index:04}.txt",
            )
            for index, ((path, _), content) in enumerate(zip(sources, raw, strict=True))
        ),
    )
    return verify_corpus(manifest, raw)


@pytest.mark.parametrize(
    "path",
    [
        "ROADMAP.md",
        "pyproject.toml",
        "uv.lock",
        ".gitignore",
        "src/lychd/system/constants.py",
        "tests/unit/test_contract.py",
        "scripts/reach_operator.py",
        "clients/web/src/App.svelte",
        "examples/profiles/public.toml",
        "src/lychd/templates/page.jinja",
        ".github/workflows/core.yml",
    ],
)
def test_project_paths_admit_only_named_public_text_surfaces(path: str) -> None:
    assert public_project_path(path)


@pytest.mark.parametrize(
    "path",
    [
        ".git/config",
        ".env",
        ".agents/scopes/build.md",
        ".github/private.json",
        "private/dossier.md",
        "docs/../private.md",
        "/etc/passwd",
        "docs//index.md",
        "docs/./index.md",
        "docs/a\\b.md",
        "src/.env.json",
        "clients/web/node_modules/package/index.js",
        "src/venv/secret.py",
        "docs/image.png",
        "clients/android/gradle/wrapper/gradle-wrapper.jar",
        "docs/a b.md",
    ],
)
def test_project_paths_exclude_hidden_private_ambient_and_binary_surfaces(path: str) -> None:
    assert not public_project_path(path)


def test_project_schema_is_explicit_and_preserves_complete_digest_bound_source_bytes() -> None:
    text = "# A Python comment is not a document title\nMAX_CONTEXT = 96000\n"
    corpus = project_corpus(("src/lychd/system/constants.py", text), ("ROADMAP.md", "# Roadmap\nPublic stages."))
    source = read_research_document(corpus, "doc:src/lychd/system/constants.py", question="MAX_CONTEXT")
    assert source.title == "src/lychd/system/constants.py"
    assert source.text == text
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == source.source_digest
    assert not source.truncated
    with pytest.raises(ValidationError, match="corpus_legacy"):
        CorpusManifest(source_revision=REVISION, documents=corpus.manifest.documents)
    with pytest.raises(ValueError, match="corpus_content"):
        verify_corpus(corpus.manifest, (b"Altered source", b"Altered roadmap"))


def test_catalogue_is_bounded_metadata_and_unknown_offered_ids_cannot_be_read_by_a_plan() -> None:
    corpus = project_corpus(
        *((f"docs/project-{index:02}.md", "# Knowledge\nA public project fact.") for index in range(40))
    )
    offered = research_document_catalogue(corpus, question="public project knowledge")
    assert len(offered) == MAX_RESEARCH_CATALOGUE_DOCUMENTS
    assert offered == research_document_catalogue(corpus, question="public project knowledge")
    assert all(set(item) == {"id", "title", "url"} for item in offered)
    assert all("public project fact" not in str(item) for item in offered)
    assert offered[0]["id"] == "doc:docs/project-00.md"
    output = '{"kind":"research","text":"Read the relevant source.","source_ids":["doc:docs/project-39.md"]}'
    assert read_research_document(corpus, "doc:docs/project-39.md", question="project").status == "ok"
    with pytest.raises(ValueError, match="conversation_research_sources"):
        parse_research_plan(output, offered)


def test_exact_paths_and_pinned_urls_precede_lexical_title_path_and_body_matches() -> None:
    corpus = project_corpus(
        ("docs/overview.md", "# Graph\nGraph implementation facts."),
        ("src/lychd/system/constants.py", "MAX_CONTEXT = 96000\n"),
        ("ROADMAP.md", "# Roadmap\nFuture work."),
    )
    selected = research_document_catalogue(corpus, question="Graph beside `src/lychd/system/constants.py`")
    assert selected[0]["id"] == "doc:src/lychd/system/constants.py"
    selected = research_document_catalogue(corpus, question=f"Graph {corpus.manifest.documents[2].url}#future")
    assert selected[0]["id"] == "doc:ROADMAP.md"
    assert research_document_matches(corpus, ("Read ROADMAP.md then doc:src/lychd/system/constants.py",)) == (
        "doc:ROADMAP.md",
        "doc:src/lychd/system/constants.py",
    )
    assert research_document_catalogue(corpus, question="zzunfindable") == ()
    assert (
        research_document_matches(corpus, (f"https://github.com/hexanomicon/lychd/blob/{'b' * 40}/ROADMAP.md",)) == ()
    )


def test_project_omissions_are_bound_and_cannot_overlap_admitted_sources() -> None:
    corpus = project_corpus(("README.md", "Public project."))
    manifest = CorpusManifest(
        schema_version=2,
        source_revision=REVISION,
        documents=corpus.manifest.documents,
        omissions=(CorpusOmission(path="uv.lock", reason="document_limit"),),
    )
    assert verify_corpus(manifest, (b"Public project.",)).digest != corpus.digest
    with pytest.raises(ValidationError, match="corpus_duplicate"):
        CorpusManifest(
            schema_version=2,
            source_revision=REVISION,
            documents=corpus.manifest.documents,
            omissions=(CorpusOmission(path="README.md", reason="not_text"),),
        )
    oversized = b"x" * (MAX_DOCUMENT_BYTES + 1)
    bad = corpus.manifest.documents[0].model_copy(update={"sha256": sha256(oversized).hexdigest()})
    with pytest.raises(ValueError, match="corpus_content"):
        verify_corpus(CorpusManifest(schema_version=2, source_revision=REVISION, documents=(bad,)), (oversized,))


def test_worker_loads_large_manifest_and_four_digit_ordinals_beyond_wire_size(tmp_path: Path) -> None:
    corpus = project_corpus(*((f"tests/project_{index:04}.py", "PUBLIC = True\n") for index in range(1001)))
    raw_manifest = corpus.manifest.model_dump_json().encode()
    assert len(raw_manifest) > 65_536
    for document, text in zip(corpus.manifest.documents, corpus.texts, strict=True):
        (tmp_path / document.file).write_text(text)
    (tmp_path / "manifest.json").write_bytes(raw_manifest)
    loaded = load_corpus(tmp_path)
    assert loaded.digest == corpus.digest
    assert loaded.manifest.documents[-1].file == "1000.txt"


def test_long_source_paths_have_the_same_bounded_catalogue_and_read_title() -> None:
    path = "src/" + "module_" * 20 + ".py"
    assert 120 < len(path) <= 200
    corpus = project_corpus((path, "PUBLIC_FACT = True\n"))
    catalogue = research_document_catalogue(corpus, question=path)
    result = read_research_document(corpus, f"doc:{path}", question=path)
    assert result.status == "ok"
    assert catalogue[0]["title"] == result.title == path[:120]


def test_project_kickoff_retrieves_an_available_roadmap_under_its_authored_title() -> None:
    corpus = project_corpus(
        *((f"docs/project-{index:02}.md", "# Project\nA project starts with public facts.") for index in range(40)),
        ("ROADMAP.md", "# Metamorphosis\nProject milestones and delivery stages."),
    )
    offered = research_document_catalogue(corpus, question="Can you kick us off? It is the start of the project.")
    assert len(offered) == MAX_RESEARCH_CATALOGUE_DOCUMENTS
    assert offered[0]["id"] == "doc:ROADMAP.md"
    assert offered[0]["title"] == "Metamorphosis"


@pytest.mark.parametrize("opening", ["Welcome to the laboratory", "Getting started", "Formation"])
def test_kickoff_excerpt_retains_opening_context_instead_of_navigation_or_later_delivery(opening: str) -> None:
    text = (
        "# Project journey\n" + "Background for the wider programme.\n" * 150 + "## Read the delivery books\n"
        "- [Opening](#opening)\n- [Implementation](#implementation)\n"
        '<a id="opening"></a>\n'
        "## First chapter\nThe opening stage brings participants together.\n"
        "### Week 00\n**Dates:** 2\N{EN DASH}8 Nov 2026\nWe explore the project together.\n"
        f"#### {opening}\nMeet the people and follow questions that interest you.\n"
        "There is no assigned implementation or required demonstration.\n"
        "### Week 01\n**Dates:** 9\N{EN DASH}15 Nov\n"
        "#### Project delivery status and first steps\nShip the implementation after its review.\n"
    )
    corpus = project_corpus(("docs/journey.md", text))
    result = read_research_document(
        corpus,
        "doc:docs/journey.md",
        question=(
            "Can you kick us off? It's the start of the project. Read our roadmap and current delivery status, "
            "introduce the project and propose our first steps. End with the so_it_begins GIF if it is available."
        ),
    )
    assert result.status == "ok"
    assert f"#### {opening}" in result.text
    assert "### Week 00\n**Dates:** 2\N{EN DASH}8 Nov 2026" in result.text
    assert "There is no assigned implementation or required demonstration." in result.text
    assert "Ship the implementation" not in result.text
    assert result.excerpt_start > 4000
    assert len(result.text) <= 4000
    assert result.text == text[result.excerpt_start : result.excerpt_start + len(result.text)]
    assert result.source_digest == sha256(text.encode()).hexdigest()
    assert result.text_digest == sha256(result.text.encode()).hexdigest()


@pytest.mark.parametrize("marker", ["-", "1."])
def test_read_imperative_does_not_prefer_a_link_only_section_but_explicit_fragment_can(marker: str) -> None:
    text = (
        "# Handbook\n## Read current delivery status {#read-status}\n"
        f"{marker} [Current delivery status](#status)\n"
        "## Delivery status\nThe reviewed release can be used now.\n"
    )
    corpus = project_corpus(("docs/handbook.md", text))
    result = read_research_document(corpus, "doc:docs/handbook.md", question="Read current delivery status")
    assert result.text == "## Delivery status\nThe reviewed release can be used now.\n"
    explicit = read_research_document(
        corpus,
        "doc:docs/handbook.md",
        question=f"Read current delivery status {corpus.manifest.documents[0].url}#read-status",
    )
    assert (
        explicit.text
        == f"## Read current delivery status {{#read-status}}\n{marker} [Current delivery status](#status)\n"
    )


def test_source_read_finds_an_explicit_function_beyond_opening_imports_and_comments() -> None:
    path = "src/lychd/compositions/reach/documents.py"
    opening = '"""Public research helpers for lychd."""\nfrom research import read_research_document\n'
    text = (
        opening
        + "# unrelated opening material\n" * 400
        + "\ndef read_research_document(corpus, source_id):\n    return 'the requested declaration'\n"
    )
    corpus = project_corpus((path, text))
    result = read_research_document(corpus, f"doc:{path}", question=f"Read read_research_document in {path}")
    assert result.status == "ok"
    assert "def read_research_document(corpus, source_id):" in result.text
    assert "the requested declaration" in result.text
    assert result.excerpt_start > 4000
    assert result.source_digest == sha256(text.encode()).hexdigest()
    assert result.text == text[result.excerpt_start : result.excerpt_start + len(result.text)]
    assert result.truncated


@pytest.mark.parametrize(
    "declaration",
    [
        "export function loadSource() { return 'requested'; }",
        "export default async function loadSource() { return 'requested'; }",
        "export const loadSource = () => 'requested';",
    ],
)
def test_source_read_prefers_a_late_exported_typescript_declaration(declaration: str) -> None:
    path = "clients/web/src/source.ts"
    text = "import { loadSource } from './provider';\n" + "// unrelated material\n" * 400 + declaration
    corpus = project_corpus((path, text))
    result = read_research_document(corpus, f"doc:{path}", question=f"Read loadSource in {path}")
    assert result.status == "ok"
    assert declaration in result.text
    assert result.excerpt_start > 4000
    assert result.text == text[result.excerpt_start : result.excerpt_start + len(result.text)]


@pytest.mark.parametrize("target", ["Week02", "Week 2", "week-02"])
def test_numbered_section_targets_match_authored_labels_and_override_previous_focus(target: str) -> None:
    text = (
        "# Programme\n## First chapter\n### Week 01\nEarlier evidence.\n"
        + "Earlier background.\n" * 300
        + "### Week02\nThe requested method and quotation.\n### Week 03\nLater evidence.\n"
    )
    corpus = project_corpus(("ROADMAP.md", text))
    source = read_research_document(
        corpus, "doc:ROADMAP.md", question=f"Explain {target}", focus="Explain Week 01 in the programme"
    )
    assert source.text == "### Week02\nThe requested method and quotation.\n"
    assert source.excerpt_start == text.index("### Week02")
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(source.text.encode()).hexdigest()


def test_exact_late_fragment_and_adjacent_anchor_survive_fenced_and_frontmatter_decoys() -> None:
    text = (
        '---\n<a id="week-02"></a>\n## False frontmatter\n---\n'
        '# Programme\n````md\n```\n<a id="week-02"></a>\n## False code\n````\n'
        '<a id="week-02"></a>\nThis is not adjacent.\n## Unrelated\n'
        + "Earlier material.\n" * 400
        + '<a id="week-02"></a>\n\n## Second interval\nThe actual section.\n## Third interval\nLater.\n'
    )
    corpus = project_corpus(("ROADMAP.md", text))
    source = read_research_document(
        corpus,
        "doc:ROADMAP.md",
        question=f"Read {corpus.manifest.documents[0].url}#week-02",
        focus="Explain Third interval",
    )
    assert source.text == "## Second interval\nThe actual section.\n"
    assert source.excerpt_start == text.index("## Second interval")


def test_multiple_numbered_sections_keep_adjacent_authored_sections_in_one_exact_read() -> None:
    text = (
        "# Programme\n## Week01\nEarlier.\n## Week02\nMethod two.\n### Notes\nQuotation two.\n"
        "## Week 03\nMethod three.\n## Week04\nLater.\n"
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Compare Week 2 and Week03"
    )
    assert source.text == text[text.index("## Week02") : text.index("## Week04")]
    assert source.text == text[source.excerpt_start : source.excerpt_start + len(source.text)]


@pytest.mark.parametrize("question", ["Explain Week02/03", "Compare Week 2 and Week03"])
def test_numbered_targets_resolve_standalone_week_anchors_with_symbol_only_titles(question: str) -> None:
    text = (
        '# Programme\n## Genesis\n<a id="week-01"></a>\n### 01 · __new__\nEarlier.\n'
        '<a id="week-02"></a>\n### 02 · __init__\nMethod two and its quotation.\n'
        '<a id="week-03"></a>\n### 03 · __next__\nMethod three and its quotation.\n'
        '<a id="week-04"></a>\n### 04 · __call__\nLater.\n'
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question=question, focus="Explain Week01"
    )
    assert "### 02 · __init__" in source.text
    assert "### 03 · __next__" in source.text
    assert "Method two and its quotation." in source.text
    assert "Method three and its quotation." in source.text
    assert "### 01 · __new__" not in source.text
    assert "### 04 · __call__" not in source.text
    assert source.excerpt_start == text.index("### 02 · __init__")
    assert source.text == text[source.excerpt_start : source.excerpt_start + len(source.text)]


@pytest.mark.parametrize("question", ["Explain Week02", "Explain Week 2", "Explain week-02"])
def test_catalogue_discovers_numbered_anchor_targets_before_more_than_sixteen_lexical_distractors(
    question: str,
) -> None:
    text = '# Programme\n## Genesis\n<a id="week-02"></a>\n### 02 · `__init__`\nThe authored method.\n'
    corpus = project_corpus(
        *(
            (f"docs/distractor-{index:02}.md", "# Explain\nWeek02 is a plain lexical distractor.")
            for index in range(20)
        ),
        ("ROADMAP.md", text),
    )
    catalogue = research_document_catalogue(corpus, question=question)
    assert len(catalogue) == MAX_RESEARCH_CATALOGUE_DOCUMENTS
    assert catalogue[0]["id"] == "doc:ROADMAP.md"
    assert all(set(item) == {"id", "title", "url"} for item in catalogue)
    source = read_research_document(corpus, catalogue[0]["id"], question=question)
    assert source.text == "### 02 · `__init__`\nThe authored method.\n"
    exact = research_document_catalogue(corpus, question=f"{question} in docs/distractor-19.md")
    assert exact[0]["id"] == "doc:docs/distractor-19.md"
    pinned = research_document_catalogue(corpus, question=f"{question} {corpus.manifest.documents[19].url}")
    assert pinned[0]["id"] == "doc:docs/distractor-19.md"


def programme_sections() -> str:
    return "## Genesis\nThe parent explains the programme.\n" + "".join(
        f"### Week {week:02}\n#### Methods and quotes\nMethod {week}; quotation {week}.\n" + "Authored detail.\n" * 90
        for week in range(10)
    )


@pytest.mark.parametrize("question", ["Explain Genesis per week with methods and quotes", "ROADMAP.md"])
def test_overview_and_elliptical_reference_retain_the_named_parent_and_all_ten_children(question: str) -> None:
    section = programme_sections()
    assert 4000 < len(section) < 16_000
    text = "# Programme\n## Earlier\n" + "Background.\n" * 400 + section + "## Next chapter\nLater.\n"
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question=question,
        focus="Explain Genesis over the first ten weeks, including its methods and quotes.",
    )
    assert source.text == section
    assert source.excerpt_start == text.index(section)
    assert source.source_chars == len(text)
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(section.encode()).hexdigest()
    assert source.truncated


@pytest.mark.parametrize(
    "scope",
    [
        "each Formation week",
        "every Formation week",
        "per initial Formation week",
        "EACH FÓRMATION WEEK",
        "each Formation chapter",
        "every Formation section",
        "per Formation stage",
    ],
)
def test_qualified_units_read_the_complete_parent_with_bounded_exact_source_custody(scope: str) -> None:
    section = programme_sections().replace("Genesis", "Formation").replace("Methods and quotes", "Methods")
    assert 4000 < len(section) < 16_000
    text = "# Programme\n## Earlier\n" + "Background.\n" * 400 + section + "## Later\nLater.\n"
    corpus = project_corpus(("ROADMAP.md", text))
    source = read_research_document(
        corpus,
        "doc:ROADMAP.md",
        question="You forgot the quotes!",
        focus=f"I will re-read the roadmap to pull the exact quotations for {scope}.",
    )
    assert source.text == section
    assert source.excerpt_start == text.index(section)
    assert source.source_chars == len(text)
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(section.encode()).hexdigest()
    assert source.truncated


@pytest.mark.parametrize("scope", ["Formation week", "each early initial Formation week"])
def test_singular_or_distant_units_keep_the_ordinary_read_bound(scope: str) -> None:
    section = programme_sections().replace("Genesis", "Formation")
    source = read_research_document(
        project_corpus(("ROADMAP.md", "# Programme\n" + section)),
        "doc:ROADMAP.md",
        question=f"Read {scope}.",
    )
    assert source.text == section[:4000]
    assert source.text_digest == sha256(section[:4000].encode()).hexdigest()


@pytest.mark.parametrize("target", ["Week02", "#week-02"])
def test_explicit_unit_targets_take_precedence_over_a_qualified_parent_overview(target: str) -> None:
    section = programme_sections().replace("Genesis", "Formation")
    source = read_research_document(
        project_corpus(("ROADMAP.md", "# Programme\n" + section)),
        "doc:ROADMAP.md",
        question=f"Read {target} from each Formation week.",
    )
    expected = section[section.index("### Week 02") : section.index("### Week 03")]
    assert source.text == expected
    assert source.text_digest == sha256(expected.encode()).hexdigest()


@pytest.mark.parametrize("length", [9000, 4000, 2000, 600])
def test_long_section_projection_distributes_budget_with_exact_ordered_spans_and_digest(length: int) -> None:
    source = read_research_document(
        project_corpus(("ROADMAP.md", "# Programme\n" + programme_sections())),
        "doc:ROADMAP.md",
        question="Explain Genesis weekly",
    )
    projection = project_research_source(source, length)
    assert projection == project_research_source(source, length)
    text = projection["text"]
    spans = cast("list[dict[str, int]]", projection["projection_spans"])
    assert isinstance(text, str)
    assert len(text) <= length
    assert len(spans) <= 48
    for span in spans:
        assert 0 <= span["start"] < span["end"] <= len(source.text)
    assert all(previous["end"] <= current["start"] for previous, current in pairwise(spans))
    assert text == "\n\n".join(source.text[span["start"] : span["end"]] for span in spans)
    assert "## Genesis\n" in text
    for week in range(10):
        assert f"### Week {week:02}\n" in text
    assert projection["projection_budget"] == length
    assert projection["projection_digest"] == sha256(text.encode()).hexdigest()
    assert projection["projection_truncated"]
    assert projection["source_digest"] == source.source_digest
    assert projection["text_digest"] == source.text_digest


@pytest.mark.parametrize("length", [2500, 1800])
@pytest.mark.parametrize("quote_boundary", ["\n\n", "\n>\n\n", "\n>\n"])
def test_long_quote_projection_keeps_each_child_opening_and_following_narrative_with_exact_spans(
    length: int, quote_boundary: str
) -> None:
    section = "## Formation\nThe parent explains the programme.\n" + "".join(
        f"### Interval {week:02}\n**Dates:** authored interval {week}.\n\n> Quotation {week:02}: "
        + "A long authored observation. " * 35
        + f"\n> — Witness{week:02}, [Ref{week:02}](https://example.com/"
        + "long-destination/" * 10
        + f"){quote_boundary}Meaning {week:02}: practise the distinct skill.\n\n"
        for week in range(10)
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", "# Programme\n" + section)),
        "doc:ROADMAP.md",
        question="Formation overview",
    )
    assert source.text == section
    projection = project_research_source(source, length)
    assert projection == project_research_source(source, length)
    text = projection["text"]
    spans = cast("list[dict[str, int]]", projection["projection_spans"])
    assert isinstance(text, str)
    assert len(text) <= length
    assert len(spans) == 31
    assert len(spans) <= 48
    for week in range(10):
        assert f"### Interval {week:02}\n" in text
        assert f"> Quotation {week:02}: " in text
        assert f"> — Witness{week:02}, [Ref{week:02}]" in text
        assert f"Meaning {week:02}: practise the distinct skill." in text
    assert all(0 <= span["start"] < span["end"] <= len(source.text) for span in spans)
    assert all(previous["end"] <= current["start"] for previous, current in pairwise(spans))
    assert text == "\n\n".join(source.text[span["start"] : span["end"]] for span in spans)
    assert projection["projection_budget"] == length
    assert projection["projection_digest"] == sha256(text.encode()).hexdigest()
    assert projection["projection_truncated"]
    assert projection["source_digest"] == source.source_digest
    assert projection["text_digest"] == source.text_digest
    assert "long-destination/" not in text


def test_ordinary_reads_keep_four_thousand_character_cap_and_projections_are_prefixes() -> None:
    text = "# Ordinary document\n" + "Public source text.\n" * 1000
    source = read_research_document(project_corpus(("README.md", text)), "doc:README.md", question="Read README.md")
    assert len(source.text) == 4000
    for length in (0, 1, 50, 4000, 16_000):
        projection = project_research_source(source, length)
        assert projection["text"] == source.text[:length]
        assert projection["projection_spans"] == ([{"start": 0, "end": min(length, 4000)}] if length else [])
        assert projection["projection_truncated"] == (length < 4000)
    with pytest.raises(ValueError, match="research_projection_length"):
        project_research_source(source, -1)


@pytest.mark.parametrize("question", ["Formation overview", "Read every Formation stage"])
def test_large_parent_read_is_capped_and_code_does_not_gain_markdown_projection(question: str) -> None:
    text = "# Programme\n## Formation\n" + "### Stage\nAuthored detail.\n" * 1000
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question=question)
    assert len(source.text) == 16_000
    assert source.text == text[source.excerpt_start : source.excerpt_start + len(source.text)]
    code = "# Source\n# Week 01\n" + "value = 1\n" * 800 + "# Week 02\n"
    ordinary = read_research_document(
        project_corpus(("src/programme.py", code)), "doc:src/programme.py", question="src/programme.py weekly overview"
    )
    assert len(ordinary.text) == 4000
    assert project_research_source(ordinary, 600)["text"] == ordinary.text[:600]


def test_ordinary_next_does_not_misidentify_a_late_dunder_symbol_as_an_explicit_target() -> None:
    text = "PUBLIC = True\n" + "# Unrelated material\n" * 400 + "def __next__(self):\n    return self.value\n"
    corpus = project_corpus(("src/iterator.py", text))
    ordinary = read_research_document(corpus, "doc:src/iterator.py", question="What comes next?")
    explicit = read_research_document(corpus, "doc:src/iterator.py", question="Explain __next__")
    assert ordinary.excerpt_start == 0
    assert "def __next__" not in ordinary.text
    assert "def __next__" in explicit.text


@pytest.mark.parametrize("question", ["What comes next?", "What comes in the next weeks?"])
def test_markdown_prose_next_keeps_acknowledged_parent_focus_instead_of_a_code_identifier(question: str) -> None:
    section = (
        '## Genesis\nThe programme.\n<a id="week-02"></a>\n### 02 · `__init__`\nMethod two.\n'
        '<a id="week-09"></a>\n### 09 · `__next__`\n#### Methods\nMethod nine.\n'
    )
    corpus = project_corpus(("ROADMAP.md", "# Programme\n" + section))
    source = read_research_document(
        corpus, "doc:ROADMAP.md", question=question, focus="Explain Genesis per week with its methods"
    )
    assert source.text == section
    explicit = read_research_document(corpus, "doc:ROADMAP.md", question="Explain __next__")
    assert explicit.text.startswith("### 09 · `__next__`\n")
    assert "Method nine." in explicit.text
    assert "Method two." not in explicit.text


def test_overlong_numbered_label_does_not_crash_or_override_acknowledged_focus() -> None:
    text = "# Programme\n## Genesis\n### Week02\nMethod two.\n"
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question="Explain Week" + "9" * 5000,
        focus="Explain Genesis weekly",
    )
    assert source.text == "## Genesis\n### Week02\nMethod two.\n"
