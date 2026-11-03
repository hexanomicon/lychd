"""Pinned project text remains bounded knowledge, with offered-ID and source-byte custody."""

from __future__ import annotations

from hashlib import sha256
from itertools import pairwise
from pathlib import Path
from typing import Literal, cast

import pytest
from pydantic import ValidationError
from scripts.reach_worker import load_corpus

from lychd.compositions.reach.conversation_references import reference_selectors
from lychd.compositions.reach.documents import (
    MAX_DOCUMENT_BYTES,
    MAX_RESEARCH_CATALOGUE_DOCUMENTS,
    MAX_RESEARCH_SECTION_MATCH_CHARS,
    RESEARCH_PROJECTION_OMISSION,
    CorpusDocument,
    CorpusManifest,
    CorpusOmission,
    PublicCorpus,
    _research_numbered_targets,  # pyright: ignore[reportPrivateUsage] - bounded range parsing boundary
    project_research_source,
    public_project_path,
    read_research_document,
    render_research_projection,
    research_document_catalogue,
    research_document_matches,
    research_projection_mode,
    verify_corpus,
)
from lychd.compositions.reach.research import parse_research_plan
from tests.unit.compositions.test_reach_conversation_references import anchored_request
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


@pytest.mark.parametrize("question", ["What is the first small thing to try today?", "Explain the first living thread"])
def test_nested_selection_keeps_its_own_stage_dates_and_method_across_a_long_parent_quote(question: str) -> None:
    owner = (
        "### Stage 17 · `participate`\n**Dates:** 9\N{EN DASH}15 Nov\n\n> "
        + "An authored observation between the owner and its child. " * 20
        + "\n\n#### Choose the first living thread\n"
        "Choose one useful encounter and inspect it together.\n"
    )
    text = (
        "# Programme\n## Formation\n### Stage 16 · `begin`\nEarlier activity belongs to another stage.\n"
        + owner
        + "### Stage 18\nLater activity.\n"
    )
    assert text.index("#### Choose") - text.index("### Stage 17") > 600
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question=question)
    assert source.status == "ok"
    assert source.text == owner
    assert source.excerpt_start == text.index(owner)
    assert "### Stage 16" not in source.text
    assert "### Stage 18" not in source.text
    assert len(source.text) <= 4000
    assert source.text == text[source.excerpt_start : source.excerpt_start + len(source.text)]
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(owner.encode()).hexdigest()


def test_nested_selection_refuses_when_owner_and_meaningful_child_opening_cannot_fit_the_read_budget() -> None:
    text = (
        "# Programme\n## Formation\n### Stage 16\nEarlier activity.\n"
        "### Stage 17 · `participate`\n**Dates:** 9\N{EN DASH}15 Nov\n\n> "
        + "An authored observation. "
        * 200
        + "\n\n#### Choose the first living thread\nChoose one useful encounter together.\n"
        "### Stage 18\nLater activity.\n"
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Explain the first living thread"
    )
    assert source.status == "refused"
    assert source.reason == "research_document_context"
    assert source.text == ""
    assert source.source_digest is None
    assert source.text_digest is None


def test_late_lexical_hit_cannot_shift_a_selected_child_past_its_owner_and_dates() -> None:
    owner = "### Stage 17 · `participate`\n**Dates:** 9\N{EN DASH}15 Nov\n\n"
    text = (
        "# Programme\n## Formation\n### Stage 16\nEarlier activity.\n"
        + owner
        + "#### Welcome to the laboratory\n"
        + "Unrelated authored background.\n" * 160
        + "The uniqueneedle appears only after the ordinary read boundary.\n"
        "### Stage 18\nLater activity.\n"
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question="Kick us off and explain uniqueneedle",
    )
    assert source.status == "ok"
    assert source.excerpt_start == text.index(owner)
    assert source.text.startswith(owner)
    assert "#### Welcome to the laboratory\n" in source.text
    assert "uniqueneedle" not in source.text
    assert len(source.text) == 4000
    assert source.truncated
    assert source.text == text[source.excerpt_start : source.excerpt_start + len(source.text)]
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(source.text.encode()).hexdigest()


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


@pytest.mark.parametrize("targets", ["Weeks 01 and 02", "Weeks01 and02", "Weeks 01, 02", "Weeks01/02"])
def test_elliptical_comparison_uses_the_plans_coordinated_targets_with_exact_source_custody(targets: str) -> None:
    text = "# Programme\n## Formation\n" + "".join(
        f'<a id="week-{number:02}"></a>\n### {number:02} · `method_{number}`\nQuotation and meaning {number}.\n'
        for number in range(4)
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question="Compare the second and third weeks from your answer, including their methods and quotations.",
        focus=f"I will read {targets} to compare their methods and quotations.",
    )
    expected = text[text.index("### 01 ·") : text.index("### 03 ·")]
    assert source.text == expected
    assert source.excerpt_start == text.index("### 01 ·")
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(expected.encode()).hexdigest()


@pytest.mark.parametrize("targets", ["Stages1,2 and4", "Stages 1, 2, and 4", "Stages1/2/4"])
def test_coordinated_numbered_lists_keep_only_the_smallest_contiguous_available_section_range(targets: str) -> None:
    text = "# Programme\n" + "".join(f"## Stage{number}\nAuthored detail {number}.\n" for number in range(6))
    corpus = project_corpus(("ROADMAP.md", text))
    source = read_research_document(corpus, "doc:ROADMAP.md", question=f"Compare {targets}")
    expected = text[text.index("## Stage1") : text.index("## Stage5")]
    assert source.text == expected
    assert source.text_digest == sha256(expected.encode()).hexdigest()
    explicit = read_research_document(corpus, "doc:ROADMAP.md", question=f"Compare {targets} at #stage4")
    assert explicit.text == "## Stage4\nAuthored detail 4.\n"


@pytest.mark.parametrize("tail", ["and the 4 priorities", "and then 4", "and 9999999", ", 9999999"])
def test_coordinated_numbered_lists_do_not_promote_intervening_prose_or_overlong_numbers(tail: str) -> None:
    text = "# Programme\n## Stage1\nFirst.\n## Stage4\nUnrelated.\n"
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question=f"Explain Stage1 {tail}"
    )
    assert source.text == "## Stage1\nFirst.\n"


@pytest.mark.parametrize(
    "question", ["Explain the opening chapter and the following chapter", "Compare first and second chapters"]
)
def test_source_relative_opening_and_following_units_use_authored_labels(question: str) -> None:
    text = (
        "# Programme\n## Formation\n### Chapter0 · `begin`\nOpening quotation and meaning.\n"
        "### Chapter1 · `participate`\nFollowing quotation and meaning.\n### Chapter2\nLater.\n"
    )
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question=question)
    expected = text[text.index("### Chapter0") : text.index("### Chapter2")]
    assert source.text == expected
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(expected.encode()).hexdigest()


@pytest.mark.parametrize("question", ["Compare the second and third stages", "Compare second stage and third stage"])
def test_source_relative_ordinals_follow_authored_order_instead_of_incrementing_numbers(question: str) -> None:
    text = (
        '# Programme\n## Formation\n<a id="stage-10"></a>\n### `begin`\nFirst.\n'
        '<a id="stage-20"></a>\n### `participate`\nSecond.\n'
        '<a id="stage-30"></a>\n### `complete`\nThird.\n## Later\nUnrelated.\n'
    )
    corpus = project_corpus(("ROADMAP.md", text))
    source = read_research_document(corpus, "doc:ROADMAP.md", question=question)
    expected = text[text.index("### `participate`") : text.index("## Later")]
    assert source.text == expected
    assert source.text_digest == sha256(expected.encode()).hexdigest()
    literal = read_research_document(corpus, "doc:ROADMAP.md", question=question + " about `begin`")
    assert literal.text.startswith("### `begin`\n")
    assert "Second." not in literal.text
    fragment = read_research_document(corpus, "doc:ROADMAP.md", question=question + " at #stage-10")
    assert fragment.text == literal.text


