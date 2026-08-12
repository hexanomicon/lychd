from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from email.parser import BytesParser
from pathlib import Path

REVISION_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
VERSION_PATTERN = re.compile(r'^__version__ = "([^"]+)"$', flags=re.MULTILINE)
SOURCE_URL_PREFIX = "https://github.com/hexanomicon/lychd/tree/"


class ReleaseArtifactError(RuntimeError):
    """Raised when a release artifact loses source identity or legal material."""


def _only(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        message = f"expected exactly one {pattern} in {directory}, found {len(matches)}"
        raise ReleaseArtifactError(message)
    return matches[0]


def _contains_exact_source(payloads: list[bytes], revision: str, label: str) -> None:
    expected = f"{SOURCE_URL_PREFIX}{revision}/clients/web".encode()
    joined = b"\n".join(payloads)
    if expected not in joined:
        message = f"{label} does not link its Altar to exact source revision {revision}"
        raise ReleaseArtifactError(message)
    if f"{SOURCE_URL_PREFIX}main/clients/web".encode() in joined:
        message = f"{label} still embeds the mutable main-branch source URL"
        raise ReleaseArtifactError(message)


def _require_suffix(names: set[str], suffix: str, label: str) -> str:
    matches = [name for name in names if name.endswith(suffix)]
    if len(matches) != 1:
        message = f"{label} expected one member ending {suffix!r}, found {len(matches)}"
        raise ReleaseArtifactError(message)
    return matches[0]


def _distribution_version(root: Path) -> str:
    about = (root / "src" / "lychd" / "__about__.py").read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(about)
    if match is None:
        message = "could not resolve the distribution version from src/lychd/__about__.py"
        raise ReleaseArtifactError(message)
    return match.group(1)


def _metadata_value(payload: bytes, field: str, label: str) -> str:
    value = BytesParser().parsebytes(payload).get(field)
    if value is None:
        message = f"{label} metadata is missing {field}"
        raise ReleaseArtifactError(message)
    return value


def _git_paths(root: Path, *arguments: str) -> list[str]:
    git = shutil.which("git")
    if git is None:
        message = "git is required to constrain release-generated files"
        raise ReleaseArtifactError(message)
    result = subprocess.run(  # noqa: S603
        [git, "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _verify_generated_delta(root: Path) -> None:
    changed = {
        *_git_paths(root, "diff", "HEAD", "--name-only"),
        *_git_paths(root, "ls-files", "--others", "--exclude-standard"),
    }
    unexpected = sorted(path for path in changed if not path.startswith("src/lychd/public/"))
    if unexpected:
        message = "release build changed files outside the generated Altar tree: " + ", ".join(unexpected)
        raise ReleaseArtifactError(message)


def _verify_static_tree(root: Path, revision: str) -> None:
    public = root / "src" / "lychd" / "public"
    payloads = [
        path.read_bytes() for path in sorted(public.rglob("*")) if path.is_file() and path.suffix in {".html", ".js"}
    ]
    _contains_exact_source(payloads, revision, "tracked Altar")
    if not (public / "THIRD_PARTY_NOTICES.txt").is_file():
        message = "tracked Altar is missing THIRD_PARTY_NOTICES.txt"
        raise ReleaseArtifactError(message)


def _verify_wheel(wheel: Path, revision: str, version: str, root: Path) -> None:
    if not wheel.name.startswith(f"lychd-{version}-"):
        message = f"wheel filename does not match project version {version}: {wheel.name}"
        raise ReleaseArtifactError(message)
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        metadata_name = _require_suffix(names, ".dist-info/METADATA", "wheel")
        metadata = archive.read(metadata_name)
        if b"License-Expression: MPL-2.0" not in metadata:
            message = "wheel metadata does not declare MPL-2.0"
            raise ReleaseArtifactError(message)
        if _metadata_value(metadata, "Name", "wheel") != "lychd":
            message = "wheel metadata does not identify the lychd distribution"
            raise ReleaseArtifactError(message)
        if _metadata_value(metadata, "Version", "wheel") != version:
            message = f"wheel metadata does not match project version {version}"
            raise ReleaseArtifactError(message)

        license_member = _require_suffix(names, ".dist-info/licenses/LICENSE", "wheel")
        source_notice_member = _require_suffix(
            names,
            ".dist-info/licenses/THIRD_PARTY_NOTICES.md",
            "wheel",
        )
        frontend_notice_member = _require_suffix(
            names,
            ".dist-info/licenses/clients/web/static/THIRD_PARTY_NOTICES.txt",
            "wheel",
        )
        public_notice_member = _require_suffix(
            names,
            "lychd/public/THIRD_PARTY_NOTICES.txt",
            "wheel",
        )
        _require_suffix(names, "lychd/public/index.html", "wheel")

        expected_license = (root / "LICENSE").read_bytes()
        expected_source_notice = (root / "THIRD_PARTY_NOTICES.md").read_bytes()
        expected_frontend_notice = (root / "clients" / "web" / "static" / "THIRD_PARTY_NOTICES.txt").read_bytes()
        if archive.read(license_member) != expected_license:
            message = "wheel project license differs from the reviewed repository license"
            raise ReleaseArtifactError(message)
        if archive.read(source_notice_member) != expected_source_notice:
            message = "wheel source notice differs from the reviewed repository notice"
            raise ReleaseArtifactError(message)
        if archive.read(frontend_notice_member) != expected_frontend_notice:
            message = "wheel frontend notice differs from the reviewed source inventory"
            raise ReleaseArtifactError(message)
        if archive.read(public_notice_member) != expected_frontend_notice:
            message = "wheel Altar notice differs from the reviewed source inventory"
            raise ReleaseArtifactError(message)

        payloads = [
            archive.read(name)
            for name in sorted(names)
            if name.startswith("lychd/public/") and name.endswith((".html", ".js"))
        ]
        _contains_exact_source(payloads, revision, "wheel")


def _read_tar_member(archive: tarfile.TarFile, member: str, label: str) -> bytes:
    extracted = archive.extractfile(member)
    if extracted is None:
        message = f"{label} is not a regular file"
        raise ReleaseArtifactError(message)
    return extracted.read()


def _verify_sdist_metadata(
    archive: tarfile.TarFile,
    root: str,
    version: str,
) -> None:
    pkg_info = _read_tar_member(archive, f"{root}/PKG-INFO", "sdist PKG-INFO")
    if _metadata_value(pkg_info, "Name", "sdist") != "lychd":
        message = "sdist metadata does not identify the lychd distribution"
        raise ReleaseArtifactError(message)
    if _metadata_value(pkg_info, "Version", "sdist") != version:
        message = f"sdist metadata does not match project version {version}"
        raise ReleaseArtifactError(message)
    if _metadata_value(pkg_info, "License-Expression", "sdist") != "MPL-2.0":
        message = "sdist metadata does not declare MPL-2.0"
        raise ReleaseArtifactError(message)


def _verify_sdist_files(
    archive: tarfile.TarFile,
    root: str,
    names: set[str],
    source_root: Path,
) -> None:
    expected_files = {
        "LICENSE": (source_root / "LICENSE").read_bytes(),
        "THIRD_PARTY_NOTICES.md": (source_root / "THIRD_PARTY_NOTICES.md").read_bytes(),
        "clients/web/static/THIRD_PARTY_NOTICES.txt": (
            source_root / "clients" / "web" / "static" / "THIRD_PARTY_NOTICES.txt"
        ).read_bytes(),
        "src/lychd/public/THIRD_PARTY_NOTICES.txt": (
            source_root / "clients" / "web" / "static" / "THIRD_PARTY_NOTICES.txt"
        ).read_bytes(),
    }
    for relative, expected in expected_files.items():
        member = f"{root}/{relative}"
        if member not in names or _read_tar_member(archive, member, f"sdist {relative}") != expected:
            message = f"sdist {relative} differs from the reviewed repository file"
            raise ReleaseArtifactError(message)


def _verify_sdist_source_link(
    archive: tarfile.TarFile,
    root: str,
    names: set[str],
    revision: str,
) -> None:
    public_prefix = f"{root}/src/lychd/public/"
    public_payloads = [
        _read_tar_member(archive, name, f"sdist {name}")
        for name in sorted(names)
        if name.startswith(public_prefix) and name.endswith((".html", ".js"))
    ]
    _contains_exact_source(public_payloads, revision, "sdist")


def _verify_sdist(sdist: Path, revision: str, version: str, source_root: Path) -> None:
    if sdist.name != f"lychd-{version}.tar.gz":
        message = f"sdist filename does not match project version {version}: {sdist.name}"
        raise ReleaseArtifactError(message)
    with tarfile.open(sdist, "r:gz") as archive:
        names = set(archive.getnames())
        roots = {name.split("/", 1)[0] for name in names if "/" in name}
        if len(roots) != 1:
            message = f"sdist expected one root directory, found {sorted(roots)}"
            raise ReleaseArtifactError(message)
        root = roots.pop()
        for relative in (
            "Containerfile",
            "LICENSE",
            "Makefile",
            "THIRD_PARTY_NOTICES.md",
            "clients/web/package-lock.json",
            "clients/web/package.json",
            "clients/web/static/THIRD_PARTY_NOTICES.txt",
            "clients/web/src/lib/components/AltarShell.svelte",
            "clients/web/vite.config.ts",
            "scripts/generate_python_third_party_notices.py",
            "scripts/verify_release_artifacts.py",
            "scripts/verify_release_source.py",
            "src/lychd/public/THIRD_PARTY_NOTICES.txt",
        ):
            member = f"{root}/{relative}"
            if member not in names:
                message = f"sdist is missing {relative}"
                raise ReleaseArtifactError(message)

        _verify_sdist_metadata(archive, root, version)
        _verify_sdist_files(archive, root, names, source_root)
        _verify_sdist_source_link(archive, root, names, revision)


def _verify_isolated_install(wheel: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        message = "uv is required for the isolated wheel-install check"
        raise ReleaseArtifactError(message)

    with tempfile.TemporaryDirectory(prefix="lychd-release-install-") as temporary:
        environment = Path(temporary) / "venv"
        subprocess.run(  # noqa: S603
            [uv, "venv", "--clear", "--python", f"{sys.version_info.major}.{sys.version_info.minor}", str(environment)],
            check=True,
        )
        python = environment / "bin" / "python"
        executable = environment / "bin" / "lychd"
        subprocess.run(  # noqa: S603
            [uv, "pip", "install", "--python", str(python), str(wheel)],
            check=True,
        )
        subprocess.run(  # noqa: S603
            [uv, "pip", "check", "--python", str(python)],
            check=True,
        )
        help_result = subprocess.run(  # noqa: S603
            [str(executable), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        if "Usage:" not in help_result.stdout:
            message = "isolated wheel install did not expose the LychD CLI"
            raise ReleaseArtifactError(message)
        subprocess.run(  # noqa: S603
            [str(python), "-c", "from lychd.app import create_app; assert callable(create_app)"],
            check=True,
        )
        for arguments in (("reactor", "consume", "--help"), ("database", "--help")):
            subprocess.run(  # noqa: S603
                [str(executable), *arguments],
                check=True,
                capture_output=True,
                text=True,
            )


def _write_checksums(dist_directory: Path, artifacts: tuple[Path, ...]) -> None:
    rows = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in sorted(artifacts)]
    (dist_directory / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def verify_release_artifacts(
    root: Path,
    dist_directory: Path,
    revision: str,
    *,
    install_check: bool,
    release_tag: str,
) -> None:
    """Inspect real archives and optionally exercise the wheel in a clean environment."""
    normalized = revision.strip().lower()
    if REVISION_PATTERN.fullmatch(normalized) is None:
        message = "source revision must be one full lowercase Git object id"
        raise ReleaseArtifactError(message)
    if not dist_directory.is_dir():
        message = f"artifact directory does not exist: {dist_directory}"
        raise ReleaseArtifactError(message)

    wheel = _only(dist_directory, "lychd-*.whl")
    sdist = _only(dist_directory, "lychd-*.tar.gz")
    version = _distribution_version(root)
    if release_tag and release_tag != f"v{version}":
        message = f"release tag {release_tag} does not match project version v{version}"
        raise ReleaseArtifactError(message)
    _verify_generated_delta(root)
    _verify_static_tree(root, normalized)
    _verify_wheel(wheel, normalized, version, root)
    _verify_sdist(sdist, normalized, version, root)
    if install_check:
        _verify_isolated_install(wheel)
    _write_checksums(dist_directory, (wheel, sdist))


def main() -> None:
    """Parse release-audit arguments and inspect the candidate artifacts."""
    parser = argparse.ArgumentParser(
        description="Verify LychD release archives, exact Altar source, notices, and installability.",
    )
    parser.add_argument("--dist-dir", required=True, type=Path)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument(
        "--release-tag",
        default="",
        help="Optional vX.Y.Z tag that must match the package version",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--install-check",
        action="store_true",
        help="Install the wheel and invoke its CLI in a fresh temporary environment",
    )
    arguments = parser.parse_args()
    verify_release_artifacts(
        arguments.root.resolve(),
        arguments.dist_dir.resolve(),
        arguments.source_revision,
        install_check=arguments.install_check,
        release_tag=arguments.release_tag,
    )
    print("release artifacts verified")  # noqa: T201


if __name__ == "__main__":
    main()
