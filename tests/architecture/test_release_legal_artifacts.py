from __future__ import annotations

import json
import tomllib
import zipfile
from pathlib import Path

import pytest
from scripts.verify_release_artifacts import ReleaseArtifactError, _verify_wheel  # pyright: ignore[reportPrivateUsage]

from lychd.__about__ import __version__

ROOT = Path(__file__).parents[2]
_WHEEL_DIST_INFO = f"lychd-{__version__}.dist-info"
_SOURCE_REVISION = "a" * 40


def test_delivery_clients_are_project_roots_outside_python_source() -> None:
    assert (ROOT / "clients" / "web" / "package.json").is_file()
    assert (ROOT / "clients" / "android" / "README.md").is_file()
    assert not (ROOT / "frontend").exists()
    assert not (ROOT / "src" / "clients").exists()


def test_python_distributions_declare_every_project_notice() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    assert project["project"]["license"] == "MPL-2.0"
    assert set(project["project"]["license-files"]) == {
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "clients/web/static/THIRD_PARTY_NOTICES.txt",
    }

    sdist_includes = set(project["tool"]["hatch"]["build"]["targets"]["sdist"]["include"])
    assert {
        "/.containerignore",
        "/Containerfile",
        "/LICENSE",
        "/Makefile",
        "/THIRD_PARTY_NOTICES.md",
        "/clients/web",
        "/scripts",
        "/src",
        "/uv.lock",
    } <= sdist_includes
    assert "Advanced Alchemy 1.8.0" in notices
    assert "Copyright (c) 2024 Litestar Organization" in notices
    assert "Alembic 1.17.2" in notices
    assert "Copyright 2009-2025 Michael Bayer." in notices


def test_container_build_context_is_podman_native_and_strictly_bounded() -> None:
    assert not (ROOT / "compose.yaml").exists()
    assert not (ROOT / ".dockerignore").exists()

    ignore_lines = [
        line
        for raw_line in (ROOT / ".containerignore").read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip()) and not line.startswith("#")
    ]
    assert ignore_lines[0] == "**"
    assert ignore_lines[1:] == [
        "!.containerignore",
        "!Containerfile",
        "!LICENSE",
        "!README.md",
        "!THIRD_PARTY_NOTICES.md",
        "!pyproject.toml",
        "!uv.lock",
        "!clients/",
        "clients/**",
        "!clients/web/",
        "clients/web/**",
        "!clients/web/static/",
        "clients/web/static/**",
        "!clients/web/static/THIRD_PARTY_NOTICES.txt",
        "!scripts/",
        "!scripts/generate_python_third_party_notices.py",
        "!src/",
        "!src/**",
    ]


def test_version_bump_is_review_only_and_has_one_real_version_owner() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    about = (ROOT / "src" / "lychd" / "__about__.py").read_text(encoding="utf-8")
    bump = project["tool"]["bumpversion"]

    assert f'__version__ = "{__version__}"' in about
    assert bump["current_version"] == __version__
    assert bump["commit"] is False
    assert bump["tag"] is False
    assert {entry["filename"] for entry in bump["files"]} == {
        "pyproject.toml",
        "src/lychd/__about__.py",
    }


def test_container_carries_project_license_and_notices() -> None:
    containerfile = (ROOT / "Containerfile").read_text(encoding="utf-8")

    assert "COPY pyproject.toml uv.lock README.md LICENSE THIRD_PARTY_NOTICES.md ./" in containerfile
    notice_copy = "COPY clients/web/static/THIRD_PARTY_NOTICES.txt ./clients/web/static/"
    project_install = "/bin/uv sync --frozen --no-dev --no-editable"
    assert notice_copy in containerfile
    assert containerfile.index(notice_copy) < containerfile.index(project_install)
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
        "psycopg-binary==3.3.6",
    ]
    assert "--no-dev --no-install-project --no-editable" in containerfile