@pytest.mark.parametrize("question", ["Explain the following stage", "What comes next?", "Explain the first galaxy"])
def test_unanchored_or_unknown_ordinal_units_do_not_override_acknowledged_source_focus(question: str) -> None:
    text = "# Programme\n## Formation\n### Stage10\nFirst.\n### Stage20\nSecond.\n"
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question=question,
        focus="Explain Formation overview",
    )
    assert source.text == text[text.index("## Formation") :]


def test_named_parent_scopes_ordinal_units_before_global_order_and_explicit_targets_still_win() -> None:
    text = (
        "# Programme\n## Alpha\n### Stage10 · `alpha_method` {#alpha-stage}\nAlpha detail.\n"
        "## Beta\n### Stage20 {#beta-stage}\nBeta opening.\n### Stage30\nBeta following.\n"
        "## First\n### Stage40\nUnrelated later branch.\n## Gamma\nNo authored stages here.\n"
    )
    corpus = project_corpus(("ROADMAP.md", text))
    question = "Compare Beta's first and second stages"
    source = read_research_document(corpus, "doc:ROADMAP.md", question=question)
    expected = text[text.index("### Stage20") : text.index("## First")]
    assert source.text == expected
    assert "Stage10" not in source.text
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(expected.encode()).hexdigest()
    for target in ("#alpha-stage", "`alpha_method`"):
        explicit = read_research_document(corpus, "doc:ROADMAP.md", question=question + " at " + target)
        assert explicit.text.startswith("### Stage10")
        assert "Stage20" not in explicit.text
    for ambiguous in (
        "Compare Alpha and Beta's first and second stages",
        "Explain Gamma's first stage",
        "Explain the following stage",
    ):
        unresolved = read_research_document(corpus, "doc:ROADMAP.md", question=ambiguous)
        assert unresolved.status == "refused"
        assert unresolved.reason == "research_document_context"
        assert unresolved.text == ""
        resolved = read_research_document(corpus, "doc:ROADMAP.md", question=ambiguous, focus="Read #beta-stage")
        if ambiguous == "Explain the following stage":
            assert resolved.text == "### Stage20 {#beta-stage}\nBeta opening.\n"
        else:
            assert resolved.status == "refused"
            assert resolved.reason == "research_document_context"
            assert resolved.text == ""
    unnamed = read_research_document(corpus, "doc:ROADMAP.md", question="Compare the first and second stages")
    assert unnamed.text.startswith("### Stage10")
    assert "### Stage20" in unnamed.text
    assert "Stage30" not in unnamed.text


def test_nested_named_parents_use_the_unique_most_specific_branch_for_ordinal_units() -> None:
    text = (
        "# Programme\n## Alpha\n### Stage10\nAlpha.\n## Beta\n### Beta branch\n"
        "#### Stage20\nBranch opening.\n#### Stage30\nBranch following.\n"
        "### Other\n#### Stage40\nOther branch.\n"
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question="Compare Beta branch's first and second stages",
    )
    assert source.text == text[text.index("#### Stage20") : text.index("### Other")]


def test_nested_partial_parent_name_keeps_ancestor_scope_until_a_distinguishing_child_term_is_named() -> None:
    text = (
        "# Programme\n## Beta\n### Earlier\n#### Stage10\nEarlier detail.\n"
        "### Beta branch\n#### Stage20\nBranch opening.\n#### Stage30\nBranch following.\n## Later\nUnrelated.\n"
    )
    corpus = project_corpus(("ROADMAP.md", text))
    source = read_research_document(corpus, "doc:ROADMAP.md", question="Compare Beta's first and second stages")
    expected = text[text.index("#### Stage10") : text.index("#### Stage30")]
    assert source.text == expected
    assert "Stage30" not in source.text
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(expected.encode()).hexdigest()
    child = read_research_document(corpus, "doc:ROADMAP.md", question="Compare Beta branch's first and second stages")
    assert child.text == text[text.index("#### Stage20") : text.index("## Later")]


def test_after_first_week_keeps_the_anchor_and_following_sibling_as_exact_source_context() -> None:
    text = (
        "# Programme\n## Formation\n### Week00 · `begin`\n**Dates:** opening interval.\nOpening meaning.\n"
        "### Week01 · `participate`\n**Dates:** following interval.\nFollowing method and quotation.\n"
        "### Week02 · `establish`\nLater meaning.\n"
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question="And what comes after that first week?",
        focus="I will read Week00 to explain the opening stage.",
    )
    expected = text[text.index("### Week00") : text.index("### Week02")]
    assert source.text == expected
    assert "`participate`" in source.text
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(expected.encode()).hexdigest()


@pytest.mark.parametrize(
    "question",
    [
        (
            "Hey Nadir, today is the first day of the project. Kick us off: what should we do today, "
            "and what lies ahead? Keep it welcoming and concrete."
        ),
        "Explain the first week and what comes next.",
        "Explain the opening week and the upcoming timeline.",
    ],
)
def test_opening_outlook_keeps_current_and_following_authored_weeks_with_their_own_dates(question: str) -> None:
    text = (
        '# Roadmap\n## Genesis · 00\N{EN DASH}09\nFormation.\n<a id="week-00"></a>\n'
        "### 00 · `__new__`\n**Dates:** 2\N{EN DASH}8 Nov 2026\nThere are no delivery assignments.\n"
        "#### Welcome to the laboratory\nMeet the people and the idea.\n"
        '<a id="week-01"></a>\n### 01 · `__enter__`\n**Dates:** 9\N{EN DASH}15 Nov\n'
        "#### Choose the first living thread\nChoose the first useful shared task.\n"
        '<a id="week-02"></a>\n### 02 · `__init__`\n**Dates:** 16\N{EN DASH}22 Nov\nLater.\n'
    )
    corpus = project_corpus(("docs/roadmap.md", text))
    source = read_research_document(
        corpus,
        "doc:docs/roadmap.md",
        question=question,
        focus=(
            "Read the roadmap's opening stage and timeline, the README's project purpose and current status, "
            "and the CONTRIBUTING guide's first steps for new participants."
        ),
    )
    expected = text[text.index("### 00 ·") : text.index("### 02 ·")]
    assert source.text == expected
    assert "### 00 · `__new__`\n**Dates:** 2\N{EN DASH}8 Nov 2026" in source.text
    assert "### 01 · `__enter__`\n**Dates:** 9\N{EN DASH}15 Nov" in source.text
    assert "There are no delivery assignments." in source.text
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(expected.encode()).hexdigest()
    plain = read_research_document(corpus, "doc:docs/roadmap.md", question="Explain the first week.")
    assert "__enter__" not in plain.text
    explicit = read_research_document(corpus, "doc:docs/roadmap.md", question=question + " at #week-00")
    assert "__enter__" not in explicit.text


def test_opening_outlook_refuses_when_following_unit_context_cannot_fit_the_existing_document_cap() -> None:
    text = "# Programme\n## Formation\n### Stage10\n" + "Opening detail.\n" * 1100 + "### Stage20\nFollowing detail.\n"
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question="Explain the first stage and what lies ahead.",
    )
    assert source.status == "refused"
    assert source.reason == "research_document_context"
    assert source.text == ""


