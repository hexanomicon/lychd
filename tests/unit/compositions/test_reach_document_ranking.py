"""Versioned lexical ranking preserves source fencing and stronger authored selections."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from math import isfinite
from typing import Literal, cast

import pytest

from lychd.compositions.reach.documents import (
    CorpusDocument,
    CorpusManifest,
    PublicCorpus,
    _research_normalized_scores,  # pyright: ignore[reportPrivateUsage] - inspect authored-title credit directly
    research_document_catalogue,
    retrieval_terms,
    verify_corpus,
)

_REVISION = "a" * 40


def _corpus(*documents: tuple[str, str]) -> PublicCorpus:
    contents = tuple(text.encode() for _, text in documents)
    manifest = CorpusManifest(
        schema_version=2,
        source_revision=_REVISION,
        documents=tuple(
            CorpusDocument(
                path=path,
                url=f"https://github.com/hexanomicon/lychd/blob/{_REVISION}/{path}",
                sha256=sha256(raw).hexdigest(),
                file=f"{index:04}.txt",
            )
            for index, ((path, _), raw) in enumerate(zip(documents, contents, strict=True))
        ),
    )
    return verify_corpus(manifest, contents)


def _ids(catalogue: tuple[dict[str, str], ...]) -> tuple[str, ...]:
    return tuple(item["id"] for item in catalogue)


def test_default_version_preserves_original_fallback_path_scoring() -> None:
    corpus = _corpus(
        ("docs/guide.md", "# Field guide\nfirst run instructions"),
        ("src/lychd/first_run.py", "opaque material"),
    )
    original = research_document_catalogue(corpus, question="first run", ranking_version=1)
    assert _ids(original) == ("doc:src/lychd/first_run.py", "doc:docs/guide.md")
    assert research_document_catalogue(corpus, question="first run") == original
    assert original[0]["title"] == "src/lychd/first_run.py"


def test_version_two_prefers_rare_topic_over_repeated_common_generated_noise() -> None:
    corpus = _corpus(
        ("src/lychd/first_run.py", "first run ordinary " * 4000),
        ("docs/instrument.md", "# Instrument\nquasar calibration"),
        *((f"docs/background-{index}.md", "# Background\nfirst run ordinary") for index in range(8)),
    )
    question = "first run quasar calibration"
    assert research_document_catalogue(corpus, question=question, ranking_version=1)[0]["id"] == (
        "doc:src/lychd/first_run.py"
    )
    assert research_document_catalogue(corpus, question=question, ranking_version=2)[0]["id"] == (
        "doc:docs/instrument.md"
    )


def test_length_normalization_distinguishes_equal_topic_counts() -> None:
    corpus = _corpus(
        ("docs/a-long.md", "# Manual\nquasar " + "unrelated " * 4000),
        ("docs/z-short.md", "# Manual\nquasar"),
    )
    assert _ids(research_document_catalogue(corpus, question="quasar", ranking_version=1)) == (
        "doc:docs/a-long.md",
        "doc:docs/z-short.md",
    )
    assert _ids(research_document_catalogue(corpus, question="quasar", ranking_version=2)) == (
        "doc:docs/z-short.md",
        "doc:docs/a-long.md",
    )


def test_genuine_heading_equal_to_fallback_label_keeps_independent_title_credit() -> None:
    plain = _corpus(("docs/anchor.md", "docs/anchor.md\n"))
    headed = _corpus(("docs/anchor.md", "# docs/anchor.md\n"))
    query = retrieval_terms("anchor")
    assert research_document_catalogue(plain)[0]["title"] == research_document_catalogue(headed)[0]["title"]
    assert (
        _research_normalized_scores(headed, query, frozenset())[0]
        > _research_normalized_scores(plain, query, frozenset())[0]
    )


def test_plain_source_label_does_not_receive_authored_title_credit() -> None:
    corpus = _corpus(
        ("docs/anchor.md", "# Calibration\nopaque"),
        ("docs/anchor.txt", "# Calibration\nopaque"),
    )
    # Equal body counts and path terms for the query; only Markdown has an authored title.
    assert _ids(research_document_catalogue(corpus, question="calibration", ranking_version=2)) == (
        "doc:docs/anchor.md",
        "doc:docs/anchor.txt",
    )
    assert research_document_catalogue(corpus, question="calibration", ranking_version=2)[1]["title"] == (
        "docs/anchor.txt"
    )


def test_version_two_uses_existing_unicode_term_normalization() -> None:
    corpus = _corpus(("docs/a.md", "# Manual\nCafé mémoire"), ("docs/b.md", "# Manual\nUnrelated text"))
    assert _ids(research_document_catalogue(corpus, question="CAFE MEMOIRE", ranking_version=2)) == ("doc:docs/a.md",)


def test_current_terms_do_not_gain_duplicate_weight_from_history() -> None:
    corpus = _corpus(("docs/a.md", "# Manual\nquasar"), ("docs/b.md", "# Manual\nUnrelated text"))
    terms = retrieval_terms("quasar")
    current = _research_normalized_scores(corpus, terms, frozenset())
    assert _research_normalized_scores(corpus, terms, terms) == current
    historical = _research_normalized_scores(corpus, frozenset(), terms)
    assert historical == pytest.approx(tuple(score * 0.25 for score in current))


@pytest.mark.parametrize("version", [1, 2])
def test_current_exact_code_source_dominates_context_and_lexical_matches(version: Literal[1, 2]) -> None:
    corpus = _corpus(
        ("docs/context.md", "# Quasar calibration\nquasar calibration " * 20),
        ("src/lychd/target.py", "opaque material"),
        ("docs/other.md", "# Quasar\ncalibration"),
    )
    offered = research_document_catalogue(
        corpus,
        question="quasar calibration in src/lychd/target.py",
        context=("docs/context.md",),
        ranking_version=version,
    )
    assert _ids(offered)[:2] == ("doc:src/lychd/target.py", "doc:docs/context.md")
    pinned = research_document_catalogue(
        corpus,
        question=f"quasar calibration {corpus.manifest.documents[1].url}#symbol",
        ranking_version=version,
    )
    assert pinned[0]["id"] == "doc:src/lychd/target.py"


@pytest.mark.parametrize("version", [1, 2])
def test_numbered_target_precedes_incidental_topic_words(version: Literal[1, 2]) -> None:
    corpus = _corpus(
        ("docs/a-noise.md", "# Quasar calibration\nquasar calibration " * 30),
        ("docs/z-units.md", "# Manual\n## Week 42\nA bounded unit.\n## Week 43\nAnother unit."),
    )
    offered = research_document_catalogue(
        corpus, question="Explain Week 42 quasar calibration", ranking_version=version
    )
    assert offered[0]["id"] == "doc:docs/z-units.md"


@pytest.mark.parametrize("version", [1, 2])
def test_named_sibling_structure_retains_its_priority_and_descriptor(version: Literal[1, 2]) -> None:
    corpus = _corpus(
        ("docs/a-noise.md", "# Aurora weeks\nAurora weeks " * 30),
        (
            "docs/z-units.md",
            "# Manual\n## Aurora\nAn introduction.\n### Week 00\nFirst unit.\n### Week 01\nSecond unit.\n",
        ),
    )
    offered = research_document_catalogue(corpus, question="Explain Aurora weeks", ranking_version=version)
    assert offered[0]["id"] == "doc:docs/z-units.md"
    assert "matching sections: 2" in offered[0]["section_match"]
    assert set(offered[0]) == {"id", "title", "url", "section_match"}


@pytest.mark.parametrize("version", [1, 2])
def test_existing_kickoff_route_still_precedes_lexical_noise(version: Literal[1, 2]) -> None:
    corpus = _corpus(
        ("docs/a-noise.md", "# First project\nkick off first project " * 20),
        ("docs/roadmap.md", "# Schedule\nAn ordered introduction."),
    )
    assert research_document_catalogue(corpus, question="Can you kick us off?", ranking_version=version)[0]["id"] == (
        "doc:docs/roadmap.md"
    )


@pytest.mark.parametrize("version", [1, 2])
def test_no_query_preserves_authored_order_and_query_ties_use_paths(version: Literal[1, 2]) -> None:
    corpus = _corpus(
        ("docs/z.md", "# Manual\nalpha beta gamma"),
        ("docs/a.md", "# Manual\nalpha beta gamma"),
    )
    assert _ids(research_document_catalogue(corpus, ranking_version=version)) == ("doc:docs/z.md", "doc:docs/a.md")
    expected = ("doc:docs/a.md", "doc:docs/z.md")
    first = research_document_catalogue(corpus, question="gamma alpha beta", ranking_version=version)
    assert _ids(first) == expected
    assert research_document_catalogue(corpus, question="beta gamma alpha", ranking_version=version) == first
    assert research_document_catalogue(corpus, question="gamma alpha beta", ranking_version=version) == first


def test_zero_token_and_empty_internal_corpus_have_finite_ranking() -> None:
    corpus = _corpus(("docs/empty.md", ""), ("docs/stop.md", "the and of"))
    scores = _research_normalized_scores(corpus, retrieval_terms("empty absent"), frozenset())
    assert len(scores) == 2
    assert all(isfinite(score) for score in scores)
    assert research_document_catalogue(corpus, question="absent", ranking_version=2) == ()
    assert research_document_catalogue(corpus, question="docs/empty.md", ranking_version=2)[0]["id"] == (
        "doc:docs/empty.md"
    )
    # Public admission forbids an empty manifest; internal scoring still handles it defensively.
    empty = replace(corpus, manifest=corpus.manifest.model_copy(update={"documents": ()}), texts=())
    assert research_document_catalogue(empty, question="absent", ranking_version=2) == ()


@pytest.mark.parametrize("version", [1, 2])
def test_catalogue_limit_and_ids_remain_manifest_bound(version: Literal[1, 2]) -> None:
    corpus = _corpus(
        *(
            (f"docs/item-{index:02}.md", "# Instrument\nquasar docs/foreign.md https://foreign.example/read")
            for index in range(22)
        )
    )
    offered = research_document_catalogue(
        corpus, question="quasar docs/foreign.md https://foreign.example/read", ranking_version=version
    )
    assert len(offered) == 16
    by_id = {f"doc:{document.path}": document for document in corpus.manifest.documents}
    assert len(set(_ids(offered))) == 16
    assert set(_ids(offered)) <= by_id.keys()
    assert all(item["url"] == by_id[item["id"]].url for item in offered)
    assert all(set(item) == {"id", "title", "url"} for item in offered)


@pytest.mark.parametrize("invalid", [0, 3, True, False, 1.0, "2", None])
def test_unknown_or_coerced_ranking_version_refuses(invalid: object) -> None:
    with pytest.raises(ValueError, match=r"^research_ranking_version$"):
        research_document_catalogue(_corpus(("docs/only.md", "# Only")), ranking_version=cast("Literal[1, 2]", invalid))
