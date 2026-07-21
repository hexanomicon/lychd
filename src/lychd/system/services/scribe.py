from __future__ import annotations

import json
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import structlog
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from lychd.system.constants import (
    PATH_RUNE_TEMPLATES_DIR,
    PATH_SYSTEMD_UNITS_DIR,
    PATH_SYSTEMD_USER_UNITS_DIR,
)
from lychd.system.schemas import (
    QuadletBase,
    QuadletContainer,
    QuadletPod,
    QuadletTarget,
    SystemdService,
    quadlet_environment_assignment,
)

logger = structlog.get_logger()

_OWNERSHIP_FILENAME = ".lychd-owned.json"
_AUTHORITY_MODE = 0o600
_QUADLET_SUFFIXES: frozenset[str] = frozenset(
    {".container", ".pod", ".volume", ".network", ".kube", ".image", ".build"}
)
_GENERATED_SYSTEMD_SUFFIXES: frozenset[str] = frozenset({".target"})
_PLAIN_SYSTEMD_SUFFIXES: frozenset[str] = frozenset({".path", ".service"})
_SYSTEMD_SUFFIXES = _GENERATED_SYSTEMD_SUFFIXES | _PLAIN_SYSTEMD_SUFFIXES
_SAFE_STEM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@-]*\Z")


class ScribeOwnershipError(RuntimeError):
    """The binding-site ownership record is absent where needed or invalid."""


class ScribeConflictError(RuntimeError):
    """A requested filename is occupied by a unit LychD does not own."""


class ScribeTransactionError(RuntimeError):
    """A binding transaction failed and could not be rolled back cleanly."""


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON keys instead of silently accepting the last one."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = f"Duplicate ownership manifest key: {key!r}."
            raise ValueError(msg)
        result[key] = value
    return result


def _validate_owned_filename(
    filename: str,
    *,
    suffixes: frozenset[str],
    site: Literal["quadlet", "systemd"],
) -> None:
    """Reject traversal, foreign namespaces, and unsupported unit kinds."""
    path = Path(filename)
    if (
        not filename
        or path.is_absolute()
        or path.name != filename
        or "/" in filename
        or "\\" in filename
        or "\x00" in filename
    ):
        msg = f"Unsafe {site} ownership entry: {filename!r}."
        raise ValueError(msg)

    suffix = path.suffix
    stem = filename[: -len(suffix)] if suffix else filename
    if suffix not in suffixes or not _SAFE_STEM.fullmatch(stem) or ".." in stem:
        msg = f"Invalid LychD {site} unit filename: {filename!r}."
        raise ValueError(msg)

    if site == "quadlet":
        namespaced = stem == "lychd" or (stem.startswith("lychd-") and len(stem) > len("lychd-"))
    else:
        namespaced = stem.startswith("lychd-") and len(stem) > len("lychd-")
    if not namespaced:
        msg = f"Unit filename is outside the LychD namespace: {filename!r}."
        raise ValueError(msg)