def test_relational_ordinal_context_stays_within_the_named_parent_and_existing_siblings() -> None:
    text = (
        "# Programme\n## Alpha\n### Stage10\nAlpha.\n## Beta\n### Stage20\nBeta first.\n"
        "### Stage30\nBeta second.\n### Stage40\nBeta third.\n## Later\nUnrelated.\n"
    )
    corpus = project_corpus(("ROADMAP.md", text))
    after = read_research_document(corpus, "doc:ROADMAP.md", question="In Beta, what comes after the first stage?")
    assert after.text == text[text.index("### Stage20") : text.index("### Stage40")]
    before = read_research_document(corpus, "doc:ROADMAP.md", question="In Beta, what comes before the third stage?")
    assert before.text == text[text.index("### Stage30") : text.index("## Later")]
    plain = read_research_document(corpus, "doc:ROADMAP.md", question="Explain Beta's first stage")
    assert plain.text == "### Stage20\nBeta first.\n"
    absent = read_research_document(corpus, "doc:ROADMAP.md", question="In Beta, what comes after the third stage?")
    assert absent.text == "### Stage40\nBeta third.\n"
    other_parent = read_research_document(corpus, "doc:ROADMAP.md", question="What comes after the first stage?")
    assert other_parent.text == "### Stage10\nAlpha.\n"
    explicit = read_research_document(corpus, "doc:ROADMAP.md", question="In Beta, after the first stage at #stage40?")
    assert explicit.text == absent.text


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


@pytest.mark.parametrize("unit", ["Week", "Stage", "Chapter"])
@pytest.mark.parametrize("separator", ["-", "\N{EN DASH}", " to ", " through", " through "])
def test_numbered_ranges_select_only_the_requested_contiguous_sections_before_parent_and_focus(
    unit: str, separator: str
) -> None:
    section = "## Formation\nThe complete programme.\n" + "".join(
        f'<a id="{unit.casefold()}-{number:02}"></a>\n### {number:02} · `method_{number}`\n'
        f"> Complete quotation {number}.\n\nMeaning {number}.\n" + "Authored detail.\n" * 95
        for number in range(5)
    )
    text = "# Programme\n" + section + "## Later\nLater material.\n"
    corpus = project_corpus(("ROADMAP.md", text))
    source = read_research_document(
        corpus,
        "doc:ROADMAP.md",
        question=f"Explain Formation {unit}s 00{separator}02. Include each method and exact quotation.",
        focus=f"Explain {unit} 04 in Formation weekly",
    )
    expected = text[text.index("### 00 ·") : text.index("### 03 ·")]
    assert 4000 < len(expected) < 16_000
    assert source.text == expected
    assert source.excerpt_start == text.index("### 00 ·")
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(expected.encode()).hexdigest()
    assert source.truncated
    assert "method_3" not in source.text
    assert "method_4" not in source.text
    complete = project_research_source(source, len(expected))
    assert complete["text"] == expected
    assert not complete["projection_truncated"]
    assert RESEARCH_PROJECTION_OMISSION not in cast("str", complete["text"])
    fragment = read_research_document(
        corpus,
        "doc:ROADMAP.md",
        question=f"Explain {unit}s 00{separator}02 at #{unit.casefold()}-04",
    )
    assert fragment.text.startswith("### 04 ·")
    assert "method_0" not in fragment.text


def test_numbered_range_catalogue_precedes_lexical_distractors_but_exact_paths_still_win() -> None:
    corpus = project_corpus(
        *(
            (f"docs/distractor-{number:02}.md", "# Formation\nFormation stages and exact quotations.")
            for number in range(20)
        ),
        ("ROADMAP.md", "# Programme\n## Formation\n### Stage00\nFirst.\n### Stage 01\nSecond.\n### Stage02\nThird.\n"),
    )
    question = "Explain Formation Stages 00\N{EN DASH}02 and their exact quotations"
    catalogue = research_document_catalogue(corpus, question=question)
    assert catalogue[0]["id"] == "doc:ROADMAP.md"
    exact = research_document_catalogue(corpus, question=question + " in docs/distractor-19.md")
    assert exact[0]["id"] == "doc:docs/distractor-19.md"


@pytest.mark.parametrize("separator", ["-", " to ", " through "])
def test_numbered_range_bounds_match_available_sections_without_materializing_requested_integers(
    separator: str,
) -> None:
    text = "# Programme\n## Formation\n### Stage00\nFirst.\n### Stage999999\nLast.\n## Later\nUnrelated.\n"
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question=f"Explain Stages 0{separator}999999"
    )
    assert source.text == text[text.index("### Stage00") : text.index("## Later")]
    malformed = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question="Explain Stages " + "9" * 5000 + "-" + "9" * 5000,
        focus="Explain Stage999999",
    )
    assert malformed.text == "### Stage999999\nLast.\n"


@pytest.mark.parametrize("expression", ["Weeks 00 through week09", "Weeks00 to Week 09", "Weeks00-Week09"])
def test_numbered_ranges_allow_only_a_repeated_same_unit_without_duplicate_endpoints(expression: str) -> None:
    assert _research_numbered_targets(expression) == frozenset({("weeks", 0, 9)})


@pytest.mark.parametrize("expression", ["Stages2 through0", "Stages02 to Stage00", "Stages2-Stage0"])
def test_reversed_numbered_ranges_do_not_select_either_endpoint_or_expand(expression: str) -> None:
    assert _research_numbered_targets(expression) == frozenset()


@pytest.mark.parametrize(
    "tail", [" through Chapter02", " to Chapter02", " today02", " throughout02", " through 1000000"]
)
def test_range_words_do_not_expand_foreign_units_prose_or_overlong_endpoints(tail: str) -> None:
    text = "# Programme\n" + "".join(f"## Stage{number:02}\nDetail {number}.\n" for number in range(3))
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Stages00" + tail)
    assert source.text == "## Stage00\nDetail 0.\n"


@pytest.mark.parametrize("parent", ["Genesis", "Aurora"])
@pytest.mark.parametrize("unit", ["Week", "Stage"])
def test_acknowledged_through_range_focus_reads_all_ten_authored_sections(parent: str, unit: str) -> None:
    section = "".join(
        f'<a id="{unit.casefold()}-{number:02}"></a>\n### {number:02} · `method_{number}`\n'
        f"> Complete quotation {number}.\n\nPurpose {number}.\n" + "Authored detail.\n" * 35
        for number in range(10)
    )
    text = f"# Programme\n## {parent}\nThe parent describes this programme.\n" + section + "## Later\nUnrelated.\n"
    focus = (
        f"{unit}s 00 through 09 in the {parent} phase of docs/roadmap.md: full untruncated quote text, "
        "method description, and purpose/action for each week. Also check docs/divination/transmutation/genesis.md "
        "for any additional full quote or methodological context per week."
    )
    source = read_research_document(
        project_corpus(("docs/roadmap.md", text)),
        "doc:docs/roadmap.md",
        question="Please give just methods and full quotes and purpose whybdidnuntrim it xD",
        focus=focus,
    )
    expected = text[text.index("### 00 ·") : text.index("## Later")]
    assert 4000 < len(expected) < 16_000
    assert source.text == expected
    assert source.excerpt_start == text.index("### 00 ·")
    assert source.text_digest == sha256(expected.encode()).hexdigest()
    assert all(f"method_{number}" in source.text for number in range(10))
    assert "Unrelated" not in source.text


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
    assert text == render_research_projection(source.text, spans)
    assert "## Genesis\n" in text
    for week in range(10):
        assert f"### Week {week:02}\n" in text
    assert projection["projection_budget"] == length
    assert projection["projection_digest"] == sha256(text.encode()).hexdigest()
    assert projection["projection_truncated"]
    assert projection["source_digest"] == source.source_digest
    assert projection["text_digest"] == source.text_digest


