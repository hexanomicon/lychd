"""Private per-user credential files for native desktop installation."""

from __future__ import annotations

import os
import secrets

from lychd.system.constants import PATH_POSTGRES_ROOT_DIR
from lychd.system.desktop.private import check_path, private_directory, private_file, publish_file

_RUNTIME = ("LYCHD_RUNTIME_DB_PASSWORD", "LYCHD_APP_SECRET_KEY", "LYCHD_LOCAL_ACCESS_PASSWORD")
_ADMIN = ("LYCHD_DB_PASSWORD", "LYCHD_PHOENIX_DB_PASSWORD")


def load_credentials(*, administrative: bool = False, provision: bool = False) -> None:
    """Set standard file references without replacing explicit credentials or disclosing values."""
    directory = PATH_POSTGRES_ROOT_DIR / "desktop-credentials"
    if provision:
        private_directory(directory)
    for name in (*_RUNTIME, *_ADMIN) if administrative else _RUNTIME:
        file_key = f"{name}_FILE"
        if os.environ.get(name) or os.environ.get(file_key):
            continue
        path = directory / name.lower()
        check_path(path)
        if provision and not path.exists():
            publish_file(path, secrets.token_urlsafe(48).encode("ascii"))
        if path.is_file():
            private_file(path)
            os.environ[file_key] = str(path)