def test_altar_notice_is_generated_and_shipped_with_static_client() -> None:
    source_notice = ROOT / "clients" / "web" / "static" / "THIRD_PARTY_NOTICES.txt"
    public_notice = ROOT / "src" / "lychd" / "public" / "THIRD_PARTY_NOTICES.txt"
    notice = source_notice.read_text(encoding="utf-8")

    assert "@xyflow/svelte@1.6.6" in notice
    assert "svelte@5.57.0" in notice
    assert "Regenerate with: npm run licenses" in notice
    assert public_notice.read_bytes() == source_notice.read_bytes()

    package = json.loads((ROOT / "clients" / "web" / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["build"].startswith("npm run licenses && ")


def test_ordinary_altar_ci_does_not_stamp_the_ambient_github_revision() -> None:
    workflow = (ROOT / ".github" / "workflows" / "checks.yml").read_text(encoding="utf-8")
    frontend_commands = [line.strip() for line in workflow.splitlines() if "make frontend-" in line]

    assert frontend_commands == [
        "env -u GITHUB_SHA make frontend-check",
        "env -u GITHUB_SHA make frontend-build",
    ]


def test_candidate_workflow_cannot_publish_packages_or_images() -> None:
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

    assert "Release Candidate (No Publication)" in workflow
    assert "make release-candidate" in workflow
    assert "actions/upload-artifact@v7" in workflow
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


@pytest.fixture
def wheel_members() -> dict[str, bytes]:
    frontend_notice = (ROOT / "clients" / "web" / "static" / "THIRD_PARTY_NOTICES.txt").read_bytes()
    return {
        f"{_WHEEL_DIST_INFO}/METADATA": (
            f"Metadata-Version: 2.4\nName: lychd\nVersion: {__version__}\nLicense-Expression: MPL-2.0\n\n"
        ).encode(),
        f"{_WHEEL_DIST_INFO}/licenses/LICENSE": (ROOT / "LICENSE").read_bytes(),
        f"{_WHEEL_DIST_INFO}/licenses/THIRD_PARTY_NOTICES.md": (ROOT / "THIRD_PARTY_NOTICES.md").read_bytes(),
        f"{_WHEEL_DIST_INFO}/licenses/clients/web/static/THIRD_PARTY_NOTICES.txt": frontend_notice,
        "lychd/public/THIRD_PARTY_NOTICES.txt": frontend_notice,
        "lychd/public/index.html": (
            f'<a href="https://github.com/hexanomicon/lychd/tree/{_SOURCE_REVISION}/clients/web">Source</a>'
        ).encode(),
    }


def _write_wheel(tmp_path: Path, members: dict[str, bytes]) -> Path:
    wheel = tmp_path / f"lychd-{__version__}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return wheel


def test_wheel_accepts_exact_mpl_license_header(tmp_path: Path, wheel_members: dict[str, bytes]) -> None:
    wheel_members[f"{_WHEEL_DIST_INFO}/METADATA"] += b"Description mentions License-Expression: MIT.\n"
    wheel = _write_wheel(tmp_path, wheel_members)

    _verify_wheel(wheel, _SOURCE_REVISION, __version__, ROOT)


@pytest.mark.parametrize(
    "license_metadata",
    [
        pytest.param("\n", id="missing"),
        pytest.param("License-Expression: MIT\n\n", id="wrong"),
        pytest.param("\nLicense-Expression: MPL-2.0\n", id="missing-with-body-spoof"),
        pytest.param("License-Expression: MIT\n\nLicense-Expression: MPL-2.0\n", id="wrong-with-body-spoof"),
        pytest.param("License-Expression: MPL-2.00\n\n", id="value-suffix"),
        pytest.param("License-Expression: MPL-2.0 OR MIT\n\n", id="compound-expression"),
        pytest.param("X-License-Expression: MPL-2.0\n\n", id="field-prefix"),
        pytest.param("Summary: License-Expression: MPL-2.0\n\n", id="other-field-value"),
    ],
)
def test_wheel_rejects_missing_or_inexact_license_header(
    tmp_path: Path,
    wheel_members: dict[str, bytes],
    license_metadata: str,
) -> None:
    wheel_members[f"{_WHEEL_DIST_INFO}/METADATA"] = (
        f"Metadata-Version: 2.4\nName: lychd\nVersion: {__version__}\n{license_metadata}"
    ).encode()
    wheel = _write_wheel(tmp_path, wheel_members)

    with pytest.raises(ReleaseArtifactError, match="wheel metadata"):
        _verify_wheel(wheel, _SOURCE_REVISION, __version__, ROOT)


@pytest.mark.parametrize(
    ("member", "replacement", "error"),
    [
        pytest.param(
            f"{_WHEEL_DIST_INFO}/METADATA",
            f"Name: other\nVersion: {__version__}\nLicense-Expression: MPL-2.0\n\n".encode(),
            "wheel metadata does not identify the lychd distribution",
            id="name",
        ),
        pytest.param(
            f"{_WHEEL_DIST_INFO}/METADATA",
            b"Name: lychd\nVersion: 999.0.0\nLicense-Expression: MPL-2.0\n\n",
            "wheel metadata does not match project version",
            id="version",
        ),
        pytest.param(f"{_WHEEL_DIST_INFO}/licenses/LICENSE", b"altered", "wheel project license differs", id="license"),
        pytest.param(
            f"{_WHEEL_DIST_INFO}/licenses/THIRD_PARTY_NOTICES.md",
            b"altered",
            "wheel source notice differs",
            id="source-notice",
        ),
        pytest.param(
            f"{_WHEEL_DIST_INFO}/licenses/clients/web/static/THIRD_PARTY_NOTICES.txt",
            b"altered",
            "wheel frontend notice differs",
            id="frontend-notice",
        ),
        pytest.param(
            "lychd/public/THIRD_PARTY_NOTICES.txt", b"altered", "wheel Altar notice differs", id="altar-notice"
        ),
        pytest.param("lychd/public/index.html", b"altered", "wheel does not link its Altar", id="source-revision"),
    ],
)
def test_wheel_rejects_altered_identity_or_payload(
    tmp_path: Path,
    wheel_members: dict[str, bytes],
    member: str,
    replacement: bytes,
    error: str,
) -> None:
    wheel_members[member] = replacement
    wheel = _write_wheel(tmp_path, wheel_members)

    with pytest.raises(ReleaseArtifactError, match=error):
        _verify_wheel(wheel, _SOURCE_REVISION, __version__, ROOT)