@pytest.mark.parametrize("length", [2000, 2367])
def test_compact_markdown_range_balances_all_siblings_quotes_and_meanings_with_exact_provenance(length: int) -> None:
    section = "".join(
        f"### Interval {number:02}\n**Dates:** authored interval {number}.\n\n"
        f"> Exact quotation {number}: observe this complete authored sentence.\n> \N{EM DASH} Witness {number}\n\n"
        f"Meaning {number}: practise the distinct skill.\n\n" + "Further authored detail. " * 35 + "\n\n"
        for number in range(3)
    )
    text = "# Programme\n" + section
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Explain Intervals 00\N{EN DASH}02"
    )
    assert 2367 < len(source.text) < 4000
    assert source.text == section
    projection = project_research_source(source, length)
    rendered = cast("str", projection["text"])
    spans = cast("list[dict[str, int]]", projection["projection_spans"])
    assert projection == project_research_source(source, length)
    assert len(rendered) <= length
    assert len(spans) <= 48
    assert rendered == render_research_projection(source.text, spans)
    assert all(0 <= span["start"] < span["end"] <= len(source.text) for span in spans)
    assert all(left["end"] <= right["start"] for left, right in pairwise(spans))
    for number in range(3):
        assert f"### Interval {number:02}\n" in rendered
        assert f"> Exact quotation {number}: observe this complete authored sentence.\n" in rendered
        assert f"Meaning {number}: practise the distinct skill." in rendered
    assert RESEARCH_PROJECTION_OMISSION in rendered
    assert projection["projection_budget"] == length
    assert projection["projection_truncated"]
    assert projection["projection_digest"] == sha256(rendered.encode()).hexdigest()
    assert projection["source_digest"] == sha256(text.encode()).hexdigest()
    assert projection["text_digest"] == sha256(section.encode()).hexdigest()


def test_single_section_markdown_keeps_prefix_projection_when_trimmed() -> None:
    text = "# Handbook\n## One section\n" + "Authored detail.\n" * 300
    source = read_research_document(project_corpus(("README.md", text)), "doc:README.md", question="Read README.md")
    projection = project_research_source(source, 600)
    end = 600 - len(RESEARCH_PROJECTION_OMISSION)
    assert len(source.text) == 4000
    assert projection["projection_spans"] == [{"start": 0, "end": end}]
    assert projection["text"] == source.text[:end] + RESEARCH_PROJECTION_OMISSION


@pytest.mark.parametrize("length", [3000, 2500])
@pytest.mark.parametrize("quote_boundary", ["\n\n", "\n>\n\n", "\n>\n"])
def test_long_quote_projection_keeps_each_child_opening_and_following_narrative_with_exact_spans(
    length: int, quote_boundary: str
) -> None:
    # Explicit omission boundaries consume budget; 1800 cannot retain all three
    # source components for all ten children as well as those boundaries.
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
    assert text == render_research_projection(source.text, spans)
    assert projection["projection_budget"] == length
    assert projection["projection_digest"] == sha256(text.encode()).hexdigest()
    assert projection["projection_truncated"]
    assert projection["source_digest"] == source.source_digest
    assert projection["text_digest"] == source.text_digest
    assert "long-destination/" not in text


def test_projection_renderer_marks_prefix_gaps_and_tail_without_changing_contiguous_source() -> None:
    text = "PREFIX first OMITTED second TAIL"
    spans = [{"start": 7, "end": 12}, {"start": 21, "end": 27}]
    assert render_research_projection(text, spans) == (
        RESEARCH_PROJECTION_OMISSION + "first" + RESEARCH_PROJECTION_OMISSION + "second" + RESEARCH_PROJECTION_OMISSION
    )
    assert render_research_projection(text, [{"start": 0, "end": 7}, {"start": 7, "end": len(text)}]) == text
    assert render_research_projection(text, []) == ""
    with pytest.raises(ValueError, match="research_projection_spans"):
        render_research_projection(text, [{"start": 5, "end": 12}, {"start": 7, "end": 15}])


@pytest.mark.parametrize("length", [0, 1, 19, 20, 40, 600, 1800])
def test_tight_projection_budgets_keep_explicit_omissions_and_exact_source_provenance(length: int) -> None:
    text = "# Programme\n" + programme_sections()
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Genesis weekly")
    projection = project_research_source(source, length)
    rendered = cast("str", projection["text"])
    spans = cast("list[dict[str, int]]", projection["projection_spans"])
    assert len(rendered) <= length
    assert projection == project_research_source(source, length)
    assert rendered == render_research_projection(source.text, spans)
    assert projection["projection_digest"] == sha256(rendered.encode()).hexdigest()
    assert projection["source_digest"] == source.source_digest
    assert projection["text_digest"] == source.text_digest
    assert projection["projection_truncated"]
    if spans:
        assert RESEARCH_PROJECTION_OMISSION in rendered
    if length <= len(RESEARCH_PROJECTION_OMISSION):
        assert spans == []
        assert rendered == ""
    if length >= 600:
        assert all(f"### Week {number:02}\n" in rendered for number in range(10))


def test_ordinary_reads_keep_four_thousand_character_cap_and_mark_projected_prefix_omissions() -> None:
    text = "# Ordinary document\n" + "Public source text.\n" * 1000
    source = read_research_document(project_corpus(("README.md", text)), "doc:README.md", question="Read README.md")
    assert len(source.text) == 4000
    for length in (0, 1, 50, 4000, 16_000):
        projection = project_research_source(source, length)
        spans = cast("list[dict[str, int]]", projection["projection_spans"])
        assert projection["text"] == render_research_projection(source.text, spans)
        assert len(cast("str", projection["text"])) <= length
        if spans:
            assert spans == [{"start": 0, "end": spans[0]["end"]}]
            expected = source.text[: spans[0]["end"]]
            if spans[0]["end"] < len(source.text):
                expected += RESEARCH_PROJECTION_OMISSION
            assert projection["text"] == expected
        if 0 < length < 4000 and spans:
            assert cast("str", projection["text"]).endswith(RESEARCH_PROJECTION_OMISSION)
        if length >= 4000:
            assert projection["text"] == source.text
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
    projection = project_research_source(ordinary, 600)
    assert projection["text"] == ordinary.text[: 600 - len(RESEARCH_PROJECTION_OMISSION)] + RESEARCH_PROJECTION_OMISSION


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


def test_explicit_authored_symbols_select_sections_before_parent_focus_and_after_exact_fragments() -> None:
    text = (
        "# Programme\n```md\n### False `third`\n```\n## Formation\nThe parent.\n"
        "### `__first__`\nFirst method.\n### Second {#second}\nSecond method.\n"
        "### `third`\nThird method.\n### Later\nLater method.\n"
    )
    corpus = project_corpus(("ROADMAP.md", text))
    source = read_research_document(
        corpus,
        "doc:ROADMAP.md",
        question="Compare __first__ and `third`",
        focus="Explain Formation overview",
    )
    expected = text[text.index("### `__first__`") : text.index("### Later")]
    assert source.text == expected
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(expected.encode()).hexdigest()
    current = read_research_document(corpus, "doc:ROADMAP.md", question="Explain `third`", focus="Explain __first__")
    assert current.text == "### `third`\nThird method.\n"
    fragment = read_research_document(corpus, "doc:ROADMAP.md", question="Compare __first__ and `third` at #second")
    assert fragment.text == "### Second {#second}\nSecond method.\n"
    for question in ("What happens third?", "Explain prefix__first__suffix"):
        ordinary = read_research_document(
            corpus, "doc:ROADMAP.md", question=question, focus="Explain Formation overview"
        )
        assert ordinary.text.startswith("## Formation\n")
        assert "First method." in ordinary.text
        assert "Third method." in ordinary.text


def test_overlong_numbered_label_does_not_crash_or_override_acknowledged_focus() -> None:
    text = "# Programme\n## Genesis\n### Week02\nMethod two.\n"
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question="Explain Week" + "9" * 5000,
        focus="Explain Genesis weekly",
    )
    assert source.text == "## Genesis\n### Week02\nMethod two.\n"


