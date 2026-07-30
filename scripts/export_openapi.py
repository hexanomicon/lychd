"""Export the real Altar controller contract for deterministic TypeScript generation."""

from __future__ import annotations

import json
from pathlib import Path

from litestar import Litestar

from lychd.interface.web import (
    AltarController,
    BridgeController,
    LoomController,
    NexusController,
    OrbController,
)
from lychd.interface.web.deps import web_dependencies
from lychd.interface.web.openapi import build_openapi_config

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "openapi.json"


def main() -> None:
    """Write a stable OpenAPI document from the production controller classes."""
    app = Litestar(
        route_handlers=[
            AltarController,
            BridgeController,
            NexusController,
            LoomController,
            OrbController,
        ],
        dependencies=web_dependencies,
        openapi_config=build_openapi_config(
            title="LychD Altar API",
            version="1",
            use_handler_docstrings=False,
        ),
    )
    schema = app.openapi_schema.to_schema()
    OUTPUT.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
