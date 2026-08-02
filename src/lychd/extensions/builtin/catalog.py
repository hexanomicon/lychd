"""Trusted, static catalog of built-in extension register shims."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final


@dataclass(frozen=True)
class BuiltinExtension:
    """A built-in extension that may be selected in the Codex."""

    register_module: str
    description: str
    dependencies: tuple[str, ...] = ()


BUILTIN_EXTENSIONS: Final = MappingProxyType(
    {
        "animator": BuiltinExtension(
            register_module="lychd.extensions.builtin.animator.register",
            description="OpenAI-compatible portal and animator base schemas.",
        ),
        "animator/llamacpp": BuiltinExtension(
            register_module="lychd.extensions.builtin.animator.llamacpp.register",
            description="llama.cpp local Soulstone runtime.",
            dependencies=("animator",),
        ),
        "animator/exllamav3": BuiltinExtension(
            register_module="lychd.extensions.builtin.animator.exllamav3.register",
            description="Dynamic ExLlamaV3 Soulstone served by TabbyAPI.",
            dependencies=("animator",),
        ),
        "animator/vllm": BuiltinExtension(
            register_module="lychd.extensions.builtin.animator.vllm.register",
            description="vLLM local Soulstone runtime.",
            dependencies=("animator",),
        ),
        "animator/sglang": BuiltinExtension(
            register_module="lychd.extensions.builtin.animator.sglang.register",
            description="SGLang local Soulstone runtime.",
            dependencies=("animator",),
        ),
        "observability/phoenix": BuiltinExtension(
            register_module="lychd.extensions.builtin.observability.phoenix.register",
            description="Optional legacy Phoenix telemetry Eye (not native Oculus).",
        ),
        "simulation": BuiltinExtension(
            register_module="lychd.extensions.builtin.simulation.register",
            description="Shadow simulation rune schema.",
        ),
        "delegation": BuiltinExtension(
            register_module="lychd.extensions.builtin.delegation.register",
            description="Delegated-agent runtime catalogue and no-network reference adapter.",
        ),
    }
)


def builtin_register_module(extension_id: str) -> str:
    """Return the allowed register module for a selected built-in id."""
    extension = BUILTIN_EXTENSIONS.get(extension_id)
    if extension is None:
        known = ", ".join(sorted(BUILTIN_EXTENSIONS))
        msg = f"Unknown built-in extension {extension_id!r}. Known built-ins: {known}."
        raise ValueError(msg)
    return extension.register_module


def builtin_registration_order(extension_ids: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Expand explicit selections into dependency-first, duplicate-free order."""
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(extension_id: str) -> None:
        if extension_id in visited:
            return
        if extension_id in visiting:
            msg = f"Built-in extension dependency cycle includes {extension_id!r}."
            raise ValueError(msg)
        extension = BUILTIN_EXTENSIONS.get(extension_id)
        if extension is None:
            builtin_register_module(extension_id)
            return
        visiting.add(extension_id)
        for dependency_id in extension.dependencies:
            visit(dependency_id)
        visiting.remove(extension_id)
        visited.add(extension_id)
        ordered.append(extension_id)

    for extension_id in extension_ids:
        visit(extension_id)
    return tuple(ordered)
