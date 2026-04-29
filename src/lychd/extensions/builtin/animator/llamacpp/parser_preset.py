from __future__ import annotations

from pathlib import Path
from typing import Final

from lychd.extensions.builtin.animator.llamacpp.parser_models import (
    LlamaCppPresetDefaults,
    LlamaCppPresetDocument,
)
from lychd.system.constants import PATH_CODEX_ROOT


class LlamaCppPresetParser:
    """Load and interpret llama.cpp model preset files."""

    _PRESET_KEY_MAP: Final[dict[str, str]] = {
        "c": "n_ctx",
        "ctx-size": "n_ctx",
        "n_ctx": "n_ctx",
        "llama_arg_ctx_size": "n_ctx",
        "np": "n_parallel",
        "parallel": "n_parallel",
        "n-parallel": "n_parallel",
        "n_parallel": "n_parallel",
        "llama_arg_n_parallel": "n_parallel",
        "n-predict": "n_predict",
        "predict": "n_predict",
        "n": "n_predict",
        "n_predict": "n_predict",
        "llama_arg_n_predict": "n_predict",
        "temp": "temperature",
        "temperature": "temperature",
        "llama_arg_temperature": "temperature",
        "top-k": "top_k",
        "top_k": "top_k",
        "llama_arg_top_k": "top_k",
        "top-p": "top_p",
        "top_p": "top_p",
        "llama_arg_top_p": "top_p",
        "min-p": "min_p",
        "min_p": "min_p",
        "llama_arg_min_p": "min_p",
        "reasoning-format": "reasoning_format",
        "llama_arg_think": "reasoning_format",
    }
    _PRESET_MODEL_KEYS: Final[set[str]] = {"model", "m", "llama_arg_model"}
    _TRUE_VALUES: Final[set[str]] = {"1", "on", "true", "enabled", "yes"}
    _FALSE_VALUES: Final[set[str]] = {"0", "off", "false", "disabled", "no"}

    def parse_preset_defaults(
        self,
        *,
        path: str,
        model_provider: str | None,
        model_path: str | None,
        preset: LlamaCppPresetDocument | None = None,
    ) -> LlamaCppPresetDefaults:
        """Parse known defaults from global and matching model sections."""
        document = preset or self.load_preset(path)
        if document.error is not None:
            return LlamaCppPresetDefaults(values={})

        sections = document.sections
        global_defaults = self._extract_known_preset_values(sections.get("*", {}))
        model_section = self._select_model_section(
            sections=sections,
            model_provider=model_provider,
            model_path=model_path,
        )
        model_defaults = self._extract_known_preset_values(sections.get(model_section, {})) if model_section else {}
        return LlamaCppPresetDefaults(values={**global_defaults, **model_defaults}, model_section=model_section)

    def load_preset(self, path: str) -> LlamaCppPresetDocument:
        """Load and parse a preset file into section maps."""
        preset_path = self.resolve_preset_path(path)
        if not preset_path.exists() or not preset_path.is_file():
            return LlamaCppPresetDocument(path=preset_path, sections={}, error="missing")

        try:
            lines = preset_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return LlamaCppPresetDocument(path=preset_path, sections={}, error="read_error")

        return LlamaCppPresetDocument(path=preset_path, sections=self._parse_ini_sections(lines))

    def resolve_preset_path(self, value: str) -> Path:
        """Resolve preset path relative to codex root when needed."""
        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            return candidate
        return PATH_CODEX_ROOT / candidate

    def _parse_ini_sections(self, lines: list[str]) -> dict[str, dict[str, str]]:
        sections: dict[str, dict[str, str]] = {}
        current = ""
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith(("#", ";")):
                continue
            if line.startswith("[") and line.endswith("]"):
                current = line[1:-1].strip()
                sections.setdefault(current, {})
                continue
            if "=" not in line or current == "":
                continue
            key, value = line.split("=", 1)
            sections[current][key.strip()] = value.strip()
        return sections

    def _extract_known_preset_values(self, options: dict[str, str]) -> dict[str, object]:
        result: dict[str, object] = {}
        for raw_key, raw_value in options.items():
            canonical = self._PRESET_KEY_MAP.get(raw_key.strip().lower())
            if canonical is None:
                continue
            parsed = self._coerce_preset_value(raw_value)
            result[canonical] = parsed
        return result

    def _coerce_preset_value(self, value: str) -> object:
        cleaned = value.strip()
        lowered = cleaned.lower()
        if lowered in self._TRUE_VALUES:
            return True
        if lowered in self._FALSE_VALUES:
            return False
        try:
            if any(char in cleaned for char in (".", "e", "E")):
                return float(cleaned)
            return int(cleaned)
        except ValueError:
            return cleaned

    def _select_model_section(
        self,
        *,
        sections: dict[str, dict[str, str]],
        model_provider: str | None,
        model_path: str | None,
    ) -> str | None:
        model_sections = {name: options for name, options in sections.items() if name != "*"}
        if not model_sections:
            return None

        candidates = self._model_identity_candidates(model_provider) + self._model_identity_candidates(model_path)
        by_name = self._match_section_by_name(model_sections=model_sections, candidates=candidates)
        if by_name:
            return by_name

        by_model_path = self._match_section_by_model_path(model_sections=model_sections, model_path=model_path)
        if by_model_path:
            return by_model_path

        if len(model_sections) == 1:
            return next(iter(model_sections))
        return None

    def _match_section_by_name(self, *, model_sections: dict[str, dict[str, str]], candidates: list[str]) -> str | None:
        for candidate in candidates:
            if candidate in model_sections:
                return candidate

        normalized_sections = {name.lower(): name for name in model_sections}
        for candidate in candidates:
            matched = normalized_sections.get(candidate.lower())
            if matched:
                return matched
        return None

    def _match_section_by_model_path(
        self,
        *,
        model_sections: dict[str, dict[str, str]],
        model_path: str | None,
    ) -> str | None:
        if not model_path:
            return None

        model_path_candidates = {item.lower() for item in self._model_identity_candidates(model_path)}
        for section_name, options in model_sections.items():
            section_model = self._extract_section_model(options)
            if not section_model:
                continue
            section_model_candidates = {item.lower() for item in self._model_identity_candidates(section_model)}
            if model_path_candidates.intersection(section_model_candidates):
                return section_name
        return None

    def _extract_section_model(self, options: dict[str, str]) -> str | None:
        for key, value in options.items():
            if key.strip().lower() in self._PRESET_MODEL_KEYS:
                return value.strip()
        return None

    def _model_identity_candidates(self, value: str | None) -> list[str]:
        if value is None:
            return []
        stripped = value.strip()
        if not stripped:
            return []
        path = Path(stripped)
        return [part for part in dict.fromkeys((stripped, path.name, path.stem)) if part]


__all__ = ["LlamaCppPresetParser"]
