"""Command admission prevents engine sleep from bypassing readiness ownership.

At upstream 434ddbbc0e30522e897670681e503b797c12b7c1, fixed health/models
remain available during sleep and router autoload=false still permits sleeping
children. These tests prove the supported command profile, not live GPU behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from lychd.extensions.builtin.animator.runtimes import LlamaCppRuntimeAdapter
from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstoneConfig


@pytest.mark.parametrize("sleep", [None, -1])
@pytest.mark.parametrize("mode", ["single", "router"])
def test_managed_commands_explicitly_disable_engine_sleep(mode: str, sleep: int | None) -> None:
    fields: dict[str, object] = {"name": "managed", "startup_mode": mode, "sleep_idle_seconds": sleep}
    fields.update({"model_path": "/models/chat.gguf"} if mode == "single" else {"models_dir": "/models"})
    stone = LlamaCppSoulstoneConfig.model_validate(fields)

    command = LlamaCppRuntimeAdapter().plan(stone).exec_args

    assert command[:2] == ["--sleep-idle-seconds", "-1"]


@pytest.mark.parametrize("source", ["typed", "environment", "extra_args"])
def test_generated_cli_disables_sleep_above_global_and_model_presets(tmp_path: Path, source: str) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text("[*]\nsleep-idle-seconds=900\n[chat]\nmodel=/models/chat.gguf\nsleep-idle-seconds=30\n")
    fields: dict[str, object] = {"name": "router"}
    if source == "typed":
        fields["models_preset"] = str(preset)
    elif source == "environment":
        fields["env_vars"] = {"LLAMA_ARG_MODELS_PRESET": str(preset)}
    else:
        fields["extra_args"] = ["--models-preset", str(preset)]
    stone = LlamaCppSoulstoneConfig.model_validate(fields)

    command = LlamaCppRuntimeAdapter().plan(stone).exec_args

    # The pinned engine overlays the router CLI on each preset; preset parsing
    # or a missing local copy must never omit this command-level disabling value.
    assert command[:2] == ["--sleep-idle-seconds", "-1"]


@pytest.mark.parametrize("executable", [[], ["llama-server"], ["/custom/wrapper"]])
@pytest.mark.parametrize("source", [["-m", "/models/chat.gguf"], ["--models-preset", "/presets/router.ini"]])
def test_admitted_passthrough_retains_exact_command_bytes(executable: list[str], source: list[str]) -> None:
    command = [*executable, "--sleep-idle-seconds", "-1", *source]
    stone = LlamaCppSoulstoneConfig(name="raw", exec=tuple(command))

    assert LlamaCppRuntimeAdapter().plan(stone).exec_args == command


@pytest.mark.parametrize("field", ["exec", "extra_args"])
@pytest.mark.parametrize(
    "control",
    [
        ["--sleep-idle-seconds", "-1"],
        ["--sleep-idle-seconds", "30"],
        ["--sleep_idle_seconds", "30"],
        ["--sleep_idle-seconds", "30"],
        ["--sleep-idle-seconds=-1"],
        ["--sleep_idle_seconds=30"],
    ],
)
def test_later_sleep_controls_are_refused_without_guessing_argument_arity(field: str, control: list[str]) -> None:
    fields: dict[str, object] = {"name": "later-control"}
    fields[field] = ["llama-server", "--sleep-idle-seconds", "-1", *control] if field == "exec" else control
    if field == "extra_args":
        fields["model_path"] = "/models/chat.gguf"

    with pytest.raises(ValidationError, match="forbids later"):
        LlamaCppSoulstoneConfig.model_validate(fields)


@pytest.mark.parametrize("sleep", [0, 1, 900, -2])
def test_typed_sleep_cannot_enable_or_misconfigure_automatic_wake(sleep: int) -> None:
    with pytest.raises(ValidationError, match="sleep_idle_seconds"):
        LlamaCppSoulstoneConfig.model_validate(
            {"name": "typed", "model_path": "/models/chat.gguf", "sleep_idle_seconds": sleep}
        )


@pytest.mark.parametrize("value", ["", "0", "-2", "true", "1.0", "1_000", "2147483648", "--other-option"])
def test_invalid_prefix_values_cannot_hide_behind_a_later_disable(value: str) -> None:
    with pytest.raises(ValidationError, match="requires --sleep-idle-seconds -1"):
        LlamaCppSoulstoneConfig(
            name="invalid", exec=("llama-server", "--sleep-idle-seconds", value, "--sleep-idle-seconds", "-1")
        )


@pytest.mark.parametrize(
    "command",
    [
        ["llama-server", "-m", "/models/chat.gguf"],
        ["llama-server", "--models-preset", "/presets/unread.ini"],
        ["custom-wrapper", "--custom-listen", "8080"],
        ["llama-server", "--sleep-idle-seconds", "900"],
        ["llama-server", "--sleep-idle-seconds"],
        ["llama-server", "--sleep-idle-seconds=-1"],
        ["llama-server", "--sleep_idle_seconds", "-1"],
        ["llama-server", "-m", "/models/chat.gguf", "--sleep-idle-seconds", "-1"],
        ["--alias", "--sleep-idle-seconds", "-1"],
        ["", "--sleep-idle-seconds", "-1"],
    ],
)
def test_passthrough_requires_an_explicit_valid_disabling_flag(command: list[str]) -> None:
    with pytest.raises(ValidationError, match="sleep-idle-seconds"):
        LlamaCppSoulstoneConfig(name="unadmitted", exec=tuple(command))


@pytest.mark.parametrize(
    "command",
    [
        ["llama-server", "--sleep-idle-seconds", "-1", "--sleep_idle_seconds", "30"],
        ["llama-server", "--alias", "--sleep-idle-seconds=-1"],
    ],
)
def test_sleep_tokens_cannot_misrepresent_the_engine_argument_contract(command: list[str]) -> None:
    with pytest.raises(ValidationError, match="sleep-idle-seconds"):
        LlamaCppSoulstoneConfig(name="ambiguous", exec=tuple(command))
