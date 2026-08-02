"""OpenAPI configuration shared by the runtime and offline contract exporter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import JsonRenderPlugin
from litestar.plugins.pydantic import PydanticSchemaPlugin
from pydantic import BaseModel

if TYPE_CHECKING:
    from litestar.openapi.spec import Schema
    from litestar.typing import FieldDefinition

__all__ = ["StrictPydanticSchemaPlugin", "build_openapi_config"]


class StrictPydanticSchemaPlugin(PydanticSchemaPlugin):
    """Keep Pydantic's forbidden-extra law in Litestar's generated schemas."""

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: Any) -> Schema:
        schema = super().to_openapi_schema(field_definition, schema_creator)
        annotation: Any = field_definition.annotation
        if (
            isinstance(annotation, type)
            and issubclass(annotation, BaseModel)
            and annotation.model_config.get("extra") == "forbid"
        ):
            schema.additional_properties = False
        return schema


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
