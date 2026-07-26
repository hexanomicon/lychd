"""Stable Scribe service facade over rendering, authority, planning, and commit."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

import structlog
from pydantic import ValidationError

from lychd.system.binding_sites import (
    DEFAULT_BINDING_SITES,
    AttestedBindingSites,
    BindingSites,
)
from lychd.system.constants import PATH_RUNE_TEMPLATES_DIR
from lychd.system.schemas import QuadletBase, SystemdService
from lychd.system.services.scribe.authority import BindingAuthority
from lychd.system.services.scribe.errors import ScribeOwnershipError
from lychd.system.services.scribe.models import (
    BindingReconcilePlan,
    OwnedBindings,
    SitePlan,
)
from lychd.system.services.scribe.naming import encode_plain_units, runtime_unit_for_source
from lychd.system.services.scribe.planning import BindingPlanner, validate_plans
from lychd.system.services.scribe.rendering import BindingRenderer
from lychd.system.services.scribe.sites import require_prepared, validate_binding_site
from lychd.system.services.scribe.transaction import BindingTransaction

logger = structlog.get_logger()


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
        expected_sites: AttestedBindingSites | None = None,
    ) -> None:
        """Initialize the two physical binding sites and rendering templates."""
        attested_paths = expected_sites.paths if expected_sites is not None else None
        self._output_dir = output_dir or (
            attested_paths.quadlet if attested_paths is not None else DEFAULT_BINDING_SITES.quadlet
        )
        self._systemd_dir = systemd_dir or (
            attested_paths.systemd_user if attested_paths is not None else DEFAULT_BINDING_SITES.systemd_user
        )
        if attested_paths is not None and (
            self._output_dir != attested_paths.quadlet or self._systemd_dir != attested_paths.systemd_user
        ):
            message = "Scribe paths must match the supplied attested binding sites."
            raise ValueError(message)
        self._templates_dir = templates_dir or PATH_RUNE_TEMPLATES_DIR
        self._sites = BindingSites(quadlet=self._output_dir, systemd_user=self._systemd_dir)
        self._authority = BindingAuthority(self._output_dir)
        self._renderer = BindingRenderer(templates_dir=self._templates_dir, sites=self._sites)
        self._planner = BindingPlanner(
            sites=self._sites,
            renderer=self._renderer,
            authority=self._authority,
        )
        self._transaction = BindingTransaction(
            self._authority,
            expected_sites=expected_sites,
        )

    @property
    def _ownership_path(self) -> Path:
        return self._authority.path

    @property
    def ownership_path(self) -> Path:
        """Return the exact Scribe authority path for lifecycle reporting."""
        return self._ownership_path

    def generate_all(self, manifests: Sequence[QuadletBase]) -> None:
        """Render and replace exactly the previously owned generated file set.

        Quadlet sources land in the Quadlet directory. Coven ``.target`` units
        land in the systemd user directory. LychD-owned plain ``.service`` and
        ``.path`` units are preserved because they are managed independently by
        :meth:`write_plain_unit`.
        """
        logger.info("beginning_inscription", count=len(manifests))
        require_prepared(self._sites)
        write_set = self._planner.generated(manifests)
        require_prepared(self._sites)
        self._transaction.commit(write_set)
        logger.info("inscription_complete")

    def reconcile_all(
        self,
        manifests: Sequence[QuadletBase],
        *,
        plain_units: Mapping[str, str],
        expected_generation: str | None = None,
        expected_desired_generation: str | None = None,
    ) -> str:
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
        require_prepared(self._sites)
        write_set = self._planner.complete(manifests, plain_units=plain_units)
        require_prepared(self._sites)
        committed_generation = self._transaction.commit(
            write_set,
            expected_generation=expected_generation,
            expected_desired_generation=expected_desired_generation,
        )
        logger.info("complete_inscription_finished")
        return committed_generation

    def plan_reconcile_all(
        self,
        manifests: Sequence[QuadletBase],
        *,
        plain_units: Mapping[str, str],
    ) -> BindingReconcilePlan:
        """Inspect the exact complete-fileset transaction without mutation."""
        require_prepared(self._sites)
        return self._planner.preview(self._planner.complete(manifests, plain_units=plain_units))

    def write_plain_unit(self, filename: str, content: str) -> Path:
        """Atomically write one LychD-namespaced plain user unit.

        ``filename`` must be a basename ending in ``.service`` or ``.path``.
        Existing paths are replaceable only when the ownership manifest already
        grants LychD authority over that exact filename.
        """
        plain_file = encode_plain_units({filename: content})
        require_prepared(self._sites)
        write_set = self._planner.plain_unit(filename, plain_file)
        require_prepared(self._sites)
        self._transaction.commit(write_set)
        target = self._systemd_dir / filename
        logger.info("user_unit_inscribed", path=str(target))
        return target

    def write_user_unit(self, service: SystemdService) -> Path:
        """Inscribe an uncaged daemon ``.service`` through the ownership gate."""
        return self.write_plain_unit(service.filename, service.render())

    def inspect_owned_bindings(self) -> OwnedBindings:
        """Return validated exact binding ownership without mutating either site."""
        receipt_present = os.path.lexists(self._ownership_path)
        if not receipt_present:
            return OwnedBindings(receipt_present=False)
        validate_binding_site(self._output_dir)
        try:
            content = self._authority.read()
            previous = self._authority.parse(content)
        except ScribeOwnershipError:
            raise
        except (OSError, UnicodeError, ValueError, ValidationError, TypeError) as exc:
            msg = f"Invalid Scribe ownership manifest at {self._ownership_path}: {exc}"
            raise ScribeOwnershipError(msg) from exc
        if previous.systemd and os.path.lexists(self._systemd_dir):
            validate_binding_site(self._systemd_dir)
        plans = [
            SitePlan(
                directory=self._output_dir,
                owned_names=frozenset(previous.quadlet),
                previous_names=frozenset(previous.quadlet),
                files={},
            )
        ]
        if os.path.lexists(self._systemd_dir):
            plans.append(
                SitePlan(
                    directory=self._systemd_dir,
                    owned_names=frozenset(previous.systemd),
                    previous_names=frozenset(previous.systemd),
                    files={},
                )
            )
        validate_plans(plans)
        quadlet_sources = tuple(self._output_dir / name for name in previous.quadlet)
        systemd_sources = tuple(self._systemd_dir / name for name in previous.systemd)
        generation = self._authority.generation(
            authority=content,
            sources=(*quadlet_sources, *systemd_sources),
        )
        runtime_units = tuple(
            sorted({runtime_unit_for_source(name) for name in (*previous.quadlet, *previous.systemd)})
        )
        return OwnedBindings(
            receipt_present=True,
            generation=generation,
            quadlet_sources=quadlet_sources,
            systemd_sources=systemd_sources,
            runtime_units=runtime_units,
        )

    def clear_owned_bindings(self, *, expected_generation: str | None = None) -> None:
        """Transactionally remove exact sources while retaining their authority."""
        owned = self.inspect_owned_bindings()
        if expected_generation is not None and owned.generation != expected_generation:
            msg = "Scribe ownership changed after lifecycle planning; rerun `lychd del`."
            raise ScribeOwnershipError(msg)
        if not owned.receipt_present or owned.source_count == 0:
            return
        guarded_generation = owned.generation
        if guarded_generation is None:  # pragma: no cover - receipt inspection invariant
            msg = "Scribe ownership receipt has no observed generation."
            raise ScribeOwnershipError(msg)
        include_systemd = os.path.lexists(self._systemd_dir)
        if include_systemd:
            validate_binding_site(self._systemd_dir)
        self._transaction.commit(
            self._planner.removal(
                include_systemd=include_systemd,
                release_authority=False,
            ),
            expected_generation=guarded_generation,
        )

    def release_owned_binding_authority(
        self,
        *,
        expected_generation: str,
    ) -> None:
        """Clear exact authority only after every recorded source is absent."""
        owned = self.inspect_owned_bindings()
        if owned.generation != expected_generation:
            msg = "Scribe ownership changed before authority release; rerun `lychd del`."
            raise ScribeOwnershipError(msg)
        if not owned.receipt_present:
            return
        remaining = tuple(path for path in (*owned.quadlet_sources, *owned.systemd_sources) if os.path.lexists(path))
        if remaining:
            msg = "Refusing to release Scribe authority while owned binding sources remain."
            raise ScribeOwnershipError(msg)

        include_systemd = os.path.lexists(self._systemd_dir)
        if include_systemd:
            validate_binding_site(self._systemd_dir)
        self._transaction.commit(
            self._planner.removal(
                include_systemd=include_systemd,
                release_authority=True,
            ),
            expected_generation=expected_generation,
            release_empty_authority=True,
        )
