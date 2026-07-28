# ruff: noqa: INP001
"""Export the real Altar controller contract for deterministic TypeScript generation."""

from __future__ import annotations

import json
from pathlib import Path

from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig

from lychd.interface.web import (
    AltarController,
    BridgeController,
    LoomController,
    NexusController,
    OrbController,
)
from lychd.interface.web.deps import web_dependencies

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
        openapi_config=OpenAPIConfig(title="LychD Altar API", version="1"),
    )
    schema = app.openapi_schema.to_schema()
    OUTPUT.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
