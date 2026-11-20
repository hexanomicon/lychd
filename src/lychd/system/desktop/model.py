"""Bind the local browser Bridge to a real single-model llama.cpp runtime."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import click
import tomlkit

from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstoneConfig
from lychd.system.constants import PATH_LYCHD_TOML, PATH_SOULSTONES_DIR
from lychd.system.desktop.private import check_native_inputs, check_path

_BRIDGE_KEY = "personal:chat:personal-model"
_HEADER = "# Managed by lychd desktop configure-model.\n"


def _replace(path: Path, value: str) -> None:
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(value)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def configure(engine: Path, model: Path, port: int) -> None:
    """Bind the installed native engine and GGUF while retaining other extension selections."""
    engine = engine.resolve(strict=True)
    model = model.resolve(strict=True)
    try:
        check_native_inputs(engine, model)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    if engine.name.lower() not in {"llama-server.exe", "llama-server"} or not os.access(engine, os.X_OK):
        msg = "The engine must be an executable llama-server or llama-server.exe."
        raise click.ClickException(msg)
    with model.open("rb") as stream:
        if model.suffix.lower() != ".gguf" or stream.read(4) != b"GGUF":
            msg = "Select a local GGUF model file."
            raise click.ClickException(msg)
    check_path(PATH_LYCHD_TOML)
    if not PATH_LYCHD_TOML.is_file():
        msg = "Run lychd desktop install before configuring the browser model."
        raise click.ClickException(msg)
    document: Any = tomlkit.parse(PATH_LYCHD_TOML.read_text(encoding="utf-8"))
    switching = document.get("orchestration", {}).get("switching", {})
    if switching.get("actuator") != "native-process":
        msg = "The current settings must select the native-process actuator."
        raise click.ClickException(msg)
    weaver = document.setdefault("weaver", tomlkit.table())
    bridge = weaver.get("bridge")
    selection = {"revision": "2", "capability_key": _BRIDGE_KEY}
    if bridge is not None and bridge != selection:
        msg = "Existing weaver.bridge selection differs; reconcile that configuration before binding a desktop model."
        raise click.ClickException(msg)
    extensions = document.setdefault("extensions", tomlkit.table())
    builtins = extensions.setdefault("builtins", tomlkit.array())
    if "animator/llamacpp" not in builtins:
        builtins.append("animator/llamacpp")
    weaver["bridge"] = selection
    switching.update({"native_llama_server": str(engine), "native_model_root": str(model.parent)})
    rune = {
        "name": "personal",
        "startup_mode": "single",
        "structured_output": "json-schema",
        "cache_type_k": "f16",
        "cache_type_v": "f16",
        "model_path": str(model),
        "served_model_id": "personal-model",
        "port": port,
        "base_url": f"http://127.0.0.1:{port}/v1",
    }
    LlamaCppSoulstoneConfig.model_validate(rune)
    path = PATH_SOULSTONES_DIR / "llamacpp" / "personal.toml"
    check_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not path.read_text(encoding="utf-8").startswith(_HEADER):
        msg = f"Preserved existing user-managed Rune {path}; reconcile it before configuring a desktop model."
        raise click.ClickException(msg)
    _replace(path, _HEADER + tomlkit.dumps(rune))
    _replace(PATH_LYCHD_TOML, tomlkit.dumps(document))
