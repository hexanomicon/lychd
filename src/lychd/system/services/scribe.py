from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader

from lychd.system.constants import (
    PATH_RUNE_TEMPLATES_DIR,
    PATH_SYSTEMD_UNITS_DIR,
    PATH_SYSTEMD_USER_UNITS_DIR,
)
from lychd.system.schemas import QuadletBase, QuadletContainer, QuadletPod, QuadletTarget, SystemdService

logger = structlog.get_logger()

# Quadlet-managed unit suffixes (processed by the Quadlet generator in the
# containers/systemd dir). Coven `.target` units are NOT here -- they are plain
# systemd units and live in the systemd user unit dir instead.
_QUADLET_SUFFIXES: frozenset[str] = frozenset(
    {".container", ".pod", ".volume", ".network", ".kube", ".image", ".build"}
)
_SYSTEMD_SUFFIXES: frozenset[str] = frozenset({".target"})


class ScribeService:
    """The Scribe of Quadlet manifests.

    Responsible for:
    - Rendering validated manifest models into Systemd Quadlet files.
    - Transactional Inscription (Atomic Swap).
    - Version control via the Git Sentinel.
    """

    def __init__(
        self,
        templates_dir: Path | None = None,
        output_dir: Path | None = None,
        systemd_dir: Path | None = None,
    ) -> None:
        """Initialize ScribeService.

        ``output_dir`` is the Quadlet dir (``.container``/``.pod``/``.volume``);
        ``systemd_dir`` is the systemd user unit dir where plain units (Coven
        ``.target`` files) are written so systemd can actually load them.
        """
        self._output_dir = output_dir or PATH_SYSTEMD_UNITS_DIR
        self._systemd_dir = systemd_dir or PATH_SYSTEMD_USER_UNITS_DIR
        self._templates_dir = templates_dir or PATH_RUNE_TEMPLATES_DIR
        # autoescape MUST be False: these are systemd unit files, not HTML. HTML
        # autoescaping corrupts Exec=/Environment= lines that carry shell-quoted
        # args (shlex uses `'`, `&`, etc.) into `&#39;`/`&amp;`.
        self._env = Environment(
            loader=FileSystemLoader(self._templates_dir),
            autoescape=False,  # noqa: S701 - unit files are not HTML; see comment above
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._container_tmpl = self._env.get_template("container.jinja")
        self._pod_tmpl = self._env.get_template("pod.jinja")
        self._target_tmpl = self._env.get_template("target.jinja")

    def initialize_git_sentinel(self) -> None:
        """Initialize Git in the binding site.

        The Ritual of the Unblinking Eye.
        """
        git_path = shutil.which("git")
        if git_path is None:
            logger.warning("git_not_found", action="skipping_sentinel_initialization")
            return

        if not (self._output_dir / ".git").exists():
            logger.info("initializing_git_sentinel", path=str(self._output_dir))
            try:
                subprocess.run(  # noqa: S603
                    [git_path, "init", "-b", "main", str(self._output_dir)],
                    check=True,
                    capture_output=True,
                )
                # Initial commit if empty
                (self._output_dir / ".gitignore").write_text("*.bak\n", encoding="utf-8")
                subprocess.run([git_path, "-C", str(self._output_dir), "add", "."], check=True)  # noqa: S603
                subprocess.run(  # noqa: S603
                    [git_path, "-C", str(self._output_dir), "commit", "-m", "Initial inscription"],
                    check=True,
                    capture_output=True,
                )
                logger.info("git_sentinel_initialised", path=str(self._output_dir))
            except (subprocess.CalledProcessError, OSError) as e:
                error_msg = getattr(e, "stderr", str(e)).strip()
                logger.warning("git_init_failed", error=error_msg)

    def generate_all(self, manifests: Sequence[QuadletBase]) -> None:
        """Generate all Quadlet manifests via the Rite of Atomic Inscription (ADR 08).

        Design choice (F1): units are routed by kind. Quadlet-managed units
        (``.container``/``.pod``/``.volume``) go to the Quadlet dir; plain
        systemd units (Coven ``.target``) go to the systemd user unit dir where
        systemd will actually load them. Writing ``.target`` into the Quadlet dir
        (the previous behaviour) left them dead -- Quadlet ignores them and the
        ``WantedBy=``/``Conflicts=`` edges pointing at them never resolved.
        """
        logger.info("beginning_inscription", count=len(manifests))

        # Ensure both binding sites exist.
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._systemd_dir.mkdir(parents=True, exist_ok=True)
        self.initialize_git_sentinel()

        with tempfile.TemporaryDirectory(prefix="lychd-scribe-") as staging_dir:
            staging_root = Path(staging_dir)
            quadlet_staging = staging_root / "quadlet"
            systemd_staging = staging_root / "systemd"
            quadlet_staging.mkdir()
            systemd_staging.mkdir()

            # Render each manifest into the staging dir for its destination.
            for manifest in manifests:
                dest = self._destination_for(manifest)
                staging = quadlet_staging if dest == self._output_dir else systemd_staging
                self._write_manifest(manifest, target_dir=staging)

            self._atomic_swap(quadlet_staging, self._output_dir, _QUADLET_SUFFIXES)
            self._atomic_swap(systemd_staging, self._systemd_dir, _SYSTEMD_SUFFIXES)
            self._sentinel_commit()

        logger.info("inscription_complete")

    def _destination_for(self, manifest: QuadletBase) -> Path:
        """Route a manifest to its physical directory by unit kind (F1)."""
        if isinstance(manifest, QuadletTarget):
            return self._systemd_dir
        return self._output_dir

    def _atomic_swap(self, staging_path: Path, dest_dir: Path, managed_suffixes: frozenset[str]) -> None:
        """Move rendered files from a staging directory to a destination Binding Site.

        Only files whose suffix this Scribe manages are cleared from the
        destination, so unrelated units in the systemd user dir are preserved.
        """
        if dest_dir.exists():
            for item in dest_dir.iterdir():
                if item.is_file() and item.suffix in managed_suffixes:
                    item.unlink()

        # Move new ones
        for manifest in staging_path.iterdir():
            shutil.move(str(manifest), str(dest_dir / manifest.name))

    def _sentinel_commit(self) -> None:
        """Commit the new state to the Git Sentinel."""
        git_path = shutil.which("git")
        if git_path is None:
            return

        try:
            subprocess.run([git_path, "-C", str(self._output_dir), "add", "."], check=True)  # noqa: S603
            res = subprocess.run(  # noqa: S603
                [git_path, "-C", str(self._output_dir), "commit", "-m", "Manual Transmutation (lych bind)"],
                capture_output=True,
                text=True,
                check=False,
            )
            if "nothing to commit" in res.stdout:
                logger.debug("sentinel_no_changes")
            else:
                logger.info("sentinel_updated", message="Sentinels updated. Inscription versioned.")
        except (subprocess.CalledProcessError, OSError):
            logger.exception("sentinel_commit_failed")

    def write_user_unit(self, service: SystemdService) -> Path:
        """Inscribe a plain systemd ``--user`` unit (uncaged daemonhood).

        A deliberately SEPARATE path from :meth:`generate_all`: plain units do
        NOT touch the Quadlet staging dir, the Git Sentinel, or the
        managed-suffix atomic swap. They are written straight into the systemd
        user unit dir with the same atomic-write discipline (temp file in the
        same directory -> ``os.replace`` rename), so a rewrite is byte-stable
        and never disturbs any ``.container``/``.target``/sentinel state.

        Returns the path of the written unit.
        """
        self._systemd_dir.mkdir(parents=True, exist_ok=True)
        target = self._systemd_dir / service.filename
        content = service.render()

        fd, tmp_name = tempfile.mkstemp(dir=self._systemd_dir, prefix=".lychd-unit-", suffix=".tmp")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            tmp_path.replace(target)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

        logger.info("user_unit_inscribed", path=str(target))
        return target

    def _write_manifest(self, manifest: QuadletBase, target_dir: Path) -> None:
        """Render a single Quadlet manifest into its physical file."""
        if isinstance(manifest, QuadletPod):
            content = self._pod_tmpl.render(**manifest.model_dump())
            filename = f"{manifest.pod_name}.pod"
        elif isinstance(manifest, QuadletContainer):
            content = self._container_tmpl.render(**manifest.model_dump())
            filename = f"{manifest.container_name}.container"
        elif isinstance(manifest, QuadletTarget):
            content = self._target_tmpl.render(**manifest.model_dump())
            filename = f"lychd-coven-{manifest.name}.target"
        else:
            msg = f"Unknown Quadlet manifest type: {type(manifest)}"
            raise TypeError(msg)

        (target_dir / filename).write_text(content, encoding="utf-8")
