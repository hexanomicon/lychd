"""Project knowledge exports only eligible public text from one immutable Git revision."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from scripts import reach_operator as operator
from scripts.reach_worker import load_corpus


def git(root: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    assert executable is not None
    completed = subprocess.run(  # noqa: S603 - closed local Git fixture, no network or project execution
        [executable, *arguments],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return completed.stdout.decode().strip()


def repository(directory: Path, sources: dict[str, bytes]) -> str:
    directory.mkdir()
    for path, raw in sources.items():
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    git(directory, "init", "--quiet")
    git(directory, "add", "--all")
    git(
        directory,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "Public base",
    )
    return git(directory, "rev-parse", "HEAD")


def test_project_export_is_explicit_pinned_and_excludes_ambient_private_and_binary_material(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    revision = repository(
        repo,
        {
            "README.md": b"# Project\nPublic readme.\n",
            "ROADMAP.md": b"# Roadmap\nPublic milestone.\n",
            "pyproject.toml": b'[project]\nname = "public-project"\n',
            "src/lychd/public.py": b"PUBLIC_FACT = True\n",
            "tests/test_public.py": b"assert True\n",
            "scripts/public.py": b"PUBLIC_SCRIPT = True\n",
            "clients/web/src/public.ts": b"export const publicFact = true;\n",
            "examples/reach/public-docs.txt": b"README.md\n",
            ".github/workflows/core.yml": b"name: Public Core\n",
            ".gitignore": b"ignored.py\n",
            ".env": b"SYNTHETIC_PRIVATE_VALUE=never-project-knowledge\n",
            ".agents/workflows/private.md": b"Never admitted.\n",
            "private/dossier.md": b"Never admitted.\n",
            "clients/web/node_modules/example/index.js": b"Never admitted.\n",
            "docs/image.png": b"\x89PNG\r\n\x1a\n",
        },
    )
    (repo / "README.md").write_text("Dirty private working value.\n")
    (repo / "src/lychd/untracked.py").write_text("Untracked private value.\n")
    (repo / "ignored.py").write_text("Ignored private value.\n")
    output = tmp_path / "project"
    assert operator.export_corpus(output, revision, root=repo, project_files=True) == revision
    corpus = load_corpus(output)
    assert corpus.manifest.schema_version == 2
    paths = {document.path for document in corpus.manifest.documents}
    assert paths == {
        "README.md",
        "ROADMAP.md",
        "pyproject.toml",
        "src/lychd/public.py",
        "tests/test_public.py",
        "scripts/public.py",
        "clients/web/src/public.ts",
        "examples/reach/public-docs.txt",
        ".github/workflows/core.yml",
        ".gitignore",
    }
    assert "Public readme." in "\n".join(corpus.texts)
    assert all("private" not in text.casefold() for text in corpus.texts)
    assert all(
        document.url == f"https://github.com/hexanomicon/lychd/blob/{revision}/{document.path}"
        for document in corpus.manifest.documents
    )
    assert all(
        path.is_file() and not path.is_symlink() and path.stat().st_mode & 0o777 == 0o600 for path in output.iterdir()
    )
    assert not (output / ".git").exists()
    legacy_output = tmp_path / "legacy"
    operator.export_corpus(legacy_output, revision, root=repo)
    assert json.loads((legacy_output / "manifest.json").read_bytes())["schema_version"] == 1
    assert [document.path for document in load_corpus(legacy_output).manifest.documents] == ["README.md"]
    parsed = operator.parser().parse_args(
        ["export-corpus", "--output", str(tmp_path / "other"), "--project-files", "--revision", revision]
    )
    assert parsed.project_files
    assert not operator.parser().parse_args(["export-corpus", "--output", str(tmp_path / "other")]).project_files


def test_project_export_records_oversize_and_invalid_text_omissions_without_losing_other_sources(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    revision = repository(
        repo,
        {
            "README.md": b"Public source.\n",
            "uv.lock": b"x" * (operator.DOCUMENT_LIMIT + 1),
            "src/binary.py": b"before\x00after",
        },
    )
    output = tmp_path / "export"
    operator.export_corpus(output, revision, root=repo, project_files=True)
    corpus = load_corpus(output)
    assert [document.path for document in corpus.manifest.documents] == ["README.md"]
    assert [(item.path, item.reason) for item in corpus.manifest.omissions] == [
        ("src/binary.py", "not_text"),
        ("uv.lock", "document_limit"),
    ]
    assert len(list(output.iterdir())) == 2


@pytest.mark.parametrize("project_files", [True, False])
def test_git_mode_refuses_tracked_symlinks_even_when_target_is_public_and_dirty_link_is_absent(
    tmp_path: Path, *, project_files: bool
) -> None:
    repo = tmp_path / "repo"
    repository(repo, {"README.md": b"Public source.", "examples/reach/public-docs.txt": b"docs/link.md\n"})
    (repo / "docs").mkdir()
    link = repo / "docs/link.md"
    link.symlink_to("../README.md")
    git(repo, "add", "docs/link.md")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "Link")
    revision = git(repo, "rev-parse", "HEAD")
    link.unlink()
    link.write_text("A dirty regular replacement cannot alter the pinned Git mode.")
    with pytest.raises(ValueError, match="corpus_git_mode"):
        operator.export_corpus(tmp_path / "export", revision, root=repo, project_files=project_files)
    assert not (tmp_path / "export/manifest.json").exists()


def test_project_export_refuses_total_overflow_and_count_overflow_before_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    revision = repository(repo, {"README.md": b"Public source.", "ROADMAP.md": b"Public roadmap."})
    monkeypatch.setattr(operator, "CORPUS_LIMIT", 5)
    with pytest.raises(ValueError, match="corpus_limit"):
        operator.export_corpus(tmp_path / "bytes", revision, root=repo, project_files=True)
    assert not (tmp_path / "bytes").exists()
    monkeypatch.setattr(operator, "MAX_DOCUMENTS", 1)
    with pytest.raises(ValueError, match="corpus_catalogue"):
        operator.export_corpus(tmp_path / "count", revision, root=repo, project_files=True)
    assert not (tmp_path / "count").exists()
