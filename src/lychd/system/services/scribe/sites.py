"""Prepared binding-site validation shared by every Scribe operation."""

from __future__ import annotations

import os
from pathlib import Path

from lychd.system.binding_sites import BindingSites, inspect_binding_site
from lychd.system.services.scribe.errors import ScribeOwnershipError


def require_prepared(sites: BindingSites) -> None:
    """Require initialization-prepared sites; Binding never creates them."""
    for path in sites.paths:
        if not os.path.lexists(path):
            msg = f"Binding site is absent; run `lychd init` first: {path}"
            raise ScribeOwnershipError(msg)
        validate_binding_site(path)


def validate_binding_site(path: Path) -> None:
    """Enforce the same binding-site law presented by host readiness."""
    inspection = inspect_binding_site(path, current_uid=os.getuid())
    if not inspection.prepared:
        if inspection.detail.startswith("owned by uid"):
            msg = f"Binding site must be {inspection.detail}: {path}"
        else:
            msg = f"Binding site is not prepared: {path}: {inspection.detail}"
        raise ScribeOwnershipError(msg)