def test_anchor_observations_select_actual_labels_before_source_ordinal_order_and_model_focus() -> None:
    text = "# Programme\n## Formation\n" + "".join(
        f"### Week {number:02}\nAuthored method {number}.\n" for number in (0, 1, 2, 4, 9, 12, 13)
    )
    corpus = project_corpus(("ROADMAP.md", text))
    request = anchored_request("1. Week04\n1. Week09\n1. Week12\n")
    original_question = request.event.question
    ordinary = read_research_document(corpus, "doc:ROADMAP.md", question=original_question)
    assert ordinary.text.startswith("### Week 01\n")
    source = read_research_document(
        corpus,
        "doc:ROADMAP.md",
        question=original_question,
        focus="Compare Week02 and Week03",
        reference_labels=reference_selectors(request),
    )
    expected = text[text.index("### Week 09\n") : text.index("### Week 13\n")]
    assert source.status == "ok"
    assert source.id == "doc:ROADMAP.md"
    assert source.text == expected
    assert source.excerpt_start == text.index(expected)
    assert source.source_chars == len(text)
    assert source.source_digest == sha256(text.encode()).hexdigest()
    assert source.text_digest == sha256(expected.encode()).hexdigest()
    assert request.event.question == original_question
    unknown = read_research_document(
        corpus, "doc:unoffered.md", question=original_question, reference_labels=reference_selectors(request)
    )
    assert unknown.status == "refused"
    assert unknown.reason == "research_document_unknown"


@pytest.mark.parametrize("question", ["Read Week04", "Read #week-04", "Read `__init__`"])
def test_literal_current_targets_precede_observed_anchor_labels(question: str) -> None:
    text = "# Programme\n## Formation\n### Week04 `__init__`\nOpening.\n### Week09\nMiddle.\n### Week12\nClosing.\n"
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question=question,
        reference_labels=("Week09", "Week12"),
    )
    assert source.text == "### Week04 `__init__`\nOpening.\n"


@pytest.mark.parametrize(
    ("sections", "labels"),
    [
        ("### Week01\nOne.\n### Week02\nTwo.\n### Week02\nDuplicate.\n", ("Week01", "Week02")),
        ("## First\n### Week01\nOne.\n## Second\n### Week02\nTwo.\n", ("Week01", "Week02")),
        ("### Week01\nOne.\n### Week02\nTwo.\n", ("Week01", "Week03")),
        ("### Week01\nOne.\n### Month02\nTwo.\n", ("Week01", "Month02")),
        ("### Week01\nOne.\n### Week02\nTwo.\n", ("Week01", "Week02", "Week03", "Week04")),
    ],
)
def test_ambiguous_missing_or_invalid_label_scopes_refuse_without_ordinal_or_focus_fallback(
    sections: str, labels: tuple[str, ...]
) -> None:
    source = read_research_document(
        project_corpus(("ROADMAP.md", "# Programme\n" + sections)),
        "doc:ROADMAP.md",
        question="Compare second and third weeks from your answer",
        focus="Read Week01",
        reference_labels=labels,
    )
    assert (source.status, source.reason, source.text) == ("refused", "research_document_context", "")


def test_repeated_source_labels_need_a_unique_explicit_parent_branch() -> None:
    first = "## Formation\n### Week01\nFormation one.\n### Week02\nFormation two.\n"
    second = "## Practice\n### Week01\nPractice one.\n### Week02\nPractice two.\n"
    text = "# Programme\n" + first + second
    corpus = project_corpus(("ROADMAP.md", text))
    ambiguous = read_research_document(
        corpus,
        "doc:ROADMAP.md",
        question="Compare second and third weeks from your answer",
        reference_labels=("Week01", "Week02"),
    )
    assert ambiguous.status == "refused"
    scoped = read_research_document(
        corpus,
        "doc:ROADMAP.md",
        question="Compare second and third Formation weeks from your answer",
        reference_labels=("Week01", "Week02"),
    )
    expected = first[first.index("### Week01") :]
    assert scoped.text == expected
    assert scoped.excerpt_start == text.index(expected)
    assert scoped.text_digest == sha256(expected.encode()).hexdigest()


@pytest.mark.parametrize("question", ["Read Week99", "Read Week9999999"])
def test_unmatched_explicit_question_target_cannot_be_replaced_by_anchor_labels(question: str) -> None:
    source = read_research_document(
        project_corpus(("ROADMAP.md", "# Programme\n### Week01\nOne.\n### Week02\nTwo.\n")),
        "doc:ROADMAP.md",
        question=question,
        reference_labels=("Week01", "Week02"),
    )
    assert source.status == "refused"


def test_anchor_ordinal_word_cannot_disambiguate_a_same_named_source_parent() -> None:
    request = anchored_request(
        "1. Week00\n2. Week01\n3. Week02\n4. Week09\n5. Week12\n",
        "Compare fourth and fifth weeks from your answer.",
    )
    labels = reference_selectors(request)
    assert labels == ("Week09", "Week12")
    text = (
        "# Programme\n## Fourth\n### Week09\nFirst nine.\n### Week12\nFirst twelve.\n"
        "## Other\n### Week09\nOther nine.\n### Week12\nOther twelve.\n"
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question=request.event.question,
        reference_labels=labels,
    )
    assert (source.status, source.reason, source.text) == ("refused", "research_document_context", "")


@pytest.mark.parametrize("verb", ["give", "show", "explain"])
@pytest.mark.parametrize("focus", ["Read #formation", "Formation overview"])
def test_resolved_focus_precedes_a_weak_incidental_instruction_heading(verb: str, focus: str) -> None:
    text = (
        f"# Programme\n## {verb.title()} the instrument a body\nUnrelated construction.\n"
        "## Formation {#formation}\n### Stage01\nQuote one.\n### Stage02\nQuote two.\n"
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question=f"Please {verb} just methods and full quotes and purpose",
        focus=focus,
    )
    assert source.text == text[text.index("## Formation") :]
    assert "Unrelated construction" not in source.text


@pytest.mark.parametrize("question", ["Give the instrument a body", "Read #body", "Read Stage01", "Read `method_one`"])
def test_explicit_current_targets_and_whole_heading_keep_precedence_over_focus(question: str) -> None:
    text = (
        "# Programme\n## Give the instrument a body {#body}\nAuthored construction.\n"
        "### Stage01 `method_one`\nFirst method.\n## Formation\nOther material.\n"
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question=question, focus="Formation overview"
    )
    assert "Authored construction" in source.text or "First method" in source.text
    assert "Other material" not in source.text


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("give genesis in weeks and quotes and methods and what to do", "complete_quotes"),
        ("Please give just methods and full quotes and purpose whybdidnuntrim it xD", "complete_quotes"),
        ("Include every quotation and explain its meaning.", "complete_quotes"),
        ("Summarize the methods and include quotes.", "complete_quotes"),
        ("Do not shorten the quotations.", "complete_quotes"),
        ("Don't trim quotes.", "complete_quotes"),
        ("Don\N{RIGHT SINGLE QUOTATION MARK}t trim quotes; give them in full.", "complete_quotes"),
        ("No quote fragments; give full quotations.", "complete_quotes"),
        ("Please shorten the quotations.", "balanced"),
        ("Summarise quotes and explain the methods.", "balanced"),
        ("Give excerpts of the quotations.", "balanced"),
        ("Give quotation fragments.", "balanced"),
        ("Explain the methods.", "balanced"),
    ],
)
def test_projection_mode_comes_from_requested_quotation_operation(question: str, expected: str) -> None:
    assert research_projection_mode(question) == expected


