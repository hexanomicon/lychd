"""Pinned project text remains bounded knowledge, with offered-ID and source-byte custody."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

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
