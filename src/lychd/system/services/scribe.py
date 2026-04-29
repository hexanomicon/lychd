from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader

from lychd.system.constants import PATH_RUNE_TEMPLATES_DIR, PATH_SYSTEMD_UNITS_DIR
from lychd.system.schemas import QuadletBase, QuadletContainer, QuadletPod, QuadletTarget

logger = structlog.get_logger()


class ScribeService:
    """The Scribe of Runes.

    Responsible for:
    - Transmuting Rune schemas into Systemd Quadlet files.
    - Transactional Inscription (Atomic Swap).
    - Version control via the Git Sentinel.
    """

    def __init__(
        self,
        templates_dir: Path | None = None,
        output_dir: Path | None = None,
    ) -> None:
        """Initialize ScribeService."""
        self._output_dir = output_dir or PATH_SYSTEMD_UNITS_DIR
        self._templates_dir = templates_dir or PATH_RUNE_TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(self._templates_dir),
            autoescape=True,
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

    def generate_all(self, runes: Sequence[QuadletBase]) -> None:
        """Generate all Runes via the Rite of Atomic Inscription (ADR 08)."""
        logger.info("beginning_inscription", count=len(runes))

        # Ensure output directory exists (The Binding Site)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self.initialize_git_sentinel()

        with tempfile.TemporaryDirectory(prefix="lychd-scribe-") as staging_dir:
            staging_path = Path(staging_dir)
            # Inscribe all runes into the staging directory
            for rune in runes:
                self._write_rune(rune, target_dir=staging_path)
            self._atomic_swap(staging_path)
            self._sentinel_commit()

        logger.info("inscription_complete")

    def _atomic_swap(self, staging_path: Path) -> None:
        """Move files from staging directory to the Binding Site."""
        if self._output_dir.exists():
            for item in self._output_dir.iterdir():
                if item.is_file() and item.suffix in [".container", ".pod", ".target", ".volume"]:
                    item.unlink()

        # Move new ones
        for rune in staging_path.iterdir():
            shutil.move(str(rune), str(self._output_dir / rune.name))

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

    def _write_rune(self, rune: QuadletBase, target_dir: Path) -> None:
        """Inscribe a single Rune into its physical form."""
        if isinstance(rune, QuadletPod):
            content = self._pod_tmpl.render(**rune.model_dump())
            filename = f"{rune.pod_name}.pod"
        elif isinstance(rune, QuadletContainer):
            content = self._container_tmpl.render(**rune.model_dump())
            filename = f"{rune.container_name}.container"
        elif isinstance(rune, QuadletTarget):
            content = self._target_tmpl.render(**rune.model_dump())
            filename = f"lychd-coven-{rune.name}.target"
        else:
            msg = f"Unknown rune type: {type(rune)}"
            raise TypeError(msg)

        (target_dir / filename).write_text(content, encoding="utf-8")
