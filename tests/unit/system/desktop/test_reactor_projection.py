"""Exercise preparation through the installed CLI and reload the bundle as a caged Vessel."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
import tomlkit
from click.testing import CliRunner

from lychd.cli import portable
from lychd.config.runes.registry import RuneRegistry, load_rune_registry
from lychd.config.settings.root import Settings
from lychd.domain.animation.services.declarations import compile_animator_declarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.orchestration.actuator import capability_config_generation
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppSoulstoneConfig
from lychd.extensions.host import assemble_extensions
from lychd.system.desktop import reactor
from lychd.system.desktop.reactor_link import ReactorProjection


def _invoke(environment: dict[str, str], *args: str) -> dict[str, str]:
    if source_path := os.environ.get("PYTHONPATH"):
        environment = {
            **environment,
            "PYTHONPATH": os.pathsep.join(str(Path(part).resolve()) for part in source_path.split(os.pathsep)),
        }
    result = subprocess.run(  # noqa: S603 -- current interpreter, disposable installation, fixed CLI commands
        [sys.executable, "-m", "lychd", *args], env=environment, capture_output=True, text=True, check=True, timeout=180
    )
    return json.loads(result.stdout)


def test_prepare_reloads_mixed_desktop_model_identities_and_operator_policy(tmp_path: Path) -> None:
    scratch = tmp_path.resolve()
    environment = {
        **{key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "WINDIR") if key in os.environ},
        "HOME": str(scratch),
        "USERPROFILE": str(scratch),
        "LOCALAPPDATA": str(scratch / "AppData" / "Local"),
        "XDG_CONFIG_HOME": str(scratch / "config"),
        "XDG_DATA_HOME": str(scratch / "data"),
        "XDG_CACHE_HOME": str(scratch / "cache"),
        "LYCHD_VESSEL_MODE": "native",
    }
    settings_file = Path(_invoke(environment, "platform")["settings"])
    settings_file.parent.mkdir(parents=True)
    body: dict[str, Any] = {
        "extensions": {"builtins": ["animator/llamacpp"]},
        "orchestration": {
            "switching": {
                "actuator": "native-process",
                "native_state_dir": str(scratch / "state"),
                "native_llama_server": str(scratch / "engine" / "llama-server"),
                "native_model_root": str(scratch / "models"),
                "min_priority_for_hard_swap": 82,
                "containers": [
                    {
                        "animator": "guest-model",
                        "engine": "docker",
                        "endpoint": "npipe:////./pipe/dockerDesktopLinuxEngine",
                        "container_id": "a" * 64,
                        "container_port": 8080,
                        "host_port": 18443,
                        "tls_sha256": "b" * 64,
                    }
                ],
            }
        },
        "weaver": {"bridge": {"revision": "2", "capability_key": "personal:chat:personal.q4"}},
    }
    settings_file.write_text(tomlkit.dumps(body), encoding="utf-8")
    shelf = settings_file.parent / "runes" / "animator" / "soulstones" / "llamacpp"
    shelf.mkdir(parents=True)
    for name, placement, model_path, port in (
        ("personal", "native", r"C:\Users\Operator\My Models\personal.q4.gguf", 28081),
        ("guest-model", "container", "/models/container.gguf", 28082),
    ):
        (shelf / f"{name}.toml").write_text(
            tomlkit.dumps(
                {
                    "name": name,
                    "placement": placement,
                    "model_path": model_path,
                    "startup_mode": "single",
                    "base_url": f"http://127.0.0.1:{port}/v1",
                }
            ),
            encoding="utf-8",
        )

    sources = _invoke(environment, "desktop", "reactor-prepare")
    bundle = Path(sources["LYCHD_REACTOR_BUNDLE"])
    assert Path(sources["LYCHD_REACTOR_INBOX"]).is_dir()
    assert Path(sources["LYCHD_REACTOR_JOURNAL"]).is_dir()
    projection = ReactorProjection.model_validate_json((bundle / "projection.json").read_bytes())
    assert projection.ports == {"personal": 28081, "guest-model": 28082}
    published_shelf = bundle / "config" / "lychd" / "runes" / "animator" / "soulstones" / "llamacpp"
    published = [tomllib.loads(path.read_text(encoding="utf-8")) for path in published_shelf.glob("*.toml")]
    assert {rune["name"]: rune["port"] for rune in published} == projection.ports
    guest_file = bundle / "config" / "lychd" / "lychd.toml"
    guest = Settings.model_validate(tomllib.loads(guest_file.read_text(encoding="utf-8")))
    switching = guest.orchestration.switching
    assert switching.actuator == "host-reactor"
    assert switching.native_llama_server is None
    assert switching.containers == ()
    extensions = assemble_extensions(guest)
    registry = AnimatorRegistry(
        declarations=compile_animator_declarations(
            settings=guest,
            runes=load_rune_registry(extensions, guest_file.parent / "runes"),
            lifecycle_binding_digest=projection.binding_digest,
        ),
        soulstone_registrations=extensions.soulstone_registrations,
        portal_registrations=extensions.portal_registrations,
    )
    registry.load(probe_readiness=False)
    assert capability_config_generation(registry) == projection.generation
    assert {"personal:chat:personal.q4", "guest-model:chat:container"} <= {
        spec.key for spec in registry.list_capabilities()
    }
    assert switching.min_priority_for_hard_swap == 82

    # An immutable bundle already mounted by a running Vessel retains its original policy.
    body["orchestration"]["switching"]["policy"] = "evict-idle"
    body["weaver"]["bridge"]["capability_key"] = "guest-model:chat:container"
    settings_file.write_text(tomlkit.dumps(body), encoding="utf-8")
    updated = Path(_invoke(environment, "desktop", "reactor-prepare")["LYCHD_REACTOR_BUNDLE"])
    assert updated != bundle
    replacement = tomllib.loads((updated / "config" / "lychd" / "lychd.toml").read_text(encoding="utf-8"))
    assert replacement["orchestration"]["switching"]["policy"] == "evict-idle"
    assert replacement["weaver"]["bridge"]["capability_key"] == "guest-model:chat:container"
    assert tomllib.loads(guest_file.read_text(encoding="utf-8"))["weaver"]["bridge"]["capability_key"] == (
        "personal:chat:personal.q4"
    )


@pytest.mark.parametrize(
    ("endpoint", "error"),
    [
        (None, "explicit http://127.0.0.1:20001/v1"),
        ("http://127.0.0.1:8000/v1", "Port 8000"),
        ("http://127.0.0.1:5432/v1", "Port 5432"),
        ("http://127.0.0.1:7134/v1", "Port 7134"),
        ("http://127.0.0.1:17134/v1", "Port 17134"),
    ],
)
def test_prepare_rejects_unusable_guest_endpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, endpoint: str | None, error: str
) -> None:
    # The independent host installation uses custom ports, so the guest's fixed
    # web/database listeners must still be reserved during host preparation.
    settings = Settings.model_validate(
        {
            "server": {"port": 20000, "database": {"port": 6543}},
            "extensions": {"builtins": ["animator/llamacpp"]},
            "orchestration": {
                "switching": {
                    "actuator": "native-process",
                    "native_state_dir": str(tmp_path / "state"),
                    "native_llama_server": str(tmp_path / "llama-server"),
                    "native_model_root": str(tmp_path / "models"),
                }
            },
        }
    )
    rune = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "personal",
            "placement": "native",
            "startup_mode": "single",
            "model_path": "fixed.gguf",
            **({"base_url": endpoint} if endpoint else {}),
        }
    )
    monkeypatch.setattr(reactor, "get_settings", lambda: settings)
    monkeypatch.setattr(reactor, "PATH_CRYPT_ROOT", tmp_path)
    monkeypatch.setattr(reactor, "get_extensions", lambda: assemble_extensions(settings))
    monkeypatch.setattr(reactor, "load_rune_registry", Mock(return_value=RuneRegistry([rune])))
    with pytest.raises(ValueError, match=error):
        reactor.prepare()


def test_portable_status_selects_only_the_prepared_reactor_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = Path(__file__).resolve().parents[4] / "deployments" / "portable-container"
    assert (project / "compose.reactor.yaml").is_file()
    monkeypatch.setenv("LYCHD_CONTAINER_DIR", str(project))
    monkeypatch.delenv("LYCHD_GGUF", raising=False)
    from lychd.system import constants
    from lychd.system.desktop.private import private_directory

    root = tmp_path / "desktop-reactor"
    monkeypatch.setattr(constants, "PATH_CRYPT_ROOT", tmp_path)
    for variable, directory in (
        ("INBOX", root / "inbox"),
        ("JOURNAL", root / "journal"),
        ("BUNDLE", root / "bundles" / ("a" * 64)),
    ):
        private_directory(directory)
        monkeypatch.setenv(f"LYCHD_REACTOR_{variable}", str(directory))
    monkeypatch.setenv("LYCHD_REACTOR_UID", "1001")
    monkeypatch.setattr(portable, "_local_engine", lambda: ["docker", "--context", "desktop-linux"])
    execute = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(portable.subprocess, "run", execute)
    runner = CliRunner()
    assert runner.invoke(portable.status).exit_code == 0
    arguments = execute.call_args.args[0]
    assert [arguments[index + 1] for index, flag in enumerate(arguments) if flag == "-f"] == [
        str(project / "compose.yaml"),
        str(project / "compose.reactor.yaml"),
    ]
    monkeypatch.delenv("LYCHD_REACTOR_INBOX")
    assert runner.invoke(portable.status).exit_code != 0
    execute.assert_called_once()
