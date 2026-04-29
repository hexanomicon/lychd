from __future__ import annotations

from pathlib import Path

from lychd.extensions.builtin.animator.llamacpp.parser_cli import LlamaCppCliInferenceParser
from lychd.extensions.builtin.animator.llamacpp.parser_models import (
    LlamaCppPresetDefaults,
    LlamaCppPresetDocument,
    LlamaCppRuntimeInference,
)
from lychd.extensions.builtin.animator.llamacpp.parser_preset import LlamaCppPresetParser


class LlamaCppCommandParser:
    """Compatibility facade combining CLI/env inference and preset parsing.

    The parser keeps a stable public API used by runtime planners and adapters,
    while delegating implementation details to focused helpers.
    """

    def __init__(
        self,
        *,
        cli: LlamaCppCliInferenceParser | None = None,
        preset: LlamaCppPresetParser | None = None,
    ) -> None:
        """Initialize parser helpers for command/env and preset concerns."""
        self._cli = cli or LlamaCppCliInferenceParser()
        self._preset = preset or LlamaCppPresetParser()

    def infer_args(self, args: list[str], *, source: str) -> LlamaCppRuntimeInference:
        """Infer runtime metadata from CLI args."""
        return self._cli.infer_args(args, source=source)

    def infer_env(self, env: dict[str, str]) -> LlamaCppRuntimeInference:
        """Infer runtime metadata from LLAMA_ARG_* env variables."""
        return self._cli.infer_env(env)

    def merge(
        self,
        *,
        primary: LlamaCppRuntimeInference,
        secondary: LlamaCppRuntimeInference,
    ) -> LlamaCppRuntimeInference:
        """Merge two inference objects with primary precedence."""
        return self._cli.merge(primary=primary, secondary=secondary)

    def inspect_exec_args(self, args: list[str]) -> list[str]:
        """Return non-fatal diagnostics for explicit passthrough command lines."""
        return self._cli.inspect_exec_args(args)

    def parse_preset_defaults(
        self,
        *,
        path: str,
        model_provider: str | None,
        model_path: str | None,
        preset: LlamaCppPresetDocument | None = None,
    ) -> LlamaCppPresetDefaults:
        """Parse known defaults from a preset document or preset path."""
        return self._preset.parse_preset_defaults(
            path=path,
            model_provider=model_provider,
            model_path=model_path,
            preset=preset,
        )

    def load_preset(self, path: str) -> LlamaCppPresetDocument:
        """Load and parse a preset file into section maps."""
        return self._preset.load_preset(path)

    def resolve_preset_path(self, value: str) -> Path:
        """Resolve a preset path relative to codex root when needed."""
        return self._preset.resolve_preset_path(value)


__all__ = [
    "LlamaCppCommandParser",
    "LlamaCppPresetDefaults",
    "LlamaCppPresetDocument",
    "LlamaCppRuntimeInference",
]