def test_complete_quote_mode_keeps_all_uneven_multiline_units_at_a_fixed_shared_budget() -> None:
    quotes = [
        f"> QUOTE_{number:02}: "
        + f"authored-word-{number} " * (3 + number % 4)
        + ".\n"
        + (
            f">\n> SECOND_{number:02}: This entire additional paragraph also belongs to the quotation.\n"
            if number in {3, 5, 6, 8}
            else ""
        )
        for number in range(10)
    ]
    text = "# Programme\n## Formation\nAn authored introduction.\n### Context\nOptional orientation.\n" + "".join(
        f"### Stage{number:02} · `method_{number}`\n**Dates:** period {number}.\n\n"
        + quote
        + f"> — Author{number:02}, [Reference{number:02}](https://example.com/"
        + "long-destination/" * 20
        + f")\n\nPURPOSE_{number:02}: Practise this distinct skill. More supporting detail follows.\n\n"
        + "Further authored background. " * 20
        + "\n\n"
        for number, quote in enumerate(quotes)
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Formation overview"
    )
    assert source.text == text[text.index("## Formation") :]
    projection = project_research_source(source, 4270, projection_mode="complete_quotes")
    rendered = cast("str", projection["text"])
    spans = cast("list[dict[str, int]]", projection["projection_spans"])
    assert len(rendered) <= 4270
    assert len(spans) <= 48
    for number, quote in enumerate(quotes):
        assert quote in rendered
        assert f"`method_{number}`" in rendered
        assert f"> — Author{number:02}, [Reference{number:02}]" in rendered
        assert f"PURPOSE_{number:02}: Practise this distinct skill." in rendered
    assert "long-destination/" not in rendered
    assert rendered == render_research_projection(source.text, spans)
    assert projection["projection_digest"] == sha256(rendered.encode()).hexdigest()
    assert projection["text_digest"] == source.text_digest
    assert projection["projection_mode"] == "complete_quotes"
    assert projection == project_research_source(source, 4270, projection_mode="complete_quotes")


def test_compact_omissions_keep_every_first_purpose_with_unequal_paragraphs_at_a_tight_budget() -> None:
    quotes = [
        f"> QUOTE_{number:02}: "
        + f"authored-word-{number} " * (9 + number % 4)
        + ".\n"
        + (
            f">\n> SECOND_{number:02}: This entire additional paragraph also belongs to the quotation.\n"
            if number in {3, 5, 6, 8}
            else ""
        )
        for number in range(10)
    ]
    purposes = [
        f"PURPOSE_{number:02}: Practise this distinct skill and observe its documented outcome." for number in range(10)
    ]
    section = "## Formation\nAn authored introduction.\n" + "".join(
        f"### Stage{number:02} · `method_{number}`\n\n**Dates:** period {number}.\n\n"
        + quote
        + f"> — Author{number:02}, [Reference{number:02}](https://example.com/"
        + "long-destination/" * 20
        + f")\n\n{purpose} "
        + (
            "Brief additional context."
            if number == 1
            else "This longer additional explanation gives supporting detail. " * (1 + number % 3)
        )
        + "\n\n"
        + "Further authored background. " * 20
        + "\n\n"
        for number, (quote, purpose) in enumerate(zip(quotes, purposes, strict=True))
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", "# Programme\n" + section)),
        "doc:ROADMAP.md",
        question="Give Formation stage quotes and purposes.",
    )
    assert source.text == section
    projection = project_research_source(source, 3737, projection_mode="complete_quotes")
    rendered = cast("str", projection["text"])
    spans = cast("list[dict[str, int]]", projection["projection_spans"])
    assert len(rendered) <= 3737
    assert len(spans) <= 48
    for number, (quote, purpose) in enumerate(zip(quotes, purposes, strict=True)):
        assert quote in rendered
        assert f"`method_{number}`" in rendered
        assert f"> — Author{number:02}, [Reference{number:02}]" in rendered
        assert purpose in rendered
    assert "long-destination/" not in rendered
    assert RESEARCH_PROJECTION_OMISSION in rendered
    assert rendered == render_research_projection(source.text, spans)
    assert projection["projection_digest"] == sha256(rendered.encode()).hexdigest()
    assert projection["source_digest"] == source.source_digest
    assert projection["text_digest"] == source.text_digest
    assert projection["projection_budget"] == 3737
    assert projection["projection_mode"] == "complete_quotes"
    assert projection["projection_truncated"]
    assert projection == project_research_source(source, 3737, projection_mode="complete_quotes")


@pytest.mark.parametrize("length", [0, 20, 80, 200, 400])
def test_complete_quote_mode_omits_unfitting_units_instead_of_clipping_them(length: int) -> None:
    quotations = [
        f"> QUOTE_{number}: " + "The whole authored sentence remains exact. " * number + "\n" for number in (1, 3, 5)
    ]
    text = "# Programme\n" + "".join(
        f"## Stage{number}\n" + quote + f"> — Author{number}\n\nMeaning {number}.\n\n"
        for number, quote in enumerate(quotations, 1)
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Programme overview"
    )
    projection = project_research_source(source, length, projection_mode="complete_quotes")
    rendered = cast("str", projection["text"])
    spans = cast("list[dict[str, int]]", projection["projection_spans"])
    assert len(rendered) <= length
    assert len(spans) <= 48
    assert rendered == render_research_projection(source.text, spans)
    for quote in quotations:
        marker = quote.partition(":")[0]
        assert marker not in rendered or quote in rendered
    assert projection["projection_mode"] == "complete_quotes"


def test_complete_quote_mode_ignores_fenced_decoys_and_keeps_multiple_blocks_in_one_section() -> None:
    text = (
        "# Programme\n## Method\n```md\n> FENCED_DECOY\n```\n"
        "> First complete quotation.\n> — First author\n\nFirst purpose.\n\n"
        "> Second complete quotation.\n>\n> Its second paragraph.\n"
        "> — Second author, [Work](https://example.com/work), translated by Witness\n\nSecond purpose.\n\n"
        + "Unrelated background. "
        * 100
    )
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Method")
    projection = project_research_source(source, 400, projection_mode="complete_quotes")
    rendered = cast("str", projection["text"])
    assert "> First complete quotation.\n" in rendered
    assert "> Second complete quotation.\n>\n> Its second paragraph.\n" in rendered
    assert "> — Second author, [Work]" in rendered
    assert ", translated by Witness" in rendered
    assert "FENCED_DECOY" not in rendered
    with pytest.raises(ValueError, match="research_projection_mode"):
        project_research_source(source, 400, projection_mode=cast("Literal['balanced']", "invented"))


@pytest.mark.parametrize("extra_budget", [0, 200])
def test_complete_quote_mode_does_not_expose_a_truncated_acquisition_quote_with_ample_budget(extra_budget: int) -> None:
    text = "# Method\n> CLIPPED_QUOTATION begins here and continues outside the excerpt"
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Method")
    truncated = source.model_copy(update={"truncated": True, "source_chars": source.source_chars + 100})
    projection = project_research_source(truncated, len(source.text) + extra_budget, projection_mode="complete_quotes")
    assert "CLIPPED_QUOTATION" not in cast("str", projection["text"])
    assert RESEARCH_PROJECTION_OMISSION in cast("str", projection["text"])
    complete = project_research_source(source, len(source.text) + extra_budget, projection_mode="complete_quotes")
    assert complete["text"] == source.text


@pytest.mark.parametrize(
    "title", ["Genesis · 00\u201309 — Formation", "Genesis (00\u201309): Formation", "Genesis | Formation"]
)
def test_authored_decorated_parent_name_precedes_a_stale_explicit_focus(title: str) -> None:
    section = f"## {title}\nFormation purpose.\n### Week00\nOpening.\n### Week01\nFollowing.\n"
    text = "# Programme\n" + section + "## Exodus · 10\u201317 {#exodus-10-17}\nLater material.\n"
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)),
        "doc:ROADMAP.md",
        question="Explain Genesis per week",
        focus="Read #exodus-10-17",
    )
    assert source.text == section
    assert "Later material" not in source.text