class _OwnershipManifest(BaseModel):
    """Exact filenames that this installation has authority to replace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1]
    quadlet: tuple[str, ...] = ()
    systemd: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_entries(self) -> _OwnershipManifest:
        if len(set(self.quadlet)) != len(self.quadlet) or len(set(self.systemd)) != len(self.systemd):
            msg = "The Scribe ownership manifest contains duplicate filenames."
            raise ValueError(msg)
        for filename in self.quadlet:
            _validate_owned_filename(filename, suffixes=_QUADLET_SUFFIXES, site="quadlet")
        for filename in self.systemd:
            _validate_owned_filename(filename, suffixes=_SYSTEMD_SUFFIXES, site="systemd")
        return self


@dataclass(frozen=True)
class _SitePlan:
    """The selected owned subset to replace at one binding site."""

    directory: Path
    owned_names: frozenset[str]
    previous_names: frozenset[str]
    files: Mapping[str, bytes]


@dataclass
class _PreparedCommit:
    """Same-filesystem backups and replacement files prepared before mutation."""

    transaction_dirs: dict[Path, Path]
    backups: dict[tuple[Path, str], Path]
    files: dict[tuple[Path, str], Path]
    existed: set[tuple[Path, str]]
    manifest_backup: Path | None
    manifest_file: Path


class ScribeService:
    """Render and transactionally bind LychD-owned Quadlet/systemd units.

    The binding directories are shared operator namespaces. Authority comes
    only from the validated hidden ownership manifest; a suffix alone never
    grants permission to overwrite or remove a file.
    """

    def __init__(
        self,
        templates_dir: Path | None = None,
        output_dir: Path | None = None,
        systemd_dir: Path | None = None,
    ) -> None:
        """Initialize the two physical binding sites and rendering templates."""
        self._output_dir = output_dir or PATH_SYSTEMD_UNITS_DIR
        self._systemd_dir = systemd_dir or PATH_SYSTEMD_USER_UNITS_DIR
        self._templates_dir = templates_dir or PATH_RUNE_TEMPLATES_DIR
        # These are systemd unit files, not HTML. Autoescaping would corrupt
        # Exec=/Environment= values that contain shell quoting or ampersands.
        self._env = Environment(
            loader=FileSystemLoader(self._templates_dir),
            autoescape=False,  # noqa: S701
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template_globals = cast("dict[str, object]", self._env.globals)
        template_globals["quadlet_environment_assignment"] = quadlet_environment_assignment
        self._container_tmpl = self._env.get_template("container.jinja")
        self._pod_tmpl = self._env.get_template("pod.jinja")
        self._target_tmpl = self._env.get_template("target.jinja")

    @property
    def _ownership_path(self) -> Path:
        return self._output_dir / _OWNERSHIP_FILENAME

    def generate_all(self, manifests: Sequence[QuadletBase]) -> None:
        """Render and replace exactly the previously owned generated file set.

        Quadlet sources land in the Quadlet directory. Coven ``.target`` units
        land in the systemd user directory. LychD-owned plain ``.service`` and
        ``.path`` units are preserved because they are managed independently by
        :meth:`write_plain_unit`.
        """
        logger.info("beginning_inscription", count=len(manifests))
        self._ensure_binding_sites()
        previous = self._load_ownership()
        quadlet_files, systemd_files = self._render_generated(manifests)
        previous_targets = frozenset(
            name for name in previous.systemd if Path(name).suffix in _GENERATED_SYSTEMD_SUFFIXES
        )
        preserved_plain_units = set(previous.systemd) - set(previous_targets)
        next_ownership = _OwnershipManifest(
            version=1,
            quadlet=tuple(sorted(quadlet_files)),
            systemd=tuple(sorted(preserved_plain_units | set(systemd_files))),
        )
        plans = (
            _SitePlan(
                directory=self._output_dir,
                owned_names=frozenset(previous.quadlet),
                previous_names=frozenset(previous.quadlet),
                files=quadlet_files,
            ),
            _SitePlan(
                directory=self._systemd_dir,
                owned_names=frozenset(previous.systemd),
                previous_names=previous_targets,
                files=systemd_files,
            ),
        )
        self._commit(plans, next_ownership)

        logger.info("inscription_complete")

    def reconcile_all(
        self,
        manifests: Sequence[QuadletBase],
        *,
        plain_units: Mapping[str, str],
    ) -> None:
        """Reconcile one complete desired binding state in a single transaction.

        The supplied generated manifests and named plain units are the complete
        desired LychD-owned set. Previously owned files absent from either set
        are removed; every unowned binding-site path remains untouched.
        """
        logger.info(
            "beginning_complete_inscription",
            manifest_count=len(manifests),
            plain_unit_count=len(plain_units),
        )
        plain_files = self._encode_plain_units(plain_units)
        self._ensure_binding_sites()
        previous = self._load_ownership()
        quadlet_files, generated_systemd_files = self._render_generated(manifests)
        systemd_files = {**generated_systemd_files, **plain_files}
        next_ownership = _OwnershipManifest(
            version=1,
            quadlet=tuple(sorted(quadlet_files)),
            systemd=tuple(sorted(systemd_files)),
        )
        plans = (
            _SitePlan(
                directory=self._output_dir,
                owned_names=frozenset(previous.quadlet),
                previous_names=frozenset(previous.quadlet),
                files=quadlet_files,
            ),
            _SitePlan(
                directory=self._systemd_dir,
                owned_names=frozenset(previous.systemd),
                previous_names=frozenset(previous.systemd),
                files=systemd_files,
            ),
        )
        self._commit(plans, next_ownership)
        logger.info("complete_inscription_finished")

    def write_plain_unit(self, filename: str, content: str) -> Path:
        """Atomically write one LychD-namespaced plain user unit.

        ``filename`` must be a basename ending in ``.service`` or ``.path``.
        Existing paths are replaceable only when the ownership manifest already
        grants LychD authority over that exact filename.
        """
        plain_file = self._encode_plain_units({filename: content})

        self._ensure_binding_sites()
        previous = self._load_ownership()
        next_ownership = _OwnershipManifest(
            version=1,
            quadlet=tuple(sorted(previous.quadlet)),
            systemd=tuple(sorted({*previous.systemd, filename})),
        )
        plans = (
            _SitePlan(
                directory=self._output_dir,
                owned_names=frozenset(previous.quadlet),
                previous_names=frozenset(),
                files={},
            ),
            _SitePlan(
                directory=self._systemd_dir,
                owned_names=frozenset(previous.systemd),
                previous_names=frozenset({filename}) if filename in previous.systemd else frozenset(),
                files=plain_file,
            ),
        )
        self._commit(plans, next_ownership)
        target = self._systemd_dir / filename
        logger.info("user_unit_inscribed", path=str(target))
        return target

    def write_user_unit(self, service: SystemdService) -> Path:
        """Inscribe an uncaged daemon ``.service`` through the ownership gate."""
        return self.write_plain_unit(service.filename, service.render())

    def _ensure_binding_sites(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._systemd_dir.mkdir(parents=True, exist_ok=True)

    def _render_generated(
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
                staging = quadlet_staging if destination == self._output_dir else systemd_staging
                self._write_manifest(manifest, target_dir=staging)

            return (
                self._read_staged(quadlet_staging, site="quadlet"),
                self._read_staged(systemd_staging, site="systemd"),
            )

    @staticmethod
    def _encode_plain_units(plain_units: Mapping[str, str]) -> dict[str, bytes]:
        encoded: dict[str, bytes] = {}
        for filename, content in plain_units.items():
            _validate_owned_filename(filename, suffixes=_PLAIN_SYSTEMD_SUFFIXES, site="systemd")
            if "\x00" in content:
                msg = f"Systemd unit content cannot contain NUL bytes: {filename}."
                raise ValueError(msg)
            encoded[filename] = content.encode("utf-8")
        return encoded

    def _destination_for(self, manifest: QuadletBase) -> Path:
        """Route a manifest to its physical directory by unit kind."""
        if isinstance(manifest, QuadletTarget):
            return self._systemd_dir
        return self._output_dir

    def _load_ownership(self) -> _OwnershipManifest:
        path = self._ownership_path
        if not os.path.lexists(path):
            return _OwnershipManifest(version=1)
        try:
            content = self._read_authority_manifest().decode("utf-8")
            raw = json.loads(content, object_pairs_hook=_unique_json_object)
            return _OwnershipManifest.model_validate(raw)
        except ScribeOwnershipError:
            raise
        except (OSError, UnicodeError, ValueError, ValidationError, TypeError) as exc:
            msg = f"Invalid Scribe ownership manifest at {path}: {exc}"
            raise ScribeOwnershipError(msg) from exc

    def _read_authority_manifest(self) -> bytes:
        """Read the manifest through a no-follow descriptor after authority checks."""
        path = self._ownership_path
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            msg = f"Unsafe Scribe ownership manifest path: {path}."
            raise ScribeOwnershipError(msg) from exc
        try:
            self._validate_authority_stat(path, os.fstat(fd))
            with os.fdopen(fd, "rb") as handle:
                fd = -1
                return handle.read()
        finally:
            if fd >= 0:
                os.close(fd)

    def _validate_authority_path(self) -> None:
        path = self._ownership_path
        try:
            manifest_stat = path.lstat()
        except OSError as exc:
            msg = f"Scribe ownership manifest is unavailable: {path}."
            raise ScribeOwnershipError(msg) from exc
        self._validate_authority_stat(path, manifest_stat)

    @staticmethod
    def _validate_authority_stat(path: Path, manifest_stat: os.stat_result) -> None:
        if not stat.S_ISREG(manifest_stat.st_mode):
            msg = f"Scribe ownership manifest must be a regular non-symlink file: {path}."
            raise ScribeOwnershipError(msg)
        current_uid = os.getuid()
        if manifest_stat.st_uid != current_uid:
            msg = (
                f"Scribe ownership manifest must be owned by uid {current_uid}; "
                f"found uid {manifest_stat.st_uid}: {path}."
            )
            raise ScribeOwnershipError(msg)
        mode = stat.S_IMODE(manifest_stat.st_mode)
        if mode != _AUTHORITY_MODE:
            msg = f"Scribe ownership manifest must have mode 0600; found {mode:04o}: {path}."
            raise ScribeOwnershipError(msg)

    def _read_staged(
        self,
        staging_dir: Path,
        *,
        site: Literal["quadlet", "systemd"],
    ) -> dict[str, bytes]:
        suffixes = _QUADLET_SUFFIXES if site == "quadlet" else _GENERATED_SYSTEMD_SUFFIXES
        files: dict[str, bytes] = {}
        for path in staging_dir.iterdir():
            _validate_owned_filename(path.name, suffixes=suffixes, site=site)
            files[path.name] = path.read_bytes()
        return files

    def _commit(self, plans: Sequence[_SitePlan], ownership: _OwnershipManifest) -> None:
        """Apply per-file atomic replacements and roll every site back on error."""
        self._validate_plans(plans)
        prepared = self._prepare_commit(plans, ownership)
        manifest_attempted = False

        try:
            for plan in plans:
                for name in sorted(plan.files):
                    self._atomic_replace(prepared.files[(plan.directory, name)], plan.directory / name)
                for name in sorted(plan.previous_names - frozenset(plan.files)):
                    target = plan.directory / name
                    if os.path.lexists(target):
                        target.unlink()
                self._fsync_directory(plan.directory)

            manifest_attempted = True
            self._atomic_replace(prepared.manifest_file, self._ownership_path)
            self._validate_authority_path()
            self._fsync_directory(self._output_dir)
        except BaseException as exc:
            try:
                self._rollback(
                    plans,
                    backups=prepared.backups,
                    existed=prepared.existed,
                    manifest_backup=prepared.manifest_backup,
                    manifest_attempted=manifest_attempted,
                )
            except Exception as rollback_exc:  # noqa: BLE001 - preserve both transaction failures
                msg = f"Scribe binding failed ({exc!r}) and rollback failed ({rollback_exc!r})."
                raise ScribeTransactionError(msg) from exc
            raise
        finally:
            for transaction_dir in prepared.transaction_dirs.values():
                shutil.rmtree(transaction_dir, ignore_errors=True)

    def _prepare_commit(
        self,
        plans: Sequence[_SitePlan],
        ownership: _OwnershipManifest,
    ) -> _PreparedCommit:
        """Prepare all backups and new files before the first live mutation."""
        transaction_dirs: dict[Path, Path] = {}
        backups: dict[tuple[Path, str], Path] = {}
        files: dict[tuple[Path, str], Path] = {}
        existed: set[tuple[Path, str]] = set()
        manifest_backup: Path | None = None

        try:
            for directory in {plan.directory for plan in plans}:
                transaction_dirs[directory] = Path(tempfile.mkdtemp(prefix=".lychd-transaction-", dir=directory))

            for plan in plans:
                transaction_dir = transaction_dirs[plan.directory]
                for name in sorted(plan.previous_names | frozenset(plan.files)):
                    target = plan.directory / name
                    key = (plan.directory, name)
                    if os.path.lexists(target):
                        existed.add(key)
                        mode = stat.S_IMODE(target.stat(follow_symlinks=False).st_mode)
                        backups[key] = self._prepare_file(
                            transaction_dir,
                            target.read_bytes(),
                            mode=mode,
                            prefix="backup-",
                        )
                for name, content in sorted(plan.files.items()):
                    files[(plan.directory, name)] = self._prepare_file(
                        transaction_dir,
                        content,
                        mode=0o644,
                        prefix="new-",
                    )

            ownership_path = self._ownership_path
            output_transaction = transaction_dirs[self._output_dir]
            if os.path.lexists(ownership_path):
                manifest_backup = self._prepare_file(
                    output_transaction,
                    self._read_authority_manifest(),
                    mode=_AUTHORITY_MODE,
                    prefix="manifest-backup-",
                )
            manifest_content = (json.dumps(ownership.model_dump(mode="json"), indent=2, sort_keys=True) + "\n").encode()
            manifest_file = self._prepare_file(
                output_transaction,
                manifest_content,
                mode=_AUTHORITY_MODE,
                prefix="manifest-new-",
            )
            prepared = _PreparedCommit(
                transaction_dirs=transaction_dirs,
                backups=backups,
                files=files,
                existed=existed,
                manifest_backup=manifest_backup,
                manifest_file=manifest_file,
            )
        except BaseException:
            for transaction_dir in transaction_dirs.values():
                shutil.rmtree(transaction_dir, ignore_errors=True)
            raise
        return prepared

    def _validate_plans(self, plans: Sequence[_SitePlan]) -> None:
        for plan in plans:
            if not plan.previous_names <= plan.owned_names:
                msg = "Scribe transaction attempted to replace a filename it does not own."
                raise ScribeOwnershipError(msg)

            for name in plan.owned_names:
                target = plan.directory / name
                if os.path.lexists(target):
                    target_stat = target.stat(follow_symlinks=False)
                    if target.is_symlink() or not stat.S_ISREG(target_stat.st_mode):
                        msg = f"Owned unit path is not a regular file: {target}."
                        raise ScribeOwnershipError(msg)

            for name in plan.files:
                target = plan.directory / name
                if os.path.lexists(target) and name not in plan.owned_names:
                    msg = f"Refusing to overwrite unowned binding-site path: {target}."
                    raise ScribeConflictError(msg)

    def _rollback(
        self,
        plans: Sequence[_SitePlan],
        *,
        backups: Mapping[tuple[Path, str], Path],
        existed: set[tuple[Path, str]],
        manifest_backup: Path | None,
        manifest_attempted: bool,
    ) -> None:
        for plan in reversed(plans):
            affected = plan.previous_names | frozenset(plan.files)
            for name in sorted(affected, reverse=True):
                key = (plan.directory, name)
                target = plan.directory / name
                if key in existed:
                    self._atomic_replace(backups[key], target)
                elif os.path.lexists(target):
                    target.unlink()
            self._fsync_directory(plan.directory)

        if manifest_attempted:
            if manifest_backup is None:
                self._ownership_path.unlink(missing_ok=True)
            else:
                self._atomic_replace(manifest_backup, self._ownership_path)
                self._validate_authority_path()
            self._fsync_directory(self._output_dir)
        elif os.path.lexists(self._ownership_path):
            self._validate_authority_path()

    @staticmethod
    def _prepare_file(directory: Path, content: bytes, *, mode: int, prefix: str) -> Path:
        fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=prefix, suffix=".tmp")
        path = Path(tmp_name)
        try:
            os.fchmod(fd, mode)
            with os.fdopen(fd, "wb") as handle:
                fd = -1
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            if fd >= 0:
                os.close(fd)
            path.unlink(missing_ok=True)
            raise
        return path

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _atomic_replace(source: Path, target: Path) -> None:
        """Use the platform atomic-overwrite primitive explicitly."""
        os.replace(source, target)  # noqa: PTH105 - explicit atomic overwrite primitive

    def _write_manifest(self, manifest: QuadletBase, target_dir: Path) -> None:
        """Render one manifest into isolated staging after validating its name."""
        if isinstance(manifest, QuadletPod):
            content = self._pod_tmpl.render(**manifest.model_dump())
            filename = f"{manifest.pod_name}.pod"
            site: Literal["quadlet", "systemd"] = "quadlet"
            suffixes = _QUADLET_SUFFIXES
        elif isinstance(manifest, QuadletContainer):
            content = self._container_tmpl.render(**manifest.model_dump())
            filename = f"{manifest.container_name}.container"
            site = "quadlet"
            suffixes = _QUADLET_SUFFIXES
        elif isinstance(manifest, QuadletTarget):
            content = self._target_tmpl.render(**manifest.model_dump())
            filename = f"lychd-coven-{manifest.name}.target"
            site = "systemd"
            suffixes = _GENERATED_SYSTEMD_SUFFIXES
        else:
            msg = f"Unknown Quadlet manifest type: {type(manifest)}"
            raise TypeError(msg)

        _validate_owned_filename(filename, suffixes=suffixes, site=site)
        target = target_dir / filename
        if target.exists():
            msg = f"Duplicate generated unit filename: {filename}."
            raise ScribeConflictError(msg)
        target.write_text(content, encoding="utf-8")
