from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_python_distributions_declare_every_project_notice() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["license"] == "MPL-2.0"
    assert set(project["project"]["license-files"]) == {
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "frontend/static/THIRD_PARTY_NOTICES.txt",
    }

    sdist_includes = set(project["tool"]["hatch"]["build"]["targets"]["sdist"]["include"])
    assert {
        "/Containerfile",
        "/LICENSE",
        "/Makefile",
        "/THIRD_PARTY_NOTICES.md",
        "/frontend",
        "/scripts",
        "/src",
    } <= sdist_includes


def test_version_bump_is_review_only_and_has_one_real_version_owner() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    about = (ROOT / "src" / "lychd" / "__about__.py").read_text(encoding="utf-8")
    bump = project["tool"]["bumpversion"]

    assert '__version__ = "0.0.2"' in about
    assert bump["current_version"] == "0.0.2"
    assert bump["commit"] is False
    assert bump["tag"] is False
    assert {entry["filename"] for entry in bump["files"]} == {
        "pyproject.toml",
        "src/lychd/__about__.py",
    }


def test_container_carries_project_license_and_notices() -> None:
    containerfile = (ROOT / "Containerfile").read_text(encoding="utf-8")

    assert "COPY pyproject.toml uv.lock README.md LICENSE THIRD_PARTY_NOTICES.md ./" in containerfile
    assert "/app/LICENSE /app/LICENSE" in containerfile
    assert "/app/THIRD_PARTY_NOTICES.md /app/THIRD_PARTY_NOTICES.md" in containerfile
    assert "/app/PYTHON_THIRD_PARTY_NOTICES.txt" in containerfile
    assert "--forbid-distribution psycopg-binary" in containerfile
    assert "apt-get install --yes --no-install-recommends libpq5" in containerfile
    assert 'org.opencontainers.image.licenses="MPL-2.0"' in containerfile

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = set(project["project"]["dependencies"])
    assert "litestar-saq>=0.5.3" in dependencies
    assert "psycopg[pool]>=3.2.13,<4" in dependencies
    assert all("psycopg-binary" not in dependency for dependency in dependencies)
    assert project["project"]["optional-dependencies"]["postgres-binary"] == [
        "psycopg-binary==3.2.13",
    ]
    assert "--no-dev --no-install-project --no-editable" in containerfile


def test_altar_notice_is_generated_and_shipped_with_static_client() -> None:
    source_notice = ROOT / "frontend" / "static" / "THIRD_PARTY_NOTICES.txt"
    public_notice = ROOT / "src" / "lychd" / "public" / "THIRD_PARTY_NOTICES.txt"
    notice = source_notice.read_text(encoding="utf-8")

    assert "mermaid@11.16.0" in notice
    assert "svelte@5.56.8" in notice
    assert "Regenerate with: npm run licenses" in notice
    assert public_notice.read_bytes() == source_notice.read_bytes()

    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["build"].startswith("npm run licenses && ")


def test_candidate_workflow_cannot_publish_packages_or_images() -> None:
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

    assert "Release Candidate (No Publication)" in workflow
    assert "make release-candidate" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "contents: read" in workflow
    for forbidden in (
        "packages: write",
        "id-token: write",
        "docker/login-action",
        "docker/build-push-action",
        "gh-action-pypi-publish",
        "twine upload",
        "uv publish",
    ):
        assert forbidden not in workflow


def test_release_candidate_has_immutable_source_and_real_archive_gates() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    source_gate = (ROOT / "scripts" / "verify_release_source.py").read_text(encoding="utf-8")
    artifact_gate = (ROOT / "scripts" / "verify_release_artifacts.py").read_text(encoding="utf-8")

    assert "release-candidate: release-preflight" in makefile
    assert "$(MAKE) format-check" in makefile
    assert "--release-tag" in makefile
    assert "--install-check" in makefile
    assert '"status", "--porcelain=v1", "--untracked-files=all"' in source_gate
    assert '[uv, "pip", "check"' in artifact_gate
    assert "SHA256SUMS" in artifact_gate
    assert "src/lychd/public/" in artifact_gate
    assert "release tag" in artifact_gate