@pytest.mark.parametrize("length", [40, 400])
def test_complete_quote_mode_omits_an_acquisition_starting_inside_a_quote(length: int) -> None:
    text = "# Method\n> Original opening.\n> RETAINED_LAST_PARAGRAPH\n> — Author\n\nMeaning.\n"
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Method")
    start = text.index("> RETAINED")
    excerpt = text[start:]
    clipped = source.model_copy(
        update={
            "text": excerpt,
            "text_digest": sha256(excerpt.encode()).hexdigest(),
            "excerpt_start": start,
            "truncated": True,
        }
    )
    projection = project_research_source(clipped, length, projection_mode="complete_quotes")
    assert "RETAINED_LAST_PARAGRAPH" not in cast("str", projection["text"])
    assert len(cast("str", projection["text"])) <= length


def test_complete_quote_mode_retains_a_final_section_quote_at_the_observed_source_eof() -> None:
    text = "# Programme\n## Earlier\nBackground.\n## Final\n> Complete final quotation.\n> — Final author\n"
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Final")
    assert source.excerpt_start > 0
    assert source.truncated
    assert source.excerpt_start + len(source.text) == source.source_chars
    projection = project_research_source(source, len(source.text) + 100, projection_mode="complete_quotes")
    assert projection["text"] == source.text


def test_complete_quote_mode_never_reintroduces_a_parent_quote_as_a_clipped_preamble() -> None:
    text = (
        "# Programme\n## Formation\n> PARENT_QUOTE "
        + "Long authored parent quotation. " * 50
        + "\n> — Parent author\n\nParent meaning.\n"
        "### Stage01\n> Complete child quotation.\n> — Child author\n\nChild purpose.\n"
        "### Stage02\n> Another complete child quotation.\n> — Another author\n\nAnother purpose.\n"
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Formation overview"
    )
    projection = project_research_source(source, 400, projection_mode="complete_quotes")
    rendered = cast("str", projection["text"])
    assert "PARENT_QUOTE" not in rendered
    assert "> Complete child quotation.\n" in rendered
    assert "> Another complete child quotation.\n" in rendered
    assert len(rendered) <= 400


@pytest.mark.parametrize("truncated", [False, True])
def test_complete_quote_mode_keeps_lazy_paragraph_continuation_atomic(*, truncated: bool) -> None:
    quote = "> QUOTE_OPENING\n" + "continued authored quotation words " * 15 + "\n"
    text = "# Method\n" + quote + ("" if truncated else "\nMeaning.\n")
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Method")
    if truncated:
        source = source.model_copy(update={"source_chars": source.source_chars + 100, "truncated": True})
    for length in (80, len(source.text) + 200):
        rendered = cast("str", project_research_source(source, length, projection_mode="complete_quotes")["text"])
        assert "QUOTE_OPENING" not in rendered or quote in rendered
        if truncated:
            assert "QUOTE_OPENING" not in rendered
        assert len(rendered) <= length


