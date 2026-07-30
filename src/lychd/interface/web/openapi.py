"""OpenAPI configuration shared by the runtime and offline contract exporter."""

from __future__ import annotations

from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import JsonRenderPlugin


def build_openapi_config(
    *,
    title: str,
    version: str,
    use_handler_docstrings: bool,
) -> OpenAPIConfig:
    """Serve deterministic schema JSON without injecting a remote documentation UI."""
    return OpenAPIConfig(
        title=title,
        version=version,
        use_handler_docstrings=use_handler_docstrings,
        render_plugins=[JsonRenderPlugin()],
    )
