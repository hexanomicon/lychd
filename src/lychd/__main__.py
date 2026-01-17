from __future__ import annotations

import os

from litestar.cli.main import litestar_group


def run_cli() -> None:
    """Entry point for the command-line interface.

    Bootstrap the CLI, establish a environment variable `LITESTAR_APP`, which points to the
    application factory function - lychd.app:create_app.

    Then invoke `litestar_group()`, a generic CLI runner that uses this
    variable to discover and initialize the application, triggering the
    `on_cli_init` hook within the `AppInit` protocol implementation.
    """
    from lychd.config import get_settings

    settings = get_settings()

    os.environ.setdefault("LITESTAR_APP", "lychd.app:create_app")
    os.environ.setdefault("LITESTAR_APP_NAME", settings.app.name)

    litestar_group()


if __name__ == "__main__":
    run_cli()