def test_complete_quote_mode_keeps_a_long_authorship_label_when_the_whole_unit_fits() -> None:
    authorship = "> — " + "Authored identity and work label " * 6
    text = (
        "# Method\n> Complete short quotation.\n"
        + authorship
        + "[Reference](https://example.com/work), translated by Witness\n\nPurpose.\n\n"
        + "Unrelated background. " * 100
    )
    source = read_research_document(project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Method")
    projection = project_research_source(source, 1000, projection_mode="complete_quotes")
    rendered = cast("str", projection["text"])
    assert len(authorship) > 120
    assert "> Complete short quotation.\n" in rendered
    assert authorship + "[Reference]" in rendered
    assert ", translated by Witness" in rendered
    assert len(rendered) <= 1000


def test_complete_quote_mode_packs_a_short_parent_quotation_with_child_quotations() -> None:
    text = (
        "# Programme\n## Formation\n> Complete parent quotation.\n> — Parent author\n\nParent purpose.\n\n"
        "### Stage01\n> Complete child quotation.\n> — Child author\n\nChild purpose.\n\n"
        + "Unrelated background. "
        * 100
    )
    source = read_research_document(
        project_corpus(("ROADMAP.md", text)), "doc:ROADMAP.md", question="Formation overview"
    )
    projection = project_research_source(source, 400, projection_mode="complete_quotes")
    rendered = cast("str", projection["text"])
    assert "> Complete parent quotation.\n> — Parent author" in rendered
    assert "> Complete child quotation.\n> — Child author" in rendered
    assert len(rendered) <= 400


@pytest.mark.parametrize("question", ["Give quotes from Archive.", "Give the full quotations from Archive."])
def test_quotation_request_acquires_its_selected_markdown_scope_without_an_overview_word(question: str) -> None:
    text = "# Archive\n\n" + "\n\n".join(
        f"## Part {number}\n> Complete quotation {number}.\n> — Author {number}\n\n" + "Supporting narrative. " * 100
        for number in range(4)
    )
    corpus = project_corpus(("docs/archive.md", text))
    source = read_research_document(corpus, "doc:docs/archive.md", question=question)
    assert 4000 < len(text) < 16_000
    assert source.text == text
    assert not source.truncated
    assert source.excerpt_start == 0
    assert source.text_digest == sha256(text.encode()).hexdigest()
    for balanced_question in ("Explain Archive.", "Summarize the quotations from Archive."):
        balanced = read_research_document(corpus, "doc:docs/archive.md", question=balanced_question)
        assert balanced.text == text[:4000]
        assert balanced.truncated


def test_quotation_scope_acquisition_keeps_the_existing_document_and_code_limits() -> None:
    text = "# Archive\n" + "## Part\n> Authored quotation.\n\nSupporting narrative.\n" * 400
    corpus = project_corpus(("docs/archive.md", text), ("src/archive.py", text))
    source = read_research_document(corpus, "doc:docs/archive.md", question="Give quotes from Archive.")
    assert source.text == text[:16_000]
    assert source.truncated
    assert source.source_chars == len(text)
    code = read_research_document(corpus, "doc:src/archive.py", question="Give quotes from src/archive.py.")
    assert len(code.text) == 4000
    assert code.text == text[code.excerpt_start : code.excerpt_start + 4000]


@pytest.mark.parametrize("unit", ["Week", "Chapter", "Interval"])
def test_structural_catalogue_routes_a_named_unit_overview_to_its_actual_container(unit: str) -> None:
    topic = "# Aurora\nAurora methods and quotations explain the idea, without a schedule.\n"
    structure = "# Metamorphosis\n## Aurora · 00\u201309 — Formation\nThe authored scope.\n" + "".join(
        f'<a id="{unit.lower()}-{number:02}"></a>\n### {number:02} · `method_{number}`\n'
        "PRIVATE_BODY_MARKER must never enter catalogue metadata.\n"
        for number in (0, 2, 9)
    )
    corpus = project_corpus(
        ("docs/aurora.md", topic),
        *((f"docs/distractor-{number:02}.md", topic) for number in range(20)),
        ("docs/programme.md", structure),
    )
    question = f"Give Aurora in {unit.lower()}s and quotes and methods and what to do."
    catalogue = research_document_catalogue(corpus, question=question)
    assert len(catalogue) == MAX_RESEARCH_CATALOGUE_DOCUMENTS
    assert catalogue[0]["id"] == "doc:docs/programme.md"
    assert catalogue[0]["title"] == "Metamorphosis"
    descriptor = catalogue[0]["section_match"]
    assert len(descriptor) <= MAX_RESEARCH_SECTION_MATCH_CHARS
    assert "Aurora · 00\u201309 — Formation" in descriptor
    assert "matching sections: 3" in descriptor
    assert "examples (sample)" in descriptor
    for number in (0, 2, 9):
        assert f"`method_{number}`" in descriptor
        assert f"#{unit.lower()}-{number:02}" in descriptor
    assert "PRIVATE_BODY_MARKER" not in str(catalogue)
    assert all(set(item) <= {"id", "title", "url", "section_match"} for item in catalogue)
    assert "section_match" not in next(item for item in catalogue if item["id"] == "doc:docs/aurora.md")
    for exact in ("docs/aurora.md", corpus.manifest.documents[0].url):
        selected = research_document_catalogue(corpus, question=f"{question} in {exact}")
        assert selected[0]["id"] == "doc:docs/aurora.md"


@pytest.mark.parametrize(
    "structure",
    [
        "## Aurora\n### Month01\nUnrelated unit kind.\n### Month02\nLater.\n",
        "## Other\nAurora is described elsewhere.\n### Week01\nWrong parent.\n### Week02\nLater.\n",
        "## Aurora\nA named topic without numbered units.\n",
        "## Aurora\n### Week01\nFirst.\n### Week01\nDuplicate label.\n",
        '## Aurora\n<a id="week-02"></a>\n### Week01\nConflicting authored unit.\n',
        "## Aurora\n### First branch\n#### Week01\nFirst.\n### Second branch\n#### Week02\nSecond.\n",
        "## Aurora\n### Week01\nFirst.\n## Aurora\n### Week02\nSecond.\n",
    ],
)
def test_structural_catalogue_does_not_invent_a_match_for_wrong_or_ambiguous_scopes(structure: str) -> None:
    corpus = project_corpus(("docs/programme.md", "# Programme\n" + structure))
    catalogue = research_document_catalogue(corpus, question="Give Aurora in weeks and quotes.")
    assert catalogue
    assert all("section_match" not in item for item in catalogue)


def test_structural_catalogue_ignores_fenced_frontmatter_and_navigation_decoys() -> None:
    text = (
        "---\n## Aurora\n### Week01\n---\n# Programme\n"
        "```md\n## Aurora\n### Week01\n```\n"
        "## Aurora\n- [Week01](#week01)\n### Week01\n- [Other](#other)\n"
    )
    catalogue = research_document_catalogue(
        project_corpus(("docs/programme.md", text)), question="Give Aurora in weeks."
    )
    assert catalogue
    assert "section_match" not in catalogue[0]


def test_structural_catalogue_keeps_explicit_numeric_targets_before_an_overview_boost() -> None:
    corpus = project_corpus(
        ("docs/named.md", "# Programme\n## Aurora\n### Week00\nFirst.\n### Week01\nSecond.\n"),
        ("docs/target.md", "# Evidence\n### Week09\nThe literal current target.\n"),
    )
    catalogue = research_document_catalogue(corpus, question="Explain Aurora weeks and Week09 quotations.")
    assert catalogue[0]["id"] == "doc:docs/target.md"


def test_structural_catalogue_bounds_sampled_heading_metadata_and_preserves_legacy_descriptors() -> None:
    label = "An authored label " * 10
    text = "# Programme\n## Aurora\nThe scope.\n" + "".join(
        f'<a id="week-{number:02}"></a>\n### {number:02} {label}\nBody must not appear in metadata.\n'
        for number in range(30)
    )
    corpus = project_corpus(("docs/programme.md", text))
    descriptor = research_document_catalogue(corpus, question="Aurora weeks")[0]["section_match"]
    assert len(descriptor) <= MAX_RESEARCH_SECTION_MATCH_CHARS
    assert "matching sections: 30" in descriptor
    assert "Body must not appear" not in descriptor
    assert set(research_document_catalogue(corpus)[0]) == {"id", "title", "url"}


def test_structural_catalogue_omits_an_oversized_authored_parent_without_boosting_it() -> None:
    long_parent = "Aurora | " + "An authored parent qualification " * 20
    assert len(long_parent) > MAX_RESEARCH_SECTION_MATCH_CHARS
    long_source = f"# Programme\n## {long_parent}\nThe scope.\n### Week00\nFirst.\n### Week01\nSecond.\n"
    corpus = project_corpus(
        ("docs/oversized.md", long_source),
        ("docs/normal.md", "# Programme\n## Aurora\nThe scope.\n### Week00\nFirst.\n"),
    )
    catalogue = research_document_catalogue(corpus, question="Aurora weeks")
    assert catalogue[0]["id"] == "doc:docs/normal.md"
    oversized = next(item for item in catalogue if item["id"] == "doc:docs/oversized.md")
    assert "section_match" not in oversized
    assert all(len(item.get("section_match", "")) <= MAX_RESEARCH_SECTION_MATCH_CHARS for item in catalogue)


def test_structural_catalogue_counts_nested_substantive_units_from_the_programme_fixture() -> None:
    corpus = project_corpus(
        ("docs/genesis.md", "# Genesis\nThe idea and its methods and quotations.\n"),
        ("docs/programme.md", "# Programme\n" + programme_sections()),
    )
    catalogue = research_document_catalogue(corpus, question="Explain Genesis per week with methods and quotes.")
    assert catalogue[0]["id"] == "doc:docs/programme.md"
    descriptor = catalogue[0]["section_match"]
    assert "matching sections: 10" in descriptor
    for week in (0, 5, 9):
        assert f"Week {week:02}" in descriptor
    assert "Methods and quotes" not in descriptor
    assert "Method 0; quotation 0." not in descriptor


def test_structural_catalogue_keeps_ambiguity_between_distinct_named_unit_parents() -> None:
    text = (
        "# Programme\n## Aurora\nThe first scope.\n### Week01\nFirst substantive method.\n"
        "## Methods and quotes\nThe second scope.\n### Week02\nAnother substantive method.\n"
    )
    catalogue = research_document_catalogue(
        project_corpus(("docs/programme.md", text)), question="Explain Aurora per week with methods and quotes."
    )
    assert catalogue
    assert "section_match" not in catalogue[0]


@pytest.mark.parametrize("marker", ["-", "1."])
@pytest.mark.parametrize("nested", [False, True])
def test_structural_catalogue_does_not_count_link_only_children_under_a_substantive_parent(
    marker: str, *, nested: bool
) -> None:
    directory_child = "### Reading\n" if nested else ""
    mixed_child = "#### Reading\n" if nested else ""
    directory = (
        "# Aurora\nWeekly directory with an explanatory introduction.\n"
        f"## Week00\n{directory_child}{marker} [Read the first unit](week00.md)\n"
        f"## Week01\n{directory_child}{marker} [Read the next unit](week01.md)\n"
    )
    content = "# Metamorphosis\n## Aurora\nThe authored schedule.\n### Week00\nThe method and its purpose.\n"
    mixed = (
        "# Programme\n## Aurora\nThe authored schedule.\n"
        f"### Week00\n{mixed_child}{marker} [Read another document](other.md)\n"
        "### Week01\nA substantive method and its purpose.\n"
    )
    corpus = project_corpus(("docs/aurora.md", directory), ("docs/content.md", content), ("docs/mixed.md", mixed))
    catalogue = research_document_catalogue(corpus, question="Aurora weeks")
    assert catalogue[0]["id"] != "doc:docs/aurora.md"
    by_id = {item["id"]: item for item in catalogue}
    assert "section_match" not in by_id["doc:docs/aurora.md"]
    assert "matching sections: 1" in by_id["doc:docs/content.md"]["section_match"]
    mixed_hint = by_id["doc:docs/mixed.md"]["section_match"]
    assert "matching sections: 1" in mixed_hint
    assert "Week01" in mixed_hint
    assert "Week00" not in mixed_hint
