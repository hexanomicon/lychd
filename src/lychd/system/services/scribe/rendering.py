"""Isolated Jinja rendering for generated Quadlet and systemd sources."""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, cast

from jinja2 import Environment, FileSystemLoader

from lychd.system.binding_sites import BindingSites
from lychd.system.schemas import (
    QuadletBase,
    QuadletContainer,
    QuadletPod,
    QuadletTarget,
    quadlet_environment_assignment,
)
from lychd.system.services.scribe.errors import ScribeConflictError
from lychd.system.services.scribe.naming import (
    GENERATED_SYSTEMD_SUFFIXES,
    QUADLET_SUFFIXES,
    validate_owned_filename,
)


class BindingRenderer:
    """Render generated units into an isolated staging directory."""

    def __init__(self, *, templates_dir: Path, sites: BindingSites) -> None:
        """Load unit templates and their two physical destinations."""
        self._sites = sites
        # These are systemd unit files, not HTML. Autoescaping would corrupt
        # Exec=/Environment= values that contain shell quoting or ampersands.
        self._env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=False,  # noqa: S701
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template_globals = cast("dict[str, object]", self._env.globals)
        template_globals["quadlet_environment_assignment"] = quadlet_environment_assignment
        self._container_tmpl = self._env.get_template("container.jinja")
        self._pod_tmpl = self._env.get_template("pod.jinja")
        self._target_tmpl = self._env.get_template("target.jinja")

    def render_generated(
        self,
        manifests: Sequence[QuadletBase],
    ) -> tuple[dict[str, bytes], dict[str, bytes]]:
        """Render all generated units into isolated staging."""
        with tempfile.TemporaryDirectory(prefix="lychd-scribe-") as staging_dir:
            staging_root = Path(staging_dir)
            quadlet_staging = staging_root / "quadlet"
            systemd_staging = staging_root / "systemd"
            quadlet_staging.mkdir()
            systemd_staging.mkdir()

            for manifest in manifests:
                destination = self._destination_for(manifest)
                staging = quadlet_staging if destination == self._sites.quadlet else systemd_staging
                self._write_manifest(manifest, target_dir=staging)

            return (
                self._read_staged(quadlet_staging, site="quadlet"),
                self._read_staged(systemd_staging, site="systemd"),
            )

    def _destination_for(self, manifest: QuadletBase) -> Path:
        """Route a manifest to its physical directory by unit kind."""
        if isinstance(manifest, QuadletTarget):
            return self._sites.systemd_user
        return self._sites.quadlet

    @staticmethod
    def _read_staged(
        staging_dir: Path,
        *,
        site: Literal["quadlet", "systemd"],
    ) -> dict[str, bytes]:
        suffixes = QUADLET_SUFFIXES if site == "quadlet" else GENERATED_SYSTEMD_SUFFIXES
        files: dict[str, bytes] = {}
        for path in staging_dir.iterdir():
            validate_owned_filename(path.name, suffixes=suffixes, site=site)
            files[path.name] = path.read_bytes()
        return files

    def _write_manifest(self, manifest: QuadletBase, target_dir: Path) -> None:
        """Render one manifest into isolated staging after validating its name."""
        if isinstance(manifest, QuadletPod):
            content = self._pod_tmpl.render(**manifest.model_dump())
            filename = f"{manifest.pod_name}.pod"
            site: Literal["quadlet", "systemd"] = "quadlet"
            suffixes = QUADLET_SUFFIXES
        elif isinstance(manifest, QuadletContainer):
            content = self._container_tmpl.render(**manifest.model_dump())
            filename = f"{manifest.container_name}.container"
            site = "quadlet"
            suffixes = QUADLET_SUFFIXES
        elif isinstance(manifest, QuadletTarget):
            content = self._target_tmpl.render(**manifest.model_dump())
            filename = manifest.filename
            site = "systemd"
            suffixes = GENERATED_SYSTEMD_SUFFIXES
        else:
            msg = f"Unknown Quadlet manifest type: {type(manifest)}"
            raise TypeError(msg)

        validate_owned_filename(filename, suffixes=suffixes, site=site)
        target = target_dir / filename
        if target.exists():
            msg = f"Duplicate generated unit filename: {filename}."
            raise ScribeConflictError(msg)
        target.write_text(content, encoding="utf-8")
