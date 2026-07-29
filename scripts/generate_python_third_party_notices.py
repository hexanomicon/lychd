from __future__ import annotations

import argparse
import re
from importlib import metadata
from pathlib import Path

LICENSE_FILENAME = re.compile(
    r"^(?:licen[cs]e|copying|notice|authors?)(?:[-._].*)?$",
    flags=re.IGNORECASE,
)
MAX_LEGACY_LICENSE_LENGTH = 160
FALLBACK_DONORS = {
    "logfire-api": "logfire",
    "opentelemetry-util-http": "opentelemetry-instrumentation",
}


class DependencyNoticeError(RuntimeError):
    """Raised when a shipped Python distribution has no auditable license terms."""


def _canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _declared_license(distribution: metadata.Distribution) -> str:
    expression = distribution.metadata.get("License-Expression")
    if expression:
        return expression.strip()
    legacy = distribution.metadata.get("License")
    if legacy and len(legacy.strip()) <= MAX_LEGACY_LICENSE_LENGTH and "\n" not in legacy.strip():
        return legacy.strip()
    return "UNKNOWN"


def _project_url(distribution: metadata.Distribution) -> str:
    for value in distribution.metadata.get_all("Project-URL") or ():
        _, separator, url = value.partition(",")
        if separator and url.strip():
            return url.strip()
    return distribution.metadata.get("Home-page") or "not declared"


def _license_payloads(distribution: metadata.Distribution) -> list[tuple[str, str]]:
    payloads: list[tuple[str, str]] = []
    seen: set[Path] = set()
    for relative in distribution.files or ():
        if LICENSE_FILENAME.fullmatch(relative.name) is None:
            continue
        located = Path(str(distribution.locate_file(relative))).resolve()
        if located in seen or not located.is_file():
            continue
        seen.add(located)
        text = located.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            payloads.append((str(relative), text))
    return sorted(payloads)


def _fallback_payloads(
    distribution_name: str,
    distribution: metadata.Distribution,
) -> tuple[str, list[tuple[str, str]]]:
    donor_name = FALLBACK_DONORS.get(distribution_name)
    if donor_name is None:
        message = f"{distribution_name} ships no readable license or notice file"
        raise DependencyNoticeError(message)
    try:
        donor = metadata.distribution(donor_name)
    except metadata.PackageNotFoundError as error:
        message = f"{distribution_name} requires missing audited license donor {donor_name}"
        raise DependencyNoticeError(message) from error

    declared = _declared_license(distribution)
    donor_declared = _declared_license(donor)
    if declared != donor_declared:
        message = (
            f"{distribution_name} declares {declared}, but its audited donor {donor_name} declares {donor_declared}"
        )
        raise DependencyNoticeError(message)
    payloads = _license_payloads(donor)
    if not payloads:
        message = f"audited license donor {donor_name} ships no readable license file"
        raise DependencyNoticeError(message)
    note = (
        f"Upstream package omitted a physical license file. The identical {declared} terms below "
        f"come from installed sibling distribution {donor_name} {donor.version}."
    )
    return note, payloads


def generate_notice(*, forbidden: set[str]) -> str:
    """Render a deterministic notice inventory for the active Python environment."""
    installed: dict[str, metadata.Distribution] = {}
    for distribution in metadata.distributions():
        raw_name = distribution.metadata.get("Name")
        if not raw_name:
            message = "an installed distribution has no Name metadata"
            raise DependencyNoticeError(message)
        name = _canonical_name(raw_name)
        if name == "lychd":
            continue
        if name in installed:
            message = f"multiple installed distributions normalize to {name}"
            raise DependencyNoticeError(message)
        installed[name] = distribution

    forbidden_present = sorted(forbidden & installed.keys())
    if forbidden_present:
        message = f"forbidden binary distributions are installed: {', '.join(forbidden_present)}"
        raise DependencyNoticeError(message)

    sections: list[str] = []
    for name, distribution in sorted(installed.items()):
        declared = _declared_license(distribution)
        payloads = _license_payloads(distribution)
        fallback_note: str | None = None
        if not payloads:
            fallback_note, payloads = _fallback_payloads(name, distribution)
        rendered_payloads = "\n\n".join(f"--- {relative} ---\n{text}" for relative, text in payloads)
        heading = [
            "=" * 80,
            f"{name}@{distribution.version}",
            f"Declared license: {declared}",
            f"Project: {_project_url(distribution)}",
            "=" * 80,
        ]
        if fallback_note is not None:
            heading.extend(("", fallback_note))
        sections.append("\n".join((*heading, "", rendered_payloads)))

    preamble = [
        "LychD Vessel — Python Third-Party Notices",
        "",
        "Generated from the distributions installed in the production Python environment.",
        "Every distribution must provide readable license material or match one explicitly",
        "audited same-project fallback. The generator fails closed for unexplained omissions",
        "and for forbidden bundled-binary distributions.",
        "",
        "Debian base-image and system-library notices remain available under /usr/share/doc.",
        "",
    ]
    return "\n".join(preamble) + "\n\n".join(sections) + "\n"


def main() -> None:
    """Generate the production Python dependency notice file."""
    parser = argparse.ArgumentParser(
        description="Generate fail-closed notices from an installed Python environment.",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--forbid-distribution",
        action="append",
        default=[],
        help="Fail when this normalized distribution name is installed",
    )
    arguments = parser.parse_args()
    forbidden = {_canonical_name(name) for name in arguments.forbid_distribution}
    output = arguments.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generate_notice(forbidden=forbidden), encoding="utf-8")
    print(f"wrote Python dependency notices to {output}")  # noqa: T201


if __name__ == "__main__":
    main()
