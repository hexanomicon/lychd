from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypeVar, overload

from advanced_alchemy.extensions.litestar.dto import SQLAlchemyDTO, SQLAlchemyDTOConfig
from litestar.dto import DataclassDTO, dto_field
from litestar.dto.config import DTOConfig
from litestar.plugins.pydantic import PydanticDTO
from litestar.types.protocols import DataclassProtocol
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet

    from litestar.dto import RenameStrategy

__all__ = ("DTOConfig", "DataclassDTO", "PydanticDTO", "SQLAlchemyDTO", "config", "dto_field")

type DTOT = DataclassProtocol | DeclarativeBase

DTOFactoryT = TypeVar("DTOFactoryT", bound=DataclassDTO[Any] | SQLAlchemyDTO[Any] | PydanticDTO[Any])
type SQLAlchemyModelT = DeclarativeBase
type DataclassModelT = DataclassProtocol
type PydanticModelT = BaseModel
type ModelT = SQLAlchemyModelT | DataclassModelT | PydanticModelT


@overload
def config(
    backend: Literal["sqlalchemy"] = "sqlalchemy",
    exclude: AbstractSet[str] | None = None,
    rename_fields: dict[str, str] | None = None,
    rename_strategy: RenameStrategy | None = None,
    max_nested_depth: int | None = None,
    *,
    partial: bool | None = None,
) -> SQLAlchemyDTOConfig: ...


@overload
def config(
    backend: Literal["dataclass"] = "dataclass",
    exclude: AbstractSet[str] | None = None,
    rename_fields: dict[str, str] | None = None,
    rename_strategy: RenameStrategy | None = None,
    max_nested_depth: int | None = None,
    *,
    partial: bool | None = None,
) -> DTOConfig: ...


def config(
    backend: Literal["dataclass", "sqlalchemy"] = "dataclass",  # noqa: ARG001
    exclude: AbstractSet[str] | None = None,
    rename_fields: dict[str, str] | None = None,
    rename_strategy: RenameStrategy | None = None,
    max_nested_depth: int | None = None,
    *,
    partial: bool | None = None,
) -> DTOConfig | SQLAlchemyDTOConfig:
    default_kwargs: dict[str, Any] = {"rename_strategy": "camel", "max_nested_depth": 2}
    if exclude:
        default_kwargs["exclude"] = exclude
    if rename_fields:
        default_kwargs["rename_fields"] = rename_fields
    if rename_strategy:
        default_kwargs["rename_strategy"] = rename_strategy
    if max_nested_depth:
        default_kwargs["max_nested_depth"] = max_nested_depth
    if partial:
        default_kwargs["partial"] = partial
    return DTOConfig(**default_kwargs)
